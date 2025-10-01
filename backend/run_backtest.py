"""
Backtest runner for SMC engine
"""

import pandas as pd
import ccxt
import sys
from pathlib import Path

# Add backend folder to Python path
sys.path.append(str(Path(__file__).resolve().parent))

from smc.smc_engine import generate_signal


# -------------------------------
# Binance se candles fetch karna
# -------------------------------
def fetch_binance_data(symbol="BTC/USDT", timeframe="5m", limit=500):
    exchange = ccxt.binance()
    print(f"⏳ Fetching {symbol} {timeframe} candles from Binance...")
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    print(f"✅ Got {len(df)} candles")
    return df


# -------------------------------
# Filter trades with TP >= 150
# -------------------------------
def filter_trades(trades, min_tp=150):
    filtered = []
    for t in trades:
        if t.get("signal") in ["buy", "sell"] and t.get("take_profits"):
            tp_points = abs(t["take_profits"][0] - t["entry"])
            if tp_points >= min_tp:
                t["profit"] = tp_points
                filtered.append(t)
    return filtered


# -------------------------------
# Backtest runner
# -------------------------------
def run_backtest(symbol="BTC/USDT", timeframe="5m", limit=500):
    df = fetch_binance_data(symbol, timeframe, limit)

    trades = []
    print("🔍 Generating signals...")

    for i in range(200, len(df)):  # skip first 200 for EMA warmup
        window = df.iloc[: i + 1]
        try:
            sig = generate_signal(window)
            if sig and sig["signal"] in ["buy", "sell"] and sig.get("entry"):
                sig["index"] = i
                trades.append(sig)
        except Exception as e:
            print(f"⚠️ Error at index {i}: {e}")

    # Filter valid trades
    trades = filter_trades(trades)

    # Summary
    print(f"\n📊 Backtest finished")
    print(f"Total trades: {len(trades)}")
    if trades:
        df_trades = pd.DataFrame(trades)
        df_trades.to_csv("backtest_results.csv", index=False)
        print("✅ Saved results to backtest_results.csv")


# -------------------------------
# Main
# -------------------------------
if __name__ == "__main__":
    run_backtest("BTC/USDT", "5m", limit=500)
