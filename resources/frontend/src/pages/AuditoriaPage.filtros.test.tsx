/**
 * Auditoría — filtros reales y detalle de eventos (C04-T10 · UI-BUSQUEDA-MUERTA).
 *
 * Fija el contrato de la pantalla `/auditoria` sin la búsqueda muerta `q`:
 * filtros reales, columnas legibles, detalle accesible y estados completos.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { AuditEvent, AuditFilters, PagedResult } from "@/api/types";

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

function evento(parcial: Partial<AuditEvent> = {}): AuditEvent {
  return {
    id: "ev-1",
    action: "LOGIN_SUCCESS",
    action_label: "Inicio de sesión",
    entity_type: "AuthSession",
    entity_id: "session-1",
    user_id: "usuario-1",
    username: "maria",
    request_id: "req-1",
    source: "QA",
    reason: null,
    event_time: "2026-09-30T18:30:00+00:00",
    company_id: null,
    company_name: null,
    scope: "UNCATALOGUED",
    details: {},
    ...parcial,
  };
}

function sobre(items: AuditEvent[], total = items.length): PagedResult<AuditEvent> {
  return { items, total, page: 1, page_size: 10 };
}

function filtrosSinteticos(tenantWide = false): AuditFilters {
  return {
    catalog_version: "cat-1",
    tenant_wide: tenantWide,
    actions: [
      { code: "LOGIN_SUCCESS", entity_type: "AuthSession", label: "Inicio de sesión", scope: "TENANT", lifecycle: "active" },
      { code: "DOCUMENT_SIGNED", entity_type: "Document", label: "Firma de documento", scope: "COMPANY", lifecycle: "active" },
    ],
    companies: [
      { id: "c-1", code: "EMPRESA_A", name: "Empresa Alfa" },
      { id: "c-2", code: "EMPRESA_B", name: "Empresa Beta" },
    ],
  };
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

function peticionesDe(ruta: string): string[] {
  return apiFetch.mock.calls
    .map((llamada) => String(llamada[0]))
    .filter((url) => url.includes(ruta));
}

function ultimaPeticionDe(ruta: string): string | undefined {
  return peticionesDe(ruta).at(-1);
}

function selectPorEtiqueta(etiqueta: string): HTMLSelectElement {
  return screen.getByLabelText(etiqueta) as HTMLSelectElement;
}

describe("AuditoriaPage · filtros reales y detalle", () => {
  beforeEach(() => {
    apiFetch.mockReset();
    apiFetch.mockImplementation(async (ruta: string) => {
      if (ruta === "/audit/filters") return filtrosSinteticos(false);
      if (typeof ruta === "string" && ruta.startsWith("/audit/events")) return sobre([]);
      throw new Error(`Ruta no simulada: ${String(ruta)}`);
    });
    tieneMock.mockReturnValue(false);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("FIL-01 aplicar Desde y Hasta envía esas fechas y page=1", async () => {
    const usuario = userEvent.setup();
    montar();
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/audit/filters"));

    await usuario.type(screen.getByLabelText("Desde"), "2026-03-01");
    await usuario.type(screen.getByLabelText("Hasta"), "2026-03-10");
    await usuario.click(screen.getByRole("button", { name: "Aplicar filtros" }));

    await waitFor(() => {
      expect(ultimaPeticionDe("/audit/events")).toContain("desde=2026-03-01");
    });
    const ultima = ultimaPeticionDe("/audit/events") ?? "";
    expect(ultima).toContain("hasta=2026-03-10");
    expect(ultima).toContain("page=1");
  });

  it("FIL-02 Desde posterior a Hasta muestra el error y no pide eventos", async () => {
    const usuario = userEvent.setup();
    montar();
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/audit/filters"));
    const peticionesAntes = peticionesDe("/audit/events").length;

    await usuario.type(screen.getByLabelText("Desde"), "2026-03-11");
    await usuario.type(screen.getByLabelText("Hasta"), "2026-03-10");
    await usuario.click(screen.getByRole("button", { name: "Aplicar filtros" }));

    expect(screen.getByText("“Desde” no puede ser posterior a “Hasta”.")).toBeInTheDocument();
    expect(peticionesDe("/audit/events").length).toBe(peticionesAntes);
  });

  it("FIL-03 elegir una acción envía action y entity_type", async () => {
    const usuario = userEvent.setup();
    montar();
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/audit/filters"));
    await screen.findByRole("option", { name: /Firma de documento/ });

    await usuario.selectOptions(
      selectPorEtiqueta("Acción"),
      "DOCUMENT_SIGNED|Document",
    );
    await usuario.click(screen.getByRole("button", { name: "Aplicar filtros" }));

    await waitFor(() => {
      const ultima = ultimaPeticionDe("/audit/events") ?? "";
      expect(ultima).toContain("action=DOCUMENT_SIGNED");
      expect(ultima).toContain("entity_type=Document");
    });
  });

  it("FIL-04a con tenant_wide=false no existe la opción tenant", async () => {
    montar();
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/audit/filters"));

    expect(screen.queryByRole("option", { name: "Solo eventos del tenant" })).not.toBeInTheDocument();
  });

  it("FIL-04b con tenant_wide=true existe la opción tenant y envía scope; elegir empresa envía company_id", async () => {
    apiFetch.mockImplementation(async (ruta: string) => {
      if (ruta === "/audit/filters") return filtrosSinteticos(true);
      if (typeof ruta === "string" && ruta.startsWith("/audit/events")) return sobre([]);
      throw new Error(`Ruta no simulada: ${String(ruta)}`);
    });
    const usuario = userEvent.setup();
    montar();
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/audit/filters"));

    expect(await screen.findByRole("option", { name: "Solo eventos del tenant" })).toBeInTheDocument();

    await usuario.selectOptions(selectPorEtiqueta("Ámbito"), "TENANT");
    await usuario.click(screen.getByRole("button", { name: "Aplicar filtros" }));

    await waitFor(() => {
      expect(ultimaPeticionDe("/audit/events")).toContain("scope=TENANT");
    });

    await usuario.selectOptions(selectPorEtiqueta("Ámbito"), "company:c-1");
    await usuario.click(screen.getByRole("button", { name: "Aplicar filtros" }));

    await waitFor(() => {
      expect(ultimaPeticionDe("/audit/events")).toContain("company_id=c-1");
    });
  });

  it("FIL-05 ninguna petición lleva el parámetro q", async () => {
    const usuario = userEvent.setup();
    montar();
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/audit/filters"));

    await usuario.type(screen.getByLabelText("Usuario"), "maria");
    await usuario.click(screen.getByRole("button", { name: "Aplicar filtros" }));

    await waitFor(() => expect(ultimaPeticionDe("/audit/events")).toContain("username=maria"));
    for (const peticion of peticionesDe("/audit/events")) {
      expect(peticion).not.toContain("q=");
    }
  });

  it("FIL-06 Limpiar vuelve a pedir sin filtros", async () => {
    const usuario = userEvent.setup();
    montar();
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/audit/filters"));

    await usuario.type(screen.getByLabelText("Desde"), "2026-03-01");
    await usuario.click(screen.getByRole("button", { name: "Aplicar filtros" }));
    await waitFor(() => expect(ultimaPeticionDe("/audit/events")).toContain("desde=2026-03-01"));

    await usuario.click(screen.getByRole("button", { name: "Limpiar" }));

    await waitFor(() => {
      const ultima = ultimaPeticionDe("/audit/events") ?? "";
      expect(ultima).not.toContain("desde=");
      expect(ultima).toContain("page=1");
    });
  });

  it("FIL-07 la columna Ámbito muestra Tenant, empresa y evento histórico sin empresa", async () => {
    apiFetch.mockImplementation(async (ruta: string) => {
      if (ruta === "/audit/filters") return filtrosSinteticos();
      if (typeof ruta === "string" && ruta.startsWith("/audit/events")) {
        return sobre([
          evento({ id: "ev-1", scope: "TENANT", company_id: null, company_name: null }),
          evento({ id: "ev-2", scope: "COMPANY", company_id: "c-1", company_name: "Empresa Alfa" }),
          evento({ id: "ev-3", scope: "COMPANY", company_id: null, company_name: null }),
        ]);
      }
      throw new Error(`Ruta no simulada: ${String(ruta)}`);
    });
    montar();

    expect(await screen.findByText("Tenant")).toBeInTheDocument();
    expect(screen.getByText("Empresa Alfa")).toBeInTheDocument();
    expect(screen.getByText("Empresa no registrada (evento histórico)")).toBeInTheDocument();
  });

  it("FIL-08 Ver detalle expande la región con el detalle after y Cerrar detalle la quita", async () => {
    apiFetch.mockImplementation(async (ruta: string) => {
      if (ruta === "/audit/filters") return filtrosSinteticos();
      if (typeof ruta === "string" && ruta.startsWith("/audit/events")) {
        return sobre([
          evento({
            id: "ev-1",
            details: { after: { estado: "firmado" } },
          }),
        ]);
      }
      throw new Error(`Ruta no simulada: ${String(ruta)}`);
    });
    const usuario = userEvent.setup();
    montar();

    const boton = await screen.findByRole("button", { name: "Ver detalle" });
    expect(boton).toHaveAttribute("aria-expanded", "false");

    await usuario.click(boton);

    const botonAbierto = screen.getByRole("button", { name: "Ver detalle" });
    expect(botonAbierto).toHaveAttribute("aria-expanded", "true");
    const detalle = screen.getByRole("region", { name: /Detalle del evento/i });
    expect(detalle).toBeInTheDocument();
    expect(within(detalle).getByText("Después")).toBeInTheDocument();
    expect(within(detalle).getByText("estado")).toBeInTheDocument();
    expect(within(detalle).getByText("firmado")).toBeInTheDocument();

    await usuario.click(screen.getByRole("button", { name: "Cerrar detalle" }));

    expect(screen.queryByRole("region", { name: /Detalle del evento/i })).not.toBeInTheDocument();
  });

  it("FIL-09 un error 403 muestra el mensaje de autoridad con Reintentar", async () => {
    apiFetch.mockImplementation(async (ruta: string) => {
      if (ruta === "/audit/filters") return filtrosSinteticos();
      if (typeof ruta === "string" && ruta.startsWith("/audit/events")) {
        throw { status: 403 };
      }
      throw new Error(`Ruta no simulada: ${String(ruta)}`);
    });
    montar();

    expect(await screen.findByText("No tiene autoridad de auditoría para consultar estos eventos.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reintentar" })).toBeInTheDocument();
  });

  it("FIL-10 estando en la página 2, aplicar un filtro vuelve a pedir page=1", async () => {
    apiFetch.mockImplementation(async (ruta: string) => {
      if (ruta === "/audit/filters") return filtrosSinteticos();
      if (typeof ruta === "string" && ruta.startsWith("/audit/events")) {
        return sobre([], 25);
      }
      throw new Error(`Ruta no simulada: ${String(ruta)}`);
    });
    const usuario = userEvent.setup();
    montar();

    const botonSiguiente = await screen.findByRole("button", { name: /Página siguiente/i });
    await usuario.click(botonSiguiente);
    await waitFor(() => expect(ultimaPeticionDe("/audit/events")).toContain("page=2"));

    await usuario.type(screen.getByLabelText("Usuario"), "maria");
    await usuario.click(screen.getByRole("button", { name: "Aplicar filtros" }));

    await waitFor(() => {
      const ultima = ultimaPeticionDe("/audit/events") ?? "";
      expect(ultima).toContain("page=1");
      expect(ultima).toContain("username=maria");
    });
  });
});
