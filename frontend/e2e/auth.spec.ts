import { expect, test } from "@playwright/test";

import { ADMIN, AUDITOR, signIn } from "./helpers";

test("protected pages redirect to login and come back after sign-in", async ({ page }) => {
  await page.goto("/settings");
  await expect(page).toHaveURL(/\/login\?next=%2Fsettings$/);

  await page.getByLabel("Email").fill(ADMIN.email);
  await page.getByLabel("Password", { exact: true }).fill(ADMIN.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/settings$/);
});

test("invalid credentials show an error and stay on login", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill("nobody@campusshield.local");
  await page.getByLabel("Password", { exact: true }).fill("wrong-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  // filter: Next.js also renders an (empty) role="alert" route announcer
  await expect(
    page.getByRole("alert").filter({ hasText: "Invalid email or password" }),
  ).toBeVisible();
  await expect(page).toHaveURL(/\/login$/); // no reload to /login?next=...
  await expect(page.getByLabel("Email")).toHaveValue("nobody@campusshield.local");
});

test("form validation runs before calling the API", async ({ page }) => {
  await page.goto("/login");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Email is required")).toBeVisible();
  await expect(page.getByText("Password is required")).toBeVisible();
});

test("admin lands on the dashboard with the app shell", async ({ page }) => {
  await signIn(page, ADMIN);
  await expect(page.getByRole("heading", { name: "Security overview" })).toBeVisible();
  await expect(page.getByText(/Good (morning|afternoon|evening), Campus IT Admin\./)).toBeVisible();
  for (const item of ["Dashboard", "Assets", "Network scans", "Checklist", "Alerts", "Reports", "Settings"]) {
    await expect(page.getByRole("link", { name: item }).first()).toBeVisible();
  }
  await expect(page.getByText("Signed in").first()).toBeVisible(); // recent activity feed
});

test("sign out ends the session", async ({ page }) => {
  await signIn(page, ADMIN);
  await page.getByRole("button", { name: /Campus IT Admin/ }).click();
  await page.getByRole("menuitem", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login$/);

  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login/);
});

test("auditor gets read-only settings (no user management)", async ({ page }) => {
  await signIn(page, AUDITOR);
  await page.goto("/settings");
  await expect(page.getByRole("tab", { name: "Audit log" })).toBeVisible();
  await expect(page.getByRole("tab", { name: "Users" })).toHaveCount(0);
});
