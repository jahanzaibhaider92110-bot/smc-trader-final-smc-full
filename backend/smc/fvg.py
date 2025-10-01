import pandas as pd

def detect_fvg(df: pd.DataFrame, lookback=50):
    """
    Detect Fair Value Gaps (FVGs) in OHLC data.
    df must have ['open','high','low','close']
    """
    fvg_list = []
    for i in range(2, len(df)):
        prev_low = df.iloc[i-2]['low']
        prev_high = df.iloc[i-2]['high']
        cur_low = df.iloc[i]['low']
        cur_high = df.iloc[i]['high']

        # Bullish FVG
        if prev_high < cur_low:
            fvg_list.append({
                "index": i,
                "type": "bullish",
                "gap": (prev_high, cur_low)
            })

        # Bearish FVG
        if prev_low > cur_high:
            fvg_list.append({
                "index": i,
                "type": "bearish",
                "gap": (cur_high, prev_low)
            })
    return fvg_list
