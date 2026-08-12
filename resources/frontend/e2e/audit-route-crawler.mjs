/**
 * Crawler de pantallas KONTROL (Spec 012) — v3: cap duro por ruta (Promise.race).
 *
 * Recorre todas las opciones del menú; por ruta registra URL, H1, breadcrumb,
 * requests fallidos, console.error, excepciones, scroll horizontal, duración y
 * screenshot. Ninguna ruta puede colgar el run (cap 12s).
 * Salidas: qa/audits/<RUN_ID>/route-crawl-results.json y route-crawl-report.md
 * Uso: node e2e/audit-route-crawler.mjs [baseURL] [runId]
 */
import { chromium } from "playwright";
import { mkdirSync, writeFileSync, appendFileSync } from "node:fs";
import { join } from "node:path";

const BASE = process.argv[2] ?? process.env.KONTROL_E2E_BASE_URL ?? "http://localhost:5173";
const RUN_ID = process.argv[3] ?? `KONTROL-AUDIT-${new Date().toISOString().slice(0, 19).replace(/[-:]/g, "").replace("T", "-")}`;
const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const USER = process.env.KONTROL_E2E_USERNAME ?? "admin";
const PASS = process.env.KONTROL_E2E_PASSWORD ?? "Kontrol2026Segura!";
const CAP_MS = Number(process.env.CRAWL_CAP_MS ?? 12000);

const OUT = join(process.cwd(), "qa", "audits", RUN_ID);
mkdirSync(join(OUT, "screenshots"), { recursive: true });
const LOG = join(OUT, "crawl.log");
const log = (s) => { try { appendFileSync(LOG, `${new Date().toISOString()} ${s}\n`); } catch { /* ignore */ } console.log(s); };

const withTimeout = (p, ms, tag) => Promise.race([
  p,
  new Promise((_, rej) => setTimeout(() => rej(new Error(`TIMEOUT(${ms}ms): ${tag}`)), ms)),
]);

const results = [];
const start = Date.now();
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1366, height: 768 } });
page.setDefaultTimeout(8000);
page.setDefaultNavigationTimeout(10000);
const consoleErrors = [];
const pageErrors = [];
page.on("console", (msg) => { if (msg.type() === "error") consoleErrors.push(`[${page.url()}] ${msg.text()}`); });
page.on("pageerror", (err) => pageErrors.push(`[${page.url()}] ${err}`));

