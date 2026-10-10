import { expect, test } from "@playwright/test";

import { ADMIN, AUDITOR, signIn } from "./helpers";

test("out-of-scope targets are refused before anything is scanned", async ({ page }) => {
  await signIn(page, ADMIN);
  await page.goto("/scans");
  await page.getByRole("button", { name: "New scan" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Target").fill("8.8.8.0/24");
  await dialog.getByRole("button", { name: "Start scan" }).click();
  await expect(dialog.getByRole("alert")).toContainText("outside the authorised scan scope");
});

test("admin runs a standard scan and inspects the results", async ({ page }) => {
  test.setTimeout(120_000);
  await signIn(page, ADMIN);
  await page.goto("/scans");

  await page.getByRole("button", { name: "New scan" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByLabel("Target")).toHaveValue("172.25.0.0/24");
  await dialog.getByText("Standard audit").click();
  await expect(dialog.getByText(/--version-light/)).toBeVisible(); // command preview
  await dialog.getByRole("button", { name: "Start scan" }).click();

  // live progress card, then completion
  await expect(page.getByText(/Scan #\d+ in progress/)).toBeVisible();
  await expect(page.getByRole("progressbar", { name: "Scan progress" })).toBeVisible();
  await expect(page.getByText(/Scan #\d+ completed/)).toBeVisible({ timeout: 90_000 });

  // newest row in the history opens the detail page
  const row = page.getByRole("row").nth(1);
  await expect(row).toContainText("Completed");
  await expect(row).toContainText("172.25.0.0/24");
  await row.click();
  await expect(page).toHaveURL(/\/scans\/\d+$/);

  await expect(page.getByText("7 live hosts")).toBeVisible();
  await expect(page.getByText("Raspberry Pi Foundation")).toBeVisible();

  // expand the department web server: the outdated Apache version is identified
  await page.getByRole("button", { name: /172\.25\.0\.11/ }).click();
  await expect(page.getByRole("cell", { name: "Apache httpd 2.4.49" })).toBeVisible();
});

test("auditors can view scans but not start them", async ({ page }) => {
  await signIn(page, AUDITOR);
  await page.goto("/scans");
  await expect(page.getByText("Scan history")).toBeVisible();
  await expect(page.getByRole("row").nth(1)).toContainText("Completed"); // results visible
  await expect(page.getByRole("button", { name: "New scan" })).toHaveCount(0);
});

test("dashboard marks the first-scan step done", async ({ page }) => {
  await signIn(page, ADMIN);
  const step = page.getByRole("link", { name: /Run the first network scan/ });
  await expect(step).toContainText("Done");
});
