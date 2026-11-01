import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
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

const descargarArchivo = vi.fn().mockResolvedValue("x.csv");

vi.mock("@/api/descargas", () => ({
  descargarArchivo: (...args: unknown[]) => descargarArchivo(...args),
}));

vi.mock("@/lib/fecha-de-negocio", async (original) => ({
  ...(await original<typeof import("@/lib/fecha-de-negocio")>()),
  hoyDeNegocio: () => "2026-10-30",
}));

const { CargoPage } = await import("./CargoPage");

const COMPETENCIAS = [
  {
    id: "c1",
    accion: "APROBAR",
    materia: "CONTRATACIONES",
    tipo_limite: "MONTO",
    monto: "50000.00",
    moneda: "USD",
    fundamento: "Reglamento interno, art. 12",
    version: 3,
  },
  {
    id: "c2",
    accion: "FIRMAR",
    materia: "TESORERIA",
    tipo_limite: "SIN_LIMITE",
    monto: null,
    moneda: null,
    fundamento: null,
    version: 3,
  },
];

function CARGO(
  estado: string,
  faltantes: string[],
  documentoVinculado: boolean,
  vigenteHasta?: string | null,
): unknown {
  return {
    id: "k1",
    codigo: "DIR-ADM",
    denominacion: "Director de Administración",
    unidad_id: "u2",
    unidad_codigo: "DA-01",
    unidad_denominacion: "Dirección de Administración",
    estado,
    version: 3,
    vigente_desde: "2026-01-01",
    vigente_hasta: vigenteHasta === undefined ? null : vigenteHasta,
    activado_en: estado === "VIGENTE" ? "2026-01-15T10:00:00Z" : null,
    faltantes_para_activar: faltantes,
    documento_vinculado: documentoVinculado,
    competencias: COMPETENCIAS,
  };
}

const ESTRUCTURA = (estado: string): unknown => ({
  id: "s1",
  ejercicio: 2026,
  estado,
  version: 2,
  faltantes_para_publicar: [],
  documento_vinculado: true,
  publicada_en: estado === "VIGENTE" ? "2026-01-08" : null,
  cerrada_en: estado === "CERRADA" ? "2026-01-05" : null,
  unidades: [
    {
      id: "u1",
      codigo: "DESP",
      denominacion: "Despacho del Alcalde",
      tipo: "ORGANO",
      unidad_superior_id: null,
      nivel: 0,
      estado: "ACTIVA",
      vigente_desde: "2026-01-01",
      vigente_hasta: null,
      version: 1,
    },
    {
      id: "u2",
      codigo: "DA-01",
      denominacion: "Dirección de Administración",
      tipo: "UNIDAD_ADMINISTRATIVA",
      unidad_superior_id: "u1",
      nivel: 1,
      estado: "ACTIVA",
      vigente_desde: "2026-01-01",
      vigente_hasta: null,
      version: 1,
    },
  ],
});

const VERSIONES = {
  items: [
    {
      version: 1,
      estado: "BORRADOR",
      creado_en: "2026-01-02T10:00:00Z",
      motivo: "Creación inicial",
      datos: { competencias: [] },
    },
    {
      version: 2,
      estado: "BORRADOR",
      creado_en: "2026-01-03T10:00:00Z",
      motivo: "Ajuste de unidad",
      datos: { competencias: COMPETENCIAS },
    },
    {
      version: 3,
      estado: "BORRADOR",
      creado_en: "2026-01-04T10:00:00Z",
      motivo: "Reorganización aprobada",
      datos: { competencias: COMPETENCIAS },
    },
  ],
};

