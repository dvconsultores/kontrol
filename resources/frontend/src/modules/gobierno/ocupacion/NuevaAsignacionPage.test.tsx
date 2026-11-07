import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import { NuevaAsignacionPage } from "./NuevaAsignacionPage";

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

const catalogo = {
  figuras: [
    {
      codigo: "TITULAR",
      etiqueta: "Titular",
      grupo: "Principal",
      base_legal: "Ley Orgánica",
      descripcion: "Titular del cargo",
    },
    {
      codigo: "DELEGACION_ATRIBUCIONES",
      etiqueta: "Delegación de atribuciones",
      grupo: "Delegación",
      base_legal: "LOAP art. 34",
      descripcion: "Delegación de atribuciones",
    },
    {
      codigo: "SUPLENCIA",
      etiqueta: "Suplencia",
      grupo: "Suplencia",
      base_legal: "LOPPM art. 87",
      descripcion: "Suplencia temporal",
    },
  ],
  instrumentos: [],
  situaciones: [],
};

const opciones = {
  funcionarios: [
    { id: "f1", codigo: "PER-001", nombre: "Persona Uno" },
    { id: "f2", codigo: "PER-002", nombre: "Persona Dos" },
  ],
  cargos: [
    {
      id: "c1",
      codigo: "CAR-001",
      nombre: "Cargo Uno",
      unidad: "Unidad Uno",
      ejercicio: 2024,
      competencias: [
        { accion: "FIRMAR", materia: "PRESUPUESTO", tipo_limite: "SIN_LIMITE", monto: null, moneda: null },
        { accion: "APROBAR", materia: "CONTRATACIONES", tipo_limite: "SIN_LIMITE", monto: null, moneda: null },
      ],
    },
    {
      id: "c2",
      codigo: "CAR-002",
      nombre: "Cargo Dos",
      unidad: "Unidad Dos",
      ejercicio: 2024,
      competencias: [],
    },
  ],
  actos: [
    {
      id: "a1",
      numero: "123",
      tipo: "Resolución",
      fecha: "2024-01-01",
      fecha_eficacia: "2024-01-01",
      medio: null,
      emisor_cargo_id: "c2",
      emisor_cargo: "Cargo Dos · Unidad Dos",
      asunto: "Acto de prueba",
    },
  ],
};

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

