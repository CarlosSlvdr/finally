# FinAlly — AI Trading Workstation

A visually stunning AI-powered trading workstation that streams live market data, simulates portfolio trading, and integrates an LLM chat assistant that can analyze positions and execute trades via natural language.

Built entirely by coding agents as a capstone project for an agentic AI coding course. See [planning/PLAN.md](planning/PLAN.md) for the full specification.

## Status

In progress. The market data subsystem (backend) is complete — see [planning/MARKET_DATA_SUMMARY.md](planning/MARKET_DATA_SUMMARY.md). The API layer, database, AI chat integration, frontend, and Docker packaging are not yet built.

## Planned Features

- **Live price streaming** via SSE with green/red flash animations
- **Simulated portfolio** — $10k virtual cash, market orders, instant fills
- **Portfolio visualizations** — heatmap (treemap), P&L chart, positions table
- **AI chat assistant** — analyzes holdings, suggests and auto-executes trades
- **Watchlist management** — track tickers manually or via AI
- **Dark terminal aesthetic** — Bloomberg-inspired, data-dense layout

## Architecture (target)

Single Docker container serving everything on port 8000:

- **Frontend**: Next.js (static export) with TypeScript and Tailwind CSS
- **Backend**: FastAPI (Python/uv) with SSE streaming
- **Database**: SQLite with lazy initialization
- **AI**: LiteLLM → OpenRouter (Cerebras inference) with structured outputs
- **Market data**: Built-in GBM simulator (default) or Massive API (optional) — done

## Current Project Structure

```
finally/
├── backend/     # FastAPI uv project — market data subsystem implemented
├── planning/    # Project documentation and agent contracts
└── LICENSE
```

See [backend/README.md](backend/README.md) for running the backend and its tests.

## License

See [LICENSE](LICENSE).
