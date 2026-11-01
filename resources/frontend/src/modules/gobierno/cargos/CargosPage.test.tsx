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

const { CargosPage } = await import("./CargosPage");

const UNIDADES = [
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
];

const CARGOS = [
  {
    id: "k1",
    codigo: "DIR-ADM",
    denominacion: "Director Administrativo",
    unidad_id: "u2",
    unidad_codigo: "DA-01",
    unidad_denominacion: "Dirección de Administración",
    estado: "VIGENTE",
    vigente_desde: "2026-01-01",
    vigente_hasta: null,
    version: 1,
    competencias: [
      {
        id: "c1",
        accion: "APROBAR",
        materia: "CONTRATACIONES",
        tipo_limite: "MONTO",
        monto: "50000.00",
        moneda: "USD",
        fundamento: null,
      },
    ],
    faltantes_para_activar: [],
    documento_vinculado: true,
    activado_en: "2026-01-01",
    activado_por: "user-1",
    creado_en: "2026-01-01",
  },
  {
    id: "k2",
    codigo: "SUP-SEDE",
    denominacion: "Supervisor de Sede",
    unidad_id: "u1",
    unidad_codigo: "DESP",
    unidad_denominacion: "Despacho del Alcalde",
    estado: "BORRADOR",
    vigente_desde: "2026-01-01",
    vigente_hasta: null,
    version: 1,
    competencias: [],
    faltantes_para_activar: [],
    documento_vinculado: false,
    activado_en: null,
    activado_por: null,
    creado_en: "2026-01-01",
  },
];

function ESTRUCTURA(estado: string): unknown {
  return {
    id: "s1",
    ejercicio: 2026,
    estado,
    version: 2,
    copiada_de: null,
    publicada_en: estado === "VIGENTE" ? "2026-01-08" : null,
    publicada_por: estado === "VIGENTE" ? "user-1" : null,
    cerrada_en: estado === "CERRADA" ? "2026-01-05" : null,
    cerrada_por: estado === "CERRADA" ? "user-1" : null,
    documento_vinculado: true,
    faltantes_para_publicar: [],
    unidades: UNIDADES,
    creado_en: "2026-01-01",
  };
}

function LISTA_CARGOS(estadoEstructura: string, items: unknown[] = CARGOS): unknown {
  return {
    estructura: {
      ejercicio: 2026,
      estado: estadoEstructura,
      version: 2,
    },
    items,
    total: items.length,
  };
}

