import { defineConfig, devices } from "@playwright/test";

/**
 * KONTROL - Playwright E2E.
 * Los flujos críticos requieren el backend levantado (compose.dev) y un
 * servidor de prueba. Se definen los proyectos base.
 */
/** Suites que necesitan el estado que el resto deja: van en un proyecto dependiente, al final. */
const TRAS_LA_SUITE = /licencia-revision\.spec\.ts/;

export default defineConfig({
  testDir: "./e2e",
  globalSetup: "./e2e/global-setup.ts",
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  reporter: [["list"]],
  use: {
    baseURL: process.env.KONTROL_E2E_BASE_URL ?? "http://localhost:5173",
    trace: "on-first-retry",
  },
  projects: [
    { name: "chromium", testIgnore: TRAS_LA_SUITE, use: { ...devices["Desktop Chrome"] } },
    { name: "firefox", testIgnore: TRAS_LA_SUITE, use: { ...devices["Desktop Firefox"] } },
    { name: "webkit", testIgnore: TRAS_LA_SUITE, use: { ...devices["Desktop Safari"] } },
    // El linaje revisionado de la licencia cambia el identificador vigente y deja el estado revisionado:
    // corre después de todo lo demás (depende de `chromium`), sobre la misma base de la corrida.
    { name: "licencia-revision", testMatch: TRAS_LA_SUITE, dependencies: ["chromium"], use: { ...devices["Desktop Chrome"] } },
  ],
});
