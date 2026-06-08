const { expect, test } = require("@playwright/test");

test("admin creates user and user reaches document upload flow", async ({ page }) => {
  const baseUrl = process.env.E2E_BASE_URL;
  const adminLogin = process.env.E2E_ADMIN_LOGIN;
  const adminPassword = process.env.E2E_ADMIN_PASSWORD;
  const userLogin = `e2e-${Date.now()}`;
  const userPassword = "e2e-strong-password";

  await page.goto(`${baseUrl}/login`);
  await page.getByLabel("Login").fill(adminLogin);
  await page.getByLabel("Password").fill(adminPassword);
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).toHaveURL(/\/documents/);

  await page.goto(`${baseUrl}/admin/users`);
  await page.getByLabel("Login").fill(userLogin);
  await page.getByLabel("Display name").fill("E2E User");
  await page.getByLabel("Initial password").fill(userPassword);
  await page.getByRole("button", { name: "Create user" }).click();
  await expect(page.getByText(userLogin)).toBeVisible();

  await page.getByRole("button", { name: "Log out" }).click();
  await page.getByLabel("Login").fill(userLogin);
  await page.getByLabel("Password").fill(userPassword);
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).toHaveURL(/\/documents/);

  await page.goto(`${baseUrl}/documents/upload`);
  await expect(page.getByRole("heading", { name: /Upload/i })).toBeVisible();
});
