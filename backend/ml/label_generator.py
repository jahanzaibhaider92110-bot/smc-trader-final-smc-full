"""
Label generator with ML + SMC signals
"""

import os, pandas as pd, json
from pathlib import Path
from datetime import datetime
from smc.advanced_smc import evaluate_smc
from smc.analyzer import extract_features
from ccxt_client import fetch_ohlcv

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
PRED_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "predictions")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PRED_DIR, exist_ok=True)


def fetch_and_store_historical(symbol='BTC/USDT', timeframe='1m', limit=5000, filename=None):
    raw = fetch_ohlcv(symbol=symbol, timeframe=timeframe, limit=limit)
    if not raw:
        return None
    df = pd.DataFrame(raw, columns=['ts','open','high','low','close','volume'])
    df['ts'] = pd.to_datetime(df['ts'], unit='ms')
    if filename is None:
        filename = f"{symbol.replace('/','')}_{timeframe}.parquet"
    path = os.path.join(DATA_DIR, filename)
    df.to_parquet(path, index=False)
    return path


def forward_label_one_candidate(cand: dict, future_df: pd.DataFrame, max_bars=120, tp_index=1):
    entry = float(cand.get('entry', 0.0))
    sl = float(cand.get('stop_loss', 0.0))
    tps = cand.get('take_profits', [])
    if len(tps) < tp_index:
        return 0
    tp = float(tps[tp_index-1])
    side = cand.get('side','buy')

    for i in range(min(len(future_df), max_bars)):
        hi = float(future_df['high'].iloc[i])
        lo = float(future_df['low'].iloc[i])

        if side == 'buy':
            if lo <= sl:  
                return 0
            if hi >= tp:  
                return 1
        else:
            if hi >= sl:  
                return 0
            if lo <= tp:  
                return 1
    return 0


def generate_labeled_dataset(parquet_path: str, lookback: int = 500, forward_bars: int = 120, tp_index: int = 1, out_csv: str = None, max_samples: int = None):
    df_all = pd.read_parquet(parquet_path).reset_index(drop=True)
    n = len(df_all)
    rows = []
    start = lookback
    count = 0

    for t in range(start, n - forward_bars - 1):
        window = df_all.iloc[t-lookback:t].copy().reset_index(drop=True)
        window.attrs['symbol'] = Path(parquet_path).stem.split('_')[0]
        window.attrs['timeframe'] = Path(parquet_path).stem.split('_')[-1]

        candidates = evaluate_smc(window)
        if not candidates:
            continue

        future = df_all.iloc[t:t+forward_bars].reset_index(drop=True)
        for cand in candidates:
            label = forward_label_one_candidate(cand, future, max_bars=forward_bars, tp_index=tp_index)
            feat = extract_features(window, cand)
            feat['label'] = int(label)
            rows.append(feat)
            count += 1
            if max_samples and count >= max_samples:
                break

        if max_samples and count >= max_samples:
            break

    out_path = out_csv or parquet_path.replace('.parquet', f'_labeled_tp{tp_index}.csv')
    pd.DataFrame(rows).to_csv(out_path, index=False)
    return out_path


def save_prediction(cand, ml_label, confidence):
    """
    Save final prediction to predictions/signal.json
    """
    signal = {
        "label": cand.get("side", "-"),
        "reason": cand.get("reason", "-"),
        "ml_label": ml_label,
        "ml_confidence": confidence,
        "created_at": datetime.utcnow().isoformat()
    }
    out_path = os.path.join(PRED_DIR, "signal.json")
    with open(out_path, "w") as f:
        json.dump(signal, f, indent=4)
    return out_path


if __name__ == "__main__":
    p = fetch_and_store_historical('BTC/USDT','1m', limit=3000)
    if p:
        out = generate_labeled_dataset(p, lookback=400, forward_bars=120, tp_index=1, max_samples=2000)
        print("Labeled dataset:", out)
