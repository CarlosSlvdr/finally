import { test, expect } from "@playwright/test";

// Backend integration coverage for PLAN.md §12 "AI chat (mocked)" scenario, driven against
// POST /api/chat with LLM_MOCK=true (backend/app/chat/mock.py). Matching rules per
// mock.py's docstring, confirmed with llm-engineer:
//   - "buy <qty> <TICKER>" / "sell <qty> <TICKER>" (case-insensitive) -> trade action(s)
//   - "watch <TICKER>" / "add <TICKER>" -> watchlist add
//   - "unwatch <TICKER>" / "remove <TICKER>" -> watchlist remove
//   - anything else -> plain acknowledgement, no actions

test.describe("chat (LLM_MOCK)", () => {
  test("a plain message returns the exact mock acknowledgement with no actions", async ({ request }) => {
    const res = await request.post("/api/chat", { data: { message: "what's my portfolio doing?" } });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.message).toBe("Mock response: I received your message.");
    expect(body.actions.trades).toEqual([]);
    expect(body.actions.watchlist_changes).toEqual([]);
  });

  test("a buy-trade message auto-executes and reflects in the portfolio", async ({ request }) => {
    const before = await (await request.get("/api/portfolio")).json();

    const res = await request.post("/api/chat", { data: { message: "buy 2 msft" } });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.message).toBe("Mock: executed buy 2 MSFT.");
    expect(body.actions.trades).toHaveLength(1);
    expect(body.actions.trades[0]).toMatchObject({ ticker: "MSFT", side: "buy", quantity: 2 });
    expect(body.actions.trades[0].error).toBeNull();
    expect(body.actions.trades[0].price).toBeGreaterThan(0);

    const after = await (await request.get("/api/portfolio")).json();
    expect(after.cash_balance).toBeLessThan(before.cash_balance);
    const position = after.positions.find((p: { ticker: string }) => p.ticker === "MSFT");
    expect(position).toBeDefined();
  });

  test("a multi-trade message executes each trade in order", async ({ request }) => {
    const res = await request.post("/api/chat", { data: { message: "buy 1 AAPL and sell 3 MSFT" } });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.actions.trades).toHaveLength(2);
    expect(body.actions.trades[0]).toMatchObject({ ticker: "AAPL", side: "buy", quantity: 1 });
    expect(body.actions.trades[1]).toMatchObject({ ticker: "MSFT", side: "sell", quantity: 3 });
  });

  test("a chat trade that fails validation reports the error instead of a 500", async ({ request }) => {
    const res = await request.post("/api/chat", { data: { message: "buy 1000000 NVDA" } });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.actions.trades).toHaveLength(1);
    expect(body.actions.trades[0].error).toBeTruthy();
    expect(body.message).toContain("failed:");
  });

  test("a watch message adds the ticker to the watchlist", async ({ request }) => {
    const res = await request.post("/api/chat", { data: { message: "watch PYPL" } });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.message).toBe("Mock: updated your watchlist.");
    expect(body.actions.watchlist_changes).toHaveLength(1);
    expect(body.actions.watchlist_changes[0]).toMatchObject({ ticker: "PYPL", action: "add" });

    const tickers = (await (await request.get("/api/watchlist")).json()).map(
      (row: { ticker: string }) => row.ticker
    );
    expect(tickers).toContain("PYPL");

    await request.delete("/api/watchlist/PYPL"); // cleanup for repeatability
  });

  test("an unwatch message removes the ticker from the watchlist", async ({ request }) => {
    await request.post("/api/watchlist", { data: { ticker: "SHOP" } });

    const res = await request.post("/api/chat", { data: { message: "unwatch SHOP" } });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.message).toBe("Mock: updated your watchlist.");
    expect(body.actions.watchlist_changes).toHaveLength(1);
    expect(body.actions.watchlist_changes[0]).toMatchObject({ ticker: "SHOP", action: "remove" });

    const tickers = (await (await request.get("/api/watchlist")).json()).map(
      (row: { ticker: string }) => row.ticker
    );
    expect(tickers).not.toContain("SHOP");
  });

  test("a message combining a trade and a watchlist change uses the combined ack", async ({ request }) => {
    const res = await request.post("/api/chat", { data: { message: "buy 1 AAPL and watch PYPL" } });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.message).toBe("Mock: executed the requested trades and watchlist changes.");
    expect(body.actions.trades).toHaveLength(1);
    expect(body.actions.watchlist_changes).toHaveLength(1);

    await request.delete("/api/watchlist/PYPL"); // cleanup for repeatability
  });
});
