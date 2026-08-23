import type { Page } from "@playwright/test";
import { expect } from "@playwright/test";

// Header renders cash as "$0.00" until the initial GET /api/portfolio resolves;
// wait past that placeholder before treating a reading as a real baseline.
export async function readCash(page: Page): Promise<number> {
  const cashLabel = page.locator("text=Cash").locator("xpath=following-sibling::div");
  await expect(cashLabel).not.toHaveText("$0.00");
  return Number((await cashLabel.textContent())?.replace(/[^0-9.-]/g, ""));
}
