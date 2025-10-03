# path: backend/client/fetch_signals.py
from db import SessionLocal, Signal
import json

def fetch_recent_signals(limit=50):
    db = SessionLocal()
    try:
        q = db.query(Signal).order_by(Signal.created_at.desc()).limit(limit).all()
        out = []
        for s in q:
            out.append({
                "id": s.id,
                "symbol": s.symbol,
                "timeframe": s.timeframe,
                "side": s.side,
                "entry": float(s.entry) if s.entry else None,
                "stop_loss": float(s.stop_loss) if s.stop_loss else None,
                "take_profit": float(s.take_profit) if s.take_profit else None,
                "rr": float(s.rr) if s.rr else None,
                "ml_label": s.ml_label,
                "confidence": float(s.confidence) if s.confidence else None,
                "smc_confirmed": bool(s.smc_confirmed),
                "reason": s.reason,
                "raw_data": json.loads(s.raw_data) if s.raw_data else {}
            })
        return out
    finally:
        db.close()

if __name__ == "__main__":
    print(fetch_recent_signals(10))
