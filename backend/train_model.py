
# retrain_model.py

import pandas as pd
import ccxt
import pickle
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# ------------------------------
# ATR Calculation Helper
# ------------------------------
def atr(df, period=14):
    df["h-l"] = df["high"] - df["low"]
    df["h-c"] = abs(df["high"] - df["close"].shift())
    df["l-c"] = abs(df["low"] - df["close"].shift())
    tr = df[["h-l", "h-c", "l-c"]].max(axis=1)
    return tr.rolling(period).mean().iloc[-1]

# ------------------------------
# Data Fetch
# ------------------------------
exchange = ccxt.binance()
symbol = "BTC/USDT"
timeframe = "5m"

print(f"Fetching data for {symbol} - {timeframe}")
candles = exchange.fetch_ohlcv(symbol, timeframe, limit=500)
df = pd.DataFrame(candles, columns=["timestamp","open","high","low","close","volume"])
df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

# ------------------------------
# Features (same as predict_signal.py)
# ------------------------------
df["atr"] = df.apply(lambda row: atr(df), axis=1)

features = ["open", "high", "low", "close", "volume", "atr"]
df = df.dropna()

# Target bana lo (simple logic: next candle close > current close → BUY else SELL)
df["target"] = (df["close"].shift(-1) > df["close"]).astype(int)

X = df[features]
y = df["target"]

# ------------------------------
# Train-Test Split
# ------------------------------
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

# ------------------------------
# Train Model
# ------------------------------
print("Training model with features:", features)
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# ------------------------------
# Evaluate
# ------------------------------
y_pred = model.predict(X_test)
print("\nClassification Report:\n", classification_report(y_test, y_pred))

# ------------------------------
# Save Model
# ------------------------------
with open("models/smc_model.pkl", "wb") as f:
    pickle.dump(model, f)

print("✅ Model retrained and saved at models/smc_model.pkl with ATR feature")


