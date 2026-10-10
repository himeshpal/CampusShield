import { expect, test, type Page } from "@playwright/test";

import { ADMIN, AUDITOR, ensureCompletedScan, signIn } from "./helpers";

type Asset = Record<string, unknown> & { id: number; status: string; ip_address: string };

async function rogue(page: Page): Promise<Asset> {
  const assets: Asset[] = await (await page.request.get("/api/v1/assets")).json();
  return assets.find((a) => a.ip_address === "172.25.0.66")!;
}

test.beforeEach(async ({ page }) => {
  await signIn(page, ADMIN);
  await ensureCompletedScan(page);
});

test("inventory flags the unregistered Raspberry Pi first", async ({ page }) => {
  await page.goto("/assets");
  await expect(page.getByText(/1 unregistered device/)).toBeVisible();

  const firstRow = page.getByRole("row").nth(1);
  await expect(firstRow).toContainText("Unknown device");
  await expect(firstRow).toContainText("Raspberry Pi Foundation");
  await expect(firstRow).toContainText("Unregistered");
  await expect(firstRow.getByRole("button", { name: "Register" })).toBeVisible();

  await page.getByRole("tab", { name: /Registered/ }).first().click();
  await expect(page.getByRole("row")).toHaveCount(7); // header + 6 registered lab devices
});

test("search and type filter narrow the list", async ({ page }) => {
  await page.goto("/assets");
  await page.getByLabel("Search assets").fill("main gate");
  await expect(page.getByRole("row")).toHaveCount(2);
  await expect(page.getByRole("row").nth(1)).toContainText("CCTV Main Gate");
});

test("asset detail shows ports outside the expected baseline", async ({ page }) => {
  await page.goto("/assets");
  await page.getByRole("link", { name: "Lab 3 Workstation 01" }).click();
  await expect(page.getByRole("heading", { name: "Lab 3 Workstation 01" })).toBeVisible();
  await expect(page.getByText(/1 port open that is not in the expected baseline/)).toBeVisible();
  await expect(page.getByRole("row", { name: /21\/tcp/ })).toContainText("Unexpected");
  await expect(page.getByRole("row", { name: /22\/tcp/ })).toContainText("Expected");
  // Next keeps the previous page mounted but hidden (Activity), so match visible text only
  await expect(page.getByText("low4/12").filter({ visible: true })).toBeVisible();
});

test("admin registers the rogue device from the inventory", async ({ page }) => {
  const original = await rogue(page);
  expect(original.status).toBe("unregistered");
  try {
    await page.goto("/assets");
    await page.getByRole("row").nth(1).getByRole("button", { name: "Register" }).click();

    const dialog = page.getByRole("dialog");
    await expect(dialog.getByText(/Discovered on the network as/)).toBeVisible();
    await expect(dialog.getByLabel("IP address")).toHaveValue("172.25.0.66");
    await expect(dialog.getByLabel("Expected open ports")).toHaveValue("6379, 8080");
    await dialog.getByLabel("Name", { exact: true }).fill("Robotics Club Pi");
    await dialog.getByLabel("Department").fill("Robotics Club");
    await dialog.getByRole("radiogroup", { name: "Data sensitivity" }).getByRole("radio", { name: "Low" }).click();
    await dialog.getByRole("button", { name: "Register device" }).click();

    await expect(page.getByText(/CS-\d{4} registered/)).toBeVisible();
    await expect(page.getByText(/unregistered device/)).toHaveCount(0); // banner gone
    expect((await rogue(page)).status).toBe("registered");
  } finally {
    // put the demo back: the Pi must stay an unregistered rogue device
    const { id, name, department, data_sensitivity, baseline_ports, asset_type } = original;
    const res = await page.request.patch(`/api/v1/assets/${id}`, {
      data: { status: "unregistered", name, department, data_sensitivity, baseline_ports, asset_type },
    });
    expect(res.ok()).toBeTruthy();
  }
});

test("scan results link hosts to inventory records", async ({ page }) => {
  await page.goto("/scans");
  // newest *completed* scan (cancelled/failed scans have no hosts)
  await page.getByRole("row").filter({ hasText: "Completed" }).first().getByRole("link").click();
  await expect(page.getByText(/matched to the inventory/)).toBeVisible();
  await expect(page.getByRole("link", { name: "CS-0002 · Department Website" })).toBeVisible();
  await page.getByRole("link", { name: /Unregistered$/ }).first().click();
  await expect(page).toHaveURL(/\/assets\/\d+$/);
  await expect(page.getByText("Not in the inventory")).toBeVisible();
});

test("dashboard counts assets and links to unregistered devices", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page.getByRole("link", { name: "Total assets: 6" })).toBeVisible();
  await page.getByRole("link", { name: "Unregistered devices: 1" }).click();
  await expect(page).toHaveURL(/\/assets\?status=unregistered$/);
  await expect(page.getByRole("row")).toHaveCount(2);
});

test("auditors see the inventory but cannot change it", async ({ page }) => {
  await page.context().clearCookies();
  await signIn(page, AUDITOR);
  await page.goto("/assets");
  await expect(page.getByRole("row").nth(1)).toBeVisible();
  await expect(page.getByRole("button", { name: "Add asset" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Register" })).toHaveCount(0);
});
