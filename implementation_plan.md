# Refinement & Submission Plan: Alpaca AI Portfolio Hedging System

This plan outlines the end-to-end refinement of the **Alpaca AI Portfolio Hedging System** and the creation of all required submission assets for the **Alpaca AI Trading Agents Hackathon** ($6K prize pool, Lablab.ai x Alpaca x Featherless).

---

## 📋 Hackathon Requirements & Submission Checklist

| Requirement Area | Hackathon Rule | System Implementation & Status |
| :--- | :--- | :--- |
| **1. Autonomous Agents** | Autonomous AI trading agent designed to generate P&L / protect equity. | **Implemented**: ForecastAgent XLSTM temporal model + FinRL-X real-time risk gates + Vibe-Trading Options Lab. |
| **2. MCP or CLI Tooling** | Project MUST use either Alpaca's MCP server or CLI tools. | **To Refine**: Provide both **FastMCP Server** (HTTP/SSE on Cloud Run) and **Alpaca Hedge CLI** (`src/cli.py`) with structured JSON output. |
| **3. Options Trading** | All strategies MUST incorporate options trading. | **Implemented**: Black-Scholes Greeks engine, dynamic Delta-hedged protective put selector, OCC symbol generation, Alpaca options execution. |
| **4. Account Requirement** | Brand-new paper account dedicated to hackathon with **$100,000** starting balance. | **Documented**: Step-by-step guide and config for linking fresh Alpaca Paper Account ID for judging. |
| **5. Mandatory Write-Up** | 1-page write-up covering AI logic, risk gates, and Alpaca infrastructure. | **To Generate**: `submission/HACKATHON_ONE_PAGE_WRITEUP.md` & formatted PDF export script. |
| **6. Media Presentation** | Demo video presentation & slide presentation deck (PDF). | **To Generate**: `submission/VIDEO_PRESENTATION_SCRIPT.md` (3-min script) + `submission/SLIDE_PRESENTATION.md` (10-slide deck). |
| **7. Submission Metadata** | Title, short description (50-255 chars), long description (600-2000 chars), tech tags. | **To Generate**: `submission/SUBMISSION_METADATA.md` ready for LabLab.ai form. |
| **8. Build in Public** | Up to 5 social media post links tagging `@lablabai` and `@AlpacaHQ`. | **To Generate**: `submission/social_media_posts.md` (5 high-impact X & LinkedIn posts). |
| **9. Featherless Bonus** | Integration with Featherless LLM inference (`ALPACAA26` sponsor code). | **To Refine**: Add native Featherless provider support in `src/agent/orchestration.py`. |
| **10. Cover Image** | 16:9 aspect ratio cover image. | **To Generate**: AI-generated 16:9 banner artifact. |

---

## User Review Required

> [!IMPORTANT]
> **Alpaca Paper Trading Account Requirement**:
> As specified in the hackathon rules, projects must run on a **brand-new Alpaca paper trading account** with starting capital set to **$100,000.00**.
> Please create a fresh paper trading API key in your Alpaca dashboard and ensure the starting equity is reset to $100,000. Your Account ID will be included in the submission form for judges to evaluate live P&L.

> [!TIP]
> **Featherless LLM Integration**:
> We will add native Featherless API integration (`https://api.featherless.ai/v1`) with voucher code `ALPACAA26` ($25 credit), allowing seamless switching between local Ollama, OpenClaude, and cloud-hosted open models (e.g., Llama-3.1-70B / Qwen-2.5-72B).

---

## Proposed Changes

### Component 1: Engine Refinements (CLI, Featherless LLM & Live Daemon)

