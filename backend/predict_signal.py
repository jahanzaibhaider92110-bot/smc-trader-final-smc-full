# path: backend/predict_signal.py
from datetime import datetime
from db import SessionLocal, Signal
import pandas as pd
import json
import joblib
import os
import ccxt
import traceback

# Model paths (adjust if your project uses different locations)
BASE_DIR = os.path.dirname(__file__)
MODEL_5M = os.path.join(BASE_DIR, "models", "smc_model_5m.pkl")
MODEL_FALLBACK = os.path.join(BASE_DIR, "models", "smc_model.pkl")
MODEL_PATHS = [MODEL_5M, MODEL_FALLBACK, os.path.join(os.path.dirname(BASE_DIR), "models", "smc_model_5m.pkl"), os.path.join(os.path.dirname(BASE_DIR), "models", "smc_model.pkl")]

def load_model():
    for p in MODEL_PATHS:
        if os.path.exists(p):
            try:
                m = joblib.load(p)
                print("✅ Loaded model:", p)
                return m
            except Exception as e:
                print("⚠️ Model load error:", p, e)
    print("⚠️ No model found. ML disabled.")
    return None

def features_from_candles(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy().reset_index(drop=True)
    last = df.iloc[-1]
    try:
        # try to import atr from smc_filters if exists
        from smc_filters import atr
        a = atr(df)
    except Exception:
        a = 0.0
    feat = {
        "open": last["open"],
        "high": last["high"],
        "low": last["low"],
        "close": last["close"],
        "volume": last.get("volume", 0),
        "atr": a
    }
    return pd.DataFrame([feat])

# load model once for faster repeated calls (thread/process safety: safe enough for small workloads)
_GLOBAL_MODEL = load_model()

# function that contains the pipeline: returns saved signal dict OR None
def predict_from_candles(candles: pd.DataFrame, symbol="BTC/USDT", timeframe="5m", require_smc=True):
    """
    Uses loaded model + SMC confirmation to decide and SAVE a signal if valid.
    Returns saved signal dict (same shape as API returns) or None.
    """
    try:
        model = _GLOBAL_MODEL
        features = features_from_candles(candles)
    except Exception as e:
        print("feature extraction failed:", e)
        return None

    ml_label, confidence = None, 0.0
    if model is not None:
        try:
            proba = model.predict_proba(features)[0]
            ml_label = int(model.predict(features)[0])
            confidence = float(max(proba))
        except Exception as e:
            print("ML predict error:", e)

    # if no ML label, abort
    if ml_label is None:
        return None

    # generate side and minimal signal dict
    side = "BUY" if ml_label == 1 else "SELL"
    signal_stub = {"type": "long" if ml_label == 1 else "short", "index": len(candles)-1}

    # SMC confirm: call the project smc_confirm from smc_filters if available
    try:
        from smc_filters import smc_confirm, compute_sl_tp
    except Exception:
        smc_confirm = None
        compute_sl_tp = None

    # Confirm via SMC if function provided
    confirmed = {}
    if smc_confirm:
        try:
            out = smc_confirm(candles, signal_stub)
            if isinstance(out, dict):
                confirmed = out
            else:
                # boolean fallback
                confirmed = {"smc_confirmed": bool(out), "atr": 0.0, "order_block": None}
        except Exception as e:
            print("smc_confirm error:", e)
            confirmed = {"smc_confirmed": False, "atr": 0.0, "order_block": None}
    else:
        # If smc_confirm missing, do not confirm (strict)
        confirmed = {"smc_confirmed": False, "atr": 0.0, "order_block": None}

    if require_smc and not confirmed.get("smc_confirmed", False):
        # strict mode: require SMC confirmation
        print("Rejected: not SMC confirmed")
        return None

    entry = float(candles['close'].iloc[-1])
    atr_val = confirmed.get("atr", 0.0)
    ob = confirmed.get("order_block")

    # compute SL/TP (use compute_sl_tp if exists, else fallback simple RR=2)
    if compute_sl_tp:
        try:
            sl, tp = compute_sl_tp(entry, side, ob, atr_val, prefer_rr=2.0)
        except Exception:
            # fallback safe SL/TP
            sl = entry - atr_val*1.0 if side == "BUY" else entry + atr_val*1.0
            tp = entry + (entry - sl)*2 if side == "BUY" else entry - (sl - entry)*2
    else:
        sl = entry - atr_val*1.0 if side == "BUY" else entry + atr_val*1.0
        tp = entry + (entry - sl)*2 if side == "BUY" else entry - (sl - entry)*2

    # move potential check (use absolute difference in price)
    move = abs(tp - entry)
    # translate to "points" vs pip size? assume BTC price units (user earlier used MIN_MOVE_POINTS=150)
    # We adhere to the project's existing MIN_MOVE_PIPS by not relaxing threshold.
    MIN_MOVE_POINTS = 150.0
    if move < MIN_MOVE_POINTS:
        print(f"Rejected: move potential {move} < required {MIN_MOVE_POINTS}")
        return None

    # Save to DB (only if passed all conditions)
    try:
        db = SessionLocal()
        sig = Signal(
            symbol=symbol.replace("/", ""),
            timeframe=timeframe,
            side=side.lower(),
            entry=float(entry),
            stop_loss=float(sl),
            take_profit=float(tp),
            rr=float(abs((tp - entry) / (entry - sl) if (entry - sl) != 0 else 0.0)),
            ml_label=int(ml_label),
            confidence=float(confidence),
            reason="SMC+ML",
            raw_data=json.dumps({"confirmed": confirmed}),
            smc_confirmed=bool(confirmed.get("smc_confirmed", False)),
            created_at=datetime.utcnow()
        )
        db.add(sig)
        db.commit()
        db.refresh(sig)
        saved = {
            "id": sig.id,
            "symbol": sig.symbol,
            "timeframe": sig.timeframe,
            "side": sig.side,
            "entry": sig.entry,
            "stop_loss": sig.stop_loss,
            "take_profit": sig.take_profit,
            "rr": sig.rr,
            "ml_label": sig.ml_label,
            "confidence": sig.confidence,
            "reason": sig.reason,
            "smc_confirmed": sig.smc_confirmed,
            "created_at": sig.created_at.isoformat()
        }
        db.close()
        print("✅ Saved signal to DB:", saved)
        return saved
    except Exception as e:
        print("DB save error:", e)
        traceback.print_exc()
        try:
            db.close()
        except:
            pass
        return None


# helper to fetch candles (ccxt)
def fetch_candles(symbol="BTC/USDT", timeframe="5m", limit=500):
    try:
        exchange = ccxt.binance()
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.set_index("timestamp")
        return df
    except Exception as e:
        print("fetch_candles error:", e)
        return None

# -------------------------
# RUNNER used by scheduler
# returns saved dict OR None
def run_prediction(symbol="BTC/USDT", timeframe="5m"):
    try:
        candles = fetch_candles(symbol, timeframe, limit=500)
        if candles is None or candles.empty:
            print("No candles fetched")
            return None
        return predict_from_candles(candles, symbol=symbol, timeframe=timeframe, require_smc=True)
    except Exception as e:
        print("run_prediction error:", e)
        traceback.print_exc()
        return None

# Allow running manually
if __name__ == "__main__":
    res = run_prediction()
    print("run_prediction result:", res)
