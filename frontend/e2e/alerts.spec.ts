import { expect, test } from "@playwright/test";

import { ADMIN, AUDITOR, ensureCompletedScan, labExec, runScan, signIn } from "./helpers";

const telnetOn = () => labExec("lab-pc-01", "pgrep telnetd >/dev/null || telnetd -p 23 -l /bin/login");
const telnetOff = () => labExec("lab-pc-01", "pkill telnetd; true");
const TITLE = "Port 23/tcp (telnet) opened on CS-0004 Lab 3 Workstation 01";

test.beforeEach(async ({ page }) => {
  await signIn(page, ADMIN);
  await ensureCompletedScan(page);
});

test("a port opened on the lab raises an alert that resolves itself once closed", async ({ page }) => {
  test.setTimeout(180_000);
  try {
    await runScan(page); // baseline: telnet closed
    telnetOn();
    const scanId = await runScan(page);

    await page.goto("/alerts");
    const item = page.locator("li", { hasText: TITLE }).first();
    await expect(item).toBeVisible();
    await expect(item).toContainText("High");
    await expect(item).toContainText("Not in the approved baseline");
    await expect(page.getByLabel(/^\d+ open alerts$/)).toBeVisible(); // sidebar badge

    await item.getByRole("button", { name: "Acknowledge" }).click();
    await expect(item).toContainText("Acknowledged by Campus IT Admin");

    await page.goto(`/scans/${scanId}`);
    await expect(page.getByText("Changes since the previous scan")).toBeVisible();
    await expect(page.getByText(TITLE)).toBeVisible();

    telnetOff();
    const closedIn = await runScan(page);
    await page.goto("/alerts?status=resolved");
    const resolved = page.locator("li", { hasText: TITLE }).first();
    await expect(resolved).toContainText(`Port closed again in scan #${closedIn}`);
  } finally {
    telnetOff();
  }
});

test("admin resolves an alert with a note", async ({ page }) => {
  const res = await page.request.get("/api/v1/alerts?unresolved=true&limit=1");
  const { items } = await res.json();
  test.skip(!items.length, "no unresolved alert to resolve");
  await page.goto(`/alerts?focus=${items[0].id}`);
  const item = page.locator(`#alert-${items[0].id}`);
  await item.getByRole("button", { name: "Resolve" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("What was done (optional)").fill("Checked on site during the E2E run");
  await dialog.getByRole("button", { name: "Resolve" }).click();
  await expect(page.getByText("Alert resolved")).toBeVisible();
});

test("auditor reads alerts but cannot act on them", async ({ page }) => {
  await page.request.post("/api/v1/auth/logout");
  await signIn(page, AUDITOR);
  await page.goto("/alerts?status=all");
  await expect(page.getByRole("heading", { name: "Alerts", exact: true })).toBeVisible();
  await expect(page.getByText("Unresolved by severity")).toBeVisible();
  await expect(page.getByRole("button", { name: "Acknowledge" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Resolve" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /Acknowledge all/ })).toHaveCount(0);
});

test("notification settings: threshold and test alert", async ({ page }) => {
  await page.goto("/settings?tab=notifications");
  await expect(page.getByText("Alert delivery")).toBeVisible();
  const threshold = page.getByRole("combobox", { name: "Minimum severity to notify" });
  await expect(threshold).toHaveText("Medium and above");
  try {
    await threshold.click();
    await page.getByRole("option", { name: "High and above" }).click();
    await expect(page.getByText("Notification threshold saved")).toBeVisible();
  } finally {
    await page.request.put("/api/v1/alerts/settings", { data: { min_severity: "medium" } });
  }

  await page.getByRole("button", { name: "Send test alert" }).click();
  // n8n may not be running in every environment: both outcomes are reported clearly
  await expect(
    page.getByText("Test alert sent to n8n").or(page.getByText("Test alert not delivered")),
  ).toBeVisible({ timeout: 15_000 });
});