function renderPage(initialEntries = ["/gobierno/ocupacion/asignaciones/nueva"]) {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route path="/gobierno/ocupacion/asignaciones/nueva" element={<NuevaAsignacionPage />} />
          <Route path="/gobierno/ocupacion/asignaciones/:asignacionId/editar" element={<NuevaAsignacionPage />} />
          <Route path="/gobierno/ocupacion/asignaciones/:asignacionId" element={<div>Detalle de asignación</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("NuevaAsignacionPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    notifyMock.mockReset();
    capacidades = new Set<string>();
    capacidades.add("gobierno_ocupacion:manage");
    apiFetchMock.mockImplementation(async (url: string) => {
      if (url === "/gobierno/ocupacion/catalogo") {
        return catalogo;
      }
      if (url.startsWith("/gobierno/ocupacion/opciones")) {
        return opciones;
      }
      throw new ApiError(404, { code: "NOT_FOUND", message: "Not found" });
    });
  });

  it("NAP-01 · sin manage muestra sin acceso", async () => {
    capacidades.clear();

    renderPage();

    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
    expect(
      screen.getByText("No tiene permiso para gestionar asignaciones."),
    ).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("NAP-02 · TITULAR válido hace POST con competencias [] y cargo_origen_id null y navega al detalle", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.selectOptions(await screen.findByLabelText(/^Figura/), "TITULAR");

    const funcionarioSelect = await screen.findByLabelText(/^Funcionario/);
    await user.selectOptions(funcionarioSelect, "f1");

    const cargoSelect = screen.getByLabelText(/^Cargo \*/);
    await user.selectOptions(cargoSelect, "c1");

    const actoSelect = screen.getByLabelText(/^Acto que la sustenta/);
    await user.selectOptions(actoSelect, "a1");

    const desdeInput = screen.getByLabelText(/^Desde/);
    await user.type(desdeInput, "2024-01-01");

    const fundamentoTextarea = screen.getByLabelText(/^Fundamento/);
    await user.type(fundamentoTextarea, "Fundamento válido de prueba");

    apiFetchMock.mockImplementation(async (url: string, options?: { method?: string }) => {
      if (url === "/gobierno/ocupacion/asignaciones" && options?.method === "POST") {
        return {
          id: "nueva-asignacion-1",
          codigo: "ASIG-001",
          figura: "TITULAR",
          figura_etiqueta: "Titular",
          funcionario: { id: "f1", codigo: "PER-001", nombre: "Persona Uno", documento: "V-12345678" },
          cargo: { id: "c1", codigo: "CAR-001", nombre: "Cargo Uno", unidad_id: "u1", unidad: "Unidad Uno", ejercicio: 2024 },
          cargo_origen: null,
          acto: {
            id: "a1",
            tipo: "Resolución",
            numero: "123",
            fecha: "2024-01-01",
            status: "VIGENTE",
            fecha_eficacia: "2024-01-01",
            medio: null,
            emisor_cargo_id: "c2",
            emisor_cargo: "Cargo Dos · Unidad Dos",
            funcionario: "Persona Dos",
            asunto: "Acto de prueba",
          },
          desde: "2024-01-01",
          hasta: null,
          fin_efectivo: null,
          status: "BORRADOR",
          situacion: "BORRADOR",
          version: 1,
        };
      }
      throw new ApiError(404, { code: "NOT_FOUND", message: "Not found" });
    });

    await user.click(screen.getByRole("button", { name: "Guardar borrador" }));

    await waitFor(() => {
      expect(screen.getByText("Detalle de asignación")).toBeInTheDocument();
    });

    expect(apiFetchMock).toHaveBeenCalledWith(
      "/gobierno/ocupacion/asignaciones",
      expect.objectContaining({
        method: "POST",
        body: expect.objectContaining({
          funcionario_id: "f1",
          cargo_id: "c1",
          figura: "TITULAR",
          cargo_origen_id: null,
          acto_id: "a1",
          desde: "2024-01-01",
          hasta: null,
          fundamento: "Fundamento válido de prueba",
          rendicion: null,
          maxima_autoridad: false,
          autorizacion_concejo: null,
          declara_delegable: false,
          competencias: [],
        }),
      }),
    );
    expect(notifyMock).toHaveBeenCalledWith({
      type: "success",
      title: "Asignación registrada en borrador",
    });
  });

  it("NAP-03 · falta de requeridos no llama POST", async () => {
    const user = userEvent.setup();
    renderPage();

    await screen.findByLabelText(/^Funcionario/);

    apiFetchMock.mockImplementation(async (url: string) => {
      if (url === "/gobierno/ocupacion/catalogo") return catalogo;
      if (url.startsWith("/gobierno/ocupacion/opciones")) return opciones;
      throw new ApiError(404, { code: "NOT_FOUND", message: "Not found" });
    });

    await user.click(screen.getByRole("button", { name: "Guardar borrador" }));

    await waitFor(() => {
      expect(screen.getByText("Elija la figura.")).toBeInTheDocument();
    });
    expect(screen.getByText("Elija el funcionario.")).toBeInTheDocument();
    expect(screen.getByText("Elija el cargo.")).toBeInTheDocument();
    expect(screen.getByText("Elija el acto que la sustenta.")).toBeInTheDocument();
    expect(screen.getByText("Indique la fecha de inicio.")).toBeInTheDocument();
    expect(
      screen.getByText("El fundamento debe tener entre 10 y 500 caracteres."),
    ).toBeInTheDocument();

    const postCalls = apiFetchMock.mock.calls.filter(
      ([url, options]) => url === "/gobierno/ocupacion/asignaciones" && (options as { method?: string })?.method === "POST",
    );
    expect(postCalls).toHaveLength(0);
  });

  it("NAP-04 · figura delegación muestra rendición, casilla y competencias; sin casilla no envía; envía accion y materia marcadas", async () => {
    const user = userEvent.setup();
    renderPage();

    const funcionarioSelect = await screen.findByLabelText(/^Funcionario/);
    await user.selectOptions(funcionarioSelect, "f1");

    const figuraSelect = screen.getByLabelText(/^Figura/);
    await user.selectOptions(figuraSelect, "DELEGACION_ATRIBUCIONES");

    expect(screen.getByLabelText(/^Rendición de cuenta/)).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /no es indelegable/ })).toBeInTheDocument();
    const cargoSelect = screen.getByLabelText(/^Cargo \*/);
    await user.selectOptions(cargoSelect, "c1");

    expect(screen.getByText("FIRMAR · PRESUPUESTO")).toBeInTheDocument();
    expect(screen.getByText("APROBAR · CONTRATACIONES")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText(/^Cargo de origen/), "c2");

    const actoSelect = screen.getByLabelText(/^Acto que la sustenta/);
    await user.selectOptions(actoSelect, "a1");

    const desdeInput = screen.getByLabelText(/^Desde/);
    await user.type(desdeInput, "2024-02-01");

    const fundamentoTextarea = screen.getByLabelText(/^Fundamento/);
    await user.type(fundamentoTextarea, "Fundamento válido de prueba");

    const rendicionTextarea = screen.getByLabelText(/^Rendición de cuenta/);
    await user.type(rendicionTextarea, "Rendición de cuenta válida");

    const firmaCheckbox = screen.getByRole("checkbox", { name: "FIRMAR · PRESUPUESTO" });
    await user.click(firmaCheckbox);

    await user.click(screen.getByRole("button", { name: "Guardar borrador" }));

    await waitFor(() => {
      expect(
        screen.getByText("Debe declarar que la competencia no es indelegable."),
      ).toBeInTheDocument();
    });

    const postCalls = apiFetchMock.mock.calls.filter(
      ([url, options]) => url === "/gobierno/ocupacion/asignaciones" && (options as { method?: string })?.method === "POST",
    );
    expect(postCalls).toHaveLength(0);

    const declaraCheckbox = screen.getByRole("checkbox", { name: /no es indelegable/ });
    await user.click(declaraCheckbox);

    apiFetchMock.mockImplementation(async (url: string, options?: { method?: string }) => {
      if (url === "/gobierno/ocupacion/asignaciones" && options?.method === "POST") {
        return {
          id: "nueva-asignacion-delegacion",
          codigo: "ASIG-DEL",
          figura: "DELEGACION_ATRIBUCIONES",
          figura_etiqueta: "Delegación de atribuciones",
          funcionario: { id: "f1", codigo: "PER-001", nombre: "Persona Uno", documento: "V-12345678" },
          cargo: { id: "c1", codigo: "CAR-001", nombre: "Cargo Uno", unidad_id: "u1", unidad: "Unidad Uno", ejercicio: 2024 },
          cargo_origen: null,
          acto: {
            id: "a1",
            tipo: "Resolución",
            numero: "123",
            fecha: "2024-01-01",
            status: "VIGENTE",
            fecha_eficacia: "2024-01-01",
            medio: null,
            emisor_cargo_id: "c2",
            emisor_cargo: "Cargo Dos · Unidad Dos",
            funcionario: "Persona Dos",
            asunto: "Acto de prueba",
          },
          desde: "2024-02-01",
          hasta: null,
          fin_efectivo: null,
          status: "BORRADOR",
          situacion: "BORRADOR",
          version: 1,
        };
      }
      throw new ApiError(404, { code: "NOT_FOUND", message: "Not found" });
    });

    await user.click(screen.getByRole("button", { name: "Guardar borrador" }));

    await waitFor(() => {
      expect(screen.getByText("Detalle de asignación")).toBeInTheDocument();
    });

    expect(apiFetchMock).toHaveBeenCalledWith(
      "/gobierno/ocupacion/asignaciones",
      expect.objectContaining({
        method: "POST",
        body: expect.objectContaining({
          rendicion: "Rendición de cuenta válida",
          declara_delegable: true,
          competencias: [{ accion: "FIRMAR", materia: "PRESUPUESTO" }],
        }),
      }),
    );
  });

  it("NAP-05 · SUPLENCIA muestra cargo de origen, exige Hasta y 'Suple a la máxima autoridad'", async () => {
    const user = userEvent.setup();
    renderPage();

    const funcionarioSelect = await screen.findByLabelText(/^Funcionario/);
    await user.selectOptions(funcionarioSelect, "f1");

    const figuraSelect = screen.getByLabelText(/^Figura/);
    await user.selectOptions(figuraSelect, "SUPLENCIA");

    expect(screen.getByLabelText(/^Cargo de origen/)).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /Suple a la máxima autoridad/ })).toBeInTheDocument();

    const cargoSelect = screen.getByLabelText(/^Cargo \*/);
    await user.selectOptions(cargoSelect, "c1");

    const cargoOrigenSelect = screen.getByLabelText(/^Cargo de origen/);
    await user.selectOptions(cargoOrigenSelect, "c2");

    const actoSelect = screen.getByLabelText(/^Acto que la sustenta/);
    await user.selectOptions(actoSelect, "a1");

    const desdeInput = screen.getByLabelText(/^Desde/);
    await user.type(desdeInput, "2024-03-01");

    const fundamentoTextarea = screen.getByLabelText(/^Fundamento/);
    await user.type(fundamentoTextarea, "Fundamento válido de prueba");

    const maximaCheckbox = screen.getByRole("checkbox", { name: /Suple a la máxima autoridad/ });
    await user.click(maximaCheckbox);

    const autorizacionTextarea = await screen.findByLabelText(/^Autorización del Concejo/);
    await user.type(autorizacionTextarea, "Autorización aprobada");

    await user.click(screen.getByRole("button", { name: "Guardar borrador" }));

    await waitFor(() => {
      expect(screen.getByText("Indique la fecha final.")).toBeInTheDocument();
    });

    const postCalls = apiFetchMock.mock.calls.filter(
      ([url, options]) => url === "/gobierno/ocupacion/asignaciones" && (options as { method?: string })?.method === "POST",
    );
    expect(postCalls).toHaveLength(0);

    const hastaInput = screen.getByLabelText(/^Hasta/);
    await user.type(hastaInput, "2024-03-15");

    apiFetchMock.mockImplementation(async (url: string, options?: { method?: string }) => {
      if (url === "/gobierno/ocupacion/asignaciones" && options?.method === "POST") {
        return {
          id: "nueva-asignacion-suplencia",
          codigo: "ASIG-SUP",
          figura: "SUPLENCIA",
          figura_etiqueta: "Suplencia",
          funcionario: { id: "f1", codigo: "PER-001", nombre: "Persona Uno", documento: "V-12345678" },
          cargo: { id: "c1", codigo: "CAR-001", nombre: "Cargo Uno", unidad_id: "u1", unidad: "Unidad Uno", ejercicio: 2024 },
          cargo_origen: { id: "c2", codigo: "CAR-002", nombre: "Cargo Dos", unidad_id: "u2", unidad: "Unidad Dos", ejercicio: 2024 },
          acto: {
            id: "a1",
            tipo: "Resolución",
            numero: "123",
            fecha: "2024-01-01",
            status: "VIGENTE",
            fecha_eficacia: "2024-01-01",
            medio: null,
            emisor_cargo_id: "c2",
            emisor_cargo: "Cargo Dos · Unidad Dos",
            funcionario: "Persona Dos",
            asunto: "Acto de prueba",
          },
          desde: "2024-03-01",
          hasta: "2024-03-15",
          fin_efectivo: null,
          status: "BORRADOR",
          situacion: "BORRADOR",
          version: 1,
        };
      }
      throw new ApiError(404, { code: "NOT_FOUND", message: "Not found" });
    });

    await user.click(screen.getByRole("button", { name: "Guardar borrador" }));

    await waitFor(() => {
      expect(screen.getByText("Detalle de asignación")).toBeInTheDocument();
    });

    expect(apiFetchMock).toHaveBeenCalledWith(
      "/gobierno/ocupacion/asignaciones",
      expect.objectContaining({
        method: "POST",
        body: expect.objectContaining({
          hasta: "2024-03-15",
          maxima_autoridad: true,
          autorizacion_concejo: "Autorización aprobada",
        }),
      }),
    );
  });

  it("NAP-06 · ?cargo=<id> preselecciona el cargo", async () => {
    renderPage(["/gobierno/ocupacion/asignaciones/nueva?cargo=c1"]);

    const cargoSelect = (await screen.findByLabelText(/^Cargo/)) as HTMLSelectElement;
    expect(cargoSelect.value).toBe("c1");
  });

  it("NAP-07 · edición: carga el detalle y hace PATCH con ifMatch", async () => {
    const detalleAsignacion = {
      id: "asig-1",
      codigo: "ASIG-BORRADOR",
      figura: "TITULAR",
      figura_etiqueta: "Titular",
      funcionario: { id: "f1", codigo: "PER-001", nombre: "Persona Uno", documento: "V-12345678" },
      cargo: { id: "c1", codigo: "CAR-001", nombre: "Cargo Uno", unidad_id: "u1", unidad: "Unidad Uno", ejercicio: 2024 },
      cargo_origen: null,
      acto: {
        id: "a1",
        tipo: "Resolución",
        numero: "123",
        fecha: "2024-01-01",
        status: "VIGENTE",
        fecha_eficacia: "2024-01-01",
        medio: null,
        emisor_cargo_id: "c2",
        emisor_cargo: "Cargo Dos · Unidad Dos",
        funcionario: "Persona Dos",
        asunto: "Acto de prueba",
      },
      desde: "2024-01-01",
      hasta: null,
      fin_efectivo: null,
      status: "BORRADOR",
      situacion: "BORRADOR",
      version: 2,
      fundamento: "Fundamento original válido",
      rendicion: null,
      maxima_autoridad: false,
      autorizacion_concejo: null,
      declara_delegable: false,
      competencias: [],
      autoridad: [],
      ejerce: true,
      registrada_por: null,
      activada_por: null,
      activada_en: null,
      terminada_por: null,
      terminada_en: null,
      historia: [],
      avocaciones: [],
    };

    apiFetchMock.mockImplementation(async (url: string, options?: { method?: string }) => {
      if (url === "/gobierno/ocupacion/catalogo") return catalogo;
      if (url.startsWith("/gobierno/ocupacion/opciones")) return opciones;
      if (url === "/gobierno/ocupacion/asignaciones/asig-1") {
        if (options?.method === "PATCH") {
          return { ...detalleAsignacion, version: 3 };
        }
        return detalleAsignacion;
      }
      throw new ApiError(404, { code: "NOT_FOUND", message: "Not found" });
    });

    const user = userEvent.setup();
    renderPage(["/gobierno/ocupacion/asignaciones/asig-1/editar"]);

    const funcionarioSelect = (await screen.findByLabelText(/^Funcionario/)) as HTMLSelectElement;
    expect(funcionarioSelect.value).toBe("f1");

    const fundamentoTextarea = screen.getByLabelText(/^Fundamento/);
    await user.clear(fundamentoTextarea);
    await user.type(fundamentoTextarea, "Fundamento actualizado válido");

    await user.click(screen.getByRole("button", { name: "Guardar borrador" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/ocupacion/asignaciones/asig-1",
        expect.objectContaining({
          method: "PATCH",
          ifMatch: "2",
          body: expect.objectContaining({
            fundamento: "Fundamento actualizado válido",
          }),
        }),
      );
    });

    expect(notifyMock).toHaveBeenCalledWith({
      type: "success",
      title: "Asignación actualizada",
    });
    expect(screen.getByText("Detalle de asignación")).toBeInTheDocument();
  });

  it("NAP-08 · edición de un ACTIVO muestra 'Solo se edita un borrador'", async () => {
    apiFetchMock.mockImplementation(async (url: string) => {
      if (url === "/gobierno/ocupacion/catalogo") return catalogo;
      if (url.startsWith("/gobierno/ocupacion/opciones")) return opciones;
      if (url === "/gobierno/ocupacion/asignaciones/asig-activo") {
        return {
          id: "asig-activo",
          codigo: "ASIG-ACT",
          figura: "TITULAR",
          figura_etiqueta: "Titular",
          funcionario: { id: "f1", codigo: "PER-001", nombre: "Persona Uno", documento: "V-12345678" },
          cargo: { id: "c1", codigo: "CAR-001", nombre: "Cargo Uno", unidad_id: "u1", unidad: "Unidad Uno", ejercicio: 2024 },
          cargo_origen: null,
          acto: {
            id: "a1",
            tipo: "Resolución",
            numero: "123",
            fecha: "2024-01-01",
            status: "VIGENTE",
            fecha_eficacia: "2024-01-01",
            medio: null,
            emisor_cargo_id: "c2",
            emisor_cargo: "Cargo Dos · Unidad Dos",
            funcionario: "Persona Dos",
            asunto: "Acto de prueba",
          },
          desde: "2024-01-01",
          hasta: null,
          fin_efectivo: null,
          status: "ACTIVO",
          situacion: "VIGENTE",
          version: 1,
          fundamento: "Fundamento original válido",
          rendicion: null,
          maxima_autoridad: false,
          autorizacion_concejo: null,
          declara_delegable: false,
          competencias: [],
          autoridad: [],
          ejerce: true,
          registrada_por: null,
          activada_por: null,
          activada_en: null,
          terminada_por: null,
          terminada_en: null,
          historia: [],
          avocaciones: [],
        };
      }
      throw new ApiError(404, { code: "NOT_FOUND", message: "Not found" });
    });

    renderPage(["/gobierno/ocupacion/asignaciones/asig-activo/editar"]);

    expect(await screen.findByText("Solo se edita un borrador")).toBeInTheDocument();
    expect(
      screen.getByText("Esta asignación ya no está en borrador y no puede modificarse."),
    ).toBeInTheDocument();
  });

  it("NAP-09 · 422 GOV_ASSIGNMENT_ACT_INVALID muestra error.message en role='alert'", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.selectOptions(await screen.findByLabelText(/^Figura/), "TITULAR");
    const funcionarioSelect = await screen.findByLabelText(/^Funcionario/);
    await user.selectOptions(funcionarioSelect, "f1");
    await user.selectOptions(screen.getByLabelText(/^Cargo/), "c1");
    await user.selectOptions(screen.getByLabelText(/^Acto que la sustenta/), "a1");
    await user.type(screen.getByLabelText(/^Desde/), "2024-01-01");
    await user.type(
      screen.getByLabelText(/^Fundamento/),
      "Fundamento válido de prueba",
    );

    apiFetchMock.mockImplementation(async (url: string, options?: { method?: string }) => {
      if (url === "/gobierno/ocupacion/asignaciones" && options?.method === "POST") {
        throw new ApiError(422, { code: "GOV_ASSIGNMENT_ACT_INVALID", message: "El acto no está eficaz para la fecha de inicio." });
      }
      if (url === "/gobierno/ocupacion/catalogo") return catalogo;
      if (url.startsWith("/gobierno/ocupacion/opciones")) return opciones;
      throw new ApiError(404, { code: "NOT_FOUND", message: "Not found" });
    });

    await user.click(screen.getByRole("button", { name: "Guardar borrador" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("El acto no está eficaz para la fecha de inicio.");
  });

  it("NAP-10 · 422 VALIDATION_ERROR por campo muestra mensaje por campo", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.selectOptions(await screen.findByLabelText(/^Figura/), "TITULAR");
    const funcionarioSelect = await screen.findByLabelText(/^Funcionario/);
    await user.selectOptions(funcionarioSelect, "f1");
    await user.selectOptions(screen.getByLabelText(/^Cargo/), "c1");
    await user.selectOptions(screen.getByLabelText(/^Acto que la sustenta/), "a1");
    await user.type(screen.getByLabelText(/^Desde/), "2024-01-01");
    await user.type(
      screen.getByLabelText(/^Fundamento/),
      "Fundamento válido de prueba",
    );

    apiFetchMock.mockImplementation(async (url: string, options?: { method?: string }) => {
      if (url === "/gobierno/ocupacion/asignaciones" && options?.method === "POST") {
        throw new ApiError(422, { code: "VALIDATION_ERROR", message: "Datos inválidos", field_errors: { desde: ["La fecha de inicio no es válida."] } });
      }
      if (url === "/gobierno/ocupacion/catalogo") return catalogo;
      if (url.startsWith("/gobierno/ocupacion/opciones")) return opciones;
      throw new ApiError(404, { code: "NOT_FOUND", message: "Not found" });
    });

    await user.click(screen.getByRole("button", { name: "Guardar borrador" }));

    expect(
      await screen.findByText("La fecha de inicio no es válida."),
    ).toBeInTheDocument();
  });
});
