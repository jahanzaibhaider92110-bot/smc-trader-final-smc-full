import json
from datetime import datetime, timedelta
import pandas as pd
from typing import Optional   # ✅ Add this line

from db import SessionLocal, Signal
import smc_filters

# Configuration
MIN_MOVE_PIPS = 150.0
PIP_SIZE = 0.0001  # change per instrument if needed (1 for BTC if you measure in USD points)
KILLZONE_LONDON = (8, 11)   # 08:00 - 11:00 UTC
KILLZONE_NY = (13, 16)      # 13:00 - 16:00 UTC


# ------------------------
# DB helpers
# ------------------------
def is_duplicate(session, symbol, timeframe, side, entry, tolerance=0.0005):
    window = datetime.utcnow() - timedelta(minutes=30)
    q = session.query(Signal).filter(
        Signal.symbol == symbol,
        Signal.timeframe == timeframe,
        Signal.side == side,
        Signal.created_at >= window
    ).order_by(Signal.created_at.desc()).all()
    for s in q:
        if abs(s.entry - entry) <= (entry * tolerance):
            return True
    return False


def finalize_and_return_execution(signal_id):
    db = SessionLocal()
    try:
        sig = db.query(Signal).get(signal_id)
        if not sig:
            return None
        if not sig.stop_loss or not sig.take_profit:
            print("Signal missing SL/TP - reject")
            return None
        if is_duplicate(db, sig.symbol, sig.timeframe, sig.side, sig.entry):
            print("Duplicate signal suppressed:", sig.id)
            return None
        payload = {
            "id": sig.id,
            "symbol": sig.symbol,
            "timeframe": sig.timeframe,
            "side": sig.side,
            "entry": float(sig.entry),
            "stop_loss": float(sig.stop_loss),
            "take_profit": float(sig.take_profit),
            "rr": float(sig.rr),
            "smc_confirmed": bool(sig.smc_confirmed),
            "reason": sig.reason,
            "raw_data": json.loads(sig.raw_data) if sig.raw_data else {}
        }
        return payload
    except Exception as e:
        print("check_signals error:", e)
        return None
    finally:
        db.close()


# ------------------------
# Session / Killzone utils
# ------------------------
def in_killzone(ts: datetime) -> bool:
    """
    ts expected in UTC (naive datetime or timezone-aware).
    """
    hour = ts.hour
    if KILLZONE_LONDON[0] <= hour <= KILLZONE_LONDON[1]:
        return True
    if KILLZONE_NY[0] <= hour <= KILLZONE_NY[1]:
        return True
    return False


# ------------------------
# HTF Confluence helper
# ------------------------
def confirm_htf_confluence(df_ltf: pd.DataFrame, pip_size: float = PIP_SIZE) -> bool:
    """
    Confirm direction with higher timeframes:
    - require 15m & 1H trend to agree with 5m signal (simple MA method).
    df_ltf: original dataframe indexed by datetime (5m)
    """
    try:
        df_15 = smc_filters.resample_ohlcv(df_ltf, "15T")
        df_1h = smc_filters.resample_ohlcv(df_ltf, "1H")
        # simple MA-based trend
        def trend(df):
            ma_fast = df['close'].rolling(20).mean().iloc[-1]
            ma_slow = df['close'].rolling(50).mean().iloc[-1]
            return "bull" if ma_fast > ma_slow else ("bear" if ma_fast < ma_slow else "neutral")

        t15 = trend(df_15)
        t1h = trend(df_1h)
        return t15 == t1h and t15 != "neutral"
    except Exception:
        return False


# ------------------------
# SMT Divergence helper (uses reference symbol df)
# ------------------------
def check_smt_divergence(primary_df: pd.DataFrame, reference_df: pd.DataFrame, lookback: int = 20) -> Optional[str]:
    """
    Wrapper for smc_filters.detect_smt_divergence
    """
    return smc_filters.detect_smt_divergence(primary_df, reference_df, lookback=lookback)


