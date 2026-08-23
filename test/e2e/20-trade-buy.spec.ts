import { test, expect } from "@playwright/test";
import { readCash } from "./helpers";

// PLAN.md §12: Buy shares — cash decreases, position appears, portfolio updates.
test("buying shares decreases cash and creates a position", async ({ page }) => {
  await page.goto("/");

  const cashBefore = await readCash(page);

  await page.getByTestId("watchlist-row-AAPL").click();
  await page.getByLabel("Trade quantity").fill("2");
  await page.getByRole("button", { name: "Buy", exact: true }).click();

  await expect(page.getByRole("button", { name: "Buy", exact: true })).toBeEnabled();

  await expect.poll(() => readCash(page)).toBeLessThan(cashBefore);

  const positionsSection = page.locator("section", { hasText: "Positions" });
  await expect(positionsSection.locator("tr", { hasText: "AAPL" })).toBeVisible();
});
