import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
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
      id: "sup",
      codigo: "SUP",
      denominacion: "Supervisor de Bienes",
    },
  ],
};

const ROW_SUP: MatrizFila = {
  id: "sup:CUSTODIAR:BIENES",
  cargo_id: "sup",
  cargo_codigo: "SUP",
  cargo_denominacion: "Supervisor de Bienes",
  estado_cargo: "INACTIVO",
  unidad_id: "u-desp",
  unidad_codigo: "DESP",
  unidad_denominacion: "Despacho",
  ruta_unidad: "DESP",
  accion: "CUSTODIAR",
  materia: "BIENES",
  tipo_limite: "SIN_LIMITE",
  monto: null,
  moneda: null,
  fundamento: null,
  vigente_desde: "2026-01-01",
  vigente_hasta: "2026-03-31",
  acto_soporte: [],
  version: {
    version: 1,
    registrada_en: "2026-01-05T16:00:00Z",
    motivo: null,
  },
  origen: "CARGO",
};

const ROW_DIR_APROBAR: MatrizFila = {
  id: "dir:APROBAR:CONTRATACIONES",
  cargo_id: "dir",
  cargo_codigo: "DIR-ADM",
  cargo_denominacion: "Director de Administración",
  estado_cargo: "VIGENTE",
  unidad_id: "u-dir",
  unidad_codigo: "DIR-ADM",
  unidad_denominacion: "Dirección de Administración",
  ruta_unidad: "DESP › DIR-ADM",
  accion: "APROBAR",
  materia: "CONTRATACIONES",
  tipo_limite: "MONTO",
  monto: "1500000.00",
  moneda: "VES",
  fundamento: "Reglamento interno, art. 12",
  vigente_desde: "2026-01-01",
  vigente_hasta: null,
  acto_soporte: ["Resolución DA-001"],
  version: {
    version: 3,
    registrada_en: "2026-01-20T16:00:00Z",
    motivo: "Amplía el límite",
  },
  origen: "CARGO",
};

const ROW_DIR_FIRMAR: MatrizFila = {
  ...ROW_DIR_APROBAR,
  id: "dir:FIRMAR:EXPEDIENTE",
  accion: "FIRMAR",
  materia: "EXPEDIENTE",
  tipo_limite: "SIN_LIMITE",
  monto: null,
  moneda: null,
};

const MATRIZ: MatrizAutoridad = {
  ejercicio: 2026,
  fecha: "2026-02-15",
  items: [ROW_SUP, ROW_DIR_APROBAR, ROW_DIR_FIRMAR],
  total: 3,
  cargos: 2,
  pagina: 1,
  por_pagina: 50,
  estructura: { estado: "VIGENTE" },
};

