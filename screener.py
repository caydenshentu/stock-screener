#!/usr/bin/env python3
"""
Stock Screener — Cayden's Summer AI Project
Filters stocks by fundamental & technical criteria using yfinance.

Usage:
  screener.py --min-price 100 --max-pe 25            # bargain large-caps
  screener.py --min-volume 10 --min-change 2          # active gainers
  screener.py --sector Technology                     # all tech stocks
  screener.py --min-target 20                         # analyst darlings
  screener.py --sp500 --min-market-cap 10 --limit 20  # S&P 500 mid+ large
"""

import argparse
import sys
import time
from dataclasses import dataclass
from typing import Optional

import yfinance as yf
import pandas as pd

pd.set_option("display.max_rows", 200)
pd.set_option("display.width", 260)
pd.set_option("display.max_columns", 20)
pd.set_option("display.float_format", lambda x: f"{x:,.1f}" if abs(x) >= 1000 else f"{x:.2f}")


# ── Default universe (90+ tickers across sectors) ──────────────────────
DEFAULT_TICKERS = [
    # Tech
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AVGO", "ORCL",
    "ADBE", "CRM", "INTC", "AMD", "IBM", "CSCO", "QCOM", "TXN", "NOW",
    "UBER", "SNOW", "PLTR", "DDOG",
    # Financials
    "JPM", "BAC", "GS", "MS", "V", "MA", "BLK", "C", "WFC", "AXP", "SCHW",
    # Healthcare
    "UNH", "JNJ", "PFE", "MRK", "ABBV", "LLY", "TMO", "ABT", "BMY", "AMGN",
    # Consumer
    "WMT", "COST", "HD", "MCD", "NKE", "SBUX", "DIS", "LOW", "TGT", "KO",
    "PEP", "PG", "PM", "MO",
    # Energy & Industrials
    "XOM", "CVX", "COP", "CAT", "GE", "BA", "HON", "UPS", "UNP", "RTX",
    # Communication & Media
    "NFLX", "CMCSA", "T", "VZ", "TMUS", "CHTR",
    # Real Estate
    "PLD", "AMT", "CCI", "EQIX", "PSA",
    # High-growth / crypto-adjacent
    "SQ", "ROKU", "SHOP", "RIVN", "HOOD", "COIN", "MSTR",
]

SP500_FALLBACK = DEFAULT_TICKERS


# ── Filter parameters ───────────────────────────────────────────────────
@dataclass
class Filters:
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_market_cap: Optional[float] = None
    max_market_cap: Optional[float] = None
    min_pe: Optional[float] = None
    max_pe: Optional[float] = None
    min_volume: Optional[float] = None
    min_dividend: Optional[float] = None
    max_dividend: Optional[float] = None
    sector: Optional[str] = None
    min_change: Optional[float] = None
    max_change: Optional[float] = None
    min_target: Optional[float] = None
    limit: int = 30
    sp500: bool = False
    verbose: bool = False


