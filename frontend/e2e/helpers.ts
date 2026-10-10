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
