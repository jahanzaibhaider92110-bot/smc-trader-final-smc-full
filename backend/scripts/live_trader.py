"""
live_trader.py
Stream Binance 5m candles -> generate signals -> optional trade execution
"""

import asyncio, json, pandas as pd
import websockets
import joblib, os, sys
from datetime import datetime

# Add backend path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from smc.smc_engine import generate_signal
from predict_signal import extract_features, model

# Binance WebSocket (BTCUSDT 5m candles)
BINANCE_WS = "wss://stream.binance.com:9443/ws/btcusdt@kline_5m"

async def listen():
    print("🚀 Listening to Binance 5m candles...")
    async with websockets.connect(BINANCE_WS) as ws:
        async for msg in ws:
            data = json.loads(msg)
            k = data["k"]  # kline payload

            if k["x"]:  # candle closed
                row = {
                    "ts": datetime.fromtimestamp(k["t"]/1000),
                    "open": float(k["o"]),
                    "high": float(k["h"]),
                    "low": float(k["l"]),
                    "close": float(k["c"]),
                    "volume": float(k["v"]),
                }
                df = pd.DataFrame([row])

                # Generate raw SMC signal
                sig = generate_signal(df)

                # ML filter
                feats = extract_features(sig.get("reason", ""))
                pred = model.predict(feats)[0]
                prob = model.predict_proba(feats)[0][1]

                sig["ml_label"] = int(pred)
                sig["ml_confidence"] = float(prob)

                print("📊 Live Signal:", sig)

if __name__ == "__main__":
    asyncio.run(listen())
