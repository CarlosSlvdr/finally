import { test, expect } from "@playwright/test";

// Backend integration coverage for PLAN.md §12 "fresh start" watchlist contents and
// "add/remove a ticker" scenarios, driven against backend/app/api/watchlist.py.

const DEFAULT_TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"];

test.describe("watchlist", () => {
  test("GET /api/watchlist includes the seeded default tickers with price info", async ({ request }) => {
    const res = await request.get("/api/watchlist");
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    const tickers = body.map((row: { ticker: string }) => row.ticker);
    for (const ticker of DEFAULT_TICKERS) {
      expect(tickers).toContain(ticker);
    }
    const aapl = body.find((row: { ticker: string }) => row.ticker === "AAPL");
    expect(typeof aapl.price).toBe("number");
  });

  test("adding a ticker makes it appear in the watchlist", async ({ request }) => {
    const addRes = await request.post("/api/watchlist", { data: { ticker: "pypl" } });
    expect(addRes.ok()).toBeTruthy();
    expect((await addRes.json()).ticker).toBe("PYPL");

    const listRes = await request.get("/api/watchlist");
    const tickers = (await listRes.json()).map((row: { ticker: string }) => row.ticker);
    expect(tickers).toContain("PYPL");

    // cleanup so this test is repeatable against a persistent dev server
    await request.delete("/api/watchlist/PYPL");
  });

  test("removing a ticker makes it disappear from the watchlist", async ({ request }) => {
    await request.post("/api/watchlist", { data: { ticker: "SHOP" } });

    const removeRes = await request.delete("/api/watchlist/SHOP");
    expect(removeRes.ok()).toBeTruthy();
    expect((await removeRes.json()).ticker).toBe("SHOP");

    const listRes = await request.get("/api/watchlist");
    const tickers = (await listRes.json()).map((row: { ticker: string }) => row.ticker);
    expect(tickers).not.toContain("SHOP");
  });

  test("removing a ticker not on the watchlist returns 404", async ({ request }) => {
    const res = await request.delete("/api/watchlist/ZZZZZ");
    expect(res.status()).toBe(404);
  });
});
