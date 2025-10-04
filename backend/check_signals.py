import json
from datetime import datetime, timedelta
import pandas as pd
from typing import Optional

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
    """
    try:
        df_15 = smc_filters.resample_ohlcv(df_ltf, "15T")
        df_1h = smc_filters.resample_ohlcv(df_ltf, "1H")
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
# SMT Divergence helper
# ------------------------
def check_smt_divergence(primary_df: pd.DataFrame, reference_df: pd.DataFrame, lookback: int = 20) -> Optional[str]:
    """Wrapper for smc_filters.detect_smt_divergence"""
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
    Relaxed scoring-based validation pipeline (Smart Money Concept)
    """

    out = {"valid": False, "reason": "", "confluences": [], "payload": None}

    if candles_df is None or len(candles_df) < 10:
        out['reason'] = "insufficient_data"
        return out

    ts = ml_signal.get("time") or candles_df.index[-1]
    if isinstance(ts, str):
        ts = pd.to_datetime(ts)

    # Start scoring
    score = 0
    reasons = []
    confluences = []

    # ✅ Killzone (Optional)
    if in_killzone(ts):
        score += 1
        confluences.append("killzone ✅ [Optional]")
    else:
        reasons.append("outside_killzone")

    # ✅ Impulsive Move (Important)
    if smc_filters.is_impulsive_move(candles_df, min_points=MIN_MOVE_PIPS, pip_size=PIP_SIZE):
        score += 1
        confluences.append("impulsive_move ✅ [Important]")
    else:
        reasons.append("not_impulsive_move")

    # ✅ HTF Confirmation (Must-Have)
    if confirm_htf_confluence(candles_df):
        score += 1
        confluences.append("htf_confluence ✅ [Must-Have]")
    else:
        reasons.append("htf_confluence_failed")

    # ✅ FVG / OB / BOS / Mitigation / Liquidity
    order_blocks = smc_filters.detect_order_blocks(candles_df)
    bos_points = smc_filters.detect_bos(candles_df)
    fvgs = smc_filters.detect_fvg(candles_df)
    pools = smc_filters.detect_liquidity_pools(candles_df)
    mitigations = smc_filters.detect_mitigation_blocks(candles_df, bos_points, order_blocks)
    breakers = smc_filters.detect_breaker_blocks(order_blocks, candles_df)
    zone, eq = smc_filters.detect_premium_discount(candles_df)

    if pools['highs'] or pools['lows']:
        score += 1
        confluences.append("liquidity_grab ✅ [Must-Have]")

    if fvgs:
        score += 1
        confluences.append("fvg ✅ [Important]")

    if order_blocks:
        score += 1
        confluences.append("ob_rejection ✅ [Important]")

    if mitigations or breakers:
        score += 1
        confluences.append("mitigation/breaker ✅ [Optional]")

    confluences.append(f"zone: {zone}")

    # ✅ SMT Divergence (Optional)
    if reference_df is not None:
        div = check_smt_divergence(candles_df, reference_df)
        if div:
            score += 1
            confluences.append("smt_divergence ✅ [Optional]")

    # ✅ TP Move potential (Important)
    entry = float(ml_signal.get("entry", candles_df['close'].iloc[-1]))
    tp = float(ml_signal.get("take_profit", entry))
    move_points = abs(tp - entry) / PIP_SIZE
    if move_points >= MIN_MOVE_PIPS:
        score += 1
        confluences.append("tp_move_ok ✅ [Important]")
    else:
        reasons.append("tp_below_min_move")

    # ------------------------
    # Final Classification
    # ------------------------
    category = "❌ REJECTED (0/5)"
    valid = False

    if score >= 5:
        category = "💎 SUPER DUPER TRADE (5/5) ✅ Execute Confidently"
        valid = True
    elif score == 4:
        category = "💎 SUPER TRADE (4/5) ✅ High-Probability Entry"
        valid = True
    elif score == 3:
        category = "✅ VALID TRADE (3/5) ⚙️ Moderate Risk"
        valid = True
    elif score == 2:
        category = "⚠️ WEAK TRADE (2/5) 🚫 Avoid / Demo Only"
        valid = False
    elif score == 1:
        category = "❌ RECOMMENDED NO ENTRY (1/5) ❌ Skip Trade"
        valid = False
    else:
        category = "❌ REJECTED (0/5) ❌ Ignore"
        valid = False

    payload = {
        "symbol": symbol,
        "timeframe": timeframe,
        "side": ml_signal.get("type"),
        "entry": entry,
        "stop_loss": float(ml_signal.get("stop_loss", entry)),
        "take_profit": tp,
        "confidence": float(ml_signal.get("confidence", 0.0)),
        "confluences": confluences,
        "score": score,
        "category": category,
        "created_at": datetime.utcnow().isoformat()
    }

    out["valid"] = valid
    out["reason"] = category if valid else ";".join(reasons)
    out["confluences"] = confluences
    out["payload"] = payload
    return out
