import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiFetch = vi.fn();
const notify = vi.fn();
const descargarArchivo = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

vi.mock("@/api/descargas", async (original) => ({
  ...(await original<typeof import("@/api/descargas")>()),
  descargarArchivo: (...args: unknown[]) => descargarArchivo(...args),
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
  useNotifications: () => ({ notify }),
}));

const { CentroReportesPage, REPORTS } = await import("./CentroReportesPage");
import { ApiError } from "@/api/client";

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
    if (typeof ruta === "string" && ruta === "/reporting/exports") {
      return Promise.resolve({ id: "e9", file_ref: "report-executive_ventas-20261027120000.csv", status: "DONE" });
    }
    return Promise.reject(new Error(`ruta inesperada ${ruta}`));
  });
  descargarArchivo.mockResolvedValue("report-executive_ventas-20261027120000.csv");
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

  it("CR-05 descarga el archivo tras crear la exportación", async () => {
    permisos = new Set(["reportes:view", "ventas:view"]);
    montar();

    await screen.findByRole("button", { name: "Exportar CSV (auditado)" });
    fireEvent.click(screen.getByRole("button", { name: "Exportar CSV (auditado)" }));

    await waitFor(() => {
      expect(descargarArchivo).toHaveBeenCalledWith("/reporting/exports/e9/download", "exportacion-e9");
    });

    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith({
        type: "success",
        title: "Archivo descargado",
        description: "report-executive_ventas-20261027120000.csv",
      });
    });
  });

  it("CR-06 notifica el error cuando falla la creación y no intenta descargar", async () => {
    permisos = new Set(["reportes:view", "ventas:view"]);
    apiFetch.mockImplementation((ruta: string) => {
      if (typeof ruta === "string" && ruta.startsWith("/reporting/reports/")) {
        return Promise.resolve({ report_key: "x", count: 0, total: 0, rows: [] });
      }
      if (typeof ruta === "string" && ruta === "/reporting/exports") {
        return Promise.reject(new ApiError(403, {
          code: "PERMISSION_DENIED",
          message: "No tiene permiso para esta acción",
        }));
      }
      return Promise.reject(new Error(`ruta inesperada ${ruta}`));
    });
    montar();

    await screen.findByRole("button", { name: "Exportar CSV (auditado)" });
    fireEvent.click(screen.getByRole("button", { name: "Exportar CSV (auditado)" }));

    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith({
        type: "error",
        title: "No fue posible exportar",
        description: "No tiene permiso para esta acción",
      });
    });
    expect(descargarArchivo).not.toHaveBeenCalled();
  });

  it("CR-07 notifica el error cuando falla la descarga y nunca muestra éxito", async () => {
    permisos = new Set(["reportes:view", "ventas:view"]);
    descargarArchivo.mockRejectedValue(new TypeError("Failed to fetch"));
    montar();

    await screen.findByRole("button", { name: "Exportar CSV (auditado)" });
    fireEvent.click(screen.getByRole("button", { name: "Exportar CSV (auditado)" }));

    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith({
        type: "error",
        title: "No fue posible descargar",
        description:
          "No hay conexión con el servidor. Inténtelo de nuevo. La exportación quedó creada; puede descargarla desde Exportaciones.",
      });
    });
    expect(notify).not.toHaveBeenCalledWith(
      expect.objectContaining({ type: "success", title: "Archivo descargado" }),
    );
  });

  it("CR-08 un período inválido muestra el error y no pide el reporte", async () => {
    permisos = new Set(["reportes:view", "ventas:view"]);
    montar();

    await waitFor(() => {
      expect(
        apiFetch.mock.calls.some(
          ([ruta]) => typeof ruta === "string" && ruta.startsWith("/reporting/reports/"),
        ),
      ).toBe(true);
    });
    apiFetch.mockClear();

    fireEvent.change(screen.getByPlaceholderText("2026-01"), { target: { value: "2026-13" } });

    expect(await screen.findByText("Formato AAAA-MM, mes 01 a 12.")).toBeTruthy();
    expect(screen.getByPlaceholderText("2026-01").getAttribute("aria-invalid")).toBe("true");
    expect(
      apiFetch.mock.calls.some(
        ([ruta]) => typeof ruta === "string" && ruta.includes("period=2026-13"),
      ),
    ).toBe(false);
  });

  it("CR-09 un período válido viaja al servidor", async () => {
    permisos = new Set(["reportes:view", "ventas:view"]);
    montar();

    fireEvent.change(screen.getByPlaceholderText("2026-01"), { target: { value: "2026-10" } });

    await waitFor(() => {
      expect(
        apiFetch.mock.calls.some(
          ([ruta]) => typeof ruta === "string" && ruta.includes("period=2026-10"),
        ),
      ).toBe(true);
    });
  });

  it("CR-10 avisa cuando el libro fiscal no filtra por período", async () => {
    permisos = new Set(["reportes:view", "fiscal:view"]);
    apiFetch.mockImplementation((ruta: string) => {
      if (typeof ruta === "string" && ruta.startsWith("/reporting/reports/")) {
        return Promise.resolve({
          report_key: "fiscal_libros_VENTAS",
          count: 1,
          total: 10,
          rows: [],
          period_applied: false,
          period_rule: "LEGAL_VALIDATION_REQUIRED",
        });
      }
      if (typeof ruta === "string" && ruta === "/reporting/exports") {
        return Promise.resolve({ id: "e9", file_ref: "report-fiscal_libros_VENTAS-20261027120000.csv", status: "DONE" });
      }
      return Promise.reject(new Error(`ruta inesperada ${ruta}`));
    });
    montar();

    fireEvent.click(screen.getByRole("button", { name: "Fiscales" }));
    fireEvent.change(screen.getByPlaceholderText("2026-01"), { target: { value: "2026-10" } });

    expect((await screen.findByRole("status")).textContent).toContain("no se filtra por período");
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
