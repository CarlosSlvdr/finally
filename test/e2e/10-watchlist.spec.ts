import { test, expect } from "@playwright/test";

// PLAN.md §12: Add and remove a ticker from the watchlist.
test("adding a ticker adds it to the watchlist grid", async ({ page }) => {
  await page.goto("/");

  await page.getByLabel("Add ticker").fill("pypl");
  await page.getByRole("button", { name: "Add" }).click();

  await expect(page.getByTestId("watchlist-row-PYPL")).toBeVisible();
});

test("removing a ticker removes it from the watchlist grid", async ({ page }) => {
  await page.goto("/");

  const row = page.getByTestId("watchlist-row-NFLX");
  await expect(row).toBeVisible();
  await row.getByRole("button", { name: "Remove NFLX", exact: true }).click();

  await expect(row).not.toBeVisible();
});
