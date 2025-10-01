"""
scripts/label_data.py
Create labelled examples by running the rule-engine sliding window and checking forward outcome.
"""

import pandas as pd
import numpy as np
import argparse
import os
import sys

# --- Fix path issue ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from smc.smc_engine import generate_signal


def label_df(df: pd.DataFrame, forward_bars=60, profit_pct=0.006, stop_pct=0.004):
    rows = []
    total = len(df) - forward_bars

    for i in range(120, total):
        # progress every 50 rows
        if i % 50 == 0:
            print(f"   Processing row {i}/{total}")

        window = df.iloc[: i + 1].copy()
        sig = generate_signal(window)

        # agar signal empty ya dict me 'signal' na ho → skip
        if not sig or "signal" not in sig:
            continue  

        entry = sig.get("entry", float(window["close"].iat[-1]))
        fut = df["close"].iloc[i + 1 : i + 1 + forward_bars]
        fut_max = fut.max()
        fut_min = fut.min()

        label = 0
        if sig["signal"] == "buy":
            win = fut_max >= entry * (1 + profit_pct)
            loss = fut_min <= entry * (1 - stop_pct)
            if win and not loss:
                label = 1
        elif sig["signal"] == "sell":
            win = fut_min <= entry * (1 - stop_pct)
            loss = fut_max >= entry * (1 + profit_pct)
            if win and not loss:
                label = 1

        rows.append(
            {
                "ts": window["ts"].iat[-1],
                "signal": sig["signal"],
                "entry": entry,
                "label": label,
                "reason": sig.get("reason", ""),
            }
        )

    return pd.DataFrame(rows)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python label_data.py input.parquet out.parquet")
        sys.exit(1)

    inp = sys.argv[1]
    out = sys.argv[2]

    print(f"📂 Reading input file: {inp}")
    df = pd.read_parquet(inp)
    df = df.sort_values("ts").reset_index(drop=True)
    print(f"Total rows in input dataframe: {len(df)}")

    print("👉 Labeling started...")
    labels = label_df(df)

    os.makedirs(os.path.dirname(out), exist_ok=True)
    labels.to_parquet(out)

    print(f"✅ Saved labels to {out}")
    print(f"Total labeled rows: {len(labels)}")
    print("🎉 Done.")
