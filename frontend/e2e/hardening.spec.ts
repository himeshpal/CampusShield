// Regressions for issues found in the full-system test pass (see docs/test-report.md).
import { expect, test } from "@playwright/test";

import { ADMIN, signIn } from "./helpers";

test("security headers on pages and proxied API responses", async ({ page }) => {
  for (const path of ["/login", "/api/v1/health"]) {
    const res = await page.request.get(path);
    const h = res.headers();
    expect(h["x-frame-options"], path).toBe("DENY");
    expect(h["x-content-type-options"], path).toBe("nosniff");
    expect(h["content-security-policy"], path).toContain("frame-ancestors 'none'");
    expect(h["x-powered-by"], path).toBeUndefined();
  }
});

test("login page loads without console errors", async ({ page }) => {
  const errors: string[] = [];
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  await page.goto("/login");
  await page.waitForLoadState("networkidle");
  expect(errors).toEqual([]);
});

test("asset detail fits a phone screen", async ({ page }) => {
  await signIn(page, ADMIN);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/assets/4");
  await expect(page.getByRole("heading", { name: "Lab 3 Workstation 01" })).toBeVisible();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);
});
