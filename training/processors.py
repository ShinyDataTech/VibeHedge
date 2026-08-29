"""
FinRL Technical Indicators & Cross-Asset Relative Strength Processor
===================================================================

Enriches raw hourly OHLCV bars with FinRL technical trend/momentum indicators
and cross-asset Relative Strength (RS) features against the SPY market baseline
to capture capital rotation, sector breakdowns, and macro market divergence.
"""

import logging
from typing import List, Optional, Union, Dict, Any
import pandas as pd
import numpy as np
from stockstats import StockDataFrame

logger = logging.getLogger("processors")


class FinRLDataProcessor:
    """Processes financial time-series data using FinRL indicators and cross-asset Relative Strength."""

    DEFAULT_INDICATORS: List[str] = [
        "macd",
        "macds",
        "macdh",
        "rsi_14",
        "rsi_30",
        "boll_ub",
        "boll_lb",
        "atr_14",
        "cci_14",
        "dx_14",
        "close_20_sma",
        "close_50_sma",
        "close_12_ema",
        "close_26_ema",
    ]

    def __init__(self, indicators: Optional[List[str]] = None):
        self.indicators = indicators or self.DEFAULT_INDICATORS

    def add_technical_indicators(
        self,
        df: pd.DataFrame,
        benchmark_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Append FinRL technical trend indicators and Cross-Asset Relative Strength features.

        Args:
            df: DataFrame containing ['timestamp', 'open', 'high', 'low', 'close', 'volume'].
            benchmark_df: Optional benchmark DataFrame (e.g. SPY) aligned on timestamps.

        Returns:
            DataFrame with enriched technical and cross-asset relative strength feature columns.
        """
        if df.empty:
            return df

        df = df.copy()
        # Sort chronologically and standardize timestamps
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)

        # Initialize stockstats wrapper
        stock = StockDataFrame.retype(df.copy())

        # 1. Compute standard FinRL indicators
        for ind in self.indicators:
            try:
                df[ind] = stock[ind].values
            except Exception as e:
                logger.warning(f"Error computing indicator {ind}: {e}")

        # 2. Bollinger Band Width and Position (%B)
        if "boll_ub" in df.columns and "boll_lb" in df.columns:
            band_width = df["boll_ub"] - df["boll_lb"]
            df["boll_bandwidth"] = np.where(df["close"] > 0, band_width / df["close"], 0.0)
            df["boll_pct_b"] = np.where(band_width > 0, (df["close"] - df["boll_lb"]) / band_width, 0.5)

        # 3. Moving Average Cross Ratios (Short vs Long MA)
        if "close_20_sma" in df.columns and "close_50_sma" in df.columns:
            df["sma_ratio_20_50"] = np.where(df["close_50_sma"] > 0, df["close_20_sma"] / df["close_50_sma"] - 1.0, 0.0)

        # 4. Hourly Returns & Rolling Volatility
        df["return_1h"] = df["close"].pct_change()
        df["return_4h"] = df["close"].pct_change(4)
        df["return_24h"] = df["close"].pct_change(24)
        df["volatility_24h"] = df["return_1h"].rolling(window=24).std()

        # 5. Volume Price Trend Momentum
        if "volume" in df.columns:
            df["volume_sma_20"] = df["volume"].rolling(window=20).mean()
            df["volume_ratio"] = np.where(df["volume_sma_20"] > 0, df["volume"] / df["volume_sma_20"], 1.0)

        # 6. Cross-Asset Relative Strength & Capital Rotation Features (vs SPY Baseline)
        if benchmark_df is not None and not benchmark_df.empty:
            bm = benchmark_df.copy()
            bm["timestamp"] = pd.to_datetime(bm["timestamp"])
            bm = bm.sort_values("timestamp").reset_index(drop=True)
            bm["spy_return_1h"] = bm["close"].pct_change()
            bm["spy_return_4h"] = bm["close"].pct_change(4)
            bm["spy_return_24h"] = bm["close"].pct_change(24)
            bm_lookup = bm[["timestamp", "close", "spy_return_1h", "spy_return_4h", "spy_return_24h"]].rename(
                columns={"close": "spy_close"}
            )

            # Merge on timestamp
            merged = pd.merge(df, bm_lookup, on="timestamp", how="left")
            merged["spy_close"] = merged["spy_close"].ffill().bfill()
            merged["spy_return_1h"] = merged["spy_return_1h"].fillna(0.0)
            merged["spy_return_4h"] = merged["spy_return_4h"].fillna(0.0)
            merged["spy_return_24h"] = merged["spy_return_24h"].fillna(0.0)

            # Relative Strength Price Ratio (Asset Price / SPY Price)
            rs_price_ratio = np.where(merged["spy_close"] > 0, merged["close"] / merged["spy_close"], 1.0)
            df["rs_ratio_to_spy"] = rs_price_ratio
            df["rs_ratio_sma20"] = pd.Series(rs_price_ratio).rolling(window=20).mean().bfill().ffill().values
            df["rs_ratio_momentum"] = np.where(df["rs_ratio_sma20"] > 0, df["rs_ratio_to_spy"] / df["rs_ratio_sma20"] - 1.0, 0.0)

            # Relative Momentum (Excess returns over SPY)
            df["rs_excess_return_1h"] = df["return_1h"].values - merged["spy_return_1h"].values
            df["rs_excess_return_4h"] = df["return_4h"].values - merged["spy_return_4h"].values
            df["rs_excess_return_24h"] = df["return_24h"].values - merged["spy_return_24h"].values

            # Sector Breakdown Indicator: Asset severely lagging broader market (>1.2% underperformance over 24h)
            df["sector_breakdown_flag"] = (df["rs_excess_return_24h"] < -0.012).astype(float)

            # Rolling 24-hour Covariance / Beta to SPY
            cov_24 = df["return_1h"].rolling(window=24).cov(merged["spy_return_1h"])
            var_24 = merged["spy_return_1h"].rolling(window=24).var()
            df["beta_to_spy_24h"] = np.where(var_24 > 1e-8, cov_24 / var_24, 1.0)
        else:
            # Baseline placeholder when processing SPY itself or standalone
            df["rs_ratio_to_spy"] = 1.0
            df["rs_ratio_sma20"] = 1.0
            df["rs_ratio_momentum"] = 0.0
            df["rs_excess_return_1h"] = 0.0
            df["rs_excess_return_4h"] = 0.0
            df["rs_excess_return_24h"] = 0.0
            df["sector_breakdown_flag"] = 0.0
            df["beta_to_spy_24h"] = 1.0

        # 7. Macro Downtrend Labels for Training (Forecast Horizon: 24 hours)
        df["forward_return_24h"] = df["close"].pct_change(-24) * -1.0 # negative forward return is downtrend magnitude
        df["is_downtrend_24h"] = (df["close"].pct_change(-24) < -0.015).astype(float)

        # Clean NaN values resulting from rolling windows
        df = df.bfill().ffill().fillna(0.0)

        logger.info(f"Appended {len(self.indicators) + 16} technical & Relative Strength features. Total features: {df.shape[1]}")
        return df

    def process_cross_asset_panel(
        self,
        raw_data_dict: Dict[str, pd.DataFrame],
        benchmark_symbol: str = "SPY"
    ) -> Dict[str, pd.DataFrame]:
        """
        Processes a full panel of ETF assets, calculating Relative Strength features against benchmark.

        Args:
            raw_data_dict: Dictionary mapping symbol -> raw hourly DataFrame.
            benchmark_symbol: Baseline symbol for Relative Strength (default: 'SPY').

        Returns:
            Dictionary mapping symbol -> processed DataFrame with cross-asset features.
        """
        processed_panel = {}
        benchmark_df = raw_data_dict.get(benchmark_symbol)

        if benchmark_df is None:
            logger.warning(f"Benchmark symbol '{benchmark_symbol}' not found in raw data. Processing without benchmark.")

        for symbol, df in raw_data_dict.items():
            logger.info(f"Processing FinRL and Relative Strength features for {symbol} (benchmark: {benchmark_symbol})...")
            # For SPY itself, benchmark_df is None so it serves as baseline
            bm = benchmark_df if symbol != benchmark_symbol else None
            processed_df = self.add_technical_indicators(df, benchmark_df=bm)
            processed_df["symbol"] = symbol
            processed_panel[symbol] = processed_df

        return processed_panel

    def get_feature_matrix(
        self,
        df: pd.DataFrame,
        feature_cols: Optional[List[str]] = None
    ) -> np.ndarray:
        """Extracts numerical feature array suitable for ML model input."""
        if feature_cols is None:
            exclude = ["timestamp", "symbol", "is_downtrend_24h", "forward_return_24h"]
            feature_cols = [c for c in df.columns if c not in exclude and np.issubdtype(df[c].dtype, np.number)]

        return df[feature_cols].values
