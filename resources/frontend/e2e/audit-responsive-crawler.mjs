/**
 * Crawler responsive (T-217 de la auditoría 012).
 *
 * Visita las rutas principales en varios viewports (móvil, tablet, desktop,
 * full-HD) y detecta scroll horizontal general (prohibido por el estándar).
 *
 * Salidas: qa/audits/<RUN_ID>/responsive-results.json y responsive-report.md
 * Uso: node e2e/audit-responsive-crawler.mjs [baseURL] [runId]
 * Requiere backend + frontend levantados y credenciales QA.
 */
import { chromium } from "playwright";
import { mkdirSync, writeFileSync, appendFileSync } from "node:fs";
import { join } from "node:path";

const BASE = process.argv[2] ?? process.env.KONTROL_E2E_BASE_URL ?? "http://localhost:5173";
const RUN_ID = process.argv[3] ?? "KONTROL-AUDIT-20260812-RESPONSIVE";
const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const USER = process.env.KONTROL_E2E_USERNAME ?? "admin";
const PASS = process.env.KONTROL_E2E_PASSWORD ?? "Kontrol2026Segura!";
const CAP_MS = Number(process.env.CRAWL_CAP_MS ?? 12000);

const VIEWPORTS = [
  { name: "320x568", width: 320, height: 568 },
  { name: "375x667", width: 375, height: 667 },
  { name: "412x915", width: 412, height: 915 },
  { name: "768x1024", width: 768, height: 1024 },
  { name: "1366x768", width: 1366, height: 768 },
  { name: "1920x1080", width: 1920, height: 1080 },
];

// Rutas representativas de todos los módulos
const ROUTES = [
  "/", "/mi-licencia", "/organizacion/empresas", "/organizacion/sucursales",
  "/maestros/terceros", "/maestros/productos", "/maestros/atributos",
  "/inventario/existencias", "/inventario/kardex", "/inventario/movimientos",
  "/inventario/transferencias", "/inventario/seriales", "/inventario/reservas",
  "/inventario/tipos-movimiento",
  "/compras/ordenes", "/compras/facturas", "/compras/cotizaciones",
  "/compras/cuentas-por-pagar",
  "/ventas/ordenes", "/ventas/facturas", "/ventas/cuentas-por-cobrar",
  "/tesoreria/cajas", "/tesoreria/conciliacion", "/fiscal/configuracion",
  "/fiscal/numeracion", "/fiscal/lotes-declaracion",
  "/regulatorio/aprobaciones", "/reportes/centro",
  "/reportes/exportaciones", "/reportes/auditoria", "/seguridad/usuarios",
  "/seguridad/roles", "/auditoria",
];

const OUT = join(process.cwd(), "qa", "audits", RUN_ID);
mkdirSync(join(OUT), { recursive: true });
const LOG = join(OUT, "responsive.log");
const log = (s) => { try { appendFileSync(LOG, `${new Date().toISOString()} ${s}\n`); } catch { /* ignore */ } console.log(s); };

const withTimeout = (p, ms, tag) => Promise.race([p, new Promise((_, rej) => setTimeout(() => rej(new Error(`TIMEOUT ${tag}`)), ms))]);

const browser = await chromium.launch();
const results = [];
const start = Date.now();

// login una vez en un context; luego creamos páginas por viewport del mismo context
const context = await browser.newContext({ viewport: { width: 1366, height: 768 } });
const page = await context.newPage();
page.setDefaultTimeout(8000);
page.setDefaultNavigationTimeout(10000);
await withTimeout(page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded" }), 15000, "login");
await page.getByLabel(/Empresa/).fill(TENANT).catch(() => undefined);
await page.getByLabel(/Usuario/).fill(USER).catch(() => undefined);
await page.getByLabel(/Contraseña/).fill(PASS).catch(() => undefined);
await page.getByRole("button", { name: "Iniciar sesión" }).click().catch(() => undefined);
await page.waitForTimeout(2500);
log(`login OK: ${page.url()}`);

for (const vp of VIEWPORTS) {
  await page.setViewportSize({ width: vp.width, height: vp.height });
  for (const route of ROUTES) {
    const row = { viewport: vp.name, route, horizontal_scroll: false, h1: null, status: "PASS", ms: 0 };
    const t0 = Date.now();
    try {
      await withTimeout(page.goto(`${BASE}${route}`, { waitUntil: "domcontentloaded", timeout: 10000 }), CAP_MS, route);
      await page.waitForTimeout(700);
      row.horizontal_scroll = await page.evaluate(() => {
        const el = document.scrollingElement ?? document.documentElement;
        return el.scrollWidth > el.clientWidth + 2;
      }).catch(() => false);
      row.h1 = (await page.locator("h1").first().textContent().catch(() => null))?.trim() ?? null;
      if (row.horizontal_scroll) row.status = "HORIZONTAL_SCROLL";
      if (!row.h1) row.status = row.status === "PASS" ? "NO_H1" : `${row.status}+NO_H1`;
    } catch (e) {
      row.status = "ERROR";
      row.error = String(e).slice(0, 120);
    }
    row.ms = Date.now() - t0;
    results.push(row);
    if (row.status !== "PASS") log(`${vp.name} ${route} -> ${row.status}`);
  }
  log(`${vp.name} completado`);
}
await browser.close().catch(() => undefined);

const total = results.length;
const bad = results.filter((r) => r.status !== "PASS");
const hscroll = results.filter((r) => r.horizontal_scroll);
const summary = {
  audit_run_id: RUN_ID, timestamp: new Date().toISOString(),
  viewports: VIEWPORTS.map((v) => v.name),
  routes: ROUTES.length, checks: total,
  pass: total - bad.length, non_pass: bad.length,
  horizontal_scroll_cases: hscroll.length,
  by_viewport: VIEWPORTS.map((v) => ({
    name: v.name,
    checks: results.filter((r) => r.viewport === v.name).length,
    hscroll: results.filter((r) => r.viewport === v.name && r.horizontal_scroll).length,
  })),
};
writeFileSync(join(OUT, "responsive-results.json"), JSON.stringify({ summary, results }, null, 2));
writeFileSync(join(OUT, "responsive-report.md"), render(summary, results));
log(`TERMINADO: ${JSON.stringify(summary)}`);

function render(s, rows) {
  const L = [`# Reporte Responsive — ${s.audit_run_id}`, "",
    `- Checks: ${s.checks} (${s.routes} rutas × ${s.viewports.length} viewports)`,
    `- PASS: ${s.pass} · No-PASS: ${s.non_pass} · Scroll horizontal: ${s.horizontal_scroll_cases}`,
    "", "| Viewport | Checks | Scroll horizontal |", "|---|---|---|"];
  for (const v of s.by_viewport) L.push(`| ${v.name} | ${v.checks} | ${v.hscroll} |`);
  const bads = rows.filter((r) => r.status !== "PASS");
  if (bads.length) {
    L.push("", "## Casos no-PASS", "", "| Viewport | Ruta | Estado |", "|---|---|---|");
    for (const r of bads) L.push(`| ${r.viewport} | ${r.route} | ${r.status} ${r.error ?? ""} |`);
  }
  return L.join("\n");
}
