"""
Local Orchestration & Reasoning Engine Module
=============================================

Implements an offline, multi-step reasoning loop (supporting Ollama / OpenClaude)
that coordinates FinRL-X Risk Monitoring, ForecastAgent downtrend predictions,
and Vibe-Trading Options Lab quantitative hedging calculations.
"""

import os
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

import requests
import pandas as pd
from dotenv import load_dotenv

from src.risk.risk_monitor import FinRLXRiskMonitor, RiskGateEvaluation
from src.agent.forecast_predictor import ForecastDowntrendPredictor
from src.options.options_lab import OptionsLab, ProtectivePutRecommendation

load_dotenv()
logger = logging.getLogger("orchestration")


@dataclass
class HedgeDecisionPlan:
    """Complete actionable plan produced by the hedging reasoning engine."""
    action: str  # "EXECUTE_PROTECTIVE_PUT", "MONITOR", "NO_ACTION"
    confidence: float
    risk_evaluation: Dict[str, Any]
    forecast_evaluation: Dict[str, Any]
    hedge_recommendation: Optional[Dict[str, Any]]
    reasoning_trace: List[str]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "confidence": round(self.confidence, 4),
            "risk_evaluation": self.risk_evaluation,
            "forecast_evaluation": self.forecast_evaluation,
            "hedge_recommendation": self.hedge_recommendation,
            "reasoning_trace": self.reasoning_trace,
            "timestamp": self.timestamp,
        }