function montar(rutaInicial = "/gobierno/cargos/2026"): void {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[rutaInicial]}>
        <Routes>
          <Route path="/gobierno/cargos/:ejercicio" element={<CargosPage />} />
          <Route
            path="/gobierno/cargos/:ejercicio/:cargoId"
            element={<p>Detalle de cargo</p>}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function responderCargos(
  estadoEstructura: string,
  items: unknown[] = CARGOS,
): void {
  apiFetch.mockImplementation((ruta: string, opciones?: { method?: string }) => {
    if (ruta === "/gobierno/estructuras/2026" && (!opciones?.method || opciones.method === "GET")) {
      return Promise.resolve(ESTRUCTURA(estadoEstructura));
    }
    if (ruta === "/gobierno/estructuras/2026/cargos" && (!opciones?.method || opciones.method === "GET")) {
      return Promise.resolve(LISTA_CARGOS(estadoEstructura, items));
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

describe("CargosPage", () => {
  it("GCL-01 · la tabla muestra cargos, estados y resumen de competencias", async () => {
    capacidades = new Set(["gobierno_cargos:view"]);
    responderCargos("VIGENTE");
    montar();
    expect(await screen.findByRole("link", { name: "Abrir el cargo DIR-ADM" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Abrir el cargo SUP-SEDE" })).toBeInTheDocument();
    const filaDir = screen.getByRole("row", { name: /DIR-ADM/ });
    const filaSup = screen.getByRole("row", { name: /SUP-SEDE/ });
    expect(within(filaDir).getByText("Vigente")).toBeInTheDocument();
    expect(within(filaSup).getByText("Borrador")).toBeInTheDocument();
    expect(screen.getByText("Aprobar · Contrataciones: Hasta 50.000,00 USD por operación")).toBeInTheDocument();
  });

  it("GCL-02 · filtro Buscar deja solo SUP-SEDE", async () => {
    capacidades = new Set(["gobierno_cargos:view"]);
    responderCargos("VIGENTE");
    montar();
    await screen.findByRole("link", { name: "Abrir el cargo DIR-ADM" });
    const buscar = screen.getByLabelText("Buscar");
    await userEvent.type(buscar, "sup");
    expect(screen.getByRole("link", { name: "Abrir el cargo SUP-SEDE" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Abrir el cargo DIR-ADM" })).toBeNull();
  });

  it("GCL-02 · filtro Estado Vigente deja solo DIR-ADM", async () => {
    capacidades = new Set(["gobierno_cargos:view"]);
    responderCargos("VIGENTE");
    montar();
    await screen.findByRole("link", { name: "Abrir el cargo DIR-ADM" });
    const estado = screen.getByLabelText("Estado");
    await userEvent.selectOptions(estado, "VIGENTE");
    expect(screen.getByRole("link", { name: "Abrir el cargo DIR-ADM" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Abrir el cargo SUP-SEDE" })).toBeNull();
  });

  it("GCL-02 · texto sin coincidencias muestra mensaje de filtro vacío", async () => {
    capacidades = new Set(["gobierno_cargos:view"]);
    responderCargos("VIGENTE");
    montar();
    await screen.findByRole("link", { name: "Abrir el cargo DIR-ADM" });
    const buscar = screen.getByLabelText("Buscar");
    await userEvent.type(buscar, "no-existe");
    expect(await screen.findByText("Ningún cargo coincide con el filtro.")).toBeInTheDocument();
  });

  it("GCL-03 · estructura borrador muestra aviso y enlace a estructura", async () => {
    capacidades = new Set(["gobierno_cargos:view"]);
    responderCargos("BORRADOR");
    montar();
    expect(
      await screen.findByText(/^La estructura de este ejercicio está en borrador/),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ir a la estructura" })).toHaveAttribute(
      "href",
      "/gobierno/estructura/2026",
    );
  });

  it("GCL-04 · estructura cerrada sin edición y con mensaje de solo lectura", async () => {
    capacidades = new Set(["gobierno_cargos:view", "gobierno_cargos:edit"]);
    responderCargos("CERRADA");
    montar();
    expect(await screen.findByText("Ejercicio cerrado: los cargos son de solo lectura.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Agregar cargo" })).toBeNull();
  });

  it("GCL-05 · sin gobierno_cargos:edit no se ve Agregar cargo", async () => {
    capacidades = new Set(["gobierno_cargos:view"]);
    responderCargos("VIGENTE");
    montar();
    await screen.findByRole("link", { name: "Abrir el cargo DIR-ADM" });
    expect(screen.queryByRole("button", { name: "Agregar cargo" })).toBeNull();
  });

  it("GCL-05 · con gobierno_cargos:edit se ve Agregar cargo", async () => {
    capacidades = new Set(["gobierno_cargos:view", "gobierno_cargos:edit"]);
    responderCargos("VIGENTE");
    montar();
    expect(await screen.findByRole("button", { name: "Agregar cargo" })).toBeInTheDocument();
  });

  it("GCL-06 · alta crea cargo, notifica éxito y navega al detalle", async () => {
    capacidades = new Set(["gobierno_cargos:view", "gobierno_cargos:edit"]);
    const creado = {
      id: "k3",
      codigo: "DIR-TES",
      denominacion: "Director de Tesorería",
      unidad_id: "u2",
      estado: "BORRADOR",
      vigente_desde: "2026-01-01",
      vigente_hasta: null,
      competencias: [],
      unidad_codigo: "DA-01",
      unidad_denominacion: "Dirección de Administración",
      version: 1,
      faltantes_para_activar: [],
      documento_vinculado: false,
      activado_en: null,
      activado_por: null,
      creado_en: "2026-01-01",
    };
    apiFetch.mockImplementation((ruta: string, opciones?: { method?: string }) => {
      if (ruta === "/gobierno/estructuras/2026" && (!opciones?.method || opciones.method === "GET")) {
        return Promise.resolve(ESTRUCTURA("VIGENTE"));
      }
      if (ruta === "/gobierno/estructuras/2026/cargos" && opciones?.method === "POST") {
        return Promise.resolve(creado);
      }
      if (ruta === "/gobierno/estructuras/2026/cargos" && (!opciones?.method || opciones.method === "GET")) {
        return Promise.resolve(LISTA_CARGOS("VIGENTE"));
      }
      return Promise.reject(new Error(`ruta inesperada ${ruta}`));
    });
    montar();
    await userEvent.click(await screen.findByRole("button", { name: "Agregar cargo" }));
    const form = await screen.findByRole("form", { name: "Registrar cargo" });
    await userEvent.type(within(form).getByLabelText(/^Código/), "dir-tes");
    await userEvent.type(within(form).getByLabelText(/^Denominación/), "Director de Tesorería");
    await userEvent.selectOptions(within(form).getByLabelText(/^Unidad/), "u2");
    await userEvent.click(within(form).getByRole("button", { name: "Guardar" }));
    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/gobierno/estructuras/2026/cargos",
        expect.objectContaining({
          method: "POST",
          body: {
            codigo: "DIR-TES",
            denominacion: "Director de Tesorería",
            unidad_id: "u2",
            vigente_desde: "2026-01-01",
          },
        }),
      );
    });
    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith({ type: "success", title: "Cargo registrado" });
    });
    expect(await screen.findByText("Detalle de cargo")).toBeInTheDocument();
  });

  it("GCL-07 · alta con 409 GOV_POSITION_CODE_DUPLICATE muestra el error bajo Código", async () => {
    capacidades = new Set(["gobierno_cargos:view", "gobierno_cargos:edit"]);
    apiFetch.mockImplementation((ruta: string, opciones?: { method?: string }) => {
      if (ruta === "/gobierno/estructuras/2026" && (!opciones?.method || opciones.method === "GET")) {
        return Promise.resolve(ESTRUCTURA("VIGENTE"));
      }
      if (ruta === "/gobierno/estructuras/2026/cargos" && opciones?.method === "POST") {
        return Promise.reject(new ApiError(409, { code: "GOV_POSITION_CODE_DUPLICATE", message: "El código ya existe" }));
      }
      if (ruta === "/gobierno/estructuras/2026/cargos" && (!opciones?.method || opciones.method === "GET")) {
        return Promise.resolve(LISTA_CARGOS("VIGENTE"));
      }
      return Promise.reject(new Error(`ruta inesperada ${ruta}`));
    });
    montar();
    await userEvent.click(await screen.findByRole("button", { name: "Agregar cargo" }));
    const form = await screen.findByRole("form", { name: "Registrar cargo" });
    await userEvent.type(within(form).getByLabelText(/^Código/), "DIR-ADM");
    await userEvent.type(within(form).getByLabelText(/^Denominación/), "Otra denominación");
    await userEvent.selectOptions(within(form).getByLabelText(/^Unidad/), "u2");
    await userEvent.click(within(form).getByRole("button", { name: "Guardar" }));
    expect(await within(form).findByText("El código ya existe")).toBeInTheDocument();
  });

  it("GCL-08 · lista vacía muestra mensaje de vacío", async () => {
    capacidades = new Set(["gobierno_cargos:view"]);
    responderCargos("VIGENTE", []);
    montar();
    expect(await screen.findByText("Aún no hay cargos en este ejercicio.")).toBeInTheDocument();
  });

  it("GCL-09 · Exportar CSV llama a descargarArchivo con la ruta y nombre correctos", async () => {
    capacidades = new Set(["gobierno_cargos:view"]);
    responderCargos("VIGENTE");
    montar();
    await userEvent.click(await screen.findByRole("button", { name: "Exportar CSV" }));
    await waitFor(() => {
      expect(descargarArchivo).toHaveBeenCalledWith(
        "/gobierno/estructuras/2026/cargos/exportar",
        "cargos-2026.csv",
      );
    });
  });

  it("GCL-10 · 404 GOV_STRUCTURE_NOT_FOUND muestra no hay estructura", async () => {
    capacidades = new Set(["gobierno_cargos:view"]);
    apiFetch.mockImplementation((ruta: string) => {
      if (ruta === "/gobierno/estructuras/2026") {
        return Promise.reject(new ApiError(404, { code: "GOV_STRUCTURE_NOT_FOUND", message: "x" }));
      }
      if (ruta === "/gobierno/estructuras/2026/cargos") {
        return Promise.reject(new ApiError(404, { code: "GOV_STRUCTURE_NOT_FOUND", message: "x" }));
      }
      return Promise.reject(new Error(`ruta inesperada ${ruta}`));
    });
    montar();
    expect(await screen.findByText("No hay estructura para el ejercicio 2026")).toBeInTheDocument();
  });
});
