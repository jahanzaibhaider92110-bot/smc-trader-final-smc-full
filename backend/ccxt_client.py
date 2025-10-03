# path: backend/ccxt_client.py
import ccxt
import pandas as pd
import os
from datetime import datetime

API_KEY = os.getenv("BINANCE_API_KEY", None)
API_SECRET = os.getenv("BINANCE_API_SECRET", None)

exchange = ccxt.binance({
    'enableRateLimit': True,
    'apiKey': API_KEY,
    'secret': API_SECRET
})

def fetch_ohlcv_df(symbol="BTC/USDT", timeframe="5m", since=None, limit=500):
    try:
        data = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)
        df = pd.DataFrame(data, columns=['timestamp','open','high','low','close','volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        print("ccxt fetch error:", e)
        return pd.DataFrame(columns=['timestamp','open','high','low','close','volume'])
