/**
 * Smoke cross-browser de la página pública de login de KONTROL (QA, sin credenciales).
 * Carga la URL real, verifica título + botón y captura screenshot por motor.
 * Uso: node qa/cross-browser-smoke.mjs <RUN_ID>
 */
import { createRequire } from "node:module";
import { mkdirSync } from "node:fs";
import { join } from "node:path";

// Resolver playwright-core desde resources/frontend (donde está instalado)
const require = createRequire("/home/maria/Proyectos/kontrol/resources/frontend/package.json");
const { chromium, firefox, webkit } = require("playwright-core");

const RUN_ID = process.argv[2] ?? "KONTROL-QA-DEV";
const REPO = process.argv[3] ?? process.cwd();
const BASE = "https://kontrol.globaldv.net";
const outDir = join(REPO, "qa", "runs", RUN_ID, "screenshots");
mkdirSync(outDir, { recursive: true });

const engines = [
  { name: "chromium", launch: chromium.launch },
  { name: "firefox", launch: firefox.launch },
  { name: "webkit", launch: webkit.launch },
];

const results = [];
for (const eng of engines) {
  let browser;
  try {
    browser = await eng.launch({ headless: true });
    const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
    const consoleErrors = [];
    page.on("console", (m) => { if (m.type() === "error") consoleErrors.push(m.text().slice(0, 120)); });
    await page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded", timeout: 45000 });
    await page.waitForTimeout(3500);
    const title = await page.title();
    const hasLoginBtn = await page.getByRole("button", { name: "Iniciar sesión" }).isVisible().catch(() => false);
    const heading = await page.locator("h1").first().textContent().catch(() => "");
    const shot = join(outDir, `login-${eng.name}.png`);
    await page.screenshot({ path: shot, fullPage: true });
    results.push({ engine: eng.name, status: "PASS", title, heading, hasLoginBtn, consoleErrors, screenshot: shot });
  } catch (err) {
    results.push({ engine: eng.name, status: "FAIL", error: String(err).slice(0, 200) });
  } finally {
    if (browser) await browser.close();
  }
}
console.log(JSON.stringify(results, null, 2));
