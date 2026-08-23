import { test, expect } from "@playwright/test";
import { readCash } from "./helpers";

// PLAN.md §12: AI chat (mocked) — send a message, receive a response, trade execution
// appears inline. Requires LLM_MOCK=true. Trigger phrases confirmed with llm-engineer
// against backend/app/chat/mock.py: "buy <qty> <TICKER>" auto-executes a trade.
test("sending a chat message returns a mocked assistant response", async ({ page }) => {
  await page.goto("/");

  await page.getByLabel("Chat message").fill("what's my portfolio doing?");
  await page.getByRole("button", { name: "Send" }).click();

  await expect(page.getByText("FinAlly is thinking…")).toBeVisible();
  await expect(page.getByText("Mock response: I received your message.")).toBeVisible();
});

test("a chat message that triggers a mocked trade shows an inline execution confirmation", async ({ page }) => {
  await page.goto("/");

  const cashBefore = await readCash(page);

  await page.getByLabel("Chat message").fill("buy 1 AAPL");
  await page.getByRole("button", { name: "Send" }).click();

  await expect(page.getByText(/Mock: executed buy 1 AAPL\./)).toBeVisible();
  await expect(page.getByText(/^✓ BUY 1 AAPL$/)).toBeVisible();

  await expect.poll(() => readCash(page)).toBeLessThan(cashBefore);

  const positionsSection = page.locator("section", { hasText: "Positions" });
  await expect(positionsSection.locator("tr", { hasText: "AAPL" })).toBeVisible();
});