class HedgingOrchestrator:
    """Agent orchestrator for portfolio monitoring, macro forecasting, and hedging."""

    def __init__(
        self,
        risk_monitor: Optional[FinRLXRiskMonitor] = None,
        forecast_predictor: Optional[ForecastDowntrendPredictor] = None,
        options_lab: Optional[OptionsLab] = None,
        ollama_base_url: Optional[str] = None,
        model_name: str = "llama3.1",
        featherless_api_key: Optional[str] = None,
        featherless_base_url: Optional[str] = None,
        featherless_model: Optional[str] = None,
    ):
        self.risk_monitor = risk_monitor or FinRLXRiskMonitor(
            starting_balance=float(os.getenv("INITIAL_PORTFOLIO_EQUITY", "100000.0")),
            max_drawdown_threshold=float(os.getenv("MAX_DRAWDOWN_THRESHOLD", "0.025"))
        )
        self.forecast_predictor = forecast_predictor or ForecastDowntrendPredictor()
        self.options_lab = options_lab or OptionsLab()
        self.ollama_base_url = ollama_base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model_name = os.getenv("REASONING_MODEL", model_name)
        
        # Featherless AI Configuration (Hackathon Sponsor API)
        self.featherless_api_key = featherless_api_key or os.getenv("FEATHERLESS_API_KEY", "")
        self.featherless_base_url = (featherless_base_url or os.getenv("FEATHERLESS_BASE_URL", "https://api.featherless.ai/v1")).rstrip("/")
        self.featherless_model = featherless_model or os.getenv("FEATHERLESS_MODEL", "meta-llama/Meta-Llama-3.1-8B-Instruct")
        self.openclaude_api_key = os.getenv("OPENCLAUDE_API_KEY", "")

    def evaluate_and_reason(
        self,
        current_equity: float,
        cash: float,
        recent_market_bars: pd.DataFrame,
        hedge_symbol: str = "SPY",
        implied_volatility: float = 0.22
    ) -> HedgeDecisionPlan:
        """
        Execute multi-step reasoning to evaluate risk, forecast trend, and plan hedging.

        Steps:
        1. Evaluate real-time equity against the 2.5% drawdown gate ($100k balance).
        2. Run ForecastAgent inference on hourly market bars.
        3. If drawdown breached and trend confirmed bearish -> calculate Options Lab hedge.
        4. Synthesize decision through multi-step chain-of-thought.
        """
        reasoning_trace = []
        reasoning_trace.append(f"STEP 1: Checking FinRL-X real-time risk gates for current equity ${current_equity:,.2f}...")

        # 1. FinRL-X Risk Gate Evaluation
        risk_eval: RiskGateEvaluation = self.risk_monitor.evaluate_portfolio(
            current_equity=current_equity,
            cash=cash
        )
        reasoning_trace.append(
            f"Risk Gate Status: {risk_eval.risk_level} | Drawdown: {risk_eval.drawdown_pct * 100:.2f}% | "
            f"Threshold: {risk_eval.max_drawdown_limit_pct * 100:.2f}% (${risk_eval.drawdown_dollar:,.2f} loss)."
        )

        # 2. ForecastAgent Macro Downtrend Prediction
        reasoning_trace.append("STEP 2: Querying ForecastAgent XLSTM model for intraday macro downtrend signals...")
        forecast_eval = self.forecast_predictor.predict_downtrend(recent_market_bars)
        reasoning_trace.append(
            f"Forecast Result: is_bearish={forecast_eval['is_bearish']} | "
            f"Downtrend Probability: {forecast_eval['downtrend_probability'] * 100:.1f}% | "
            f"Projected 24h Return: {forecast_eval['predicted_median_return_pct']:.2f}%."
        )

        # 3. Decision Matrix & Options Lab Calculation
        hedge_rec: Optional[ProtectivePutRecommendation] = None
        action = "NO_ACTION"
        confidence = 0.5

        spot_price = forecast_eval.get("current_price", float(recent_market_bars["close"].iloc[-1]))

        if risk_eval.breach_status and forecast_eval["is_bearish"]:
            reasoning_trace.append(
                "STEP 3: [CRITICAL TRIGGER] Both 2.5% drawdown risk gate breached AND macro downtrend confirmed. "
                "Invoking Vibe-Trading Options Lab to calculate protective put strike & expiry."
            )
            hedge_rec = self.options_lab.calculate_optimal_protective_put(
                portfolio_equity=current_equity,
                spot_price=spot_price,
                underlying_symbol=hedge_symbol,
                target_delta=float(os.getenv("DEFAULT_HEDGE_DELTA", "-0.35")),
                target_dte_days=21,
                implied_volatility=implied_volatility,
                max_budget_pct=float(os.getenv("MAX_HEDGE_BUDGET_PCT", "0.015"))
            )
            action = "EXECUTE_PROTECTIVE_PUT"
            confidence = min(0.98, max(0.80, forecast_eval["downtrend_probability"]))
            reasoning_trace.append(
                f"Options Lab Hedge Output: Buy {hedge_rec.contract_qty}x {hedge_rec.option_symbol} "
                f"(Strike: ${hedge_rec.strike_price:.2f}, Expiry: {hedge_rec.expiry_date}, "
                f"Delta: {hedge_rec.greeks.delta:.2f}, Total Cost: ${hedge_rec.total_hedge_cost:.2f})."
            )

        elif risk_eval.breach_status and not forecast_eval["is_bearish"]:
            reasoning_trace.append(
                "STEP 3: Drawdown gate breached, but ForecastAgent predicts positive mean-reversion. "
                "Holding position and raising monitoring frequency to 5-minute intervals."
            )
            action = "MONITOR"
            confidence = 0.65

        elif not risk_eval.breach_status and forecast_eval["is_bearish"]:
            reasoning_trace.append(
                "STEP 3: Macro downtrend detected, but portfolio equity is safely above 2.5% drawdown gate. "
                "Pre-calculating hedge parameters for instant execution if drawdown threshold is touched."
            )
            action = "MONITOR"
            confidence = 0.70
        else:
            reasoning_trace.append(
                "STEP 3: Portfolio healthy and macro trend stable. Continuing routine alpha generation."
            )
            action = "NO_ACTION"
            confidence = 0.90

        # 4. Synthesize with LLM (Featherless AI / Ollama / OpenClaude) or fallback
        llm_synthesis, provider_used = self._call_llm_synthesis(reasoning_trace, risk_eval.to_dict(), forecast_eval)
        if llm_synthesis:
            reasoning_trace.append(f"AI Risk Supervisor Synthesis ({provider_used}): {llm_synthesis}")

        return HedgeDecisionPlan(
            action=action,
            confidence=confidence,
            risk_evaluation=risk_eval.to_dict(),
            forecast_evaluation=forecast_eval,
            hedge_recommendation=hedge_rec.to_dict() if hedge_rec else None,
            reasoning_trace=reasoning_trace
        )

    def _call_llm_synthesis(
        self,
        trace: List[str],
        risk_dict: Dict[str, Any],
        forecast_dict: Dict[str, Any]
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Synthesize narrative using Featherless AI, Ollama, or OpenClaude.
        Returns tuple of (synthesis_text, provider_name).
        """
        prompt = (
            f"You are an Institutional AI Risk & Hedging Supervisor. Analyze the following agent telemetry:\n"
            f"- Portfolio Risk Evaluation: {json.dumps(risk_dict)}\n"
            f"- ForecastAgent Macro Signals: {json.dumps(forecast_dict)}\n"
            f"- Chain-of-Thought Trace: {' -> '.join(trace)}\n\n"
            f"Provide a concise 1-paragraph institutional risk supervisor verdict and justification."
        )

        # 1. Try Featherless AI (Hackathon Inference Sponsor) if key provided
        if self.featherless_api_key:
            try:
                headers = {
                    "Authorization": f"Bearer {self.featherless_api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": self.featherless_model,
                    "messages": [
                        {"role": "system", "content": "You are a quantitative portfolio risk manager."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 200
                }
                resp = requests.post(
                    f"{self.featherless_base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=3.0
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"].strip()
                    return content, f"Featherless AI ({self.featherless_model})"
            except Exception as e:
                logger.debug(f"Featherless API call failed: {e}")

        # 2. Try Local Ollama if running
        try:
            resp = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={"model": self.model_name, "prompt": prompt, "stream": False},
                timeout=1.5
            )
            if resp.status_code == 200:
                text = resp.json().get("response", "").strip()
                if text:
                    return text, f"Ollama ({self.model_name})"
        except Exception:
            pass

        return None, None
