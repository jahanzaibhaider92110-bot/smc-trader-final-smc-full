"""
train_model.py
Train an ML model on SMC rule-engine labeled data.
"""

import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

from scripts.label_data import label_df  # reuse your labeling

# ==== Step 1: Load data ====
df = pd.read_parquet("data/btc_1h.parquet")
df = df.sort_values("ts").reset_index(drop=True)

# ==== Step 2: Create labels using your rule-engine ====
labeled = label_df(df)
print("Sample labeled data:\n", labeled.head())

# ==== Step 3: Prepare features ====
X = []
y = []

for _, row in labeled.iterrows():
    feats = [
        len(row['reason']),              # reason length (proxy for complexity)
        1 if "bullish" in row['reason'] else 0,
        1 if "bearish" in row['reason'] else 0,
        1 if "OB retest" in row['reason'] else 0,
        1 if "FVG" in row['reason'] else 0,
        1 if "liquidity" in row['reason'] else 0,
        1 if "discount" in row['reason'] else 0,
        1 if "premium" in row['reason'] else 0,
    ]
    X.append(feats)
    y.append(row['label'])

import numpy as np
X = np.array(X)
y = np.array(y)

# ==== Step 4: Train/Test Split ====
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

# ==== Step 5: Train Model ====
model = RandomForestClassifier(n_estimators=200, random_state=42)
model.fit(X_train, y_train)

# ==== Step 6: Evaluate ====
y_pred = model.predict(X_test)
print("Model Performance:")
print(classification_report(y_test, y_pred))

# ==== Step 7: Save Model ====
joblib.dump(model, "models/smc_model.pkl")
print("✅ Model trained and saved at models/smc_model.pkl")
