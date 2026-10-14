import { readFileSync } from "node:fs";
import path from "node:path";

import { expect, test } from "@playwright/test";

import { ADMIN, ensureCompletedScan, signIn } from "./helpers";

/** The service key the Wazuh manager uses (from the project's .env). */
function serviceKey(): string {
  const env = readFileSync(path.resolve(__dirname, "../../.env"), "utf-8");
  const line = env.split(/\r?\n/).find((l) => l.startsWith("SERVICE_API_KEY="));
  if (!line) throw new Error("SERVICE_API_KEY missing in .env");
  return line.slice("SERVICE_API_KEY=".length);
}

// What wazuh-integratord forwards for rule 51007 (trimmed), as the manager would send it.
const BRUTE_FORCE = {
  rule: {
    id: "51007",
    level: 10,
    description: "Dropbear: brute force attempt.",
    groups: ["syslog", "dropbear", "authentication_failures"],
    mitre: { id: ["T1110"] },
  },
  agent: { id: "001", name: "lab-pc-01", ip: "172.25.0.20" },
  data: { srcip: "172.25.0.66", srcuser: "root" },
  full_log: "lab-pc-01 dropbear[241]: Bad password attempt for 'root' from 172.25.0.66:45154",
  location: "/var/log/messages",
};

test("a Wazuh host event appears as an alert linked to both devices", async ({ page }) => {
  await signIn(page, ADMIN);
  await ensureCompletedScan(page);
  const res = await page.request.post("/api/v1/automation/wazuh", {
    data: BRUTE_FORCE,
    headers: { "X-API-Key": serviceKey() },
  });
  expect(res.status()).toBe(202);
  const { alert_id: id } = await res.json();
  try {
    await page.goto("/alerts?kind=wazuh");
    const item = page.locator(`#alert-${id}`);
    await expect(item).toContainText("Dropbear: brute force attempt on CS-0004 Lab 3 Workstation 01");
    await expect(item).toContainText("Host event (Wazuh)");
    await expect(item).toContainText("Wazuh rule 51007 · level 10");
    await expect(item).toContainText("CS-0007, an unregistered device");
    await item.getByRole("link", { name: "from 172.25.0.66" }).click();
    await expect(page).toHaveURL(/\/assets\/\d+$/); // the attacking (rogue) device

    await page.goto("/assets/4"); // the attacked lab PC lists it under open alerts
    await expect(page.getByText("Open alerts")).toBeVisible();
    await expect(page.locator(`#alert-${id}`)).toBeVisible();

    await page.goto("/settings?tab=notifications");
    await expect(page.getByText("Wazuh host monitoring")).toBeVisible();
    await expect(page.getByText(/Dropbear: brute force attempt\. · agent lab-pc-01/)).toBeVisible();
  } finally {
    await page.request.post(`/api/v1/alerts/${id}/resolve`, { data: { note: "E2E test event" } });
  }
});
