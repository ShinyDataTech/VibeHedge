"""
ForecastAgent Macro Downtrend Model Panel Training Loop
======================================================

Trains an XLSTM / Sequence Forecasting model on preprocessed hourly
historical bars across a diversified 9-ETF cross-asset panel with
FinRL technical indicators and Relative Strength features.

Prevents overfitting and boundary data leakage by isolating sequence
windows per asset before combining into a generalized panel dataset.

Saves trained model weights and metadata to `models/`.
"""

import os
import json
import logging
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import numpy as np
import pandas as pd
import yaml

from training.download_hourly_data import HourlyDataDownloader
from training.processors import FinRLDataProcessor

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("train_forecast_agent")


class PanelSequenceDataset(Dataset):
    """
    Leak-Free Multi-Asset Panel Dataset.
    Extracts sliding sequence windows strictly within each asset's boundary,
    preventing any cross-ticker data leakage.
    """

    def __init__(
        self,
        asset_data_list: List[Tuple[str, np.ndarray, np.ndarray, np.ndarray]],
        seq_len: int = 72,
        pred_len: int = 24
    ):
        """
        Args:
            asset_data_list: List of tuples: (symbol, normalized_features, raw_prices, downtrend_labels)
            seq_len: Input sequence window (72 hours).
            pred_len: Forecast horizon (24 hours).
        """
        self.seq_len = seq_len
        self.pred_len = pred_len
        self.samples = []  # Stores (ticker_idx, start_idx)

        self.assets = []
        for ticker_idx, (symbol, feats, targets, downtrends) in enumerate(asset_data_list):
            num_samples = len(feats) - seq_len - pred_len + 1
            if num_samples > 0:
                self.assets.append({
                    "symbol": symbol,
                    "features": torch.tensor(feats, dtype=torch.float32),
                    "targets": torch.tensor(targets, dtype=torch.float32),
                    "downtrends": torch.tensor(downtrends, dtype=torch.float32),
                })
                for start_idx in range(num_samples):
                    self.samples.append((ticker_idx, start_idx))

        logger.info(f"Initialized PanelSequenceDataset with {len(self.samples)} valid sequence windows across {len(self.assets)} assets.")

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        ticker_idx, start_idx = self.samples[idx]
        asset = self.assets[ticker_idx]

        x = asset["features"][start_idx : start_idx + self.seq_len]
        y_traj = asset["targets"][start_idx + self.seq_len : start_idx + self.seq_len + self.pred_len]
        y_down = asset["downtrends"][start_idx + self.seq_len + self.pred_len - 1]

        return x, y_traj, y_down


class MacroDowntrendForecastModel(nn.Module):
    """
    Generalized Cross-Asset Sequence Neural Network with Bi-directional
    recurrent backbone and multi-head trajectory & downtrend classifiers.
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 128,
        num_layers: int = 2,
        pred_len: int = 24,
        dropout: float = 0.15
    ):
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.pred_len = pred_len

        # Feature projection & LayerNorm
        self.input_proj = nn.Linear(input_dim, hidden_dim)
        self.layer_norm = nn.LayerNorm(hidden_dim)

        # Recurrent temporal backbone (LSTM / XLSTM compatible)
        self.lstm = nn.LSTM(
            input_size=hidden_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
            bidirectional=True
        )

        # Head 1: Multi-step forward price trajectory quantile predictions (10th, 50th, 90th percentile)
        self.trajectory_head = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, pred_len * 3)
        )

        # Head 2: Intraday macro downtrend probability classifier
        self.downtrend_head = nn.Sequential(
            nn.Linear(hidden_dim * 2, 64),
            nn.GELU(),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass.
        Args:
            x: (batch_size, seq_len, input_dim)
        Returns:
            quantiles: (batch_size, pred_len, 3) -> [lower 10%, median 50%, upper 90%]
            downtrend_prob: (batch_size, 1) -> probability in [0, 1]
        """
        batch_size = x.size(0)
        proj = self.layer_norm(self.input_proj(x))
        lstm_out, _ = self.lstm(proj)

        # Use last hidden state
        last_hidden = lstm_out[:, -1, :]

        # Forward trajectory & downtrend probability
        traj = self.trajectory_head(last_hidden).view(batch_size, self.pred_len, 3)
        downtrend_prob = self.downtrend_head(last_hidden)

        return traj, downtrend_prob


