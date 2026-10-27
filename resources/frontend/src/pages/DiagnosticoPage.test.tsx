/**
 * DIAGNOSTICO · La pantalla pinta lo que el diagnóstico responde (FR-054-E2EDB-031, FR-001-084).
 *
 * Antes la pantalla esperaba una lista `services` dentro de la respuesta, que el servidor nunca
 * envió, y caía al pintar. Aquí recibe la respuesta real del servidor y comprueba que se muestra
 * entera, que los estados ausentes se dicen y que cada fila indica si lo que muestra está bien.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { DiagnosticsResponse } from "@/api/types";

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

const { DiagnosticoPage, PERMISO_DE_DIAGNOSTICO, filasDeDiagnostico } = await import("./DiagnosticoPage");

const SANO: DiagnosticsResponse = {
  environment: "qa",
  version: "1.0.0",
  database: { ok: true },
  installation: { id: "KTL-VE-0001", state: "ACTIVE" },
  license: { activated: true, mode: "FULL_ACCESS", period_end: "2027-01-01T00:00:00+00:00" },
};

function montar(): void {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <DiagnosticoPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("DiagnosticoPage", () => {
  beforeEach(() => {
    apiFetch.mockReset();
    permisos = new Set(["license:view"]);
  });

  it("DIAG-01 · con la respuesta real del servidor la pantalla se pinta entera", async () => {
    apiFetch.mockResolvedValue({ ...SANO, storage: "/ruta/interna/que-no-se-muestra" });
    montar();
    expect(await screen.findByText("1.0.0")).toBeTruthy();
    for (const texto of [
      "Entorno",
      "qa",
      "Base de datos",
      "ok",
      "Instalación",
      "ACTIVE",
      "Identificador",
      "KTL-VE-0001",
      "Licencia",
      "FULL_ACCESS",
    ]) {
      expect(screen.getByText(texto)).toBeTruthy();
    }
    expect(screen.getByRole("heading", { level: 1, name: "Diagnóstico" })).toBeTruthy();
    expect(screen.queryByText(/ruta\/interna/)).toBeNull();
    expect(apiFetch).toHaveBeenCalledWith("/system/diagnostics");
  });

  it("DIAG-02 · una instalación sin base, sin identidad y sin licencia se dice, no se rompe", async () => {
    apiFetch.mockResolvedValue({
      environment: "local",
      version: "1.0.0",
      database: { ok: false },
      installation: { id: null, state: null },
      license: { activated: false, mode: null, period_end: null },
    });
    montar();
    expect(await screen.findByText("sin conexión")).toBeTruthy();
    expect(screen.getByText("sin identidad")).toBeTruthy();
    expect(screen.getByText("sin licencia")).toBeTruthy();
    expect(screen.getByText("—")).toBeTruthy();
  });

  it("DIAG-03 · si el diagnóstico no responde, se dice", async () => {
    apiFetch.mockRejectedValue(new Error("caído"));
    montar();
    expect(await screen.findByText("No fue posible obtener el diagnóstico.")).toBeTruthy();
  });

  it("DIAG-05 · sin el permiso: acceso prohibido, nada del diagnóstico y ni una petición", () => {
    permisos = new Set(["dashboard:view", "organization:view"]);
    apiFetch.mockResolvedValue(SANO);
    montar();
    expect(screen.getByRole("heading", { level: 1, name: "Acceso prohibido" })).toBeTruthy();
    expect(screen.queryByText("1.0.0")).toBeNull();
    expect(screen.queryByText("Entorno")).toBeNull();
    expect(apiFetch).not.toHaveBeenCalled();
  });

  it("DIAG-06 · el permiso que abre la pantalla es el de leer la licencia", () => {
    expect(PERMISO_DE_DIAGNOSTICO).toBe("license:view");
  });

  it("DIAG-04 · cada fila dice si lo que muestra está bien", () => {
    expect(filasDeDiagnostico(SANO).map((f) => [f.nombre, f.valor, f.correcto])).toEqual([
      ["Entorno", "qa", true],
      ["Base de datos", "ok", true],
      ["Instalación", "ACTIVE", true],
      ["Identificador", "KTL-VE-0001", true],
      ["Licencia", "FULL_ACCESS", true],
    ]);
    const roto: DiagnosticsResponse = {
      ...SANO,
      database: { ok: false },
      installation: { id: null, state: null },
      license: { activated: false, mode: "READ_ONLY", period_end: null },
    };
    expect(filasDeDiagnostico(roto).map((f) => [f.nombre, f.valor, f.correcto])).toEqual([
      ["Entorno", "qa", true],
      ["Base de datos", "sin conexión", false],
      ["Instalación", "sin identidad", false],
      ["Identificador", "—", false],
      ["Licencia", "READ_ONLY", false],
    ]);
  });
});