#### [NEW] [src/cli.py](file:///c:/AI_Tools/alpaca-ai-trading-agents-hackathon/src/cli.py)
- Command-line interface (`alpaca-hedge-cli`) supporting both human-readable Rich table formats and machine-readable JSON (`--json` flag).
- Subcommands:
  - `status`: Show live portfolio equity, cash, and open positions.
  - `risk`: Evaluate 2.5% drawdown risk gate against $100k starting equity.
  - `forecast --symbol SPY`: Run ForecastAgent 24h macro downtrend prediction.
  - `hedge --symbol SPY --delta -0.35`: Compute optimal protective put strike, expiry, and Greeks.
  - `cycle --symbol SPY --execute`: Run the full autonomous reasoning & execution cycle.

#### [MODIFY] [src/agent/orchestration.py](file:///c:/AI_Tools/alpaca-ai-trading-agents-hackathon/src/agent/orchestration.py)
- Add native support for **Featherless API** (`FEATHERLESS_API_KEY`, `FEATHERLESS_BASE_URL=https://api.featherless.ai/v1`, model: `meta-llama/Meta-Llama-3.1-8B-Instruct` or `Qwen/Qwen2.5-72B-Instruct`) alongside Ollama and OpenClaude.
- Provide institutional risk supervisor narrative synthesis from the multi-step reasoning trace.

#### [NEW] [scripts/run_live_agent.py](file:///c:/AI_Tools/alpaca-ai-trading-agents-hackathon/scripts/run_live_agent.py)
- Continuous live monitoring daemon for paper trading.
- Periodically polls Alpaca account equity, checks the 2.5% drawdown gate, runs ForecastAgent inference, and automatically executes options hedging orders if gates breach.

---

### Component 2: Submission Documents & Deliverables

#### [NEW] [submission/HACKATHON_ONE_PAGE_WRITEUP.md](file:///c:/AI_Tools/alpaca-ai-trading-agents-hackathon/submission/HACKATHON_ONE_PAGE_WRITEUP.md)
- Complete, publication-grade 1-page writeup addressing all judging criteria:
  1. **Executive Summary & Mission**: Quantitative portfolio protection via autonomous options trading.
  2. **AI Logic & Deep Sequence Modeling**: ForecastAgent bi-directional temporal architecture, 9-ETF macroeconomic panel, FinRL & Relative Strength feature engineering (42 indicators), leak-free boundary training.
  3. **Risk Management & 2.5% Drawdown Gate**: Real-time equity monitoring against $100k capital, multi-tiered states (`SAFE`, `WARNING`, `BREACHED`).
  4. **Vibe-Trading Options Lab & Greeks Engine**: Analytical Black-Scholes pricing, dynamic Delta targeting (-0.35), contract sizing, 1.5% budget constraint.
  5. **Alpaca Infrastructure & Deployment**: FastMCP HTTP/SSE server on Google Cloud Run, Alpaca Trading & Market Data API integration, and CLI tool.

#### [NEW] [submission/SLIDE_PRESENTATION.md](file:///c:/AI_Tools/alpaca-ai-trading-agents-hackathon/submission/SLIDE_PRESENTATION.md)
- Complete 10-slide visual presentation deck:
  - Slide 1: Title & Vision (Alpaca AI Portfolio Hedging System)
  - Slide 2: The Problem (Drawdown destruction in macro selloffs)
  - Slide 3: The Solution (Autonomous AI Options Hedging)
  - Slide 4: System Architecture (Mermaid diagram & data pipeline)
  - Slide 5: Deep Sequence Model (ForecastAgent & 9-ETF Macro Panel)
  - Slide 6: Risk Monitoring & 2.5% Hard Gate ($97,500 Floor)
  - Slide 7: Vibe-Trading Options Lab & Greeks Engine
  - Slide 8: FastMCP, CLI & Google Cloud Run Infrastructure
  - Slide 9: Live Paper Trading Performance & Execution Trace
  - Slide 10: Summary, Impact & Future Roadmap