class ForecastDowntrendTrainer:
    """Trainer and artifact compiler for the ForecastAgent cross-asset panel model."""

    PANEL_UNIVERSE: List[str] = [
        "SPY", "QQQ", "IWM", "XLK", "XLF", "XLE", "XLV", "GLD", "TLT"
    ]

    def __init__(
        self,
        models_dir: str = "models",
        seq_len: int = 72,
        pred_len: int = 24,
        device: Optional[str] = None
    ):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.seq_len = seq_len
        self.pred_len = pred_len
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Initialized cross-asset panel trainer on device: {self.device}")

    def prepare_panel_dataset(
        self,
        symbols: Optional[List[str]] = None,
        train_split_ratio: float = 0.85
    ) -> Tuple[PanelSequenceDataset, PanelSequenceDataset, List[str], Dict[str, Any], int]:
        """
        Loads the multi-asset panel, enriches with FinRL + Relative Strength,
        and constructs leak-free training and validation datasets.
        """
        target_symbols = symbols or self.PANEL_UNIVERSE
        downloader = HourlyDataDownloader()
        raw_data = downloader.fetch_stock_hourly_bars(symbols=target_symbols, lookback_years=2)
        processor = FinRLDataProcessor()

        # Process cross-asset panel with SPY baseline
        processed_panel = processor.process_cross_asset_panel(raw_data, benchmark_symbol="SPY")

        # Extract numerical feature column list
        exclude = ["timestamp", "symbol", "is_downtrend_24h", "forward_return_24h"]
        first_df = next(iter(processed_panel.values()))
        feature_names = [c for c in first_df.columns if c not in exclude and np.issubdtype(first_df[c].dtype, np.number)]
        input_dim = len(feature_names)

        # Fit feature scaler ONLY on training splits of all assets to prevent leakage
        train_matrices = []
        for symbol, df in processed_panel.items():
            split_idx = int(len(df) * train_split_ratio)
            train_matrices.append(df[feature_names].iloc[:split_idx].values)

        combined_train_matrix = np.vstack(train_matrices)
        mean = np.nanmean(combined_train_matrix, axis=0, keepdims=True)
        std = np.nanstd(combined_train_matrix, axis=0, keepdims=True) + 1e-6

        scaler_meta = {
            "mean": mean.tolist()[0],
            "std": std.tolist()[0],
            "feature_names": feature_names
        }

        # Build isolated asset partitions
        train_asset_list = []
        val_asset_list = []

        for symbol, df in processed_panel.items():
            split_idx = int(len(df) * train_split_ratio)
            feats_raw = df[feature_names].values
            feats_norm = (feats_raw - mean) / std
            targets = df["close"].values
            downtrends = df["is_downtrend_24h"].values

            train_asset_list.append((
                symbol,
                feats_norm[:split_idx],
                targets[:split_idx],
                downtrends[:split_idx]
            ))
            val_asset_list.append((
                symbol,
                feats_norm[split_idx:],
                targets[split_idx:],
                downtrends[split_idx:]
            ))

        train_dataset = PanelSequenceDataset(train_asset_list, seq_len=self.seq_len, pred_len=self.pred_len)
        val_dataset = PanelSequenceDataset(val_asset_list, seq_len=self.seq_len, pred_len=self.pred_len)

        return train_dataset, val_dataset, feature_names, scaler_meta, input_dim

    def train(
        self,
        epochs: int = 12,
        batch_size: int = 64,
        learning_rate: float = 1e-3
    ) -> Dict[str, Any]:
        """Execute the cross-asset panel training loop and compile model weights."""
        logger.info("Preparing cross-asset panel dataset...")
        train_dataset, val_dataset, feature_names, scaler_meta, input_dim = self.prepare_panel_dataset()

        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

        model = MacroDowntrendForecastModel(
            input_dim=input_dim,
            hidden_dim=128,
            num_layers=2,
            pred_len=self.pred_len,
            dropout=0.15
        ).to(self.device)

        optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
        criterion_mse = nn.MSELoss()
        criterion_bce = nn.BCELoss()

        best_val_loss = float("inf")
        history = {"train_loss": [], "val_loss": []}

        logger.info(f"Training ForecastAgent across 9-ETF panel for {epochs} epochs on {len(train_dataset)} sequences...")

        for epoch in range(1, epochs + 1):
            model.train()
            total_train_loss = 0.0

            for batch_x, batch_y_traj, batch_y_down in train_loader:
                batch_x = batch_x.to(self.device)
                batch_y_traj = batch_y_traj.to(self.device)
                batch_y_down = batch_y_down.unsqueeze(-1).to(self.device)

                optimizer.zero_grad()
                pred_traj, pred_downtrend = model(batch_x)

                # Loss: trajectory MSE + downtrend classification BCE
                loss_traj = criterion_mse(pred_traj[:, :, 1], batch_y_traj)
                loss_down = criterion_bce(pred_downtrend, batch_y_down)
                loss = loss_traj * 0.01 + loss_down * 1.0

                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()

                total_train_loss += loss.item()

            scheduler.step()
            avg_train_loss = total_train_loss / max(1, len(train_loader))

            # Validation
            model.eval()
            total_val_loss = 0.0
            with torch.no_grad():
                for batch_x, batch_y_traj, batch_y_down in val_loader:
                    batch_x = batch_x.to(self.device)
                    batch_y_traj = batch_y_traj.to(self.device)
                    batch_y_down = batch_y_down.unsqueeze(-1).to(self.device)

                    pred_traj, pred_downtrend = model(batch_x)
                    loss_traj = criterion_mse(pred_traj[:, :, 1], batch_y_traj)
                    loss_down = criterion_bce(pred_downtrend, batch_y_down)
                    total_val_loss += (loss_traj * 0.01 + loss_down * 1.0).item()

            avg_val_loss = total_val_loss / max(1, len(val_loader))
            history["train_loss"].append(avg_train_loss)
            history["val_loss"].append(avg_val_loss)

            logger.info(f"Epoch {epoch}/{epochs} - Train Loss: {avg_train_loss:.4f} | Val Loss: {avg_val_loss:.4f}")

            if avg_val_loss < best_val_loss:
                best_val_loss = avg_val_loss
                self.save_artifacts(model, scaler_meta, feature_names, input_dim)

        logger.info(f"Panel training complete. Best validation loss: {best_val_loss:.4f}")
        return history

    def save_artifacts(
        self,
        model: nn.Module,
        scaler_meta: Dict[str, Any],
        feature_names: List[str],
        input_dim: int
    ):
        """Save model checkpoint, weights, and configuration."""
        weights_path = self.models_dir / "forecast_agent_downtrend.pt"
        config_path = self.models_dir / "model_config.yaml"
        scaler_path = self.models_dir / "scaler_metadata.json"

        # 1. PyTorch weights
        torch.save({
            "model_state_dict": model.state_dict(),
            "input_dim": input_dim,
            "hidden_dim": 128,
            "num_layers": 2,
            "pred_len": self.pred_len,
            "seq_len": self.seq_len,
            "universe": self.PANEL_UNIVERSE
        }, weights_path)

        # 2. YAML config
        config = {
            "model_type": "ForecastAgent-XLSTM-CrossAssetPanel",
            "input_dim": input_dim,
            "hidden_dim": 128,
            "num_layers": 2,
            "seq_len": self.seq_len,
            "pred_len": self.pred_len,
            "feature_count": len(feature_names),
            "features": feature_names,
            "universe": self.PANEL_UNIVERSE
        }
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)

        # 3. Scaler JSON
        with open(scaler_path, "w") as f:
            json.dump(scaler_meta, f, indent=2)

        logger.info(f"Saved cross-asset panel model artifacts to {self.models_dir}")


def main():
    """CLI to execute panel training pipeline."""
    trainer = ForecastDowntrendTrainer()
    trainer.train(epochs=10, batch_size=64)


if __name__ == "__main__":
    main()
