"""
scripts/backtest.py - simplified backtest applying signals to price series
Usage: python backtest.py features.parquet model.txt
"""
import pandas as pd, numpy as np, sys
import lightgbm as lgb

if len(sys.argv) < 3:
    print("Usage: python backtest.py features.parquet model.txt")
    sys.exit(1)

feat_file = sys.argv[1]; model_file = sys.argv[2]
df = pd.read_parquet(feat_file).dropna().reset_index(drop=True)
model = lgb.Booster(model_file=model_file)
feature_cols = [c for c in df.columns if c not in ('ts','label','signal','reason')]
X = df[feature_cols].values
probs = model.predict(X)
df['pred_prob'] = probs
entries = df[df['pred_prob'] > 0.6]
print("Entries:", len(entries))
print(entries[['ts','signal','pred_prob','label']].head(20))
# Extend this file to compute PnL using next N bars, TP/SL rules.