"""
FastMCP Server for Alpaca Autonomous Portfolio Hedging Agent
===========================================================

Exposes structured tools over HTTP/SSE transport for MCP clients
(Claude Desktop, Cursor, Alpaca CLI, and Google Cloud Run).
"""

import os
import json
import logging
from typing import Dict, Any, Optional

import pandas as pd
from fastmcp import FastMCP
from dotenv import load_dotenv

from src.execution.alpaca_trader import AlpacaTrader
from src.risk.risk_monitor import FinRLXRiskMonitor
from src.agent.forecast_predictor import ForecastDowntrendPredictor
from src.options.options_lab import OptionsLab
from src.agent.orchestration import HedgingOrchestrator
from training.download_hourly_data import HourlyDataDownloader

# Load environment configuration
load_dotenv()

# Setup logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("mcp_server")

# Initialize FastMCP application
mcp = FastMCP(
    "alpaca-portfolio-hedging-agent",
)

# Global Module Singletons
trader = AlpacaTrader()
risk_monitor = FinRLXRiskMonitor(
    starting_balance=float(os.getenv("INITIAL_PORTFOLIO_EQUITY", "100000.0")),
    max_drawdown_threshold=float(os.getenv("MAX_DRAWDOWN_THRESHOLD", "0.025"))
)
forecast_predictor = ForecastDowntrendPredictor()
options_lab = OptionsLab()
orchestrator = HedgingOrchestrator(
    risk_monitor=risk_monitor,
    forecast_predictor=forecast_predictor,
    options_lab=options_lab
)
downloader = HourlyDataDownloader()


@mcp.tool()
def get_portfolio_status() -> str:
    """
    Query real-time portfolio status from Alpaca Trading API.
    Returns account equity, cash, buying power, and all open positions.
    """
    account = trader.get_account_status()
    positions = trader.get_open_positions()
    payload = {
        "status": "success",
        "account": account,
        "positions_count": len(positions),
        "positions": positions
    }
    return json.dumps(payload, indent=2)


@mcp.tool()
def check_risk_gates(
    initial_balance: float = 100000.0,
    max_drawdown_pct: float = 0.025
) -> str:
    """
    Evaluate real-time equity against the FinRL-X 2.5% drawdown risk gate.
    
    Args:
        initial_balance: Starting paper trading balance (default: $100,000.00).
        max_drawdown_pct: Hardcoded drawdown threshold (default: 0.025 = 2.5%).
    """
    acct = trader.get_account_status()
    current_equity = acct.get("equity", 100000.0)
    cash = acct.get("cash", 100000.0)

    monitor = FinRLXRiskMonitor(
        starting_balance=initial_balance,
        max_drawdown_threshold=max_drawdown_pct
    )
    eval_result = monitor.evaluate_portfolio(current_equity=current_equity, cash=cash)

    return json.dumps({
        "status": "success",
        "risk_gate_evaluation": eval_result.to_dict()
    }, indent=2)


@mcp.tool()
def predict_macro_forecast(symbol: str = "SPY") -> str:
    """
    Run ForecastAgent inference on hourly market bars to predict macro downtrend probability.
    
    Args:
        symbol: Stock/ETF ticker symbol (default: 'SPY').
    """
    # Fetch latest hourly data
    raw_data = downloader.fetch_stock_hourly_bars(symbols=[symbol], lookback_years=1, save=False)
    df = raw_data.get(symbol)

    if df is None or df.empty:
        # Load cached historical file
        cached_file = f"data/historical/{symbol}_hourly.csv"
        if os.path.exists(cached_file):
            df = pd.read_csv(cached_file)
        else:
            return json.dumps({"status": "error", "message": f"Could not retrieve hourly bars for {symbol}."})

    forecast = forecast_predictor.predict_downtrend(df)
    return json.dumps({
        "status": "success",
        "symbol": symbol,
        "forecast": forecast
    }, indent=2)


