import os
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split
import joblib
MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'ml', 'smc_model.pkl')
def train_dummy_model():
    df = pd.DataFrame({
        'feat1': [0,1,1,0,1,0,1,0],
        'feat2': [1,0,1,1,0,1,0,1],
        'label': [0,1,1,0,1,0,1,0]
    })
    X = df[['feat1','feat2']]
    y = df['label']
    X_train, X_val, y_train, y_val = train_test_split(X,y,test_size=0.25,random_state=42)
    train_data = lgb.Dataset(X_train, label=y_train)
    val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)
    params = {'objective':'binary','verbose':-1}
    bst = lgb.train(params, train_data, valid_sets=[val_data], num_boost_round=20, early_stopping_rounds=5)
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(bst, MODEL_PATH)
    return MODEL_PATH
def load_model():
    try:
        import joblib
        return joblib.load(MODEL_PATH)
    except Exception:
        return None
