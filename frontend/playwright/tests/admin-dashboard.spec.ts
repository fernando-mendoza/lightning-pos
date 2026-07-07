// E2E del dashboard admin (/admin) contra el backend multi-tenant /api/v2.
// Corre con docker-compose.test-mt.yml. En la suite v1 (docker-compose.test.yml)
// el backend no expone /api/v2 y el spec entero se salta solo.

import { expect, test } from "@playwright/test";

const BACKEND = process.env.BACKEND_URL || "http://backend:8000";
const EMAIL = `e2e_${Date.now()}@t.mx`;
const PASSWORD = "e2e-supersecret1";
const TENANT = "Cafe E2E";

test.describe("admin dashboard", () => {
  test.beforeAll(async ({ request }) => {
    // ¿Este backend tiene /api/v2? (404 = suite v1, saltar todo el spec)
    const probe = await request.post(`${BACKEND}/api/v2/auth/register`, {
      data: { email: EMAIL, password: PASSWORD, tenant_name: TENANT },
    });
    test.skip(probe.status() === 404, "backend sin /api/v2 (suite v1)");
    expect(probe.status(), "registro del tenant e2e").toBe(201);
  });

  test("login → reportes en cero", async ({ page }) => {
    await page.goto("/admin/login");
    await page.getByTestId("admin-email").fill(EMAIL);
    await page.getByTestId("admin-password").fill(PASSWORD);
    await page.getByTestId("admin-login-submit").click();
    await expect(page).toHaveURL(/\/admin$/);
    await expect(page.getByText("Ventas pagadas")).toBeVisible();
    await expect(page.getByTestId("report-count")).toHaveText("0");
    await expect(page.getByText(TENANT)).toBeVisible(); // header con el tenant
    await expect(page.getByText("Powered by AgentykCo")).toBeVisible();
  });

  test("catálogo: crear producto y verlo listado", async ({ page }) => {
    await login(page);
    await page.getByRole("link", { name: "Catálogo" }).click();
    await page.getByTestId("admin-product-new").click();
    await page.getByTestId("admin-product-name").fill("Cafe de olla");
    await page.getByTestId("admin-product-price").fill("45.50");
    await page.getByTestId("admin-product-save").click();
    await expect(page.getByText("Cafe de olla")).toBeVisible();
    await expect(page.getByText("$45.50 MXN")).toBeVisible();
  });

  test("terminales: generar QR de pairing con countdown", async ({ page }) => {
    await login(page);
    await page.getByRole("link", { name: "Terminales" }).click();
    await page.getByTestId("admin-terminal-new").click();
    await page.getByTestId("admin-pairing-name").fill("Caja E2E");
    await page.getByTestId("admin-pairing-generate").click();
    await expect(page.getByText("Escanea con la app")).toBeVisible();
    await expect(page.locator("svg").filter({ has: page.locator("path") }).first()).toBeVisible();
    await expect(page.getByText("Código manual:")).toBeVisible();
    await expect(page.getByText(/expira en \d{2}:\d{2}/)).toBeVisible();
  });

  test("ajustes: renombrar comercio", async ({ page }) => {
    await login(page);
    await page.getByRole("link", { name: "Ajustes" }).click();
    await page.getByTestId("admin-tenant-name").fill("Cafe E2E Renombrado");
    await page.getByTestId("admin-tenant-save").click();
    await expect(page.getByText("Nombre del comercio actualizado.")).toBeVisible();
  });

  test("logout regresa al login", async ({ page }) => {
    await login(page);
    await page.getByTestId("admin-logout").click();
    await expect(page).toHaveURL(/\/admin\/login/);
  });
});

async function login(page: import("@playwright/test").Page) {
  await page.goto("/admin/login");
  await page.getByTestId("admin-email").fill(EMAIL);
  await page.getByTestId("admin-password").fill(PASSWORD);
  await page.getByTestId("admin-login-submit").click();
  await page.waitForURL(/\/admin$/);
}
