import { test, expect } from "@playwright/test";

// PLAN.md §12: SSE resilience — disconnect and verify reconnection.
test("connection indicator recovers after the SSE stream drops", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Live")).toBeVisible({ timeout: 10_000 });

  await page.route("**/api/stream/prices", (route) => route.abort());
  // Existing EventSource keeps retrying against the aborted route; drive a reconnect
  // attempt by reloading so the new connection attempt is the one that gets blocked.
  await page.reload();
  await expect(page.getByText(/Reconnecting|Offline/)).toBeVisible({ timeout: 10_000 });

  await page.unroute("**/api/stream/prices");
  await expect(page.getByText("Live")).toBeVisible({ timeout: 20_000 });
});
