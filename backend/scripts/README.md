SMC helper scripts
------------------
Run these scripts from project root (where scripts/ and backend/ exist).
Examples:
  python scripts/fetch_ohlcv.py BTC/USDT 1m data/BTCUSDT_1m.parquet
  python scripts/label_data.py data/BTCUSDT_1m.parquet data/labels.parquet
  streamlit run scripts/label_gui.py
  python scripts/features.py data/BTCUSDT_1m.parquet data/labels.parquet data/features.parquet
  python scripts/train.py data/features.parquet models/smc_lgb.txt
  python scripts/backtest.py data/features.parquet models/smc_lgb.txt

Requirements: ccxt, pandas, numpy, lightgbm, scikit-learn, streamlit, ta