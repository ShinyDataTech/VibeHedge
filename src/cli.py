"""
Alpaca Portfolio Hedging CLI (alpaca-hedge-cli)
==============================================

Provides command-line access to all autonomous trading agent functions:
- Portfolio status inspection
- FinRL-X 2.5% drawdown risk gate evaluation
- ForecastAgent 24h macro downtrend forecasting
- Vibe-Trading Options Lab Greeks and protective put calculation
- Full autonomous reasoning cycle & live options order execution

Supports structured JSON output (--json) for automation & assistant tools.
"""

import sys
import os
import json
import argparse
import logging
from typing import Any, Dict

# Ensure UTF-8 output on all operating systems / Windows terminals
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd
from dotenv import load_dotenv

from src.execution.alpaca_trader import AlpacaTrader
from src.risk.risk_monitor import FinRLXRiskMonitor
from src.agent.forecast_predictor import ForecastDowntrendPredictor
from src.options.options_lab import OptionsLab
from src.agent.orchestration import HedgingOrchestrator
from training.download_hourly_data import HourlyDataDownloader

load_dotenv()
logger = logging.getLogger("cli")


def print_json(data: Any):
    """Print structured JSON output."""
    print(json.dumps(data, indent=2, default=str))


def cmd_status(args):
    """Query live account status from Alpaca Trading API."""
    trader = AlpacaTrader()
    account = trader.get_account_status()
    positions = trader.get_open_positions()

    data = {
        "status": "success",
        "account": account,
        "positions_count": len(positions),
        "positions": positions
    }

    if args.json:
        print_json(data)
        return

    print("=" * 60)
    print(" 🏛️  ALPACA PAPER PORTFOLIO STATUS")
    print("=" * 60)
    print(f" Account ID:       {account.get('account_id')}")
    print(f" Status:           {account.get('status')}")
    print(f" Equity:           ${account.get('equity', 0.0):,.2f}")
    print(f" Cash Balance:     ${account.get('cash', 0.0):,.2f}")
    print(f" Buying Power:     ${account.get('buying_power', 0.0):,.2f}")
    print(f" Portfolio Value:  ${account.get('portfolio_value', 0.0):,.2f}")
    print("-" * 60)
    print(f" Open Positions ({len(positions)}):")
    if not positions:
        print("  [No open positions currently]")
    else:
        for p in positions:
            print(f"  • {p.get('symbol')}: {p.get('qty')} shares/contracts @ ${p.get('current_price', 0.0):,.2f} "
                  f"(Market Value: ${p.get('market_value', 0.0):,.2f} | Unrealized P&L: ${p.get('unrealized_pl', 0.0):,.2f})")
    print("=" * 60)


def cmd_risk(args):
    """Evaluate FinRL-X 2.5% drawdown risk gate."""
    trader = AlpacaTrader()
    account = trader.get_account_status()
    equity = account.get("equity", args.starting_balance)
    cash = account.get("cash", args.starting_balance)

    monitor = FinRLXRiskMonitor(
        starting_balance=args.starting_balance,
        max_drawdown_threshold=args.max_drawdown
    )
    eval_result = monitor.evaluate_portfolio(current_equity=equity, cash=cash)
    data = {
        "status": "success",
        "risk_gate_evaluation": eval_result.to_dict()
    }

    if args.json:
        print_json(data)
        return

    color = "\033[92m" if eval_result.risk_level == "SAFE" else ("\033[93m" if eval_result.risk_level == "WARNING" else "\033[91m")
    reset = "\033[0m"

    print("=" * 60)
    print(" 🛡️  FINRL-X RISK GATE MONITOR")
    print("=" * 60)
    print(f" Starting Balance:    ${eval_result.starting_balance:,.2f}")
    print(f" Current Equity:      ${eval_result.current_equity:,.2f}")
    print(f" Total Drawdown ($):  ${eval_result.drawdown_dollar:,.2f}")
    print(f" Total Drawdown (%):  {eval_result.drawdown_pct * 100:.2f}%")
    floor = eval_result.starting_balance * (1.0 - eval_result.max_drawdown_limit_pct)
    print(f" Hard Threshold:      {eval_result.max_drawdown_limit_pct * 100:.2f}% (Floor: ${floor:,.2f})")
    print(f" Status:              {color}{eval_result.risk_level}{reset}")
    print(f" Gate Breached:       {'🚨 YES - INITIATE HEDGE' if eval_result.breach_status else '✅ NO - NORMAL OPERATIONS'}")
    print("=" * 60)


