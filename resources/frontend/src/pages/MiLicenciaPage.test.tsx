/**
 * F-03/F-04 · «Mi licencia» exige `license:view` antes de pedir nada (FR-010-113).
 * El backend es la autoridad —`GET /license/detail` responde 401/403—; aquí se comprueba que la
 * pantalla no pide ni pinta el detalle a quien no puede verlo, y que con permiso lo pide y lo pinta.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { LicenseStatus } from "@/api/types";

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

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: vi.fn() }),
}));

const { MiLicenciaPage } = await import("./MiLicenciaPage");

const DETALLE: LicenseStatus = {
  installation_id: "KTL-XX-0000-TEST",
  activated: true,
  mode: "FULL_ACCESS",
  period_start: "2026-04-01T00:00:00+00:00",
  period_end: "2027-03-31T23:59:59+00:00",
  read_only_start: "2027-05-01T00:00:00+00:00",
  entitlements: {},
  minimum_version: "1.0.0",
  license_url: "/mi-licencia",
};

function montar() {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter>
        <MiLicenciaPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("MiLicenciaPage", () => {
  beforeEach(() => {
    apiFetch.mockReset();
    permisos = new Set(["license:view"]);
  });

  it("F-03 · sin license:view: acceso prohibido y ninguna petición", async () => {
    permisos = new Set(["organization:view"]);
    montar();
    expect(await screen.findByRole("heading", { level: 1, name: "Acceso prohibido" })).toBeTruthy();
    expect(screen.queryByRole("heading", { level: 1, name: "Mi licencia" })).toBeNull();
    expect(screen.queryByText("KTL-XX-0000-TEST")).toBeNull();
    expect(apiFetch).not.toHaveBeenCalled();
  });

  it("F-04 · con license:view pide /license/detail y pinta identificador, modo y fechas", async () => {
    apiFetch.mockResolvedValue(DETALLE);
    montar();
    expect(await screen.findByText("KTL-XX-0000-TEST")).toBeTruthy();
    expect(screen.getByRole("heading", { level: 1, name: "Mi licencia" })).toBeTruthy();
    expect(screen.getByText("FULL ACCESS")).toBeTruthy();
    for (const etiqueta of ["Instalación", "Modo", "Período pagado", "Modo solo consulta desde"]) {
      expect(screen.getByText(etiqueta)).toBeTruthy();
    }
    expect(apiFetch).toHaveBeenCalledWith("/license/detail");
    expect(apiFetch).not.toHaveBeenCalledWith("/license/status");
    expect(screen.queryByRole("heading", { level: 1, name: "Acceso prohibido" })).toBeNull();
  });

  it("F-04b · si el detalle falla se muestra el error, no el acceso prohibido", async () => {
    apiFetch.mockRejectedValue(new Error("403"));
    montar();
    expect(await screen.findByText("No fue posible consultar el estado de la licencia.")).toBeTruthy();
    expect(screen.queryByRole("heading", { level: 1, name: "Acceso prohibido" })).toBeNull();
  });
});
