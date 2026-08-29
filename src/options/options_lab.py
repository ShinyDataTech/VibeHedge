"""
Vibe-Trading Options Lab Quantitative Engine
============================================

Implements Black-Scholes pricing, Greeks analysis (Delta, Gamma, Vega, Theta, Rho),
and optimal protective put strike & expiry calculations for portfolio hedging.
"""

import math
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
from scipy.stats import norm

logger = logging.getLogger("options_lab")


@dataclass
class OptionGreeks:
    """Option Greeks and analytical pricing container."""
    price: float
    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float
    intrinsic_value: float
    extrinsic_value: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "price": round(self.price, 4),
            "delta": round(self.delta, 4),
            "gamma": round(self.gamma, 6),
            "vega": round(self.vega, 4),
            "theta": round(self.theta, 4),
            "rho": round(self.rho, 4),
            "intrinsic_value": round(self.intrinsic_value, 4),
            "extrinsic_value": round(self.extrinsic_value, 4),
        }


@dataclass
class ProtectivePutRecommendation:
    """Optimal protective put hedge recommendation."""
    underlying_symbol: str
    spot_price: float
    strike_price: float
    expiry_days: int
    expiry_date: str
    option_symbol: str  # Standard OCC / Alpaca symbol (e.g. SPY260918P00550000)
    option_type: str = "put"
    contract_qty: int = 1
    per_contract_premium: float = 0.0
    total_hedge_cost: float = 0.0
    hedge_cost_pct_of_portfolio: float = 0.0
    portfolio_delta_covered: float = 0.0
    breakeven_price: float = 0.0
    max_downside_protection: float = 0.0
    greeks: Optional[OptionGreeks] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "underlying_symbol": self.underlying_symbol,
            "spot_price": round(self.spot_price, 2),
            "strike_price": round(self.strike_price, 2),
            "expiry_days": self.expiry_days,
            "expiry_date": self.expiry_date,
            "option_symbol": self.option_symbol,
            "option_type": self.option_type,
            "contract_qty": self.contract_qty,
            "per_contract_premium": round(self.per_contract_premium, 2),
            "total_hedge_cost": round(self.total_hedge_cost, 2),
            "hedge_cost_pct_of_portfolio": round(self.hedge_cost_pct_of_portfolio * 100, 2),
            "portfolio_delta_covered": round(self.portfolio_delta_covered, 2),
            "breakeven_price": round(self.breakeven_price, 2),
            "max_downside_protection": round(self.max_downside_protection, 2),
            "greeks": self.greeks.to_dict() if self.greeks else {}
        }


