# LabLab.ai Hackathon Submission Metadata

Use this document to copy and paste directly into the **LabLab.ai Alpaca AI Trading Agents Hackathon** submission portal (`https://lablab.ai/ai-hackathons/alpaca-ai-trading-agents-hackathon/`).

---

## 📝 Step 1: Basic Information

### Submission Title *
```text
Alpaca AI Portfolio Hedging Agent: Autonomous Options Risk & Alpha Engine
```
*(73 characters)*

---

### Short Description *
*(Constraint: Minimum 50 characters, Maximum 255 characters)*

```text
Autonomous AI portfolio hedging agent on Alpaca Trading API combining ForecastAgent deep sequence forecasting, a 2.5% FinRL-X drawdown gate ($100k balance), and Vibe-Trading Options Lab for dynamic -0.35 Delta protective put execution via FastMCP & CLI.
```
*(Length: 251 characters — verified within limits)*

---

### Long Description *
*(Constraint: Minimum 100 words, Minimum 600 characters, Maximum 2000 characters)*

```text
In quantitative investing, catastrophic market drawdowns permanently destroy compounding capital. Traditional stop-loss orders suffer from severe slippage during overnight gap-downs and trigger premature liquidations at market bottoms. 

The Alpaca AI Portfolio Hedging System solves this by uniting real-time risk supervision, deep sequence forecasting, and quantitative options calculus into an autonomous agent built for the Alpaca AI Trading Agents Hackathon.

Key Technical Capabilities:
1. FinRL-X Real-Time Risk Monitor: Audits live portfolio equity on Alpaca's Paper Trading API ($100,000 starting balance) and enforces a hardcoded 2.5% Maximum Drawdown Risk Gate ($97,500 equity floor), classifying health into SAFE, WARNING, and BREACHED states.
2. ForecastAgent Deep Sequence Core: A bi-directional recurrent model trained across a 9-ETF macroeconomic panel (SPY, QQQ, IWM, XLK, XLF, XLE, XLV, GLD, TLT) with 32,886 hourly rows (1.38M data points). Extracts 42 FinRL and cross-asset Relative Strength features using leak-free per-ticker boundary sequencing to predict 24h downtrend probabilities and multi-quantile return trajectories.
3. Vibe-Trading Options Lab: Analytical Black-Scholes Greeks engine (Delta, Gamma, Vega, Theta) dynamically selecting optimal -0.35 Delta out-of-the-money protective puts with 21-28 DTE, contract sizing, and a strict 1.5% maximum hedge budget cap.
4. FastMCP & CLI Tooling: Exposes 6 structured MCP tools over HTTP/SSE on port 8080 for AI assistants (Claude Desktop, Cursor, Alpaca CLI), complemented by a dedicated CLI tool (alpaca-hedge-cli) with --json output and Google Cloud Run containerization.
5. Featherless AI Integration: Employs sponsor Featherless API (code ALPACAA26) with Llama-3.1 for institutional risk supervisor chain-of-thought narrative synthesis.
```
*(Word Count: 268 words | Character Count: 1,840 characters — verified within 600-2000 character limit)*

---

### Categories *
```text
Autonomous Agents, Algorithmic Trading, Quantitative Finance, Risk Management, Machine Learning
```

---

### Event Tracks *
```text
Options Alpha Agents
```

---

### Technologies Used *
```text
Alpaca Trading API, Alpaca Market Data API, Alpaca CLI, FastMCP, Model Context Protocol, Python 3.12, PyTorch, Featherless AI, FinRL, Vibe-Trading, Google Cloud Run, Docker, uv, Pandas, SciPy
```

---

### Social Media Post Links (Build in Public Challenge)
*(Submit up to 5 links from X/LinkedIn tagging @lablabai and @AlpacaHQ)*
- **Post Link 1:** `https://x.com/your_handle/status/1` (Kickoff & Problem Framing)
- **Post Link 2:** `https://x.com/your_handle/status/2` (ForecastAgent 9-ETF Deep Sequence Model)
- **Post Link 3:** `https://x.com/your_handle/status/3` (Options Lab Black-Scholes Greeks Engine)
- **Post Link 4:** `https://x.com/your_handle/status/4` (FastMCP Server & Cloud Run Deployment)
- **Post Link 5:** `https://x.com/your_handle/status/5` (Final Submission & Live Demo Video)
*(See `submission/social_media_posts.md` for full post copy)*

