import { test, expect, request as apiRequest } from "@playwright/test";

// Verificacion visual + layout del app shell:
//   - el documento NUNCA scrollea (el scroll vive dentro de <main>)
//   - el bottom nav queda completo dentro del viewport en toda pagina
//   - branding AgentykCo presente en login y dashboard
// Screenshots a /shots si esta montado (run -v <host>:/shots).

const BACKEND_URL = process.env.BACKEND_URL || "http://backend:8000";
const TEST_PIN = "1234";

const VIEWPORTS = [
  { name: "mobile", width: 375, height: 812 },
  { name: "desktop", width: 1440, height: 900 },
] as const;

const PAGES = ["/dashboard", "/pos", "/products", "/history"] as const;

async function getToken() {
  const api = await apiRequest.newContext({ baseURL: BACKEND_URL });
  await api.post("/api/auth/setup-pin", { data: { pin: TEST_PIN } });
  const login = await api.post("/api/auth/verify-pin", {
    data: { pin: TEST_PIN },
  });
  const { token } = await login.json();
  return { api, token };
}

test("app shell: sin scroll de documento y nav visible en toda pagina", async ({
  browser,
}) => {
  const { api, token } = await getToken();

  // El POS necesita al menos un producto para renderear el grid real
  const products = await api.get("/api/products", {
    headers: { Authorization: `Bearer ${token}` },
  });
  if ((await products.json()).length === 0) {
    await api.post("/api/products", {
      headers: { Authorization: `Bearer ${token}` },
      data: { name: "Cafe", price_mxn: 50.0 },
    });
  }

  for (const vp of VIEWPORTS) {
    const ctx = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
    });
    const page = await ctx.newPage();
    await page.addInitScript((t: string) => {
      localStorage.setItem("lpos.auth.token", t);
    }, token);

    for (const path of PAGES) {
      await page.goto(path);
      await page.locator("nav").waitFor();

      // 1. El documento no debe scrollear: el shell es h-dvh y el overflow
      //    vive dentro de <main>.
      const docScrolls = await page.evaluate(
        () =>
          document.documentElement.scrollHeight >
          window.innerHeight + 1
      );
      expect(docScrolls, `documento scrollea en ${path} @${vp.name}`).toBe(
        false
      );

      // 2. El bottom nav debe quedar completo dentro del viewport.
      const navBox = await page.locator("nav").boundingBox();
      expect(navBox, `nav sin boundingBox en ${path} @${vp.name}`).not.toBeNull();
      expect(
        navBox!.y + navBox!.height,
        `nav fuera del viewport en ${path} @${vp.name}`
      ).toBeLessThanOrEqual(vp.height + 1);

      // 3. Branding "Powered by AgentykCo" en el header (toda pagina, todo
      //    viewport) y en el nav (solo desktop; en movil esta oculto).
      await expect(
        page.locator("header").getByText("Powered by AgentykCo"),
        `branding de header ausente en ${path} @${vp.name}`
      ).toBeVisible();
      const navBranding = page
        .locator("nav")
        .getByText("Powered by AgentykCo");
      if (vp.name === "desktop") {
        await expect(
          navBranding,
          `branding de nav ausente en ${path} @${vp.name}`
        ).toBeVisible();
      } else {
        await expect(
          navBranding,
          `branding de nav deberia estar oculto en ${path} @${vp.name}`
        ).toBeHidden();
      }

      await page
        .screenshot({
          path: `/shots/${path.replace("/", "")}-${vp.name}.png`,
          fullPage: false,
        })
        .catch(() => {});
    }

    // Footer "Made with ... by AgentykCo" presente en dashboard
    await page.goto("/dashboard");
    await page.getByText("Made with").waitFor();
    await ctx.close();

    // Login (sin token) con branding
    const ctxLogin = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
    });
    const pageLogin = await ctxLogin.newPage();
    await pageLogin.goto("/");
    await pageLogin.getByText("AgentykCo").waitFor();
    await pageLogin
      .screenshot({ path: `/shots/login-${vp.name}.png`, fullPage: true })
      .catch(() => {});
    await ctxLogin.close();
  }

  await api.dispose();
});
