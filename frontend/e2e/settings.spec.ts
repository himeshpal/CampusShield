import { expect, test } from "@playwright/test";

import { ADMIN, signIn } from "./helpers";

test("admin adds a user and the change appears in the audit log", async ({ page }) => {
  const email = `e2e.${Date.now()}@campusshield.local`;
  await signIn(page, ADMIN);
  await page.goto("/settings");

  await page.getByRole("button", { name: "Add user" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Full name").fill("E2E Lab Assistant");
  await dialog.getByLabel("Email").fill(email);
  await dialog.getByLabel("Temporary password").fill("Lab@Assist1");
  await dialog.getByRole("button", { name: "Add user" }).click();

  await expect(dialog).toBeHidden();
  await expect(page.getByRole("cell", { name: new RegExp(email.replace(".", "\\.")) })).toBeVisible();

  await page.getByRole("tab", { name: "Audit log" }).click();
  await expect(page.getByRole("cell", { name: "Created a user" }).first()).toBeVisible();

  // clean up so repeated runs don't clutter the demo data (uses the signed-in cookie)
  const users: { id: number; email: string }[] = await (
    await page.request.get("/api/v1/users")
  ).json();
  const created = users.find((u) => u.email === email)!;
  expect((await page.request.delete(`/api/v1/users/${created.id}`)).status()).toBe(204);
});

test("system tab shows all services operational", async ({ page }) => {
  await signIn(page, ADMIN);
  await page.goto("/settings");
  await page.getByRole("tab", { name: "System" }).click();
  await expect(page.getByText("Operational")).toHaveCount(3);
});

test("theme toggle switches to dark mode", async ({ page }) => {
  await signIn(page, ADMIN);
  const html = page.locator("html");
  const wasDark = (await html.getAttribute("class"))?.includes("dark") ?? false;
  await page.getByRole("button", { name: "Toggle theme" }).click();
  if (wasDark) await expect(html).not.toHaveClass(/dark/);
  else await expect(html).toHaveClass(/dark/);
});
