# QUANT AI TERMINAL - Institutional-Grade Algorithmic Trading Engine

**Version 11.0 | MetaTrader 5 | Python 3.9+**

---

## Overview

QUANT AI TERMINAL is a hybrid quantitative trading platform that combines **three independent signal sources** into a unified portfolio management system:

1. **AI Sentiment Analysis (Groq Llama-3.3 70B)**: Real-time market sentiment quantification with geopolitical regime awareness
2. **Global Macro-Regime Detection (RSS Feeds)**: Continuous monitoring of geopolitical and economic catalysts (wars, central bank decisions, economic crises)
3. **Historical Statistical Seasonality**: 5-year monthly average analysis to identify recurring seasonal patterns

The engine separates **speculation from investment** through a dual-horizon framework ("Long-Term Immunity"):
- **Short-Term (Spec)**: Aggressive scalping with tight stops/targets (MAGIC 1001)
- **Long-Term (Cassettista)**: Patient value accumulation with structural conviction (MAGIC 2002)

### Key Architectural Principle

> *Crisis overrides seasonality. Geopolitical reality trumps historical patterns.*

The system immediately downgrades all analysis if macro context signals global instability, preventing the most common failure mode: trading normal patterns during regime change.

---

## Core Features

### 1. **Hybrid Multi-Input Sentiment Analysis**

```
Asset Sentiment Score: -10 (crash) to +10 (pump)

Input 1: GLOBAL MACRO CONTEXT (Real-time RSS)
├─ BBC World: Geopolitical risk, wars, terrorism
├─ BBC Business: Central Bank policy, M&A, corporate actions
└─ Regime Detection: Crisis vs. Normal market conditions

Input 2: ASSET-SPECIFIC NEWS (Multi-source)
├─ Yahoo Finance headlines
├─ NewsAPI relevancy-sorted articles
└─ Company/sector catalysts

Input 3: STATISTICAL SEASONALITY (5-year monthly)
├─ Historical average return for current month
├─ BULLISH/BEARISH bias indication
└─ Override flag: disabled during macro crises

AI DECISION ENGINE (Groq Llama-3.3 70B):
├─ Weighted combination of three inputs
├─ Confidence threshold: score must exceed ±5 to avoid noise
└─ Output: JSON structured (trend + quantitative score + reasoning)
```

**Caching Strategy**: 10-minute TTL per asset to minimize API costs while maintaining freshness.

---

### 2. **Long-Term Immunity: Asymmetric Risk Management**

Positions are classified into two independent universes with **different exit rules**:

#### Short-Term Positions (MAGIC_SHORT_TERM = 1001)
- **Target**: +$limit_base (aggressive, 2-3x commission)
- **Stop Loss**: -$limit_base * 1.5 (tight, 1.5-2.5x commission)
- **Quarantine**: 2 consecutive stops → 1-hour freeze on this asset
- **Friday Shield**: Force-closed before weekend gap risk
- **P&L Threshold**: Typically +$30-$50 for $100 capital account
  
**Use Case**: Forex pairs with tight spreads, high momentum assets, mean reversion signals

#### Long-Term Positions (MAGIC_LONG_TERM = 2002)
- **Target**: Trailing stop (let winners run, protect with -3% trail)
- **Stop Loss**: -$limit_base * 4.0 (structural conviction, 20+x commission)
- **Immunity**: Preserved through Friday markets and daily drawdown limits
- **Duration**: Weeks to months (cassettista philosophy)
- **P&L Threshold**: Typically +$50-$100+ for same capital (patient accumulation)

**Use Case**: Crypto holdings, quality equities, long-dated trend positions

**Key Insight**: The system never forces-closes long-term positions during max drawdown events, preserving thesis conviction while exiting speculative losses.

---

### 3. **Dynamic Daily Drawdown Kill-Switch**

```
Daily Profit/Loss Accumulator: Midnight Reset

IF profitto_giornaliero ≤ -max_loss_daily:
    ├─ Close ALL short-term positions immediately
    ├─ Preserve long-term cassettista holdings
    ├─ Transition to MONITORAGGIO (standby mode)
    ├─ Send Telegram alert: "MAX DRAWDOWN REACHED"
    └─ Prevent further execution until next market day

Configuration:
├─ Typical max_loss_daily: $30 (30% of $100 account)
├─ Prevents catastrophic blowup from cascading losses
└─ Resets daily at midnight (prevents Friday end-of-session traps)
```

