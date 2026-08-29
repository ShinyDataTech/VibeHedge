"""
FinRL-X Portfolio Risk Monitoring Module
=======================================

Tracks real-time portfolio equity, peak valuation, and enforces
the mandatory 2.5% drawdown risk gate against the $100,000 Alpaca paper balance.
"""

import os
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger("risk_monitor")


@dataclass
class RiskGateEvaluation:
    """Structured evaluation of portfolio risk gates."""
    starting_balance: float
    current_equity: float
    peak_equity: float
    cash: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    drawdown_pct: float
    drawdown_dollar: float
    max_drawdown_limit_pct: float
    breach_status: bool
    risk_level: str  # "SAFE", "WARNING", "BREACHED"
    reason: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "starting_balance": self.starting_balance,
            "current_equity": round(self.current_equity, 2),
            "peak_equity": round(self.peak_equity, 2),
            "cash": round(self.cash, 2),
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "unrealized_pnl_pct": round(self.unrealized_pnl_pct * 100, 2),
            "drawdown_pct": round(self.drawdown_pct * 100, 2),
            "drawdown_dollar": round(self.drawdown_dollar, 2),
            "max_drawdown_limit_pct": round(self.max_drawdown_limit_pct * 100, 2),
            "breach_status": self.breach_status,
            "risk_level": self.risk_level,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


class FinRLXRiskMonitor:
    """Real-time portfolio risk and drawdown gate monitor."""

    def __init__(
        self,
        starting_balance: float = 100000.0,
        max_drawdown_threshold: float = 0.025, # Hardcoded 2.5% drawdown limit
        warning_drawdown_threshold: float = 0.018 # Warning at 1.8%
    ):
        self.starting_balance = starting_balance
        self.max_drawdown_threshold = max_drawdown_threshold
        self.warning_drawdown_threshold = warning_drawdown_threshold
        self.peak_equity = starting_balance
        self.history: List[Dict[str, Any]] = []

    def update_peak_equity(self, current_equity: float):
        """Update high watermark equity."""
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

    def evaluate_portfolio(
        self,
        current_equity: float,
        cash: float = 100000.0,
        positions_value: float = 0.0
    ) -> RiskGateEvaluation:
        """
        Evaluate real-time equity against the 2.5% hackathon starting balance gate.

        Args:
            current_equity: Current total portfolio equity (cash + open positions).
            cash: Unallocated cash in account.
            positions_value: Market value of open stock & option positions.

        Returns:
            RiskGateEvaluation object with breach status.
        """
        self.update_peak_equity(current_equity)

        # Drawdown calculation against $100,000 starting balance
        dollar_drawdown_from_start = self.starting_balance - current_equity
        drawdown_pct_from_start = max(0.0, dollar_drawdown_from_start / self.starting_balance)

        # Drawdown from peak
        peak_drawdown_pct = max(0.0, (self.peak_equity - current_equity) / max(1.0, self.peak_equity))

        # PnL against start
        unrealized_pnl = current_equity - self.starting_balance
        unrealized_pnl_pct = unrealized_pnl / self.starting_balance

        # Evaluate risk gates
        is_breached = drawdown_pct_from_start >= self.max_drawdown_threshold
        is_warning = drawdown_pct_from_start >= self.warning_drawdown_threshold

        if is_breached:
            risk_level = "BREACHED"
            reason = (
                f"CRITICAL RISK GATE BREACHED: Portfolio drawdown ({drawdown_pct_from_start * 100:.2f}%) "
                f"exceeds hardcoded 2.5% limit (${self.starting_balance * (1 - self.max_drawdown_threshold):,.2f} threshold). "
                f"Automated hedge protocol initiated."
            )
            logger.warning(reason)
        elif is_warning:
            risk_level = "WARNING"
            reason = (
                f"RISK WARNING: Portfolio drawdown ({drawdown_pct_from_start * 100:.2f}%) "
                f"is approaching the 2.5% threshold. ForecastAgent on alert."
            )
            logger.info(reason)
        else:
            risk_level = "SAFE"
            reason = f"Portfolio within safe parameters. Drawdown: {drawdown_pct_from_start * 100:.2f}%."

        eval_result = RiskGateEvaluation(
            starting_balance=self.starting_balance,
            current_equity=current_equity,
            peak_equity=self.peak_equity,
            cash=cash,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_pct=unrealized_pnl_pct,
            drawdown_pct=drawdown_pct_from_start,
            drawdown_dollar=dollar_drawdown_from_start,
            max_drawdown_limit_pct=self.max_drawdown_threshold,
            breach_status=is_breached,
            risk_level=risk_level,
            reason=reason
        )

        self.history.append(eval_result.to_dict())
        return eval_result


def create_risk_monitor_from_env() -> FinRLXRiskMonitor:
    """Instantiate risk monitor using environment parameters."""
    starting_bal = float(os.getenv("INITIAL_PORTFOLIO_EQUITY", "100000.0"))
    threshold = float(os.getenv("MAX_DRAWDOWN_THRESHOLD", "0.025"))
    return FinRLXRiskMonitor(starting_balance=starting_bal, max_drawdown_threshold=threshold)
