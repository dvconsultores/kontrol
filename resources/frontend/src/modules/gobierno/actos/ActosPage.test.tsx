import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import {
  ETIQUETA_ESTADO_ACTO,
  nombreDeActo,
  type ActoResumen,
} from "@/modules/gobierno/api";

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

const descargarArchivo = vi.fn().mockResolvedValue("x.csv");

vi.mock("@/api/descargas", () => ({
  descargarArchivo: (...args: unknown[]) => descargarArchivo(...args),
}));

vi.mock("@/lib/fecha-de-negocio", async (original) => ({
  ...(await original<typeof import("@/lib/fecha-de-negocio")>()),
  hoyDeNegocio: () => "2026-10-30",
}));

const DATOS_FALSOS = {
  fecha: "2026-10-30",
  cargo_id: "cargo-1",
  competencia: { accion: "APROBAR", materia: "CONTRATACIONES" },
  fundamento_competencia: "Art. 1",
  funcionario: "Nombre del funcionario",
  titularidad: "TITULAR",
  caracter: "GENERAL",
  simple_tramite: false,
  tipo: "RESOLUCION",
  numero: "NUEVO-1",
  asunto: "Alta de prueba",
  hechos: "Hechos",
  fundamentos: "Fundamentos",
  decision: "Decisión",
  lugar: "Sede",
};

vi.mock("./ActoFormulario", () => ({
  ActoFormulario: (p: {
    onGuardar: (datos: unknown) => Promise<void>;
    erroresServidor: Record<string, string[]>;
  }) => (
    <div>
      <button
        type="button"
        onClick={() => {
          void p.onGuardar(DATOS_FALSOS);
        }}
      >
        Guardar falso
      </button>
      <output data-testid="errores">
        {JSON.stringify(p.erroresServidor)}
      </output>
    </div>
  ),
}));

const { ActosPage } = await import("./ActosPage");

const ACTOS: ActoResumen[] = [
  {
    id: "a1",
    tipo: "RESOLUCION",
    denominacion_tipo: null,
    numero: "DA-001-2026",
    fecha: "2026-03-10",
    cargo_codigo: "DIR-ADM",
    cargo_denominacion: "Dirección de Administración",
    unidad_codigo: "DA",
    caracter: "PARTICULAR",
    asunto: "Designación del tesorero",
    estado: "EFICAZ",
    fecha_eficacia: "2026-03-12",
  },
  {
    id: "a2",
    tipo: "DECRETO",
    denominacion_tipo: null,
    numero: "D-002-2026",
    fecha: "2026-04-01",
    cargo_codigo: "ALC",
    cargo_denominacion: "Alcalde",
    unidad_codigo: "DESP",
    caracter: "GENERAL",
    asunto: "Horario de atención al público",
    estado: "EMITIDO",
    fecha_eficacia: null,
  },
  {
    id: "a3",
    tipo: "CIRCULAR",
    denominacion_tipo: null,
    numero: "C-003-2026",
    fecha: "2026-05-05",
    cargo_codigo: "DIR-ADM",
    cargo_denominacion: "Dirección de Administración",
    unidad_codigo: "DA",
    caracter: "INTERNO",
    asunto: "Uso de vehículos oficiales",
    estado: "BORRADOR",
    fecha_eficacia: null,
  },
];

function LISTA_ACTOS(items: ActoResumen[] = ACTOS): unknown {
  return {
    anio: 2026,
    items,
    total: items.length,
  };
}

