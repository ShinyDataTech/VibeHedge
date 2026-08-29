"""
ForecastAgent Inference Predictor Module
=======================================

Loads the trained ForecastAgent weights and configuration to evaluate
real-time hourly macro downtrend probability and expected downside price movement.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import torch
import numpy as np
import pandas as pd
import yaml

from training.processors import FinRLDataProcessor
from training.train_forecast_agent import MacroDowntrendForecastModel

logger = logging.getLogger("forecast_predictor")


class ForecastDowntrendPredictor:
    """Inference engine for real-time macro downtrend probability forecasting."""

    def __init__(
        self,
        model_dir: str = "models",
        device: Optional[str] = None
    ):
        self.model_dir = Path(model_dir)
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.processor = FinRLDataProcessor()

        self.model: Optional[MacroDowntrendForecastModel] = None
        self.scaler_meta: Optional[Dict[str, Any]] = None
        self.config: Optional[Dict[str, Any]] = None

        self._load_artifacts()

    def _load_artifacts(self):
        """Loads saved weights, scaler metadata, and config from disk."""
        weights_path = self.model_dir / "forecast_agent_downtrend.pt"
        config_path = self.model_dir / "model_config.yaml"
        scaler_path = self.model_dir / "scaler_metadata.json"

        if not weights_path.exists():
            logger.warning(f"Weights file not found at {weights_path}. Model will need to be trained first.")
            return

        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        with open(scaler_path, "r") as f:
            self.scaler_meta = json.load(f)

        checkpoint = torch.load(weights_path, map_location=self.device)

        self.model = MacroDowntrendForecastModel(
            input_dim=checkpoint["input_dim"],
            hidden_dim=checkpoint.get("hidden_dim", 128),
            num_layers=checkpoint.get("num_layers", 2),
            pred_len=checkpoint.get("pred_len", 24)
        ).to(self.device)

        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.eval()
        logger.info("Successfully loaded ForecastAgent downtrend model weights.")

    def predict_downtrend(
        self,
        recent_hourly_bars: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Evaluate real-time market bars to compute downtrend probability and price forecast.

        Args:
            recent_hourly_bars: DataFrame containing at least 72 hourly OHLCV bars.

        Returns:
            Dictionary with:
                - 'is_bearish': bool (True if downtrend_prob > 0.60 or median return < -0.015)
                - 'downtrend_probability': float (0.0 to 1.0)
                - 'forecast_horizon_hours': int
                - 'predicted_median_return_pct': float
                - 'projected_trajectory': list of forecasted prices
                - 'confidence_level': str ('HIGH', 'MEDIUM', 'LOW')
        """
        if self.model is None or self.scaler_meta is None:
            # Fallback heuristic if weights not loaded
            logger.warning("ForecastAgent model not loaded. Running fallback rule-based trend evaluation.")
            return self._heuristic_fallback(recent_hourly_bars)

        # Ensure basic required columns are present or imputed
        if "vwap" not in recent_hourly_bars.columns and "close" in recent_hourly_bars.columns:
            recent_hourly_bars = recent_hourly_bars.copy()
            recent_hourly_bars["vwap"] = recent_hourly_bars["close"]
        if "trades" not in recent_hourly_bars.columns:
            recent_hourly_bars = recent_hourly_bars.copy()
            recent_hourly_bars["trades"] = 1000

        # 1. Process recent bars with FinRL indicators
        df_proc = self.processor.add_technical_indicators(recent_hourly_bars)

        feature_cols = self.scaler_meta["feature_names"]
        # Ensure any missing feature in df_proc is filled with 0.0
        for col in feature_cols:
            if col not in df_proc.columns:
                df_proc[col] = 0.0

        seq_len = self.config.get("seq_len", 72)

        # Take last seq_len rows
        if len(df_proc) < seq_len:
            logger.warning(f"Input bars ({len(df_proc)}) < required seq_len ({seq_len}). Padding with oldest bar.")
            pad_count = seq_len - len(df_proc)
            pad_df = pd.concat([df_proc.iloc[[0]] * 1] * pad_count, ignore_index=True)
            df_proc = pd.concat([pad_df, df_proc], ignore_index=True)

        features = df_proc[feature_cols].tail(seq_len).values

        # Normalize features
        mean = np.array(self.scaler_meta["mean"])
        std = np.array(self.scaler_meta["std"])
        features_norm = (features - mean) / std

        # Convert to tensor
        x_tensor = torch.tensor(features_norm, dtype=torch.float32).unsqueeze(0).to(self.device)

        with torch.no_grad():
            traj, downtrend_prob = self.model(x_tensor)
            prob = float(downtrend_prob.item())
            pred_median_traj = traj[0, :, 1].cpu().numpy().tolist()

        current_price = float(recent_hourly_bars["close"].iloc[-1])
        expected_final_price = pred_median_traj[-1] if pred_median_traj else current_price
        pct_change = (expected_final_price - current_price) / max(current_price, 1e-6)

        is_bearish = (prob >= 0.55) or (pct_change < -0.015)

        confidence = "HIGH" if prob > 0.75 or prob < 0.25 else ("MEDIUM" if prob > 0.60 else "LOW")

        return {
            "is_bearish": bool(is_bearish),
            "downtrend_probability": round(prob, 4),
            "forecast_horizon_hours": self.config.get("pred_len", 24),
            "current_price": round(current_price, 2),
            "projected_price_24h": round(expected_final_price, 2),
            "predicted_median_return_pct": round(pct_change * 100, 2),
            "confidence_level": confidence,
            "projected_trajectory": [round(p, 2) for p in pred_median_traj]
        }

    def _heuristic_fallback(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Rule-based trend analysis when deep model weights are uncompiled."""
        current_price = float(df["close"].iloc[-1])
        ma20 = float(df["close"].tail(20).mean())
        ma50 = float(df["close"].tail(50).mean()) if len(df) >= 50 else ma20
        rsi = 50.0

        is_bearish = current_price < ma20 and ma20 < ma50
        prob = 0.70 if is_bearish else 0.30

        return {
            "is_bearish": bool(is_bearish),
            "downtrend_probability": prob,
            "forecast_horizon_hours": 24,
            "current_price": round(current_price, 2),
            "projected_price_24h": round(current_price * (0.98 if is_bearish else 1.01), 2),
            "predicted_median_return_pct": -2.0 if is_bearish else 1.0,
            "confidence_level": "MEDIUM",
            "projected_trajectory": [round(current_price * 0.98, 2)] * 24
        }