class OptionsLab:
    """Quantitative options pricing and hedge structuring engine."""

    def __init__(self, default_risk_free_rate: float = 0.045):
        self.risk_free_rate = default_risk_free_rate

    def black_scholes_greeks(
        self,
        spot: float,
        strike: float,
        expiry_days: float,
        volatility: float = 0.25,
        risk_free_rate: Optional[float] = None,
        option_type: str = "put"
    ) -> OptionGreeks:
        r"""
        Calculate Black-Scholes option price and Greeks (Delta, Gamma, Vega, Theta, Rho).

        Args:
            spot: Current underlying price ($S$).
            strike: Strike price ($K$).
            expiry_days: Days until expiration ($T$ in days).
            volatility: Annualized implied volatility ($\sigma$).
            risk_free_rate: Annual risk-free interest rate ($r$).
            option_type: 'put' or 'call'.

        Returns:
            OptionGreeks object.
        """
        r = risk_free_rate if risk_free_rate is not None else self.risk_free_rate
        T = max(1e-4, expiry_days / 365.25)
        sigma = max(1e-4, volatility)
        S = max(1e-4, spot)
        K = max(1e-4, strike)

        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)

        pdf_d1 = norm.pdf(d1)
        cdf_d1 = norm.cdf(d1)
        cdf_d2 = norm.cdf(d2)

        # Gamma (same for call and put)
        gamma = pdf_d1 / (S * sigma * math.sqrt(T))

        # Vega (1% change in vol)
        vega = (S * math.sqrt(T) * pdf_d1) / 100.0

        if option_type.lower() == "call":
            price = S * cdf_d1 - K * math.exp(-r * T) * cdf_d2
            delta = cdf_d1
            theta = (-(S * pdf_d1 * sigma) / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * cdf_d2) / 365.25
            rho = (K * T * math.exp(-r * T) * cdf_d2) / 100.0
            intrinsic = max(0.0, S - K)
        else:
            # Put
            price = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
            delta = cdf_d1 - 1.0 # Delta in [-1, 0]
            theta = (-(S * pdf_d1 * sigma) / (2 * math.sqrt(T)) + r * K * math.exp(-r * T) * norm.cdf(-d2)) / 365.25
            rho = (-K * T * math.exp(-r * T) * norm.cdf(-d2)) / 100.0
            intrinsic = max(0.0, K - S)

        extrinsic = max(0.0, price - intrinsic)

        return OptionGreeks(
            price=max(0.01, price),
            delta=delta,
            gamma=gamma,
            vega=vega,
            theta=theta,
            rho=rho,
            intrinsic_value=intrinsic,
            extrinsic_value=extrinsic
        )

    def calculate_optimal_protective_put(
        self,
        portfolio_equity: float,
        spot_price: float,
        underlying_symbol: str = "SPY",
        target_delta: float = -0.35, # Asymmetric tail hedge
        target_dte_days: int = 21,    # ~3 weeks to expiration
        implied_volatility: float = 0.22,
        max_budget_pct: float = 0.015  # Max 1.5% portfolio cost
    ) -> ProtectivePutRecommendation:
        """
        Calculates optimal protective put strike, expiry, and contracts to hedge portfolio drawdown.

        Args:
            portfolio_equity: Total portfolio equity to protect (e.g. $97,500).
            spot_price: Current market price of underlying (e.g., $550 for SPY).
            underlying_symbol: Ticker of hedging instrument.
            target_delta: Target option delta for cost-efficiency.
            target_dte_days: Target days to expiration.
            implied_volatility: Current IV.
            max_budget_pct: Maximum allowed hedge premium as fraction of portfolio.

        Returns:
            ProtectivePutRecommendation.
        """
        # 1. Search candidate strikes (from 2% OTM to 7% OTM in $1 intervals)
        best_strike = spot_price * 0.96 # Default 4% OTM
        best_greeks = None
        min_delta_diff = float("inf")

        candidate_strikes = np.arange(math.floor(spot_price * 0.90), math.ceil(spot_price * 1.01), 1.0)

        for strike in candidate_strikes:
            greeks = self.black_scholes_greeks(
                spot=spot_price,
                strike=strike,
                expiry_days=target_dte_days,
                volatility=implied_volatility,
                option_type="put"
            )
            delta_diff = abs(greeks.delta - target_delta)
            if delta_diff < min_delta_diff:
                min_delta_diff = delta_diff
                best_strike = strike
                best_greeks = greeks

        # 2. Number of contracts required to cover portfolio notional
        # Each contract covers 100 shares ($S * 100 notional)
        notional_per_contract = spot_price * 100.0
        target_contracts = max(1, math.ceil(portfolio_equity / notional_per_contract))

        # 3. Check budget constraint
        premium_per_share = best_greeks.price
        total_cost = target_contracts * premium_per_share * 100.0
        max_allowed_cost = portfolio_equity * max_budget_pct

        if total_cost > max_allowed_cost and target_contracts > 1:
            target_contracts = max(1, int(max_allowed_cost / (premium_per_share * 100.0)))
            total_cost = target_contracts * premium_per_share * 100.0

        # 4. Formulate Alpaca/OCC Option Symbol: e.g. SPY260918P00550000
        expiry_dt = datetime.now(timezone.utc) + timedelta(days=target_dte_days)
        # Standardize to next Friday
        days_ahead = 4 - expiry_dt.weekday() # Friday is 4
        if days_ahead <= 0:
            days_ahead += 7
        expiry_dt = expiry_dt + timedelta(days=days_ahead)
        actual_dte = (expiry_dt - datetime.now(timezone.utc)).days

        # Format: YYMMDD + P/C + 8-digit price * 1000
        occ_date = expiry_dt.strftime("%y%m%d")
        occ_strike = f"{int(best_strike * 1000):08d}"
        option_symbol = f"{underlying_symbol}{occ_date}P{occ_strike}"

        # 5. Breakeven and coverage
        breakeven = best_strike - premium_per_share
        delta_covered = abs(best_greeks.delta) * target_contracts * 100.0 * spot_price
        max_protection = target_contracts * best_strike * 100.0

        return ProtectivePutRecommendation(
            underlying_symbol=underlying_symbol,
            spot_price=spot_price,
            strike_price=best_strike,
            expiry_days=actual_dte,
            expiry_date=expiry_dt.strftime("%Y-%m-%d"),
            option_symbol=option_symbol,
            option_type="put",
            contract_qty=target_contracts,
            per_contract_premium=premium_per_share,
            total_hedge_cost=total_cost,
            hedge_cost_pct_of_portfolio=total_cost / max(1.0, portfolio_equity),
            portfolio_delta_covered=delta_covered,
            breakeven_price=breakeven,
            max_downside_protection=max_protection,
            greeks=best_greeks
        )
