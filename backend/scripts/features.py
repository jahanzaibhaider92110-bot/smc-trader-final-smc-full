"""
scripts/features.py
Takes a OHLCV parquet and label parquet and produces feature table for model training.
"""
import pandas as pd, numpy as np, os, sys
try:
    from ta.volatility import AverageTrueRange
except Exception:
    AverageTrueRange = None

def add_features(df):
    df = df.copy().reset_index(drop=True)
    df['r1'] = df['close'].pct_change(1)
    df['r3'] = df['close'].pct_change(3)
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    if AverageTrueRange is not None:
        df['atr'] = AverageTrueRange(df['high'], df['low'], df['close'], window=14).average_true_range()
    else:
        df['atr'] = df['high'] - df['low']
    df['body'] = (df['close'] - df['open']).abs()
    df['upper_wick'] = df['high'] - df[['close','open']].max(axis=1)
    df['lower_wick'] = df[['close','open']].min(axis=1) - df['low']
    df['vol_spike'] = (df['volume'] > df['volume'].rolling(20).mean()*2).astype(int)
    return df.dropna()

if __name__ == "__main__":
    if len(sys.argv)<4:
        print("Usage: python features.py in.parquet labels.parquet out_features.parquet")
        sys.exit(1)
    inp, labels, out = sys.argv[1], sys.argv[2], sys.argv[3]
    df = pd.read_parquet(inp)
    lab = pd.read_parquet(labels)
    df = df.sort_values('ts').reset_index(drop=True)
    lab = lab.sort_values('ts').reset_index(drop=True)
    df_feat = add_features(df)
    merged = pd.merge_asof(lab.sort_values('ts'), df_feat.sort_values('ts'), on='ts')
    merged.to_parquet(out)
    print("Saved features to", out)