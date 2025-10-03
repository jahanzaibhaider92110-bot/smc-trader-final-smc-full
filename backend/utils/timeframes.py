import pandas as pd

def resample_timeframe(df, timeframe="15T"):
    """
    Resample OHLCV dataframe to given timeframe.
    df must have datetime index.
    """
    ohlc_dict = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }
    return df.resample(timeframe).apply(ohlc_dict).dropna()


def confirm_with_htf(df_15m, df_1h, signal_direction):
    """
    Confirm 5m signal with HTF (15m, 1h).
    Simple logic: if trend direction matches on both HTF, confirm true.
    """
    try:
        last15 = df_15m.iloc[-1]
        last1h = df_1h.iloc[-1]

        if signal_direction == "long":
            return last15["close"] > last15["open"] and last1h["close"] > last1h["open"]
        elif signal_direction == "short":
            return last15["close"] < last15["open"] and last1h["close"] < last1h["open"]
        else:
            return False
    except Exception:
        return False
