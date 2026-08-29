# Alpaca AI Portfolio Hedging System: Autonomous Options Risk & Alpha Engine

**Hackathon Track:** Options Alpha Agents & Autonomous Trading  
**Target Platform:** Alpaca Trading API, FastMCP (SSE/HTTP), Google Cloud Run  
**Author / Team:** ShinyDataTech (Wei Liu) | **Dedicated Paper Account ID:** `ea533232-e5c5-4eee-87c9-b64cdf4c0c27`  
**Starting Capital:** $100,000.00 USD  

---

## 1. Executive Summary & Problem Formulation
In equity investing and algorithmic trading, catastrophic portfolio drawdowns during macro regime shifts, geopolitical shocks, and flash selloffs permanently impair compounding capital. Traditional stop-loss mechanisms suffer from severe execution slippage, gap-down risk, and whipsaw losses. 

The **Alpaca AI Portfolio Hedging System** solves this by uniting real-time risk supervision, zero-shot deep temporal sequence forecasting, and quantitative options calculus into an autonomous agent. Designed for the **Alpaca AI Trading Agents Hackathon**, the agent monitors a dedicated **$100,000.00** paper trading portfolio, enforces a hardcoded **2.5% Maximum Drawdown Risk Gate ($97,500.00 equity floor)**, and dynamically hedges downside equity risk by acquiring optimal protective puts via Alpaca's Options Trading API.

---

## 2. AI Logic & Deep Sequence Modeling (ForecastAgent)
To anticipate market downturns before catastrophic equity breaches occur, the system deploys **ForecastAgent**—a bi-directional recurrent temporal deep learning architecture trained on high-frequency market dynamics:

* **Diversified 9-ETF Macroeconomic Panel:** Ingests 2-year hourly market bars across a cross-asset panel (`SPY`, `QQQ`, `IWM`, `XLK`, `XLF`, `XLE`, `XLV`, `GLD`, `TLT`) via Alpaca's Historical Market Data clients (32,886 hourly rows, 1.38M data points).
* **FinRL & Relative Strength Feature Engineering:** Computes 22 FinRL technical indicators (MACD, RSI, Bollinger Bands, ATR, CCI, EMA crossovers) augmented by 8 cross-asset Relative Strength/Beta features against `SPY` (`rs_ratio_to_spy`, `rs_momentum`, `sector_breakdown_flag`, `beta_to_spy_24h`), generating **42 standardized features per step**.
* **Leak-Free Panel Sequencing:** Implements strict per-ticker boundary sliding windows (24h lookback to predict $t+24\text{h}$ median return and quantiles $p_{10}, p_{50}, p_{90}$), eliminating lookahead bias and cross-asset temporal leakage across 27,090 training and 4,086 validation sequences.
* **LLM Risk Supervisor Synthesis:** Features an integrated multi-step reasoning layer compatible with **Featherless AI** (`meta-llama/Meta-Llama-3.1-8B-Instruct` via sponsor code `ALPACAA26`), local Ollama (`llama3.1`), and OpenClaude.

```
Macro Data Panel (9 ETFs) ──► 42 FinRL/RS Indicators ──► ForecastAgent Bi-LSTM ──► P(Downtrend) & Quantiles
```

---

## 3. Real-Time Risk Supervision (FinRL-X 2.5% Hard Gate)
The **FinRL-X Risk Monitor** continuously audits portfolio health against Alpaca's Paper Trading API:
$$\text{Drawdown}_t = \frac{\text{PeakEquity} - \text{CurrentEquity}_t}{\text{PeakEquity}} \times 100\%$$
* **`SAFE` ($<1.8\%$ Drawdown):** Regular alpha generation and monitoring.
* **`WARNING` ($1.8\% - 2.49\%$ Drawdown):** Pre-calculates options hedge parameters and escalates polling frequency.
* **`BREACHED` ($\ge 2.5\%$ Drawdown / $\text{Equity} \le \$97,500.00$):** Initiates automated protective put protocol if ForecastAgent confirms macro bearishness ($P_{\text{down}} \ge 55\%$).

---

## 4. Quantitative Options Lab & Greeks Optimization (Vibe-Trading)
When triggered, the **Options Lab** calculates analytical Black-Scholes Greeks ($\Delta, \Gamma, \Theta, \mathcal{V}, \rho$) to construct an asymmetric tail hedge:
* **Optimal Strike & Expiry Selection:** Dynamically scans implied volatility surfaces to select target $-0.35$ Delta out-of-the-money puts with 21–28 Days to Expiration (DTE), balancing high gamma acceleration against theta decay.
* **Capital Sizing & Cost Budget Gate:** Sizing is computed as $N = \lceil \frac{\text{Portfolio Equity}}{\text{Spot Price} \times 100} \rceil$ subject to a strict hedge budget cap ($\le 1.5\%$ of total portfolio value).
* **OCC Symbol Generation:** Formats standard OCC symbology (e.g., `SPY260925P00267000`) for direct execution.

---

## 5. Alpaca Infrastructure, FastMCP & Cloud Run Deployment
The system provides multi-channel execution interfaces compliant with all hackathon standards:

1. **FastMCP Server (SSE / HTTP):** Exposes 6 structured MCP tools (`get_portfolio_status`, `check_risk_gates`, `predict_macro_forecast`, `calculate_protective_put`, `run_autonomous_hedging_cycle`, `execute_protective_put_order`) over Server-Sent Events on port 8080 for Claude Desktop, Cursor, and Alpaca CLI.
2. **Dedicated Alpaca Hedge CLI (`src/cli.py`):** Provides terminal command execution with `--json` output for automated workflows (`alpaca-hedge-cli status --json`, `risk`, `forecast`, `hedge`, `cycle --execute`).
3. **Autonomous Live Daemon (`scripts/run_live_agent.py`):** Standalone background service performing continuous polling, risk auditing, and automated order execution.
4. **Google Cloud Run:** Fully containerized multi-stage Docker build (`uv` builder + minimal `python:3.11-slim` runtime) with autoscaling from 1 to 5 instances.
