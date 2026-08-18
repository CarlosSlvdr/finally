# Market Data Backend — Design Reference

**Status:** The subsystem described here is implemented, tested, and reviewed. This document is the authoritative reference for how it works and how the rest of the backend (routes, chat, `main.py`) should integrate with it. See `planning/MARKET_DATA_SUMMARY.md` for the short version and `planning/archive/` for the original design and code review notes.

All code lives under `backend/app/market/`. Tests live under `backend/tests/market/` (73 tests, 84% coverage).

---

## Table of Contents

1. [Architecture](#1-architecture)
2. [File Structure](#2-file-structure)
3. [Data Model — `models.py`](#3-data-model--modelspy)
4. [Price Cache — `cache.py`](#4-price-cache--cachepy)
5. [Abstract Interface — `interface.py`](#5-abstract-interface--interfacepy)
6. [Seed Prices & Ticker Parameters — `seed_prices.py`](#6-seed-prices--ticker-parameters--seed_pricespy)
7. [GBM Simulator — `simulator.py`](#7-gbm-simulator--simulatorpy)
8. [Massive API Client — `massive_client.py`](#8-massive-api-client--massive_clientpy)
9. [Factory — `factory.py`](#9-factory--factorypy)
10. [SSE Streaming Endpoint — `stream.py`](#10-sse-streaming-endpoint--streampy)
11. [Package Exports — `__init__.py`](#11-package-exports--__init__py)
12. [Integrating with `main.py` (not yet built)](#12-integrating-with-mainpy-not-yet-built)
13. [Watchlist Coordination (for the watchlist routes)](#13-watchlist-coordination-for-the-watchlist-routes)
14. [Portfolio & Trade Integration](#14-portfolio--trade-integration)
15. [Testing Strategy](#15-testing-strategy)
16. [Error Handling & Edge Cases](#16-error-handling--edge-cases)
17. [Configuration Summary](#17-configuration-summary)

---

## 1. Architecture

```
                 create_market_data_source(cache)
                              │
                 reads MASSIVE_API_KEY env var
                              │
              ┌───────────────┴───────────────┐
              ▼                                ▼
   SimulatorDataSource                MassiveDataSource
   (GBM math, in-process,             (Polygon.io REST poller,
    no external deps)                  runs in asyncio.to_thread)
              │                                │
              └───────────────┬───────────────┘
                               ▼
                   PriceCache (thread-safe,
                   in-memory, versioned)
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                 ▼
   GET /api/stream/prices  Trade execution   Portfolio valuation
   (SSE, stream.py)        (reads price_cache.get_price)
```

Both data sources implement the same `MarketDataSource` ABC (strategy pattern). Neither the SSE layer nor any REST route needs to know which one is active — they only ever read from `PriceCache`. This is the core design invariant: **data sources push into the cache; everything else pulls from the cache.**

---

## 2. File Structure

```
backend/
  app/
    market/
      __init__.py         # Re-exports: PriceUpdate, PriceCache, MarketDataSource,
                           #             create_market_data_source, create_stream_router
      models.py            # PriceUpdate dataclass
      cache.py             # PriceCache (thread-safe in-memory store)
      interface.py         # MarketDataSource ABC
      seed_prices.py       # SEED_PRICES, TICKER_PARAMS, DEFAULT_PARAMS, CORRELATION_GROUPS
      simulator.py          # GBMSimulator + SimulatorDataSource
      massive_client.py    # MassiveDataSource
      factory.py            # create_market_data_source()
      stream.py             # SSE endpoint (FastAPI router factory)
  tests/
    market/
      test_models.py
      test_cache.py
      test_simulator.py
      test_simulator_source.py
      test_factory.py
      test_massive.py
  market_data_demo.py       # Rich terminal demo (uv run market_data_demo.py)
```

Each file has a single responsibility. `app/market/__init__.py` re-exports the public API so the rest of the backend never reaches into submodules directly — always `from app.market import ...`.

---

## 3. Data Model — `models.py`

`PriceUpdate` is the only data structure that leaves the market data layer. Every downstream consumer — SSE streaming, portfolio valuation, trade execution — works exclusively with this type.

```python
"""Data models for market data."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class PriceUpdate:
    """Immutable snapshot of a single ticker's price at a point in time."""

    ticker: str
    price: float
    previous_price: float
    timestamp: float = field(default_factory=time.time)  # Unix seconds

    @property
    def change(self) -> float:
        """Absolute price change from previous update."""
        return round(self.price - self.previous_price, 4)

    @property
    def change_percent(self) -> float:
        """Percentage change from previous update."""
        if self.previous_price == 0:
            return 0.0
        return round((self.price - self.previous_price) / self.previous_price * 100, 4)

    @property
    def direction(self) -> str:
        """'up', 'down', or 'flat'."""
        if self.price > self.previous_price:
            return "up"
        elif self.price < self.previous_price:
            return "down"
        return "flat"

    def to_dict(self) -> dict:
        """Serialize for JSON / SSE transmission."""
        return {
            "ticker": self.ticker,
            "price": self.price,
            "previous_price": self.previous_price,
            "timestamp": self.timestamp,
            "change": self.change,
            "change_percent": self.change_percent,
            "direction": self.direction,
        }
```

**Design decisions**

- `frozen=True`: price updates are immutable value objects, safe to share across async tasks and threads without copying or defensive locking.
- `slots=True`: many of these are created per second (10 tickers × 2 ticks/sec); slots avoid per-instance `__dict__` overhead.
- Computed properties (`change`, `change_percent`, `direction`) derive from `price`/`previous_price` so they can never drift out of sync with the underlying data — there's no stale-field risk.
- `to_dict()` is the single serialization point used by both the SSE endpoint and any REST response that embeds a price.

---

## 4. Price Cache — `cache.py`

The price cache is the central hub of the whole subsystem. Data sources write to it; SSE streaming, trade execution, and portfolio valuation read from it. It must be thread-safe because `MassiveDataSource` runs its synchronous HTTP calls in `asyncio.to_thread`, which executes in a real OS thread, not just another coroutine.

```python
"""Thread-safe in-memory price cache."""

from __future__ import annotations

import time
from threading import Lock

from .models import PriceUpdate


class PriceCache:
    """Thread-safe in-memory cache of the latest price for each ticker.

    Writers: SimulatorDataSource or MassiveDataSource (one at a time).
    Readers: SSE streaming endpoint, portfolio valuation, trade execution.
    """

    def __init__(self) -> None:
        self._prices: dict[str, PriceUpdate] = {}
        self._lock = Lock()
        self._version: int = 0  # Monotonically increasing; bumped on every update

    def update(self, ticker: str, price: float, timestamp: float | None = None) -> PriceUpdate:
        """Record a new price for a ticker. Returns the created PriceUpdate.

        Automatically computes direction and change from the previous price.
        If this is the first update for the ticker, previous_price == price (direction='flat').
        """
        with self._lock:
            ts = timestamp or time.time()
            prev = self._prices.get(ticker)
            previous_price = prev.price if prev else price

            update = PriceUpdate(
                ticker=ticker,
                price=round(price, 2),
                previous_price=round(previous_price, 2),
                timestamp=ts,
            )
            self._prices[ticker] = update
            self._version += 1
            return update

    def get(self, ticker: str) -> PriceUpdate | None:
        """Get the latest price for a single ticker, or None if unknown."""
        with self._lock:
            return self._prices.get(ticker)

    def get_all(self) -> dict[str, PriceUpdate]:
        """Snapshot of all current prices. Returns a shallow copy."""
        with self._lock:
            return dict(self._prices)

    def get_price(self, ticker: str) -> float | None:
        """Convenience: get just the price float, or None."""
        update = self.get(ticker)
        return update.price if update else None

    def remove(self, ticker: str) -> None:
        """Remove a ticker from the cache (e.g., when removed from watchlist)."""
        with self._lock:
            self._prices.pop(ticker, None)

    @property
    def version(self) -> int:
        """Current version counter. Useful for SSE change detection."""
        return self._version

    def __len__(self) -> int:
        with self._lock:
            return len(self._prices)

    def __contains__(self, ticker: str) -> bool:
        with self._lock:
            return ticker in self._prices
```

**Why a version counter?** The SSE loop polls the cache every ~500ms. Without a version counter it would serialize and push all prices on every tick even when nothing changed (e.g. Massive only updates every 15s). The counter lets the SSE loop skip a send when nothing is new:

```python
last_version = -1
while True:
    if price_cache.version != last_version:
        last_version = price_cache.version
        yield format_sse(price_cache.get_all())
    await asyncio.sleep(0.5)
```

**Why `threading.Lock` and not `asyncio.Lock`:** `MassiveDataSource._poll_once` calls `asyncio.to_thread(self._fetch_snapshots)`, which runs in a real OS thread outside the event loop. An `asyncio.Lock` only coordinates coroutines on the same loop — it would not protect the cache from that thread. `threading.Lock` works correctly from both a sync thread and the async event loop (each `with self._lock:` block is a few dict operations, so contention is negligible).

---

## 5. Abstract Interface — `interface.py`

```python
"""Abstract interface for market data sources."""

from __future__ import annotations

from abc import ABC, abstractmethod


class MarketDataSource(ABC):
    """Contract for market data providers.

    Implementations push price updates into a shared PriceCache on their own
    schedule. Downstream code never calls the data source directly for prices —
    it reads from the cache.

    Lifecycle:
        source = create_market_data_source(cache)
        await source.start(["AAPL", "GOOGL", ...])
        # ... app runs ...
        await source.add_ticker("TSLA")
        await source.remove_ticker("GOOGL")
        # ... app shutting down ...
        await source.stop()
    """

    @abstractmethod
    async def start(self, tickers: list[str]) -> None:
        """Begin producing price updates for the given tickers.

        Starts a background task that periodically writes to the PriceCache.
        Must be called exactly once. Calling start() twice is undefined behavior.
        """

    @abstractmethod
    async def stop(self) -> None:
        """Stop the background task and release resources.

        Safe to call multiple times. After stop(), the source will not write
        to the cache again.
        """

    @abstractmethod
    async def add_ticker(self, ticker: str) -> None:
        """Add a ticker to the active set. No-op if already present.

        The next update cycle will include this ticker.
        """

    @abstractmethod
    async def remove_ticker(self, ticker: str) -> None:
        """Remove a ticker from the active set. No-op if not present.

        Also removes the ticker from the PriceCache.
        """

    @abstractmethod
    def get_tickers(self) -> list[str]:
        """Return the current list of actively tracked tickers."""
```

**Why the source writes to the cache instead of returning prices from a method call:** this push model decouples timing. The simulator ticks every 500ms; Massive polls every 15s; the SSE layer always reads from the cache at its own fixed 500ms cadence regardless of which source is active. No caller needs to know an update interval or await a per-ticker fetch.

---

## 6. Seed Prices & Ticker Parameters — `seed_prices.py`

Constants only — no logic, no imports beyond stdlib. Shared by the simulator (initial prices + GBM parameters) and available as fallback data for any ticker not explicitly configured.

```python
"""Seed prices and per-ticker parameters for the market simulator."""

# Realistic starting prices for the default watchlist (as of project creation)
SEED_PRICES: dict[str, float] = {
    "AAPL": 190.00,
    "GOOGL": 175.00,
    "MSFT": 420.00,
    "AMZN": 185.00,
    "TSLA": 250.00,
    "NVDA": 800.00,
    "META": 500.00,
    "JPM": 195.00,
    "V": 280.00,
    "NFLX": 600.00,
}

# Per-ticker GBM parameters
# sigma: annualized volatility (higher = more price movement)
# mu: annualized drift / expected return
TICKER_PARAMS: dict[str, dict[str, float]] = {
    "AAPL": {"sigma": 0.22, "mu": 0.05},
    "GOOGL": {"sigma": 0.25, "mu": 0.05},
    "MSFT": {"sigma": 0.20, "mu": 0.05},
    "AMZN": {"sigma": 0.28, "mu": 0.05},
    "TSLA": {"sigma": 0.50, "mu": 0.03},  # High volatility
    "NVDA": {"sigma": 0.40, "mu": 0.08},  # High volatility, strong drift
    "META": {"sigma": 0.30, "mu": 0.05},
    "JPM": {"sigma": 0.18, "mu": 0.04},  # Low volatility (bank)
    "V": {"sigma": 0.17, "mu": 0.04},  # Low volatility (payments)
    "NFLX": {"sigma": 0.35, "mu": 0.05},
}

# Default parameters for tickers not in the list above (dynamically added)
DEFAULT_PARAMS: dict[str, float] = {"sigma": 0.25, "mu": 0.05}

# Correlation groups for the simulator's Cholesky decomposition
# Tickers in the same group have higher intra-group correlation
CORRELATION_GROUPS: dict[str, set[str]] = {
    "tech": {"AAPL", "GOOGL", "MSFT", "AMZN", "META", "NVDA", "NFLX"},
    "finance": {"JPM", "V"},
}

# Correlation coefficients
INTRA_TECH_CORR = 0.6  # Tech stocks move together
INTRA_FINANCE_CORR = 0.5  # Finance stocks move together
CROSS_GROUP_CORR = 0.3  # Between sectors / unknown tickers
TSLA_CORR = 0.3  # TSLA does its own thing
```

Note: a ticker added dynamically (e.g. via the AI chat's watchlist tool or a manual add of an unrecognized symbol) that isn't in `SEED_PRICES` gets a random seed price in `[50, 300]` and falls back to `DEFAULT_PARAMS` — see `GBMSimulator._add_ticker_internal` below. There is no separate `DEFAULT_CORR` constant; unmatched pairs fall through to `CROSS_GROUP_CORR` in `_pairwise_correlation`.

---

## 7. GBM Simulator — `simulator.py`

Two classes live here:
- `GBMSimulator` — pure math engine, stateful, holds current prices and advances them one step at a time.
- `SimulatorDataSource` — the `MarketDataSource` implementation that wraps `GBMSimulator` in an async loop and writes results to the `PriceCache`.

### 7.1 `GBMSimulator` — the math engine

```python
"""GBM-based market simulator."""

from __future__ import annotations

import asyncio
import logging
import math
import random

import numpy as np

from .cache import PriceCache
from .interface import MarketDataSource
from .seed_prices import (
    CORRELATION_GROUPS,
    CROSS_GROUP_CORR,
    DEFAULT_PARAMS,
    INTRA_FINANCE_CORR,
    INTRA_TECH_CORR,
    SEED_PRICES,
    TICKER_PARAMS,
    TSLA_CORR,
)

logger = logging.getLogger(__name__)


class GBMSimulator:
    """Geometric Brownian Motion simulator for correlated stock prices.

    Math:
        S(t+dt) = S(t) * exp((mu - sigma^2/2) * dt + sigma * sqrt(dt) * Z)

    Where:
        S(t)   = current price
        mu     = annualized drift (expected return)
        sigma  = annualized volatility
        dt     = time step as fraction of a trading year
        Z      = correlated standard normal random variable

    The tiny dt (~8.5e-8 for 500ms ticks over 252 trading days * 6.5h/day)
    produces sub-cent moves per tick that accumulate naturally over time.
    """

    # 500ms expressed as a fraction of a trading year
    # 252 trading days * 6.5 hours/day * 3600 seconds/hour = 5,896,800 seconds
    TRADING_SECONDS_PER_YEAR = 252 * 6.5 * 3600  # 5,896,800
    DEFAULT_DT = 0.5 / TRADING_SECONDS_PER_YEAR  # ~8.48e-8

    def __init__(
        self,
        tickers: list[str],
        dt: float = DEFAULT_DT,
        event_probability: float = 0.001,
    ) -> None:
        self._dt = dt
        self._event_prob = event_probability

        # Per-ticker state
        self._tickers: list[str] = []
        self._prices: dict[str, float] = {}
        self._params: dict[str, dict[str, float]] = {}

        # Cholesky decomposition of the correlation matrix (for correlated moves)
        self._cholesky: np.ndarray | None = None

        # Initialize all starting tickers
        for ticker in tickers:
            self._add_ticker_internal(ticker)
        self._rebuild_cholesky()

    # --- Public API ---

    def step(self) -> dict[str, float]:
        """Advance all tickers by one time step. Returns {ticker: new_price}.

        This is the hot path — called every 500ms. Keep it fast.
        """
        n = len(self._tickers)
        if n == 0:
            return {}

        # Generate n independent standard normal draws
        z_independent = np.random.standard_normal(n)

        # Apply Cholesky to get correlated draws
        if self._cholesky is not None:
            z_correlated = self._cholesky @ z_independent
        else:
            z_correlated = z_independent

        result: dict[str, float] = {}
        for i, ticker in enumerate(self._tickers):
            params = self._params[ticker]
            mu = params["mu"]
            sigma = params["sigma"]

            # GBM: S(t+dt) = S(t) * exp((mu - 0.5*sigma^2)*dt + sigma*sqrt(dt)*Z)
            drift = (mu - 0.5 * sigma**2) * self._dt
            diffusion = sigma * math.sqrt(self._dt) * z_correlated[i]
            self._prices[ticker] *= math.exp(drift + diffusion)

            # Random event: ~0.1% chance per tick per ticker
            # With 10 tickers at 2 ticks/sec, expect an event ~every 50 seconds
            if random.random() < self._event_prob:
                shock_magnitude = random.uniform(0.02, 0.05)
                shock_sign = random.choice([-1, 1])
                self._prices[ticker] *= 1 + shock_magnitude * shock_sign
                logger.debug(
                    "Random event on %s: %.1f%% %s",
                    ticker,
                    shock_magnitude * 100,
                    "up" if shock_sign > 0 else "down",
                )

            result[ticker] = round(self._prices[ticker], 2)

        return result

    def add_ticker(self, ticker: str) -> None:
        """Add a ticker to the simulation. Rebuilds the correlation matrix."""
        if ticker in self._prices:
            return
        self._add_ticker_internal(ticker)
        self._rebuild_cholesky()

    def remove_ticker(self, ticker: str) -> None:
        """Remove a ticker from the simulation. Rebuilds the correlation matrix."""
        if ticker not in self._prices:
            return
        self._tickers.remove(ticker)
        del self._prices[ticker]
        del self._params[ticker]
        self._rebuild_cholesky()

    def get_price(self, ticker: str) -> float | None:
        """Current price for a ticker, or None if not tracked."""
        return self._prices.get(ticker)

    def get_tickers(self) -> list[str]:
        """Return the list of currently tracked tickers."""
        return list(self._tickers)

    # --- Internals ---

    def _add_ticker_internal(self, ticker: str) -> None:
        """Add a ticker without rebuilding Cholesky (for batch initialization)."""
        if ticker in self._prices:
            return
        self._tickers.append(ticker)
        self._prices[ticker] = SEED_PRICES.get(ticker, random.uniform(50.0, 300.0))
        self._params[ticker] = TICKER_PARAMS.get(ticker, dict(DEFAULT_PARAMS))

    def _rebuild_cholesky(self) -> None:
        """Rebuild the Cholesky decomposition of the ticker correlation matrix.

        Called whenever tickers are added or removed. O(n^2) but n < 50.
        """
        n = len(self._tickers)
        if n <= 1:
            self._cholesky = None
            return

        # Build the correlation matrix
        corr = np.eye(n)
        for i in range(n):
            for j in range(i + 1, n):
                rho = self._pairwise_correlation(self._tickers[i], self._tickers[j])
                corr[i, j] = rho
                corr[j, i] = rho

        self._cholesky = np.linalg.cholesky(corr)

    @staticmethod
    def _pairwise_correlation(t1: str, t2: str) -> float:
        """Determine correlation between two tickers based on sector grouping.

        Correlation structure:
          - Same tech sector:    0.6
          - Same finance sector: 0.5
          - TSLA with anything:  0.3 (it does its own thing)
          - Cross-sector:        0.3
          - Unknown tickers:     0.3
        """
        tech = CORRELATION_GROUPS["tech"]
        finance = CORRELATION_GROUPS["finance"]

        # TSLA is in the tech set but behaves independently
        if t1 == "TSLA" or t2 == "TSLA":
            return TSLA_CORR

        if t1 in tech and t2 in tech:
            return INTRA_TECH_CORR
        if t1 in finance and t2 in finance:
            return INTRA_FINANCE_CORR

        return CROSS_GROUP_CORR
```

### 7.2 `SimulatorDataSource` — async wrapper

```python
class SimulatorDataSource(MarketDataSource):
    """MarketDataSource backed by the GBM simulator.

    Runs a background asyncio task that calls GBMSimulator.step() every
    `update_interval` seconds and writes results to the PriceCache.
    """

    def __init__(
        self,
        price_cache: PriceCache,
        update_interval: float = 0.5,
        event_probability: float = 0.001,
    ) -> None:
        self._cache = price_cache
        self._interval = update_interval
        self._event_prob = event_probability
        self._sim: GBMSimulator | None = None
        self._task: asyncio.Task | None = None

    async def start(self, tickers: list[str]) -> None:
        self._sim = GBMSimulator(
            tickers=tickers,
            event_probability=self._event_prob,
        )
        # Seed the cache with initial prices so SSE has data immediately
        for ticker in tickers:
            price = self._sim.get_price(ticker)
            if price is not None:
                self._cache.update(ticker=ticker, price=price)
        self._task = asyncio.create_task(self._run_loop(), name="simulator-loop")
        logger.info("Simulator started with %d tickers", len(tickers))

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("Simulator stopped")

    async def add_ticker(self, ticker: str) -> None:
        if self._sim:
            self._sim.add_ticker(ticker)
            # Seed cache immediately so the ticker has a price right away
            price = self._sim.get_price(ticker)
            if price is not None:
                self._cache.update(ticker=ticker, price=price)
            logger.info("Simulator: added ticker %s", ticker)

    async def remove_ticker(self, ticker: str) -> None:
        if self._sim:
            self._sim.remove_ticker(ticker)
        self._cache.remove(ticker)
        logger.info("Simulator: removed ticker %s", ticker)

    def get_tickers(self) -> list[str]:
        return self._sim.get_tickers() if self._sim else []

    async def _run_loop(self) -> None:
        """Core loop: step the simulation, write to cache, sleep."""
        while True:
            try:
                if self._sim:
                    prices = self._sim.step()
                    for ticker, price in prices.items():
                        self._cache.update(ticker=ticker, price=price)
            except Exception:
                logger.exception("Simulator step failed")
            await asyncio.sleep(self._interval)
```

**Key behaviors**

- **Immediate seeding.** `start()` populates the cache with seed prices *before* the loop begins, so the SSE endpoint has data to send on its very first tick — no blank-screen delay on fresh page load.
- **Graceful cancellation.** `stop()` cancels the task and awaits it, swallowing `CancelledError`. Clean shutdown during FastAPI lifespan teardown.
- **Exception resilience.** The loop catches exceptions per-step so a single bad tick can't kill the whole feed; it logs and continues on the next interval.
- **Encapsulation.** `get_tickers()` delegates to `GBMSimulator.get_tickers()` rather than reaching into `self._sim._tickers` — keeps the class boundary clean (this was a code-review fix over the original draft).

---

## 8. Massive API Client — `massive_client.py`

Polls the Massive (Polygon.io) REST snapshot endpoint on a configurable interval. `massive` is a core dependency (see `pyproject.toml`), so the import is at module level — no lazy import needed since the package is always installed, whether or not `MASSIVE_API_KEY` is set.

```python
"""Massive (Polygon.io) API client for real market data."""

from __future__ import annotations

import asyncio
import logging

from massive import RESTClient
from massive.rest.models import SnapshotMarketType

from .cache import PriceCache
from .interface import MarketDataSource

logger = logging.getLogger(__name__)


class MassiveDataSource(MarketDataSource):
    """MarketDataSource backed by the Massive (Polygon.io) REST API.

    Polls GET /v2/snapshot/locale/us/markets/stocks/tickers for all watched
    tickers in a single API call, then writes results to the PriceCache.

    Rate limits:
      - Free tier: 5 req/min → poll every 15s (default)
      - Paid tiers: higher limits → poll every 2-5s
    """

    def __init__(
        self,
        api_key: str,
        price_cache: PriceCache,
        poll_interval: float = 15.0,
    ) -> None:
        self._api_key = api_key
        self._cache = price_cache
        self._interval = poll_interval
        self._tickers: list[str] = []
        self._task: asyncio.Task | None = None
        self._client: RESTClient | None = None

    async def start(self, tickers: list[str]) -> None:
        self._client = RESTClient(api_key=self._api_key)
        self._tickers = list(tickers)

        # Do an immediate first poll so the cache has data right away
        await self._poll_once()

        self._task = asyncio.create_task(self._poll_loop(), name="massive-poller")
        logger.info(
            "Massive poller started: %d tickers, %.1fs interval",
            len(tickers),
            self._interval,
        )

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        self._client = None
        logger.info("Massive poller stopped")

    async def add_ticker(self, ticker: str) -> None:
        ticker = ticker.upper().strip()
        if ticker not in self._tickers:
            self._tickers.append(ticker)
            logger.info("Massive: added ticker %s (will appear on next poll)", ticker)

    async def remove_ticker(self, ticker: str) -> None:
        ticker = ticker.upper().strip()
        self._tickers = [t for t in self._tickers if t != ticker]
        self._cache.remove(ticker)
        logger.info("Massive: removed ticker %s", ticker)

    def get_tickers(self) -> list[str]:
        return list(self._tickers)

    # --- Internal ---

    async def _poll_loop(self) -> None:
        """Poll on interval. First poll already happened in start()."""
        while True:
            await asyncio.sleep(self._interval)
            await self._poll_once()

    async def _poll_once(self) -> None:
        """Execute one poll cycle: fetch snapshots, update cache."""
        if not self._tickers or not self._client:
            return

        try:
            # The Massive RESTClient is synchronous — run in a thread to
            # avoid blocking the event loop.
            snapshots = await asyncio.to_thread(self._fetch_snapshots)
            processed = 0
            for snap in snapshots:
                try:
                    price = snap.last_trade.price
                    # Massive timestamps are Unix milliseconds → convert to seconds
                    timestamp = snap.last_trade.timestamp / 1000.0
                    self._cache.update(
                        ticker=snap.ticker,
                        price=price,
                        timestamp=timestamp,
                    )
                    processed += 1
                except (AttributeError, TypeError) as e:
                    logger.warning(
                        "Skipping snapshot for %s: %s",
                        getattr(snap, "ticker", "???"),
                        e,
                    )
            logger.debug("Massive poll: updated %d/%d tickers", processed, len(self._tickers))

        except Exception as e:
            logger.error("Massive poll failed: %s", e)
            # Don't re-raise — the loop will retry on the next interval.
            # Common failures: 401 (bad key), 429 (rate limit), network errors.

    def _fetch_snapshots(self) -> list:
        """Synchronous call to the Massive REST API. Runs in a thread."""
        return self._client.get_snapshot_all(
            market_type=SnapshotMarketType.STOCKS,
            tickers=self._tickers,
        )
```

**Error handling philosophy** — the poller is intentionally resilient; a bad tick never kills the loop:

| Error | Behavior |
|---|---|
| 401 Unauthorized | Logged as error. Poller keeps running (user might fix `.env` and restart). |
| 429 Rate limited | Logged as error. Next poll retries after `poll_interval` seconds. |
| Network timeout | Logged as error. Retries automatically on the next cycle. |
| Malformed snapshot for one ticker | That ticker is skipped with a warning; other tickers in the same poll still process. |
| All tickers fail | Cache retains last-known prices. SSE keeps streaming stale data — better than no data at all. |

**Why `_fetch_snapshots` is a separate method:** it isolates the one synchronous, blocking call (`RESTClient.get_snapshot_all`) so `_poll_once` can hand it to `asyncio.to_thread` cleanly, and so tests can patch just that method without needing a real `massive` package or network access.

---

## 9. Factory — `factory.py`

```python
"""Factory for creating market data sources."""

from __future__ import annotations

import logging
import os

from .cache import PriceCache
from .interface import MarketDataSource
from .massive_client import MassiveDataSource
from .simulator import SimulatorDataSource

logger = logging.getLogger(__name__)


def create_market_data_source(price_cache: PriceCache) -> MarketDataSource:
    """Create the appropriate market data source based on environment variables.

    - MASSIVE_API_KEY set and non-empty → MassiveDataSource (real market data)
    - Otherwise → SimulatorDataSource (GBM simulation)

    Returns an unstarted source. Caller must await source.start(tickers).
    """
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()

    if api_key:
        logger.info("Market data source: Massive API (real data)")
        return MassiveDataSource(api_key=api_key, price_cache=price_cache)
    else:
        logger.info("Market data source: GBM Simulator")
        return SimulatorDataSource(price_cache=price_cache)
```

Usage at app startup:

```python
price_cache = PriceCache()
source = create_market_data_source(price_cache)
await source.start(initial_tickers)  # e.g., ["AAPL", "GOOGL", ...]
```

This is the *only* place in the codebase that should branch on `MASSIVE_API_KEY`. Everything downstream — routes, chat, SSE — takes a `MarketDataSource` or a `PriceCache` and stays agnostic to which implementation is live.

---

## 10. SSE Streaming Endpoint — `stream.py`

A FastAPI route that holds open a long-lived HTTP connection and pushes price updates as `text/event-stream`.

```python
"""SSE streaming endpoint for live price updates."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from .cache import PriceCache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stream", tags=["streaming"])


def create_stream_router(price_cache: PriceCache) -> APIRouter:
    """Create the SSE streaming router with a reference to the price cache.

    This factory pattern lets us inject the PriceCache without globals.
    """

    @router.get("/prices")
    async def stream_prices(request: Request) -> StreamingResponse:
        """SSE endpoint for live price updates.

        Streams all tracked ticker prices every ~500ms. The client connects
        with EventSource and receives events in the format:

            data: {"AAPL": {"ticker": "AAPL", "price": 190.50, ...}, ...}

        Includes a retry directive so the browser auto-reconnects on
        disconnection (EventSource built-in behavior).
        """
        return StreamingResponse(
            _generate_events(price_cache, request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering if proxied
            },
        )

    return router


async def _generate_events(
    price_cache: PriceCache,
    request: Request,
    interval: float = 0.5,
) -> AsyncGenerator[str, None]:
    """Async generator that yields SSE-formatted price events.

    Sends all prices every `interval` seconds. Stops when the client
    disconnects (detected via request.is_disconnected()).
    """
    # Tell the client to retry after 1 second if the connection drops
    yield "retry: 1000\n\n"

    last_version = -1
    client_ip = request.client.host if request.client else "unknown"
    logger.info("SSE client connected: %s", client_ip)

    try:
        while True:
            # Check for client disconnect
            if await request.is_disconnected():
                logger.info("SSE client disconnected: %s", client_ip)
                break

            current_version = price_cache.version
            if current_version != last_version:
                last_version = current_version
                prices = price_cache.get_all()

                if prices:
                    data = {ticker: update.to_dict() for ticker, update in prices.items()}
                    payload = json.dumps(data)
                    yield f"data: {payload}\n\n"

            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        logger.info("SSE stream cancelled for: %s", client_ip)
```

**Wire format** — each event the client receives:

```
data: {"AAPL":{"ticker":"AAPL","price":190.50,"previous_price":190.42,"timestamp":1707580800.5,"change":0.08,"change_percent":0.042,"direction":"up"},"GOOGL":{"ticker":"GOOGL","price":175.12,...}}

```

Frontend consumption:

```javascript
const eventSource = new EventSource('/api/stream/prices');
eventSource.onmessage = (event) => {
    const prices = JSON.parse(event.data);
    // prices is { "AAPL": { ticker, price, previous_price, change, change_percent, direction, timestamp }, ... }
    for (const [ticker, update] of Object.entries(prices)) {
        applyPriceFlash(ticker, update.direction);   // green/red CSS flash
        appendSparklinePoint(ticker, update.price);  // accumulate since page load
    }
};
```

**Why poll-and-push instead of event-driven push from the data source:** the SSE loop polls the cache on a fixed interval rather than being notified by the producer. This keeps the SSE layer fully decoupled from which data source is active (500ms simulator vs 15s Massive poll) and produces evenly-spaced updates, which matters for the frontend's sparkline accumulation — irregular spacing would distort the mini-chart shape.

**Known limitation (accepted for this project's scope):** the router pattern uses a module-level `router` and registers the `/prices` route via closure inside `create_stream_router()`. This is safe because `create_stream_router()` is called exactly once during app startup (see §12). Calling it twice (e.g. across two app instances in the same process, such as parallel test runs sharing the module) would double-register the route on the shared router object — not a concern for a single-instance FastAPI app, but worth knowing if writing SSE integration tests that instantiate the app multiple times in-process.

---

## 11. Package Exports — `__init__.py`

```python
"""Market data subsystem for FinAlly.

Public API:
    PriceUpdate         - Immutable price snapshot dataclass
    PriceCache          - Thread-safe in-memory price store
    MarketDataSource    - Abstract interface for data providers
    create_market_data_source - Factory that selects simulator or Massive
    create_stream_router - FastAPI router factory for SSE endpoint
"""

from .cache import PriceCache
from .factory import create_market_data_source
from .interface import MarketDataSource
from .models import PriceUpdate
from .stream import create_stream_router

__all__ = [
    "PriceUpdate",
    "PriceCache",
    "MarketDataSource",
    "create_market_data_source",
    "create_stream_router",
]
```

All other backend code should import exclusively from `app.market`, never `app.market.cache` or similar — this keeps the internal module layout free to change without breaking call sites.

---

## 12. Integrating with `main.py` (not yet built)

`backend/app/main.py` does not exist yet — this section is the contract the Backend Engineer building it should follow. The market data system starts and stops with the FastAPI app via the `lifespan` context manager.

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.market import PriceCache, MarketDataSource, create_market_data_source, create_stream_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown of background services."""

    # --- STARTUP ---

    # 1. Ensure the DB exists and is seeded (lazy init — see PLAN.md §7)
    await init_db()

    # 2. Create the shared price cache
    price_cache = PriceCache()
    app.state.price_cache = price_cache

    # 3. Create and start the market data source
    source = create_market_data_source(price_cache)
    app.state.market_source = source

    # 4. Load initial tickers from the database watchlist (not the SEED_PRICES
    #    default — the DB is the source of truth once seeded)
    initial_tickers = await load_watchlist_tickers()  # SELECT ticker FROM watchlist
    await source.start(initial_tickers)

    # 5. Register the SSE streaming router
    app.include_router(create_stream_router(price_cache))

    yield  # App is running

    # --- SHUTDOWN ---
    await source.stop()


app = FastAPI(title="FinAlly", lifespan=lifespan)
```

**Dependency injection for other routers.** Portfolio, watchlist, and chat routes need access to `price_cache` and `source`. Use FastAPI `Depends`, reading from `app.state` via the request:

```python
from fastapi import Request


def get_price_cache(request: Request) -> PriceCache:
    return request.app.state.price_cache


def get_market_source(request: Request) -> MarketDataSource:
    return request.app.state.market_source
```

Using `request.app.state` (rather than a module-level global bound at import time) avoids import-order issues and works correctly under the test client, which constructs its own `FastAPI` instance per test.

---

## 13. Watchlist Coordination (for the watchlist routes)

When the watchlist changes — via `POST /api/watchlist`, `DELETE /api/watchlist/{ticker}`, or the AI chat's `watchlist_changes` action — the market data source must be told, so it tracks the right set of tickers. The route/service layer, not the market module, owns this coordination; `MarketDataSource.add_ticker`/`remove_ticker` are the hooks.

**Adding a ticker**

```python
@router.post("/api/watchlist")
async def add_to_watchlist(
    payload: WatchlistAdd,
    source: MarketDataSource = Depends(get_market_source),
):
    ticker = payload.ticker.upper().strip()

    await db.insert_watchlist_entry(ticker)   # UNIQUE(user_id, ticker) enforces no dupes
    await source.add_ticker(ticker)
    # Simulator: seeds a price into the cache synchronously, so a price is
    #            available in the very next SSE event.
    # Massive:   ticker appears on the next poll cycle (up to poll_interval
    #            seconds later) — there may be a brief window with no price.

    return {"ticker": ticker, "status": "ok"}
```

**Removing a ticker**

```python
@router.delete("/api/watchlist/{ticker}")
async def remove_from_watchlist(
    ticker: str,
    source: MarketDataSource = Depends(get_market_source),
):
    ticker = ticker.upper().strip()

    # Keep tracking the ticker if the user still holds a position in it —
    # portfolio valuation and the positions table need a live price even
    # for tickers no longer on the watchlist.
    position = await db.get_position(ticker)
    if position is None or position.quantity == 0:
        await source.remove_ticker(ticker)

    await db.delete_watchlist_entry(ticker)
    return {"status": "ok"}
```

This "keep tracking if a position is open" rule is the one piece of business logic layered on top of the raw `MarketDataSource` interface — the market module itself has no concept of positions, only tickers.

---

## 14. Portfolio & Trade Integration

Trade execution and portfolio valuation are pure readers of `PriceCache`; they never touch the data source directly.

```python
@router.post("/api/portfolio/trade")
async def execute_trade(
    trade: TradeRequest,
    price_cache: PriceCache = Depends(get_price_cache),
):
    current_price = price_cache.get_price(trade.ticker)
    if current_price is None:
        raise HTTPException(
            status_code=400,
            detail=f"Price not yet available for {trade.ticker}. Please wait a moment and try again.",
        )

    # Market order, instant fill at current_price — no order book, no partial fills.
    # ... validate cash/shares, write to positions + trades tables, update cash_balance ...
```

Portfolio valuation (`GET /api/portfolio`) sums `quantity * price_cache.get_price(ticker)` across all open positions, falling back to `avg_cost` only if a price is momentarily missing (should not normally happen once a position exists, since a position implies the ticker was tradeable and therefore priced).

---

## 15. Testing Strategy

**73 tests across 6 modules, 84% overall coverage** (`backend/tests/market/`). Run with:

```bash
cd backend
uv run --extra dev pytest -v              # all tests
uv run --extra dev pytest --cov=app       # with coverage
uv run --extra dev ruff check app/ tests/ # lint
```

| Module | Tests | Coverage | Notes |
|---|---|---|---|
| `test_models.py` | 11 | `models.py`: 100% | |
| `test_cache.py` | 13 | `cache.py`: 100% | |
| `test_simulator.py` | 17 | `simulator.py`: 98% | Unit tests for `GBMSimulator` math |
| `test_simulator_source.py` | 10 | (integration) | Async lifecycle tests for `SimulatorDataSource` |
| `test_factory.py` | 7 | `factory.py`: 100% | Env-var branching, monkeypatched |
| `test_massive.py` | 13 | `massive_client.py`: 56% | Real API calls mocked via `patch.object(source, "_fetch_snapshots", ...)` |

### 15.1 `GBMSimulator` — representative cases

```python
import pytest
from app.market.simulator import GBMSimulator
from app.market.seed_prices import SEED_PRICES


class TestGBMSimulator:
    def test_step_returns_all_tickers(self):
        sim = GBMSimulator(tickers=["AAPL", "GOOGL"])
        result = sim.step()
        assert set(result.keys()) == {"AAPL", "GOOGL"}

    def test_prices_are_positive(self):
        """GBM prices can never go negative (exp() is always positive)."""
        sim = GBMSimulator(tickers=["AAPL"])
        for _ in range(10_000):
            prices = sim.step()
            assert prices["AAPL"] > 0

    def test_initial_prices_match_seeds(self):
        sim = GBMSimulator(tickers=["AAPL"])
        assert sim.get_price("AAPL") == SEED_PRICES["AAPL"]

    def test_add_ticker_rebuilds_cholesky(self):
        sim = GBMSimulator(tickers=["AAPL"])
        assert sim._cholesky is None  # Only 1 ticker, no correlation matrix
        sim.add_ticker("GOOGL")
        assert sim._cholesky is not None

    def test_remove_ticker(self):
        sim = GBMSimulator(tickers=["AAPL", "GOOGL"])
        sim.remove_ticker("GOOGL")
        result = sim.step()
        assert "GOOGL" not in result
        assert "AAPL" in result

    def test_unknown_ticker_gets_random_seed_price(self):
        sim = GBMSimulator(tickers=["ZZZZ"])
        price = sim.get_price("ZZZZ")
        assert 50.0 <= price <= 300.0

    def test_get_tickers_public_accessor(self):
        sim = GBMSimulator(tickers=["AAPL", "GOOGL"])
        assert sim.get_tickers() == ["AAPL", "GOOGL"]
```

### 15.2 `PriceCache` — representative cases

```python
from app.market.cache import PriceCache


class TestPriceCache:
    def test_first_update_is_flat(self):
        cache = PriceCache()
        update = cache.update("AAPL", 190.50)
        assert update.direction == "flat"
        assert update.previous_price == 190.50

    def test_direction_up_and_down(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        up = cache.update("AAPL", 191.00)
        assert up.direction == "up" and up.change == 1.00
        down = cache.update("AAPL", 189.00)
        assert down.direction == "down"

    def test_version_increments_on_every_update(self):
        cache = PriceCache()
        v0 = cache.version
        cache.update("AAPL", 190.00)
        assert cache.version == v0 + 1

    def test_remove_evicts_ticker(self):
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        cache.remove("AAPL")
        assert cache.get("AAPL") is None
```

### 15.3 `SimulatorDataSource` — async integration

```python
import asyncio
import pytest
from app.market.cache import PriceCache
from app.market.simulator import SimulatorDataSource


@pytest.mark.asyncio
class TestSimulatorDataSource:
    async def test_start_populates_cache_immediately(self):
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.1)
        await source.start(["AAPL", "GOOGL"])
        assert cache.get("AAPL") is not None  # Seeded before the loop's first tick
        await source.stop()

    async def test_add_and_remove_ticker(self):
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.1)
        await source.start(["AAPL"])

        await source.add_ticker("TSLA")
        assert "TSLA" in source.get_tickers()
        assert cache.get("TSLA") is not None

        await source.remove_ticker("TSLA")
        assert "TSLA" not in source.get_tickers()
        assert cache.get("TSLA") is None

        await source.stop()

    async def test_double_stop_is_safe(self):
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.1)
        await source.start(["AAPL"])
        await source.stop()
        await source.stop()  # Must not raise
```

### 15.4 `MassiveDataSource` — mocked, no network/package dependency in the mock path

```python
from unittest.mock import MagicMock, patch
import pytest
from app.market.cache import PriceCache
from app.market.massive_client import MassiveDataSource


def _make_snapshot(ticker: str, price: float, timestamp_ms: int) -> MagicMock:
    snap = MagicMock()
    snap.ticker = ticker
    snap.last_trade.price = price
    snap.last_trade.timestamp = timestamp_ms
    return snap


@pytest.mark.asyncio
class TestMassiveDataSource:
    async def test_poll_updates_cache(self):
        cache = PriceCache()
        source = MassiveDataSource(api_key="test-key", price_cache=cache, poll_interval=60.0)
        mock_snapshots = [_make_snapshot("AAPL", 190.50, 1707580800000)]

        with patch.object(source, "_fetch_snapshots", return_value=mock_snapshots):
            await source._poll_once()

        assert cache.get_price("AAPL") == 190.50

    async def test_malformed_snapshot_is_skipped_not_fatal(self):
        cache = PriceCache()
        source = MassiveDataSource(api_key="test-key", price_cache=cache, poll_interval=60.0)
        source._tickers = ["AAPL", "BAD"]

        good = _make_snapshot("AAPL", 190.50, 1707580800000)
        bad = MagicMock(ticker="BAD", last_trade=None)  # AttributeError on access

        with patch.object(source, "_fetch_snapshots", return_value=[good, bad]):
            await source._poll_once()

        assert cache.get_price("AAPL") == 190.50
        assert cache.get_price("BAD") is None

    async def test_api_error_does_not_crash_the_loop(self):
        cache = PriceCache()
        source = MassiveDataSource(api_key="test-key", price_cache=cache, poll_interval=60.0)
        source._tickers = ["AAPL"]

        with patch.object(source, "_fetch_snapshots", side_effect=Exception("network error")):
            await source._poll_once()  # Must not raise

        assert cache.get_price("AAPL") is None
```

Because `massive_client.py` imports `RESTClient` at module level (a core dependency, not lazily imported), these tests patch `_fetch_snapshots` on the instance rather than patching `RESTClient` itself — this avoids needing a real network call or a live API key while still exercising the real `_poll_once` control flow (success path, partial-failure path, total-failure path).

### 15.5 Coverage gaps (known, accepted)

- `stream.py` sits at ~31% coverage — the SSE generator needs a running ASGI server (`httpx.AsyncClient` against the app) to exercise meaningfully. A basic SSE integration test is worth adding once `main.py` exists, since `stream.py` is the primary consumer of `PriceCache`.
- No dedicated concurrent-writer stress test for `PriceCache` — the lock usage is straightforward enough that this wasn't prioritized, but a multi-thread write test would give empirical confidence if the cache logic ever changes.

---

## 16. Error Handling & Edge Cases

**Empty watchlist at startup.** If the DB has no watchlist rows, `source.start([])` is called with an empty list. Both sources handle this gracefully — the simulator's `GBMSimulator.step()` returns `{}` for zero tickers; the Massive poller's `_poll_once()` short-circuits when `self._tickers` is empty. The SSE endpoint simply sends nothing until a ticker is added.

**Price cache miss during trade.** If a user tries to trade a ticker with no cached price (just added to the watchlist, Massive hasn't polled yet):

```python
price = price_cache.get_price(ticker)
if price is None:
    raise HTTPException(400, f"Price not yet available for {ticker}. Please wait a moment and try again.")
```

The simulator avoids this window entirely by seeding the cache synchronously inside `add_ticker()`. Massive has an inherent gap of up to `poll_interval` seconds — the 400 response with a clear message is the correct behavior, not a bug to work around.

**Invalid Massive API key.** The first poll fails with 401; the poller logs and keeps retrying every `poll_interval` seconds (it does not stop). The SSE endpoint keeps streaming — with no data, since the cache never gets populated. The user sees a "connected" status dot (SSE itself works) but an empty watchlist grid. Fix: correct `MASSIVE_API_KEY` in `.env` and restart the container.

**Thread safety under load.** `PriceCache` uses a single `threading.Lock`. At the project's scale (≤ ~10-20 tickers, 2 updates/sec from the simulator or 1 poll/15s from Massive, one SSE reader per connected browser tab) lock contention is negligible — each critical section is a dict lookup/assignment. A `ReadWriteLock` would be the fix if this ever became a bottleneck (hundreds of tickers, many concurrent SSE readers), but that's out of scope for a single-user simulated trading app.

**Floating-point precision in GBM.** The tiny `dt` (~8.5e-8) produces very small per-tick log-returns. This is not a precision concern: prices are `round()`ed to 2 decimals in `GBMSimulator.step()`, the exponential formulation is numerically stable for these magnitudes, and GBM prices are always strictly positive by construction (`exp(...)` never returns ≤ 0).

---

## 17. Configuration Summary

| Parameter | Location | Default | Description |
|---|---|---|---|
| `MASSIVE_API_KEY` | Environment variable | `""` (empty) | If set and non-empty → Massive API; otherwise → simulator |
| `update_interval` | `SimulatorDataSource.__init__` | `0.5` (seconds) | Time between simulator ticks |
| `event_probability` | `GBMSimulator.__init__` | `0.001` | Chance of a random shock event per ticker per tick (~2-5% move) |
| `dt` | `GBMSimulator.__init__` | `~8.48e-8` | GBM time step, as a fraction of a trading year |
| `poll_interval` | `MassiveDataSource.__init__` | `15.0` (seconds) | Time between Massive API polls (tune per API tier) |
| SSE push interval | `_generate_events()` | `0.5` (seconds) | Cadence the SSE loop checks `price_cache.version` |
| SSE retry directive | `_generate_events()` | `1000` (ms) | Browser `EventSource` auto-reconnect delay |

**Dependencies** (`backend/pyproject.toml`): `fastapi`, `uvicorn[standard]`, `numpy` (GBM/Cholesky math), `massive` (Polygon.io client, core dependency — always installed, only used when `MASSIVE_API_KEY` is set), `rich` (terminal demo only). Dev: `pytest`, `pytest-asyncio`, `pytest-cov`, `ruff`.

**Manual/demo verification** — a Rich terminal dashboard exercises the simulator end-to-end without needing the rest of the backend built:

```bash
cd backend
uv run market_data_demo.py
```

Shows all 10 default tickers with live sparklines, color-coded direction arrows, and an event log for notable shock moves. Runs for 60 seconds or until Ctrl+C — useful for sanity-checking simulator behavior (drift, volatility, correlation, event frequency) visually before wiring it into the API layer.
