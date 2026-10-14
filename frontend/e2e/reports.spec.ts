import { expect, test, type Page } from "@playwright/test";

import { ADMIN, AUDITOR, ensureCompletedScan, signIn } from "./helpers";

type Report = { id: number; number: string; title: string };

/** Remove reports a test created, as admin, so the demo history stays as it was. */
async function cleanup(page: Page, ids: number[]) {
  if (!ids.length) return;
  const login = await page.request.post("/api/v1/auth/login", { data: ADMIN });
  expect(login.ok()).toBeTruthy();
  for (const id of ids) await page.request.delete(`/api/v1/reports/${id}`);
}

test.beforeEach(async ({ page }) => {
  await signIn(page, ADMIN);
  await ensureCompletedScan(page);
});

test("admin generates a PDF report and opens it from the history", async ({ page }) => {
  const created: number[] = [];
  try {
    await page.goto("/reports");
    await expect(page.getByRole("heading", { name: "Reports", exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Generate report" }).first().click();

    const dialog = page.getByRole("dialog");
    await dialog.getByLabel("Title").fill("E2E audit report");
    await dialog.getByRole("radio", { name: /Summary only/ }).click();
    const response = page.waitForResponse(
      (r) => r.url().endsWith("/api/v1/reports") && r.request().method() === "POST",
    );
    await dialog.getByRole("button", { name: "Generate PDF" }).click();
    const report: Report = await (await response).json();
    created.push(report.id);

    await expect(page.getByText(`${report.number} generated`)).toBeVisible({ timeout: 30_000 });
    await expect(dialog).toBeHidden();
    await expect(page.getByText(`${report.number} · latest`)).toBeVisible();
    const row = page.getByRole("row", { name: /E2E audit report/ });
    await expect(row).toContainText("summary only");

    const href = await row.getByRole("link", { name: `Open ${report.number}` }).getAttribute("href");
    const pdf = await page.request.get(href!);
    expect(pdf.headers()["content-type"]).toBe("application/pdf");
    expect((await pdf.body()).subarray(0, 5).toString()).toBe("%PDF-");

    const download = page.waitForEvent("download");
    await row.getByRole("link", { name: `Download ${report.number}` }).click();
    expect((await download).suggestedFilename()).toMatch(
      new RegExp(`^CampusShield-${report.number}-\\d{4}-\\d{2}-\\d{2}\\.pdf$`),
    );
  } finally {
    await cleanup(page, created);
  }
});

test("admin deletes a report after confirming", async ({ page }) => {
  const res = await page.request.post("/api/v1/reports", {
    data: { title: "E2E report to delete", include_details: false },
  });
  const report: Report = await res.json();
  try {
    await page.goto("/reports");
    await page.getByRole("button", { name: `Delete ${report.number}` }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toContainText(`Delete ${report.number}?`);
    await dialog.getByRole("button", { name: "Delete report" }).click();
    await expect(page.getByText(`${report.number} deleted`)).toBeVisible();
    await expect(page.getByRole("row", { name: /E2E report to delete/ })).toHaveCount(0);
  } finally {
    await cleanup(page, [report.id]); // no-op when the UI already deleted it
  }
});

test("auditor can generate reports but not delete them", async ({ page }) => {
  await page.request.post("/api/v1/auth/logout");
  await signIn(page, AUDITOR);
  const res = await page.request.post("/api/v1/reports", {
    data: { title: "E2E auditor report", include_details: false },
  });
  expect(res.status()).toBe(201);
  const report: Report = await res.json();
  try {
    await page.goto("/reports");
    await expect(page.getByRole("row", { name: /E2E auditor report/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /^Delete RPT-/ })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Generate report" }).first()).toBeEnabled();
  } finally {
    await cleanup(page, [report.id]);
  }
});

test("dashboard shows the campus trend, audit status and live refresh", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page.getByText("Live", { exact: true })).toBeVisible();
  await expect(page.getByText("Campus risk over time")).toBeVisible();
  const status = page.locator("[data-slot=card]", { hasText: "Audit status" });
  await expect(status).toContainText("Latest scan");
  await expect(status).toContainText("Security checklist");
  await expect(status).toContainText("Latest report");
});
