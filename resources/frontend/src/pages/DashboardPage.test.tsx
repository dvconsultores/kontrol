/**
 * VER · La tarjeta «Versión» de Inicio pinta la versión que publica el diagnóstico, solo a quien puede
 * verla, y nunca un hueco ni un número inventado (PANEL-VERSION-VACIA; FR-001-084, FR-001-042).
 *
 * Antes leía `version` de `/health/ready`, que nunca la trajo: «—» siempre. Ahora la pide a
 * `/system/diagnostics` con `license:view`; sin permiso la tarjeta no existe; sin versión utilizable
 * dice «No disponible».
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiFetch = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

let permisos = new Set(["license:view"]);

vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({
    estado: "LISTA",
    tiene: (c: string) => permisos.has(c),
    puede: () => true,
    motivo: () => null,
    motivoDeCapacidad: () => null,
  }),
}));
vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({ activeCompany: { legal_name: "Demo C.A." } }),
}));
vi.mock("@/app/contexts/LicenseContext", () => ({
  useLicense: () => ({ mode: "FULL_ACCESS" }),
}));

const { DashboardPage, PERMISO_DE_VERSION, VERSION_NO_DISPONIBLE, versionMostrada } = await import("./DashboardPage");

const READY = { status: "ok", service: "kontrol-backend", database: "ok" };
const DIAGNOSTICO = {
  environment: "qa",
  version: "3.4.5",
  database: { ok: true },
  installation: { id: "KTL-VE-0001", state: "ACTIVE" },
  license: { activated: true, mode: "FULL_ACCESS", period_end: null },
};

function respuestas(diagnostico: unknown): void {
  apiFetch.mockImplementation((ruta: string) => {
    if (ruta === "/health/ready") return Promise.resolve(READY);
    if (ruta === "/system/diagnostics") return diagnostico instanceof Error ? Promise.reject(diagnostico) : Promise.resolve(diagnostico);
    if (ruta === "/reporting/dashboard") return Promise.reject(new Error("sin indicadores en esta prueba"));
    return Promise.reject(new Error(`ruta inesperada ${ruta}`));
  });
}

function montar(): void {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function tarjetaVersion(): HTMLElement | null {
  return screen.queryByText("Versión");
}

/** El valor pintado junto a la etiqueta de una tarjeta: la tarjeta es etiqueta + valor. */
function valorDeTarjeta(etiqueta: string): string {
  const label = screen.getByText(etiqueta);
  return label.nextElementSibling?.textContent ?? "";
}

describe("DashboardPage · tarjeta «Versión»", () => {
  beforeEach(() => {
    apiFetch.mockReset();
    permisos = new Set([PERMISO_DE_VERSION]);
  });

  it("VER-04 · con permiso pinta la versión que publica el diagnóstico, y la pide ahí, no al health", async () => {
    respuestas(DIAGNOSTICO);
    montar();
    expect(await screen.findByText("3.4.5")).toBeTruthy();
    expect(tarjetaVersion()).toBeTruthy();
    expect(apiFetch).toHaveBeenCalledWith("/system/diagnostics");
    expect(valorDeTarjeta("Versión")).toBe("3.4.5");
  });

  it("VER-10 · mientras carga lo dice, y nunca pinta un hueco", async () => {
    respuestas(new Promise(() => undefined)); // el diagnóstico no responde aún
    montar();
    expect(valorDeTarjeta("Versión")).toBe("Cargando…");
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/system/diagnostics"));
    expect(valorDeTarjeta("Versión")).not.toBe("—");
  });

  it("VER-05 · si el diagnóstico llega sin versión utilizable, dice «No disponible»", async () => {
    respuestas({ ...DIAGNOSTICO, version: "   " });
    montar();
    expect(await screen.findByText(VERSION_NO_DISPONIBLE)).toBeTruthy();
  });

  it("VER-06 · un `null` o un campo ausente tampoco se pintan en crudo", async () => {
    respuestas({ ...DIAGNOSTICO, version: null });
    montar();
    expect(await screen.findByText(VERSION_NO_DISPONIBLE)).toBeTruthy();
    expect(versionMostrada({})).toBe(VERSION_NO_DISPONIBLE);
    expect(versionMostrada(undefined)).toBe(VERSION_NO_DISPONIBLE);
    expect(versionMostrada({ version: undefined })).toBe(VERSION_NO_DISPONIBLE);
    expect(versionMostrada({ version: 7 })).toBe(VERSION_NO_DISPONIBLE);
  });

  it("VER-05b · si el diagnóstico falla, la tarjeta dice «No disponible» y no inventa un número", async () => {
    respuestas(new Error("503"));
    montar();
    expect(await screen.findByText(VERSION_NO_DISPONIBLE)).toBeTruthy();
    expect(screen.queryByText("1.0.0")).toBeNull();
  });

  it("VER-13 · sin `license:view` la tarjeta no existe y el diagnóstico no se pide", async () => {
    permisos = new Set();
    respuestas(DIAGNOSTICO);
    montar();
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/health/ready"));
    expect(tarjetaVersion()).toBeNull();
    expect(apiFetch).not.toHaveBeenCalledWith("/system/diagnostics");
    expect(screen.queryByText("3.4.5")).toBeNull();
  });

  it("VER-11 · la tarjeta «API» sigue leyendo el health, que no trae versión", async () => {
    respuestas(DIAGNOSTICO);
    montar();
    expect(await screen.findByText("ok")).toBeTruthy();
    expect(apiFetch).toHaveBeenCalledWith("/health/ready");
  });

  it("VER-16 · la tarjeta refleja la versión que el servidor publique, sea cual sea", async () => {
    respuestas({ ...DIAGNOSTICO, version: "12.0.0-rc.1" });
    montar();
    expect(await screen.findByText("12.0.0-rc.1")).toBeTruthy();
  });
});