def parse_args() -> Filters:
    p = argparse.ArgumentParser(
        description="Stock Screener — filter stocks by fundamentals & technicals",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--min-price", type=float)
    p.add_argument("--max-price", type=float)
    p.add_argument("--min-market-cap", type=float, help="Min market cap in $B")
    p.add_argument("--max-market-cap", type=float, help="Max market cap in $B")
    p.add_argument("--min-pe", type=float, help="Min P/E ratio")
    p.add_argument("--max-pe", type=float, help="Max P/E ratio")
    p.add_argument("--min-volume", type=float, help="Min daily volume in millions")
    p.add_argument("--min-dividend", type=float, help="Min dividend yield %")
    p.add_argument("--max-dividend", type=float, help="Max dividend yield %")
    p.add_argument("--sector", type=str, help="Sector filter (e.g. Technology, Healthcare)")
    p.add_argument("--min-change", type=float, dest="min_change",
                    help="Min daily change %")
    p.add_argument("--max-change", type=float, dest="max_change",
                    help="Max daily change %")
    p.add_argument("--min-target", type=float, help="Min analyst target upside %")
    p.add_argument("--limit", type=int, default=30, help="Max results (default: 30)")
    p.add_argument("--sp500", action="store_true", help="Use S&P 500 constituents")
    p.add_argument("--verbose", "-v", action="store_true", help="Show progress detail")
    return p.parse_args(namespace=Filters())


# ── Helpers ─────────────────────────────────────────────────────────────
def log(msg: str, verbose: bool = False):
    print(f"[~] {msg}", file=sys.stderr)


def fetch_snp500() -> list[str]:
    """Get current S&P 500 members from Wikipedia."""
    try:
        tables = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
        sp = tables[0]["Symbol"].str.replace(".", "-", regex=False).tolist()
        if sp:
            log(f"Loaded {len(sp)} S&P 500 constituents")
            return sp
    except Exception as e:
        log(f"Could not fetch S&P 500 list: {e}")
    return SP500_FALLBACK


# ── Core screening ──────────────────────────────────────────────────────
def screen(tickers: list[str], filters: Filters) -> pd.DataFrame:
    # Step 1: Batch download price history (most reliable data source)
    log(f"Downloading prices for {len(tickers)} tickers...")
    prices = yf.download(
        tickers, period="5d", auto_adjust=True, progress=False, threads=True
    )

    # Step 2: Fetch fundamentals one ticker at a time (rate-limited)
    log("Fetching fundamentals...")

    rows = []
    errors = 0
    total = len(tickers)

    for i, t in enumerate(tickers):
        if filters.verbose and (i + 1) % 10 == 0:
            log(f"Progress: {i+1}/{total}")

        try:
            # Get last 2 closes for change%
            close = prices["Close"][t] if isinstance(prices["Close"], pd.DataFrame) else prices["Close"]
            close_vals = close.dropna().tail(2).values

            if len(close_vals) < 2:
                errors += 1
                continue

            prev_close, latest_close = close_vals[0], close_vals[-1]
            change_pct = ((latest_close - prev_close) / prev_close) * 100

            price = float(latest_close)

            # ── Price filter (uses reliable yf.download data) ──
            if filters.min_price and price < filters.min_price:
                continue
            if filters.max_price and price > filters.max_price:
                continue

            # ── Fundamentals from .info (less reliable, handle gracefully) ──
            info = yf.Ticker(t).info
            if not info:
                errors += 1
                continue

            mcap = info.get("marketCap")
            mcap_b = mcap / 1e9 if mcap and mcap > 0 else None

            if filters.min_market_cap and (mcap_b is None or mcap_b < filters.min_market_cap):
                continue
            if filters.max_market_cap and (mcap_b is None or mcap_b > filters.max_market_cap):
                continue

            pe = info.get("trailingPE") or info.get("forwardPE")
            if pe is not None and pe < 0:
                pe = None  # negative P/E = meaningless
            if filters.min_pe and (pe is None or pe < filters.min_pe):
                continue
            if filters.max_pe and (pe is None or pe > filters.max_pe):
                continue

            vol = info.get("volume") or info.get("averageVolume")
            vol_m = vol / 1e6 if vol else None
            if filters.min_volume and (vol_m is None or vol_m < filters.min_volume):
                continue

            div = info.get("dividendYield")
            div_pct = div * 100 if div else 0.0
            if filters.min_dividend is not None and div_pct < filters.min_dividend:
                continue
            if filters.max_dividend is not None and div_pct > filters.max_dividend:
                continue

            sector = info.get("sector", "")
            if filters.sector and sector.lower() != filters.sector.lower():
                continue

            # ── Change % filter (from reliable price data) ──
            if filters.min_change is not None and change_pct < filters.min_change:
                continue
            if filters.max_change is not None and change_pct > filters.max_change:
                continue

            # Analyst target upside
            target = info.get("targetMeanPrice")
            upside = None
            if target and price and target > 0:
                upside = ((target - price) / price) * 100
            if filters.min_target is not None and (upside is None or upside < filters.min_target):
                continue

            rows.append({
                "Ticker": t,
                "Price": price,
                "Chg%": change_pct,
                "MktCap($B)": mcap_b,
                "P/E": pe,
                "Vol(M)": vol_m,
                "Div%": div_pct,
                "Sector": sector,
                "Target↑": upside,
            })

            # Rate-limit info lookups to avoid DNS thrashing
            time.sleep(0.15)

        except Exception as e:
            errors += 1
            if filters.verbose:
                log(f"Error on {t}: {e}")
            continue

    if errors:
        log(f"{errors}/{total} tickers had errors (skipped)")

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    # Sort by market cap descending
    if "MktCap($B)" in df.columns:
        df = df.sort_values("MktCap($B)", ascending=False).reset_index(drop=True)
    return df.head(filters.limit)


# ── Main ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    filters = parse_args()
    tickers = fetch_snp500() if filters.sp500 else DEFAULT_TICKERS

    df = screen(tickers, filters)

    if df.empty:
        print("\n❌ No stocks matched your criteria.")
        sys.exit(0)

    print(f"\n📊 {len(df)} stocks matched:\n")
    print(df.to_string(index=False))
    print(f"\n{'─' * 80}")
    print(f"💡 Tip: try --min-change 2     (hot movers)")
    print(f"         --max-pe 20 --min-div 1  (value + dividend)")
    print(f"         --sector Healthcare       (sector focus)")
    print(f"         --min-target 20           (analyst picks)")
