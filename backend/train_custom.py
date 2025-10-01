import pandas as pd, joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# Load data
df = pd.read_parquet("data/features_5m.parquet").dropna()

# Select features (exclude non-feature columns)
feature_cols = [c for c in df.columns if c not in ('ts', 'label', 'signal', 'reason')]
X = df[feature_cols]
y = df['label']

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, shuffle=False
)

# Train model
model = RandomForestClassifier(n_estimators=200, random_state=42)
model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
print(classification_report(y_test, y_pred))

# Save model + feature list
model.feature_list = feature_cols  # ✅ custom attribute
joblib.dump(model, "models/smc_model.pkl")
print("Saved models/smc_model.pkl")
