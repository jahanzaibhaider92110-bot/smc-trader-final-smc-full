import json
from datetime import datetime

# Example ML output (replace with real prediction)
label = "BUY"
reason = "BOS + OB + FVG + LIQ + EQ + OB_retest"
ml_label = "BUY"
ml_confidence = 0.85

signal = {
    "label": label,
    "reason": reason,
    "ml_label": ml_label,
    "ml_confidence": ml_confidence,
    "created_at": str(datetime.utcnow())
}

# Save to JSON
with open("predictions/signal.json", "w") as f:
    json.dump(signal, f, indent=4)

print("✅ Saved prediction:", signal)
