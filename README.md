# Doge AI — SAP Order-to-Cash Graph Explorer

An interactive knowledge-graph visualization and natural-language query system for SAP Order-to-Cash data. Ask business questions in plain English, get SQL-backed answers, and watch the results animate across a live O2C process graph.

## Architecture

```
┌─────────────────────┐       ┌──────────────────────────────┐       ┌──────────────┐
│  React + Vite       │       │  FastAPI Backend              │       │ PostgreSQL   │
│  react-force-graph  │◄─────►│                               │◄─────►│ 19 SAP O2C   │
│  Canvas-based UI    │  /api │  ┌───────────┐ ┌───────────┐  │ async │ tables       │
│                     │       │  │ Guardrails│→│ LLM (SQL) │  │  pg   │              │
└─────────────────────┘       │  └───────────┘ └─────┬─────┘  │       └──────────────┘
                              │                      │         │
                              │  ┌───────────────────▼──────┐  │
                              │  │ SQL Validate → Execute   │  │
                              │  │ → LLM Grounded Answer    │  │
                              │  └──────────────────────────┘  │
                              │                                │
                              │  NetworkX: O2C graph builder   │
                              └────────────────────────────────┘
                                           │
                                    ┌──────▼──────┐
                                    │  OpenRouter  │
                                    │  (LLM API)  │
                                    └─────────────┘
```

### Architecture Decisions

- **PostgreSQL** — Async via `asyncpg` + SQLAlchemy 2.0. Chosen for reliable relational storage of 19 interconnected SAP tables with proper FK relationships. Connection pooling (5–20 connections) handles concurrent queries.
- **NetworkX** — Builds a directed graph (DiGraph) of the full O2C flow in-memory. Each entity (Customer, SalesOrder, Delivery, BillingDoc, JournalEntry, Payment, Product) becomes a node; relationships (PLACED_ORDER, DELIVERED_VIA, INVOICED_FROM, etc.) become edges. This powers the graph API and node-expansion queries without a dedicated graph database.
- **OpenRouter** — Provides access to free/low-cost LLMs via an OpenAI-compatible API. Currently uses `arcee-ai/trinity-large-preview:free`. Swappable to any OpenRouter model by changing one constant.
- **react-force-graph-2d** — Canvas-based force-directed graph rendering. Handles 600+ nodes smoothly without DOM overhead. Nodes are color-coded by entity type with animated traversal paths on query results.

## LLM Prompting Strategy

The system uses a **two-step LLM pipeline**:

### Step 1: Natural Language → SQL

The system prompt injects the full database schema (all 19 tables with columns, PKs, FKs, and key O2C relationships) and enforces strict rules:

- Generate **SELECT-only** queries (never DML/DDL)
- Return structured JSON: `{"sql": "SELECT ...", "explanation": "..."}`
- Reject off-topic questions with `{"sql": null, "explanation": "..."}`
- Always include currency columns with amounts
- JOIN with `product_descriptions` for readable names
- Limit to 100 rows by default
- **Temperature: 0.1** (deterministic SQL generation)

If the LLM returns invalid JSON, the system retries once with an explicit formatting instruction at temperature 0.0.

Chat history (last 6 messages) is included for follow-up question context.

### Step 2: SQL Results → Grounded Answer

After executing the SQL, results are fed back to the LLM with an explicit grounding prompt:

> "Your answer MUST be grounded in the actual data returned. Do NOT make up or hallucinate any information."

- **Temperature: 0.2** (slightly creative for readable language)
- If the LLM fails, a fallback message reports the row count directly

### Auto-Retry on SQL Errors

If the generated SQL fails execution, the error message is fed back to the LLM to self-correct. The corrected SQL is re-validated before execution.

## Guardrails

Three layers of protection prevent misuse:

### Layer 1: Keyword Pre-Filter
Before the LLM is called, user input is scanned for:

