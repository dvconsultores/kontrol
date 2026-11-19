import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/api/client";
import { PoliticaActaFormPage } from "./PoliticaActaFormPage";

const apiFetchMock = vi.fn();
const notifyMock = vi.fn();

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
  useCompany: () => ({ activeCompanyId: "c1", activeCompany: { id: "c1", legal_name: "Contenedor 1" } }),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: notifyMock }),
}));

type MockRequestInit = {
  method?: string;
  body?: unknown;
  ifMatch?: string;
};

const opcionesMock = {
  nivel_territorial: "NACIONAL",
  forma_organizativa: "ENTIDAD",
  patron_por_defecto: "ACTA-{ANIO}-{NUMERO:4}",
  actos: [{ id: "acto-1", etiqueta: "Resolución" }],
  unidades: [{ id: "u1", codigo: "U1", nombre: "Unidad 1" }],
  tipos_documento: [{ id: "doc-1", nombre: "Oficio" }],
  testigos_legales: {
    modalidad: "Redacción",
    testigos: 2,
    auditor_interno: false,
    fuente: "N34 art. 6",
  },
  plazos_legales: [
    { hito: "ELABORACION", valor: 5, unidad: "DIAS_HABILES", base: "N34", fuente: "N34 art. 10" },
    { hito: "REMISION_UAI", valor: 3, unidad: "DIAS_HABILES", base: "N34", fuente: "N34 art. 14" },
  ],
  supuestos: [
    {
      codigo: "N34_ART17",
      articulo: "17",
      titulo: "Entrega con testigos",
      sujeto: "Entrega",
      vinculo: "DECLARADO",
      niveles: null,
      ambitos: ["ENTE", "UNIDAD"],
      nota: null,
      anexos: [{ codigo: "ANEXO-1", titulo: "Acta con testigos", obligatorio: true, generable: true }],
      declarable: true,
      motivo_no_declarable: null,
    },
    {
      codigo: "N34_ART16",
      articulo: "16",
      titulo: "Supuesto no disponible",
      sujeto: "Entrega",
      vinculo: "DECLARADO",
      niveles: ["PROVINCIAL"],
      ambitos: ["ENTE"],
      nota: null,
      anexos: [],
      declarable: false,
      motivo_no_declarable: "Requiere nivel provincial",
    },
  ],
};

const detalleMock = {
  id: "p1",
  codigo: "POL-1",
  numero_version: 2,
  nombre: "Política 1",
  estado: "BORRADOR",
  estado_etiqueta: "Borrador",
  vigente_desde: "2025-01-01",
  vigente_hasta: null,
  total_vinculos: 1,
  total_requisitos: 1,
  version: 7,
  descripcion: "Descripción",
  fundamento: "Fundamento",
  act_id: null,
  numeracion_patron: "ACTA-{ANIO}-{NUMERO:2}",
  testigos_en_entrega: 1,
  cargo_maxima_autoridad_codigo: "MA",
  version_anterior_id: null,
  activada_en: null,
  cerrada_en: null,
  motivo_cierre: null,
  vinculos: [{ supuesto: "N34_ART17", alcance: "ENTE", unit_id: null }],
  requisitos: [
    {
      codigo: "R1",
      titulo: "Requisito 1",
      evidencia: "DOCUMENTO",
      obligatorio: true,
      ambito: "TODAS",
      supuesto: null,
      document_type_id: "doc-1",
      fuente: "N34",
    },
  ],
  plazos: [{ hito: "ELABORACION", valor: 5, unidad: "DIAS_HABILES", fuente: "RFC" }],
  regla_ente: null,
  historia: [],
  versiones: [],
  actas_que_la_usan: 0,
  acciones: { editar: true, activar: false, cerrar: false, nueva_version: false },
};

