import pandas as pd

def detect_order_blocks(df: pd.DataFrame, min_size=3):
    """
    Detect simple bullish/bearish order blocks.
    """
    obs = []
    for i in range(len(df)-min_size):
        # Bearish OB = last bullish candle before strong drop
        if df.iloc[i]['close'] > df.iloc[i]['open'] and df.iloc[i+1]['close'] < df.iloc[i+1]['open']:
            obs.append({
                "index": i,
                "type": "bearish",
                "price": df.iloc[i]['open']
            })

        # Bullish OB = last bearish candle before strong rally
        if df.iloc[i]['close'] < df.iloc[i]['open'] and df.iloc[i+1]['close'] > df.iloc[i+1]['open']:
            obs.append({
                "index": i,
                "type": "bullish",
                "price": df.iloc[i]['open']
            })
    return obs
