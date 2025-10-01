"""
Enhanced SMC engine (rule-based)
- BOS, OB, FVG, Liquidity sweep
- EQH / EQL detection
- Premium/Discount zone
- Confidence weighting and smc_rules breakdown
- generate_signal expects pandas DataFrame (ts, open, high, low, close, volume)
"""
from typing import List, Dict, Optional
import pandas as pd
import numpy as np

def ensure_cols(df: pd.DataFrame) -> pd.DataFrame:
    req = ['ts','open','high','low','close','volume']
    for c in req:
        if c not in df.columns:
            raise ValueError(f"missing column: {c}")
    return df.reset_index(drop=True).copy()

def detect_bos(df: pd.DataFrame) -> Optional[str]:
    if len(df) < 3: return None
    if df['close'].iat[-1] > df['high'].iat[-2]: return "bullish_BOS"
    if df['close'].iat[-1] < df['low'].iat[-2]: return "bearish_BOS"
    return None

def detect_ob(df: pd.DataFrame, lookback: int = 100) -> Optional[Dict]:
    if 'bos' in df.columns:
        for i in range(len(df)-1, -1, -1):
            if df.at[i, 'bos'] in ('bull','bear'):
                window = df.iloc[max(0, i-lookback):i]
                if df.at[i,'bos']=='bull':
                    bearish = window[window['close'] < window['open']]
                    if not bearish.empty:
                        idx = bearish.index[-1]
                        return {'side':'buy','high':float(df.at[idx,'high']),'low':float(df.at[idx,'low']),'idx':int(idx)}
                else:
                    bullish = window[window['close'] > window['open']]
                    if not bullish.empty:
                        idx = bullish.index[-1]
                        return {'side':'sell','high':float(df.at[idx,'high']),'low':float(df.at[idx,'low']),'idx':int(idx)}
    return None

def find_fvg(df: pd.DataFrame) -> List[Dict]:
    fvgs = []
    for i in range(2, len(df)):
        if df.at[i,'low'] > df.at[i-2,'high']:
            fvgs.append({'type':'bull','start':i-2,'end':i,'high':float(df.at[i-2,'high']),'low':float(df.at[i,'low'])})
        if df.at[i,'high'] < df.at[i-2,'low']:
            fvgs.append({'type':'bear','start':i-2,'end':i,'high':float(df.at[i,'high']),'low':float(df.at[i-2,'low'])})
    return fvgs

def detect_liquidity_sweep(df: pd.DataFrame, lookback: int=30) -> List[Dict]:
    sweeps = []
    for i in range(lookback, len(df)):
        window = df.iloc[i-lookback:i]
        highs = window['high'].values
        lows = window['low'].values
        uniq_h = np.unique(np.round(highs, 5))
        uniq_l = np.unique(np.round(lows, 5))
        for h in uniq_h:
            count = np.sum(np.isclose(highs, h, atol=1e-5))
            if count >= 2 and df.at[i,'high'] > h:
                sweeps.append({'idx':i,'type':'high_sweep','level':float(h)})
        for l in uniq_l:
            count = np.sum(np.isclose(lows, l, atol=1e-5))
            if count >= 2 and df.at[i,'low'] < l:
                sweeps.append({'idx':i,'type':'low_sweep','level':float(l)})
    return sweeps

def detect_eqh(df: pd.DataFrame, lookback: int = 30, tol_pct: float = 0.0008) -> bool:
    if len(df) < 3 or lookback < 3: return False
    recent = df['high'].iloc[-lookback:]
    last = recent.iat[-1]
    close_vals = np.abs((recent - last) / (last + 1e-9))
    return (close_vals < tol_pct).sum() >= 2

def detect_eql(df: pd.DataFrame, lookback: int = 30, tol_pct: float = 0.0008) -> bool:
    if len(df) < 3 or lookback < 3: return False
    recent = df['low'].iloc[-lookback:]
    last = recent.iat[-1]
    close_vals = np.abs((recent - last) / (last + 1e-9))
    return (close_vals < tol_pct).sum() >= 2

