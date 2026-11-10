/**
 * PUERTAS PERMANENTES DE COMPLETITUD (Spec 012 — T-08/T-09).
 *
 * Gate 1/2 — Ningún elemento del menú puede apuntar a una ruta sin declarar o a
 *            una página inexistente (evita el patrón "Sucursales"/"Usuarios" 404).
 * Gate 3/4 — Ninguna página puede llamar un endpoint que no exista en el backend
 *            (contract contra el fixture OpenAPI; regenerar con el script de backend).
 *
 * Estos tests fallan en `npm test` / CI si se introduce una cadena incompleta.
 */
import { readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const SRC = resolve(__dirname, "..");

const read = (rel: string): string => readFileSync(resolve(SRC, rel), "utf8");
const exists = (rel: string): boolean => existsSync(resolve(SRC, rel));

const sidebar = read("layout/Sidebar.tsx");
const router = read("app/router.tsx");
const openapi = JSON.parse(read("tests/fixtures/openapi-routes.json")) as {
  routes: { method: string; path: string }[];
};

// --------------------------------------------------------------------------- //
// Extracción
// --------------------------------------------------------------------------- //
// La etiqueta puede ser literal o una clave del catálogo (`t("…")`, Spec 047):
// la puerta tiene que ver también esas entradas, o dejaría de mirarlas en silencio.
const menuTo = [...sidebar.matchAll(/\{\s*to:\s*"([^"]+)",\s*label:\s*(?:"([^"]+)"|t\("([^"]+)"\))/g)].map((m) => ({
  to: m[1],
  label: m[2] ?? m[3],
}));

const routerPaths = [...router.matchAll(/path:\s*"([^"]+)"/g)].map((m) => m[1]);
const routeSet = new Set(routerPaths);

// imports: import { A, B as C } from "@/path"  (solo componentes estáticos)
const imports: Record<string, string> = {};
for (const m of router.matchAll(/import\s*\{([^}]+)\}\s*from\s*"@\/([^"]+)"/g)) {
  for (const name of m[1].split(",")) {
    const n = name.trim();
    if (!n) continue;
    if (n.includes(" as ")) {
      imports[n.split(" as ")[1].trim()] = m[2];
    } else {
      imports[n] = m[2];
    }
  }
}

// Rutas con code-splitting (T-219): extraer path + módulo de la página desde
// el patrón `lazy: () => import("@/...").then((m) => ({ Component: m.X }))`.
const routePages = [...router.matchAll(
  /(?:\{\s*path:\s*"([^"]+)"\s*,\s*lazy:\s*\(\)\s*=>\s*import\("([^"]+)"\)|index:\s*true\s*,\s*lazy:\s*\(\)\s*=>\s*import\("([^"]+)"\))/g,
)].map((m) => ({
  path: m[1] ?? "",
  modulePath: m[2] ?? m[3],
}));