# ------------------------
# Main confluence runner
# ------------------------
def run_smc_confluence(
    candles_df: pd.DataFrame,
    symbol: str,
    timeframe: str,
    ml_signal: dict,
    reference_df: Optional[pd.DataFrame] = None
) -> dict:
    """
    Complete validation pipeline.
    - candles_df: 5m candles DataFrame (datetime index)
    - ml_signal: dict with keys: {'type': 'buy'|'sell', 'entry': float, 'stop_loss': float, 'take_profit': float, 'confidence': float}
    - reference_df: optional other instrument dataframe to check SMT divergence
    Returns: {"valid": bool, "reason": str, "confluences": [...], "payload": {...}}
    """

    out = {"valid": False, "reason": "", "confluences": [], "payload": None}

    # basic checks
    if candles_df is None or len(candles_df) < 10:
        out['reason'] = "insufficient data"
        return out

    # enforce timezone-naive in UTC assumed
    ts = ml_signal.get("time") or candles_df.index[-1]
    if isinstance(ts, str):
        ts = pd.to_datetime(ts)
    if not in_killzone(ts):
        out['reason'] = "outside_killzone"
        return out

    # impulsive move check (150+ pips)
    if not smc_filters.is_impulsive_move(candles_df, min_points=MIN_MOVE_PIPS, pip_size=PIP_SIZE):
        out['reason'] = "not_impulsive_move"
        return out

    # core detections
    order_blocks = smc_filters.detect_order_blocks(candles_df)
    bos_points = smc_filters.detect_bos(candles_df)
    fvgs = smc_filters.detect_fvg(candles_df)
    pools = smc_filters.detect_liquidity_pools(candles_df)
    mitigations = smc_filters.detect_mitigation_blocks(candles_df, bos_points, order_blocks)
    breakers = smc_filters.detect_breaker_blocks(order_blocks, candles_df)
    zone, eq = smc_filters.detect_premium_discount(candles_df)

    # store confluences
    confluences = []
    if pools['highs'] or pools['lows']:
        confluences.append("liquidity_pools")
    if mitigations:
        confluences.append("mitigation_blocks")
    if breakers:
        confluences.append("breaker_blocks")
    if fvgs:
        confluences.append("fvgs")
    confluences.append(zone)  # premium/discount

    # HTF confirmation
    if not confirm_htf_confluence(candles_df):
        out['reason'] = "htf_confluence_failed"
        return out

    # SMT divergence check (optional) - requires reference df
    if reference_df is not None:
        div = check_smt_divergence(candles_df, reference_df)
        if div:
            confluences.append(div)

    # require at least 2 strong confluences (besides premium/discount)
    strong = [c for c in confluences if c not in ("premium", "discount")]
    if len(strong) < 1:  # require at least 1 strong confluence + zone = 2 total
        out['reason'] = "insufficient_confluence"
        out['confluences'] = confluences
        return out

    # verify move potential from entry to TP
    entry = float(ml_signal.get("entry", candles_df['close'].iloc[-1]))
    tp = float(ml_signal.get("take_profit", entry))
    move_points = abs(tp - entry) / PIP_SIZE
    if move_points < MIN_MOVE_PIPS:
        out['reason'] = "tp_below_min_move"
        return out

    # Prepare payload for save/execution
    payload = {
        "symbol": symbol,
        "timeframe": timeframe,
        "side": ml_signal.get("type"),
        "entry": entry,
        "stop_loss": float(ml_signal.get("stop_loss", entry)),
        "take_profit": tp,
        "confidence": float(ml_signal.get("confidence", 0.0)),
        "confluences": confluences,
        "created_at": datetime.utcnow().isoformat()
    }

    out['valid'] = True
    out['reason'] = "passed"
    out['confluences'] = confluences
    out['payload'] = payload
    return out


# ------------------------
# Quick CLI test
# ------------------------
if __name__ == "__main__":
    # simple example to test integration
    import numpy as np
    rng = pd.date_range(end=pd.Timestamp.utcnow(), periods=200, freq="5T")
    # create synthetic candles with a big recent range
    highs = np.linspace(50000, 50250, len(rng)) + np.random.rand(len(rng))*10
    lows = highs - (np.random.rand(len(rng))*20 + 10)
    opens = highs - (highs - lows) * 0.6
    closes = lows + (highs - lows) * 0.6
    df = pd.DataFrame({"open": opens, "high": highs, "low": lows, "close": closes, "volume": 1}, index=rng)

    ml_signal = {"type": "buy", "entry": float(df['close'].iloc[-1]), "stop_loss": float(df['low'].iloc[-1]), "take_profit": float(df['close'].iloc[-1]) + 200, "confidence": 0.8, "time": df.index[-1]}

    result = run_smc_confluence(df, "BTC/USDT", "5m", ml_signal)
    print("RESULT:", result)