function montar(rutaInicial = "/gobierno/cargos/2026/k1"): void {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[rutaInicial]}>
        <Routes>
          <Route path="/gobierno/cargos/:ejercicio/:cargoId" element={<CargoPage />} />
          <Route path="/gobierno/cargos/:ejercicio" element={<p>Lista de cargos</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function responder(
  cargo: unknown,
  estructura: unknown,
  versiones: unknown,
  extra?: (ruta: string, opciones?: { method?: string }) => Promise<unknown> | undefined,
): void {
  apiFetch.mockImplementation((ruta: string, opciones?: { method?: string }) => {
    const respuestaExtra = extra?.(ruta, opciones);
    if (respuestaExtra !== undefined) return respuestaExtra;
    if (ruta === "/gobierno/estructuras/2026" && (!opciones?.method || opciones.method === "GET")) {
      return Promise.resolve(estructura);
    }
    if (ruta === "/gobierno/estructuras/2026/cargos/k1" && (!opciones?.method || opciones.method === "GET")) {
      return Promise.resolve(cargo);
    }
    if (ruta === "/gobierno/estructuras/2026/cargos/k1/versiones" && (!opciones?.method || opciones.method === "GET")) {
      return Promise.resolve(versiones);
    }
    return Promise.reject(new Error(`ruta inesperada ${ruta}`));
  });
}

beforeEach(() => {
  apiFetch.mockReset();
  notify.mockReset();
  descargarArchivo.mockReset();
  descargarArchivo.mockResolvedValue("x.csv");
  capacidades = new Set<string>();
});

describe("CargoPage", () => {
  it("GCP-01 · borrador con faltantes muestra requisitos y publicación deshabilitada", async () => {
    capacidades = new Set(["gobierno_cargos:edit", "gobierno_cargos:publish", "gobierno_cargos:view"]);
    responder(CARGO("BORRADOR", ["DOCUMENTO_ACTO"], false), ESTRUCTURA("VIGENTE"), VERSIONES);
    montar();
    expect(await screen.findByRole("heading", { name: "DIR-ADM — Director de Administración" })).toBeInTheDocument();
    const requisitos = screen.getByRole("region", { name: "Requisitos para poner en vigor" });
    expect(within(requisitos).getByText("Acto del cargo")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Poner en vigor" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Eliminar" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Desactivar" })).toBeNull();
  });

  it("GCP-02 · borrador sin faltantes activa el cargo y notifica", async () => {
    capacidades = new Set(["gobierno_cargos:edit", "gobierno_cargos:publish", "gobierno_cargos:view"]);
    responder(
      CARGO("BORRADOR", [], true),
      ESTRUCTURA("VIGENTE"),
      VERSIONES,
      (ruta, opciones) => {
        if (ruta === "/gobierno/estructuras/2026/cargos/k1/activar" && opciones?.method === "POST") {
          return Promise.resolve(CARGO("VIGENTE", [], true));
        }
        return undefined;
      },
    );
    montar();
    await userEvent.click(await screen.findByRole("button", { name: "Poner en vigor" }));
    expect(await screen.findByText("Poner en vigor el cargo DIR-ADM")).toBeInTheDocument();
    const dialogo = await screen.findByRole("dialog");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Poner en vigor" }));
    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/gobierno/estructuras/2026/cargos/k1/activar",
        expect.objectContaining({ method: "POST", ifMatch: "3" }),
      );
    });
    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith({ type: "success", title: "Cargo en vigor" });
    });
  });

  it("GCP-03 · vigente con edit y publish muestra acciones de escritura y oculta las de borrador", async () => {
    capacidades = new Set(["gobierno_cargos:edit", "gobierno_cargos:publish", "gobierno_cargos:view"]);
    responder(CARGO("VIGENTE", [], true), ESTRUCTURA("VIGENTE"), VERSIONES);
    montar();
    expect(await screen.findByRole("button", { name: "Agregar competencia" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Cambiar el límite de Aprobar · Contrataciones" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retirar Aprobar · Contrataciones" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Desactivar" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Poner en vigor" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Eliminar" })).toBeNull();
  });

  it("GCP-04 · vigente con edit sin publish muestra nota y oculta acciones de competencias", async () => {
    capacidades = new Set(["gobierno_cargos:edit", "gobierno_cargos:view"]);
    responder(CARGO("VIGENTE", [], true), ESTRUCTURA("VIGENTE"), VERSIONES);
    montar();
    expect(await screen.findByRole("heading", { name: "DIR-ADM — Director de Administración" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Agregar competencia" })).toBeNull();
    expect(
      screen.queryByRole("button", { name: "Cambiar el límite de Aprobar · Contrataciones" }),
    ).toBeNull();
    expect(
      screen.queryByRole("button", { name: "Retirar Aprobar · Contrataciones" }),
    ).toBeNull();
    expect(
      screen.getByText("Solo quien puede poner cargos en vigor cambia sus competencias."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Editar" })).toBeInTheDocument();
  });

  it("GCP-05 · solo view no muestra acciones de escritura", async () => {
    capacidades = new Set(["gobierno_cargos:view"]);
    responder(CARGO("BORRADOR", ["DOCUMENTO_ACTO"], false), ESTRUCTURA("VIGENTE"), VERSIONES);
    montar();
    expect(await screen.findByRole("heading", { name: "DIR-ADM — Director de Administración" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Editar" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Agregar competencia" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Eliminar" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Poner en vigor" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Desactivar" })).toBeNull();
  });

  it("GCP-06 · estructura cerrada muestra aviso de solo lectura y ninguna acción de escritura", async () => {
    capacidades = new Set(["gobierno_cargos:edit", "gobierno_cargos:publish", "gobierno_cargos:view"]);
    responder(CARGO("BORRADOR", [], true), ESTRUCTURA("CERRADA"), VERSIONES);
    montar();
    expect(
      await screen.findByText("Ejercicio cerrado: el cargo es de solo lectura."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Editar" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Agregar competencia" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Eliminar" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Poner en vigor" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Desactivar" })).toBeNull();
  });

  it("GCP-07 · inactivo muestra aviso con fecha civil sin desplazar el día", async () => {
    capacidades = new Set(["gobierno_cargos:view"]);
    responder(CARGO("INACTIVO", [], true, "2026-12-31"), ESTRUCTURA("VIGENTE"), VERSIONES);
    montar();
    expect(
      await screen.findByText(/su vigencia terminó el 31\/12\/2026/),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Editar" })).toBeNull();
  });

  it("GCP-08 · límites en lenguaje de negocio", async () => {
    capacidades = new Set(["gobierno_cargos:view"]);
    responder(CARGO("VIGENTE", [], true), ESTRUCTURA("VIGENTE"), VERSIONES);
    montar();
    expect(await screen.findByText("Hasta 50.000,00 USD por operación")).toBeInTheDocument();
    expect(screen.getByText("Sin límite")).toBeInTheDocument();
  });

  it("GCP-09 · cambiar límite en vigente envía PATCH con body exacto", async () => {
    capacidades = new Set(["gobierno_cargos:edit", "gobierno_cargos:publish", "gobierno_cargos:view"]);
    responder(
      CARGO("VIGENTE", [], true),
      ESTRUCTURA("VIGENTE"),
      VERSIONES,
      (ruta, opciones) => {
        if (
          ruta === "/gobierno/estructuras/2026/cargos/k1/competencias/c1" &&
          opciones?.method === "PATCH"
        ) {
          return Promise.resolve(COMPETENCIAS[0]);
        }
        return undefined;
      },
    );
    montar();
    await userEvent.click(
      await screen.findByRole("button", { name: "Cambiar el límite de Aprobar · Contrataciones" }),
    );
    expect(await screen.findByText(/Monto máximo por operación/)).toBeInTheDocument();
    const monto = screen.getByLabelText(/^Monto máximo por operación/);
    await userEvent.clear(monto);
    await userEvent.type(monto, "75000");
    const motivo = screen.getByLabelText(/^Motivo/);
    await userEvent.type(motivo, "Ajuste del límite aprobado");
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/gobierno/estructuras/2026/cargos/k1/competencias/c1",
        expect.objectContaining({
          method: "PATCH",
          ifMatch: "3",
          body: {
            tipo_limite: "MONTO",
            monto: "75000.00",
            moneda: "USD",
            fundamento: "Reglamento interno, art. 12",
            motivo: "Ajuste del límite aprobado",
          },
        }),
      );
    });
  });

  it("GCP-10 · cargo inexistente muestra mensaje de error", async () => {
    capacidades = new Set(["gobierno_cargos:view"]);
    apiFetch.mockImplementation((ruta: string, opciones?: { method?: string }) => {
      if (ruta === "/gobierno/estructuras/2026" && (!opciones?.method || opciones.method === "GET")) {
        return Promise.resolve(ESTRUCTURA("VIGENTE"));
      }
      if (ruta === "/gobierno/estructuras/2026/cargos/k1" && (!opciones?.method || opciones.method === "GET")) {
        return Promise.reject(new ApiError(404, { code: "GOV_POSITION_NOT_FOUND", message: "x" }));
      }
      if (ruta === "/gobierno/estructuras/2026/cargos/k1/versiones" && (!opciones?.method || opciones.method === "GET")) {
        return Promise.resolve(VERSIONES);
      }
      return Promise.reject(new Error(`ruta inesperada ${ruta}`));
    });
    montar();
    expect(await screen.findByText("El cargo no existe en este ejercicio")).toBeInTheDocument();
  });

  it("GCP-11 · historial en orden descendente", async () => {
    capacidades = new Set(["gobierno_cargos:view"]);
    responder(CARGO("VIGENTE", [], true), ESTRUCTURA("VIGENTE"), VERSIONES);
    montar();
    expect(await screen.findByRole("heading", { name: "Historial" })).toBeInTheDocument();
    const tablaHistorial = screen.getAllByRole("table")[1];
    const filas = within(tablaHistorial).getAllByRole("row").slice(1);
    expect(within(filas[0]).getByText("3")).toBeInTheDocument();
    expect(within(filas[0]).getByText("Reorganización aprobada")).toBeInTheDocument();
  });

  it("GCP-12 · eliminar en borrador navega a la lista", async () => {
    capacidades = new Set(["gobierno_cargos:edit", "gobierno_cargos:view"]);
    responder(
      CARGO("BORRADOR", ["DOCUMENTO_ACTO"], false),
      ESTRUCTURA("VIGENTE"),
      VERSIONES,
      (ruta, opciones) => {
        if (ruta === "/gobierno/estructuras/2026/cargos/k1" && opciones?.method === "DELETE") {
          return Promise.resolve(undefined);
        }
        return undefined;
      },
    );
    montar();
    await userEvent.click(await screen.findByRole("button", { name: "Eliminar" }));
    expect(await screen.findByText("Eliminar el cargo DIR-ADM")).toBeInTheDocument();
    const dialogo = await screen.findByRole("dialog");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Eliminar" }));
    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/gobierno/estructuras/2026/cargos/k1",
        expect.objectContaining({ method: "DELETE", ifMatch: "3" }),
      );
    });
    expect(await screen.findByText("Lista de cargos")).toBeInTheDocument();
  });

  it("GCP-13 · conflicto al activar muestra el estado de conflicto", async () => {
    capacidades = new Set(["gobierno_cargos:edit", "gobierno_cargos:publish", "gobierno_cargos:view"]);
    responder(
      CARGO("BORRADOR", [], true),
      ESTRUCTURA("VIGENTE"),
      VERSIONES,
      (ruta, opciones) => {
        if (ruta === "/gobierno/estructuras/2026/cargos/k1/activar" && opciones?.method === "POST") {
          return Promise.reject(new ApiError(409, { code: "GOV_POSITION_STALE", message: "x" }));
        }
        return undefined;
      },
    );
    montar();
    await userEvent.click(await screen.findByRole("button", { name: "Poner en vigor" }));
    expect(await screen.findByText("Poner en vigor el cargo DIR-ADM")).toBeInTheDocument();
    const dialogo = await screen.findByRole("dialog");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Poner en vigor" }));
    expect(
      await screen.findByText("Otra persona cambió el cargo mientras trabajaba. Se cargó la versión vigente."),
    ).toBeInTheDocument();
  });
});