def cmd_forecast(args):
    """Run ForecastAgent macro downtrend prediction."""
    downloader = HourlyDataDownloader()
    predictor = ForecastDowntrendPredictor()

    raw_data = downloader.fetch_stock_hourly_bars(symbols=[args.symbol], lookback_years=1, save=False)
    df = raw_data.get(args.symbol)

    if df is None or df.empty:
        cached_file = f"data/historical/{args.symbol}_hourly.csv"
        if os.path.exists(cached_file):
            df = pd.read_csv(cached_file)
        else:
            print(json.dumps({"status": "error", "message": f"Could not retrieve hourly bars for {args.symbol}."}))
            return

    forecast = predictor.predict_downtrend(df)
    data = {
        "status": "success",
        "symbol": args.symbol,
        "forecast": forecast
    }

    if args.json:
        print_json(data)
        return

    print("=" * 60)
    print(f" 🔮 FORECASTAGENT 24H MACRO PREDICTION ({args.symbol})")
    print("=" * 60)
    print(f" Target Symbol:        {args.symbol}")
    print(f" Current Spot Price:   ${forecast.get('current_price', 0.0):.2f}")
    print(f" Bearish Downtrend:    {'🚨 YES' if forecast.get('is_bearish') else '✅ NO'}")
    print(f" Downtrend Probability: {forecast.get('downtrend_probability', 0.0) * 100:.2f}%")
    print(f" Projected 24h Return: {forecast.get('predicted_median_return_pct', 0.0):.2f}%")
    print(f" 10th Percentile (p10): {forecast.get('predicted_p10_return_pct', 0.0):.2f}%")
    print(f" 90th Percentile (p90): {forecast.get('predicted_p90_return_pct', 0.0):.2f}%")
    print(f" Confidence Score:     {forecast.get('confidence_score', 0.0) * 100:.1f}%")
    print("=" * 60)


def cmd_hedge(args):
    """Calculate optimal protective put via Vibe-Trading Options Lab."""
    trader = AlpacaTrader()
    account = trader.get_account_status()
    equity = account.get("equity", 100000.0)

    downloader = HourlyDataDownloader()
    raw_data = downloader.fetch_stock_hourly_bars(symbols=[args.symbol], lookback_years=1, save=False)
    df = raw_data.get(args.symbol)
    spot_price = float(df["close"].iloc[-1]) if df is not None and not df.empty else 550.0

    lab = OptionsLab()
    rec = lab.calculate_optimal_protective_put(
        portfolio_equity=equity,
        spot_price=spot_price,
        underlying_symbol=args.symbol,
        target_delta=args.delta,
        target_dte_days=args.dte,
        implied_volatility=args.iv,
        max_budget_pct=args.max_budget
    )

    data = {
        "status": "success",
        "protective_put_recommendation": rec.to_dict()
    }

    if args.json:
        print_json(data)
        return

    print("=" * 60)
    print(" 📉 VIBE-TRADING OPTIONS LAB HEDGE OPTIMIZER")
    print("=" * 60)
    print(f" Underlying Asset:     {rec.underlying_symbol} @ ${rec.spot_price:.2f}")
    print(f" Target Option Symbol: {rec.option_symbol}")
    print(f" Strike Price:         ${rec.strike_price:.2f}")
    print(f" Expiration Date:      {rec.expiry_date} ({rec.expiry_days} DTE)")
    if rec.greeks:
        print(f" Target Delta:         {rec.greeks.delta:.3f}")
        print(f" Greeks:               Δ={rec.greeks.delta:.3f} | Γ={rec.greeks.gamma:.4f} | Θ={rec.greeks.theta:.3f} | ν={rec.greeks.vega:.3f}")
    print(f" Per Contract Premium: ${rec.per_contract_premium:,.2f}")
    print(f" Contract Quantity:    {rec.contract_qty} contracts")
    print(f" Total Hedge Outlay:   ${rec.total_hedge_cost:,.2f} ({rec.hedge_cost_pct_of_portfolio * 100:.2f}% of portfolio)")
    print(f" Max Downside Shield:  ${rec.max_downside_protection:,.2f}")
    print("=" * 60)


