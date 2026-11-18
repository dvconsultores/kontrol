import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it, vi, beforeEach } from "vitest";

const apiFetchMock = vi.fn();
vi.mock("@/api/client", async (original) => {
  const actual = await original<typeof import("@/api/client")>();
  return {
    ...actual,
    apiFetch: (...args: unknown[]) => apiFetchMock(...args),
    ApiError: class ApiError extends Error {
      status: number;
      code: string;
      fieldErrors: Record<string, string[]>;
      constructor(
        message: string,
        status: number,
        code: string,
        fieldErrors: Record<string, string[]> = {},
      ) {
        super(message);
        this.status = status;
        this.code = code;
        this.fieldErrors = fieldErrors;
      }
    },
  };
});
vi.mock("@/api/descargas", () => ({ descargarArchivo: vi.fn() }));

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
vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: vi.fn() }),
}));

import { PoliticaComisionFormPage } from "./PoliticaComisionFormPage";
import { ApiError } from "@/api/client";

const catalogoFixture = {
  estados: [
    { codigo: "BORRADOR", etiqueta: "Borrador" },
    { codigo: "ACTIVA", etiqueta: "Activa" },
  ],
  tipos_comision: [
    { codigo: "PERMANENTE", etiqueta: "Permanente" },
    { codigo: "TEMPORAL", etiqueta: "Temporal" },
  ],
  bases_normativas: [
    { codigo: "NINGUNA", etiqueta: "Ninguna" },
    { codigo: "LCP_ART14", etiqueta: "LCP art. 14" },
  ],
  tipos_mayoria: [
    { codigo: "SIMPLE", etiqueta: "Mayoría simple" },
    { codigo: "ABSOLUTE_COUNT", etiqueta: "Cantidad absoluta" },
    { codigo: "QUALIFIED_MAJORITY", etiqueta: "Mayoría cualificada" },
  ],
  bases_decision: [
    { codigo: "VOTOS_FAVORABLES", etiqueta: "Votos favorables" },
    { codigo: "MIEMBROS_PRESENTES", etiqueta: "Miembros presentes" },
  ],
  funciones: [
    { codigo: "MIEMBRO", etiqueta: "Miembro" },
    { codigo: "SECRETARIO", etiqueta: "Secretario" },
  ],
  condiciones: [
    { codigo: "PRINCIPAL", etiqueta: "Principal" },
    { codigo: "SUPLENTE", etiqueta: "Suplente" },
    { codigo: "CUALQUIERA", etiqueta: "Principal o suplente" },
  ],
  tipos_requisito: [
    { codigo: "AREA", etiqueta: "Área" },
    { codigo: "CARGO", etiqueta: "Cargo" },
    { codigo: "UNIDAD", etiqueta: "Unidad" },
    { codigo: "COMPETENCIA", etiqueta: "Competencia" },
    { codigo: "FUNCIONARIO", etiqueta: "Funcionario" },
  ],
  areas: [
    { codigo: "AREA1", etiqueta: "Área 1" },
    { codigo: "AREA2", etiqueta: "Área 2" },
  ],
  etapas: [
    { codigo: "APERTURA", etiqueta: "Apertura" },
    { codigo: "RECOMENDACION", etiqueta: "Recomendación" },
  ],
  medios: [
    { codigo: "GACETA", etiqueta: "Gaceta" },
    { codigo: "WEB", etiqueta: "Web" },
  ],
  acciones_competencia: [
    { codigo: "AUTORIZAR", etiqueta: "Autorizar" },
    { codigo: "APROBAR", etiqueta: "Aprobar" },
  ],
  materias_competencia: [
    { codigo: "OBRAS", etiqueta: "Obras" },
    { codigo: "BIENES", etiqueta: "Bienes" },
  ],
  piso_lcp: {
    exige_impar: true,
    suplente_por_principal: true,
    exige_secretario: true,
    exige_suplente_secretario: true,
    acto_requerido: true,
  },
};

const opcionesFixture = {
  cargos: [
    { id: "cargo-1", etiqueta: "Director" },
    { id: "cargo-2", etiqueta: "Jefe" },
  ],
  unidades: [
    { id: "unit-1", etiqueta: "Unidad 1" },
    { id: "unit-2", etiqueta: "Unidad 2" },
  ],
  funcionarios: [
    { id: "func-1", etiqueta: "Funcionario 1" },
    { id: "func-2", etiqueta: "Funcionario 2" },
  ],
  tipos_documentales: [
    { id: "doc-1", etiqueta: "Oferta técnica" },
    { id: "doc-2", etiqueta: "Oferta económica" },
  ],
};

