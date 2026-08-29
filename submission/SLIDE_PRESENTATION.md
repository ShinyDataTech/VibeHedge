# Alpaca AI Portfolio Hedging System
## Slide Presentation Deck (10 Slides)

**Hackathon:** Alpaca AI Trading Agents Hackathon ($6K Prize Pool)  
**Team:** ShinyDataTech (Wei Liu) | **Track:** Options Alpha & Autonomous Trading  
**Paper Account ID:** `ea533232-e5c5-4eee-87c9-b64cdf4c0c27` | **Starting Capital:** $100,000.00 USD  

---

### Slide 1: Title & Vision
```
===================================================================================
                    ALPACA AI PORTFOLIO HEDGING SYSTEM
             Autonomous Options Risk Supervision & Alpha Engine
===================================================================================

  "Protecting capital before drawdowns compound — combining zero-shot deep temporal
   forecasting, real-time risk gates, and quantitative options execution."

  • Platform: Alpaca Trading API & Market Data API
  • Interface: FastMCP (SSE/HTTP), Alpaca CLI, Google Cloud Run
  • AI Engine: ForecastAgent (Bi-LSTM on 9-ETF Macro Panel) + Featherless AI LLM
  • Quantitative Hedging: Vibe-Trading Options Lab (Black-Scholes Greeks Engine)
```

---

### Slide 2: The Problem: Drawdown Destruction
```
===================================================================================
                  THE PROBLEM: CATASTROPHIC PORTFOLIO DRAWDOWN
===================================================================================

  1. Asymmetric Loss Recovery Math:
     • A 10% loss requires an 11.1% gain to break even.
     • A 25% loss requires a 33.3% gain to break even.
     • A 50% loss requires a 100.0% gain to break even.

  2. Traditional Stop-Loss Pitfalls:
     • Severe slippage during overnight gap-downs and macro shocks.
     • Premature whipsaws (selling at market bottom during noise).
     • Destructive execution during illiquid market opens.

  3. The Need for Autonomous Options Hedging:
     • Non-linear, convex payoff profiles that shield equity without liquidating assets.
     • Continuous AI risk monitoring with zero human emotional hesitation.
```

---

### Slide 3: The Solution: Autonomous Options Hedging Agent
```
===================================================================================
                     THE SOLUTION: AN AUTONOMOUS TRIPLE-ENGINE
===================================================================================

  ┌────────────────────────┐  ┌────────────────────────┐  ┌────────────────────────┐
  │  FinRL-X Risk Monitor  │  │  ForecastAgent AI Core │  │  Options Lab Greeks    │
  │                        │  │                        │  │                        │
  │ • Real-time $100k poll │  │ • 9-ETF macro panel    │  │ • Analytical Greeks    │
  │ • Hard 2.5% gate       │  │ • 42 FinRL & RS feat.  │  │ • -0.35 Delta Put OTM  │
  │ • $97,500 equity floor │  │ • P(Downtrend) & quant.│  │ • Strict 1.5% max cost │
  └───────────┬────────────┘  └───────────┬────────────┘  └───────────┬────────────┘
              │                           │                           │
              └───────────────────────────┼───────────────────────────┘
                                          ▼
                      ┌───────────────────────────────────────┐
                      │    FastMCP & Autonomous Execution     │
                      │  Direct Alpaca Options API Fill & CLI │
                      └───────────────────────────────────────┘
```

---

### Slide 4: System Architecture & Dataflow
```
===================================================================================
                           END-TO-END ARCHITECTURE
===================================================================================

  [Market Data Pipeline]
  Alpaca Historical API ──► 9-ETF Hourly Data ──► FinRL 42 Features ──► ForecastAgent
                                                                             │
  [Real-Time Risk & Reasoning]                                               │
  Alpaca Paper Portfolio ($100k) ──► FinRL-X Monitor                         │
            │                                                                │
            ├── Drawdown < 1.8% ──► SAFE (Routine Alpha)                    │
            ├── Drawdown 1.8-2.49% ──► WARNING (Pre-calculate Hedge)         │
            └── Drawdown >= 2.5% (Equity <= $97.5k)                          │
                      │                                                      │
                      ▼                                                      │
         [Confirm Bearish Downtrend?] ◄──────────────────────────────────────┘
                      │ (Prob >= 55% / Return < -1.5%)
                      ▼
         [Vibe-Trading Options Lab]
         Compute Optimal Protective Put Strike, Expiry, Contracts & Greeks
                      │
                      ▼
         [Execution Gateway]
         FastMCP (SSE/HTTP Port 8080) / CLI ──► Alpaca Options API Order Fill
```

---

### Slide 5: Deep Sequence Model (ForecastAgent)
```
===================================================================================
                 DEEP SEQUENCE MODEL & LEAK-FREE TRAINING
===================================================================================

  • Macroeconomic Panel (9 Cross-Asset ETFs):
    SPY (S&P 500), QQQ (Nasdaq), IWM (Russell 2000), XLK (Tech), XLF (Financials),
    XLE (Energy), XLV (Healthcare), GLD (Gold), TLT (20+ Year Treasuries).
    Total: 32,886 hourly rows, 1.38 Million data points across 2-year lookback.

  • 42 Technical & Relative Strength Features:
    22 FinRL indicators (MACD, RSI, Bollinger, ATR, CCI, Stochastics, SMA crossovers)
    + 8 Cross-Asset Relative Strength & Beta indicators against SPY benchmark
    + OHLCV volume momentum vectors.

  • Leak-Free Boundary Training:
    Sequences sliced strictly within individual asset boundaries (24h lookback -> 24h forecast).
    27,090 training sequences | 4,086 validation sequences (Zero cross-ticker contamination).
```

