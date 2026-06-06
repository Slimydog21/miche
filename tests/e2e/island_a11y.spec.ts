import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("island a11y: 0 critical violations on home+island", async ({ page }) => {
  await page.goto("/");
  await page.locator(".miche-island__pill").click();
  await page.locator(".miche-island__input").focus();

  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();

  const critical = results.violations.filter((v) => v.impact === "critical");
  expect(critical).toEqual([]);
});

test("island voice: mic denied shows inline error", async ({ page, context }) => {
  await context.clearPermissions();
  await page.goto("/");
  await page.locator(".miche-island__pill").click();
  await page.locator(".miche-island__voice").dispatchEvent("mousedown");
  await expect(page.locator(".miche-island__msg--error")).toContainText("Microphone permission denied");
});

test("island keyboard: tab to composer and send", async ({ page }) => {
  await page.goto("/");
  const pill = page.locator(".miche-island__pill");
  for (let i = 0; i < 30; i += 1) {
    await page.keyboard.press("Tab");
    if (await pill.evaluate((el) => el === document.activeElement)) break;
  }
  await expect(pill).toBeFocused();
  await page.keyboard.press("Enter");
  const input = page.locator(".miche-island__input");
  await expect(input).toBeFocused();
  await input.fill("hello");
  await page.keyboard.press("Enter");
  await expect(page.locator(".miche-island__msg--user").filter({ hasText: "hello" })).toBeVisible();
});

test("island focus trap: tab stays inside expanded panel", async ({ page }) => {
  await page.goto("/");
  await page.locator(".miche-island__pill").click();
  const panel = page.locator("#miche-island-panel");
  const send = page.locator(".miche-island__send");
  await send.focus();
  await page.keyboard.press("Tab");
  const stillInside = await panel.evaluate((el) => el.contains(document.activeElement));
  expect(stillInside).toBe(true);
});