"""
scripts/train.py - train a LightGBM classifier on features parquet
Usage: python train.py features.parquet model_out.txt
"""
import lightgbm as lgb, pandas as pd, numpy as np, sys
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import roc_auc_score

if _name_ == "_main_":
    if len(sys.argv)<3:
        print("Usage: python train.py features.parquet model_out.txt")
        sys.exit(1)
    feat_file, model_out = sys.argv[1], sys.argv[2]
    df = pd.read_parquet(feat_file).dropna()
    feature_cols = [c for c in df.columns if c not in ('ts','label','signal','reason')]
    X = df[feature_cols].values; y = df['label'].values
    tss = TimeSeriesSplit(n_splits=4)
    best_model=None; best_auc=0
    for train_idx, val_idx in tss.split(X):
        dtrain = lgb.Dataset(X[train_idx], label=y[train_idx])
        dval = lgb.Dataset(X[val_idx], label=y[val_idx])
        params = {'objective':'binary','metric':'auc','verbosity':-1,'boosting':'gbdt'}
        model = lgb.train(params, dtrain, valid_sets=[dval], num_boost_round=500, early_stopping_rounds=50)
        preds = model.predict(X[val_idx])
        auc = roc_auc_score(y[val_idx], preds)
        print("Fold AUC:", auc)
        if auc > best_auc:
            best_auc = auc; best_model = model
    if best_model:
        best_model.save_model(model_out)
        print("Saved model to", model_out, "best_auc", best_auc)