import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/api/client";
import { SupervisionContrato } from "./SupervisionContrato";

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

function supervisionSinVigente(): import("./api").Supervision {
  return {
    contrato: { id: "c1", codigo: "CON-001", estado: "FORMALIZADO", fecha_formalizacion: "2025-01-01", fecha_fin: null },
    vigente: null,
    programada: null,
    ultima_id: null,
    historia: [],
    puede_designar: true,
  };
}

function supervisionConVigente(): import("./api").Supervision {
  return {
    contrato: { id: "c1", codigo: "CON-001", estado: "FORMALIZADO", fecha_formalizacion: "2025-01-01", fecha_fin: null },
    vigente: {
      id: "d2",
      referencia: "SUP-02",
      numero: 2,
      estado: "VIGENTE",
      estado_etiqueta: "Vigente",
      situacion: "EN_EJERCICIO",
      situacion_etiqueta: "En ejercicio",
      funcionario: { id: "f2", nombre: "María López", documento: "22222222" },
      asignacion_id: "a2",
      figura: "SUPERVISOR",
      figura_etiqueta: "Supervisor",
      cargo: { id: "c2", codigo: "DIR", nombre: "Director" },
      unidad: { id: "u2", nombre: "Unidad de Obras" },
      acto: { id: "ac2", etiqueta: "Resolución 2", emisor_cargo: "Secretaría" },
      desde: "2025-06-01",
      hasta: null,
      motivo: "Reorganización",
      sustituye: "d1",
      registrado_en: "2025-05-28T10:00:00Z",
    },
    programada: null,
    ultima_id: "d2",
    historia: [
      {
        id: "d1",
        referencia: "SUP-01",
        numero: 1,
        estado: "SUSTITUIDA",
        estado_etiqueta: "Sustituida",
        situacion: "CONCLUIDA",
        situacion_etiqueta: "Concluida",
        funcionario: { id: "f1", nombre: "Juan Pérez", documento: "11111111" },
        asignacion_id: "a1",
        figura: "RESPONSABLE",
        figura_etiqueta: "Responsable",
        cargo: { id: "c1", codigo: "JEFE", nombre: "Jefe" },
        unidad: { id: "u1", nombre: "Unidad de Compras" },
        acto: { id: "ac1", etiqueta: "Resolución 1", emisor_cargo: "Secretaría" },
        desde: "2025-01-01",
        hasta: "2025-05-31",
        motivo: null,
        sustituye: null,
        registrado_en: "2025-01-02T10:00:00Z",
      },
      {
        id: "d2",
        referencia: "SUP-02",
        numero: 2,
        estado: "VIGENTE",
        estado_etiqueta: "Vigente",
        situacion: "EN_EJERCICIO",
        situacion_etiqueta: "En ejercicio",
        funcionario: { id: "f2", nombre: "María López", documento: "22222222" },
        asignacion_id: "a2",
        figura: "SUPERVISOR",
        figura_etiqueta: "Supervisor",
        cargo: { id: "c2", codigo: "DIR", nombre: "Director" },
        unidad: { id: "u2", nombre: "Unidad de Obras" },
        acto: { id: "ac2", etiqueta: "Resolución 2", emisor_cargo: "Secretaría" },
        desde: "2025-06-01",
        hasta: null,
        motivo: "Reorganización",
        sustituye: "d1",
        registrado_en: "2025-05-28T10:00:00Z",
      },
    ],
    puede_designar: true,
  };
}

const opcionesConDatos: import("./api").OpcionesSupervision = {
  fecha: "2025-07-01",
  vigente_id: null,
  funcionarios: [
    {
      id: "f1",
      nombre: "Juan Pérez",
      documento: "11111111",
      ocupaciones: [
        { asignacion_id: "a1", figura_etiqueta: "Supervisor", cargo_id: "c1", cargo: "Jefe", unidad_id: "u1", unidad: "Unidad de Compras" },
      ],
    },
  ],
  actos: [
    { id: "ac1", etiqueta: "Resolución 1", emisor_cargo: "Secretaría", fecha: "2025-07-01", fecha_eficacia: "2025-07-01" },
  ],
};

function crearQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
}

function renderComponent() {
  const queryClient = crearQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <SupervisionContrato contratoId="c1" />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiFetchMock.mockReset();
  capacidades = new Set<string>();
});

