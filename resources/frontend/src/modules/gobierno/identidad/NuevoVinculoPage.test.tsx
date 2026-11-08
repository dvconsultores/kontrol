import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import type {
  OpcionesIdentidad,
  VinculoDetalle,
} from "@/modules/gobierno/api";

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

const { NuevoVinculoPage } = await import("./NuevoVinculoPage");

function renderPage(route = "/gobierno/identidad/nuevo") {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path="/gobierno/identidad/nuevo" element={<NuevoVinculoPage />} />
          <Route path="/gobierno/identidad/vinculos/:vinculoId" element={<NuevoVinculoPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const opciones: OpcionesIdentidad = {
  cuentas: [
    { id: "cuenta-1", usuario: "analista.prueba", estado: "ACTIVE", vinculada: false },
    { id: "cuenta-2", usuario: "otra.persona", estado: "ACTIVE", vinculada: true },
  ],
  funcionarios: [
    { id: "f1", codigo: "F-001", nombre: "Funcionario de Prueba", documento: "V-12345678", vinculado: false },
    { id: "f2", codigo: "F-002", nombre: "Otro Funcionario", documento: "V-87654321", vinculado: true },
  ],
};

const borradorDetalle: VinculoDetalle = {
  id: "vinculo-1",
  version: 3,
  status: "BORRADOR",
  cuenta: { id: "cuenta-1", usuario: "analista.prueba", estado: "ACTIVE" },
  funcionario: { id: "f1", codigo: "F-001", nombre: "Funcionario de Prueba", documento: "V-12345678" },
  desde: "2025-01-15",
  hasta: null,
  motivo: "Motivo original del vínculo",
  soporte: "Soporte-001",
  situacion: "BORRADOR",
  fin_efectivo: null,
  motivo_fin: null,
  registrado_por: null,
  activado_por: null,
  activado_en: null,
  terminado_por: null,
  terminado_en: null,
  historia: [],
  contexto: null,
  codigo: "VIN-001",
};

const activoDetalle: VinculoDetalle = {
  ...borradorDetalle,
  id: "vinculo-2",
  version: 1,
  status: "ACTIVO",
  situacion: "VIGENTE",
};

beforeEach(() => {
  capacidades = new Set(["gobierno_identidad:manage"]);
  apiFetchMock.mockReset();
  notifyMock.mockReset();
});

describe("NuevoVinculoPage", () => {
  it("sin gobierno_identidad:manage muestra Sin acceso", async () => {
    capacidades = new Set();
    renderPage();

    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("alta: elige cuenta y funcionario, rellena Desde y Motivo, y Guardar borrador hace POST con body sin company_id ni ente", async () => {
    apiFetchMock.mockImplementation(async (url: string, options?: { method?: string }) => {
      if (url === "/gobierno/identidad/opciones") {
        return opciones;
      }
      if (url === "/gobierno/identidad/vinculos" && options?.method === "POST") {
        return {
          id: "vinculo-nuevo",
          version: 1,
          status: "BORRADOR",
          cuenta: { id: "cuenta-1", usuario: "analista.prueba", estado: "ACTIVE" },
          funcionario: { id: "f1", codigo: "F-001", nombre: "Funcionario de Prueba", documento: "V-12345678" },
          desde: "2025-02-01",
          hasta: null,
          motivo: "Motivo de prueba para el vínculo",
          soporte: null,
          situacion: "BORRADOR",
          fin_efectivo: null,
          motivo_fin: null,
          registrado_por: null,
          activado_por: null,
          activado_en: null,
          terminado_por: null,
          terminado_en: null,
          historia: [],
          contexto: null,
          codigo: "VIN-001",
        };
      }
      throw new Error("Ruta no esperada");
    });

    const user = userEvent.setup();
    renderPage();

    await screen.findByLabelText(/Cuenta/);
    await screen.findByLabelText(/Funcionario/);

    await user.selectOptions(screen.getByLabelText(/Cuenta/), "cuenta-1");
    await user.selectOptions(screen.getByLabelText(/Funcionario/), "f1");
    await user.type(screen.getByLabelText(/Desde/), "2025-02-01");
    await user.type(screen.getByLabelText(/Motivo/), "Motivo de prueba para el vínculo");

    const guardarBoton = screen.getByRole("button", { name: /Guardar borrador/ });
    await user.click(guardarBoton);

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/identidad/vinculos",
        expect.objectContaining({
          method: "POST",
          body: {
            user_id: "cuenta-1",
            official_id: "f1",
            desde: "2025-02-01",
            hasta: null,
            motivo: "Motivo de prueba para el vínculo",
            soporte: null,
          },
        }),
      );
    });

    const postCall = apiFetchMock.mock.calls.find(
      (call) => call[0] === "/gobierno/identidad/vinculos" && call[1]?.method === "POST",
    );
    expect(postCall).toBeDefined();
    const body = postCall![1].body;
    expect(body).not.toHaveProperty("company_id");
    expect(body).not.toHaveProperty("ente");
    expect(Object.keys(body).sort()).toEqual([
      "desde",
      "hasta",
      "motivo",
      "official_id",
      "soporte",
      "user_id",
    ]);
  });

  it("las opciones de cuenta ya vinculada muestran 'ya vinculada'", async () => {
    apiFetchMock.mockImplementation(async (url: string) => {
      if (url === "/gobierno/identidad/opciones") {
        return opciones;
      }
      throw new Error("Ruta no esperada");
    });

    renderPage();

    const cuentaSelect = await screen.findByLabelText(/Cuenta/);
    const opcionesCuenta = within(cuentaSelect).getAllByRole("option");
    const opcionCuentaVinculada = opcionesCuenta.find(
      (opcion) => opcion.textContent?.includes("otra.persona"),
    );
    expect(opcionCuentaVinculada).toHaveTextContent("ya vinculada");

    const funcionarioSelect = await screen.findByLabelText(/Funcionario/);
    const opcionesFuncionario = within(funcionarioSelect).getAllByRole("option");
    const opcionFuncionarioVinculado = opcionesFuncionario.find(
      (opcion) => opcion.textContent?.includes("Otro Funcionario"),
    );
    expect(opcionFuncionarioVinculado).toHaveTextContent("ya vinculado");
  });

  it("error 422 con field_errors muestra el error junto al campo Motivo", async () => {
    const apiError = new ApiError(422, {
      code: "GOV_IDENTITY_INVALID",
      message: "Datos inválidos",
      field_errors: { motivo: ["El motivo es demasiado corto"] },
    });

    apiFetchMock.mockImplementation(async (url: string, options?: { method?: string }) => {
      if (url === "/gobierno/identidad/opciones") {
        return opciones;
      }
      if (url === "/gobierno/identidad/vinculos" && options?.method === "POST") {
        throw apiError;
      }
      throw new Error("Ruta no esperada");
    });

    const user = userEvent.setup();
    renderPage();

    await screen.findByLabelText(/Cuenta/);
    await user.selectOptions(screen.getByLabelText(/Cuenta/), "cuenta-1");
    await user.selectOptions(screen.getByLabelText(/Funcionario/), "f1");
    await user.type(screen.getByLabelText(/Desde/), "2025-02-01");
    await user.type(screen.getByLabelText(/Motivo/), "Corto");

    await user.click(screen.getByRole("button", { name: /Guardar borrador/ }));

    const motivoField = await screen.findByText("El motivo es demasiado corto");
    expect(motivoField).toBeInTheDocument();
    expect(screen.getByLabelText(/Motivo/)).toHaveAttribute("aria-invalid", "true");
  });

  it("edición de un vínculo ACTIVO muestra No editable", async () => {
    apiFetchMock.mockImplementation(async (url: string) => {
      if (url === "/gobierno/identidad/opciones") {
        return opciones;
      }
      if (url === "/gobierno/identidad/vinculos/vinculo-2") {
        return activoDetalle;
      }
      throw new Error("Ruta no esperada");
    });

    renderPage("/gobierno/identidad/vinculos/vinculo-2");

    expect(await screen.findByText("No editable")).toBeInTheDocument();
    expect(screen.getByText("Solo se modifica un vínculo en borrador.")).toBeInTheDocument();
  });

  it("edición de un BORRADOR precarga los valores y hace PATCH con ifMatch String(version)", async () => {
    apiFetchMock.mockImplementation(async (url: string, options?: { method?: string }) => {
      if (url === "/gobierno/identidad/opciones") {
        return opciones;
      }
      if (url === "/gobierno/identidad/vinculos/vinculo-1" && !options?.method) {
        return borradorDetalle;
      }
      if (url === "/gobierno/identidad/vinculos/vinculo-1" && options?.method === "PATCH") {
        return {
          ...borradorDetalle,
          motivo: "Motivo actualizado del vínculo",
        };
      }
      throw new Error("Ruta no esperada");
    });

    const user = userEvent.setup();
    renderPage("/gobierno/identidad/vinculos/vinculo-1");

    await screen.findByLabelText(/Cuenta/);
    expect(screen.getByLabelText(/Cuenta/)).toHaveValue("cuenta-1");
    expect(screen.getByLabelText(/Funcionario/)).toHaveValue("f1");
    expect(screen.getByLabelText(/Desde/)).toHaveValue("2025-01-15");
    expect(screen.getByLabelText(/Hasta/)).toHaveValue("");
    expect(screen.getByLabelText(/Motivo/)).toHaveValue("Motivo original del vínculo");
    expect(screen.getByLabelText(/Soporte/)).toHaveValue("Soporte-001");

    const motivoField = screen.getByLabelText(/Motivo/);
    await user.clear(motivoField);
    await user.type(motivoField, "Motivo actualizado del vínculo");

    await user.click(screen.getByRole("button", { name: /Guardar borrador/ }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/identidad/vinculos/vinculo-1",
        expect.objectContaining({
          method: "PATCH",
          body: expect.objectContaining({
            user_id: "cuenta-1",
            official_id: "f1",
            desde: "2025-01-15",
            hasta: null,
            motivo: "Motivo actualizado del vínculo",
            soporte: "Soporte-001",
          }),
          ifMatch: "3",
        }),
      );
    });

    const patchCall = apiFetchMock.mock.calls.find(
      (call) => call[0] === "/gobierno/identidad/vinculos/vinculo-1" && call[1]?.method === "PATCH",
    );
    expect(patchCall).toBeDefined();
    expect(patchCall![1].ifMatch).toBe("3");
  });
});
