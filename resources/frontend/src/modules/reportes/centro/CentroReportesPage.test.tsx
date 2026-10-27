import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiFetch = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

let permisos = new Set<string>();

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

const { CentroReportesPage, REPORTS } = await import("./CentroReportesPage");

function montar(): void {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <CentroReportesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  apiFetch.mockImplementation((ruta: string) => {
    if (typeof ruta === "string" && ruta.startsWith("/reporting/reports/")) {
      return Promise.resolve({ report_key: "x", count: 0, total: 0, rows: [] });
    }
    return Promise.reject(new Error(`ruta inesperada ${ruta}`));
  });
});

describe("CentroReportesPage", () => {
  it("CR-01 muestra Operativos y pide operational_inventario cuando solo tiene inventario:view", async () => {
    permisos = new Set(["reportes:view", "inventario:view"]);
    montar();

    expect(screen.queryByRole("button", { name: "Ejecutivos" })).toBeNull();
    expect(screen.getByRole("button", { name: "Operativos" })).toBeTruthy();

    await waitFor(() => {
      expect(
        apiFetch.mock.calls.some(
          ([ruta]) => typeof ruta === "string" && ruta.startsWith("/reporting/reports/operational_inventario"),
        ),
      ).toBe(true);
    });

    const rutas = apiFetch.mock.calls.map((c) => c[0]).filter((r) => typeof r === "string");
    expect(rutas.some((r) => r.startsWith("/reporting/reports/executive_ventas"))).toBe(false);
  });

  it("CR-02 no pinta categorías ni pide reportes cuando no hay capacidades de origen", async () => {
    permisos = new Set(["reportes:view"]);
    montar();

    expect(await screen.findByText("No tiene autoridad para ver ningún reporte en esta empresa.")).toBeTruthy();
    expect(apiFetch).not.toHaveBeenCalled();
  });

  it("CR-03 oculta Financieros cuando falta compras:view", () => {
    permisos = new Set(["reportes:view", "ventas:view"]);
    montar();

    expect(screen.getByRole("button", { name: "Ejecutivos" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Financieros" })).toBeNull();
  });

  it("CR-04 mantiene paridad con report_capabilities del backend", () => {
    const operaciones = JSON.parse(
      readFileSync(resolve(__dirname, "../../../tests/fixtures/operaciones.json"), "utf8"),
    ) as { report_capabilities: Record<string, string[]> };
    const reportCapabilities = operaciones.report_capabilities;

    const clavesComparadas = REPORTS.map((r) =>
      r.key.startsWith("fiscal_libros_") ? "fiscal_libros_*" : r.key,
    );

    for (const r of REPORTS) {
      const clave = r.key.startsWith("fiscal_libros_") ? "fiscal_libros_*" : r.key;
      expect([...r.capacidades]).toEqual(reportCapabilities[clave]);
    }

    expect(new Set(clavesComparadas).size).toBe(Object.keys(reportCapabilities).length);
  });
});
