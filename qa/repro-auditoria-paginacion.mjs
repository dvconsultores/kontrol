/**
 * AUDITORIA-PAGINACION-CLIENTE · reproducción en navegador.
 *
 * Mide, entrando por el menú, lo que el servidor responde en `/audit/events` y lo
 * que la pantalla pinta: cuántos `items` y qué `total` llegan, cuántas filas se
 * ven, qué paginador hay y si pulsar «siguiente» pide otra página al servidor.
 *
 * Uso (pila local arriba):  node qa/repro-auditoria-paginacion.mjs
 */
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const raiz = join(dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(join(raiz, "resources/frontend/package.json"));
const { chromium } = require("playwright-core");

const BASE = process.env.KONTROL_E2E_BASE_URL ?? "http://localhost:5173";
const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";
const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "Kontrol2026Segura!";

const navegador = await chromium.launch();
const pagina = await navegador.newPage();
const peticiones = [];
const consola = [];
pagina.on("console", (m) => { if (m.type() === "error") consola.push(m.text()); });
pagina.on("response", async (r) => {
  if (!r.url().includes("/api/v1/audit/events")) return;
  const cuerpo = await r.json().catch(() => null);
  peticiones.push({
    url: r.url().replace(/^.*\/api\/v1/, ""), http: r.status(),
    forma: cuerpo && !Array.isArray(cuerpo) ? Object.keys(cuerpo).sort().join(",") : "array",
    items: cuerpo?.items?.length, total: cuerpo?.total, page: cuerpo?.page, page_size: cuerpo?.page_size,
  });
});

async function estado(etiqueta) {
  await pagina.waitForLoadState("networkidle");
  const filas = await pagina.locator("table tbody tr").count();
  const nav = pagina.getByRole("navigation", { name: "Paginación" });
  const paginadores = await nav.count();
  const texto = paginadores ? (await nav.first().innerText()).replace(/\s+/g, " ").match(/Página \d+ de \d+/)?.[0] : "—";
  const pie = await pagina.getByText(/Mostrando .* registros/).count()
    ? (await pagina.getByText(/Mostrando .* registros/).first().innerText()).trim() : "—";
  const caption = await pagina.locator("table caption").count() ? (await pagina.locator("table caption").innerText()).trim() : "—";
  console.log(`[${etiqueta}] filas visibles=${filas} · paginadores=${paginadores} · ${texto} · pie: ${pie} · caption: ${caption}`);
  return { filas, texto };
}

// Verdad del servidor, por API.
const login = await (await fetch(`${API}/auth/login`, {
  method: "POST", headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ tenant_code: "DEMO", username: "admin", password: PASSWORD }),
})).json();
const cabeceras = { Authorization: `Bearer ${login.access_token}` };
const porDefecto = await (await fetch(`${API}/audit/events`, { headers: cabeceras })).json();
console.log(`API por defecto: page=${porDefecto.page} page_size=${porDefecto.page_size} items=${porDefecto.items.length} total=${porDefecto.total}`);
const paginas = Math.ceil(porDefecto.total / porDefecto.page_size);
const ultima = await (await fetch(`${API}/audit/events?page=${paginas}`, { headers: cabeceras })).json();
console.log(`API última página (${paginas}): items=${ultima.items.length} · más allá del final (page=${paginas + 1}): items=${
  (await (await fetch(`${API}/audit/events?page=${paginas + 1}`, { headers: cabeceras })).json()).items.length}`);

// Lo que la persona ve, entrando por el menú.
await pagina.goto(`${BASE}/login`);
await pagina.getByLabel(/Empresa \(código\)/).fill("DEMO");
await pagina.getByLabel(/Usuario/).fill("admin");
await pagina.getByLabel(/Contraseña/).fill(PASSWORD);
await pagina.getByRole("button", { name: "Iniciar sesión" }).click();
await pagina.waitForURL((u) => !u.pathname.includes("login"), { timeout: 20000 });
await pagina.waitForLoadState("networkidle");
const compuerta = pagina.getByTestId(/^elegir-empresa-/);
if (await compuerta.count()) await compuerta.first().click();
await pagina.waitForLoadState("networkidle");
// La ruta se carga bajo demanda: se espera la respuesta, no solo la URL.
const primeraRespuesta = pagina.waitForResponse((r) => r.url().includes("/api/v1/audit/events"), { timeout: 60000 });
await pagina.locator('nav a[href="/auditoria"]').first().click();
await pagina.waitForURL((u) => u.pathname === "/auditoria", { timeout: 15000 });
await primeraRespuesta;
await pagina.locator("table tbody tr").first().waitFor({ timeout: 15000 });

await estado("al entrar");
const antes = peticiones.length;
let saltos = 0;
for (;;) {
  const siguiente = pagina.getByRole("button", { name: "Página siguiente" });
  if (!(await siguiente.count()) || (await siguiente.isDisabled())) break;
  await siguiente.click();
  saltos += 1;
  await pagina.waitForTimeout(700); // da tiempo a que salga una petición, si la pantalla la hace
  await estado(`tras «siguiente» nº ${saltos}`);
  if (saltos >= 3) break;
}
console.log(`peticiones a /audit/events al entrar: ${antes} · provocadas por «siguiente» (${saltos} pulsaciones): ${peticiones.length - antes}`);
for (const p of peticiones) console.log(`  ${p.http} ${p.url} → {${p.forma}} items=${p.items} total=${p.total} page=${p.page} page_size=${p.page_size}`);

const primera = peticiones[0];
const ui = await estado("final");
const alcanzables = primera ? Math.min(primera.items, primera.total) : 0;
console.log(`API_PAGE=${primera?.page} API_PAGE_SIZE=${primera?.page_size} API_ITEMS=${primera?.items} API_TOTAL=${primera?.total}`);
console.log(`eventos alcanzables desde la pantalla: ${peticiones.length - antes > 0 ? "todas las páginas del servidor" : `${alcanzables} de ${primera?.total}`}`);
console.log(`DOUBLE_PAGINATION=${primera && peticiones.length - antes === 0 && saltos > 0 ? "YES" : "NO"}`);
console.log(`errores de consola: ${consola.length}`);
for (const e of consola) console.log(`  ${e.slice(0, 300)}`);
console.log(`URL final: ${pagina.url()} · título: ${(await pagina.locator("h1").allInnerTexts()).join(" / ")}`);
void ui;
await navegador.close();