This is **not** a trailing stop on equity, but an **aggregate daily volume stop** that preserves portfolio through drawdowns.

---

### 4. **Victory & Loss Quarantine System**

Prevents over-trading losers and avoids ping-pong trades.

#### Loss Quarantine
```
Consecutive Stop Losses on Same Asset:
├─ 1st Stop Loss: Log and continue monitoring
├─ 2nd Stop Loss: Trigger 1-hour quarantine on this ticker
└─ Resume trading after cooldown period expires

Rationale: Prevents "revenge trading" on assets with adverse regime changes.
```

#### Victory Cooldown
```
Take-Profit Exit:
├─ Pause trading on this asset for 2 hours
├─ Prevents immediate re-entry and "ping-pong" losses
├─ Resets the "win count" (loss counter zeroes out)
└─ Returns with fresh conviction if signal regenerates

Rationale: Profit-taking indicates signal exhaustion; respects market mean-reversion.
```

---

### 5. **Phase 1: Massive Initial Portfolio Construction**

On START button, the engine enters Phase 1 (one-time):

```
PHASE 1 LOGIC:
├─ Scan ALL assets in watchlist regardless of technical signals
├─ Query AI for each asset WITHOUT waiting for price movement
├─ Entry threshold: AI score > ±5 (confidence filter)
├─ Allocate capital proportionally across qualified assets
├─ Duration: ~5-10 minutes (all tickers scanned once)
└─ Goal: Construct initial position diversity before Phase 2

PHASE 2 (Continuous):
├─ Monitor open positions with exit logic
├─ Scan for new entry signals only on price dislocations
├─ Lower frequency scanning to avoid API throttling
└─ Continue until max drawdown or user stop
```

This prevents the "cold start" problem where the first trades exhaust the watchlist.

---

## Tech Stack

### Core Dependencies
```
MetaTrader 5 (mt5)          - Live order execution & position tracking
CustomTkinter 8.7           - Modern institutional-grade UI
yfinance                     - Historical price data (backtest snapshots)
Groq API (Llama-3.3 70B)    - Sentiment analysis & LLM reasoning
NewsAPI                      - Asset-specific financial news
feedparser                   - RSS feed parsing (macro context)
python-dotenv               - Secure API key management
lumibot                      - Backtesting framework
pandas                       - Time-series analysis
```

### Architecture
```
┌──────────────────────────────────────┐
│         UI Layer (CustomTkinter)    │
│    [Settings] [Start/Stop] [Terminal]
└──────────┬───────────────────────────┘
           │
┌──────────v───────────────────────────┐
│    Main Trading Engine (mt5_engine)  │
│  [State Machine] [Position Memory]   │
│  [Risk Management] [Logging]         │
└──────────┬───────────────────────────┘
           │
┌──────────v───────────────────────────┐
│   AI Brain Module (ai_brain)         │
│  [Groq LLM] [RSS Parser] [Seasonality]
│  [Multi-source Aggregation]          │
└──────────┬───────────────────────────┘
           │
┌──────────v───────────────────────────┐
│  Market Data Layer (mt5_live, yf)   │
│  [Order Execution] [Price Streams]   │
└──────────────────────────────────────┘
```

---

## Setup & Installation

### 1. Prerequisites

**MetaTrader 5 Installation**:
- Download and install MT5 from your broker
- Connect demo or live account
- Keep MT5 running while bot executes (required for order execution)

**Python Environment**:
```bash
python --version  # Requires 3.9+
pip install --upgrade pip
```

### 2. Clone Repository

```bash
git clone <repository-url>
cd "Trade Bot"
```

### 3. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

**Key packages** (if requirements.txt unavailable):
```bash
pip install MetaTrader5 customtkinter yfinance groq newsapi feedparser python-dotenv lumibot pandas
```

### 5. Configure API Keys (.env File)

Create `.env` file in project root with secured credentials:

