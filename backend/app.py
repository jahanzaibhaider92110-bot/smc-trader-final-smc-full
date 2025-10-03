# path: backend/app.py
from flask import Flask, jsonify, request
from db import init_db, SessionLocal, Signal
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import datetime
import traceback

# we call the run_prediction helper from predict_signal.py
# ensure predict_signal.py (same folder) implements run_prediction(...)
from predict_signal import run_prediction

app = Flask(__name__)
init_db()

scheduler = BackgroundScheduler()

def auto_job():
    try:
        print("⏳ [scheduler] running prediction job...", datetime.datetime.utcnow().isoformat())
        # run_prediction should run the full pipeline and return the saved signal dict (if saved) or None
        result = run_prediction(symbol="BTC/USDT", timeframe="5m")
        if result:
            print("✅ [scheduler] valid signal produced:", result.get("id") or "no-id", result.get("side"), result.get("entry"))
        else:
            print("— [scheduler] no valid signal this run.")
    except Exception as e:
        print("🚨 [scheduler] error:", e)
        traceback.print_exc()

# schedule every 10 seconds (you asked for frequent polling)
scheduler.add_job(func=auto_job, trigger="interval", seconds=10, max_instances=1)
scheduler.start()
atexit.register(lambda: scheduler.shutdown(wait=False))

# API endpoints (frontend calls these)
@app.route("/signals")
def signals():
    """
    Returns latest matching signal as {"signal": {...}} or {"signal": None}
    Example: /signals?symbol=BTC/USDT&timeframe=5m
    """
    symbol = request.args.get("symbol", None)
    timeframe = request.args.get("timeframe", None)

    db = SessionLocal()
    query = db.query(Signal).order_by(Signal.created_at.desc())
    if symbol:
        # stored symbols often normalized without '/'
        query = query.filter(Signal.symbol == symbol.replace("/", ""))
    if timeframe:
        query = query.filter(Signal.timeframe == timeframe)
    latest = query.first()
    db.close()

    if not latest:
        return jsonify({"signal": None})

    return jsonify({
        "signal": {
            "id": latest.id,
            "symbol": latest.symbol,
            "timeframe": latest.timeframe,
            "side": latest.side,
            "entry": latest.entry,
            "stop_loss": latest.stop_loss,
            "take_profit": latest.take_profit,
            "rr": latest.rr,
            "ml_label": latest.ml_label,
            "confidence": latest.confidence,
            "reason": latest.reason,
            "smc_confirmed": latest.smc_confirmed,
            "created_at": latest.created_at.isoformat()
        }
    })


@app.route("/signals_list")
def signals_list():
    db = SessionLocal()
    rows = db.query(Signal).order_by(Signal.created_at.desc()).limit(200).all()
    db.close()
    out = []
    for s in rows:
        out.append({
            "id": s.id,
            "symbol": s.symbol,
            "timeframe": s.timeframe,
            "side": s.side,
            "entry": s.entry,
            "stop_loss": s.stop_loss,
            "take_profit": s.take_profit,
            "rr": s.rr,
            "confidence": s.confidence,
            "smc_confirmed": s.smc_confirmed,
            "reason": s.reason,
            "created_at": s.created_at.isoformat()
        })
    return jsonify({"signals": out})


@app.route("/health")
def health():
    return jsonify({"ok": True})

if __name__ == "__main__":
    # runs the Flask app and the scheduler inside same process
    app.run(host="0.0.0.0", port=8000, debug=True)
