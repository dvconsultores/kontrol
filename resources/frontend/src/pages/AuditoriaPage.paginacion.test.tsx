/**
 * PAG · la pantalla de Auditoría pedía solo la primera página al servidor y la tabla
 * volvía a paginar en cliente, de diez en diez, los veinte eventos recibidos: el
 * `total` del sobre no gobernaba nada y no había forma de pedir la página 2.
 *
 * Lo que se fija aquí: cada página y cada tamaño producen su propia petición
 * (`page` base 1, `page_size`); la tabla pinta exactamente los `items` recibidos
 * sin repaginar ni pintar el pie «Mostrando…»; el paginador solo aparece si hay
 * más de una página según el `total` del sobre; y cambiar el tamaño vuelve a la
 * primera página.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, expectTypeOf, it, vi } from "vitest";

import type { ConsultaDeAuditoria } from "@/api/audit";
import type { AuditEvent, PagedResult } from "@/api/types";

const apiFetch = vi.fn();
vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({
    estado: "LISTA",
    puede: () => true,
    tiene: () => true,
    motivo: () => null,
    motivoDeCapacidad: () => null,
  }),
}));

const { AuditoriaPage } = await import("./AuditoriaPage");
const { listAuditEvents } = await import("@/api/audit");

function evento(n: number): AuditEvent {
  return {
    id: `ev-${n}`,
    action: "LOGIN_SUCCESS",
    entity_type: "User",
    entity_id: `u-${n}`,
    user_id: null,
    request_id: `rastro-${String(n).padStart(3, "0")}`,
    source: "API",
    reason: null,
    event_time: "2026-09-30T18:30:00+00:00",
    company_id: null,
    company_name: null,
    scope: "TENANT",
    action_label: "Inicio de sesión",
    username: null,
    details: {},
  };
}

function servidor(cuantos: number): void {
  apiFetch.mockImplementation(async (ruta: string) => {
    if (ruta === "/audit/filters") {
      return { catalog_version: "x", tenant_wide: false, actions: [], companies: [] };
    }
    const url = new URL(ruta, "http://k");
    const page = Number(url.searchParams.get("page") ?? "1");
    const page_size = Number(url.searchParams.get("page_size") ?? "20");
    const items = Array.from({ length: cuantos }, (_, i) => evento(i + 1)).slice((page - 1) * page_size, page * page_size);
    return { items, total: cuantos, page, page_size } satisfies PagedResult<AuditEvent>;
  });
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

function paginadores(): HTMLElement[] {
  return screen.queryAllByRole("navigation", { name: "Paginación" });
}

describe("AuditoriaPage · paginación de servidor", () => {
  it("PAG-01 · el paginador se gobierna con el total del sobre, no con las filas recibidas", async () => {
    apiFetch.mockClear();
    servidor(108);
    montar();
    await screen.findByText("rastro-001");
    expect(screen.getAllByRole("row")).toHaveLength(11);
    expect(paginadores()).toHaveLength(1);
    expect(screen.getByText("Página 1 de 11")).toBeInTheDocument();
    expect(screen.queryByText(/Mostrando/)).not.toBeInTheDocument();
  });

  it("PAG-02 · con 25 por página la tabla pinta las 25 filas recibidas: no vuelve a paginar", async () => {
    apiFetch.mockClear();
    servidor(108);
    montar();
    await screen.findByText("rastro-001");
    await userEvent.selectOptions(screen.getByLabelText("Registros por página"), "25");
    await waitFor(() => {
      const eventos = apiFetch.mock.calls.map(([ruta]) => String(ruta)).filter((ruta) => ruta.startsWith("/audit/events"));
      expect(eventos[eventos.length - 1]).toBe("/audit/events?page=1&page_size=25");
    });
    expect(await screen.findByText("rastro-025")).toBeInTheDocument();
    expect(screen.getAllByRole("row")).toHaveLength(26);
    expect(paginadores()).toHaveLength(1);
    expect(screen.getByText("Página 1 de 5")).toBeInTheDocument();
  });

  it("PAG-03 · «siguiente» pide la página 2 al servidor y pinta sus items", async () => {
    apiFetch.mockClear();
    servidor(108);
    montar();
    await screen.findByText("rastro-001");
    await userEvent.click(screen.getByRole("button", { name: "Página siguiente" }));
    expect(await screen.findByText("rastro-011")).toBeInTheDocument();
    expect(apiFetch).toHaveBeenCalledWith("/audit/events?page=2&page_size=10");
    expect(screen.queryByText("rastro-001")).not.toBeInTheDocument();
    expect(screen.getAllByRole("row")).toHaveLength(11);
    expect(screen.getByText("Página 2 de 11")).toBeInTheDocument();
  });

  it("PAG-04 · la primera página de la interfaz es la página 1 del servidor, y la segunda la 2", async () => {
    apiFetch.mockClear();
    servidor(108);
    montar();
    await screen.findByText("rastro-001");
    const llamadasEventos = (): string[] =>
      apiFetch.mock.calls.map(([ruta]) => String(ruta)).filter((ruta) => ruta.startsWith("/audit/events"));
    expect(llamadasEventos()[0]).toBe("/audit/events?page=1&page_size=10");
    expect(llamadasEventos().every((ruta) => !ruta.includes("page=0"))).toBe(true);
    await userEvent.click(screen.getByRole("button", { name: "Página siguiente" }));
    expect(await screen.findByText("rastro-011")).toBeInTheDocument();
    expect(llamadasEventos()[1]).toBe("/audit/events?page=2&page_size=10");
    expect(llamadasEventos()).toHaveLength(2);
  });

  it("PAG-05 · elegir otro tamaño pide ese page_size", async () => {
    apiFetch.mockClear();
    servidor(108);
    montar();
    await screen.findByText("rastro-001");
    await userEvent.selectOptions(screen.getByLabelText("Registros por página"), "50");
    await waitFor(() => {
      const eventos = apiFetch.mock.calls.map(([ruta]) => String(ruta)).filter((ruta) => ruta.startsWith("/audit/events"));
      expect(eventos[eventos.length - 1]).toBe("/audit/events?page=1&page_size=50");
    });
    expect(await screen.findByText("rastro-050")).toBeInTheDocument();
    expect(screen.getAllByRole("row")).toHaveLength(51);
  });

  it("PAG-06 · cambiar el tamaño vuelve a la primera página", async () => {
    apiFetch.mockClear();
    servidor(108);
    montar();
    await screen.findByText("rastro-001");
    await userEvent.click(screen.getByRole("button", { name: "Página siguiente" }));
    await screen.findByText("rastro-011");
    await userEvent.click(screen.getByRole("button", { name: "Página siguiente" }));
    await screen.findByText("rastro-021");
    await userEvent.selectOptions(screen.getByLabelText("Registros por página"), "25");
    await waitFor(() => {
      const eventos = apiFetch.mock.calls.map(([ruta]) => String(ruta)).filter((ruta) => ruta.startsWith("/audit/events"));
      expect(eventos[eventos.length - 1]).toBe("/audit/events?page=1&page_size=25");
    });
    expect(await screen.findByText("rastro-001")).toBeInTheDocument();
    expect(screen.getByText("Página 1 de 5")).toBeInTheDocument();
  });

  it("PAG-07 · volver a la página anterior pinta otra vez la primera", async () => {
    apiFetch.mockClear();
    servidor(108);
    montar();
    await screen.findByText("rastro-001");
    await userEvent.click(screen.getByRole("button", { name: "Página siguiente" }));
    await screen.findByText("rastro-011");
    await userEvent.click(screen.getByRole("button", { name: "Página anterior" }));
    expect(await screen.findByText("rastro-001")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText("rastro-011")).not.toBeInTheDocument());
    expect(screen.getByText("Página 1 de 11")).toBeInTheDocument();
  });

  it("PAG-10 · la última página pinta el resto y no deja avanzar más", async () => {
    apiFetch.mockClear();
    servidor(23);
    montar();
    await screen.findByText("rastro-001");
    await userEvent.click(screen.getByRole("button", { name: "Página siguiente" }));
    await screen.findByText("rastro-011");
    await userEvent.click(screen.getByRole("button", { name: "Página siguiente" }));
    expect(await screen.findByText("rastro-021")).toBeInTheDocument();
    expect(screen.getAllByRole("row")).toHaveLength(4);
    expect(screen.getByText("Página 3 de 3")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Página siguiente" })).toBeDisabled();
    const eventos = apiFetch.mock.calls.map(([ruta]) => String(ruta)).filter((ruta) => ruta.startsWith("/audit/events"));
    expect(eventos[eventos.length - 1]).toBe("/audit/events?page=3&page_size=10");
  });

  it("PAG-11 · un sobre vacío es el estado vacío, sin paginador", async () => {
    apiFetch.mockClear();
    servidor(0);
    montar();
    expect(await screen.findByText("Sin eventos")).toBeInTheDocument();
    expect(paginadores()).toHaveLength(0);
    expect(screen.queryByRole("row")).not.toBeInTheDocument();
  });

  it("PAG-12 · mientras no hay respuesta hay carga y no hay paginador", async () => {
    apiFetch.mockClear();
    let responder: (v: PagedResult<AuditEvent>) => void = () => undefined;
    apiFetch.mockImplementation((ruta: string) => {
      if (ruta === "/audit/filters") {
        return Promise.resolve({ catalog_version: "x", tenant_wide: false, actions: [], companies: [] });
      }
      return new Promise<PagedResult<AuditEvent>>((resolve) => { responder = resolve; });
    });
    montar();
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(paginadores()).toHaveLength(0);
    responder({ items: [evento(1)], total: 1, page: 1, page_size: 10 });
    expect(await screen.findByText("rastro-001")).toBeInTheDocument();
  });

  it("PAG-13 · un error es un error: ni vacío ni paginador", async () => {
    apiFetch.mockClear();
    const fallo = Promise.reject(new Error("boom"));
    fallo.catch(() => undefined);
    apiFetch.mockImplementation((ruta: string) => {
      if (ruta === "/audit/filters") {
        return Promise.resolve({ catalog_version: "x", tenant_wide: false, actions: [], companies: [] });
      }
      return fallo;
    });
    montar();
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("No fue posible cargar la auditoría."));
    expect(screen.queryByText("Sin eventos")).not.toBeInTheDocument();
    expect(paginadores()).toHaveLength(0);
  });

  it("PAG-14 · contrato de tipo", () => {
    apiFetch.mockClear();
    expectTypeOf(listAuditEvents).returns.resolves.toEqualTypeOf<PagedResult<AuditEvent>>();
    expectTypeOf(listAuditEvents).parameter(0).toEqualTypeOf<ConsultaDeAuditoria | undefined>();
  });

  it("PAG-16 · con diez eventos o menos no hay paginador", async () => {
    apiFetch.mockClear();
    servidor(7);
    montar();
    await screen.findByText("rastro-001");
    expect(screen.getAllByRole("row")).toHaveLength(8);
    expect(paginadores()).toHaveLength(0);
  });

  it("PAG-17 · con exactamente diez no hay paginador", async () => {
    apiFetch.mockClear();
    servidor(10);
    montar();
    await screen.findByText("rastro-010");
    expect(screen.getAllByRole("row")).toHaveLength(11);
    expect(paginadores()).toHaveLength(0);
  });

  it("PAG-18 · con once aparece", async () => {
    apiFetch.mockClear();
    servidor(11);
    montar();
    await screen.findByText("rastro-001");
    expect(screen.getAllByRole("row")).toHaveLength(11);
    expect(paginadores()).toHaveLength(1);
    expect(screen.getByText("Página 1 de 2")).toBeInTheDocument();
  });
});