// ---- Login ----
log("Iniciando login");
await withTimeout(page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded" }), 15000, "goto login");
await page.getByLabel(/Empresa/).fill(TENANT).catch((e) => log(`label empresa: ${e.message}`));
await page.getByLabel(/Usuario/).fill(USER).catch((e) => log(`label usuario: ${e.message}`));
await page.getByLabel(/Contraseña/).fill(PASS).catch((e) => log(`label contraseña: ${e.message}`));
await page.getByRole("button", { name: "Iniciar sesión" }).click().catch((e) => log(`boton: ${e.message}`));
await withTimeout(page.waitForURL(/\/$/, { timeout: 15000 }), 20000, "wait url /").catch((e) => log(`waitURL: ${e.message}`));
await page.waitForTimeout(2500);
await page.locator('nav a[href^="/"]').first().waitFor({ state: "visible", timeout: 15000 }).catch((e) => log(`nav wait: ${e.message}`));
const navCount = await page.locator('nav a[href^="/"]').count();
log(`URL: ${page.url()} · links nav: ${navCount}`);

const links = await page.locator('nav a[href^="/"]').evaluateAll((els) =>
  [...new Set(els.map((e) => e.getAttribute("href") ?? "").filter((h) => h.length > 1 && h !== "/login" && h !== "/setup"))],
);
log(`rutas a recorrer: ${links.length}`);

for (const href of links) {
  const row = { href, url: null, title: null, h1: null, breadcrumb: null,
    status: "PASS", failed_requests: [], console_errors: [], page_errors: [],
    horizontal_scroll: false, duration_ms: 0, screenshot: null };
  const t0 = Date.now();
  const failedReq = new Set();
  const onResponse = (r) => { try { if (r.status() >= 400) failedReq.add(`${r.status()} ${r.request().method()} ${r.url()}`); } catch { /* ignore */ } };
  const onRequestFailed = (r) => { try { failedReq.add(`FAILED ${r.request().method()} ${r.url()} ${r.failure()?.errorText ?? ""}`); } catch { /* ignore */ } };
  page.on("response", onResponse);
  page.on("requestfailed", onRequestFailed);
  try {
    const work = (async () => {
      await page.goto(`${BASE}${href}`, { waitUntil: "domcontentloaded", timeout: 10000 });
      await page.waitForTimeout(1200);
      const body = await page.evaluate(() => document.body.innerText).catch(() => "");
      row.url = page.url();
      row.title = await page.title().catch(() => null);
      const h1 = await page.locator("h1").first().textContent().catch(() => null);
      row.h1 = h1?.trim() ?? null;
      const bc = await page.locator("nav[aria-label*='breadcrumb' i], [data-testid='breadcrumbs']").first().textContent().catch(() => null);
      row.breadcrumb = bc?.replace(/\s+/g, " ").trim() ?? null;
      row.horizontal_scroll = await page.evaluate(() => {
        const el = document.scrollingElement ?? document.documentElement;
        return el.scrollWidth > el.clientWidth + 2;
      }).catch(() => false);
      row.failed_requests = [...failedReq];
      row.console_errors = consoleErrors.filter((c) => c.startsWith(`[${page.url()}`)).slice(0, 5);
      row.page_errors = pageErrors.filter((e) => e.startsWith(`[${page.url()}`)).slice(0, 5);
      if (body.includes("Página no encontrada")) { row.status = "NOT_FOUND"; }
      else if (body.includes("No fue posible cargar")) { row.status = "LOAD_ERROR"; }
      else if (!h1) { row.status = "NO_H1"; }
      if (row.horizontal_scroll) { row.status = row.status === "PASS" ? "HORIZONTAL_SCROLL" : `${row.status}+HSCROLL`; }
      const slug = href.replace(/[^a-zA-Z0-9]/g, "_") || "root";
      const shot = join(OUT, "screenshots", `${slug}.png`);
      await page.screenshot({ path: shot, fullPage: false, timeout: 5000 }).catch(() => undefined);
      row.screenshot = shot;
    })();
    await withTimeout(work, CAP_MS, href);
  } catch (e) {
    row.status = row.status === "PASS" ? "ERROR" : `${row.status}+ERROR`;
    row.error = String(e).slice(0, 200);
  } finally {
    row.duration_ms = Date.now() - t0;
    page.off("response", onResponse);
    page.off("requestfailed", onRequestFailed);
    results.push(row);
    log(`${row.status} ${href} (${row.duration_ms}ms)`);
  }
}
await browser.close().catch(() => undefined);

const totalMs = Date.now() - start;
const summary = {
  audit_run_id: RUN_ID, base_url: BASE, timestamp: new Date().toISOString(),
  total_routes: links.length, duration_ms: totalMs, cap_ms: CAP_MS,
  counts: results.reduce((acc, r) => { acc[r.status] = (acc[r.status] ?? 0) + 1; return acc; }, {}),
  console_errors_total: consoleErrors.length, page_errors_total: pageErrors.length,
};
writeFileSync(join(OUT, "route-crawl-results.json"), JSON.stringify({ summary, results }, null, 2));
writeFileSync(join(OUT, "route-crawl-report.md"), renderReport(summary, results));
log(`TERMINADO: ${JSON.stringify(summary)}`);

function renderReport(summary, rows) {
  const lines = [`# Route Crawl Report — ${summary.audit_run_id}`, "",
    `- Base: ${summary.base_url}`, `- Fecha: ${summary.timestamp}`,
    `- Rutas recorridas: ${summary.total_routes}`, `- Cap por ruta: ${summary.cap_ms}ms`,
    `- Duración: ${(summary.duration_ms / 1000).toFixed(1)}s`,
    `- Errores de consola totales: ${summary.console_errors_total}`,
    `- Excepciones de página totales: ${summary.page_errors_total}`,
    "", "## Resumen por estado", ""];
  for (const [k, v] of Object.entries(summary.counts)) lines.push(`- ${k}: ${v}`);
  lines.push("", "## Detalle por ruta", "", "| Ruta | Estado | H1 | Breadcrumb | HTTP fallidos | Consola | Excepción | H-Scroll | ms |");
  lines.push("|---|---|---|---|---|---|---|---|---|");
  for (const r of rows) {
    lines.push(`| ${r.href} | ${r.status} | ${(r.h1 ?? "-").replace(/\|/g, "/")} | ${(r.breadcrumb ?? "-").replace(/\|/g, "/")} | ${r.failed_requests.length} | ${r.console_errors.length} | ${r.page_errors.length} | ${r.horizontal_scroll ? "SÍ" : "no"} | ${r.duration_ms} |`);
  }
  const nonPass = rows.filter((r) => r.status !== "PASS");
  if (nonPass.length) {
    lines.push("", "## Rutas no-PASS", "");
    for (const r of nonPass) {
      lines.push(`### ${r.href} — ${r.status}`);
      if (r.error) lines.push(`- Error: ${r.error}`);
      for (const f of r.failed_requests) lines.push(`- HTTP: ${f}`);
      for (const c of r.console_errors) lines.push(`- Console: ${c}`);
      for (const e of r.page_errors) lines.push(`- Exception: ${e}`);
    }
  }
  return lines.join("\n");
}
