import { defineConfig, devices } from "@playwright/test";

/**
 * KONTROL - Playwright E2E.
 * Los flujos críticos requieren el backend levantado (compose.dev) y un
 * servidor de prueba. Se definen los proyectos base.
 */
/** Suites que necesitan el estado que el resto deja: van en proyectos dependientes, al final y en orden. */
const TRAS_LA_SUITE = /licencia-revision\.spec\.ts/;
const TRAS_LA_REVISION = /licencia-sync\.spec\.ts/;
const TRAS_EL_SYNC = /licencia-rotacion\.spec\.ts/;
const TRAS_LA_ROTACION = /licencia-tasa\.spec\.ts/;
/** Importan licencias aceptadas: cambian el estado de toda la instalación y no pueden correr junto a la suite de producto. */
const ESTADO_DE_LICENCIA = /licencia-(import|periodo)\.spec\.ts/;
const DEPENDIENTES = /licencia-(import|periodo|revision|sync|rotacion|tasa)\.spec\.ts/;
/** Humo del entorno de prueba de la dueña: solo bajo pedido (`--project=humo-uat`), no en la canónica (QA-LIC-GOB-01). */
const HUMO_UAT = /uat-humo-gobierno\.spec\.ts/;

export default defineConfig({
  testDir: "./e2e",
  globalSetup: "./e2e/global-setup.ts",
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  reporter: [["list"]],
  use: {
    baseURL: process.env.KONTROL_E2E_BASE_URL ?? "http://localhost:5173",
    // Con `retries` 0 nada se reintenta, así que «en el primer reintento» no capturaba nunca el primer
    // fallo: cuatro fallos de 2026-10-12 quedaron sin explicar por eso (E2E-PANTALLA-SIN-PINTAR). La
    // traza se retiene solo si la prueba falla; en verde se descarta.
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "chromium", testIgnore: [DEPENDIENTES, HUMO_UAT], use: { ...devices["Desktop Chrome"] } },
    { name: "firefox", testIgnore: [DEPENDIENTES, HUMO_UAT], use: { ...devices["Desktop Firefox"] } },
    { name: "webkit", testIgnore: [DEPENDIENTES, HUMO_UAT], use: { ...devices["Desktop Safari"] } },
    // Después de la suite de producto (chromium, la de la canónica) y en un solo proyecto: las importaciones de licencia ya no se cruzan con ella.
    { name: "licencia-estado", testMatch: ESTADO_DE_LICENCIA, dependencies: ["chromium"], use: { ...devices["Desktop Chrome"] } },
    // El linaje revisionado de la licencia cambia el identificador vigente y deja el estado revisionado:
    // corre después de todo lo demás (depende de `chromium`), sobre la misma base de la corrida.
    { name: "licencia-revision", testMatch: TRAS_LA_SUITE, dependencies: ["licencia-estado"], use: { ...devices["Desktop Chrome"] } },
    // El sync autenticado contra la Autoridad Central real de la corrida: después del linaje, sobre el estado que deja.
    { name: "licencia-sync", testMatch: TRAS_LA_REVISION, dependencies: ["licencia-revision"], use: { ...devices["Desktop Chrome"] } },
    // La rotación de la clave del propietario (confianza A+B, kid firmado): al final, sobre el estado que deja el sync.
    { name: "licencia-rotacion", testMatch: TRAS_EL_SYNC, dependencies: ["licencia-sync"], use: { ...devices["Desktop Chrome"] } },
    // El límite de tasa del desafío de la autoridad real: inunda la ventana, así que va el último de todos.
    { name: "licencia-tasa", testMatch: TRAS_LA_ROTACION, dependencies: ["licencia-rotacion"], use: { ...devices["Desktop Chrome"] } },
    // El humo autenticado del entorno de prueba de la dueña: solo con `--project=humo-uat`.
    { name: "humo-uat", testMatch: HUMO_UAT, use: { ...devices["Desktop Chrome"] } },
  ],
});
