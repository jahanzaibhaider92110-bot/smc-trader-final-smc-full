import os
import json
import requests
from datetime import datetime
import time

# File jisme signals save honge
SIGNAL_FILE = os.path.join("backend", "predictions", "signal.json")

# Backend API ya exchange se price fetch karne ka dummy function
# Abhi ke liye Binance API use karte hain (spot price BTC/USDT)
def get_price_data(symbol="BTCUSDT", limit=50):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit={limit}"
    r = requests.get(url)
    data = r.json()

    closes = [float(c[4]) for c in data]  # close prices
    highs = [float(c[2]) for c in data]   # highs
    lows = [float(c[3]) for c in data]    # lows

    return closes, highs, lows


def detect_swings(highs, lows):
    """Simple swing detection (last 5 candles)"""
    swing_high = max(highs[-5:])
    swing_low = min(lows[-5:])
    return swing_high, swing_low


def generate_signal(symbol, side, price, swing_high, swing_low):
    """Generate signal with SL/TP using SMC logic"""
    if side == "BUY":
        stop_loss = swing_low
        risk = price - stop_loss
        take_profit = price + (risk * 2)  # RR 1:2
    else:  # SELL
        stop_loss = swing_high
        risk = stop_loss - price
        take_profit = price - (risk * 2)

    signal = {
        "symbol": symbol,
        "side": side,
        "entry": round(price, 2),
        "stop_loss": round(stop_loss, 2),
        "take_profit": round(take_profit, 2),
        "confidence": 0.85,
        "timestamp": datetime.utcnow().isoformat()
    }

    # Save as JSON
    os.makedirs(os.path.dirname(SIGNAL_FILE), exist_ok=True)
    with open(SIGNAL_FILE, "w") as f:
        json.dump(signal, f, indent=2)

    print("✅ Signal saved:", signal)
    return signal


if __name__ == "__main__":
    print("🔄 Starting SMC Signal Generator...")

    while True:
        try:
            closes, highs, lows = get_price_data("BTCUSDT", limit=50)
            current_price = closes[-1]

            swing_high, swing_low = detect_swings(highs, lows)

            # Dummy logic: agar price swing_low ke paas hai → BUY, agar swing_high ke paas hai → SELL
            if current_price <= swing_low * 1.01:  
                side = "BUY"
            elif current_price >= swing_high * 0.99:  
                side = "SELL"
            else:
                print("⚠️ No clear SMC signal right now")
                time.sleep(60)
                continue

            generate_signal("BTCUSDT", side, current_price, swing_high, swing_low)

        except Exception as e:
            print("❌ Error:", e)

        time.sleep(60)  # har 1 min baad check karega
