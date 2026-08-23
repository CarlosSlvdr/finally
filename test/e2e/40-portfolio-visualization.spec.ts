import { test, expect } from "@playwright/test";

// PLAN.md §12: Portfolio visualization — heatmap renders with correct colors, P&L chart has data points.
test("heatmap renders a tile per position, colored by P&L sign", async ({ page }) => {
  await page.goto("/");

  await page.getByTestId("watchlist-row-TSLA").click();
  await page.getByLabel("Trade quantity").fill("3");
  await page.getByRole("button", { name: "Buy", exact: true }).click();
  await expect(page.getByRole("button", { name: "Buy", exact: true })).toBeEnabled();

  const tile = page.getByTestId("heatmap-TSLA");
  await expect(tile).toBeVisible();

  const pnlText = await tile.locator("span").last().textContent();
  const positive = (pnlText ?? "").trim().startsWith("+");

  const bg = await tile.evaluate((el) => getComputedStyle(el).backgroundColor);
  const [r, g, b] = bg.match(/[\d.]+/g)!.map(Number);
  if (positive) {
    expect(g).toBeGreaterThan(r);
  } else {
    expect(r).toBeGreaterThan(g);
  }
  void b;
});

test("P&L chart plots portfolio value over time after trades", async ({ page }) => {
  await page.goto("/");

  await page.getByTestId("watchlist-row-AMZN").click();
  await page.getByLabel("Trade quantity").fill("1");
  await page.getByRole("button", { name: "Buy", exact: true }).click();
  await expect(page.getByRole("button", { name: "Buy", exact: true })).toBeEnabled();

  // A second trade guarantees >1 snapshot so recharts renders the area chart
  // instead of the "Building history…" placeholder (PnlChart.tsx).
  await page.getByLabel("Trade quantity").fill("1");
  await page.getByRole("button", { name: "Sell", exact: true }).click();
  await expect(page.getByRole("button", { name: "Sell", exact: true })).toBeEnabled();

  await expect(page.getByText("Building history…")).not.toBeVisible();
  await expect(page.locator(".recharts-area-area")).toBeVisible();
});