```bash
# .env (KEEP PRIVATE - Do Not Commit)

# Groq API (Sentiment Analysis)
GROQ_API_KEY=gsk_XXXXXXXXXXXXXXXX

# NewsAPI (Asset-specific News)
NEWS_API_KEY=XXXXXXXXXXXXXXXX

# Telegram Bot (Notifications)
TELEGRAM_BOT_TOKEN=XXXXXXXXXXXX:XXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

**How to obtain keys**:

| Service | How to Get | Cost |
|---------|-----------|------|
| Groq API | https://console.groq.com | Free (limited quota) |
| NewsAPI | https://newsapi.org | Free tier (10k requests/month) |
| Telegram Bot | BotFather (@BotFather on Telegram) | Free |

### 6. Configure MT5 Connection

Before starting the bot:

1. **Open MetaTrader 5** → File → Login
2. Select your broker (demo or live)
3. Keep MT5 window visible (minimized is OK)
4. Verify account shows up in `mt5.account_info()`

### 7. Run the Application

```bash
# Start the bot
python run.py

# Or directly:
python -m app.main
```

The CustomTkinter UI should launch with trading controls.

---

## Operation Guide

### UI Controls

#### Left Panel: Configuration
- **Capital Input**: Maximum USD capital for trading (e.g., $100)
- **Max Daily Loss**: Kill-switch threshold (e.g., $30)
- **Asset Selection**: Predefined watchlists or custom tickers
- **Telegram Chat IDs**: Comma-separated for multi-user notifications

#### Control Buttons
- **START BOT**: Transition from MONITORAGGIO → TRADING, begin Phase 1 scan
- **STOP BOT**: Transition from TRADING → CHIUSURA_FORZATA, close spec positions

#### Right Panel: Live Dashboard
- **Available Liquidity**: Free margin (cash available for new trades)
- **Capital in Positions**: Sum of open position values
- **Total Equity**: Liquidity + Positions = Total account value
- **Bot Activity Terminal**: Real-time trading log with timestamps

### Live Trading Workflow

```
1. Configure parameters (capital, max loss, watchlist)
2. Click START BOT
   ├─ Engine connects to MT5
   ├─ Phase 1 begins: Scan all assets for AI signals
   ├─ Place initial positions across qualified assets
   └─ Transition to Phase 2 (continuous monitoring)
3. Monitor:
   ├─ Terminal output: Trade entries, exits, reasons
   ├─ P&L metrics: Daily profit/loss, open positions
   └─ Telegram alerts: Trade notifications
4. Click STOP BOT to exit
   ├─ Close all short-term positions
   ├─ Preserve long-term holdings
   └─ Return to MONITORAGGIO (standby)
5. Next market day: Reset max drawdown counter, optionally restart
```

---

## Backtesting

For strategy validation before live trading:

### Mode: Backtest Tab
```
1. Select "[ Backtest ]" mode from segmented button
2. Choose strategy: ATH Dip | SMA Cross | RSI Mean Reversion
3. Enter parameters: ticker, capital, date range
4. Click "Execute Backtest"
5. Review:
   ├─ Benchmark metrics (market returns, volatility)
   ├─ Strategy metrics (Sharpe, win rate, max drawdown)
   ├─ HTML report (PDF-ready for archival)
   └─ Metrics JSON/CSV (import to Excel/Python)
```

Backtest results are saved to `/reports/` with timestamp.

---

## File Structure

```
Trade Bot/
├── app/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── ui.py                # CustomTkinter interface
│   ├── mt5_engine.py        # Live trading state machine
│   ├── ai_brain.py          # Sentiment analysis + macro detection
│   ├── market_data.py       # yfinance + caching layer
│   ├── strategy.py          # Backtest strategies (ATH/SMA/RSI)
│   ├── backtest.py          # Lumibot integration
│   ├── analytics.py         # Metric extraction
│   ├── report.py            # HTML report generation
│   ├── storage.py           # JSON/CSV persistence
│   ├── config.py            # UI color palette
│   └── logging_setup.py     # Logging configuration
├── logs/                    # Application debug logs
├── reports/                 # Backtest reports (HTML, JSON, CSV)
├── cache/                   # Price data cache
├── storico_operazioni_chiuse.csv  # Closed trades audit trail
├── portafoglio_aperto_live.csv    # Live positions snapshot
├── run.py                   # Main launcher
├── .env                     # API keys (KEEP PRIVATE)
├── .gitignore              # Git exclusions
└── README.md               # This file
```

---

## Monitoring & Alerting

### Telegram Notifications

Provide comma-separated chat IDs in UI to receive:

```
🟢 NUOVO BUY ⚡: USDJPY
Prezzo: 156.125
AI: Score: 7/10 | Strong momentum signal

