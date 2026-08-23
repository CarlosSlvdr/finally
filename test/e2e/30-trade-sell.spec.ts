import { test, expect } from "@playwright/test";
import { readCash } from "./helpers";

// PLAN.md §12: Sell shares — cash increases, position updates or disappears.
test("selling all shares increases cash and removes the position", async ({ page }) => {
  await page.goto("/");

  await page.getByTestId("watchlist-row-MSFT").click();
  await page.getByLabel("Trade quantity").fill("1");
  await page.getByRole("button", { name: "Buy", exact: true }).click();
  await expect(page.getByRole("button", { name: "Buy", exact: true })).toBeEnabled();

  const positionsSection = page.locator("section", { hasText: "Positions" });
  const msftRow = positionsSection.locator("tr", { hasText: "MSFT" });
  await expect(msftRow).toBeVisible();

  const cashBefore = await readCash(page);

  await page.getByRole("button", { name: "Sell", exact: true }).click();
  await expect(page.getByRole("button", { name: "Sell", exact: true })).toBeEnabled();

  await expect.poll(() => readCash(page)).toBeGreaterThan(cashBefore);
  await expect(msftRow).not.toBeVisible();
});

test("partial sell reduces position quantity without removing it", async ({ page }) => {
  await page.goto("/");

  await page.getByTestId("watchlist-row-GOOGL").click();
  await page.getByLabel("Trade quantity").fill("4");
  await page.getByRole("button", { name: "Buy", exact: true }).click();
  await expect(page.getByRole("button", { name: "Buy", exact: true })).toBeEnabled();

  const positionsSection = page.locator("section", { hasText: "Positions" });
  const googlRow = positionsSection.locator("tr", { hasText: "GOOGL" });
  await expect(googlRow).toBeVisible();
  await expect(googlRow.locator("td").nth(1)).toHaveText("4");

  await page.getByLabel("Trade quantity").fill("1");
  await page.getByRole("button", { name: "Sell", exact: true }).click();
  await expect(page.getByRole("button", { name: "Sell", exact: true })).toBeEnabled();

  await expect(googlRow).toBeVisible();
  await expect(googlRow.locator("td").nth(1)).toHaveText("3");
});
