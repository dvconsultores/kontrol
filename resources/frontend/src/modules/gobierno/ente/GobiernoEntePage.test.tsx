import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";

const apiFetch = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
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

const notify = vi.fn();

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify }),
}));

vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({
    activeCompanyId: "c1",
    activeCompany: { id: "c1", legal_name: "Contenedor 1" },
  }),
}));

vi.mock("@/modules/documentos/AdjuntosPanel", () => ({
  AdjuntosPanel: (p: { resourceType: string; resourceId: string }) => (
    <div data-testid="adjuntos">{`${p.resourceType}:${p.resourceId}`}</div>
  ),
}));

const { GobiernoEntePage } = await import("./GobiernoEntePage");

const ENTE_BORRADOR = {
  id: "e1",
  denominacion: "Alcaldía del Municipio Demo",
  siglas: null,
  rif: null,
  nivel_territorial: "MUNICIPAL",
  forma_organizativa: "ADMINISTRACION_CENTRAL",
  organo_adscripcion: null,
  entidad_federal: "Lara",
  municipio: "Iribarren",
  acto_tipo: "ORDENANZA",
  acto_numero: "1",
  acto_fecha: "2020-01-15",
  acto_publicacion: "Gaceta Municipal N.º 1",
  estado: "BORRADOR",
  version: 2,
  faltantes_para_activar: ["DOCUMENTO_ACTO"],
  documento_vinculado: false,
  activado_en: null,
  activado_por: null,
  creado_en: "2026-10-29T12:00:00Z",
  actualizado_en: "2026-10-29T12:00:00Z",
};

const ENTE_COMPLETO = {
  ...ENTE_BORRADOR,
  faltantes_para_activar: [],
  documento_vinculado: true,
};

const ENTE_ACTIVO = {
  ...ENTE_COMPLETO,
  estado: "ACTIVO",
  version: 3,
  activado_en: "2026-10-29T13:00:00Z",
};

const VERSIONES = {
  items: [
    {
      version: 1,
      estado: "BORRADOR",
      motivo: null,
      actor_id: "u1234567890",
      creado_en: "2026-10-29T12:00:00Z",
      datos: {},
    },
  ],
  total: 1,
};

