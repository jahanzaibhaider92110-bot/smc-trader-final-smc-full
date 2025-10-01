# backend/trainer/auto_trainer.py
"""
Auto trainer scheduler:
- periodically: fetch recent historical (parquet), create labeled csv, run train script as subprocess
- safe mode: only runs if we have minimum labeled samples threshold
"""

import os, subprocess, sys
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
load_dotenv()

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BACKEND_ROOT, 'data')
MIN_LABELED_SAMPLES = int(os.getenv('MIN_LABELED_SAMPLES', '500'))
AUTO_INTERVAL_MIN = int(os.getenv('AUTO_TRAIN_INTERVAL_MIN', '60'))

def _count_labeled_csv_rows():
    cnt = 0
    if not os.path.exists(DATA_DIR):
        return 0
    for f in os.listdir(DATA_DIR):
        if f.endswith('.csv') and 'labeled' in f:
            try:
                import pandas as pd
                df = pd.read_csv(os.path.join(DATA_DIR, f))
                cnt += len(df)
            except Exception:
                continue
    return cnt

def retrain_job():
    try:
        print("AutoTrainer: checking labeled dataset...")
        n = _count_labeled_csv_rows()
        print("AutoTrainer: labeled rows found:", n)
        if n < MIN_LABELED_SAMPLES:
            print(f"AutoTrainer: not enough labeled samples ({n} < {MIN_LABELED_SAMPLES}). Skipping retrain.")
            return
        # call train script (assumes backend/ml/train_model.py exists and is executable)
        train_script = os.path.join(BACKEND_ROOT, 'ml', 'train_model.py')
        if not os.path.exists(train_script):
            print("AutoTrainer: train_model.py not found at", train_script)
            return
        cmd = [sys.executable, train_script]
        print("AutoTrainer: running trainer subprocess...")
        subprocess.run(cmd, check=True)
        print("AutoTrainer: trainer finished.")
    except Exception as e:
        print("AutoTrainer error:", e)

_scheduler = None

def start_scheduler(interval_min: int = AUTO_INTERVAL_MIN):
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    sched = BackgroundScheduler()
    sched.add_job(retrain_job, 'interval', minutes=interval_min)
    sched.start()
    _scheduler = sched
    print("AutoTrainer scheduled every", interval_min, "minutes")
    return sched

def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown()
        _scheduler = None