- **SQL injection patterns** (16 keywords): `DROP TABLE`, `DELETE FROM`, `UNION SELECT`, `OR 1=1`, `pg_catalog`, `information_schema`, etc.
- **Off-topic keywords** (10): `weather`, `stock price`, `sports`, `politics`, `recipe`, etc.

Blocked inputs are rejected instantly without consuming an LLM call.

### Layer 2: LLM System Prompt Enforcement
The system prompt instructs the LLM to only answer O2C-related questions. Non-dataset questions return `{"sql": null}` which the backend handles gracefully.

### Layer 3: SQL Validation (Post-Generation)
Generated SQL is parsed with `sqlparse` to confirm:
- Statement type is `SELECT`
- No disallowed keywords: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`, `GRANT`, `REVOKE`, `EXEC`

### Rate Limiting
Per-session limit of 10 LLM calls per minute (configurable via `LLM_RATE_LIMIT`).

## O2C Data Model

```
Customer ──PLACED_ORDER──► SalesOrder ──CONTAINS──► Product
                                │
                          DELIVERED_VIA
                                │
                                ▼
                            Delivery
                                │
                          INVOICED_FROM
                                │
                                ▼
                           BillingDoc ──BILLED_TO──► Customer
                                │
                            POSTED_AS
                                │
                                ▼
                          JournalEntry ──RECEIVABLE_FROM──► Customer
                                │
                           CLEARED_BY
                                │
                                ▼
                             Payment ──PAID_BY──► Customer
```

19 tables ingested from SAP JSONL exports, covering master data (partners, products, plants), sales & fulfillment, billing & revenue, and accounting & collections.

## How to Run Locally

### Prerequisites
- Python 3.12+
- Node.js 18+
- PostgreSQL 15+

### Option 1: Docker Compose (recommended)

```bash
# 1. Clone the repo
git clone https://github.com/Lokiammu/dogeai.git
cd dogeai

# 2. Create .env from template
cp .env.example .env
# Edit .env — add your OPENROUTER_API_KEY and set POSTGRES_PASSWORD

# 3. Start all services
docker-compose up -d --build

# 4. Wait for DB to be healthy, then ingest data
docker exec doge_backend python -m app.ingest

# 5. Open http://localhost
```

### Option 2: Manual Setup

```bash
# Terminal 1 — Backend
cd backend
cp .env.example .env          # edit with your credentials
pip install -r requirements.txt
python -m app.ingest           # one-time data load
uvicorn app.main:app --reload  # http://localhost:8000

# Terminal 2 — Frontend
cd frontend
npm install
npm run dev                    # http://localhost:5173
```

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `OPENROUTER_API_KEY` | OpenRouter API key (required) | — |
| `POSTGRES_PASSWORD` | PostgreSQL password | — |
| `POSTGRES_USER` | PostgreSQL user | `postgres` |
| `POSTGRES_DB` | Database name | `o2c` |
| `DATABASE_URL` | Full connection string (manual setup) | `postgresql+asyncpg://postgres:postgres@localhost:5432/o2c` |
| `CORS_ORIGINS` | Allowed origins (comma-separated) | `*` |
| `LLM_RATE_LIMIT` | Max LLM calls/min/session | `10` |
| `DATA_DIR` | Path to SAP JSONL data | `./sap-o2c-data` |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check + DB connectivity |
| `GET` | `/graph` | Full O2C graph (nodes + edges) |
| `GET` | `/graph/node/{id}/expand` | 1-hop subgraph around a node |
| `POST` | `/query` | NL question → SQL → grounded answer |
| `GET` | `/chat/history` | Chat history for session |

## Tech Stack

| Component | Technology |
|---|---|
| Backend | FastAPI, Uvicorn, SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 15 + asyncpg |
| Graph Engine | NetworkX (DiGraph) |
| LLM | OpenRouter (arcee-ai/trinity-large-preview) |
| SQL Validation | sqlparse |
| Frontend | React 18, Vite 6 |
| Graph Visualization | react-force-graph-2d (canvas) |
| Deployment | Docker Compose, Nginx reverse proxy |

## License

Private — all rights reserved.