---

### Slide 6: Real-Time Risk Supervision (FinRL-X)
```
===================================================================================
              FINRL-X REAL-TIME RISK GATES ($100K STARTING CAPITAL)
===================================================================================

  • Initial Starting Capital: $100,000.00 USD (Mandatory Hackathon Balance)
  • Hard Drawdown Limit:      2.50% ($2,500.00 max loss)
  • Absolute Equity Floor:    $97,500.00 USD

  Evaluation States:
  ┌────────────┬──────────────────────┬───────────────────────────────────────────┐
  │ State      │ Drawdown Range       │ Agent Action                              │
  ├────────────┼──────────────────────┼───────────────────────────────────────────┤
  │ SAFE       │ < 1.8% ($0 - $1,800) │ Standard monitoring & alpha generation   │
  │ WARNING    │ 1.8% - 2.49%         │ 5-min poll escalation, pre-calculate put  │
  │ BREACHED   │ >= 2.5% (<= $97,500) │ Trigger Options Lab & Autonomous Order    │
  └────────────┴──────────────────────┴───────────────────────────────────────────┘
```

---

### Slide 7: Quantitative Options Lab (Vibe-Trading)
```
===================================================================================
             VIBE-TRADING OPTIONS LAB: BLACK-SCHOLES & GREEKS ENGINE
===================================================================================

  • Analytical Greeks Formulation:
    Delta:   Δ_put = N(d1) - 1   (Target: -0.35 Delta OTM Put)
    Gamma:   Γ = N'(d1) / (S * σ * √T)
    Theta:   Θ_put = -[S * N'(d1) * σ / (2√T)] + r * K * e^(-rT) * N(-d2)
    Vega:    ν = S * √T * N'(d1)

  • Dynamic Protective Put Sizing:
    Number of Contracts: N = ceil( Portfolio Equity / (Spot Price * 100) )
    For $100k equity & SPY @ $271.78 -> N = 4 contracts ($106,800 downside coverage).

  • Strict Budget Ceiling:
    Hedge Outlay <= 1.50% of Portfolio Value ($1,336.67 actual cost = 1.34% outlay).
```

---

### Slide 8: FastMCP, CLI & Google Cloud Run
```
===================================================================================
                     FASTMCP, CLI & CLOUD RUN INFRASTRUCTURE
===================================================================================

  1. FastMCP Server (SSE / HTTP on Port 8080):
     • get_portfolio_status         -> Live equity, cash & open positions
     • check_risk_gates             -> 2.5% drawdown gate audit
     • predict_macro_forecast       -> ForecastAgent 24h macro prediction
     • calculate_protective_put     -> Options Lab optimal strike & Greeks
     • run_autonomous_hedging_cycle -> Full reasoning & autonomous execution

  2. Alpaca Hedge CLI (`alpaca-hedge-cli`):
     • Human-readable ANSI tables or structured JSON (`--json` flag) for CI/CD & tools.

  3. Enterprise Cloud Deployment:
     • Google Cloud Run containerized deployment via multi-stage Docker & uv packaging.
```

---

### Slide 9: Live Paper Trading Execution & Telemetry
```
===================================================================================
                      LIVE EXECUTION TRACE & TELEMETRY
===================================================================================

  [Alpaca Paper Account ea533232-e5c5-4eee-87c9-b64cdf4c0c27]
  • Initial Balance: $100,000.00 | Buying Power: $400,000.00 | Status: ACTIVE

  [Live Hedge Output]:
  ---------------------------------------------------------------------------------
  Underlying Asset:      SPY @ $271.78
  Target Option Symbol:  SPY260925P00267000
  Strike Price:          $267.00 (28 DTE)
  Target Delta:          -0.340 (Δ=-0.340, Γ=0.0256, Θ=-0.113, ν=0.239)
  Contract Quantity:     4 contracts
  Total Hedge Outlay:    $1,336.67 (1.34% of portfolio)
  Downside Shield:       $106,800.00 capital protected against market crash
  ---------------------------------------------------------------------------------
```

---

### Slide 10: Featherless AI Bonus, Impact & Roadmap
```
===================================================================================
                      FEATHERLESS AI INTEGRATION & ROADMAP
===================================================================================

  • Featherless AI Integration (Hackathon Inference Sponsor):
    Integrated Llama-3.1-8B-Instruct via Per-Request API (Sponsor Code: ALPACAA26)
    for high-level institutional risk supervisor chain-of-thought synthesis.

  • Business Impact:
    • Eliminates catastrophic tail-risk drawdowns in quantitative funds & retail accounts.
    • Maintains equity compounding while preserving upside participation.

  • Future Roadmap:
    • Multi-leg volatility arbitrage (Iron Condors, VIX call calendars).
    • Reinforcement learning dynamic hedge rebalancing (FinRL PPO/DDPG agents).
    • Live WebSocket streaming order routing with zero-latency execution.
```