def classify_zone(entry: float, ob_high: float, ob_low: float) -> str:
    if ob_high == ob_low: return "neutral"
    ratio = (entry - ob_low) / (ob_high - ob_low)
    if ratio <= 0.4: return "discount"
    if ratio >= 0.6: return "premium"
    return "fair-value"

DEFAULT_WEIGHTS = {'BOS':0.30,'OB':0.25,'FVG':0.12,'LIQ':0.10,'EQ':0.08,'TF':0.05}

def generate_signal(df: pd.DataFrame, ob_lookback: int = 100) -> Dict:
    try:
        df = ensure_cols(df)
        # compute simple bos marker per row
        df['bos'] = None
        for i in range(2, len(df)):
            if df.at[i,'close'] > df.at[i-1,'high']:
                df.at[i,'bos'] = 'bull'
            if df.at[i,'close'] < df.at[i-1,'low']:
                df.at[i,'bos'] = 'bear'

        latest_idx = len(df)-1
        latest_close = float(df.at[latest_idx,'close'])

        bos_flag = df.at[latest_idx,'bos']
        ob = detect_ob(df, lookback=ob_lookback)
        fvgs = find_fvg(df)
        sweeps = detect_liquidity_sweep(df)
        eqh = detect_eqh(df)
        eql = detect_eql(df)

        triggered = []
        score = 0.0
        rules = {}

        if bos_flag == 'bull':
            triggered.append('BOS'); rules['BOS']='bull'; score += DEFAULT_WEIGHTS['BOS']
        elif bos_flag == 'bear':
            triggered.append('BOS'); rules['BOS']='bear'; score += DEFAULT_WEIGHTS['BOS']

        if ob:
            triggered.append('OB'); rules['OB']=ob; score += DEFAULT_WEIGHTS['OB']
        if len(fvgs)>0:
            triggered.append('FVG'); rules['FVG']=fvgs; score += DEFAULT_WEIGHTS['FVG']
        if len(sweeps)>0:
            triggered.append('LIQ'); rules['LIQ']=sweeps; score += DEFAULT_WEIGHTS['LIQ']
        if eqh:
            triggered.append('EQ'); rules['EQ']='EQH'; score += DEFAULT_WEIGHTS['EQ']
        if eql:
            triggered.append('EQ'); rules['EQ']='EQL'; score += DEFAULT_WEIGHTS['EQ']

        zone = 'unknown'
        if ob:
            entry = min(latest_close, ob['high']) if ob['side']=='buy' else max(latest_close, ob['low'])
            zone = classify_zone(entry, ob['high'], ob['low'])
            rules['zone'] = zone
        else:
            entry = latest_close

        confidence = min(0.99, score)
        sl = None; tps = []; signal_type = 'none'
        reason_parts = list(triggered)
        if 'OB' in rules:
            reason_parts.append('OB_retest')

        if 'BOS' in rules:
            if rules['BOS']=='bull' and zone=='discount':
                signal_type='buy'
                sl = ob['low'] - 0.5*(ob['high']-ob['low'])
                tps = [entry + (entry-sl)*1.0, entry + (entry-sl)*2.0]
            elif rules['BOS']=='bear' and zone=='premium':
                signal_type='sell'
                sl = ob['high'] + 0.5*(ob['high']-ob['low'])
                tps = [entry - (sl-entry)*1.0, entry - (sl-entry)*2.0]

        return {'signal': signal_type, 'confidence': float(round(confidence,3)), 'entry': float(round(entry,6)) if entry is not None else None,
                'stop_loss': float(round(sl,6)) if sl is not None else None, 'take_profits':[float(round(x,6)) for x in tps],
                'smc_rules': rules, 'reason': ' + '.join(reason_parts) if reason_parts else 'no_setup'}
    except Exception as e:
        return {'signal':'error','confidence':0.0,'entry':None,'stop_loss':None,'take_profits':[],'smc_rules':{},'reason':f'error: {e}'}
