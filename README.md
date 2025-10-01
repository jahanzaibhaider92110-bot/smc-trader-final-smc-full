# SMC-Trader Final (Ready-to-run scaffold)

## What this contains
- Backend (FastAPI) with SMC heuristics (Market Structure, Order Blocks, FVG)
- Frontend (Next.js 14 + Tailwind) with TradingView widget, dark dashboard, signals panel
- SQLite via SQLAlchemy for signals & executions
- LightGBM training stub & OpenAI explanation stub
- Config via `.env` (see `.env.example`)

## Quick start (Backend)
```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env
# edit .env - add your BINANCE_API_KEY, BINANCE_API_SECRET, OPENAI_API_KEY (optional)
uvicorn app:app --reload --port 8000
```

## Quick start (Frontend)
```bash
cd frontend
npm install
# ensure frontend/.env.local has NEXT_PUBLIC_API_BASE=http://localhost:8000
npm run dev
# open http://localhost:3000
```

## Notes
- The SMC logic in this scaffold is a heuristic implementation meant to be a functional demo.
- For production, refine SMC detectors, add thorough backtesting, realistic slippage, and risk management.
- Do not run live execution without proper safety checks and testing.
