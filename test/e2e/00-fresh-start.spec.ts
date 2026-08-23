import { test, expect } from "@playwright/test";

const DEFAULT_TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"];

// PLAN.md §12: Fresh start — default watchlist appears, $10k balance shown.
test("fresh start shows the default watchlist and $10k cash", async ({ page }) => {
  await page.goto("/");

  for (const ticker of DEFAULT_TICKERS) {
    await expect(page.getByTestId(`watchlist-row-${ticker}`)).toBeVisible();
  }

  // Cash and total portfolio value both start at $10,000.00 (no positions yet).
  await expect(page.getByText("$10,000.00")).toHaveCount(2);
});

test("prices stream live and the connection indicator shows Live", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Live")).toBeVisible({ timeout: 10_000 });
  const priceCell = page.getByTestId("watchlist-row-AAPL").locator(".tabular-nums").last();
  const initialPrice = await priceCell.textContent();
  await expect(priceCell).not.toHaveText(initialPrice ?? "", { timeout: 10_000 });
});