function renderPage(url: string): ReturnType<typeof render> {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[url]}>
        <Routes>
          <Route path="/gobierno/actas-entrega/politicas/nueva" element={<PoliticaActaFormPage />} />
          <Route path="/gobierno/actas-entrega/politicas/:politicaId/editar" element={<PoliticaActaFormPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function mockOpciones(): void {
  apiFetchMock.mockImplementation((url: string) => {
    if (url === "/gobierno/actas-entrega/politicas/opciones") {
      return Promise.resolve(opcionesMock);
    }
    return Promise.resolve(null);
  });
}

beforeEach(() => {
  apiFetchMock.mockReset();
  notifyMock.mockReset();
  capacidades = new Set(["gobierno_actas:configure"]);
});

describe("PoliticaActaFormPage", () => {
  it("FPF-01 alta: crea una política con supuesto, requisito y plazo", async () => {
    mockOpciones();
    const usuario = userEvent.setup();
    renderPage("/gobierno/actas-entrega/politicas/nueva");

    await screen.findByRole("heading", { name: "Nueva política de actas" });

    const codigo = await screen.findByLabelText(/^Código(?! del)/);
    const nombre = await screen.findByLabelText(/^Nombre/);
    const vigenteDesde = await screen.findByLabelText(/^Vigente desde/);

    await usuario.type(codigo, "POL-2");
    await usuario.type(nombre, "Política 2");
    await usuario.type(vigenteDesde, "2025-05-01");

    await usuario.click(screen.getByRole("button", { name: "Añadir supuesto" }));
    await screen.findByLabelText("Supuesto 1");
    await userEvent.selectOptions(screen.getByLabelText("Supuesto 1"), "N34_ART17");
    await userEvent.selectOptions(screen.getByLabelText("Alcance 1"), "ENTE");

    await usuario.click(screen.getByRole("button", { name: "Añadir requisito" }));
    await screen.findByLabelText("Código del requisito 1");
    await usuario.type(screen.getByLabelText("Código del requisito 1"), "P1");
    await usuario.type(screen.getByLabelText("Requisito 1"), "Requisito P1");
    await userEvent.selectOptions(screen.getByLabelText("Evidencia 1"), "DECLARACION");

    await usuario.click(screen.getByRole("button", { name: "Añadir plazo" }));
    await screen.findByLabelText("Hito 1");
    await userEvent.selectOptions(screen.getByLabelText("Hito 1"), "REMISION_UAI");
    await userEvent.type(screen.getByLabelText("Días 1"), "2");
    await userEvent.selectOptions(screen.getByLabelText("Unidad 1"), "DIAS_CONTINUOS");

    apiFetchMock.mockImplementationOnce((url: string, init?: MockRequestInit) => {
      if (url === "/gobierno/actas-entrega/politicas" && init?.method === "POST") {
        const body = JSON.parse(String(init.body));
        expect(body.vinculos).toEqual([{ supuesto: "N34_ART17", alcance: "ENTE", unit_id: null }]);
        expect(body.requisitos[0].evidencia).toBe("DECLARACION");
        expect(body.requisitos[0].document_type_id).toBeNull();
        expect(body.plazos).toEqual([{ hito: "REMISION_UAI", valor: 2, unidad: "DIAS_CONTINUOS", fuente: null }]);
        return Promise.resolve({ ...detalleMock, id: "nueva-1" });
      }
      return Promise.resolve(null);
    });

    await usuario.click(screen.getByRole("button", { name: "Guardar borrador" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/actas-entrega/politicas",
        expect.objectContaining({ method: "POST" }),
      );
    });
  });

  it("FPF-02 el catálogo muestra N34_ART16 como no aplicable y no lo ofrece en Supuesto", async () => {
    mockOpciones();
    const usuario = userEvent.setup();
    renderPage("/gobierno/actas-entrega/politicas/nueva");

    await screen.findByRole("heading", { name: "Nueva política de actas" });
    await screen.findByText(/N34 art\. 16 · Supuesto no disponible/);
    expect(screen.getByText("N34 art. 16 · Supuesto no disponible — no aplica: Requiere nivel provincial")).toBeTruthy();

    await usuario.click(screen.getByRole("button", { name: "Añadir supuesto" }));
    const selectSupuesto = await screen.findByLabelText("Supuesto 1");
    const options = Array.from(selectSupuesto.querySelectorAll("option")).map(
      (opcion) => (opcion as HTMLOptionElement).value,
    );

    expect(options.includes("N34_ART16")).toBe(false);
    expect(options.includes("N34_ART17")).toBe(true);
  });

  it("FPF-03 error 422 en plazo se muestra junto al campo Días 1", async () => {
    mockOpciones();
    const usuario = userEvent.setup();
    renderPage("/gobierno/actas-entrega/politicas/nueva");

    await screen.findByRole("heading", { name: "Nueva política de actas" });

    await usuario.type(await screen.findByLabelText(/^Código(?! del)/), "POL-3");
    await usuario.type(screen.getByLabelText(/^Nombre/), "Política 3");
    await userEvent.type(screen.getByLabelText(/^Vigente desde/), "2025-05-01");

    await usuario.click(screen.getByRole("button", { name: "Añadir plazo" }));
    await userEvent.selectOptions(await screen.findByLabelText("Hito 1"), "REMISION_UAI");
    await userEvent.type(screen.getByLabelText("Días 1"), "5");
    await userEvent.selectOptions(screen.getByLabelText("Unidad 1"), "DIAS_HABILES");

    apiFetchMock.mockImplementationOnce((url: string, init?: MockRequestInit) => {
      if (url === "/gobierno/actas-entrega/politicas" && init?.method === "POST") {
        return Promise.reject(
          new ApiError(422, {
            code: "GOV_HANDOVER_POLICY_INVALID",
            message: "La política no es válida",
            field_errors: {
              "plazos.0.valor": ["El plazo interno no puede superar el legal."],
            },
          }),
        );
      }
      return Promise.resolve(null);
    });

    await usuario.click(screen.getByRole("button", { name: "Guardar borrador" }));

    await waitFor(() => {
      expect(screen.getByText("El plazo interno no puede superar el legal.")).toBeTruthy();
    });
  });

  it("FPF-04 edición: carga detalle, deshabilita Código y guarda con ifMatch", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/actas-entrega/politicas/opciones") {
        return Promise.resolve(opcionesMock);
      }
      if (url === "/gobierno/actas-entrega/politicas/p1") {
        return Promise.resolve(detalleMock);
      }
      return Promise.resolve(null);
    });

    const usuario = userEvent.setup();
    renderPage("/gobierno/actas-entrega/politicas/p1/editar");

    await screen.findByRole("heading", { name: "Editar política POL-1 v2" });

    const codigo = await screen.findByLabelText(/^Código(?! del)/);
    expect(codigo.hasAttribute("disabled")).toBe(true);

    apiFetchMock.mockImplementationOnce((url: string, init?: MockRequestInit) => {
      if (url === "/gobierno/actas-entrega/politicas/p1" && init?.method === "PUT") {
        expect(init.ifMatch).toBe("7");
        return Promise.resolve(detalleMock);
      }
      return Promise.resolve(null);
    });

    await usuario.click(screen.getByRole("button", { name: "Guardar borrador" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/actas-entrega/politicas/p1",
        expect.objectContaining({ method: "PUT", ifMatch: "7" }),
      );
    });
  });

  it("FPF-05 vista previa llama a la API y muestra ejemplos", async () => {
    mockOpciones();
    const usuario = userEvent.setup();
    renderPage("/gobierno/actas-entrega/politicas/nueva");

    await screen.findByRole("heading", { name: "Nueva política de actas" });

    const patron = await screen.findByLabelText(/^Patrón de numeración/);
    fireEvent.change(patron, { target: { value: "AA-{ANIO}-{NUMERO:2}" } });

    apiFetchMock.mockImplementationOnce((url: string) => {
      if (decodeURIComponent(url).includes("/gobierno/actas-entrega/politicas/numeracion/vista-previa?patron=AA-{ANIO}-{NUMERO:2}")) {
        return Promise.resolve({ valido: true, motivo: null, ejemplos: ["AA-2025-01", "AA-2025-02"] });
      }
      return Promise.resolve(null);
    });

    await usuario.click(screen.getByRole("button", { name: "Vista previa" }));

    await waitFor(() => {
      expect(screen.getByText("AA-2025-01")).toBeTruthy();
      expect(screen.getByText("AA-2025-02")).toBeTruthy();
    });
  });

  it("FPF-06 sin configure muestra el ErrorState", async () => {
    capacidades = new Set();
    renderPage("/gobierno/actas-entrega/politicas/nueva");

    await screen.findByText("No tiene permiso para configurar políticas de actas.");
    expect(screen.getByText("Sin acceso")).toBeTruthy();
  });
});
