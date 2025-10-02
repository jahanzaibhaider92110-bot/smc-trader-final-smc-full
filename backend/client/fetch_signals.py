import time
import requests

# Backend API ka URL
BACKEND_URL = "http://127.0.0.1:8000/signals"  # FastAPI server

def fetch_signal():
    try:
        # GET request bhejna backend ke /signals endpoint pe
        r = requests.get(BACKEND_URL, params={"symbol": "BTC/USDT", "timeframe": "1m"})
        
        if r.status_code == 200:
            data = r.json()
            sig = data.get("signal", {})

            # Output ko readable format me print karna
            print("📊 Latest Signal:")
            print(f"   Label        : {sig.get('label', '-')}")
            print(f"   Reason       : {sig.get('reason', '-')}")
            print(f"   ML Label     : {sig.get('ml_label', '-')}")
            print(f"   Confidence   : {sig.get('ml_confidence', '-')}")
            print(f"   Created_at   : {sig.get('created_at', '-')}")
            print("-" * 50)
        else:
            print("⚠️ Error:", r.text)
    except Exception as e:
        print("❌ Exception:", e)
