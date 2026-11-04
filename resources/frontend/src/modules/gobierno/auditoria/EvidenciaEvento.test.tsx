import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import type { AuditoriaEventoDetalle } from "@/modules/gobierno/api";

const apiFetchMock = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

let capacidades = new Set<string>();

vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({
    estado: "LISTA",
    tiene: (c: string) => capacidades.has(c),
    puede: () => true,
    motivo: () => null,
    motivoDeCapacidad: () => null,
  }),
}));

vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({
    activeCompanyId: "c1",
    activeCompany: { id: "c1", legal_name: "Contenedor 1" },
  }),
}));

const { EvidenciaEvento } = await import("./EvidenciaEvento");

const DETALLE_BASE: AuditoriaEventoDetalle = {
  id: "e1",
  fecha: "2026-02-15T10:30:00Z",
  proceso: "ORG-03",
  proceso_nombre: "Concejo Municipal",
  accion: "UPDATE",
  accion_etiqueta: "Actualización",
  usuario: "ua",
  request_id: "req-1",
  entidad: "GovernmentPosition",
  entidad_id: "p1",
  motivo: null,
  detalle: {
    before: { estado: "BORRADOR" },
    after: { estado: "VIGENTE", codigo: "C-01" },
  },
  documentos: ["d1"],
  objeto: {
    tipo: "GovernmentPosition",
    id: "p1",
    ruta: "/gobierno/cargos/2026/p1",
    capacidad: "gobierno_cargos:view",
  },
};

function renderEvidencia(eventoId = "e1") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/gobierno/auditoria/eventos/${eventoId}`]}>
        <EvidenciaEvento eventoId={eventoId} onCerrar={vi.fn()} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiFetchMock.mockReset();
  apiFetchMock.mockImplementation((url: string) => {
    if (url === "/gobierno/auditoria/eventos/e1") {
      return Promise.resolve(DETALLE_BASE);
    }
    return Promise.reject(
      new ApiError(500, { code: "INTERNAL", message: "Error" }),
    );
  });
  capacidades = new Set(["gobierno_cargos:view"]);
});

describe("EvidenciaEvento", () => {
  it("EVI-01 · muestra detalle, documentos y enlace al objeto con capacidad concedida", async () => {
    const onCerrar = vi.fn();
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/auditoria/eventos/e1") {
        return Promise.resolve(DETALLE_BASE);
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/gobierno/auditoria/eventos/e1"]}>
          <EvidenciaEvento eventoId="e1" onCerrar={onCerrar} />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(
      screen.getByRole("heading", { name: "Evidencia del evento" }),
    ).toBeInTheDocument();
    expect(await screen.findByText("Antes")).toBeInTheDocument();
    expect(screen.getByText("Después")).toBeInTheDocument();
    expect(screen.getByText("BORRADOR")).toBeInTheDocument();
    expect(screen.getByText("VIGENTE")).toBeInTheDocument();
    expect(screen.getByText("C-01")).toBeInTheDocument();
    expect(screen.getByText("Documentos vinculados")).toBeInTheDocument();
    expect(screen.getByText("d1")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ir al objeto" })).toHaveAttribute(
      "href",
      "/gobierno/cargos/2026/p1",
    );
  });

  it("EVI-02 · sin gobierno_cargos:view muestra mensaje de permiso y sin enlace", async () => {
    capacidades = new Set();
    renderEvidencia();

    expect(
      await screen.findByText("No tiene permiso para abrir el objeto."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Ir al objeto" })).not.toBeInTheDocument();
  });

  it("EVI-03 · objeto null y detalle vacío muestra mensajes de indisponibilidad y sin detalle", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/auditoria/eventos/e1") {
        return Promise.resolve({
          id: "e1",
          fecha: "2026-02-15T10:30:00Z",
          proceso: "ORG-03",
          proceso_nombre: "Concejo Municipal",
          accion: "UPDATE",
          accion_etiqueta: "Actualización",
          usuario: "ua",
          request_id: "req-1",
          entidad: "GovernmentPosition",
          entidad_id: "p1",
          motivo: null,
          detalle: {},
          documentos: [],
          objeto: null,
        });
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    renderEvidencia();

    expect(
      await screen.findByText(
        "El objeto ya no está disponible o no tiene pantalla propia.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("El evento no registra detalle.")).toBeInTheDocument();
  });

  it("EVI-04 · 404 GOV_AUDIT_EVENT_NOT_FOUND muestra Evento no encontrado y mantiene el heading", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/auditoria/eventos/e1") {
        return Promise.reject(
          new ApiError(404, {
            code: "GOV_AUDIT_EVENT_NOT_FOUND",
            message: "No existe",
          }),
        );
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    renderEvidencia();

    expect(await screen.findByText("Evento no encontrado")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Evidencia del evento" }),
    ).toBeInTheDocument();
  });

  it("EVI-05 · Cerrar la evidencia llama a onCerrar", async () => {
    const onCerrar = vi.fn();
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/auditoria/eventos/e1") {
        return Promise.resolve(DETALLE_BASE);
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    const usuario = userEvent.setup();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/gobierno/auditoria/eventos/e1"]}>
          <EvidenciaEvento eventoId="e1" onCerrar={onCerrar} />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("BORRADOR")).toBeInTheDocument();
    });

    await usuario.click(
      screen.getByRole("button", { name: "Cerrar la evidencia" }),
    );
    expect(onCerrar).toHaveBeenCalled();
  });

  it("EVI-06 · con documentos:view enlaza el documento citado", async () => {
    capacidades = new Set(["gobierno_cargos:view", "documentos:view"]);

    renderEvidencia();

    await screen.findByText("Documentos vinculados");

    expect(
      screen.getByRole("link", { name: "Abrir el documento d1" }),
    ).toHaveAttribute("href", "/documentos/d1");
  });

  it("EVI-07 · sin documentos:view muestra el documento como texto", async () => {
    renderEvidencia();

    await screen.findByText("Documentos vinculados");

    expect(screen.getByText("d1")).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Abrir el documento d1" }),
    ).toBeNull();
  });
});
