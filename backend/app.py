from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
import os, json

from db import SessionLocal, Signal  

app = FastAPI(title="SMC-Trader Pure SMC + ML")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/signals")
def get_signals(symbol: str = "BTC/USDT", timeframe: str = "1m", db: Session = Depends(get_db)):
    sig = db.query(Signal).order_by(Signal.created_at.desc()).first()

    if sig:
        return {
            "signal": {
                "label": sig.side or "-",
                "reason": sig.explanation or "-",
                "ml_label": sig.raw.get("ml_label") if sig.raw else "-",
                "ml_confidence": sig.confidence if sig.confidence else "-",
                "created_at": sig.created_at.isoformat() if sig.created_at else "-"
            }
        }

    if os.path.exists("predictions/signal.json"):
        with open("predictions/signal.json", "r") as f:
            data = json.load(f)
    else:
        data = {
            "label": "-",
            "reason": "No signal yet",
            "ml_label": "-",
            "ml_confidence": "-",
            "created_at": str(datetime.utcnow())
        }
    return {"signal": data}
