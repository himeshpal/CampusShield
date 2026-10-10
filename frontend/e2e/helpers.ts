import { expect, type Page } from "@playwright/test";

export const ADMIN = { email: "admin@campusshield.local", password: "Admin@123" };
export const AUDITOR = { email: "auditor@campusshield.local", password: "Auditor@123" };

export async function signIn(page: Page, account: { email: string; password: string }) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(account.email);
  await page.getByLabel("Password", { exact: true }).fill(account.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
}

/** Make sure at least one completed lab scan exists (signed-in admin page). */
export async function ensureCompletedScan(page: Page) {
  const scans: { status: string }[] = await (await page.request.get("/api/v1/scans")).json();
  if (scans.some((s) => s.status === "completed")) return;
  const res = await page.request.post("/api/v1/scans", {
    data: { target: "172.25.0.0/24", profile: "quick" },
  });
  expect(res.status()).toBe(202);
  await expect
    .poll(async () => (await page.request.get("/api/v1/scans/active")).json(), { timeout: 60_000 })
    .toBeNull();
}
