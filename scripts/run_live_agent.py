"""
Autonomous Live Monitoring & Hedging Daemon
===========================================

Continuously monitors an Alpaca paper trading account, checks real-time
FinRL-X 2.5% drawdown risk gates ($100k starting capital), queries ForecastAgent
for 24h macro downtrend probabilities, and autonomously executes protective put
orders via Vibe-Trading Options Lab when danger thresholds are breached.
"""

import os
import sys
import time
import argparse
import logging
from datetime import datetime, timezone

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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("live_agent")
load_dotenv()


def run_single_cycle(
    trader: AlpacaTrader,
    downloader: HourlyDataDownloader,
    orchestrator: HedgingOrchestrator,
    symbol: str = "SPY",
    dry_run: bool = False
):
    """Execute a single monitoring, forecasting, and hedging evaluation cycle."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    logger.info(f"--- [START CYCLE] {timestamp} ---")

    # 1. Fetch Account Status
    account = trader.get_account_status()
    current_equity = account.get("equity", 100000.0)
    cash = account.get("cash", 100000.0)
    logger.info(f"Portfolio Status: Equity=${current_equity:,.2f} | Cash=${cash:,.2f} | Status={account.get('status')}")

    # 2. Fetch Latest Market Bars
    raw_data = downloader.fetch_stock_hourly_bars(symbols=[symbol], lookback_years=1, save=False)
    df = raw_data.get(symbol)
    if df is None or df.empty:
        cached_file = f"data/historical/{symbol}_hourly.csv"
        if os.path.exists(cached_file):
            logger.info(f"Using cached historical dataset for {symbol}...")
            df = pd.read_csv(cached_file)
        else:
            logger.error(f"Cannot retrieve market data for {symbol}. Skipping cycle.")
            return

    # 3. Evaluate Risk & Macro Forecast
    plan = orchestrator.evaluate_and_reason(
        current_equity=current_equity,
        cash=cash,
        recent_market_bars=df,
        hedge_symbol=symbol
    )

    logger.info(f"Orchestration Decision: Action={plan.action} (Confidence={plan.confidence * 100:.1f}%)")
    for step in plan.reasoning_trace:
        logger.info(f"  -> {step}")

    # 4. Execute Autonomous Action if Triggered
    if plan.action == "EXECUTE_PROTECTIVE_PUT" and plan.hedge_recommendation:
        rec = plan.hedge_recommendation
        if dry_run:
            logger.info(f"[DRY-RUN] Would submit order: Buy {rec['contract_qty']}x {rec['option_symbol']} (Strike: ${rec['strike_price']:.2f}).")
        else:
            logger.warning(f"🚨 [AUTO-EXECUTION TRIGGERED] Placing order for {rec['contract_qty']}x {rec['option_symbol']}...")
            exec_result = trader.execute_options_hedge(
                option_symbol=rec["option_symbol"],
                contract_qty=rec["contract_qty"],
                side="buy",
                order_type="market"
            )
            logger.info(f"Order Result: ID={exec_result.get('order_id')} | Status={exec_result.get('status')}")
    else:
        logger.info("Portfolio within safety limits. Routine alpha generation active.")

    logger.info(f"--- [END CYCLE] ---\n")


def main():
    parser = argparse.ArgumentParser(description="Alpaca Autonomous Hedging Live Daemon")
    parser.add_argument("--symbol", type=str, default="SPY", help="Benchmark/Hedge symbol (default: SPY)")
    parser.add_argument("--interval", type=int, default=60, help="Monitoring interval in seconds (default: 60)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without submitting live Alpaca orders")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit immediately")
    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("🚀 INITIALIZING ALPACA AUTONOMOUS PORTFOLIO HEDGING DAEMON")
    logger.info(f"Target Symbol:   {args.symbol}")
    logger.info(f"Poll Interval:   {args.interval} seconds")
    logger.info(f"Dry-Run Mode:    {args.dry_run}")
    logger.info("=" * 70)

    trader = AlpacaTrader()
    downloader = HourlyDataDownloader()
    orchestrator = HedgingOrchestrator()

    if args.once:
        run_single_cycle(trader, downloader, orchestrator, symbol=args.symbol, dry_run=args.dry_run)
        return

    try:
        while True:
            run_single_cycle(trader, downloader, orchestrator, symbol=args.symbol, dry_run=args.dry_run)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        logger.info("Daemon stopped by user.")


if __name__ == "__main__":
    main()
