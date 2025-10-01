# backend/smc/analyzer.py
"""
SMC Analyzer utility:
- extract_features(signal_df, candidate): create ML-friendly features for a candidate
- persist_candidate_for_labeling(candidate_record): save candidate metadata to disk for later labeling
"""

import os
import json
import math
import pandas as pd
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
CANDIDATES_DIR = os.path.join(DATA_DIR, "candidates")
os.makedirs(CANDIDATES_DIR, exist_ok=True)

def _tf_to_minutes(tf: str):
    if not isinstance(tf, str):
        return 1
    if tf.endswith('m'):
        return int(tf.replace('m',''))
    if tf.endswith('h'):
        return int(tf.replace('h',''))*60
    if tf.endswith('d'):
        return int(tf.replace('d',''))*1440
    return 1

def extract_features(df: pd.DataFrame, candidate: dict) -> dict:
    """
    df: pandas DataFrame (window used to create candidate), LAST row is current
    candidate: dict produced by advanced_smc.evaluate_smc (entry, stop_loss, take_profits, ob, fvg, bos, etc.)
    returns: flat dict of numeric features + meta for model training / inference
    """
    last = df.iloc[-1]
    f = {}
    # price/momentum
    f['close'] = float(last['close'])
    f['open']  = float(last['open'])
    f['high']  = float(last['high'])
    f['low']   = float(last['low'])
    f['volume']= float(last['volume'])
    f['r1']    = (f['close'] - f['open']) / (f['open'] + 1e-9)
    # small returns over recent candles
    for look in (3,5,10):
        if len(df) > look:
            f[f"ret_{look}"] = (float(last['close']) - float(df['close'].iloc[-look])) / (float(df['close'].iloc[-look]) + 1e-9)
        else:
            f[f"ret_{look}"] = 0.0
    # volatility / atr proxy
    rng = (df['high'] - df['low']).tail(14)
    f['atr14'] = float(rng.mean()) if len(rng)>0 else (f['high'] - f['low'])
    f['r_atr'] = f['r1'] / (f['atr14'] + 1e-9)
    # OB info
    if candidate.get('ob'):
        ob = candidate['ob']
        mid = (ob['high'] + ob['low']) / 2.0
        f['dist_to_ob_pct'] = abs(f['close'] - mid) / (mid + 1e-9)
        f['ob_width_pct'] = (ob['high'] - ob['low']) / (mid + 1e-9)
        f['ob_type'] = 1 if ob.get('type') == 'bullish' else -1
    else:
        f['dist_to_ob_pct'] = 999.0
        f['ob_width_pct'] = 0.0
        f['ob_type'] = 0
    # BOS / FVG
    f['has_bos'] = 1 if candidate.get('bos') else 0
    f['has_fvg'] = 1 if candidate.get('fvg') else 0
    # confidence given by heuristic (if present)
    f['heur_confidence'] = float(candidate.get('confidence', 0.5))
    # risk/reward engineered
    entry = float(candidate.get('entry', f['close']))
    sl = float(candidate.get('stop_loss', f['low']))
    # for sell logic sl might be > entry
    if sl == 0:
        f['rr1'] = 0.0
    else:
        if candidate.get('side', 'buy') == 'buy':
            rr = (candidate.get('take_profits',[entry])[0] - entry) / (entry - sl + 1e-9) if (entry - sl) != 0 else 0.0
        else:
            rr = (entry - candidate.get('take_profits',[entry])[0]) / (sl - entry + 1e-9) if (sl - entry) != 0 else 0.0
        f['rr1'] = float(rr)
    # timeframe numeric
    f['tf_min'] = _tf_to_minutes(candidate.get('timeframe','1m'))
    # meta
    meta = {
        'symbol': candidate.get('symbol', df.attrs.get('symbol','BTC/USDT')),
        'timeframe': candidate.get('timeframe', df.attrs.get('timeframe','1m')),
        'side': 1 if candidate.get('side','buy')=='buy' else 0,
        'entry': float(candidate.get('entry', f['close'])),
        'stop_loss': float(candidate.get('stop_loss', f['low'])),
        'take_profits': candidate.get('take_profits', []),
        'created_at': datetime.utcnow().isoformat() if 'datetime' not in globals() else datetime.now().isoformat(),
        'reason': candidate.get('reason','')
    }
    # combine
    combined = {**meta, **f}
    # ensure all values are JSON serializable
    for k,v in combined.items():
        if isinstance(v, (pd.Timestamp,)):
            combined[k] = str(v)
        if isinstance(v, (float, int, str, list)):
            continue
        # fallback stringify
        if v is None:
            combined[k] = None
        else:
            try:
                combined[k] = float(v)
            except Exception:
                combined[k] = str(v)
    return combined

def persist_candidate_for_labeling(feature_record: dict):
    """
    Save candidate features/metadata to disk so labeler/trainer can pick it up later.
    Each candidate saved as JSON file with timestamped name.
    """
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S%f")
    fn = f"candidate_{feature_record.get('symbol','X')}_{ts}.json"
    path = os.path.join(CANDIDATES_DIR, fn)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(feature_record, f, indent=2)
    return path

def gather_candidates_files(limit=1000):
    """
    Return list of saved candidate JSONs (for manual review / labeling pipeline)
    """
    files = sorted([os.path.join(CANDIDATES_DIR, p) for p in os.listdir(CANDIDATES_DIR) if p.endswith('.json')])
    if limit:
        return files[-limit:]
    return files