def cmd_cycle(args):
    """Run full autonomous reasoning cycle and optionally execute orders."""
    trader = AlpacaTrader()
    account = trader.get_account_status()
    equity = account.get("equity", 100000.0)
    cash = account.get("cash", 100000.0)

    downloader = HourlyDataDownloader()
    raw_data = downloader.fetch_stock_hourly_bars(symbols=[args.symbol], lookback_years=1, save=False)
    df = raw_data.get(args.symbol)
    if df is None or df.empty:
        cached_file = f"data/historical/{args.symbol}_hourly.csv"
        if os.path.exists(cached_file):
            df = pd.read_csv(cached_file)
        else:
            print(json.dumps({"status": "error", "message": "Failed to load market bars."}))
            return

    orchestrator = HedgingOrchestrator()
    decision = orchestrator.evaluate_and_reason(
        current_equity=equity,
        cash=cash,
        recent_market_bars=df,
        hedge_symbol=args.symbol
    )

    execution_result = None
    if args.execute and decision.action == "EXECUTE_PROTECTIVE_PUT" and decision.hedge_recommendation:
        rec = decision.hedge_recommendation
        execution_result = trader.execute_options_hedge(
            option_symbol=rec["option_symbol"],
            contract_qty=rec["contract_qty"],
            side="buy",
            order_type="market"
        )
        decision.reasoning_trace.append(
            f"Autonomous Execution: Placed order for {rec['contract_qty']}x {rec['option_symbol']}. "
            f"Status: {execution_result.get('status')}."
        )

    data = {
        "status": "success",
        "decision_plan": decision.to_dict(),
        "execution_result": execution_result
    }

    if args.json:
        print_json(data)
        return

    print("=" * 60)
    print(" 🤖 AUTONOMOUS HEDGING REASONING CYCLE")
    print("=" * 60)
    print(f" Action Verdict:       {decision.action}")
    print(f" Confidence:           {decision.confidence * 100:.1f}%")
    print("-" * 60)
    print(" Multi-Step Reasoning Trace:")
    for step in decision.reasoning_trace:
        print(f"  • {step}")
    print("-" * 60)
    if decision.hedge_recommendation:
        rec = decision.hedge_recommendation
        print(f" Recommended Hedge:    Buy {rec['contract_qty']}x {rec['option_symbol']} @ Strike ${rec['strike_price']:.2f}")
    if execution_result:
        print(f" Execution Order ID:   {execution_result.get('order_id')}")
        print(f" Execution Status:     {execution_result.get('status')}")
    print("=" * 60)


def main():
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--json", action="store_true", help="Output results in machine-readable JSON format")

    parser = argparse.ArgumentParser(
        description="Alpaca AI Portfolio Hedging CLI - Autonomous Options Risk & Alpha Engine",
        parents=[common_parser],
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # status
    p_status = subparsers.add_parser("status", parents=[common_parser], help="Show live Alpaca paper portfolio status")
    p_status.set_defaults(func=cmd_status)

    # risk
    p_risk = subparsers.add_parser("risk", parents=[common_parser], help="Evaluate FinRL-X 2.5% drawdown risk gate")
    p_risk.add_argument("--starting-balance", type=float, default=100000.0, help="Initial balance (default: $100k)")
    p_risk.add_argument("--max-drawdown", type=float, default=0.025, help="Drawdown limit (default: 0.025 = 2.5%)")
    p_risk.set_defaults(func=cmd_risk)

    # forecast
    p_forecast = subparsers.add_parser("forecast", parents=[common_parser], help="Run ForecastAgent 24h macro downtrend prediction")
    p_forecast.add_argument("--symbol", type=str, default="SPY", help="Asset ticker symbol (default: SPY)")
    p_forecast.set_defaults(func=cmd_forecast)

    # hedge
    p_hedge = subparsers.add_parser("hedge", parents=[common_parser], help="Calculate optimal protective put and Greeks")
    p_hedge.add_argument("--symbol", type=str, default="SPY", help="Hedge ticker symbol (default: SPY)")
    p_hedge.add_argument("--delta", type=float, default=-0.35, help="Target Delta (default: -0.35)")
    p_hedge.add_argument("--dte", type=int, default=21, help="Target DTE days (default: 21)")
    p_hedge.add_argument("--iv", type=float, default=0.22, help="Implied volatility (default: 0.22)")
    p_hedge.add_argument("--max-budget", type=float, default=0.015, help="Max budget %% of equity (default: 0.015)")
    p_hedge.set_defaults(func=cmd_hedge)

    # cycle
    p_cycle = subparsers.add_parser("cycle", parents=[common_parser], help="Run end-to-end autonomous reasoning cycle")
    p_cycle.add_argument("--symbol", type=str, default="SPY", help="Target symbol (default: SPY)")
    p_cycle.add_argument("--execute", action="store_true", help="Autonomously place hedge order if triggered")
    p_cycle.set_defaults(func=cmd_cycle)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