---

## 🎨 Step 2: Media Assets

| Media Item | Format / Dimensions | File Location |
| :--- | :--- | :--- |
| **Cover Image** | 16:9 PNG / WebP | `submission/cover_image.png` |
| **Video Presentation \*** | MP4 / WebM (Max 3 mins) | `submission/VIDEO_PRESENTATION_SCRIPT.md` (Script) |
| **Slide Presentation \*** | PDF (10 Slides) | `submission/SLIDE_PRESENTATION.md` |

---

## 💻 Step 3: Application (Hosting, Repository & Account ID)

### GitHub Repository *
```text
https://github.com/ShinyDataTech/VibeHedge
```

### Demo Application Platform
```text
Google Cloud Run
```
*(Select "Other" or "Google Cloud Run" in dropdown)*

### Demo Application URL *
```text
https://alpaca-hedging-agent-521695902469.us-central1.run.app
```
*(FastMCP SSE Endpoint: `https://alpaca-hedging-agent-521695902469.us-central1.run.app/sse`)*

### Alpaca Account ID *
```text
ea533232-e5c5-4eee-87c9-b64cdf4c0c27
```
*(Starting Balance: $100,000.00 USD | Status: ACTIVE | Judge P&L Evaluation Account)*

### Additional Information (Optional, max 2000 characters)
```text
The Alpaca AI Portfolio Hedging System (VibeHedge) is an autonomous options risk supervisor and alpha engine designed for the Alpaca AI Trading Agents Hackathon.

Architecture & Highlights:
1. Live Production Deployment: Deployed on Google Cloud Run (us-central1, project forecastagent-501722 / 521695902469) running 24/7 with 1 warm instance (min-instances=1) and continuous CPU allocation (cpu-throttling=false) to ensure the FinRL-X risk monitor and polling daemon never sleep during the 7-day live competition window.
2. FastMCP SSE / HTTP Protocol: Exposes 6 structured MCP tools over Server-Sent Events on port 8080 (get_portfolio_status, check_risk_gates, predict_macro_forecast, calculate_protective_put, run_autonomous_hedging_cycle, execute_protective_put_order) compatible with Claude Desktop, Cursor, and Alpaca CLI.
3. Dual Interface: Interactive CLI tool (alpaca-hedge-cli) with pure JSON output (--json) and live background daemon.
4. Triple-Engine Intelligence:
   - ForecastAgent: Bi-directional recurrent deep temporal sequence network trained on a 9-ETF macroeconomic panel (SPY, QQQ, IWM, XLK, XLF, XLE, XLV, GLD, TLT; 32,886 hourly rows, 1.38M data points) with 42 FinRL & Relative Strength features and leak-free per-ticker boundary sequencing.
   - FinRL-X Risk Supervision: Hardcoded 2.5% drawdown gate ($97,500 floor on $100k starting capital).
   - Vibe-Trading Options Lab: Analytical Black-Scholes Greeks engine dynamically targeting -0.35 Delta protective puts with 21-28 DTE, contract sizing, and a strict 1.5% maximum hedge budget cap.
5. Sponsor Bonus Integration: Native Featherless AI LLM reasoning (meta-llama/Meta-Llama-3.1-8B-Instruct via Per-Request API, code ALPACAA26) for institutional supervisor synthesis.

All documentation, slide decks, video presentation scripts, and the mandatory 1-page writeup are included in the repository.
```
*(Length: 1,845 characters — verified within 2000 character limit)*

---

### One-Page Write-Up Document
```text
submission/HACKATHON_ONE_PAGE_WRITEUP.md
```
*(Covering AI logic, FinRL-X risk gates, Options Lab Greeks formulation, and Alpaca FastMCP infrastructure)*

