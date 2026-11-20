import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PoliticasRetencionPage } from "./PoliticasRetencionPage";
import { PoliticaRetencionPage } from "./PoliticaRetencionPage";
import type { PoliticaRetencion } from "./api";

const apiFetchMock = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  ApiError: (await original<typeof import("@/api/client")>()).ApiError,
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
  useCompany: () => ({ activeCompanyId: "c1", activeCompany: { id: "c1", legal_name: "Ente 1" } }),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: vi.fn() }),
}));

const API_RETENCIONES = "/gobierno/tesoreria/retenciones";

function crearPolitica(overrides: Partial<PoliticaRetencion> = {}): PoliticaRetencion {
  return {
    id: "pol-1",
    codigo: "RET-IVA",
    numero_version: 1,
    version_anterior_id: null,
    nombre: "Retención de IVA",
    descripcion: null,
    moneda: "VES",
    tipo_regla: "INSTITUTIONAL_POLICY",
    estado_verificacion: "PENDING_PIN",
    fuente_descripcion: null,
    fuente_referencia: null,
    fuente_documento_id: null,
    act_id: null,
    aprobador_competencia_accion: null,
    aprobador_competencia_materia: null,
    permite_ajuste: true,
    redondeo_decimales: 2,
    redondeo_modo: "HALF_UP",
    vigente_desde: null,
    vigente_hasta: null,
    fundamento: null,
    estado: "BORRADOR",
    reglas_count: 0,
    activada_en: null,
    cerrada_en: null,
    motivo_cierre: null,
    version: 0,
    reglas: [],
    ...overrides,
  };
}

function configurarApiMock({
  politicas = [],
  catalogoConcepto = [],
  catalogoCondicion = [],
  configuracion = null,
  politicaId = null,
  historia = [],
}: {
  politicas?: PoliticaRetencion[];
  catalogoConcepto?: unknown[];
  catalogoCondicion?: unknown[];
  configuracion?: { id: string; patron: string; version: number; ejemplo: string | null } | null;
  politicaId?: string | null;
  historia?: unknown[];
} = {}) {
  apiFetchMock.mockImplementation(async (ruta: string, opciones?: { method?: string; body?: unknown }) => {
    const metodo = opciones?.method ?? "GET";

    // Lista de políticas
    if (ruta === `${API_RETENCIONES}/politicas` && metodo === "GET") {
      return politicas;
    }

    // Catálogo conceptos
    if (ruta === `${API_RETENCIONES}/catalogo?tipo=CONCEPTO` && metodo === "GET") {
      return catalogoConcepto;
    }

    // Catálogo condiciones
    if (ruta === `${API_RETENCIONES}/catalogo?tipo=CONDICION` && metodo === "GET") {
      return catalogoCondicion;
    }

    // Configuración
    if (ruta === `${API_RETENCIONES}/configuracion` && metodo === "GET") {
      return configuracion;
    }

    if (ruta === `${API_RETENCIONES}/configuracion` && metodo === "PUT") {
      return { ...configuracion, patron: (opciones?.body as { patron?: string })?.patron ?? "" };
    }

    // Errores de guardado específicos por política
    if (ruta === `${API_RETENCIONES}/politicas/pol-err` && metodo === "PUT") {
      const { ApiError } = await import("@/api/client");
      throw new ApiError(422, {
        code: "VALIDATION_ERROR",
        message: "Error de validación",
        field_errors: { "reglas.0.tasa": ["La tasa debe ser mayor que cero"] },
      });
    }

    // POST catálogo
    if (ruta === `${API_RETENCIONES}/catalogo` && metodo === "POST") {
      return { id: "cat-1", ...(opciones?.body as object) };
    }

    // Política individual
    if (politicaId && ruta === `${API_RETENCIONES}/politicas/${politicaId}` && metodo === "GET") {
      return politicaId ? politicas.find((p) => p.id === politicaId) : undefined;
    }

    if (politicaId && ruta === `${API_RETENCIONES}/politicas/${politicaId}` && metodo === "PUT") {
      return politicaId ? politicas.find((p) => p.id === politicaId) : undefined;
    }

    // POST políticas
    if (ruta === `${API_RETENCIONES}/politicas` && metodo === "POST") {
      return crearPolitica({ id: "pol-nueva", ...(opciones?.body as Partial<PoliticaRetencion>) });
    }

    // Acciones
    if (politicaId && ruta === `${API_RETENCIONES}/politicas/${politicaId}/activar` && metodo === "POST") {
      return { ...politicas.find((p) => p.id === politicaId), estado: "VIGENTE" };
    }

    if (politicaId && ruta === `${API_RETENCIONES}/politicas/${politicaId}/cerrar` && metodo === "POST") {
      return { ...politicas.find((p) => p.id === politicaId), estado: "CERRADA" };
    }

    // Historia
    if (politicaId && ruta === `${API_RETENCIONES}/politicas/${politicaId}/historia` && metodo === "GET") {
      return historia;
    }

    throw new Error(`Ruta no mockeada: ${metodo} ${ruta}`);
  });
}

