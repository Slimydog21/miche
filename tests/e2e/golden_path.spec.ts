import { test, expect } from "@playwright/test";

test("golden path: stale sessions → action_item inline card", async ({ page }) => {
  await page.goto("/");
  await page.locator(".miche-island__pill").click();

  const urlBefore = page.url();
  await page.locator(".miche-island__input").fill("any stale sessions?");
  await page.locator(".miche-island__send").click();

  const card = page.locator('.miche-island__inline-card[data-card-type="action_item"]').first();
  await expect(card).toBeVisible();
  await expect(card).toContainText("caffenagent");
  await expect(page.locator(".miche-island__msg--assistant").last()).toBeVisible();
  expect(page.url()).toBe(urlBefore);
});

test("golden path: needs_focus utterance shows CTA without auto-nav", async ({ page }) => {
  await page.goto("/");
  await page.locator(".miche-island__pill").click();

  const urlBefore = page.url();
  await page.locator(".miche-island__input").fill("open htmlspec");
  await page.locator(".miche-island__send").click();

  const cta = page.locator('[data-testid="island-focus-cta"]');
  await expect(cta).toBeVisible();
  await expect(cta).toHaveAttribute("href", /\/focus\/caffenagent/);
  expect(page.url()).toBe(urlBefore);

  await cta.click();
  await expect(page).toHaveURL(/\/focus\/caffenagent/);
});