import { expect, test, type Page } from "@playwright/test";

import { ADMIN, AUDITOR, ensureCompletedScan, signIn } from "./helpers";

/** Put a control back to "not confirmed" so the demo starts from scratch. */
async function reset(page: Page, assetId: number, key: string) {
  const res = await page.request.put(`/api/v1/checklist/${assetId}/${key}`, {
    data: { status: "unknown", evidence: null },
  });
  expect(res.ok()).toBeTruthy();
}

test.beforeEach(async ({ page }) => {
  await signIn(page, ADMIN);
  await ensureCompletedScan(page);
});

test("checklist lists registered assets against all six controls", async ({ page }) => {
  await page.goto("/checklist");
  await expect(page.getByRole("heading", { name: "Security checklist" })).toBeVisible();
  await expect(page.getByText(/unregistered device is not listed/)).toBeVisible();
  await expect(page.getByRole("row")).toHaveCount(7); // header + 6 registered lab devices
  for (const column of ["Firewall", "Antivirus", "Encryption", "MFA", "Patching", "Default creds"]) {
    await expect(page.getByRole("columnheader", { name: column })).toBeVisible();
  }
  await expect(page.getByRole("img", { name: /^Host firewall enabled:/ })).toBeVisible();
});

test("confirming a control lowers the risk score immediately", async ({ page }) => {
  try {
    await page.goto("/checklist");
    const row = page.getByRole("row", { name: /Department Website/ });
    await expect(row).toContainText("0/6");
    await row.getByRole("button", { name: /Host firewall enabled for Department Website/ }).click();

    const popover = page.getByRole("dialog");
    await popover.getByRole("radio", { name: "In place" }).click();
    await popover.getByLabel("Evidence note").fill("ufw active, only port 80 allowed");
    await popover.getByRole("button", { name: "Save" }).click();

    await expect(page.getByText(/Department Website: risk \d+ → \d+/)).toBeVisible();
    await expect(row).toContainText("1/6");
    await expect(row.getByRole("button", { name: /Host firewall enabled for Department Website: In place/ })).toBeVisible();
  } finally {
    await reset(page, 2, "firewall");
  }
});

test("the asset page edits the same checklist and its meter drops", async ({ page }) => {
  try {
    await page.goto("/assets/6"); // CCTV Main Gate
    const meter = page.getByRole("meter", { name: "Risk score" });
    const before = Number(await meter.getAttribute("aria-valuenow"));
    await page.getByRole("button", { name: /Antivirus \/ EDR active for CCTV Main Gate/ }).click();
    const popover = page.getByRole("dialog");
    await popover.getByRole("radio", { name: "Not applicable" }).click();
    await popover.getByRole("button", { name: "Save" }).click();
    await expect.poll(async () => Number(await meter.getAttribute("aria-valuenow"))).toBeLessThan(before);
    await expect(page.getByText("1 of 6 controls answered.")).toBeVisible();
  } finally {
    await reset(page, 6, "antivirus");
  }
});

test("auditors can read the evidence but not change answers", async ({ page }) => {
  await page.context().clearCookies();
  await signIn(page, AUDITOR);
  await page.goto("/checklist");
  await page.getByRole("row", { name: /ERP Portal Server/ }).getByRole("button", { name: /Multi-factor authentication/ }).click();
  const popover = page.getByRole("dialog");
  await expect(popover.getByText("Multi-factor authentication")).toBeVisible();
  await expect(popover.getByRole("button", { name: "Save" })).toHaveCount(0);
  await expect(popover.getByRole("radio", { name: "In place" })).toBeDisabled();
});

test("the editor's Save button stays on screen on short laptop displays", async ({ page }) => {
  // regression: on a 720px-tall window the popover ended below the screen edge
  await page.setViewportSize({ width: 1280, height: 600 });
  await page.goto("/checklist");
  for (const asset of ["Department Website", "Wi-Fi AP Block A"]) {
    await page
      .getByRole("row", { name: new RegExp(asset) })
      .getByRole("button", { name: new RegExp(`Default credentials changed for ${asset}`) })
      .click();
    const save = page.getByRole("dialog").getByRole("button", { name: "Save" });
    await save.click({ trial: true }); // fails if the button cannot be reached
    await page.keyboard.press("Escape");
  }
});
