# syntax=docker/dockerfile:1

# ---- Stage 1: build the Next.js static export ----
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
ENV NEXT_PUBLIC_USE_MOCK=false
RUN npm run build

# ---- Stage 2: Python backend + static frontend ----
FROM python:3.12-slim AS backend
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --no-dev --no-install-project

COPY backend/ ./
RUN uv sync --no-dev

# Next.js static export output directory is "out/" by default
COPY --from=frontend-build /app/frontend/out ./static

ENV PATH="/app/.venv/bin:$PATH"
ENV FINALLY_DB_PATH=/app/db/finally.db
EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
