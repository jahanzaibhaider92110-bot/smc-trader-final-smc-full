"""
Enhanced SMC engine (ATR + EMA filter + TP/SL realistic)
"""

import pandas as pd
import numpy as np
from typing import Dict
from ta.volatility import AverageTrueRange
from ta.trend import EMAIndicator


def generate_signal(df: pd.DataFrame) -> Dict:
    try:
        # Required columns check
        req = ["open", "high", "low", "close"]
        for c in req:
            if c not in df.columns:
                raise ValueError(f"Missing column: {c}")

        latest_idx = len(df) - 1
        close = df["close"].iloc[-1]

        # Indicators
        atr = AverageTrueRange(
            high=df["high"], low=df["low"], close=df["close"], window=14
        ).average_true_range()
        atr_val = atr.iloc[-1]

        ema200 = EMAIndicator(close=df["close"], window=200).ema_indicator()
        ema_val = ema200.iloc[-1]

        # Direction check (simple rule: bullish if close > prev high, bearish if close < prev low)
        signal = "none"
        if df["close"].iloc[-1] > df["high"].iloc[-2]:
            signal = "buy"
        elif df["close"].iloc[-1] < df["low"].iloc[-2]:
            signal = "sell"

        entry = close
        sl, tp = None, None

        if signal == "buy":
            if close < ema_val:  # ❌ Filter: price must be above EMA200
                return {"signal": "none", "entry": None, "stop_loss": None, "take_profits": []}

            sl = entry - atr_val
            tp = entry + 2 * atr_val

        elif signal == "sell":
            if close > ema_val:  # ❌ Filter: price must be below EMA200
                return {"signal": "none", "entry": None, "stop_loss": None, "take_profits": []}

            sl = entry + atr_val
            tp = entry - 2 * atr_val

        # ❌ Skip if TP < 150 points
        if tp is not None and abs(tp - entry) < 150:
            return {"signal": "none", "entry": None, "stop_loss": None, "take_profits": []}

        return {
            "signal": signal,
            "entry": float(round(entry, 2)) if entry else None,
            "stop_loss": float(round(sl, 2)) if sl else None,
            "take_profits": [float(round(tp, 2))] if tp else [],
        }

    except Exception as e:
        return {
            "signal": "error",
            "entry": None,
            "stop_loss": None,
            "take_profits": [],
            "error": str(e),
        }
