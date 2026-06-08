import { spawnSync } from "node:child_process";
import { createRequire } from "node:module";

const required = ["E2E_BASE_URL", "E2E_ADMIN_LOGIN", "E2E_ADMIN_PASSWORD"];
const missing = required.filter((name) => !process.env[name]);

if (missing.length > 0) {
  console.error(`Missing required e2e environment variables: ${missing.join(", ")}`);
  console.error("Start the local stack, seed an admin user, then rerun with those variables set.");
  process.exit(2);
}

const require = createRequire(import.meta.url);
try {
  require.resolve("@playwright/test");
} catch {
  console.error("Missing @playwright/test in apps/web. Install Playwright before running e2e.");
  process.exit(2);
}

const result = spawnSync("npx", ["--no-install", "playwright", "test", "tests/e2e/mvp-flow.playwright.cjs"], {
  cwd: new URL("../..", import.meta.url),
  env: process.env,
  stdio: "inherit",
});

if (result.error) {
  console.error(`Failed to start Playwright: ${result.error.message}`);
  process.exit(2);
}

process.exit(result.status ?? 1);