function montar(): void {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <GobiernoEntePage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function responderEnte(
  ente: unknown,
  extra?: (ruta: string, opciones?: { method?: string }) => Promise<unknown> | undefined,
): void {
  apiFetch.mockImplementation((ruta: string, opciones?: { method?: string }) => {
    const respuestaExtra = extra?.(ruta, opciones);
    if (respuestaExtra !== undefined) return respuestaExtra;
    if (ruta === "/gobierno/ente" && (!opciones?.method || opciones.method === "GET")) {
      return Promise.resolve(ente);
    }
    if (ruta === "/gobierno/ente/versiones") {
      return Promise.resolve(VERSIONES);
    }
    return Promise.reject(new Error(`ruta inesperada ${ruta}`));
  });
}

beforeEach(() => {
  apiFetch.mockReset();
  notify.mockReset();
  capacidades = new Set<string>();
});

describe("GobiernoEntePage", () => {
  it("GEP-01 · módulo no habilitado muestra el estado vacío y no ofrece configurar", async () => {
    apiFetch.mockImplementation((ruta: string) => {
      if (ruta === "/gobierno/ente") {
        return Promise.reject(new ApiError(403, { code: "MODULE_NOT_ENTITLED", message: "x" }));
      }
      return Promise.reject(new Error(`ruta inesperada ${ruta}`));
    });
    montar();
    expect(await screen.findByText("El módulo de Gobierno no está habilitado")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Configurar el ente" })).toBeNull();
  });

  it("GEP-02 · sin configurar y con create ofrece el alta", async () => {
    capacidades = new Set(["gobierno_ente:create"]);
    apiFetch.mockImplementation((ruta: string) => {
      if (ruta === "/gobierno/ente") {
        return Promise.reject(new ApiError(404, { code: "GOV_ENTITY_NOT_FOUND", message: "x" }));
      }
      return Promise.reject(new Error(`ruta inesperada ${ruta}`));
    });
    montar();
    expect(await screen.findByText("El ente aún no está configurado")).toBeInTheDocument();
    const boton = screen.getByRole("button", { name: "Configurar el ente" });
    await userEvent.click(boton);
    expect(await screen.findByRole("heading", { name: "Alta del ente" })).toBeInTheDocument();
  });

  it("GEP-03 · sin configurar y sin create no ofrece el botón", async () => {
    apiFetch.mockImplementation((ruta: string) => {
      if (ruta === "/gobierno/ente") {
        return Promise.reject(new ApiError(404, { code: "GOV_ENTITY_NOT_FOUND", message: "x" }));
      }
      return Promise.reject(new Error(`ruta inesperada ${ruta}`));
    });
    montar();
    expect(await screen.findByText("El ente aún no está configurado")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Configurar el ente" })).toBeNull();
  });

  it("GEP-04 · borrador con faltantes muestra requisitos, activación deshabilitada e historial", async () => {
    capacidades = new Set(["gobierno_ente:edit", "gobierno_ente:activate"]);
    responderEnte(ENTE_BORRADOR);
    montar();
    expect(await screen.findByText("Borrador")).toBeInTheDocument();
    const requisitos = screen.getByRole("region", { name: "Requisitos para activar" });
    expect(within(requisitos).getByText("Documento del acto de creación")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Activar el ente" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Editar" })).toBeInTheDocument();
    expect(screen.getByTestId("adjuntos")).toHaveTextContent("GovernmentEntity:e1");
    expect(await screen.findByText("u1234567")).toBeInTheDocument();
    const tabla = screen.getByRole("table");
    expect(within(tabla).getByText("1")).toBeInTheDocument();
  });

  it("GEP-05 · borrador completo permite activar y confirma con diálogo", async () => {
    capacidades = new Set(["gobierno_ente:edit", "gobierno_ente:activate"]);
    responderEnte(ENTE_COMPLETO, (ruta, opciones) => {
      if (ruta === "/gobierno/ente/activar" && opciones?.method === "POST") {
        return Promise.resolve(ENTE_ACTIVO);
      }
      return undefined;
    });
    montar();
    expect(await screen.findByText("El ente está completo y puede activarse.")).toBeInTheDocument();
    const activar = screen.getByRole("button", { name: "Activar el ente" });
    expect(activar).toBeEnabled();
    await userEvent.click(activar);
    expect(await screen.findByText("¿Activar el ente?")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Activar" }));
    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/gobierno/ente/activar",
        expect.objectContaining({ method: "POST", ifMatch: "2" }),
      );
    });
    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith({ type: "success", title: "Ente activado" });
    });
  });

  it("GEP-06 · sin activate ni edit no hay acciones", async () => {
    responderEnte(ENTE_BORRADOR);
    montar();
    expect(await screen.findByText("Borrador")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Activar el ente" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Editar" })).toBeNull();
  });

  it("GEP-07 · activo con edit muestra Modificar y la fecha del acto", async () => {
    capacidades = new Set(["gobierno_ente:edit"]);
    responderEnte(ENTE_ACTIVO);
    montar();
    expect(await screen.findByText("Activo")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Modificar" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Activar el ente" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Editar" })).toBeNull();
    expect(screen.getByText("15/01/2020")).toBeInTheDocument();
  });

  it("GEP-08 · conflicto al activar muestra el mensaje de versión obsoleta", async () => {
    capacidades = new Set(["gobierno_ente:edit", "gobierno_ente:activate"]);
    responderEnte(ENTE_COMPLETO, (ruta, opciones) => {
      if (ruta === "/gobierno/ente/activar" && opciones?.method === "POST") {
        return Promise.reject(new ApiError(409, { code: "GOV_ENTITY_STALE", message: "x" }));
      }
      return undefined;
    });
    montar();
    await userEvent.click(await screen.findByRole("button", { name: "Activar el ente" }));
    await userEvent.click(await screen.findByRole("button", { name: "Activar" }));
    expect(await screen.findByText(/Otra persona cambió el ente mientras lo editaba/)).toBeInTheDocument();
  });

  it("GEP-09 · ente incompleto al activar notifica el requisito faltante", async () => {
    capacidades = new Set(["gobierno_ente:edit", "gobierno_ente:activate"]);
    responderEnte(ENTE_COMPLETO, (ruta, opciones) => {
      if (ruta === "/gobierno/ente/activar" && opciones?.method === "POST") {
        return Promise.reject(
          new ApiError(422, {
            code: "GOV_ENTITY_INCOMPLETE",
            message: "x",
            details: { faltantes: ["DOCUMENTO_ACTO"] },
          }),
        );
      }
      return undefined;
    });
    montar();
    await userEvent.click(await screen.findByRole("button", { name: "Activar el ente" }));
    await userEvent.click(await screen.findByRole("button", { name: "Activar" }));
    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith({
        type: "error",
        title: "No se puede completar",
        description: "Documento del acto de creación",
      });
    });
  });

  it("GEP-10 · modificación con motivo envía PATCH con ifMatch y body", async () => {
    capacidades = new Set(["gobierno_ente:edit"]);
    responderEnte(ENTE_ACTIVO, (ruta, opciones) => {
      if (ruta === "/gobierno/ente" && opciones?.method === "PATCH") {
        return Promise.resolve(ENTE_ACTIVO);
      }
      return undefined;
    });
    montar();
    await userEvent.click(await screen.findByRole("button", { name: "Modificar" }));
    const siglas = await screen.findByLabelText("Siglas");
    await userEvent.clear(siglas);
    await userEvent.type(siglas, "AMD");
    const motivo = screen.getByLabelText(/^Motivo de la modificación/);
    await userEvent.type(motivo, "Corrección de siglas");
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/gobierno/ente",
        expect.objectContaining({
          method: "PATCH",
          ifMatch: "3",
          body: { siglas: "AMD", motivo: "Corrección de siglas" },
        }),
      );
    });
  });
});
