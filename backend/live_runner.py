import time
import os

while True:
    print("🔄 Running prediction...")
    os.system("python backend/predict_signal.py --symbol BTCUSDT --timeframe 5m")
    print("⏳ Waiting 300 seconds (5 minutes)...")
    time.sleep(300)  # 5 minutes wait
