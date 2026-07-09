# RedTeam Court — Adversarial Multi-Agent Document Review

Upload a strategic document (pitch deck, business plan, PRD, memo). Five
domain-specialist AI agents — **CFO, Legal, Competitor, Market, Execution** —
independently attack it, then cross-examine each other's findings in a debate
round, and a Judge agent synthesizes everything into a severity-scored,
evidence-cited risk report.

## 1. Architecture

```
                     ┌───────────────────────┐
                     │   React "Courtroom"    │  live SSE feed of the
                     │   Frontend (Vite)      │  attack → debate → verdict
                     └───────────┬───────────┘
                                 │ REST + Server-Sent Events
                     ┌───────────▼───────────┐
                     │   FastAPI Backend      │
                     │  routers + orchestrator│
                     └───────────┬───────────┘
                                 │
              ┌──────────────────┼───────────────────┐
              │                  │                    │
      ┌───────▼──────┐  ┌────────▼────────┐  ┌────────▼────────┐
      │  PostgreSQL   │  │  In-process      │  │  Qwen API        │
      │ (findings,    │  │  event bus       │  │ (DashScope       │
      │  debate,      │  │  (SSE pub/sub)   │  │  compatible-mode │
      │  verdict)     │  │                  │  │  OpenAI SDK)     │
      └───────────────┘  └──────────────────┘  └──────────────────┘

   Orchestration phases (backend/app/services/orchestrator.py):
   ┌─────────────┐    ┌──────────────┐    ┌─────────────┐
   │  1. ATTACK  │───▶│  2. DEBATE   │───▶│  3. VERDICT │
   │ 5 agents run│    │ agents cross-│    │ Judge agent │
   │ in parallel │    │ examine top  │    │ synthesizes │
   │ (asyncio.   │    │ findings     │    │ final       │
   │  gather)    │    │              │    │ severity-   │
   │             │    │              │    │ scored report│
   └─────────────┘    └──────────────┘    └─────────────┘
```

**Why this shape:**
- **Parallel attack phase** uses `asyncio.gather` across 5 independent Qwen
  calls — this is the "wow" moment in a demo (5 agents visibly firing at once)
  and it's also just correctly modeled: the agents shouldn't see each other's
  work until debate, or later agents anchor on earlier ones.
- **SSE instead of polling** — the courtroom view needs to feel alive turn by
  turn; a single persistent `/runs/{id}/events` stream is simpler to scale
  than websockets and works through any proxy/load balancer.
- **No Celery/Redis for the MVP** — a document review run takes seconds to a
  couple minutes, well within an HTTP request's background-task lifetime.
  `BackgroundTasks` in FastAPI is enough; the scaling section below shows the
  swap to Celery when concurrent-run volume grows.
- **Postgres from day one** — findings/debate/verdict are structured,
  relational, and get queried (severity sort, filter by agent) — a real
  schema pays off immediately, not just at scale.
- **Qwen-Agent framework** wraps the raw DashScope calls per agent
  (`backend/app/services/qwen_client.py` + `agents.py`) so each specialist is
  a `qwen_agent.Assistant` with its own system prompt/persona — swapping
  models or adding tool-use per agent later is additive.

## 2. File Structure

```
redteam-court/
├── docker-compose.yml
├── .env.example
├── db/schema.sql
├── backend/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── models.py
│       ├── schemas.py
│       ├── routers/
│       │   ├── documents.py     # upload + text extraction
│       │   └── runs.py          # start run, get state, SSE stream
│       └── services/
│           ├── text_extraction.py
│           ├── qwen_client.py   # DashScope/OpenAI-compatible client
│           ├── agents.py        # 5 specialist personas + prompts
│           ├── orchestrator.py  # attack → debate → verdict pipeline
│           └── events.py        # in-memory pub/sub for SSE per run
└── frontend/
    └── src/
        ├── App.jsx
        ├── api/client.js
        └── pages/
            ├── Upload.jsx
            ├── Courtroom.jsx    # live 5-agent attack + debate feed
            └── Verdict.jsx      # final severity-scored report
```

## 3. Database Schema — see `db/schema.sql`
`documents`, `analysis_runs`, `agent_findings`, `debate_turns`, `final_risks`.

## 4. API Endpoints

| Method | Path                              | Purpose                                   |
|--------|------------------------------------|--------------------------------------------|
| POST   | /api/v1/documents                  | Upload doc (pdf/docx/txt), extract text    |
| GET    | /api/v1/documents                  | List uploaded documents                    |
| POST   | /api/v1/documents/{id}/analyze     | Start a RedTeam run (returns run_id)       |
| GET    | /api/v1/runs/{id}                  | Full run state: findings, debate, verdict  |
| GET    | /api/v1/runs/{id}/events           | SSE stream of live phase/agent events      |
| GET    | /api/v1/runs                       | List past runs                             |
| GET    | /health                            | Liveness probe                             |

## 5. UI Architecture

- **Upload** — drag-drop a document, preview extracted text, "Convene the Court" button → creates a run and navigates to Courtroom.
- **Courtroom** (SSE-driven) — 5 live agent panels (CFO/Legal/Competitor/Market/Execution) populate with findings as they stream in; then a debate transcript feed shows cross-examination turns in real time; then auto-transitions to Verdict when the Judge finishes.
- **Verdict** — overall risk score gauge, ranked severity table with expandable evidence citations back to the source document, filter by agent/category.

## 6. Run it

```bash
cp .env.example .env   # set DASHSCOPE_API_KEY
docker compose up --build
# API:       http://localhost:8000/docs
# Dashboard: http://localhost:5173
```

## 7. Scaling path
- Swap `BackgroundTasks` for Celery+Redis once concurrent runs need to survive
  backend restarts or queue past available capacity.
- Move SSE pub/sub from in-process dict to Redis pub/sub so multiple backend
  replicas can serve the same run's stream.
- Cache per-document attack findings so re-running only the debate/verdict
  phases (e.g. after editing agent prompts) doesn't re-spend attack-phase tokens.
- Add a 6th "Devil's Advocate" meta-agent that argues the document is *fine* —
  forces the Judge to weigh a genuine counter-case, not just 5 attackers.