const normalizeMenuRoute = (to: string): string => to.replace(/^\//, "");

function apiCallsIn(text: string): string[] {
  const calls: string[] = [];
  // apiFetch<...genéricos (anidados)...>( "path" | `path` )
  for (const m of text.matchAll(/apiFetch\s*(?:<[^()]*>)?\s*\(\s*(["'`])([^"'`]*)/g)) {
    calls.push(m[2]);
  }
  return calls;
}

function pageApiCalls(rel: string): string[] {
  const text = read(rel);
  const calls = apiCallsIn(text);
  // Una página puede delegar la petición en un módulo tipado por endpoint
  // (`@/api/<módulo>`, como `@/api/audit` u `@/api/organization`): las rutas que
  // ese módulo llama cuentan como llamadas de la página, y se validan igual.
  for (const m of text.matchAll(/from\s+["']@\/api\/([\w-]+)["']/g)) {
    if (m[1] === "client" || m[1] === "types") continue;
    const modulo = `api/${m[1]}.ts`;
    if (existsSync(resolve(SRC, modulo))) calls.push(...apiCallsIn(read(modulo)));
  }
  return calls;
}

function patternToSegments(p: string): string[] {
  return p.split("/").filter(Boolean);
}

function matchesEndpoint(callBase: string): boolean {
  const call = callBase.split("?")[0].replace(/^\//, "").replace(/\$\{[^}]*\}/g, "*");
  const callSegs = patternToSegments(call);
  if (callSegs.length === 0) return false;
  return openapi.routes.some(({ path }) => {
    const segs = patternToSegments(path);
    if (segs.length !== callSegs.length) return false;
    return segs.every((s, i) => s === "*" || callSegs[i] === "*" || s === callSegs[i]);
  });
}

// --------------------------------------------------------------------------- //
// Gate 1 — menú → ruta declarada
// --------------------------------------------------------------------------- //
describe("G1: todo menú apunta a una ruta declarada", () => {
  it.each(menuTo.map((m) => [m.to, m.label] as const))("menú %s (%s)", (to, label) => {
    const norm = normalizeMenuRoute(to);
    // "/" → ruta índice (index:true); rutas con "/" final se normalizan
    const declared = norm === "" || routeSet.has(norm) || routeSet.has(norm + "/") || routeSet.has("*");
    expect(declared, `menú "${label}" → ${to}`).toBe(true);
  });
});

// --------------------------------------------------------------------------- //
// Gate 2 — ruta → página existente (code-splitting lazy)
// --------------------------------------------------------------------------- //
describe("G2: toda ruta tiene página existente", () => {
  it.each(routePages.map((r) => [r.path, r.modulePath] as const))("ruta %s (%s)", (_path, mod) => {
    const rel = mod.replace(/^@\//, "");
    expect(rel, `sin módulo para la ruta`).toBeTruthy();
    expect(exists(`${rel}.tsx`) || exists(`${rel}/index.tsx`), `${rel} no existe`).toBe(true);
  });
});

// --------------------------------------------------------------------------- //
// Gate 3/4 — página → endpoint backend (contract)
// --------------------------------------------------------------------------- //
const pages = [
  "pages/DashboardPage.tsx",
  "pages/EmpresasPage.tsx",
  "pages/MiLicenciaPage.tsx",
  "modules/organizacion/sucursales/SucursalesPage.tsx",
  "modules/organizacion/almacenes/AlmacenesPage.tsx",
  "modules/organizacion/establecimientos/EstablecimientosPage.tsx",
  "modules/organizacion/ubicaciones/UbicacionesPage.tsx",
  "modules/seguridad/usuarios/UsuariosPage.tsx",
  "modules/seguridad/roles/RolesPage.tsx",
  "modules/seguridad/sesiones/SesionesPage.tsx",
  "modules/maestros/perfiles/PerfilesFiscalesPage.tsx",
  "modules/maestros/atributos/AtributosPage.tsx",
  "modules/maestros/almacenamiento/AlmacenamientoPage.tsx",
  "modules/maestros/planificacion/PlanificacionPage.tsx",
  "modules/maestros/terceros/TercerosPage.tsx",
  "modules/ventas/ordenes/OrdenesVentasPage.tsx",
  "modules/ventas/facturas/FacturasVentasPage.tsx",
  "modules/ventas/cotizaciones/CotizacionesPage.tsx",
  "modules/ventas/devoluciones/DevolucionesVentasPage.tsx",
  "modules/ventas/notas/NotasVentasPage.tsx",
  "modules/ventas/despacho/DespachoPage.tsx",
  "modules/ventas/cuentas-por-cobrar/CuentasPorCobrarPage.tsx",
  "modules/compras/ordenes/OrdenesComprasPage.tsx",
  "modules/compras/requisiciones/RequisicionesPage.tsx",
  "modules/compras/requisiciones/RequisicionNuevaPage.tsx",
  "modules/compras/requisiciones/RequisicionDetallePage.tsx",
  "modules/compras/cotizaciones/CotizacionesComprasPage.tsx",
  "modules/compras/facturas/FacturasProveedorPage.tsx",
  "modules/compras/devoluciones/DevolucionesComprasPage.tsx",
  "modules/compras/notas/NotasComprasPage.tsx",
  "modules/compras/cuentas-por-pagar/CuentasPorPagarPage.tsx",
  "modules/inventario/existencias/ExistenciasPage.tsx",
  "modules/inventario/kardex/KardexPage.tsx",
  "modules/inventario/movimientos/MovimientosPage.tsx",
  "modules/inventario/tipos-movimiento/TiposMovimientoPage.tsx",
  "modules/inventario/transferencias/TransferenciasPage.tsx",
  "modules/inventario/conteos/ConteosPage.tsx",
  "modules/inventario/ajustes/AjustesPage.tsx",
  "modules/inventario/lotes/LotesPage.tsx",
  "modules/inventario/seriales/SerialesPage.tsx",
  "modules/inventario/reservas/ReservasPage.tsx",
  "modules/inventario/valorizacion/ValorizacionPage.tsx",
  "modules/regulatorio/aprobaciones/AprobacionesPage.tsx",
  "modules/regulatorio/evaluacion/EvaluacionPage.tsx",
  "modules/regulatorio/organismos/OrganismosPage.tsx",
  "modules/regulatorio/permisos/PermisosPage.tsx",
  "modules/regulatorio/vehiculos/VehiculosPage.tsx",
  "modules/fiscal/emision/EmisionPage.tsx",
  "modules/fiscal/lotes-declaracion/LotesDeclaracionPage.tsx",
  "modules/licenciamiento/configuracion/ConfiguracionCentralPage.tsx",
  "modules/notificaciones/centro/CentroNotificacionesPage.tsx",
  "modules/notificaciones/tareas/TareasPage.tsx",
  "modules/notificaciones/tareas/TareaDetallePage.tsx",
  "modules/notificaciones/alertas/AlertasPage.tsx",
  "modules/notificaciones/reglas/ReglasPage.tsx",
  "modules/notificaciones/preferencias/PreferenciasPage.tsx",
];

describe("G3/G4: las páginas llaman endpoints existentes", () => {
  for (const page of pages) {
    it(`${page}: llamadas API válidas`, () => {
      const calls = pageApiCalls(page);
      expect(calls.length, `${page} sin llamadas API (¿placeholder?)`).toBeGreaterThan(0);
      for (const call of calls) {
        expect(matchesEndpoint(call), `${page} llama endpoint inexistente: ${call}`).toBe(true);
      }
    });
  }
});
