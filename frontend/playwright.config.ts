import { defineConfig, devices } from "@playwright/test";

// E2E tests drive the real stack: start Docker first (.\scripts\stack.ps1 up).
// The Next.js dev server is started automatically if it is not already running.
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false, // tests share one database
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000/login",
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