#### [NEW] [submission/VIDEO_PRESENTATION_SCRIPT.md](file:///c:/AI_Tools/alpaca-ai-trading-agents-hackathon/submission/VIDEO_PRESENTATION_SCRIPT.md)
- Turn-by-turn 3-minute video presentation script:
  - 0:00 - 0:30: Introduction & Hook
  - 0:30 - 1:15: Deep Learning & Risk Architecture
  - 1:15 - 2:15: Live Demo Walkthrough (CLI, FastMCP, Options Execution in Alpaca Paper Account)
  - 2:15 - 3:00: Impact, Cloud Scalability, and Conclusion

#### [NEW] [submission/SUBMISSION_METADATA.md](file:///c:/AI_Tools/alpaca-ai-trading-agents-hackathon/submission/SUBMISSION_METADATA.md)
- Complete, exact text to paste into the LabLab.ai submission portal:
  - **Submission Title**: `Alpaca AI Portfolio Hedging Agent: Autonomous Options Risk & Alpha Engine`
  - **Short Description**: Character-counted one-liner (<255 characters, >50 characters).
  - **Long Description**: Structured multi-paragraph description (>100 words, 600–2000 characters).
  - **Categories & Event Tracks**: Trading Agents, Options Alpha, Autonomous AI, Fintech.
  - **Technologies Used**: Alpaca Trading API, Alpaca Market Data API, FastMCP, PyTorch, FinRL, Vibe-Trading, Google Cloud Run, Featherless AI, Python.
  - **Account ID Checklist & Verification**.

#### [NEW] [submission/social_media_posts.md](file:///c:/AI_Tools/alpaca-ai-trading-agents-hackathon/submission/social_media_posts.md)
- 5 comprehensive build-in-public posts tailored for X (Twitter) and LinkedIn:
  - Post 1: Kickoff & Vision — Why traditional stop-losses fail and why autonomous options hedging is the future.
  - Post 2: Deep Learning Architecture — 9-ETF macroeconomic panel, FinRL features, zero data leakage.
  - Post 3: Quantitative Options Lab — Black-Scholes Greeks engine and -0.35 Delta protective put sizing.
  - Post 4: FastMCP & Cloud Infrastructure — Exposing autonomous trading tools via SSE to AI agents and Google Cloud Run.
  - Post 5: Final Submission & Live Demo — Performance results, repo launch, and thanking `@lablabai`, `@AlpacaHQ`, and `@featherless_ai`.

#### [NEW] [submission/generate_cover_image.py](file:///c:/AI_Tools/alpaca-ai-trading-agents-hackathon/submission/generate_cover_image.py) & [Cover Image Generation]
- Generate a sleek 16:9 banner artifact for the submission media tab.

---

### Component 3: Test Suite & Documentation Polish

#### [MODIFY] [tests/test_hedging_engine.py](file:///c:/AI_Tools/alpaca-ai-trading-agents-hackathon/tests/test_hedging_engine.py)
- Expand test coverage to verify CLI outputs, Featherless LLM provider fallback, and live daemon cycle logic.

#### [MODIFY] [README.md](file:///c:/AI_Tools/alpaca-ai-trading-agents-hackathon/README.md)
- Add sections for the CLI commands, Featherless AI integration, live continuous agent daemon, and links to the submission deliverables.

---

## 🔍 Verification Plan

### Automated Tests
- Run `uv run python -m unittest discover -s tests` to verify 100% test pass rate across all engine modules.
- Test CLI commands: `uv run python -m src.cli status --json`, `uv run python -m src.cli risk`, `uv run python -m src.cli hedge --symbol SPY`.
- Test continuous daemon loop dry-run: `uv run python scripts/run_live_agent.py --interval 5 --dry-run`.

### Submission Asset Verification
- Validate word counts and character limits for all LabLab.ai submission form fields:
  - Short description: between 50 and 255 characters.
  - Long description: between 600 and 2000 characters (min 100 words).
  - 1-page writeup: comprehensive and structured according to Alpaca hackathon criteria.
- Verify that social posts tag `@lablabai` and `@AlpacaHQ`.
- Verify generated cover image is 16:9 aspect ratio.
