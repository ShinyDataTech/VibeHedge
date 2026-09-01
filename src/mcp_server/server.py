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
from starlette.responses import HTMLResponse, JSONResponse, Response
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


# ==============================================================================
# HTTP Custom Routes (Web Landing Dashboard, Health Check, Favicon)
# ==============================================================================

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Instant HTTP 200 healthcheck for Google Cloud Run startup & liveness probes."""
    return JSONResponse({
        "status": "healthy",
        "service": "alpaca-hedging-agent",
        "version": "1.0.0",
        "transport": os.getenv("MCP_TRANSPORT", "sse"),
        "account_id": "ea533232-e5c5-4eee-87c9-b64cdf4c0c27",
        "starting_balance": 100000.0,
        "max_drawdown_gate": "2.5% ($97,500.00 floor)"
    }, status_code=200)


@mcp.custom_route("/favicon.ico", methods=["GET"])
async def favicon_handler(request):
    """Handle browser favicon request to eliminate 404 logs."""
    return Response(status_code=204)


@mcp.custom_route("/", methods=["GET"])
async def web_landing_dashboard(request):
    """Rich responsive HTML landing page for browser visitors and hackathon judges."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Alpaca AI Portfolio Hedging System | FastMCP Server</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0a0f1d;
            --bg-card: rgba(16, 24, 48, 0.85);
            --border-glow: rgba(0, 242, 254, 0.25);
            --cyan-glow: #00f2fe;
            --blue-glow: #4facfe;
            --emerald: #10b981;
            --amber: #f59e0b;
            --rose: #f43f5e;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: var(--bg-primary);
            background-image: radial-gradient(circle at top right, rgba(79, 172, 254, 0.12), transparent 40%),
                              radial-gradient(circle at bottom left, rgba(0, 242, 254, 0.08), transparent 40%);
            color: var(--text-primary);
            font-family: 'Inter', sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding: 2rem 1rem;
        }
        .container {
            max-width: 900px;
            width: 100%;
        }
        .header {
            text-align: center;
            margin-bottom: 2rem;
        }
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: rgba(16, 185, 129, 0.15);
            color: var(--emerald);
            border: 1px solid rgba(16, 185, 129, 0.3);
            padding: 0.35rem 1rem;
            border-radius: 9999px;
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 1rem;
        }
        .pulse-dot {
            width: 8px;
            height: 8px;
            background: var(--emerald);
            border-radius: 50%;
            box-shadow: 0 0 10px var(--emerald);
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(1.3); }
        }
        h1 {
            font-size: 2.25rem;
            font-weight: 800;
            background: linear-gradient(135deg, #ffffff 0%, var(--cyan-glow) 50%, var(--blue-glow) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.75rem;
            letter-spacing: -0.02em;
        }
        p.subtitle {
            color: var(--text-secondary);
            font-size: 1.05rem;
            line-height: 1.6;
        }
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-glow);
            border-radius: 16px;
            padding: 1.75rem;
            backdrop-filter: blur(12px);
            margin-bottom: 1.5rem;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        }
        .grid-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 1.5rem;
        }
        .stat-box {
            background: rgba(10, 15, 29, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 1.25rem;
            text-align: center;
        }
        .stat-label {
            color: var(--text-secondary);
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.35rem;
        }
        .stat-value {
            font-size: 1.35rem;
            font-weight: 700;
            color: #ffffff;
            font-family: 'JetBrains Mono', monospace;
        }
        .stat-sub {
            font-size: 0.75rem;
            color: var(--cyan-glow);
            margin-top: 0.25rem;
        }
        h2 {
            font-size: 1.25rem;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .tools-list {
            display: grid;
            gap: 0.75rem;
        }
        .tool-item {
            background: rgba(10, 15, 29, 0.5);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 10px;
            padding: 0.85rem 1.15rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.9rem;
        }
        .tool-name { color: var(--cyan-glow); font-weight: 600; }
        .tool-desc { color: var(--text-secondary); font-family: 'Inter', sans-serif; font-size: 0.85rem; }
        .endpoint-banner {
            background: linear-gradient(135deg, rgba(0, 242, 254, 0.1), rgba(79, 172, 254, 0.1));
            border: 1px solid rgba(0, 242, 254, 0.3);
            border-radius: 12px;
            padding: 1.25rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 1rem;
        }
        .endpoint-title { font-size: 0.85rem; color: var(--text-secondary); text-transform: uppercase; }
        .endpoint-url { font-family: 'JetBrains Mono', monospace; color: #ffffff; font-weight: 600; font-size: 0.95rem; margin-top: 0.2rem; }
        .btn-link {
            background: linear-gradient(135deg, var(--cyan-glow), var(--blue-glow));
            color: #0a0f1d;
            text-decoration: none;
            padding: 0.55rem 1.25rem;
            border-radius: 8px;
            font-weight: 700;
            font-size: 0.85rem;
            transition: opacity 0.2s;
        }
        .btn-link:hover { opacity: 0.9; }
        .footer {
            text-align: center;
            color: var(--text-secondary);
            font-size: 0.85rem;
            margin-top: 1.5rem;
        }
        .footer a { color: var(--cyan-glow); text-decoration: none; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="badge">
                <span class="pulse-dot"></span>
                <span>FastMCP Agent Active &bull; Google Cloud Run 24/7</span>
            </div>
            <h1>Alpaca AI Portfolio Hedging System</h1>
            <p class="subtitle">Autonomous Options Alpha & Dynamic Tail-Risk Protection Agent<br>Built for the <strong>Alpaca AI Trading Agents Hackathon</strong></p>
        </div>

        <div class="grid-stats">
            <div class="stat-box">
                <div class="stat-label">Paper Account Starting Capital</div>
                <div class="stat-value">$100,000.00</div>
                <div class="stat-sub">Alpaca Dedicated Account</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">FinRL-X Drawdown Gate</div>
                <div class="stat-value">2.50%</div>
                <div class="stat-sub">$97,500.00 Hard Floor</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">AI Forecasting Core</div>
                <div class="stat-value">ForecastAgent</div>
                <div class="stat-sub">9-ETF Macro Panel &bull; 42 Feat.</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Quantitative Options Lab</div>
                <div class="stat-value">-0.35 &Delta; Put</div>
                <div class="stat-sub">Analytical Greeks &bull; 1.5% Cap</div>
            </div>
        </div>

        <div class="card">
            <h2>🛠️ Exposed FastMCP Tools (SSE Protocol)</h2>
            <div class="tools-list">
                <div class="tool-item">
                    <span class="tool-name">get_portfolio_status()</span>
                    <span class="tool-desc">Real-time equity, cash, buying power, and open positions</span>
                </div>
                <div class="tool-item">
                    <span class="tool-name">check_risk_gates(balance, max_dd)</span>
                    <span class="tool-desc">Audits 2.5% drawdown gate ($97.5k floor)</span>
                </div>
                <div class="tool-item">
                    <span class="tool-name">predict_macro_forecast(symbol)</span>
                    <span class="tool-desc">ForecastAgent 24h macro downtrend probability</span>
                </div>
                <div class="tool-item">
                    <span class="tool-name">calculate_protective_put(...)</span>
                    <span class="tool-desc">Options Lab Greeks engine & -0.35 Delta strike selection</span>
                </div>
                <div class="tool-item">
                    <span class="tool-name">run_autonomous_hedging_cycle(...)</span>
                    <span class="tool-desc">End-to-end multi-step reasoning & auto order execution</span>
                </div>
            </div>

            <div class="endpoint-banner">
                <div>
                    <div class="endpoint-title">FastMCP SSE Stream Connection</div>
                    <div class="endpoint-url">/sse</div>
                </div>
                <a href="/sse" class="btn-link">Connect SSE</a>
            </div>
        </div>

        <div class="footer">
            <p>GitHub Repository: <a href="https://github.com/ShinyDataTech/VibeHedge" target="_blank">ShinyDataTech/VibeHedge</a> &bull; Powered by Alpaca, FastMCP & Featherless AI</p>
        </div>
    </div>
</body>
</html>
"""
    return HTMLResponse(content=html_content, status_code=200)


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
