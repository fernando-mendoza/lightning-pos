import { test, expect } from "@playwright/test";

test("smoke: la app carga y muestra la pantalla inicial", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/Lightning POS/i);
});
