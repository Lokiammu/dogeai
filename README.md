# Doge AI — SAP Order-to-Cash Graph Explorer

An interactive knowledge-graph visualisation and natural-language query system for SAP O2C data.

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- PostgreSQL 15+

### Backend
```bash
cd backend
cp .env.example .env          # edit with your real credentials
pip install -r requirements.txt
python -m app.ingest           # one-time data load
uvicorn app.main:app --reload  # http://localhost:8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev                    # http://localhost:5173
```

## Architecture
```
Frontend (React + Vite)  ←→  Backend (FastAPI)  ←→  PostgreSQL
       ↑                            ↑
 react-force-graph-2d        OpenRouter LLM
```

## License
Private — all rights reserved.