const DETALLE_DIR: MatrizDetalleCargo = {
  cargo: {
    id: "dir",
    codigo: "DIR-ADM",
    denominacion: "Director de Administración",
    unidad_codigo: "DIR-ADM",
    unidad_denominacion: "Dirección de Administración",
    ruta_unidad: "DESP › DIR-ADM",
    estado: "VIGENTE",
    vigente_desde: "2026-01-01",
    vigente_hasta: null,
  },
  acto_soporte: [{ documento_id: "d1", titulo: "Resolución DA-001" }],
  versiones: [
    {
      version: 1,
      estado: "BORRADOR",
      motivo: null,
      creado_en: "2025-12-01T10:00:00Z",
      competencias: [],
    },
    {
      version: 2,
      estado: "VIGENTE",
      motivo: null,
      creado_en: "2026-01-10T10:00:00Z",
      competencias: [
        {
          accion: "APROBAR",
          materia: "CONTRATACIONES",
          tipo_limite: "MONTO",
          monto: "1000000.00",
          moneda: "VES",
          fundamento: null,
        },
      ],
    },
    {
      version: 3,
      estado: "VIGENTE",
      motivo: "Amplía el límite",
      creado_en: "2026-01-20T16:00:00Z",
      competencias: [
        {
          accion: "APROBAR",
          materia: "CONTRATACIONES",
          tipo_limite: "MONTO",
          monto: "1500000.00",
          moneda: "VES",
          fundamento: "Reglamento interno, art. 12",
        },
        {
          accion: "FIRMAR",
          materia: "EXPEDIENTE",
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

describe("MatrizAutoridadPage", () => {
  it("MTZ-01 · sin gobierno_autoridad:view muestra Sin acceso y no llama a apiFetch", async () => {
    capacidades = new Set();
    renderPagina();

    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("MTZ-02 · muestra título, filas, celdas, resumen e indicadores de límite, vigencia, acto e inactivo", async () => {
    renderPagina();

    expect(
      screen.getByRole("heading", { name: "Matriz de autoridad" }),
    ).toBeInTheDocument();

    expect(
      await screen.findByText("3 autorizaciones de 2 cargos al 15/02/2026"),
    ).toBeInTheDocument();

    expect(screen.getByRole("button", { name: /Exportar CSV/ })).toBeInTheDocument();
    expect(
      screen.getByText(/Las personas que ocupan los cargos llegarán/),
    ).toBeInTheDocument();

    const filas = screen.getAllByRole("row");
    expect(filas.slice(1)).toHaveLength(3);

    const filaSup = filas.find(
      (f) => within(f).queryByText("Custodiar") !== null,
    );
    expect(filaSup).not.toBeNull();
    expect(
      within(filaSup as HTMLElement).getByText("SUP"),
    ).toBeInTheDocument();
    expect(within(filaSup as HTMLElement).getByText("Inactivo")).toBeInTheDocument();
    expect(
      within(filaSup as HTMLElement).getByText("Sin límite"),
    ).toBeInTheDocument();
    expect(
      within(filaSup as HTMLElement).getByText("01/01/2026 – 31/03/2026"),
    ).toBeInTheDocument();
    expect(
      within(filaSup as HTMLElement).getByText("Sin documento"),
    ).toBeInTheDocument();

    const filaDir = filas.find(
      (f) => within(f).queryByText("Aprobar") !== null,
    );
    expect(filaDir).not.toBeNull();
    expect(
      within(filaDir as HTMLElement).getByText("DIR-ADM"),
    ).toBeInTheDocument();
    expect(
      within(filaDir as HTMLElement).getByText(
        "Hasta 1.500.000,00 VES por operación",
      ),
    ).toBeInTheDocument();
    expect(
      within(filaDir as HTMLElement).getByText("Desde 01/01/2026"),
    ).toBeInTheDocument();
    expect(
      within(filaDir as HTMLElement).getByText("Resolución DA-001"),
    ).toBeInTheDocument();
  });

  it("MTZ-03 · la ruta inicial pedida es exacta", async () => {
    renderPagina();

    await screen.findByText("3 autorizaciones de 2 cargos al 15/02/2026");
    expect(apiFetchMock).toHaveBeenCalledWith(
      "/gobierno/autoridad/2026?pagina=1&por_pagina=50",
    );
  });

  it("MTZ-04 · elegir Acción Pagar pide la consulta con accion=PAGAR", async () => {
    const usuario = userEvent.setup();
    renderPagina();

    await screen.findByText("3 autorizaciones de 2 cargos al 15/02/2026");
    await usuario.selectOptions(screen.getByLabelText(/^Acción/), "PAGAR");

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/autoridad/2026?accion=PAGAR&pagina=1&por_pagina=50",
      );
    });
  });

  it("MTZ-05 · escribir en Buscar no pide nada hasta pulsar Buscar; luego recorta el texto", async () => {
    const usuario = userEvent.setup();
    renderPagina();

    await screen.findByText("3 autorizaciones de 2 cargos al 15/02/2026");
    const urlsAntes = apiFetchMock.mock.calls.map((c) => String(c[0]));

    await usuario.type(screen.getByLabelText(/^Buscar/), "  compras ");

    const urlsAlEscribir = apiFetchMock.mock.calls.map((c) => String(c[0]));
    expect(urlsAlEscribir).toEqual(urlsAntes);

    await usuario.click(screen.getByRole("button", { name: "Buscar" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/autoridad/2026?texto=compras&pagina=1&por_pagina=50",
      );
    });
  });

  it("MTZ-06 · Limpiar filtros vacía Buscar y vuelve a la ruta sin filtros", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/autoridad/ejercicios") {
        return Promise.resolve(EJERCICIOS);
      }
      if (url === "/gobierno/autoridad/2026/filtros") {
        return Promise.resolve(FILTROS);
      }
      if (url === "/gobierno/autoridad/2026?accion=PAGAR&texto=abc&pagina=1&por_pagina=50") {
        return Promise.resolve(MATRIZ);
      }
      if (url === "/gobierno/autoridad/2026?pagina=1&por_pagina=50") {
        return Promise.resolve(MATRIZ);
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    const usuario = userEvent.setup();
    renderPagina("/gobierno/autoridad?accion=PAGAR&texto=abc");

    await screen.findByRole("table");
    expect(screen.getByLabelText(/^Buscar/)).toHaveValue("abc");

    await usuario.click(screen.getByRole("button", { name: "Limpiar filtros" }));

    await waitFor(() => {
      expect(screen.getByLabelText(/^Buscar/)).toHaveValue("");
    });
    expect(apiFetchMock).toHaveBeenCalledWith(
      "/gobierno/autoridad/2026?pagina=1&por_pagina=50",
    );
  });

  it("MTZ-07 · Ver detalle pide el detalle y muestra heading, historial y Usada para esta fecha una sola vez; sin gobierno_cargos:view no hay Abrir el cargo", async () => {
    const usuario = userEvent.setup();
    renderPagina();

    await screen.findByText("3 autorizaciones de 2 cargos al 15/02/2026");
    await usuario.click(
      screen.getAllByRole("button", { name: "Ver el detalle de DIR-ADM" })[0],
    );

    expect(
      await screen.findByRole("heading", {
        name: "Detalle de DIR-ADM · Director de Administración",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "Historial del cargo" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Usada para esta fecha")).toHaveLength(1);
    expect(screen.queryByRole("link", { name: "Abrir el cargo" })).not.toBeInTheDocument();
  });

  it("MTZ-08 · con gobierno_cargos:view aparece Abrir el cargo y Cerrar el detalle oculta el panel", async () => {
    capacidades.add("gobierno_cargos:view");
    const usuario = userEvent.setup();
    renderPagina();

    await screen.findByText("3 autorizaciones de 2 cargos al 15/02/2026");
    await usuario.click(
      screen.getAllByRole("button", { name: "Ver el detalle de DIR-ADM" })[0],
    );

    const enlace = await screen.findByRole("link", { name: "Abrir el cargo" });
    expect(enlace).toHaveAttribute("href", "/gobierno/cargos/2026/dir");

    await usuario.click(
      screen.getByRole("button", { name: "Cerrar el detalle" }),
    );
    await waitFor(() => {
      expect(
        screen.queryByRole("heading", {
          name: "Detalle de DIR-ADM · Director de Administración",
        }),
      ).not.toBeInTheDocument();
    });
  });

  it("MTZ-09 · paginación muestra Página 1 de 3, Anterior deshabilitado y Siguiente pide pagina=2", async () => {
    const matrizGrande: MatrizAutoridad = {
      ...MATRIZ,
      total: 120,
      por_pagina: 50,
      pagina: 1,
    };
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/autoridad/ejercicios") {
        return Promise.resolve(EJERCICIOS);
      }
      if (url === "/gobierno/autoridad/2026/filtros") {
        return Promise.resolve(FILTROS);
      }
      if (url === "/gobierno/autoridad/2026?pagina=1&por_pagina=50") {
        return Promise.resolve(matrizGrande);
      }
      if (url === "/gobierno/autoridad/2026?pagina=2&por_pagina=50") {
        return Promise.resolve({ ...matrizGrande, pagina: 2 });
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    const usuario = userEvent.setup();
    renderPagina();

    expect(await screen.findByText("Página 1 de 3")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Anterior" })).toBeDisabled();

    await usuario.click(screen.getByRole("button", { name: "Siguiente" }));
    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/autoridad/2026?pagina=2&por_pagina=50",
      );
    });
  });

  it("MTZ-10 · exportar con ?accion=APROBAR descarga y notifica éxito", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/autoridad/ejercicios") {
        return Promise.resolve(EJERCICIOS);
      }
      if (url === "/gobierno/autoridad/2026/filtros") {
        return Promise.resolve(FILTROS);
      }
      if (url === "/gobierno/autoridad/2026?accion=APROBAR&pagina=1&por_pagina=50") {
        return Promise.resolve(MATRIZ);
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    const usuario = userEvent.setup();
    renderPagina("/gobierno/autoridad?accion=APROBAR");

    await screen.findByRole("table");
    await usuario.click(screen.getByRole("button", { name: /Exportar CSV/ }));

    await waitFor(() => {
      expect(descargarArchivoMock).toHaveBeenCalledWith(
        "/gobierno/autoridad/2026/exportar?accion=APROBAR",
        "autoridad-2026-2026-02-15.csv",
      );
    });
    expect(notify).toHaveBeenCalledWith({
      type: "success",
      title: "Matriz exportada",
    });
  });

  it("MTZ-11 · 422 GOV_AUTHORITY_DATE_OUT_OF_EXERCISE muestra mensaje role=alert y sin tabla", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/autoridad/ejercicios") {
        return Promise.resolve(EJERCICIOS);
      }
      if (url === "/gobierno/autoridad/2026/filtros") {
        return Promise.resolve(FILTROS);
      }
      if (url === "/gobierno/autoridad/2026?fecha=2025-01-01&pagina=1&por_pagina=50") {
        return Promise.reject(
          new ApiError(422, {
            code: "GOV_AUTHORITY_DATE_OUT_OF_EXERCISE",
            message: "La fecha no está en el ejercicio",
            field_errors: {
              fecha: ["La fecha debe estar dentro del ejercicio"],
            },
          }),
        );
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    renderPagina("/gobierno/autoridad?fecha=2025-01-01");

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent("La fecha debe estar dentro del ejercicio");
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("MTZ-12 · MODULE_NOT_ENTITLED muestra Módulo no disponible", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/autoridad/ejercicios") {
        return Promise.reject(
          new ApiError(403, {
            code: "MODULE_NOT_ENTITLED",
            message: "No disponible",
          }),
        );
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    renderPagina();
    expect(
      await screen.findByText("Módulo no disponible"),
    ).toBeInTheDocument();
  });

  it("MTZ-13 · sin ejercicios muestra Sin estructuras organizativas", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/autoridad/ejercicios") {
        return Promise.resolve({ items: [] });
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    renderPagina();
    expect(
      await screen.findByText("Sin estructuras organizativas"),
    ).toBeInTheDocument();
  });

  it("MTZ-14 · total 0 sin y con filtro muestra los avisos correspondientes", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/autoridad/ejercicios") {
        return Promise.resolve(EJERCICIOS);
      }
      if (url === "/gobierno/autoridad/2026/filtros") {
        return Promise.resolve(FILTROS);
      }
      if (url === "/gobierno/autoridad/2026?pagina=1&por_pagina=50") {
        return Promise.resolve({ ...MATRIZ, items: [], total: 0 });
      }
      if (url === "/gobierno/autoridad/2026?accion=PAGAR&pagina=1&por_pagina=50") {
        return Promise.resolve({ ...MATRIZ, items: [], total: 0 });
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    userEvent.setup();
    const { unmount } = renderPagina();

    expect(
      await screen.findByText("Sin autoridad registrada al 15/02/2026"),
    ).toBeInTheDocument();

    unmount();
    renderPagina("/gobierno/autoridad?accion=PAGAR");

    expect(
      await screen.findByText("Ninguna autorización coincide con los filtros"),
    ).toBeInTheDocument();
    expect(
      screen.getAllByRole("button", { name: "Limpiar filtros" }).length,
    ).toBeGreaterThanOrEqual(2);
  });

  it("MTZ-15 · total 1 y cargos 1 usan singular", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/autoridad/ejercicios") {
        return Promise.resolve(EJERCICIOS);
      }
      if (url === "/gobierno/autoridad/2026/filtros") {
        return Promise.resolve(FILTROS);
      }
      if (url === "/gobierno/autoridad/2026?pagina=1&por_pagina=50") {
        return Promise.resolve({
          ...MATRIZ,
          items: [ROW_DIR_APROBAR],
          total: 1,
          cargos: 1,
        });
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    renderPagina();
    expect(
      await screen.findByText("1 autorización de 1 cargo al 15/02/2026"),
    ).toBeInTheDocument();
  });

  it("MTZ-16 · error 500 muestra mensaje con botón de reintento", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/autoridad/ejercicios") {
        return Promise.resolve(EJERCICIOS);
      }
      if (url === "/gobierno/autoridad/2026/filtros") {
        return Promise.resolve(FILTROS);
      }
      if (url === "/gobierno/autoridad/2026?pagina=1&por_pagina=50") {
        return Promise.reject(
          new ApiError(500, { code: "INTERNAL", message: "Error" }),
        );
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    const usuario = userEvent.setup();
    renderPagina();

    expect(
      await screen.findByText("No fue posible cargar la matriz de autoridad."),
    ).toBeInTheDocument();
    const reintentar = screen.getByRole("button", { name: "Reintentar" });
    expect(reintentar).toBeInTheDocument();

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
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    await usuario.click(reintentar);
    expect(
      await screen.findByText("3 autorizaciones de 2 cargos al 15/02/2026"),
    ).toBeInTheDocument();
  });

  it("MTZ-17 · render con ?ejercicio=2025&accion=VOLAR pide el ejercicio 2025 sin accion inválida", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/autoridad/ejercicios") {
        return Promise.resolve(EJERCICIOS);
      }
      if (url === "/gobierno/autoridad/2025/filtros") {
        return Promise.resolve(FILTROS);
      }
      if (url === "/gobierno/autoridad/2025?pagina=1&por_pagina=50") {
        return Promise.resolve({ ...MATRIZ, ejercicio: 2025 });
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    renderPagina("/gobierno/autoridad?ejercicio=2025&accion=VOLAR");

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/autoridad/2025?pagina=1&por_pagina=50",
      );
    });
    expect(apiFetchMock).not.toHaveBeenCalledWith(
      expect.stringContaining("accion=VOLAR"),
    );
  });

  it("MTZ-18 · con ejercicios [2027 BORRADOR, 2026 VIGENTE] y sin ejercicio en la URL, pide 2026 y no 2027; el select tiene valor 2026", async () => {
    const ejercicios: MatrizEjercicios = {
      items: [
        { ejercicio: 2027, estado: "BORRADOR" },
        { ejercicio: 2026, estado: "VIGENTE" },
      ],
    };
    const matriz2026: MatrizAutoridad = { ...MATRIZ };

    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/autoridad/ejercicios") {
        return Promise.resolve(ejercicios);
      }
      if (url === "/gobierno/autoridad/2026/filtros") {
        return Promise.resolve(FILTROS);
      }
      if (url === "/gobierno/autoridad/2026?pagina=1&por_pagina=50") {
        return Promise.resolve(matriz2026);
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    renderPagina();

    expect(
      await screen.findByText("3 autorizaciones de 2 cargos al 15/02/2026"),
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/autoridad/2026?pagina=1&por_pagina=50",
      );
    });
    expect(apiFetchMock).not.toHaveBeenCalledWith(
      expect.stringContaining("/gobierno/autoridad/2027"),
    );

    const selectEjercicio = screen.getByLabelText(/^Ejercicio/) as HTMLSelectElement;
    expect(selectEjercicio.value).toBe("2026");
  });

  it("MTZ-19 · tras pulsar Siguiente (pagina=2), elegir Acción «Pagar» vuelve a la página 1", async () => {
    const matrizGrande: MatrizAutoridad = {
      ...MATRIZ,
      total: 120,
      por_pagina: 50,
      pagina: 1,
    };
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/autoridad/ejercicios") {
        return Promise.resolve(EJERCICIOS);
      }
      if (url === "/gobierno/autoridad/2026/filtros") {
        return Promise.resolve(FILTROS);
      }
      if (url === "/gobierno/autoridad/2026?pagina=1&por_pagina=50") {
        return Promise.resolve(matrizGrande);
      }
      if (url === "/gobierno/autoridad/2026?pagina=2&por_pagina=50") {
        return Promise.resolve({ ...matrizGrande, pagina: 2 });
      }
      if (url === "/gobierno/autoridad/2026?accion=PAGAR&pagina=1&por_pagina=50") {
        return Promise.resolve({ ...matrizGrande, pagina: 1 });
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    const usuario = userEvent.setup();
    renderPagina();

    expect(await screen.findByText("Página 1 de 3")).toBeInTheDocument();

    await usuario.click(screen.getByRole("button", { name: "Siguiente" }));
    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/autoridad/2026?pagina=2&por_pagina=50",
      );
    });

    await usuario.selectOptions(screen.getByLabelText("Acción"), "PAGAR");

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/autoridad/2026?accion=PAGAR&pagina=1&por_pagina=50",
      );
    });
  });
});