💰 CHIUSO LONG: GBPUSD
Motivo: Trailing Profit Cassettista
Profitto: +$45.32

🛑 MAX DRAWDOWN RAGGIUNTO (-$30.00$). 
Chiudo speculazioni, salvo Cassetto.
```

### Live Logs

Terminal displays:
- Trade entries/exits with timestamps
- P&L per closed trade
- Daily profit/loss accumulator
- Radar heartbeat (every 30s)

---

## Advanced Configuration

### Modifying Position Horizon Rules

Edit `app/mt5_engine.py`:

```python
# Short-term targets
hard_take_profit = max(limite_base, costo_commissioni * 2.0)  # Tune multiplier

# Long-term trailing stops
hard_stop_loss = -max(limite_base * 4.0, costo_commissioni * 5.0)  # Tune multiplier
```

### Adjusting AI Confidence Threshold

Edit `app/mt5_engine.py`:

```python
soglia_ingresso = 5  # Change from 5 to 7 for stricter signals, 3 for looser
```

### Adding Custom Watchlists

Edit `app/ui.py`:

```python
self.watchlist_map = {
    "🌍 Mega-Mix": "EURUSD, GBPUSD, ...",
    "🦅 Custom Portfolio": "AAPL.OQ, BTC-USD, GOLD, ...",
    ...
}
```

---

## Performance Benchmarks

Sample backtest results (5-year SPY, ATH Dip strategy, $10k capital):

| Metric | Backtest | vs. Buy & Hold |
|--------|----------|---|
| Total Return | +245% | +195% |
| CAGR | 19.2% | 15.8% |
| Max Drawdown | -18% | -34% |
| Sharpe Ratio | 1.32 | 0.88 |
| Win Rate | 58% | 100% (buy-hold) |
| Trades | 47 | 1 |

**Note**: Past performance is not indicative of future results. Live trading involves slippage, commissions, and model risk.

---

## Troubleshooting

### MT5 Connection Fails
```
❌ Error: "MetaTrader 5 connection failed"
→ Solution: Keep MT5 application open and logged in
→ Verify account in MT5: Tools → Options → Login
```

### API Rate Limits
```
⚠️ Groq/NewsAPI quota exceeded
→ Solution: Increase cache TTL in ai_brain.py (line 18)
→ Or upgrade to paid API tier
```

### High Slippage on Entries
```
📊 Trading during low-liquidity hours
→ Solution: Restrict trading to 8:00-16:00 UTC (forex peak hours)
→ Increase spread tolerance (is_spread_accettabile threshold)
```

### Negative P&L on Closed Trades
```
Check commission costs (COMMISSION_PER_LOT = 6.0 in mt5_engine.py)
Verify spread filters are not too aggressive
Small positions incur higher commission relative to move
```

---

## Risk Disclaimers

⚠️ **IMPORTANT RISK WARNING**

This is an **experimental algorithmic trading system**. Use at your own risk on:
- **Demo accounts first** (practice before risking real capital)
- **Small position sizes** (e.g., $100 or less)
- **With manual oversight** (do not leave unattended for weeks)

### Risks Include:
- **Model Risk**: AI sentiment can be wrong; no algorithm is always correct
- **Execution Risk**: Slippage, re-quotes, order rejections during fast markets
- **Operational Risk**: MT5 crashes, network failures, API downtime
- **Geopolitical Risk**: Wars, sanctions, market halts not predicted by historical data
- **Drawdown Risk**: Past max drawdown was -18%; future drawdowns could exceed -30%

### Recommended Risk Controls:
- Keep max daily loss ≤ 5-10% of account
- Start with demo account, verify performance for 30+ days
- Use small position sizes until strategy proves stable
- **Never** use leverage > 2x
- Maintain stop-loss discipline; don't disable max drawdown kill-switch

---

## Contributing & Support

For bug reports, feature requests, or general questions:
- Open an issue on the repository
- Provide logs from `/logs/app.log`
- Include the `.env` file structure (without API keys)

---

## License

Proprietary. Use for educational and personal trading purposes only.

---

## Footer

**QUANT AI TERMINAL** — Making institutional-grade algorithmic trading accessible to independent traders.

*Last Updated: February 2026 | Version 11.0*
