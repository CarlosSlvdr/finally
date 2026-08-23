# Agent Team — Ownership & Coordination

Full spec: `planning/PLAN.md`. Market data (`backend/app/market/`) is DONE — see `planning/MARKET_DATA_SUMMARY.md`. Do not redo it; import it.

## Team members & ownership

| Role | Owns | Key deliverables |
|---|---|---|
| database-engineer | `backend/app/db/` | SQLite lazy-init schema + seed for all 6 tables in PLAN.md §7, connection helper, CRUD-style accessor functions, unit tests |
| backend-engineer | `backend/app/main.py`, `backend/app/api/` (portfolio, watchlist, trade, health), static serving | FastAPI app wiring market + db modules, REST endpoints per PLAN.md §8, unit tests |
| llm-engineer | `backend/app/chat/` (or `app/llm/`) | `/api/chat` endpoint, LiteLLM/OpenRouter/Cerebras call (use the `cerebras` skill), structured output schema, trade/watchlist auto-execution, `LLM_MOCK` deterministic mode, unit tests |
| frontend-engineer | `frontend/` | Full Next.js static-export UI per PLAN.md §10 against the documented `/api/*` contract (§8) |
| devops-engineer | `Dockerfile`, `docker-compose.yml`, `scripts/`, `.env.example` | Multi-stage build, start/stop scripts (mac + windows), volume mount for `db/` |
| integration-tester | `test/` | Playwright E2E per PLAN.md §12, `docker-compose.test.yml`, reports bugs back to the owning engineer instead of fixing out-of-scope code |

## Coordination rules

- Talk to each other directly via SendMessage when you need something the other owns (e.g. backend needs the db module's function signatures, llm-engineer needs the trade-execution function backend exposes).
- Report blockers or "done, ready for X" to `team-lead` (this session).
- Everyone owns their own unit tests (pytest for backend-side, RTL/Vitest for frontend). Only integration-tester writes Playwright E2E.
- Keep `backend/pyproject.toml` deps and `frontend/package.json` deps additive — don't remove what others added; use `uv add` / `npm install`, never hand-edit lockfiles.
- Follow root `CLAUDE.md`: no overengineering, latest APIs, small incremental commits validated as you go, no emojis.
- Env vars: `OPENROUTER_API_KEY`, `MASSIVE_API_KEY` (optional), `LLM_MOCK` — see PLAN.md §5.
