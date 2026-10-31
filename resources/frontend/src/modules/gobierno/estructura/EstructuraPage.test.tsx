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

const { EstructuraPage } = await import("./EstructuraPage");

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
  {
    id: "u3",
    codigo: "CG1",
    denominacion: "Centro de Gestión 1",
    tipo: "CENTRO_GESTOR",
    unidad_superior_id: "u2",
    nivel: 2,
    estado: "INACTIVA",
    vigente_desde: "2026-01-01",
    vigente_hasta: "2026-12-31",
    version: 1,
  },
];

function ESTRUCTURA(estado: string, faltantes: string[], ejercicio = 2026): unknown {
  return {
    id: "s1",
    ejercicio,
    estado,
    version: 2,
    faltantes_para_publicar: faltantes,
    documento_vinculado: !faltantes.includes("DOCUMENTO_ACTO"),
    publicada_en: estado === "VIGENTE" ? "2026-01-08" : null,
    cerrada_en: estado === "CERRADA" ? "2026-01-05" : null,
    unidades: UNIDADES,
  };
}

function montar(rutaInicial = "/gobierno/estructura/2026"): void {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[rutaInicial]}>
        <Routes>
          <Route path="/gobierno/estructura/:ejercicio" element={<EstructuraPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function responderEstructura(
  estructura: unknown,
  extra?: (ruta: string, opciones?: { method?: string }) => Promise<unknown> | undefined,
): void {
  apiFetch.mockImplementation((ruta: string, opciones?: { method?: string }) => {
    const respuestaExtra = extra?.(ruta, opciones);
    if (respuestaExtra !== undefined) return respuestaExtra;
    if (ruta.startsWith("/gobierno/estructuras/") && (!opciones?.method || opciones.method === "GET")) {
      return Promise.resolve(estructura);
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

describe("EstructuraPage", () => {
  it("GES-01 · borrador con faltantes muestra requisitos y publicación deshabilitada", async () => {
    capacidades = new Set(["gobierno_estructura:edit", "gobierno_estructura:publish"]);
    responderEstructura(ESTRUCTURA("BORRADOR", ["DOCUMENTO_ACTO"]));
    montar();
    expect(await screen.findByText("Borrador")).toBeInTheDocument();
    const requisitos = screen.getByRole("region", { name: "Requisitos para poner en vigor" });
    expect(within(requisitos).getByText("Acto que aprueba la estructura")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Poner en vigor" })).toBeDisabled();
    expect(screen.getByTestId("adjuntos")).toHaveTextContent("GovernmentStructure:s1");
  });

  it("GES-02 · árbol muestra filas en orden y dependencias", async () => {
    capacidades = new Set(["gobierno_estructura:edit"]);
    responderEstructura(ESTRUCTURA("BORRADOR", []));
    montar();
    const filas = await screen.findAllByRole("row");
    const filasDatos = filas.slice(1);
    expect(filasDatos).toHaveLength(3);
    expect(within(filasDatos[0]).getByText("DESP")).toBeInTheDocument();
    expect(within(filasDatos[1]).getByText("DA-01")).toBeInTheDocument();
    expect(within(filasDatos[2]).getByText("CG1")).toBeInTheDocument();
    expect(within(filasDatos[2]).getByText("Nivel 3.")).toBeInTheDocument();
    expect(within(filasDatos[2]).getByText("DA-01")).toBeInTheDocument();
    expect(within(filasDatos[0]).getByText("Ente")).toBeInTheDocument();
  });

  it("GES-03 · borrador muestra acciones de edición e historial", async () => {
    capacidades = new Set(["gobierno_estructura:edit"]);
    responderEstructura(ESTRUCTURA("BORRADOR", []));
    montar();
    expect(await screen.findByRole("button", { name: "Eliminar DESP" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Desactivar DESP" })).toBeNull();
    expect(screen.getByRole("button", { name: "Historial de DESP" })).toBeInTheDocument();
  });

  it("GES-03 · vigente muestra acciones de desactivación e historial", async () => {
    capacidades = new Set(["gobierno_estructura:edit"]);
    responderEstructura(ESTRUCTURA("VIGENTE", []));
    montar();
    expect(await screen.findByRole("button", { name: "Desactivar DESP" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Eliminar DESP" })).toBeNull();
    expect(screen.getByRole("button", { name: "Historial de DESP" })).toBeInTheDocument();
  });

  it("GES-03 · cerrada solo muestra historial", async () => {
    capacidades = new Set(["gobierno_estructura:edit"]);
    responderEstructura(ESTRUCTURA("CERRADA", [], 2025));
    montar("/gobierno/estructura/2025");
    expect(await screen.findByText("Estructura de un ejercicio cerrado: solo lectura.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Editar DESP" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Agregar unidad" })).toBeNull();
    expect(screen.getByRole("button", { name: "Historial de DESP" })).toBeInTheDocument();
  });

  it("GES-04 · sin edit no hay acciones de edición", async () => {
    responderEstructura(ESTRUCTURA("BORRADOR", []));
    montar();
    expect(await screen.findByText("Borrador")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Agregar unidad" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Editar DESP" })).toBeNull();
  });

  it("GES-05 · poner en vigor confirma y publica", async () => {
    capacidades = new Set(["gobierno_estructura:edit", "gobierno_estructura:publish"]);
    responderEstructura(ESTRUCTURA("BORRADOR", []), (ruta, opciones) => {
      if (ruta === "/gobierno/estructuras/2026/publicar" && opciones?.method === "POST") {
        return Promise.resolve(ESTRUCTURA("VIGENTE", []));
      }
      return undefined;
    });
    montar();
    await userEvent.click(await screen.findByRole("button", { name: "Poner en vigor" }));
    expect(await screen.findByText("¿Poner en vigor la estructura de 2026?")).toBeInTheDocument();
    const dialogo = await screen.findByRole("dialog");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Poner en vigor" }));
    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/gobierno/estructuras/2026/publicar",
        expect.objectContaining({ method: "POST", ifMatch: "2" }),
      );
    });
    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith({ type: "success", title: "Estructura en vigor" });
    });
  });

  it("GES-06 · filtro por denominación", async () => {
    capacidades = new Set(["gobierno_estructura:edit"]);
    responderEstructura(ESTRUCTURA("BORRADOR", []));
    montar();
    const buscar = await screen.findByLabelText("Buscar");
    await userEvent.type(buscar, "admin");
    const filas = screen.getAllByRole("row").slice(1);
    expect(filas).toHaveLength(1);
    expect(within(filas[0]).getByText("DA-01")).toBeInTheDocument();
  });

  it("GES-07 · exportar CSV", async () => {
    capacidades = new Set(["gobierno_estructura:view"]);
    responderEstructura(ESTRUCTURA("BORRADOR", []));
    montar();
    await userEvent.click(await screen.findByRole("button", { name: "Exportar CSV" }));
    await waitFor(() => {
      expect(descargarArchivo).toHaveBeenCalledWith("/gobierno/estructuras/2026/exportar", "estructura-2026.csv");
    });
  });

  it("GES-08 · conflicto al cerrar muestra mensaje de versión obsoleta", async () => {
    capacidades = new Set(["gobierno_estructura:edit", "gobierno_estructura:close"]);
    responderEstructura(ESTRUCTURA("VIGENTE", [], 2025), (ruta, opciones) => {
      if (ruta === "/gobierno/estructuras/2025/cerrar" && opciones?.method === "POST") {
        return Promise.reject(new ApiError(409, { code: "GOV_STRUCTURE_STALE", message: "x" }));
      }
      return undefined;
    });
    montar("/gobierno/estructura/2025");
    const cerrar = await screen.findByRole("button", { name: "Cerrar ejercicio" });
    expect(cerrar).toBeEnabled();
    await userEvent.click(cerrar);
    expect(await screen.findByText("¿Cerrar la estructura de 2025?")).toBeInTheDocument();
    const dialogo = await screen.findByRole("dialog");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Cerrar ejercicio" }));
    expect(await screen.findByText(/Otra persona cambió la estructura/)).toBeInTheDocument();
  });

  it("GES-09 · cierre no disponible para el ejercicio en curso", async () => {
    capacidades = new Set(["gobierno_estructura:edit", "gobierno_estructura:close"]);
    responderEstructura(ESTRUCTURA("VIGENTE", []));
    montar();
    expect(await screen.findByRole("button", { name: "Cerrar ejercicio" })).toBeDisabled();
    expect(screen.getByText("El ejercicio 2026 se cierra a partir del 1 de enero de 2027.")).toBeInTheDocument();
  });

  it("GES-10 · la vigencia muestra fechas civiles sin desplazar el día", async () => {
    capacidades = new Set(["gobierno_estructura:edit"]);
    responderEstructura(ESTRUCTURA("BORRADOR", []));
    montar();
    const filas = await screen.findAllByRole("row");
    const filasDatos = filas.slice(1);
    expect(filasDatos).toHaveLength(3);
    expect(within(filasDatos[0]).getByText("01/01/2026 – —")).toBeInTheDocument();
    expect(within(filasDatos[2]).getByText("01/01/2026 – 31/12/2026")).toBeInTheDocument();
  });
});
