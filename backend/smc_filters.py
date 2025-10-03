# path: backend/smc_filters.py
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple

# ------------------------
# Basic helpers
# ------------------------

def atr(df: pd.DataFrame, period: int = 14) -> float:
    """Return ATR value for the dataframe (last value)."""
    if len(df) < 2:
        return 0.0
    high = df["high"]
    low = df["low"]
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        (high - low).abs(),
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return float(tr.rolling(period, min_periods=1).mean().iloc[-1])

# ------------------------
# Order Blocks / BOS / FVG
# ------------------------

def detect_order_blocks(df: pd.DataFrame, lookback: int = 200) -> List[Dict]:
    """Detect simple bullish/bearish order blocks."""
    obs = []
    df = df.reset_index(drop=True)
    for i in range(2, min(len(df)-2, lookback)):
        prev = df.loc[i-1]
        cur = df.loc[i]
        nxt = df.loc[i+1]
        if prev['close'] < prev['open'] and cur['close'] > cur['open'] and nxt['close'] > nxt['open']:
            obs.append({"type": "bull", "index": int(i-1), "high": float(prev['high']), "low": float(prev['low'])})
        if prev['close'] > prev['open'] and cur['close'] < cur['open'] and nxt['close'] < nxt['open']:
            obs.append({"type": "bear", "index": int(i-1), "high": float(prev['high']), "low": float(prev['low'])})
    return obs

def detect_bos(df: pd.DataFrame, lookback: int = 20) -> List[Dict]:
    """Detect Break of Structure points."""
    bos = []
    if len(df) < lookback+1:
        return bos
    highs = df['high'].rolling(lookback).max().shift(1)
    lows = df['low'].rolling(lookback).min().shift(1)
    last_close = df['close'].iloc[-1]
    prev_high = highs.iloc[-1] if not np.isnan(highs.iloc[-1]) else None
    prev_low = lows.iloc[-1] if not np.isnan(lows.iloc[-1]) else None
    if prev_high is not None and last_close > prev_high:
        bos.append({"type": "bull", "level": float(prev_high), "index": int(len(df)-1)})
    if prev_low is not None and last_close < prev_low:
        bos.append({"type": "bear", "level": float(prev_low), "index": int(len(df)-1)})
    return bos

def detect_fvg(df: pd.DataFrame, lookback: int = 200) -> List[Dict]:
    """Detect Fair Value Gaps (3-candle pattern)."""
    fvg = []
    df = df.reset_index(drop=True)
    for i in range(1, min(len(df)-1, lookback)):
        prev = df.loc[i-1]
        nxt = df.loc[i+1]
        if prev['close'] < prev['open'] and nxt['close'] > nxt['open'] and nxt['low'] > prev['high']:
            fvg.append({"type": "bull", "index": i, "top": float(prev['high']), "bottom": float(nxt['low'])})
        if prev['close'] > prev['open'] and nxt['close'] < nxt['open'] and nxt['high'] < prev['low']:
            fvg.append({"type": "bear", "index": i, "top": float(nxt['high']), "bottom": float(prev['low'])})
    return fvg

# ------------------------
# Liquidity Pools
# ------------------------

def detect_liquidity_pools(df: pd.DataFrame, lookback: int = 20, threshold: float = 0.0005, precision: int = 5) -> Dict:
    """Detect liquidity pools (clusters of equal highs/lows)."""
    pools = {"highs": [], "lows": []}
    df = df.reset_index(drop=True)
    for i in range(lookback, len(df)):
        highs = df['high'].iloc[i-lookback:i]
        lows = df['low'].iloc[i-lookback:i]
        close_price = df['close'].iloc[i]
        if highs.max() - highs.min() <= close_price * threshold:
            level = round(float(highs.max()), precision)
            if level not in pools["highs"]:
                pools["highs"].append(level)
        if lows.max() - lows.min() <= close_price * threshold:
            level = round(float(lows.min()), precision)
            if level not in pools["lows"]:
                pools["lows"].append(level)
    return pools

# ------------------------
# Mitigation & Breaker Blocks
# ------------------------

def detect_mitigation_blocks(df: pd.DataFrame, bos_points: List[Dict], order_blocks: List[Dict], recent_candles: int = 5) -> List[Dict]:
    """Detect OB mitigations (retests after BOS)."""
    mitigations = []
    if not bos_points or not order_blocks:
        return mitigations
    recent = df.iloc[-recent_candles:]
    for bos in bos_points:
        for ob in order_blocks:
            try:
                if ob.get("index", -1) < bos.get("index", len(df)):
                    if recent['low'].min() <= ob['low'] and recent['high'].max() >= ob['high']:
                        mitigations.append(ob)
            except Exception:
                continue
    return mitigations

def detect_breaker_blocks(order_blocks: List[Dict], df: pd.DataFrame) -> List[Dict]:
    """Detect breaker blocks (invalidated OBs)."""
    breakers = []
    if not order_blocks:
        return breakers
    last_close = df['close'].iloc[-1]
    for ob in order_blocks:
        if ob['type'] == "bull" and last_close < ob['low']:
            nb = ob.copy(); nb['type'] = "bear_breaker"; breakers.append(nb)
        if ob['type'] == "bear" and last_close > ob['high']:
            nb = ob.copy(); nb['type'] = "bull_breaker"; breakers.append(nb)
    return breakers

