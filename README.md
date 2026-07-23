# 📊 Stock Screener

Cayden's summer AI project — screens stocks by fundamentals & technicals using real Yahoo Finance data.

## Quick start

```bash
python3 screener.py                          # see everything
python3 screener.py --limit 10               # top 10 by market cap
python3 screener.py --sector Technology      # tech stocks only
python3 screener.py --min-price 100          # stocks over $100
python3 screener.py --max-pe 20              # cheap by P/E
python3 screener.py --min-dividend 2         # dividend yield >= 2%
python3 screener.py --min-change 2           # today's gainers
python3 screener.py --min-target 20          # analyst darlings (20%+ upside)
```

**Combine them:**
```bash
python3 screener.py --min-price 100 --max-pe 25 --min-dividend 1
python3 screener.py --sector Healthcare --max-pe 30 --min-market-cap 10
```

## What it does

1. Downloads price history for ~85 well-known stocks (or the full S&P 500 with `--sp500`)
2. Fetches fundamentals from Yahoo Finance (market cap, P/E, dividend yield, sector, analyst targets)
3. Filters by whatever criteria you set
4. Ranks results by market cap (biggest first)
5. Spits out a clean table

## How it's built

- **yfinance** — pulls live stock data from Yahoo Finance
- **pandas** — tabular output
- **Pure Python** — no framework, no database, no API keys needed

## Next things to add (ideas)

Once you've played with the basic screener, here's where it gets interesting:

1. **Sector rotator** — which sectors had the best avg return this week?
2. **RSI / momentum screener** — add technical indicators (RSI, MACD, moving averages)
3. **Earnings calendar integration** — screen around earnings dates
4. **Backtesting** — "if I screened for X 6 months ago, how would I have done?"
5. **Watchlist alerts** — email/Discord ping when a stock hits your criteria
6. **Portfolio tracker** — track hypothetical buys and P&L

## File layout

```
stock-screener/
├── screener.py    # main script — run this
└── README.md      # you're here
```

No dependencies beyond `yfinance` and `pandas` — both already installed.
