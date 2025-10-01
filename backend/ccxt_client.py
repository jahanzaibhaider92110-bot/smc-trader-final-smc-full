import ccxt
import os
from dotenv import load_dotenv
load_dotenv()
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET')
def get_binance_client():
    exchange = ccxt.binance({
        'apiKey': BINANCE_API_KEY or '',
        'secret': BINANCE_API_SECRET or '',
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    })
    return exchange
def fetch_ohlcv(symbol='BTC/USDT', timeframe='1m', limit=200):
    client = get_binance_client()
    try:
        ohlcv = client.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        return ohlcv
    except Exception as e:
        print('ccxt fetch error:', e)
        return []