// Forma mínima del cuerpo enviado que leen las aserciones.
type CuerpoEnviado = Record<string, unknown> & {
  codigo?: string;
  nombre?: string;
  tipo_comision?: string;
  vigente_desde?: string;
  requisitos?: Record<string, unknown>[];
  documentos?: Record<string, unknown>[];
};

function renderPage(initialEntries: string[]) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route
            path="/gobierno/contrataciones/politicas-comision/nueva"
            element={<PoliticaComisionFormPage />}
          />
          <Route
            path="/gobierno/contrataciones/politicas-comision/:politicaId/editar"
            element={<PoliticaComisionFormPage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiFetchMock.mockReset();
  capacidades = new Set(["gobierno_comisiones:configure"]);
  apiFetchMock.mockImplementation((url: string) => {
    if (url.endsWith("/catalogo")) {
      return Promise.resolve(catalogoFixture);
    }
    if (url.endsWith("/opciones")) {
      return Promise.resolve(opcionesFixture);
    }
    return Promise.reject(new Error("URL no mockeada: " + url));
  });
});

describe("PoliticaComisionFormPage", () => {
  it("(a) sin permiso configure muestra Sin acceso", async () => {
    capacidades = new Set();
    renderPage(["/gobierno/contrataciones/politicas-comision/nueva"]);
    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
  });

  it("(b) crear: rellena y envía con el cuerpo esperado", async () => {
    const usuario = userEvent.setup();
    apiFetchMock.mockImplementation((url: string, options?: { method?: string }) => {
      if (url.endsWith("/catalogo")) return Promise.resolve(catalogoFixture);
      if (url.endsWith("/opciones")) return Promise.resolve(opcionesFixture);
      if (options?.method === "POST") {
        return Promise.resolve({
          id: "pol-1",
          version: 1,
          ...((options as { body?: Record<string, unknown> }).body ?? {}),
        });
      }
      return Promise.reject(new Error("URL no mockeada: " + url));
    });

    renderPage(["/gobierno/contrataciones/politicas-comision/nueva"]);

    await screen.findByLabelText(/^Código/);
    await usuario.type(screen.getByLabelText(/^Código/), "POL-001");
    await usuario.type(screen.getByLabelText(/^Nombre/), "Política General");
    await usuario.selectOptions(screen.getByLabelText(/^Tipo de comisión/), "PERMANENTE");
    await usuario.type(screen.getByLabelText(/^Desde/), "2025-01-01");

    await usuario.selectOptions(
      screen.getByLabelText(/^Tipo de quórum/) as HTMLSelectElement,
      "ABSOLUTE_COUNT",
    );
    await usuario.type(screen.getByLabelText(/^Cantidad del quórum/) as HTMLElement, "3");

    await usuario.selectOptions(screen.getByLabelText(/^Tipo de mayoría/), "SIMPLE");
    await usuario.selectOptions(
      screen.getByLabelText(/^Base de la decisión/),
      "VOTOS_FAVORABLES",
    );

    await usuario.click(screen.getByRole("button", { name: "Añadir requisito" }));
    const filaRequisito = screen.getByLabelText(/^Tipo de requisito/).closest("fieldset")
      ?? screen.getByLabelText(/^Tipo de requisito/).closest("div");
    await usuario.type(
      within(filaRequisito as HTMLElement).getByLabelText(/^Etiqueta/),
      "Ser economista",
    );
    await usuario.selectOptions(
      within(filaRequisito as HTMLElement).getByLabelText(/^Función/),
      "MIEMBRO",
    );
    await usuario.selectOptions(
      within(filaRequisito as HTMLElement).getByLabelText(/^Condición del miembro/),
      "PRINCIPAL",
    );
    await usuario.selectOptions(
      within(filaRequisito as HTMLElement).getByLabelText(/^Tipo de requisito/),
      "CARGO",
    );
    await usuario.selectOptions(
      within(filaRequisito as HTMLElement).getByLabelText(/^Cargo/),
      "cargo-1",
    );

    await usuario.click(screen.getByRole("button", { name: "Añadir documento" }));
    const filaDocumento = screen.getByLabelText(/^Condición del documento/).closest("fieldset")
      ?? screen.getByLabelText(/^Condición del documento/).closest("div");
    await usuario.selectOptions(
      within(filaDocumento as HTMLElement).getByLabelText(/^Tipo documental/),
      "doc-1",
    );
    await usuario.selectOptions(
      within(filaDocumento as HTMLElement).getByLabelText(/^Etapa/),
      "APERTURA",
    );

    await usuario.click(screen.getByRole("button", { name: "Guardar borrador" }));

    await waitFor(() => {
      const postCalls = apiFetchMock.mock.calls.filter(
        (call) => (call[1] as { method?: string } | undefined)?.method === "POST",
      );
      expect(postCalls).toHaveLength(1);
      const body = (postCalls[0][1] as { body: CuerpoEnviado }).body;
      expect(body.codigo).toBe("POL-001");
      expect(body.nombre).toBe("Política General");
      expect(body.tipo_comision).toBe("PERMANENTE");
      expect(body.vigente_desde).toBe("2025-01-01");
      expect(body.quorum).toEqual({
        tipo: "ABSOLUTE_COUNT",
        cantidad: 3,
        numerador: null,
        denominador: null,
      });
      expect(body.decision).toEqual({
        tipo: "SIMPLE",
        cantidad: null,
        numerador: null,
        denominador: null,
        base: "VOTOS_FAVORABLES",
      });
      expect(body.requisitos ?? []).toHaveLength(1);
      expect((body.requisitos ?? [])[0]).toMatchObject({
        etiqueta: "Ser economista",
        tipo: "CARGO",
        position_id: "cargo-1",
        area: null,
        unit_id: null,
        competencia_accion: null,
        competencia_materia: null,
        official_id: null,
      });
      expect(body.documentos ?? []).toHaveLength(1);
      expect((body.documentos ?? [])[0]).toMatchObject({
        document_type_id: "doc-1",
        etapa: "APERTURA",
        obligatorio: true,
      });
    });
  });

  it("(c) validación local: hasta < desde no llama a la API y muestra el mensaje", async () => {
    const usuario = userEvent.setup();
    renderPage(["/gobierno/contrataciones/politicas-comision/nueva"]);

    await screen.findByLabelText(/^Código/);
    await usuario.type(screen.getByLabelText(/^Código/), "POL-001");
    await usuario.type(screen.getByLabelText(/^Nombre/), "Política");
    await usuario.type(screen.getByLabelText(/^Desde/), "2025-02-01");
    await usuario.type(screen.getByLabelText(/^Hasta/), "2025-01-01");

    await usuario.click(screen.getByRole("button", { name: "Guardar borrador" }));

    expect(
      await screen.findByText("La fecha hasta no puede ser anterior a la desde."),
    ).toBeInTheDocument();
    const postCalls = apiFetchMock.mock.calls.filter(
      (call) => (call[1] as { method?: string } | undefined)?.method === "POST",
    );
    expect(postCalls).toHaveLength(0);
  });

  it("(d) base LCP bloquea las exigencias del piso", async () => {
    const usuario = userEvent.setup();
    renderPage(["/gobierno/contrataciones/politicas-comision/nueva"]);

    await screen.findByLabelText(/^Código/);
    await usuario.selectOptions(screen.getByLabelText(/^Base normativa/), "LCP_ART14");

    const impar = screen.getByRole("checkbox", { name: "Número impar" }) as HTMLInputElement;
    const suplente = screen.getByRole("checkbox", {
      name: "Suplente por principal",
    }) as HTMLInputElement;
    const secretario = screen.getByRole("checkbox", {
      name: "Secretario",
    }) as HTMLInputElement;
    const suplenteSecretario = screen.getByRole("checkbox", {
      name: "Suplente del secretario",
    }) as HTMLInputElement;
    const acto = screen.getByRole("checkbox", {
      name: "Acto requerido",
    }) as HTMLInputElement;

    expect(impar.disabled).toBe(true);
    expect(impar.checked).toBe(true);
    expect(suplente.disabled).toBe(true);
    expect(suplente.checked).toBe(true);
    expect(secretario.disabled).toBe(true);
    expect(secretario.checked).toBe(true);
    expect(suplenteSecretario.disabled).toBe(true);
    expect(suplenteSecretario.checked).toBe(true);
    expect(acto.disabled).toBe(true);
    expect(acto.checked).toBe(true);
    expect(
      screen.getByText("Piso legal LCP art. 14: el ente puede endurecerlo, no rebajarlo."),
    ).toBeInTheDocument();
  });

  it("(e) requisito de tipo CARGO muestra cargo y no área; al cambiar a COMPETENCIA aparecen acción y materia", async () => {
    const usuario = userEvent.setup();
    renderPage(["/gobierno/contrataciones/politicas-comision/nueva"]);

    await screen.findByLabelText(/^Código/);
    await usuario.click(screen.getByRole("button", { name: "Añadir requisito" }));

    const filaRequisito = screen.getByLabelText(/^Tipo de requisito/).closest("fieldset")
      ?? screen.getByLabelText(/^Tipo de requisito/).closest("div");

    await usuario.selectOptions(
      within(filaRequisito as HTMLElement).getByLabelText(/^Tipo de requisito/),
      "CARGO",
    );
    expect(within(filaRequisito as HTMLElement).getByLabelText(/^Cargo/)).toBeInTheDocument();
    expect(within(filaRequisito as HTMLElement).queryByLabelText(/^Área/)).not.toBeInTheDocument();

    await usuario.selectOptions(
      within(filaRequisito as HTMLElement).getByLabelText(/^Tipo de requisito/),
      "COMPETENCIA",
    );
    expect(
      within(filaRequisito as HTMLElement).getByLabelText(/^Acción de competencia/),
    ).toBeInTheDocument();
    expect(
      within(filaRequisito as HTMLElement).getByLabelText(/^Materia de competencia/),
    ).toBeInTheDocument();
    expect(
      within(filaRequisito as HTMLElement).queryByLabelText(/^Cargo/),
    ).not.toBeInTheDocument();
  });

  it("(f) QUALIFIED_MAJORITY muestra numerador y denominador", async () => {
    const usuario = userEvent.setup();
    renderPage(["/gobierno/contrataciones/politicas-comision/nueva"]);

    await screen.findByLabelText(/^Código/);
    await usuario.selectOptions(
      screen.getByLabelText(/^Tipo de quórum/) as HTMLSelectElement,
      "QUALIFIED_MAJORITY",
    );
    expect(screen.getByLabelText(/^Numerador del quórum/)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Denominador del quórum/)).toBeInTheDocument();
  });

  it("(g) 422 con fieldErrors.quorum muestra el mensaje en la sección Quórum", async () => {
    const usuario = userEvent.setup();
    apiFetchMock.mockImplementation((url: string, options?: { method?: string }) => {
      if (url.endsWith("/catalogo")) return Promise.resolve(catalogoFixture);
      if (url.endsWith("/opciones")) return Promise.resolve(opcionesFixture);
      if (options?.method === "POST") {
        // El mock de "@/api/client" sustituye ApiError por una clase con esta firma.
        const ErrorSimulado = ApiError as unknown as new (
          mensaje: string,
          estado: number,
          codigo: string,
          errores: Record<string, string[]>,
        ) => Error;
        const error = new ErrorSimulado(
          "Datos inválidos",
          422,
          "GOV_COMMISSION_POLICY_INVALID",
          { quorum: ["El quórum no es válido."] },
        );
        return Promise.reject(error);
      }
      return Promise.reject(new Error("URL no mockeada: " + url));
    });

    renderPage(["/gobierno/contrataciones/politicas-comision/nueva"]);

    await screen.findByLabelText(/^Código/);
    await usuario.type(screen.getByLabelText(/^Código/), "POL-001");
    await usuario.type(screen.getByLabelText(/^Nombre/), "Política");
    await usuario.selectOptions(screen.getByLabelText(/^Tipo de comisión/), "PERMANENTE");
    await usuario.type(screen.getByLabelText(/^Desde/), "2025-01-01");
    await usuario.selectOptions(screen.getByLabelText(/^Tipo de quórum/), "SIMPLE");
    await usuario.selectOptions(screen.getByLabelText(/^Tipo de mayoría/), "SIMPLE");
    await usuario.selectOptions(
      screen.getByLabelText(/^Base de la decisión/),
      "VOTOS_FAVORABLES",
    );

    await usuario.click(screen.getByRole("button", { name: "Guardar borrador" }));

    expect(await screen.findByText("El quórum no es válido.")).toBeInTheDocument();
  });

  it("(h) editar carga el detalle y hace PUT con ifMatch", async () => {
    const usuario = userEvent.setup();
    const detalle = {
      id: "pol-1",
      codigo: "POL-001",
      nombre: "Política Original",
      descripcion: null,
      tipo_comision: "PERMANENTE",
      aplica_apertura: true,
      aplica_recomendacion: false,
      base_normativa: "NINGUNA",
      fundamento: null,
      vigente_desde: "2025-01-01",
      vigente_hasta: null,
      min_principales: 3,
      max_principales: null,
      exige_impar: false,
      suplente_por_principal: false,
      exige_secretario: false,
      exige_suplente_secretario: false,
      exige_presidente: false,
      quorum: {
        tipo: "SIMPLE",
        cantidad: null,
        numerador: null,
        denominador: null,
      },
      decision: {
        tipo: "SIMPLE",
        cantidad: null,
        numerador: null,
        denominador: null,
        base: "VOTOS_FAVORABLES",
      },
      presidente_vota: false,
      presidente_dirimente: false,
      acto_requerido: false,
      acto_medio: null,
      requisitos: [],
      documentos: [],
      estado: "BORRADOR",
      version: 2,
      puede_editar: true,
    };

    apiFetchMock.mockImplementation((url: string, options?: { method?: string }) => {
      if (url.endsWith("/catalogo")) return Promise.resolve(catalogoFixture);
      if (url.endsWith("/opciones")) return Promise.resolve(opcionesFixture);
      if (typeof url === "string" && url.endsWith("/pol-1") && !options) {
        return Promise.resolve(detalle);
      }
      if (options?.method === "PUT") {
        return Promise.resolve({
          ...detalle,
          nombre: ((options as { body?: { nombre?: string } }).body ?? {}).nombre,
          version: 3,
        });
      }
      return Promise.reject(new Error("URL no mockeada: " + url));
    });

    renderPage(["/gobierno/contrataciones/politicas-comision/pol-1/editar"]);

    await screen.findByLabelText(/^Nombre/);
    await screen.findByDisplayValue("Política Original");
    await usuario.clear(screen.getByLabelText(/^Nombre/));
    await usuario.type(screen.getByLabelText(/^Nombre/), "Política Editada");

    await usuario.click(screen.getByRole("button", { name: "Guardar borrador" }));

    await waitFor(() => {
      const llamada = apiFetchMock.mock.calls.find(
        ([url, op]) =>
          typeof url === "string" &&
          url.endsWith("/pol-1") &&
          (op as { method?: string } | undefined)?.method === "PUT",
      );
      expect(llamada).toBeTruthy();
      expect(llamada?.[1]).toMatchObject({ ifMatch: "2" });
      const body = (llamada?.[1] as { body?: CuerpoEnviado } | undefined)?.body;
      expect(body?.nombre).toBe("Política Editada");
    });
  });

  it("(i) editar una política no BORRADOR muestra el aviso", async () => {
    const detalle = {
      id: "pol-2",
      codigo: "POL-002",
      nombre: "Política Activa",
      descripcion: null,
      tipo_comision: "PERMANENTE",
      aplica_apertura: true,
      aplica_recomendacion: false,
      base_normativa: "NINGUNA",
      fundamento: null,
      vigente_desde: "2025-01-01",
      vigente_hasta: null,
      min_principales: 3,
      max_principales: null,
      exige_impar: false,
      suplente_por_principal: false,
      exige_secretario: false,
      exige_suplente_secretario: false,
      exige_presidente: false,
      quorum: {
        tipo: "SIMPLE",
        cantidad: null,
        numerador: null,
        denominador: null,
      },
      decision: {
        tipo: "SIMPLE",
        cantidad: null,
        numerador: null,
        denominador: null,
        base: "VOTOS_FAVORABLES",
      },
      presidente_vota: false,
      presidente_dirimente: false,
      acto_requerido: false,
      acto_medio: null,
      requisitos: [],
      documentos: [],
      estado: "ACTIVA",
      version: 1,
      puede_editar: false,
    };

    apiFetchMock.mockImplementation((url: string) => {
      if (url.endsWith("/catalogo")) return Promise.resolve(catalogoFixture);
      if (url.endsWith("/opciones")) return Promise.resolve(opcionesFixture);
      if (url.endsWith("/pol-2")) return Promise.resolve(detalle);
      return Promise.reject(new Error("URL no mockeada: " + url));
    });

    renderPage(["/gobierno/contrataciones/politicas-comision/pol-2/editar"]);

    expect(
      await screen.findByText(
        "Esta política ya no es un borrador; cree una nueva versión desde su ficha.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText(/^Nombre/)).not.toBeInTheDocument();
  });
});
