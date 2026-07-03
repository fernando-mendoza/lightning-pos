import { test, request as apiRequest } from "@playwright/test";

// Spec temporal de verificacion visual (responsividad + branding).
// Escribe screenshots a /shots (montado desde el host con `run -v`).

const BACKEND_URL = process.env.BACKEND_URL || "http://backend:8000";
const TEST_PIN = "1234";

const VIEWPORTS = [
  { name: "mobile", width: 375, height: 812 },
  { name: "desktop", width: 1440, height: 900 },
] as const;

test("screenshots de dashboard y login en mobile y desktop", async ({
  browser,
}) => {
  const api = await apiRequest.newContext({ baseURL: BACKEND_URL });
  await api.post("/api/auth/setup-pin", { data: { pin: TEST_PIN } });
  const login = await api.post("/api/auth/verify-pin", {
    data: { pin: TEST_PIN },
  });
  const { token } = await login.json();

  for (const vp of VIEWPORTS) {
    const ctx = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
    });
    const page = await ctx.newPage();
    await page.addInitScript((t: string) => {
      localStorage.setItem("lpos.auth.token", t);
    }, token);
    await page.goto("/dashboard");
    await page.getByText("AgentykCo").waitFor();
    await page.screenshot({
      path: `/shots/dashboard-${vp.name}.png`,
      fullPage: true,
    });
    await ctx.close();

    const ctxLogin = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
    });
    const pageLogin = await ctxLogin.newPage();
    await pageLogin.goto("/");
    await pageLogin.getByText("AgentykCo").waitFor();
    await pageLogin.screenshot({
      path: `/shots/login-${vp.name}.png`,
      fullPage: true,
    });
    await ctxLogin.close();
  }

  await api.dispose();
});
