/**
 * AUDITORIA-SOBRE-VS-ARRAY · la pantalla consume el sobre paginado, no un array.
 *
 * El servidor responde `{items, total, page, page_size}`; la pantalla se lo
 * entregaba entero a la tabla como si fuera la lista y no pintaba una sola
 * fila, sin error y sin estado vacío. Lo que se fija aquí: las filas salen de
 * `items`, un sobre vacío es el estado vacío, un error sigue siendo un error,
 * y una respuesta que no sea el sobre no se acepta por la puerta de atrás.
 *
 * La columna «Fecha» tiene su propia prueba (`AuditoriaPage.fecha.test.tsx`), y la
 * paginación de servidor la suya (`AuditoriaPage.paginacion.test.tsx`).
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, expectTypeOf, it, vi } from "vitest";

import type { AuditEvent, PagedResult } from "@/api/types";

const apiFetch = vi.fn();
vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));
const tieneMock = vi.fn<(capacidad: string, alcance: string) => boolean>(() => false);
vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({
    estado: "LISTA",
    puede: () => true,
    tiene: (capacidad: string, alcance: string) => tieneMock(capacidad, alcance),
    motivo: () => null,
    motivoDeCapacidad: () => null,
  }),
}));

const { AuditoriaPage } = await import("./AuditoriaPage");
const { listAuditEvents } = await import("@/api/audit");

function evento(n: number, action: string): AuditEvent {
  return {
    id: `ev-${n}`, action, entity_type: "Probe", entity_id: `probe-${n}`, user_id: `usuario-${n}`,
    request_id: `req-${n}-${action.toLowerCase()}`, source: "QA", reason: null, event_time: "2026-09-30T18:30:00+00:00",
  };
}

function sobre(items: AuditEvent[], total = items.length): PagedResult<AuditEvent> {
  return { items, total, page: 1, page_size: 20 };
}

function montar(): void {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, throwOnError: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuditoriaPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("AuditoriaPage · consumo del sobre paginado", () => {
  it("ENV-01 · las filas de la tabla son exactamente los `items` del sobre", async () => {
    apiFetch.mockClear();
    apiFetch.mockResolvedValue(sobre([evento(1, "LOGIN_SUCCESS"), evento(2, "ROLE_ASSIGNED")], 108));
    montar();
    expect(await screen.findByText("req-1-login_success")).toBeInTheDocument();
    expect(screen.getByText("req-2-role_assigned")).toBeInTheDocument();
    expect(screen.getByText("LOGIN_SUCCESS")).toBeInTheDocument();
    expect(screen.getByText("ROLE_ASSIGNED")).toBeInTheDocument();
    expect(screen.getAllByRole("row")).toHaveLength(3); // cabecera + 2
    expect(apiFetch).toHaveBeenCalledWith("/audit/events?page=1&page_size=10");
  });

  it("ENV-02 · un sobre vacío es el estado vacío, no una tabla muda", async () => {
    apiFetch.mockClear();
    apiFetch.mockResolvedValue(sobre([], 0));
    montar();
    expect(await screen.findByText("Sin eventos")).toBeInTheDocument();
    expect(screen.queryByRole("row")).not.toBeInTheDocument();
  });

  it("ENV-03 · mientras no hay respuesta se muestra el estado de carga", async () => {
    apiFetch.mockClear();
    let responder: (v: PagedResult<AuditEvent>) => void = () => undefined;
    apiFetch.mockReturnValue(new Promise<PagedResult<AuditEvent>>((resolve) => { responder = resolve; }));
    montar();
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.queryByRole("row")).not.toBeInTheDocument();
    expect(screen.queryByText("Sin eventos")).not.toBeInTheDocument();
    // Y al llegar el sobre, la carga da paso a las filas: no se queda en `[]`.
    responder(sobre([evento(9, "LOGIN_SUCCESS")]));
    expect(await screen.findByText("req-9-login_success")).toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("ENV-04 · un error del servidor sigue siendo un error, no una lista vacía", async () => {
    apiFetch.mockClear();
    // Una sola promesa rechazada, ya observada: React Query la recibe igual, y
    // ningún observador secundario (desmontaje al limpiar) la deja sin manejar.
    const fallo = Promise.reject(new Error("boom"));
    fallo.catch(() => undefined);
    apiFetch.mockImplementation(() => fallo);
    montar();
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("No fue posible cargar la auditoría."));
    expect(screen.queryByText("Sin eventos")).not.toBeInTheDocument();
  });

  it("ENV-08 · una respuesta que no es el sobre no se pinta por una puerta de atrás", async () => {
    apiFetch.mockClear();
    // Violación del contrato: un array crudo. No hay soporte dual.
    apiFetch.mockResolvedValue([evento(1, "LOGIN_SUCCESS"), evento(2, "ROLE_ASSIGNED")]);
    montar();
    await waitFor(() => expect(apiFetch).toHaveBeenCalled());
    await waitFor(() => expect(screen.queryByRole("status")).not.toBeInTheDocument());
    expect(screen.queryByText("req-1-login_success")).not.toBeInTheDocument();
    expect(screen.queryByRole("row")).not.toBeInTheDocument();
  });

  it("ENV-07 · el contrato de tipo: la petición devuelve el sobre, nunca un array", () => {
    apiFetch.mockClear();
    expectTypeOf(listAuditEvents).returns.resolves.toEqualTypeOf<PagedResult<AuditEvent>>();
    expectTypeOf(listAuditEvents).returns.resolves.not.toEqualTypeOf<AuditEvent[]>();
  });
});

describe("AuditoriaPage · alcance de la bitácora (GOV-CTL-005)", () => {
  const TEXTO_TENANT = "Eventos de acceso y operaciones de todas las empresas del tenant, incluidos los que no pertenecen a ninguna empresa (como los inicios de sesión).";
  const TEXTO_PARCIAL = "Eventos de las empresas en las que usted tiene autoridad de auditoría. Los eventos sin empresa (como los inicios de sesión) solo los ve quien audita todas las empresas del tenant.";

  it("ALC-01 · quien audita todas las empresas lee que ve todo el tenant, también lo que no tiene empresa", async () => {
    apiFetch.mockClear();
    apiFetch.mockResolvedValue(sobre([]));
    tieneMock.mockImplementation((c, a) => c === "audit:view" && a === "tenant");
    montar();
    expect(await screen.findByText(TEXTO_TENANT)).toBeInTheDocument();
    expect(screen.queryByText(TEXTO_PARCIAL)).not.toBeInTheDocument();
  });

  it("ALC-02 · quien audita solo algunas lee que la lista se limita a sus empresas", async () => {
    apiFetch.mockClear();
    apiFetch.mockResolvedValue(sobre([]));
    tieneMock.mockReturnValue(false);
    montar();
    expect(await screen.findByText(TEXTO_PARCIAL)).toBeInTheDocument();
    expect(screen.queryByText(TEXTO_TENANT)).not.toBeInTheDocument();
  });
});
