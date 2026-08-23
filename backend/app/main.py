"""FastAPI application entrypoint for FinAlly."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.health import router as health_router
from app.api.portfolio import router as portfolio_router
from app.api.watchlist import router as watchlist_router
from app.chat import router as chat_router
from app.db.connection import get_connection
from app.db.snapshots import record_snapshot
from app.db.watchlist import list_watchlist
from app.market import PriceCache, create_market_data_source, create_stream_router
from app.portfolio_service import compute_total_value

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SNAPSHOT_INTERVAL_SECONDS = 30
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# PLAN.md §5: the backend reads .env from the project root. Loaded here
# (rather than relying on the launching shell to export it) so OPENROUTER_API_KEY,
# MASSIVE_API_KEY, and LLM_MOCK are populated before lifespan or any request
# handler reads them via os.environ.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


async def _snapshot_loop(price_cache: PriceCache) -> None:
    """Record a portfolio value snapshot every SNAPSHOT_INTERVAL_SECONDS."""
    while True:
        await asyncio.sleep(SNAPSHOT_INTERVAL_SECONDS)
        try:
            total_value = compute_total_value(price_cache)
            record_snapshot(total_value)
        except Exception:
            logger.exception("Failed to record portfolio snapshot")


# Created at import time (not in lifespan) so the SSE router below can be
# registered before the static-file catch-all mount. Starlette matches routes
# in registration order, so a route added later (e.g. during lifespan startup)
# would be shadowed by an earlier Mount("/").
price_cache = PriceCache()


@asynccontextmanager
async def lifespan(app: FastAPI):
    with get_connection():
        pass  # triggers lazy schema creation + seeding on first connection

    market_source = create_market_data_source(price_cache)
    tickers = list_watchlist()
    await market_source.start(tickers)

    app.state.price_cache = price_cache
    app.state.market_source = market_source

    snapshot_task = asyncio.create_task(_snapshot_loop(price_cache))

    yield

    snapshot_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await snapshot_task
    await market_source.stop()


app = FastAPI(title="FinAlly", lifespan=lifespan)

# Dev convenience only: the production build is single-origin (static export
# served by this app), so no cross-origin requests occur there. This lets the
# Next.js dev server (localhost:3000) hit a locally running backend directly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(portfolio_router)
app.include_router(watchlist_router)
app.include_router(chat_router)
app.include_router(create_stream_router(price_cache))

if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
