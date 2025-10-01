import pandas as pd

def detect_inducement(df: pd.DataFrame, tolerance=0.1):
    """
    Detect equal highs/lows and inducement wicks.
    """
    signals = []
    for i in range(2, len(df)):
        # Equal highs inducement
        if abs(df.iloc[i-1]['high'] - df.iloc[i-2]['high']) <= tolerance:
            if df.iloc[i]['high'] > df.iloc[i-1]['high']:
                signals.append({"index": i, "type": "inducement_high"})

        # Equal lows inducement
        if abs(df.iloc[i-1]['low'] - df.iloc[i-2]['low']) <= tolerance:
            if df.iloc[i]['low'] < df.iloc[i-1]['low']:
                signals.append({"index": i, "type": "inducement_low"})
    return signals
