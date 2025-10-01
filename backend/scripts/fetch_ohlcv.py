"""
scripts/fetch_ohlcv.py
Usage: python scripts/fetch_ohlcv.py SYMBOL TIMEFRAME OUTFILE.parquet
Example: python scripts/fetch_ohlcv.py BTC/USDT 1m data/BTCUSDT_1m.parquet
"""
import ccxt, pandas as pd, sys, os
from pathlib import Path

def fetch_symbol(symbol='BTC/USDT', timeframe='1m', limit=1000, since=None):
    ex = ccxt.binance({'enableRateLimit': True})
    rows = ex.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)
    df = pd.DataFrame(rows, columns=['ts','open','high','low','close','volume'])
    df['ts'] = pd.to_datetime(df['ts'], unit='ms')
    return df

if __name__== "__main__":
    if len(sys.argv) < 4:
        print("Usage: python fetch_ohlcv.py SYMBOL TIMEFRAME OUTPATH")
        sys.exit(1)
    sym = sys.argv[1]; tf = sys.argv[2]; out = sys.argv[3]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    df = fetch_symbol(sym, tf, limit=1000)
    df.to_parquet(out)
    print("Saved:", out)