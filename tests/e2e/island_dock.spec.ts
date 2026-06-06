import { test, expect } from "@playwright/test";

test("island dock: collapsed pill visible, expand/collapse persists", async ({ page }) => {
  await page.goto("/");
  const pill = page.locator(".miche-island__pill");
  await expect(pill).toBeVisible();
  await expect(pill).toContainText("Ask Miche");

  const mount = page.locator("#miche-island-mount");
  await expect(mount).toHaveClass(/miche-island-mount--active/);

  await pill.click();
  const panel = page.locator("#miche-island-panel");
  await expect(panel).toBeVisible();

  const input = page.locator(".miche-island__input");
  await input.fill("what is blocked");
  await page.locator(".miche-island__send").click();
  await expect(page.locator(".miche-island__msg--assistant").last()).toBeVisible();

  await page.reload();
  await expect(panel).toBeVisible();

  await page.locator(".miche-island__collapse").click();
  await expect(pill).toBeVisible();

  await page.reload();
  await expect(pill).toBeVisible();
  await expect(panel).toBeHidden();
});