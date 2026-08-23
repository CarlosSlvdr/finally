import { test, expect } from "@playwright/test";

// Backend integration coverage for PLAN.md §12 "Buy shares" / "Sell shares" scenarios,
// driven directly against the REST API (backend/app/api/portfolio.py) since the frontend
// UI isn't built yet. Assertions use deltas rather than absolute state so the suite stays
// valid whether run against a fresh DB (docker-compose.test.yml) or a persistent dev server.

test.describe("portfolio", () => {
  test("GET /api/portfolio returns cash, positions, and total value", async ({ request }) => {
    const res = await request.get("/api/portfolio");
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(typeof body.cash_balance).toBe("number");
    expect(Array.isArray(body.positions)).toBe(true);
    expect(typeof body.total_value).toBe("number");
  });

  test("buying shares decreases cash and creates/increases a position", async ({ request }) => {
    const before = await (await request.get("/api/portfolio")).json();

    const tradeRes = await request.post("/api/portfolio/trade", {
      data: { ticker: "AAPL", side: "buy", quantity: 2 },
    });
    expect(tradeRes.ok()).toBeTruthy();
    const trade = await tradeRes.json();
    expect(trade.ticker).toBe("AAPL");
    expect(trade.side).toBe("buy");
    expect(trade.quantity).toBe(2);
    expect(trade.price).toBeGreaterThan(0);
    expect(trade.cash_balance).toBeCloseTo(before.cash_balance - trade.quantity * trade.price, 2);

    const after = await (await request.get("/api/portfolio")).json();
    expect(after.cash_balance).toBeCloseTo(trade.cash_balance, 2);
    const position = after.positions.find((p: { ticker: string }) => p.ticker === "AAPL");
    expect(position).toBeDefined();
    expect(position.quantity).toBeGreaterThanOrEqual(2);
  });

  test("selling all shares of a position increases cash and removes the row", async ({ request }) => {
    // Ensure a known position exists to sell down to zero.
    await request.post("/api/portfolio/trade", { data: { ticker: "MSFT", side: "buy", quantity: 1 } });
    const before = await (await request.get("/api/portfolio")).json();
    const owned = before.positions.find((p: { ticker: string }) => p.ticker === "MSFT").quantity;

    const sellRes = await request.post("/api/portfolio/trade", {
      data: { ticker: "MSFT", side: "sell", quantity: owned },
    });
    expect(sellRes.ok()).toBeTruthy();
    const sell = await sellRes.json();
    expect(sell.cash_balance).toBeGreaterThan(before.cash_balance);

    const after = await (await request.get("/api/portfolio")).json();
    expect(after.positions.find((p: { ticker: string }) => p.ticker === "MSFT")).toBeUndefined();
  });

  test("partial sell reduces position quantity without removing it", async ({ request }) => {
    await request.post("/api/portfolio/trade", { data: { ticker: "GOOGL", side: "buy", quantity: 4 } });
    const before = await (await request.get("/api/portfolio")).json();
    const owned = before.positions.find((p: { ticker: string }) => p.ticker === "GOOGL").quantity;

    await request.post("/api/portfolio/trade", { data: { ticker: "GOOGL", side: "sell", quantity: 1 } });

    const after = await (await request.get("/api/portfolio")).json();
    const position = after.positions.find((p: { ticker: string }) => p.ticker === "GOOGL");
    expect(position).toBeDefined();
    expect(position.quantity).toBeCloseTo(owned - 1, 6);
  });

  test("selling more shares than owned returns a validation error", async ({ request }) => {
    const res = await request.post("/api/portfolio/trade", {
      data: { ticker: "TSLA", side: "sell", quantity: 1_000_000 },
    });
    expect(res.status()).toBe(400);
    const body = await res.json();
    expect(body.detail).toMatch(/insufficient/i);
  });

  test("buying with insufficient cash returns a validation error", async ({ request }) => {
    const res = await request.post("/api/portfolio/trade", {
      data: { ticker: "NVDA", side: "buy", quantity: 1_000_000 },
    });
    expect(res.status()).toBe(400);
    const body = await res.json();
    expect(body.detail).toBeTruthy();
  });

  test("GET /api/portfolio/history returns recorded snapshots after a trade", async ({ request }) => {
    await request.post("/api/portfolio/trade", { data: { ticker: "AMZN", side: "buy", quantity: 1 } });
    const res = await request.get("/api/portfolio/history");
    expect(res.ok()).toBeTruthy();
    const snapshots = await res.json();
    expect(Array.isArray(snapshots)).toBe(true);
    expect(snapshots.length).toBeGreaterThan(0);
    expect(typeof snapshots[snapshots.length - 1].total_value).toBe("number");
  });
});
