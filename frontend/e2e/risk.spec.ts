import { expect, test } from "@playwright/test";

import { ADMIN, AUDITOR, ensureCompletedScan, signIn } from "./helpers";

test.beforeEach(async ({ page }) => {
  await signIn(page, ADMIN);
  await ensureCompletedScan(page);
});

test("asset page explains its score down to the CVE", async ({ page }) => {
  await page.goto("/assets/2"); // Department Website, Apache 2.4.49
  await expect(page.getByRole("meter", { name: "Risk score" })).toBeVisible();
  await expect(page.getByText("High risk")).toBeVisible();
  await expect(page.getByText("Why this score")).toBeVisible();
  await expect(page.getByText(/min\(100, \(4 \+ 40 \+ 0 \+ \d+ \+ 0\) x 1\.06\)/)).toBeVisible();
  const cve = page.getByRole("link", { name: /CVE-2021-41773 in Apache httpd 2\.4\.49/ });
  await expect(cve).toHaveAttribute("href", "https://nvd.nist.gov/vuln/detail/CVE-2021-41773");
  await expect(page.getByText(/Found 180 points; this part of the score is capped at 40/)).toBeVisible();
});

test("dashboard shows critical count, distribution and riskiest assets", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page.getByRole("link", { name: "Critical risk: 1" })).toBeVisible();
  await expect(page.getByRole("img", { name: "Assets by risk band" })).toBeVisible();
  await expect(page.getByText("What drives the risk")).toBeVisible();
  const first = page.getByRole("listitem").filter({ hasText: "CS-0007" }).first();
  await expect(first).toContainText("Unknown device");
  await expect(first).toContainText("Critical");
});

test("assets list ranks by risk", async ({ page }) => {
  await page.goto("/assets");
  const rows = page.getByRole("row");
  await expect(rows.nth(1)).toContainText("Critical"); // unregistered rogue first
  await expect(rows.nth(2)).toContainText("Department Website"); // then highest score
});

test("changing criticality rescores the asset immediately", async ({ page }) => {
  await page.goto("/assets/4"); // Lab 3 Workstation 01, criticality low
  const meter = page.getByRole("meter", { name: "Risk score" });
  const before = Number(await meter.getAttribute("aria-valuenow"));
  try {
    await page.getByRole("button", { name: "Edit" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("radiogroup", { name: "Data sensitivity" }).getByRole("radio", { name: "High" }).click();
    await dialog.getByRole("button", { name: "Save changes" }).click();
    await expect(dialog).toBeHidden();
    await expect.poll(async () => Number(await meter.getAttribute("aria-valuenow"))).toBeGreaterThan(before);
  } finally {
    await page.request.patch("/api/v1/assets/4", { data: { data_sensitivity: 1 } });
  }
});

test("scan results list findings per host", async ({ page }) => {
  await page.goto("/scans");
  await page.getByRole("row").filter({ hasText: "Completed" }).first().getByRole("link").click();
  await page.getByRole("button", { name: /172\.25\.0\.11/ }).click();
  await expect(page.getByText(/Findings \(\d+\)/)).toBeVisible();
  await expect(page.getByText(/CVE-2021-41773 in Apache httpd 2\.4\.49/)).toBeVisible();
});

test("the risk model is published to every user", async ({ page }) => {
  await page.context().clearCookies();
  await signIn(page, AUDITOR);
  await page.goto("/settings");
  await page.getByRole("tab", { name: "Risk model" }).click();
  await expect(page.getByText("14 CVEs matched against detected product versions", { exact: false })).toBeVisible();
  await expect(page.getByRole("link", { name: "CVE-2021-41773" })).toBeVisible();
  await expect(page.getByText(/vendor backports/)).toBeVisible();
});
