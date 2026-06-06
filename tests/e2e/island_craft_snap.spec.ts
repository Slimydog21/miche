import { test, expect } from "@playwright/test";

test("craft: collapsed pill visible with label", async ({ page }) => {
  await page.goto("/");
  const pill = page.locator(".miche-island__pill");
  await expect(pill).toBeVisible();
  await expect(pill).toContainText("Ask Miche");
});

test("craft: expanded panel border and shadow tokens", async ({ page }) => {
  await page.goto("/");
  await page.locator(".miche-island__pill").click();
  const panel = page.locator(".miche-island__panel");
  await expect(panel).toBeVisible();
  const styles = await panel.evaluate((el) => {
    const s = getComputedStyle(el);
    return { borderWidth: s.borderWidth, boxShadow: s.boxShadow };
  });
  expect(styles.borderWidth).toMatch(/2px/);
  expect(styles.boxShadow).not.toBe("none");
});

test("craft: composer min-height touch target", async ({ page }) => {
  await page.goto("/");
  await page.locator(".miche-island__pill").click();
  const input = page.locator(".miche-island__input");
  const box = await input.boundingBox();
  expect(box?.height).toBeGreaterThanOrEqual(44);
});

test("craft: reduced motion still expands", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await page.locator(".miche-island__pill").click();
  await expect(page.locator("#miche-island-panel")).toBeVisible();
});