@mcp.tool()
def calculate_protective_put(
    symbol: str = "SPY",
    target_delta: float = -0.35,
    dte_days: int = 21,
    implied_volatility: float = 0.22
) -> str:
    """
    Calculate optimal protective put strike, expiry, and Greeks using Vibe-Trading Options Lab.
    
    Args:
        symbol: Underlying hedge symbol (default: 'SPY').
        target_delta: Target put delta for asymmetric tail protection (default: -0.35).
        dte_days: Target days to expiration (default: 21).
        implied_volatility: Annualized IV (default: 0.22).
    """
    acct = trader.get_account_status()
    portfolio_equity = acct.get("equity", 100000.0)

    # Estimate current spot
    raw_data = downloader.fetch_stock_hourly_bars(symbols=[symbol], lookback_years=1, save=False)
    df = raw_data.get(symbol)
    spot_price = float(df["close"].iloc[-1]) if df is not None and not df.empty else 550.0

    hedge_rec = options_lab.calculate_optimal_protective_put(
        portfolio_equity=portfolio_equity,
        spot_price=spot_price,
        underlying_symbol=symbol,
        target_delta=target_delta,
        target_dte_days=dte_days,
        implied_volatility=implied_volatility
    )

    return json.dumps({
        "status": "success",
        "protective_put_recommendation": hedge_rec.to_dict()
    }, indent=2)


@mcp.tool()
def run_autonomous_hedging_cycle(
    symbol: str = "SPY",
    auto_execute: bool = True
) -> str:
    """
    Execute the end-to-end multi-step reasoning cycle:
    1. Inspect FinRL-X risk gates against $100k balance.
    2. Query ForecastAgent for 24h macro downtrend probability.
    3. If 2.5% drawdown breached and trend is bearish -> calculate Options Lab hedge.
    4. If auto_execute is True, autonomously submit the protective put order to Alpaca.
    
    Args:
        symbol: Hedging target asset (default: 'SPY').
        auto_execute: Whether to automatically place order if risk gate is breached (default: True).
    """
    acct = trader.get_account_status()
    current_equity = acct.get("equity", 100000.0)
    cash = acct.get("cash", 100000.0)

    raw_data = downloader.fetch_stock_hourly_bars(symbols=[symbol], lookback_years=1, save=False)
    df = raw_data.get(symbol)
    if df is None or df.empty:
        cached_file = f"data/historical/{symbol}_hourly.csv"
        if os.path.exists(cached_file):
            df = pd.read_csv(cached_file)
        else:
            return json.dumps({"status": "error", "message": "Failed to load market bars."})

    # Run multi-step reasoning
    decision_plan = orchestrator.evaluate_and_reason(
        current_equity=current_equity,
        cash=cash,
        recent_market_bars=df,
        hedge_symbol=symbol
    )

    execution_result = None
    if auto_execute and decision_plan.action == "EXECUTE_PROTECTIVE_PUT" and decision_plan.hedge_recommendation:
        rec = decision_plan.hedge_recommendation
        execution_result = trader.execute_options_hedge(
            option_symbol=rec["option_symbol"],
            contract_qty=rec["contract_qty"],
            side="buy",
            order_type="market"
        )
        decision_plan.reasoning_trace.append(
            f"Autonomous Execution: Placed order for {rec['contract_qty']}x {rec['option_symbol']}. Status: {execution_result.get('status')}."
        )

    return json.dumps({
        "status": "success",
        "decision_plan": decision_plan.to_dict(),
        "execution_result": execution_result
    }, indent=2)


@mcp.tool()
def execute_protective_put_order(
    option_symbol: str,
    contract_qty: int = 1,
    limit_price: Optional[float] = None
) -> str:
    """
    Directly execute a protective put option purchase via Alpaca Trading API.
    
    Args:
        option_symbol: OCC formatted option symbol (e.g. 'SPY260918P00550000').
        contract_qty: Number of contracts (default: 1).
        limit_price: Optional limit price per share.
    """
    order_type = "limit" if limit_price is not None else "market"
    result = trader.execute_options_hedge(
        option_symbol=option_symbol,
        contract_qty=contract_qty,
        side="buy",
        order_type=order_type,
        limit_price=limit_price
    )
    return json.dumps(result, indent=2)


def start_server():
    """Start FastMCP server on configured port."""
    port = int(os.getenv("PORT", "8080"))
    host = os.getenv("HOST", "0.0.0.0")
    transport = os.getenv("MCP_TRANSPORT", "sse")

    logger.info(f"Starting FastMCP Server '{mcp.name}' on {host}:{port} via transport '{transport}'...")
    mcp.run(transport=transport, host=host, port=port)


if __name__ == "__main__":
    start_server()
