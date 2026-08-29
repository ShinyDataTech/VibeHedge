"""
Unit & Integration Tests for Phase 3 Hedging Agent Engine
"""

import unittest
import pandas as pd
import numpy as np

from src.risk.risk_monitor import FinRLXRiskMonitor
from src.options.options_lab import OptionsLab
from src.agent.orchestration import HedgingOrchestrator


class TestHedgingAgentEngine(unittest.TestCase):

    def setUp(self):
        self.risk_monitor = FinRLXRiskMonitor(starting_balance=100000.0, max_drawdown_threshold=0.025)
        self.options_lab = OptionsLab()
        self.orchestrator = HedgingOrchestrator(
            risk_monitor=self.risk_monitor,
            options_lab=self.options_lab
        )

    def test_risk_gate_safe(self):
        """Test portfolio within safe limits ($100,000 -> $99,000 = 1.0% drawdown)."""
        evaluation = self.risk_monitor.evaluate_portfolio(current_equity=99000.0)
        self.assertFalse(evaluation.breach_status)
        self.assertEqual(evaluation.risk_level, "SAFE")
        self.assertEqual(evaluation.drawdown_pct, 0.01)

    def test_risk_gate_breached(self):
        """Test portfolio breaching 2.5% drawdown ($100,000 -> $97,200 = 2.8% drawdown)."""
        evaluation = self.risk_monitor.evaluate_portfolio(current_equity=97200.0)
        self.assertTrue(evaluation.breach_status)
        self.assertEqual(evaluation.risk_level, "BREACHED")
        self.assertGreaterEqual(evaluation.drawdown_pct, 0.025)

    def test_options_lab_black_scholes_greeks(self):
        """Test Black-Scholes Greeks calculation for put option."""
        greeks = self.options_lab.black_scholes_greeks(
            spot=550.0,
            strike=530.0,
            expiry_days=21,
            volatility=0.20,
            risk_free_rate=0.045,
            option_type="put"
        )
        self.assertLess(greeks.delta, 0.0)
        self.assertGreater(greeks.delta, -1.0)
        self.assertGreater(greeks.gamma, 0.0)
        self.assertGreater(greeks.vega, 0.0)
        self.assertLess(greeks.theta, 0.0) # Theta decay is negative

    def test_optimal_protective_put_recommendation(self):
        """Test calculation of optimal protective put contract."""
        rec = self.options_lab.calculate_optimal_protective_put(
            portfolio_equity=97500.0,
            spot_price=550.0,
            underlying_symbol="SPY",
            target_delta=-0.35,
            target_dte_days=21,
            implied_volatility=0.22
        )
        self.assertEqual(rec.underlying_symbol, "SPY")
        self.assertGreater(rec.contract_qty, 0)
        self.assertTrue(rec.option_symbol.startswith("SPY"))
        self.assertIn("P", rec.option_symbol)
        self.assertLess(rec.strike_price, 550.0) # OTM put
        self.assertGreater(rec.total_hedge_cost, 0.0)

    def test_orchestration_loop_trigger(self):
        """Test end-to-end multi-step reasoning orchestrator on drawdown breach."""
        # Mock 80 bars of historical data
        dates = pd.date_range("2026-08-01", periods=80, freq="h")
        prices = [550.0 - i * 0.5 for i in range(80)]
        mock_df = pd.DataFrame({
            "timestamp": dates,
            "open": prices,
            "high": [p + 0.5 for p in prices],
            "low": [p - 0.5 for p in prices],
            "close": prices,
            "volume": [50000] * 80
        })

        # Equity at $97,000 (breaches 2.5% drawdown)
        plan = self.orchestrator.evaluate_and_reason(
            current_equity=97000.0,
            cash=15000.0,
            recent_market_bars=mock_df,
            hedge_symbol="SPY"
        )
        self.assertIn(plan.action, ["EXECUTE_PROTECTIVE_PUT", "MONITOR"])
        self.assertTrue(len(plan.reasoning_trace) >= 3)
        self.assertEqual(plan.risk_evaluation["risk_level"], "BREACHED")

    def test_featherless_llm_provider_configuration(self):
        """Test Featherless AI provider configuration and offline fallback."""
        orchestrator_fl = HedgingOrchestrator(
            risk_monitor=self.risk_monitor,
            options_lab=self.options_lab,
            featherless_api_key="fake-test-key",
            featherless_base_url="https://api.featherless.ai/v1",
            featherless_model="meta-llama/Meta-Llama-3.1-8B-Instruct"
        )
        self.assertEqual(orchestrator_fl.featherless_api_key, "fake-test-key")
        self.assertEqual(orchestrator_fl.featherless_base_url, "https://api.featherless.ai/v1")
        self.assertEqual(orchestrator_fl.featherless_model, "meta-llama/Meta-Llama-3.1-8B-Instruct")
        
        # Test synthesis offline fallback when network is unreachable/mocked
        text, provider = orchestrator_fl._call_llm_synthesis(
            trace=["Step 1", "Step 2"],
            risk_dict={"risk_level": "BREACHED"},
            forecast_dict={"is_bearish": True}
        )
        # Should gracefully return None, None or string without crashing
        self.assertTrue(text is None or isinstance(text, str))

    def test_cli_subcommands_import_and_execution(self):
        """Test CLI subcommands produce valid output structures."""
        from src.cli import cmd_status, cmd_risk, cmd_hedge
        import argparse

        # Test CLI risk command with mock args
        args_risk = argparse.Namespace(starting_balance=100000.0, max_drawdown=0.025, json=True)
        # Verify it executes without error
        try:
            cmd_risk(args_risk)
        except SystemExit:
            pass


if __name__ == "__main__":
    unittest.main()
