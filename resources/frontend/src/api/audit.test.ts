/**
 * CLI · fija la forma de la petición paginada de auditoría: `page` y `page_size`
 * viajan siempre y en ese orden, con los valores por defecto del contrato, y la
 * respuesta se devuelve tal cual la entrega el servidor.
 */
import { describe, expect, expectTypeOf, it, vi } from "vitest";

import type { AuditEvent, PagedResult } from "@/api/types";
import type { ConsultaDeAuditoria } from "./audit";

const apiFetch = vi.fn();
vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));
const { listAuditEvents } = await import("./audit");

describe("listAuditEvents", () => {
  it("CLI-01 · sin argumentos pide `page=1&page_size=20`", async () => {
    apiFetch.mockClear();
    apiFetch.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 });
    await listAuditEvents();
    expect(apiFetch).toHaveBeenCalledTimes(1);
    expect(apiFetch).toHaveBeenCalledWith("/audit/events?page=1&page_size=20");
  });

  it("CLI-02 · página y tamaño pedidos viajan tal cual", async () => {
    apiFetch.mockClear();
    apiFetch.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 });
    await listAuditEvents({ page: 3, page_size: 25 });
    expect(apiFetch).toHaveBeenCalledWith("/audit/events?page=3&page_size=25");
  });

  it("CLI-03 · lo que falta toma el valor por defecto del contrato", async () => {
    apiFetch.mockClear();
    apiFetch.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 });
    await listAuditEvents({ page: 2 });
    expect(apiFetch).toHaveBeenCalledWith("/audit/events?page=2&page_size=20");
    await listAuditEvents({ page_size: 50 });
    expect(apiFetch).toHaveBeenCalledWith("/audit/events?page=1&page_size=50");
  });

  it("CLI-04 · devuelve el sobre que responde el servidor, sin transformarlo", async () => {
    apiFetch.mockClear();
    const sobre = { items: [], total: 0, page: 1, page_size: 20 };
    apiFetch.mockResolvedValue(sobre);
    expect(await listAuditEvents()).toBe(sobre);
  });

  it("CLI-05 · contrato de tipo", () => {
    apiFetch.mockClear();
    expectTypeOf(listAuditEvents).returns.resolves.toEqualTypeOf<PagedResult<AuditEvent>>();
    expectTypeOf(listAuditEvents).parameter(0).toEqualTypeOf<ConsultaDeAuditoria | undefined>();
  });
});
