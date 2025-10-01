import pandas as pd

def higher_tf_trend(df: pd.DataFrame, ema_period=200):
    """
    Detect higher timeframe trend using EMA.
    """
    df['ema'] = df['close'].ewm(span=ema_period).mean()
    if df.iloc[-1]['close'] > df.iloc[-1]['ema']:
        return "bullish"
    else:
        return "bearish"
