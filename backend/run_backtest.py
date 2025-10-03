# path: backend/run_backtest.py
import pandas as pd
import math
from db import SessionLocal, Signal
from datetime import datetime

def run_backtest_from_db(price_df_path="data/btc_5m.parquet"):
    # load price series
    price_df = pd.read_parquet(price_df_path)
    price_df['timestamp'] = pd.to_datetime(price_df['ts'] if 'ts' in price_df.columns else price_df.get('timestamp', price_df.index))
    price_df = price_df.sort_values('timestamp').reset_index(drop=True)

    db = SessionLocal()
    try:
        signals = db.query(Signal).order_by(Signal.created_at).all()
    finally:
        db.close()

    if not signals:
        print("No signals to backtest.")
        return

    trades = []
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    wins = 0
    losses = 0
    rr_sum = 0.0
    for s in signals:
        entry = float(s.entry)
        sl = float(s.stop_loss)
        tp = float(s.take_profit)
        side = s.side
        # find the index after signal time
        future = price_df[price_df['timestamp'] > s.created_at]
        hit = None
        for _, c in future.iterrows():
            if side == "BUY":
                if c['low'] <= sl:
                    hit = ("SL", sl, c['timestamp'])
                    break
                if c['high'] >= tp:
                    hit = ("TP", tp, c['timestamp'])
                    break
            else:
                if c['high'] >= sl:
                    hit = ("SL", sl, c['timestamp'])
                    break
                if c['low'] <= tp:
                    hit = ("TP", tp, c['timestamp'])
                    break
        if hit:
            outcome = hit[0]
            exit_price = hit[1]
        else:
            # if not hit, use last close in future window or skip
            if len(future) > 0:
                exit_price = future.iloc[-1]['close']
                outcome = "NONE"
            else:
                exit_price = price_df.iloc[-1]['close']
                outcome = "NONE"

        pnl = (exit_price - entry) if side == "BUY" else (entry - exit_price)
        trades.append({"id": s.id, "outcome": outcome, "pnl": pnl, "rr": s.rr, "reason": s.reason})
        equity += pnl
        peak = max(peak, equity)
        drawdown = peak - equity
        max_dd = max(max_dd, drawdown)
        if outcome == "TP":
            wins += 1
        elif outcome == "SL":
            losses += 1
        rr_sum += (s.rr or 0)

    total = len(trades)
    winrate = wins / total if total > 0 else 0
    avg_rr = rr_sum / total if total > 0 else 0
    avg_pnl = sum(t['pnl'] for t in trades) / total if total > 0 else 0
    expectancy = (avg_pnl)  # simplification; can be refined

    report = {
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "winrate": winrate,
        "avg_rr": avg_rr,
        "total_pnl": sum(t['pnl'] for t in trades),
        "max_drawdown": max_dd,
        "expectancy": expectancy,
    }
    print("Backtest Report:", report)
    pd.DataFrame(trades).to_csv("backtest_trades.csv", index=False)
    print("Saved trades -> backtest_trades.csv")
    return report

if __name__ == "__main__":
    run_backtest_from_db()