describe("SupervisionContrato", () => {
  it("a: sin vigente muestra el estado vacío y sin permiso no ofrece nueva designación", async () => {
    apiFetchMock.mockResolvedValue(supervisionSinVigente());
    renderComponent();

    await screen.findByText("Sin supervisor designado");
    expect(screen.queryByRole("button", { name: "Nueva designación" })).not.toBeInTheDocument();
  });

  it("b: con vigente muestra los datos y el historial con SUP-01 y SUP-02", async () => {
    apiFetchMock.mockResolvedValue(supervisionConVigente());
    renderComponent();

    const vigente = await screen.findByRole("heading", { name: "Supervisor vigente" });
    expect(vigente).toBeInTheDocument();

    const historial = screen.getByRole("region", { name: "Historial de supervisores" });
    expect(within(historial).getByText("SUP-01 · Sustituida")).toBeInTheDocument();
    expect(within(historial).getByText("SUP-02 · Vigente")).toBeInTheDocument();
    expect(within(historial).getByText("Concluida · Sustituida")).toBeInTheDocument();
    expect(screen.getAllByText("María López · 22222222").length).toBe(2);
  });

  it("c: alta inicial asigna ocupación única y registra con motivo null y sustituye_id null", async () => {
    const user = userEvent.setup();
    capacidades = new Set(["gobierno_contratos:assign_supervisor"]);
    apiFetchMock.mockImplementation((ruta: string, opciones?: { method?: string; body?: unknown }) => {
      if (ruta === "/gobierno/contratos/c1/supervision") {
        return Promise.resolve(supervisionSinVigente());
      }
      if (ruta.startsWith("/gobierno/contratos/c1/supervision/opciones")) {
        return Promise.resolve(opcionesConDatos);
      }
      if (ruta === "/gobierno/contratos/c1/supervision/designaciones" && opciones?.method === "POST") {
        return Promise.resolve({
          ...supervisionSinVigente(),
          vigente: {
            id: "d3",
            referencia: "SUP-01",
            numero: 1,
            estado: "VIGENTE",
            estado_etiqueta: "Vigente",
            situacion: "EN_EJERCICIO",
            situacion_etiqueta: "En ejercicio",
            funcionario: { id: "f1", nombre: "Juan Pérez", documento: "11111111" },
            asignacion_id: "a1",
            figura: "SUPERVISOR",
            figura_etiqueta: "Supervisor",
            cargo: { id: "c1", codigo: "JEFE", nombre: "Jefe" },
            unidad: { id: "u1", nombre: "Unidad de Compras" },
            acto: { id: "ac1", etiqueta: "Resolución 1", emisor_cargo: "Secretaría" },
            desde: "2025-07-01",
            hasta: null,
            motivo: null,
            sustituye: null,
            registrado_en: "2025-07-01T10:00:00Z",
          },
          programada: null,
          ultima_id: "d3",
          historia: [],
        });
      }
      return Promise.reject(new Error("Ruta inesperada"));
    });
    renderComponent();

    await screen.findByRole("button", { name: "Nueva designación" });
    await user.click(screen.getByRole("button", { name: "Nueva designación" }));

    const funcionarioSelect = await screen.findByRole("combobox", { name: "Funcionario (obligatorio)" });
    await screen.findByRole("option", { name: "Juan Pérez · 11111111" });
    await user.selectOptions(funcionarioSelect, "f1");

    expect(screen.getByRole("combobox", { name: "Ocupación (obligatorio)" })).toHaveValue("a1");
    expect(screen.getByText("Cargo: Jefe · Unidad: Unidad de Compras")).toBeInTheDocument();

    const actoSelect = screen.getByRole("combobox", { name: "Acto de designación (obligatorio)" });
    await user.selectOptions(actoSelect, "ac1");

    const fechaInput = screen.getByLabelText(/Fecha efectiva/) as HTMLInputElement;
    const desde = fechaInput.value;

    await user.click(screen.getByRole("button", { name: "Formalizar designación" }));
    await user.click(screen.getByRole("button", { name: "Formalizar" }));

    await waitFor(() => {
      const llamada = apiFetchMock.mock.calls.find(
        ([ruta]) => ruta === "/gobierno/contratos/c1/supervision/designaciones",
      ) as [string, { body: Record<string, unknown> }] | undefined;
      expect(llamada).toBeDefined();
      expect(llamada?.[1].body).toMatchObject({
        funcionario_id: "f1",
        asignacion_id: "a1",
        acto_id: "ac1",
        motivo: null,
        sustituye_id: null,
      });
      expect(llamada?.[1].body.desde).toBe(desde);
    });

    await screen.findByText("Designación SUP-01 registrada.");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Nueva designación" })).toBeInTheDocument();
  });

  it("d: sustitución sin motivo deshabilita el botón y con motivo incluye sustituye_id", async () => {
    const user = userEvent.setup();
    capacidades = new Set(["gobierno_contratos:assign_supervisor"]);
    apiFetchMock.mockImplementation((ruta: string, opciones?: { method?: string; body?: unknown }) => {
      if (ruta === "/gobierno/contratos/c1/supervision") {
        return Promise.resolve(supervisionConVigente());
      }
      if (ruta.startsWith("/gobierno/contratos/c1/supervision/opciones")) {
        return Promise.resolve(opcionesConDatos);
      }
      if (ruta === "/gobierno/contratos/c1/supervision/designaciones" && opciones?.method === "POST") {
        return Promise.resolve(supervisionConVigente());
      }
      return Promise.reject(new Error("Ruta inesperada"));
    });
    renderComponent();

    await screen.findByRole("button", { name: "Sustituir supervisor" });
    await user.click(screen.getByRole("button", { name: "Sustituir supervisor" }));

    const funcionarioSelect = await screen.findByRole("combobox", { name: "Funcionario (obligatorio)" });
    await screen.findByRole("option", { name: "Juan Pérez · 11111111" });
    await user.selectOptions(funcionarioSelect, "f1");
    await user.selectOptions(screen.getByRole("combobox", { name: "Acto de designación (obligatorio)" }), "ac1");

    expect(screen.getByRole("button", { name: "Formalizar designación" })).toBeDisabled();

    await user.type(screen.getByRole("textbox", { name: "Motivo del cambio (obligatorio)" }), "Cambio necesario");
    expect(screen.getByRole("button", { name: "Formalizar designación" })).toBeEnabled();

    const fechaInput = screen.getByLabelText(/Fecha efectiva/) as HTMLInputElement;
    const desde = fechaInput.value;

    await user.click(screen.getByRole("button", { name: "Formalizar designación" }));
    await user.click(screen.getByRole("button", { name: "Formalizar" }));

    await waitFor(() => {
      const llamada = apiFetchMock.mock.calls.find(
        ([ruta]) => ruta === "/gobierno/contratos/c1/supervision/designaciones",
      ) as [string, { body: Record<string, unknown> }] | undefined;
      expect(llamada).toBeDefined();
      expect(llamada?.[1].body).toMatchObject({
        funcionario_id: "f1",
        asignacion_id: "a1",
        acto_id: "ac1",
        motivo: "Cambio necesario",
        sustituye_id: "d2",
      });
      expect(llamada?.[1].body.desde).toBe(desde);
    });
  });

  it("e: error de la API muestra el mensaje legible con role alert", async () => {
    const user = userEvent.setup();
    capacidades = new Set(["gobierno_contratos:assign_supervisor"]);
    apiFetchMock.mockImplementation((ruta: string, opciones?: { method?: string }) => {
      if (ruta === "/gobierno/contratos/c1/supervision") {
        return Promise.resolve(supervisionConVigente());
      }
      if (ruta.startsWith("/gobierno/contratos/c1/supervision/opciones")) {
        return Promise.resolve(opcionesConDatos);
      }
      if (ruta === "/gobierno/contratos/c1/supervision/designaciones" && opciones?.method === "POST") {
        return Promise.reject(
          new ApiError(422, {
            code: "GOV_CONTRACT_SUPERVISOR_ACT_INVALID",
            message: "El acto de designación debe estar eficaz en la fecha efectiva",
          }),
        );
      }
      return Promise.reject(new Error("Ruta inesperada"));
    });
    renderComponent();

    await screen.findByRole("button", { name: "Sustituir supervisor" });
    await user.click(screen.getByRole("button", { name: "Sustituir supervisor" }));

    const funcionarioSelect = await screen.findByRole("combobox", { name: "Funcionario (obligatorio)" });
    await screen.findByRole("option", { name: "Juan Pérez · 11111111" });
    await user.selectOptions(funcionarioSelect, "f1");
    await user.selectOptions(screen.getByRole("combobox", { name: "Acto de designación (obligatorio)" }), "ac1");
    await user.type(screen.getByRole("textbox", { name: "Motivo del cambio (obligatorio)" }), "Cambio");

    await user.click(screen.getByRole("button", { name: "Formalizar designación" }));
    await user.click(screen.getByRole("button", { name: "Formalizar" }));

    const mensaje = await screen.findByText("El acto de designación debe estar eficaz en la fecha efectiva");
    expect(mensaje.closest('[role="alert"]')).not.toBeNull();
  });

  it("f: sin opciones elegibles muestra los dos mensajes informativos", async () => {
    const user = userEvent.setup();
    capacidades = new Set(["gobierno_contratos:assign_supervisor"]);
    apiFetchMock.mockImplementation((ruta: string) => {
      if (ruta === "/gobierno/contratos/c1/supervision") {
        return Promise.resolve(supervisionSinVigente());
      }
      if (ruta.startsWith("/gobierno/contratos/c1/supervision/opciones")) {
        return Promise.resolve({
          fecha: "2025-07-01",
          vigente_id: null,
          funcionarios: [],
          actos: [],
        });
      }
      return Promise.reject(new Error("Ruta inesperada"));
    });
    renderComponent();

    await screen.findByRole("button", { name: "Nueva designación" });
    await user.click(screen.getByRole("button", { name: "Nueva designación" }));

    await screen.findByText("No hay funcionarios con ocupación vigente para la fecha efectiva elegida.");
    await screen.findByText(
      "No hay actos de designación eficaces emitidos por un cargo con la competencia Aprobar sobre Contrataciones.",
    );
  });

  it("g: designación programada muestra el bloque y al sustituir envía ultima_id", async () => {
    const user = userEvent.setup();
    capacidades = new Set(["gobierno_contratos:assign_supervisor"]);
    const supervisionProgramada: import("./api").Supervision = {
      ...supervisionConVigente(),
      programada: {
        id: "d3",
        referencia: "SUP-03",
        numero: 3,
        estado: "VIGENTE",
        estado_etiqueta: "Vigente",
        situacion: "PROGRAMADA",
        situacion_etiqueta: "Programada",
        funcionario: { id: "f3", nombre: "Carlos Ruiz", documento: "33333333" },
        asignacion_id: "a3",
        figura: "SUPERVISOR",
        figura_etiqueta: "Supervisor",
        cargo: { id: "c3", codigo: "INS", nombre: "Inspector" },
        unidad: { id: "u3", nombre: "Unidad de Inspección" },
        acto: { id: "ac3", etiqueta: "Resolución 3", emisor_cargo: "Secretaría" },
        desde: "2099-01-10",
        hasta: null,
        motivo: "Cambio programado",
        sustituye: "d2",
        registrado_en: "2025-07-01T10:00:00Z",
      },
      ultima_id: "d3",
    };
    apiFetchMock.mockImplementation((ruta: string, opciones?: { method?: string; body?: unknown }) => {
      if (ruta === "/gobierno/contratos/c1/supervision") {
        return Promise.resolve(supervisionProgramada);
      }
      if (ruta.startsWith("/gobierno/contratos/c1/supervision/opciones")) {
        return Promise.resolve(opcionesConDatos);
      }
      if (ruta === "/gobierno/contratos/c1/supervision/designaciones" && opciones?.method === "POST") {
        return Promise.resolve(supervisionProgramada);
      }
      return Promise.reject(new Error("Ruta inesperada"));
    });
    renderComponent();

    await screen.findByRole("heading", { name: "Designación programada" });
    expect(screen.getByText(/Carlos Ruiz/)).toBeInTheDocument();

    await screen.findByRole("button", { name: "Sustituir supervisor" });
    await user.click(screen.getByRole("button", { name: "Sustituir supervisor" }));

    const funcionarioSelect = await screen.findByRole("combobox", { name: "Funcionario (obligatorio)" });
    await screen.findByRole("option", { name: "Juan Pérez · 11111111" });
    await user.selectOptions(funcionarioSelect, "f1");
    await user.selectOptions(screen.getByRole("combobox", { name: "Acto de designación (obligatorio)" }), "ac1");
    await user.type(screen.getByRole("textbox", { name: "Motivo del cambio (obligatorio)" }), "Cambio");

    const fechaInput = screen.getByLabelText(/Fecha efectiva/) as HTMLInputElement;
    const desde = fechaInput.value;

    await user.click(screen.getByRole("button", { name: "Formalizar designación" }));
    await user.click(screen.getByRole("button", { name: "Formalizar" }));

    await waitFor(() => {
      const llamada = apiFetchMock.mock.calls.find(
        ([ruta]) => ruta === "/gobierno/contratos/c1/supervision/designaciones",
      ) as [string, { body: Record<string, unknown> }] | undefined;
      expect(llamada).toBeDefined();
      expect(llamada?.[1].body).toMatchObject({
        funcionario_id: "f1",
        asignacion_id: "a1",
        acto_id: "ac1",
        motivo: "Cambio",
        sustituye_id: "d3",
      });
      expect(llamada?.[1].body.desde).toBe(desde);
    });
  });
});