function montar(rutaInicial = "/gobierno/actos"): void {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[rutaInicial]}>
        <Routes>
          <Route path="/gobierno/actos" element={<ActosPage />} />
          <Route
            path="/gobierno/actos/:actoId"
            element={<p>Detalle del acto</p>}
          />
          <Route path="/gobierno/ente" element={<p>Ente</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function responderActos(items: ActoResumen[] = ACTOS): void {
  apiFetch.mockImplementation((ruta: string, opciones?: { method?: string }) => {
    if (ruta === "/gobierno/actos?anio=2026" && (!opciones?.method || opciones.method === "GET")) {
      return Promise.resolve(LISTA_ACTOS(items));
    }
    if (ruta === "/gobierno/actos?anio=2025" && (!opciones?.method || opciones.method === "GET")) {
      return Promise.resolve({ anio: 2025, items: [], total: 0 });
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

describe("ActosPage", () => {
  it("GAL-01 · con gobierno_actos:view lista los 3 actos con nombre, fecha y estado", async () => {
    capacidades = new Set(["gobierno_actos:view"]);
    responderActos();
    montar();

    await screen.findByLabelText(/^Año/);

    expect(apiFetch).toHaveBeenCalledWith("/gobierno/actos?anio=2026");

    const enlaceA1 = screen.getByRole("link", {
      name: `Abrir el acto ${nombreDeActo(ACTOS[0])}`,
    });
    expect(enlaceA1).toHaveAttribute("href", "/gobierno/actos/a1");

    const filaA1 = enlaceA1.closest("tr");
    expect(filaA1).not.toBeNull();
    expect(within(filaA1 as HTMLElement).getByText("12/03/2026")).toBeInTheDocument();
    expect(
      within(filaA1 as HTMLElement).getByText(ETIQUETA_ESTADO_ACTO.EFICAZ),
    ).toBeInTheDocument();

    const enlaceA2 = screen.getByRole("link", {
      name: `Abrir el acto ${nombreDeActo(ACTOS[1])}`,
    });
    const filaA2 = enlaceA2.closest("tr");
    expect(filaA2).not.toBeNull();
    expect(within(filaA2 as HTMLElement).getByText("—")).toBeInTheDocument();

    expect(
      screen.getByRole("link", {
        name: `Abrir el acto ${nombreDeActo(ACTOS[2])}`,
      }),
    ).toBeInTheDocument();
  });

  it("GAL-02 · cambiar «Año» a 2025 pide /gobierno/actos?anio=2025", async () => {
    capacidades = new Set(["gobierno_actos:view"]);
    responderActos();
    montar();

    await screen.findByLabelText(/^Año/);
    await userEvent.selectOptions(screen.getByLabelText("Año"), "2025");

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith("/gobierno/actos?anio=2025");
    });
  });

  it("GAL-03 · «Buscar» filtra por asunto y por número sin distinguir mayúsculas", async () => {
    capacidades = new Set(["gobierno_actos:view"]);
    responderActos();
    montar();

    await screen.findByLabelText(/^Año/);

    const buscar = screen.getByLabelText("Buscar");
    await userEvent.type(buscar, "TESORERO");
    expect(
      screen.getByRole("link", {
        name: `Abrir el acto ${nombreDeActo(ACTOS[0])}`,
      }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("link", {
        name: `Abrir el acto ${nombreDeActo(ACTOS[1])}`,
      }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", {
        name: `Abrir el acto ${nombreDeActo(ACTOS[2])}`,
      }),
    ).not.toBeInTheDocument();

    await userEvent.clear(buscar);
    await userEvent.type(buscar, "d-002");
    expect(
      screen.getByRole("link", {
        name: `Abrir el acto ${nombreDeActo(ACTOS[1])}`,
      }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("link", {
        name: `Abrir el acto ${nombreDeActo(ACTOS[0])}`,
      }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", {
        name: `Abrir el acto ${nombreDeActo(ACTOS[2])}`,
      }),
    ).not.toBeInTheDocument();
  });

  it("GAL-04 · filtros de Estado, Carácter y Cargo filtran correctamente", async () => {
    capacidades = new Set(["gobierno_actos:view"]);
    responderActos();
    montar();

    await screen.findByLabelText(/^Año/);

    await userEvent.selectOptions(screen.getByLabelText("Estado"), "BORRADOR");
    expect(
      screen.getByRole("link", {
        name: `Abrir el acto ${nombreDeActo(ACTOS[2])}`,
      }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("link", {
        name: `Abrir el acto ${nombreDeActo(ACTOS[0])}`,
      }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", {
        name: `Abrir el acto ${nombreDeActo(ACTOS[1])}`,
      }),
    ).not.toBeInTheDocument();

    await userEvent.selectOptions(screen.getByLabelText("Estado"), "");
    await userEvent.selectOptions(screen.getByLabelText("Carácter"), "GENERAL");
    expect(
      screen.getByRole("link", {
        name: `Abrir el acto ${nombreDeActo(ACTOS[1])}`,
      }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("link", {
        name: `Abrir el acto ${nombreDeActo(ACTOS[0])}`,
      }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", {
        name: `Abrir el acto ${nombreDeActo(ACTOS[2])}`,
      }),
    ).not.toBeInTheDocument();

    await userEvent.selectOptions(screen.getByLabelText("Carácter"), "");
    await userEvent.selectOptions(screen.getByLabelText("Cargo"), "DIR-ADM");
    expect(
      screen.getByRole("link", {
        name: `Abrir el acto ${nombreDeActo(ACTOS[0])}`,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", {
        name: `Abrir el acto ${nombreDeActo(ACTOS[2])}`,
      }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("link", {
        name: `Abrir el acto ${nombreDeActo(ACTOS[1])}`,
      }),
    ).not.toBeInTheDocument();
  });

  it("GAL-05 · búsqueda sin coincidencias muestra el texto real de «ningún acto coincide»", async () => {
    capacidades = new Set(["gobierno_actos:view"]);
    responderActos();
    montar();

    await screen.findByLabelText(/^Año/);
    await userEvent.type(screen.getByLabelText("Buscar"), "NO-EXISTE");

    expect(
      await screen.findByText("Ningún acto coincide con el filtro."),
    ).toBeInTheDocument();
  });

  it("GAL-06 · lista vacía muestra «No hay actos registrados en 2026»", async () => {
    capacidades = new Set(["gobierno_actos:view"]);
    responderActos([]);
    montar();

    expect(
      await screen.findByText("No hay actos registrados en 2026"),
    ).toBeInTheDocument();
  });

  it("GAL-07 · 404 GOV_ENTITY_NOT_FOUND muestra el aviso real y un enlace a /gobierno/ente", async () => {
    capacidades = new Set(["gobierno_actos:view"]);
    apiFetch.mockImplementation((ruta: string) => {
      if (ruta === "/gobierno/actos?anio=2026") {
        return Promise.reject(
          new ApiError(404, { code: "GOV_ENTITY_NOT_FOUND", message: "x" }),
        );
      }
      return Promise.reject(new Error(`ruta inesperada ${ruta}`));
    });
    montar();

    expect(
      await screen.findByText("Primero configure el ente"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Ir a Configuración del ente" }),
    ).toHaveAttribute("href", "/gobierno/ente");
    expect(screen.getByRole("heading", { level: 1, name: "Actos administrativos" })).toBeInTheDocument();
  });

  it("GAL-08 · 403 MODULE_NOT_ENTITLED muestra el aviso real de módulo no habilitado", async () => {
    capacidades = new Set(["gobierno_actos:view"]);
    apiFetch.mockImplementation((ruta: string) => {
      if (ruta === "/gobierno/actos?anio=2026") {
        return Promise.reject(
          new ApiError(403, { code: "MODULE_NOT_ENTITLED", message: "x" }),
        );
      }
      return Promise.reject(new Error(`ruta inesperada ${ruta}`));
    });
    montar();

    expect(
      await screen.findByText("Módulo no disponible"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("El módulo de Gobierno no está habilitado."),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Actos administrativos" })).toBeInTheDocument();
  });

  it("GAL-09a · sin gobierno_actos:edit no hay botón «Registrar acto»", async () => {
    capacidades = new Set(["gobierno_actos:view"]);
    responderActos();
    montar();

    await screen.findByLabelText(/^Año/);
    expect(
      screen.queryByRole("button", { name: "Registrar acto" }),
    ).not.toBeInTheDocument();
  });

  it("GAL-09b · con view+edit hay botón «Registrar acto» y abre el formulario", async () => {
    capacidades = new Set(["gobierno_actos:view", "gobierno_actos:edit"]);
    responderActos();
    montar();

    await userEvent.click(
      await screen.findByRole("button", { name: "Registrar acto" }),
    );
    expect(
      await screen.findByRole("button", { name: "Guardar falso" }),
    ).toBeInTheDocument();
  });

  it("GAL-10 · alta correcta hace POST a /gobierno/actos, notifica éxito y navega al detalle", async () => {
    capacidades = new Set(["gobierno_actos:view", "gobierno_actos:edit"]);
    apiFetch.mockImplementation((ruta: string, opciones?: { method?: string }) => {
      if (ruta === "/gobierno/actos?anio=2026" && (!opciones?.method || opciones.method === "GET")) {
        return Promise.resolve(LISTA_ACTOS());
      }
      if (ruta === "/gobierno/actos" && opciones?.method === "POST") {
        return Promise.resolve({ id: "a-nueva", numero: "NUEVO-1" });
      }
      return Promise.reject(new Error(`ruta inesperada ${ruta}`));
    });
    montar();

    await userEvent.click(
      await screen.findByRole("button", { name: "Registrar acto" }),
    );
    await userEvent.click(
      await screen.findByRole("button", { name: "Guardar falso" }),
    );

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/gobierno/actos",
        expect.objectContaining({
          method: "POST",
          body: expect.objectContaining({ numero: "NUEVO-1" }),
        }),
      );
    });
    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith({
        type: "success",
        title: "Acto registrado",
      });
    });
    expect(await screen.findByText("Detalle del acto")).toBeInTheDocument();
  });

  it("GAL-11 · alta con 409 GOV_ACT_NUMBER_DUPLICATE muestra el error en el output", async () => {
    capacidades = new Set(["gobierno_actos:view", "gobierno_actos:edit"]);
    apiFetch.mockImplementation((ruta: string, opciones?: { method?: string }) => {
      if (ruta === "/gobierno/actos?anio=2026" && (!opciones?.method || opciones.method === "GET")) {
        return Promise.resolve(LISTA_ACTOS());
      }
      if (ruta === "/gobierno/actos" && opciones?.method === "POST") {
        return Promise.reject(
          new ApiError(409, {
            code: "GOV_ACT_NUMBER_DUPLICATE",
            message: "Ya existe un acto con este cargo, tipo y número",
          }),
        );
      }
      return Promise.reject(new Error(`ruta inesperada ${ruta}`));
    });
    montar();

    await userEvent.click(
      await screen.findByRole("button", { name: "Registrar acto" }),
    );
    await userEvent.click(
      await screen.findByRole("button", { name: "Guardar falso" }),
    );

    const errores = await screen.findByTestId("errores");
    await waitFor(() => {
      expect(JSON.parse(errores.textContent ?? "{}")).toEqual({
        numero: ["Ya existe un acto con este cargo, tipo y número"],
      });
    });
    expect(screen.queryByText("Detalle del acto")).not.toBeInTheDocument();
  });

  it("GAL-12 · alta con 422 field_errors muestra los errores en el output", async () => {
    capacidades = new Set(["gobierno_actos:view", "gobierno_actos:edit"]);
    apiFetch.mockImplementation((ruta: string, opciones?: { method?: string }) => {
      if (ruta === "/gobierno/actos?anio=2026" && (!opciones?.method || opciones.method === "GET")) {
        return Promise.resolve(LISTA_ACTOS());
      }
      if (ruta === "/gobierno/actos" && opciones?.method === "POST") {
        return Promise.reject(
          new ApiError(422, {
            code: "VALIDATION_ERROR",
            message: "x",
            field_errors: { asunto: ["Escriba el asunto"] },
          }),
        );
      }
      return Promise.reject(new Error(`ruta inesperada ${ruta}`));
    });
    montar();

    await userEvent.click(
      await screen.findByRole("button", { name: "Registrar acto" }),
    );
    await userEvent.click(
      await screen.findByRole("button", { name: "Guardar falso" }),
    );

    const errores = await screen.findByTestId("errores");
    await waitFor(() => {
      expect(JSON.parse(errores.textContent ?? "{}")).toEqual({
        asunto: ["Escriba el asunto"],
      });
    });
  });

  it("GAL-13 · alta con 403 notifica error de permiso", async () => {
    capacidades = new Set(["gobierno_actos:view", "gobierno_actos:edit"]);
    apiFetch.mockImplementation((ruta: string, opciones?: { method?: string }) => {
      if (ruta === "/gobierno/actos?anio=2026" && (!opciones?.method || opciones.method === "GET")) {
        return Promise.resolve(LISTA_ACTOS());
      }
      if (ruta === "/gobierno/actos" && opciones?.method === "POST") {
        return Promise.reject(
          new ApiError(403, { code: "FORBIDDEN", message: "x" }),
        );
      }
      return Promise.reject(new Error(`ruta inesperada ${ruta}`));
    });
    montar();

    await userEvent.click(
      await screen.findByRole("button", { name: "Registrar acto" }),
    );
    await userEvent.click(
      await screen.findByRole("button", { name: "Guardar falso" }),
    );

    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith({
        type: "error",
        title: "No tiene permiso para esta acción",
      });
    });
  });

  it("GAL-14 · «Exportar CSV» llama a descargarArchivo con la ruta y nombre correctos y notifica éxito", async () => {
    capacidades = new Set(["gobierno_actos:view"]);
    responderActos();
    montar();

    await userEvent.click(
      await screen.findByRole("button", { name: "Exportar CSV" }),
    );

    await waitFor(() => {
      expect(descargarArchivo).toHaveBeenCalledWith(
        "/gobierno/actos/exportar?anio=2026",
        "actos-2026.csv",
      );
    });
    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith({
        type: "success",
        title: "Actos exportados",
      });
    });
  });
});