function renderLista() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={["/gobierno/tesoreria/politicas-retencion"]}>
        <Routes>
          <Route path="/gobierno/tesoreria/politicas-retencion" element={<PoliticasRetencionPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function renderFicha(ruta = "/gobierno/tesoreria/politicas-retencion/nueva") {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={[ruta]}>
        <Routes>
          <Route path="/gobierno/tesoreria/politicas-retencion/nueva" element={<PoliticaRetencionPage />} />
          <Route path="/gobierno/tesoreria/politicas-retencion/:politicaId" element={<PoliticaRetencionPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("PoliticasRetencion", () => {
  beforeEach(() => {
    apiFetchMock.mockClear();
    capacidades = new Set(["gobierno_retenciones:view", "gobierno_retenciones:manage", "gobierno_retenciones:policy", "gobierno_retenciones:approve", "gobierno_retenciones:cancel"]);
  });

  afterEach(() => {
    cleanup();
  });

  it("1. lista vacía muestra el estado vacío", async () => {
    configurarApiMock();
    renderLista();

    expect(await screen.findByText("Aún no hay políticas de retención")).toBeInTheDocument();
  });

  it("2. lista con dos políticas muestra código, versión y estado en la tabla", async () => {
    configurarApiMock({
      politicas: [
        crearPolitica({ id: "p1", codigo: "RET-IVA", numero_version: 3, estado: "BORRADOR" }),
        crearPolitica({ id: "p2", codigo: "RET-ISLR", numero_version: 1, estado: "VIGENTE" }),
      ],
    });
    renderLista();

    const tabla = await screen.findByRole("table", { name: "Políticas de retención" });
    expect(within(tabla).getByText("RET-IVA")).toBeInTheDocument();
    expect(within(tabla).getByText("RET-ISLR")).toBeInTheDocument();
    expect(within(tabla).getByText("Borrador")).toBeInTheDocument();
    expect(within(tabla).getByText("Vigente")).toBeInTheDocument();
  });

  it("3. sin permiso view muestra 'Sin acceso' y no llama a la API de políticas", async () => {
    capacidades = new Set();
    configurarApiMock();
    renderLista();

    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalledWith(
      `${API_RETENCIONES}/politicas`,
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("4. alta de concepto (manage) llama POST catalogo con {tipo:'CONCEPTO', codigo, nombre, clase}", async () => {
    configurarApiMock({
      catalogoConcepto: [],
      catalogoCondicion: [],
      configuracion: { id: "cfg-1", patron: "", version: 0, ejemplo: null },
    });
    const { container } = renderLista();

    await screen.findByRole("heading", { name: "Catálogo del ente" });

    const campoCodigo = container.querySelector("#concepto-codigo") as HTMLInputElement;
    const campoNombre = container.querySelector("#concepto-nombre") as HTMLInputElement;
    const campoDescripcion = container.querySelector("#concepto-descripcion") as HTMLInputElement;
    const campoClase = container.querySelector("#concepto-clase") as HTMLSelectElement;

    await userEvent.type(campoCodigo, "RET-003");
    await userEvent.type(campoNombre, "Retención municipal");
    await userEvent.type(campoDescripcion, "Impuesto municipal");
    await userEvent.selectOptions(campoClase, "TRIBUTARIA");

    await userEvent.click(screen.getByRole("button", { name: "Añadir concepto" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        `${API_RETENCIONES}/catalogo`,
        expect.objectContaining({
          method: "POST",
          body: expect.objectContaining({
            tipo: "CONCEPTO",
            codigo: "RET-003",
            nombre: "Retención municipal",
            descripcion: "Impuesto municipal",
            clase: "TRIBUTARIA",
          }),
        }),
      );
    });
  });

  it("5. guardar patrón llama PUT configuracion con ifMatch de la versión y body {patron}", async () => {
    configurarApiMock({
      catalogoConcepto: [],
      catalogoCondicion: [],
      configuracion: { id: "cfg-1", patron: "ABC-###", version: 4, ejemplo: "ABC-001" },
    });
    renderLista();

    const campoPatron = await screen.findByLabelText("Patrón");
    await waitFor(() => expect(campoPatron).toHaveValue("ABC-###"));
    await userEvent.clear(campoPatron);
    await userEvent.type(campoPatron, "XYZ-###");

    await userEvent.click(screen.getByRole("button", { name: "Guardar patrón" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        `${API_RETENCIONES}/configuracion`,
        expect.objectContaining({
          method: "PUT",
          ifMatch: "4",
          body: { patron: "XYZ-###" },
        }),
      );
    });
  });

  it("6. ficha nueva: 'Porcentaje de la base' aparece solo con 'Porcentaje del bruto' y 'Monto del umbral' solo con 'Monto fijo'", async () => {
    configurarApiMock({
      catalogoConcepto: [
        { id: "c1", tipo: "CONCEPTO", codigo: "IVA", nombre: "IVA", descripcion: null, clase: "TRIBUTARIA", serie_comprobante: null, estado: "ACTIVO", version: 1 },
      ],
      catalogoCondicion: [],
      configuracion: { id: "cfg-1", patron: "", version: 0, ejemplo: null },
    });
    renderFicha();

    await userEvent.click(await screen.findByRole("button", { name: "Añadir regla" }));

    const campoBase = await screen.findByLabelText("Base");
    expect(screen.queryByLabelText("Porcentaje de la base")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Monto del umbral")).not.toBeInTheDocument();

    await userEvent.selectOptions(campoBase, "PORCENTAJE_DEL_BRUTO");
    expect(await screen.findByLabelText("Porcentaje de la base")).toBeInTheDocument();

    await userEvent.selectOptions(screen.getByLabelText("Umbral"), "MONTO");
    expect(await screen.findByLabelText("Monto del umbral")).toBeInTheDocument();
  });

  it("7. 'Múltiplo de una tasa oficial' deshabilitado si la moneda no es VES", async () => {
    configurarApiMock({
      catalogoConcepto: [],
      catalogoCondicion: [],
      configuracion: { id: "cfg-1", patron: "", version: 0, ejemplo: null },
    });
    renderFicha();

    await userEvent.click(await screen.findByRole("button", { name: "Añadir regla" }));

    await userEvent.selectOptions(await screen.findByLabelText("Moneda"), "USD");
    const campoUmbral = screen.getByLabelText("Umbral");
    const opcionMultiplo = within(campoUmbral).getByRole("option", { name: "Múltiplo de una tasa oficial" }) as HTMLOptionElement;
    expect(opcionMultiplo.disabled).toBe(true);
  });

  it("8. ficha existente en BORRADOR carga los datos de la política en el formulario", async () => {
    const politica = crearPolitica({ id: "pol-x", nombre: "Retención de IVA v2", moneda: "USD" });
    configurarApiMock({
      politicas: [politica],
      politicaId: "pol-x",
      catalogoConcepto: [],
      catalogoCondicion: [],
      configuracion: { id: "cfg-1", patron: "", version: 0, ejemplo: null },
    });
    renderFicha("/gobierno/tesoreria/politicas-retencion/pol-x");

    const campoNombre = await screen.findByLabelText("Nombre");
    await waitFor(() => {
      expect(campoNombre).toHaveValue("Retención de IVA v2");
    });
    expect(screen.getByLabelText("Moneda")).toHaveValue("USD");
  });

  it("9. activar con fundamento corto muestra alerta y NO llama a /activar; con fundamento válido llama POST /activar", async () => {
    const politica = crearPolitica({ id: "pol-act", estado: "BORRADOR" });
    configurarApiMock({
      politicas: [politica],
      politicaId: "pol-act",
      catalogoConcepto: [],
      catalogoCondicion: [],
      configuracion: { id: "cfg-1", patron: "", version: 0, ejemplo: null },
    });
    renderFicha("/gobierno/tesoreria/politicas-retencion/pol-act");

    const botonActivar = await screen.findByRole("button", { name: "Activar" });
    await userEvent.click(botonActivar);

    const dialogo = await screen.findByRole("dialog", { name: "Activar política" });
    const campoFundamento = await within(dialogo).findByLabelText("Fundamento");
    await userEvent.type(campoFundamento, "corto");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Activar" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/fundamento debe tener al menos 20 caracteres/i);
    });
    expect(apiFetchMock).not.toHaveBeenCalledWith(
      `${API_RETENCIONES}/politicas/pol-act/activar`,
      expect.any(Object),
    );

    await userEvent.clear(campoFundamento);
    await userEvent.type(campoFundamento, "Fundamento válido con más de veinte caracteres");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Activar" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        `${API_RETENCIONES}/politicas/pol-act/activar`,
        expect.objectContaining({
          method: "POST",
          ifMatch: "0",
          body: { fundamento: "Fundamento válido con más de veinte caracteres" },
        }),
      );
    });
  });

  it("10. política VIGENTE: campos de solo lectura y botón 'Cerrar' visible con permiso policy", async () => {
    const politica = crearPolitica({ id: "pol-vig", estado: "VIGENTE", vigente_desde: "2025-01-01", fundamento: "Activada legalmente" });
    configurarApiMock({
      politicas: [politica],
      politicaId: "pol-vig",
      catalogoConcepto: [],
      catalogoCondicion: [],
      configuracion: { id: "cfg-1", patron: "", version: 0, ejemplo: null },
    });
    renderFicha("/gobierno/tesoreria/politicas-retencion/pol-vig");

    const campoNombre = await screen.findByLabelText("Nombre");
    await waitFor(() => {
      expect(campoNombre).toBeDisabled();
    });
    expect(screen.getByLabelText("Moneda")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Cerrar" })).toBeInTheDocument();
  });

  it("11. historia se muestra en la tabla 'Historia de la política'", async () => {
    const politica = crearPolitica({ id: "pol-h", numero_version: 2 });
    configurarApiMock({
      politicas: [politica],
      politicaId: "pol-h",
      catalogoConcepto: [],
      catalogoCondicion: [],
      configuracion: { id: "cfg-1", patron: "", version: 0, ejemplo: null },
      historia: [
        { id: "h1", evento: "ACTIVADA", numero_version: 1, actor_id: "a1", created_at: "2025-01-01T00:00:00Z", instantanea: null },
        { id: "h2", evento: "NUEVA_VERSION", numero_version: 2, actor_id: "a1", created_at: "2025-02-01T00:00:00Z", instantanea: null },
      ],
    });
    renderFicha("/gobierno/tesoreria/politicas-retencion/pol-h");

    const tablaHistoria = await screen.findByRole("table", { name: "Historia de la política" });
    expect(within(tablaHistoria).getByText("ACTIVADA")).toBeInTheDocument();
    expect(within(tablaHistoria).getByText("NUEVA_VERSION")).toBeInTheDocument();
  });

  it("12. error 422 con fieldErrors {'reglas.0.tasa': [...]} se muestra junto a la regla", async () => {
    const politica = crearPolitica({
      id: "pol-err",
      reglas: [
        {
          id: "regla-1",
          orden: 1,
          concept_id: "c1",
          base_tipo: "MONTO_BRUTO",
          base_porcentaje: null,
          tasa: "15",
          umbral_tipo: "NINGUNO",
          umbral_monto: null,
          umbral_multiplo: null,
          umbral_moneda_tasa: null,
          sustraendo: null,
          tope: null,
          condiciones_exigidas: [],
          exclusiones: [],
          tipos_persona: null,
          exige_comprobante: false,
        },
      ],
    });
    configurarApiMock({
      politicas: [politica],
      politicaId: "pol-err",
      catalogoConcepto: [],
      catalogoCondicion: [],
      configuracion: { id: "cfg-1", patron: "", version: 0, ejemplo: null },
    });

    renderFicha("/gobierno/tesoreria/politicas-retencion/pol-err");

    await userEvent.click(await screen.findByRole("button", { name: "Guardar política" }));

    await waitFor(() => {
      expect(screen.getByText("La tasa debe ser mayor que cero")).toBeInTheDocument();
    });
  });
});