# ------------------------
# Premium / Discount Zones
# ------------------------

def detect_premium_discount(df: pd.DataFrame, lookback: int = 50) -> Tuple[str, float]:
    """Return ("premium" or "discount", equilibrium_level)."""
    if len(df) < lookback:
        lookback = len(df)
    swing_high = float(df['high'].iloc[-lookback:].max())
    swing_low = float(df['low'].iloc[-lookback:].min())
    equilibrium = (swing_high + swing_low) / 2.0
    zone = "premium" if df['close'].iloc[-1] > equilibrium else "discount"
    return zone, equilibrium

# ------------------------
# Impulsive Move
# ------------------------

def is_impulsive_move(df: pd.DataFrame, min_points: float = 150.0, pip_size: float = 0.0001) -> bool:
    """Check if the last swing >= min_points (in pips)."""
    if len(df) < 2:
        return False
    last_high = float(df['high'].iloc[-2])
    last_low = float(df['low'].iloc[-2])
    move_points = abs(last_high - last_low) / pip_size
    return move_points >= min_points

# ------------------------
# SMT Divergence
# ------------------------

def detect_smt_divergence(df_primary: pd.DataFrame, df_reference: pd.DataFrame, lookback: int = 20) -> Optional[str]:
    """Detect SMT divergence (bullish or bearish)."""
    if len(df_primary) < lookback or len(df_reference) < lookback:
        return None
    p = df_primary.iloc[-lookback:]
    r = df_reference.iloc[-lookback:]
    primary_ll = p['low'].min()
    primary_hh = p['high'].max()
    ref_ll = r['low'].min()
    ref_hh = r['high'].max()
    if df_primary['low'].iloc[-1] < primary_ll and df_reference['low'].iloc[-1] >= ref_ll:
        return "bull_div"
    if df_primary['high'].iloc[-1] > primary_hh and df_reference['high'].iloc[-1] <= ref_hh:
        return "bear_div"
    return None

# ------------------------
# Resampling
# ------------------------

def resample_ohlcv(df: pd.DataFrame, timeframe: str = "15T") -> pd.DataFrame:
    """Resample OHLCV dataframe to given timeframe."""
    if not isinstance(df.index, pd.DatetimeIndex):
        df = df.set_index(pd.to_datetime(df.index))
    ohlc = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    res = df.resample(timeframe).apply(ohlc).dropna()
    return res

# ------------------------
# SL/TP helper
# ------------------------

def compute_sl_tp(entry: float, side: str, ob: Optional[Dict], atr_val: float, prefer_rr: float = 2.0) -> Tuple[float, float]:
    """Compute Stop Loss / Take Profit levels."""
    if side.upper() == "BUY":
        if ob and ob.get("type") == "bull":
            sl = ob["low"] - (atr_val * 0.1)
        else:
            sl = entry - max(atr_val * 1.0, entry * 0.0005)
        tp = entry + abs(entry - sl) * prefer_rr
    else:
        if ob and ob.get("type") == "bear":
            sl = ob["high"] + (atr_val * 0.1)
        else:
            sl = entry + max(atr_val * 1.0, entry * 0.0005)
        tp = entry - abs(entry - sl) * prefer_rr
    return float(round(sl, 8)), float(round(tp, 8))

# ------------------------
# Extra helpers for signals
# ------------------------

def calculate_move_potential(df: pd.DataFrame, signal: Dict, horizon: int = 12) -> float:
    """Calculate potential move size after a signal within N candles."""
    idx = signal.get("index")
    if idx is None or idx >= len(df) - horizon:
        return 0.0
    entry_price = df['close'].iloc[idx]
    future_high = df['high'].iloc[idx+1:idx+1+horizon].max()
    future_low = df['low'].iloc[idx+1:idx+1+horizon].min()
    if signal['type'] == "long":
        return future_high - entry_price
    elif signal['type'] == "short":
        return entry_price - future_low
    return 0.0

def smc_validate_signal(df: pd.DataFrame, signal: Dict) -> bool:
    """Validate a signal using SMA20 trend filter."""
    idx = signal.get("index", None)
    if idx is None or idx >= len(df):
        return False
    df['sma20'] = df['close'].rolling(20).mean()
    side = signal.get("type")
    close_price = df['close'].iloc[idx]
    sma20 = df['sma20'].iloc[idx]
    if side == "long" and close_price > sma20:
        return True
    if side == "short" and close_price < sma20:
        return True
    return False

def smc_confirm(df: pd.DataFrame, signal: Dict) -> bool:
    """Confirm a signal with confluence of SMA20 + Premium/Discount zones."""
    if signal is None:
        return False
    side = signal.get("type")
    price = signal.get("price", None)
    if price is None:
        return False
    df['sma20'] = df['close'].rolling(20).mean()
    sma20 = df['sma20'].iloc[-1]
    zone, eq = detect_premium_discount(df, lookback=50)
    if side == "long":
        if price < eq and df['close'].iloc[-1] > sma20:
            return True
    elif side == "short":
        if price > eq and df['close'].iloc[-1] < sma20:
            return True
    return False
