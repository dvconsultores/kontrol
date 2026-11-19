import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import type {
  MatrizAutoridad,
  MatrizDetalleCargo,
  MatrizEjercicios,
  MatrizFila,
  MatrizFiltros,
} from "@/modules/gobierno/api";

const apiFetchMock = vi.fn();
const descargarArchivoMock = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

vi.mock("@/api/descargas", () => ({
  descargarArchivo: (...args: unknown[]) => descargarArchivoMock(...args),
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

vi.mock("@/lib/fecha-de-negocio", async (original) => ({
  ...(await original<typeof import("@/lib/fecha-de-negocio")>()),
  hoyDeNegocio: () => "2026-02-15",
}));

const { MatrizAutoridadPage } = await import("./MatrizAutoridadPage");

const EJERCICIOS: MatrizEjercicios = {
  items: [
    { ejercicio: 2026, estado: "VIGENTE" },
    { ejercicio: 2025, estado: "CERRADA" },
  ],
};

const FILTROS: MatrizFiltros = {
  unidades: [
    {
      id: "u-desp",
      codigo: "DESP",
      denominacion: "Despacho",
      ruta: "DESP",
    },
    {
      id: "u-dir",
      codigo: "DIR-ADM",
      denominacion: "Dirección de Administración",
      ruta: "DESP › DIR-ADM",
    },
  ],
  cargos: [
    {
      id: "dir",
      codigo: "DIR-ADM",
      denominacion: "Director de Administración",
    },
    {
      id: "jef",
      codigo: "JEF-COM",
      denominacion: "Jefe de Compras",
    },
  ],
};

function buildFila(parcial: Partial<MatrizFila> & { id: string }): MatrizFila {
  return {
    cargo_id: "dir",
    cargo_codigo: "DIR-ADM",
    cargo_denominacion: "Director de Administración",
    unidad_id: "u-dir",
    unidad_codigo: "DIR-ADM",
    unidad_denominacion: "Dirección de Administración",
    ruta_unidad: "DESP › DIR-ADM",
    accion: "APROBAR",
    materia: "CONTRATACIONES",
    tipo_limite: "MONTO",
    monto: null,
    moneda: null,
    fundamento: null,
    vigente_desde: "2026-01-01",
    vigente_hasta: null,
    estado_cargo: "VIGENTE",
    acto_soporte: [],
    version: {
      version: 1,
      registrada_en: "2026-01-01",
      motivo: null,
    },
    origen: "CARGO",
    fuente: null,
    ...parcial,
  };
}

const MATRIZ: MatrizAutoridad = {
  fecha: "2026-02-15",
  ejercicio: 2026,
  estructura: { estado: "VIGENTE" },
  total: 4,
  cargos: 3,
  pagina: 1,
  por_pagina: 50,
  items: [
    buildFila({
      id: "f1:APROBAR:CONTRATACIONES",
      origen: "CARGO",
      vigente_desde: "2026-01-05",
      tipo_limite: "SIN_LIMITE",
      monto: null,
      moneda: null,
      fuente: {
        figura: "TITULAR",
        figura_etiqueta: "Titular",
        grupo: "TITULARIDAD",
        asignacion_id: "as1",
        asignacion_codigo: "AS-0001",
        desde: "2026-01-05",
        hasta: null,
        fin_efectivo: null,
        persona: { id: "f1", codigo: "F-001", nombre: "Ana Pérez" },
        persona_reservada: false,
        sustituye_a: null,
        sustituye_reservado: false,
        cargo_origen: null,
        acto: {
          id: "acto1",
          tipo: "RESOLUCION",
          numero: "R-10",
          fecha: "2026-01-03",
          fecha_eficacia: "2026-01-05",
        },
        avocaciones: 0,
      },
    }),
    buildFila({
      id: "as2:APROBAR:CONTRATACIONES",
      origen: "DELEGACION_ATRIBUCIONES",
      tipo_limite: "MONTO",
      monto: "500000.00",
      moneda: "VES",
      fuente: {
        figura: "DELEGACION_ATRIBUCIONES",
        figura_etiqueta: "Delegación de atribuciones",
        grupo: "DELEGACION",
        asignacion_id: "as2",
        asignacion_codigo: "AS-0002",
        desde: "2026-02-01",
        hasta: null,
        fin_efectivo: null,
        persona: { id: "f2", codigo: "F-002", nombre: "Luis Gómez" },
        persona_reservada: false,
        sustituye_a: null,
        sustituye_reservado: false,
        cargo_origen: {
          id: "jef",
          codigo: "JEF-COM",
          denominacion: "Jefe de Compras",
        },
        acto: null,
        avocaciones: 2,
      },
    }),
    buildFila({
      id: "sup:APROBAR:CONTRATACIONES",
      cargo_id: "sup",
      cargo_codigo: "SUP-ADM",
      cargo_denominacion: "Suplente de Administración",
      unidad_codigo: "SUP-ADM",
      unidad_denominacion: "Suplencia de Administración",
      ruta_unidad: "DESP › SUP-ADM",
      origen: "SUPLENCIA",
      fuente: {
        figura: "SUPLENCIA",
        figura_etiqueta: "Suplente",
        grupo: "TEMPORAL",
        asignacion_id: "as3",
        asignacion_codigo: "AS-0003",
        desde: "2026-02-01",
        hasta: "2026-02-20",
        fin_efectivo: null,
        persona: { id: "f3", codigo: "F-003", nombre: "Rosa Díaz" },
        persona_reservada: false,
        sustituye_a: { id: "f4", codigo: "F-004", nombre: "Juan Mora" },
        sustituye_reservado: false,
        cargo_origen: null,
        acto: null,
        avocaciones: 0,
      },
    }),
    buildFila({
      id: "vac:APROBAR:CONTRATACIONES",
      cargo_id: "vac",
      cargo_codigo: "VAC-ADM",
      cargo_denominacion: "Vacante de Administración",
      unidad_codigo: "VAC-ADM",
      unidad_denominacion: "Vacante de Administración",
      ruta_unidad: "DESP › VAC-ADM",
      origen: "CARGO",
      fuente: null,
    }),
  ],
};

const DETALLE_DIR: MatrizDetalleCargo = {
  cargo: {
    id: "dir",
    codigo: "DIR-ADM",
    denominacion: "Director de Administración",
    estado: "VIGENTE",
    unidad_codigo: "DIR-ADM",
    unidad_denominacion: "Dirección de Administración",
    ruta_unidad: "DESP › DIR-ADM",
    vigente_desde: "2026-01-01",
    vigente_hasta: null,
  },
  acto_soporte: [],
  versiones: [
    {
      version: 1,
      estado: "VIGENTE",
      motivo: null,
      creado_en: "2026-01-01",
      competencias: [
        {
          accion: "APROBAR",
          materia: "CONTRATACIONES",
          tipo_limite: "SIN_LIMITE",
          monto: null,
          moneda: null,
          fundamento: null,
        },
      ],
    },
  ],
};

function configurarRespuestasBase() {
  apiFetchMock.mockImplementation((url: string) => {
    if (url === "/gobierno/autoridad/ejercicios") {
      return Promise.resolve(EJERCICIOS);
    }
    if (url === "/gobierno/autoridad/2026/filtros") {
      return Promise.resolve(FILTROS);
    }
    if (url === "/gobierno/autoridad/2026?pagina=1&por_pagina=50") {
      return Promise.resolve(MATRIZ);
    }
    if (url === "/gobierno/autoridad/2026/cargos/dir") {
      return Promise.resolve(DETALLE_DIR);
    }
    return Promise.reject(
      new ApiError(500, { code: "INTERNAL", message: "Error" }),
    );
  });
}

function renderPagina(entrada = "/gobierno/autoridad") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[entrada]}>
        <Routes>
          <Route path="/gobierno/autoridad" element={<MatrizAutoridadPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiFetchMock.mockReset();
  descargarArchivoMock.mockReset();
  notify.mockReset();
  capacidades = new Set(["gobierno_autoridad:view"]);
  configurarRespuestasBase();
});

describe("MatrizAutoridadPage · autoridad efectiva", () => {
  it("EFE-01 · muestra el aviso nuevo y no el de usuarios (ORG-06)", async () => {
    renderPagina();

    expect(
      await screen.findByText(
        /quién ejerce cada competencia a la fecha de corte/,
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText(/llegarán/)).not.toBeInTheDocument();
  });

  it("EFE-02 · columna Ejerce con fuente, sustituto y vigencia", async () => {
    renderPagina();

    expect(
      await screen.findByRole("columnheader", { name: "Ejerce" }),
    ).toBeInTheDocument();

    const filas = screen.getAllByRole("row");
    const anaFila = filas.find(
      (fila) => within(fila).queryByText("Ana Pérez") !== null,
    );
    expect(anaFila).toBeDefined();
    expect(within(anaFila as HTMLElement).getByText("Cargo")).toBeInTheDocument();

    const luisFila = filas.find(
      (fila) => within(fila).queryByText("Luis Gómez") !== null,
    );
    expect(luisFila).toBeDefined();
    expect(
      within(luisFila as HTMLElement).getByText("Delegación de atribuciones"),
    ).toBeInTheDocument();
    expect(
      within(luisFila as HTMLElement).getByText("Desde 01/02/2026"),
    ).toBeInTheDocument();

    const rosaFila = filas.find(
      (fila) => within(fila).queryByText("Rosa Díaz") !== null,
    );
    expect(rosaFila).toBeDefined();
    expect(
      within(rosaFila as HTMLElement).getByText("Suplente"),
    ).toBeInTheDocument();
    expect(
      within(rosaFila as HTMLElement).getByText("Sustituye a Juan Mora"),
    ).toBeInTheDocument();
    expect(
      within(rosaFila as HTMLElement).getByText("01/02/2026 – 20/02/2026"),
    ).toBeInTheDocument();

    const vacanteFila = filas.find(
      (fila) => within(fila).queryByText("Sin ocupante") !== null,
    );
    expect(vacanteFila).toBeDefined();
    expect(
      within(vacanteFila as HTMLElement).getByText("Cargo"),
    ).toBeInTheDocument();
  });

  it("EFE-03 · persona reservada se muestra como Reservado y sustituto reservado", async () => {
    const matrixReservada: MatrizAutoridad = {
      ...MATRIZ,
      items: MATRIZ.items.map((fila) => {
        if (fila.id === "as2:APROBAR:CONTRATACIONES") {
          return {
            ...fila,
            fuente: {
              ...fila.fuente!,
              persona: null,
              persona_reservada: true,
            },
          };
        }
        if (fila.id === "sup:APROBAR:CONTRATACIONES") {
          return {
            ...fila,
            fuente: {
              ...fila.fuente!,
              sustituye_a: null,
              sustituye_reservado: true,
            },
          };
        }
        return fila;
      }),
    };
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/autoridad/2026?pagina=1&por_pagina=50") {
        return Promise.resolve(matrixReservada);
      }
      if (url === "/gobierno/autoridad/ejercicios") {
        return Promise.resolve(EJERCICIOS);
      }
      if (url === "/gobierno/autoridad/2026/filtros") {
        return Promise.resolve(FILTROS);
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    renderPagina();

    expect(await screen.findByText("Reservado")).toBeInTheDocument();
    expect(screen.queryByText("Luis Gómez")).not.toBeInTheDocument();

    const filas = screen.getAllByRole("row");
    const rosaFila = filas.find(
      (fila) => within(fila).queryByText("Rosa Díaz") !== null,
    );
    expect(rosaFila).toBeDefined();
    expect(
      within(rosaFila as HTMLElement).getByText("Sustituye a Reservado"),
    ).toBeInTheDocument();
  });

  it("EFE-04 · el detalle muestra la sección de autoridad efectiva", async () => {
    const user = userEvent.setup();
    renderPagina();

    const botones = await screen.findAllByRole("button", {
      name: "Ver el detalle de DIR-ADM",
    });
    await user.click(botones[0]);

    expect(
      await screen.findByRole("heading", {
        name: "Autoridad efectiva al 15/02/2026",
      }),
    ).toBeInTheDocument();

    const region = screen.getByRole("region", {
      name: "Autoridad efectiva del cargo DIR-ADM",
    });
    const tabla = within(region).getByRole("table");
    const filas = within(tabla).getAllByRole("row").slice(1);
    expect(filas).toHaveLength(2);

    expect(within(tabla).getByText("Resolución R-10")).toBeInTheDocument();
    expect(within(tabla).getByText("Eficaz desde 05/01/2026")).toBeInTheDocument();
    expect(
      within(tabla).getByText("Desde el cargo JEF-COM · Jefe de Compras"),
    ).toBeInTheDocument();
    expect(within(tabla).getByText("AS-0001")).toBeInTheDocument();
    expect(
      within(tabla).getByText("2 avocaciones registradas"),
    ).toBeInTheDocument();
  });

  it("EFE-05 · la fila delegada muestra la etiqueta en la columna Fuente", async () => {
    const user = userEvent.setup();
    renderPagina();

    const botones = await screen.findAllByRole("button", {
      name: "Ver el detalle de DIR-ADM",
    });
    await user.click(botones[0]);

    const region = await screen.findByRole("region", {
      name: "Autoridad efectiva del cargo DIR-ADM",
    });
    const tabla = within(region).getByRole("table");
    const filaDeLuis = within(tabla)
      .getAllByRole("row")
      .slice(1)
      .find((fila) => within(fila).queryByText("Luis Gómez"));

    expect(filaDeLuis).toBeDefined();
    expect(
      within(filaDeLuis as HTMLElement).getByText(
        "Delegación de atribuciones",
      ),
    ).toBeInTheDocument();
  });

  it("EFE-06 · la URL pedida para la matriz sigue sin nuevos parámetros", async () => {
    renderPagina();
    await screen.findByText(/autorizaciones de \d+ cargos al 15\/02\/2026/);

    expect(apiFetchMock).toHaveBeenCalledWith(
      "/gobierno/autoridad/2026?pagina=1&por_pagina=50",
    );
  });

  it("EFE-07 · sin gobierno_autoridad:view no se llama a apiFetch", async () => {
    capacidades = new Set();
    renderPagina();

    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });
});
