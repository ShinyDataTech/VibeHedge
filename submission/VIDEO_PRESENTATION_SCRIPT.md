# Alpaca AI Portfolio Hedging System
## Video Presentation Script (3-Minute Hackathon Demo)

**Hackathon:** Alpaca AI Trading Agents Hackathon ($6,000 Prize Pool)  
**Presenter:** Wei Liu (ShinyDataTech)  
**Project:** Alpaca AI Portfolio Hedging Agent  
**Video Target Length:** 3 minutes (180 seconds)  

---

### Segment 1: Hook & The Problem (0:00 - 0:35)

* **Visual on Screen:**  
  * *Slide 1 & Slide 2:* Show the compounding destruction of portfolio drawdowns (e.g., losing 50% requires a 100% gain to break even) and the limitations of traditional stop-loss orders in gap-down crashes.
* **Speaker Audio:**  
  > *"Hi everyone! In algorithmic trading and quantitative investing, catastrophic market drawdowns permanently destroy compounding capital. When macro shocks hit, traditional stop-loss orders suffer from massive gap-down slippage or trigger premature whipsaw liquidations at market bottoms.*
  >
  > *Welcome to the **Alpaca AI Portfolio Hedging System** — an autonomous AI agent built for the Alpaca AI Trading Agents Hackathon that protects equity before drawdowns compound. By combining zero-shot deep sequence forecasting, real-time risk supervision, and quantitative options calculus, our agent dynamically executes protective put hedges directly on Alpaca."*

---

### Segment 2: Architecture & Deep Learning Core (0:35 - 1:15)

* **Visual on Screen:**  
  * *Mermaid Architecture Diagram + Training Code in VS Code / IDE.*
  * Show the 9-ETF macroeconomic panel (`SPY`, `QQQ`, `IWM`, `XLK`, `XLF`, `XLE`, `XLV`, `GLD`, `TLT`) and the 42 FinRL/Relative Strength feature pipeline.
* **Speaker Audio:**  
  > *"Our system operates on a unified triple-engine architecture:*
  >
  > *First, **ForecastAgent** — our deep temporal sequence model. We trained a bi-directional recurrent model on a 9-ETF macroeconomic panel with over 32,000 hourly data points, engineering 42 FinRL indicators and cross-asset relative strength features. Crucially, our dataset sequencing respects individual asset boundaries, mathematically eliminating cross-ticker data leakage.*
  >
  > *Second, **FinRL-X Real-Time Risk Supervision**. The monitor audits our brand-new $100,000 Alpaca paper portfolio, enforcing a hardcoded **2.5% Maximum Drawdown Gate** with an equity floor of $97,500.*
  >
  > *Third, **Vibe-Trading Options Lab** — an analytical Black-Scholes Greeks engine that calculates the optimal -0.35 Delta protective put, dynamic contract sizing, and a strict 1.5% maximum hedge budget ceiling."*

---

### Segment 3: Live Demonstration & CLI / FastMCP (1:15 - 2:20)

* **Visual on Screen:**  
  * Open Terminal / Command Prompt and Alpaca Paper Trading Web Dashboard side-by-side.
  * Run `uv run python -m src.cli status` -> displays live account ID `ea533232-e5c5-4eee-87c9-b64cdf4c0c27` with $100,000.00 equity.
  * Run `uv run python -m src.cli risk` -> displays real-time 2.5% drawdown gate status.
  * Run `uv run python -m src.cli hedge --symbol SPY` -> displays options strike, expiry, Greeks ($\Delta=-0.34, \Gamma=0.025, \Theta=-0.11, \nu=0.24$), and total cost.
  * Run `uv run python -m src.cli cycle --execute` or show the FastMCP server connected to Claude Desktop / Cursor.
* **Speaker Audio:**  
  > *"Let's see the agent in action live!*
  >
  > *Running our dedicated CLI tool `alpaca-hedge-cli status`, we connect to our fresh Alpaca paper account with $100,000 starting equity. Every command supports the `--json` flag for seamless tool integration.*
  >
  > *Checking `alpaca-hedge-cli risk`, our FinRL-X monitor confirms the portfolio is healthy. But let's look at what happens when market risk escalates:*
  >
  > *Running `alpaca-hedge-cli hedge --symbol SPY`, our Options Lab instantly prices the entire volatility surface, selecting an optimal $267 strike OTM put with -0.34 Delta and 28 DTE. It automatically sizes 4 contracts, providing $106,800 of downside shield for just $1,336 — well under our 1.5% budget limit.*
  >
  > *In full autonomous mode or via our FastMCP server over HTTP/SSE, the agent monitors market bars, detects downtrend probabilities with ForecastAgent, and immediately submits the protective put order directly through Alpaca's Options Trading API."*

---

### Segment 4: Cloud Run, Featherless AI & Conclusion (2:20 - 3:00)

* **Visual on Screen:**  
  * Google Cloud Run console / `Dockerfile` / `deploy_cloud_run.sh` script.
  * Featherless AI integration snippet and slide summary.
  * GitHub repository overview.
* **Speaker Audio:**  
  > *"For production scalability, the FastMCP server is containerized with a lightweight multi-stage Docker build ready for Google Cloud Run with automatic horizontal scaling.*
  >
  > *We also integrated the hackathon sponsor **Featherless AI** using their Per-Request API for high-level risk supervisor synthesis.*
  >
  > *The Alpaca AI Portfolio Hedging System delivers institutional-grade capital protection, turning volatile market drops from existential threats into managed risks.*
  >
  > *Check out our complete open-source codebase on GitHub. Thank you to LabLab.ai, Alpaca, and Featherless for an incredible hackathon!"*

---

### Recording & Demo Checklist for Presenter:
- [x] Alpaca Paper Trading Account initialized with exactly $100,000.00 USD.
- [x] Account ID: `ea533232-e5c5-4eee-87c9-b64cdf4c0c27` verified and active.
- [x] Terminal open with `uv run python -m src.cli status`, `risk`, `hedge`, and `cycle` ready.
- [x] FastMCP Server running on port 8080 (`uv run python -m src.mcp_server.server`).
- [x] Slide deck open (`submission/SLIDE_PRESENTATION.md`).
