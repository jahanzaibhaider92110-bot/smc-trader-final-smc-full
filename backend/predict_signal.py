from datetime import datetime
from db import SessionLocal, Signal

def save_signal(symbol, timeframe, side, entry, stop_loss, take_profit, rr, ml_label, confidence, reason, raw_data):
    db = SessionLocal()
    try:
        # Raw data ke andar bhi ML ka result inject kar dete hain
        if raw_data is None:
            raw_data = {}
        raw_data.update({
            "ml_label": ml_label,
            "ml_confidence": confidence
        })

        signal = Signal(
            symbol=symbol,
            timeframe=timeframe,
            side=side,
            entry=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            rr=rr,
            confidence=confidence if confidence is not None else 0.0,
            explanation=reason if reason else "No explanation",
            raw=raw_data,
            created_at=datetime.utcnow()
        )
        db.add(signal)
        db.commit()
        db.refresh(signal)
        return signal
    except Exception as e:
        db.rollback()
        print("❌ Error saving signal:", str(e))
        return None
    finally:
        db.close()


# Example usage (for testing)
if __name__ == "__main__":
    test_signal = save_signal(
        symbol="BTCUSDT",
        timeframe="1h",
        side="BUY",
        entry=50000.0,
        stop_loss=49500.0,
        take_profit=51000.0,
        rr=2.0,
        ml_label=1,   # ✅ Ab ML Label bhi save hoga
        confidence=0.85,
        reason="BOS + OB + FVG + LIQ + EQ",
        raw_data={"example": "test"}
    )
    if test_signal:
        print("✅ Signal saved:", test_signal.id, test_signal.created_at)
