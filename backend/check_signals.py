from db import SessionLocal, Signal

def show_last_signals():
    # DB session open karo
    db = SessionLocal()
    try:
        # Last 10 records newest first
        signals = db.query(Signal).order_by(Signal.created_at.desc()).limit(10).all()

        print("\n🔍 Last 10 Signals in DB:\n")
        if not signals:
            print("⚠️ No signals found in DB.")
            return

        for s in signals:
            print(f"ID: {s.id}")
            print(f"Symbol      : {s.symbol}")
            print(f"Timeframe   : {s.timeframe}")
            print(f"Side        : {s.side}")
            print(f"Confidence  : {s.confidence}")
            print(f"Created_at  : {s.created_at}")
            print("-" * 40)

    except Exception as e:
        print("❌ Error reading signals:", str(e))
    finally:
        db.close()


if __name__ == "__main__":
    show_last_signals()
