import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import { NuevaCuentaPage } from "./NuevaCuentaPage";

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

const opciones = {
  bancos: [
    { id: "b1", codigo: "0102", nombre: "Banco Uno" },
    { id: "b2", codigo: "0177", nombre: "Banco Dos" },
  ],
  cargos: [],
  actos: [],
};

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/gobierno/tesoreria/cuentas/nueva"]}>
        <Routes>
          <Route path="/gobierno/tesoreria/cuentas/nueva" element={<NuevaCuentaPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("NCP", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    notifyMock.mockReset();
    capacidades = new Set<string>();
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/tesoreria/opciones") {
        return Promise.resolve(opciones);
      }
      if (url === "/gobierno/tesoreria/cuentas") {
        const cuenta = {
          id: "c1",
          codigo: "CB-2026-0001",
          denominacion: "Fondos de funcionamiento",
          banco_id: "b1",
          banco_codigo: "0102",
          banco_nombre: "Banco Uno",
          tipo: "CORRIENTE",
          moneda: "VES",
          numero_enmascarado: "••••0001",
          vigente_desde: "2026-11-01",
          vigente_hasta: null,
          estado: "BORRADOR",
          en_vigor: false,
          acto_sin_efecto: false,
          autorizados_en_vigor: 0,
          version: 1,
        };
        return Promise.resolve(cuenta);
      }
      return Promise.reject(new Error(`URL no esperada: ${url}`));
    });
  });

  it("NC-01 · sin manage: «Sin acceso» y no se ve el formulario", async () => {
    renderPage();

    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
    expect(
      screen.getByText("No tiene permiso para registrar cuentas bancarias."),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText(/^Denominación/)).not.toBeInTheDocument();
  });

  it("NC-02 · sin bancos: «Aún no hay bancos activos» y enlace a Bancos", async () => {
    capacidades.add("gobierno_cuentas:manage");
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/tesoreria/opciones") {
        return Promise.resolve({ ...opciones, bancos: [] });
      }
      return Promise.reject(new Error(`URL no esperada: ${url}`));
    });

    renderPage();

    expect(await screen.findByText("Aún no hay bancos activos")).toBeInTheDocument();
    expect(screen.getByText("Registre primero el banco en el catálogo.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ir a Bancos" })).toBeInTheDocument();
  });

  it("NC-03 · enviar vacío: errores por campo, sin llamar a POST", async () => {
    capacidades.add("gobierno_cuentas:manage");
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/tesoreria/opciones") {
        return Promise.resolve(opciones);
      }
      return Promise.reject(new Error(`URL no esperada: ${url}`));
    });
    renderPage();

    await screen.findByLabelText(/^Denominación/);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Registrar cuenta" }));

    expect(await screen.findByText("La denominación debe tener al menos 3 caracteres.")).toBeInTheDocument();
    expect(screen.getByText("Elija un banco.")).toBeInTheDocument();
    expect(screen.getByText("Elija el tipo de cuenta.")).toBeInTheDocument();
    expect(screen.getByText("El número debe tener 20 dígitos.")).toBeInTheDocument();
    expect(screen.getByText("Elija la moneda.")).toBeInTheDocument();


    const postCalls = apiFetchMock.mock.calls.filter(
      ([, options]) => options?.method === "POST",
    );
    expect(postCalls).toHaveLength(0);
  });

  it("NC-04 · número de 19 dígitos: «El número debe tener 20 dígitos», sin POST", async () => {
    capacidades.add("gobierno_cuentas:manage");
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/tesoreria/opciones") {
        return Promise.resolve(opciones);
      }
      return Promise.reject(new Error(`URL no esperada: ${url}`));
    });
    renderPage();

    const user = userEvent.setup();
    await screen.findByLabelText(/^Denominación/);
    await user.type(screen.getByLabelText(/^Denominación/), "Fondos de funcionamiento");
    await user.selectOptions(screen.getByLabelText(/^Banco/), "b1");
    await user.selectOptions(screen.getByLabelText(/^Tipo de cuenta/), "CORRIENTE");
    await user.type(screen.getByLabelText(/^Número de cuenta/), "0102000000000000001");
    await user.selectOptions(screen.getByLabelText(/^Moneda/), "VES");
    await user.click(screen.getByRole("button", { name: "Registrar cuenta" }));

    expect(await screen.findByText("El número debe tener 20 dígitos.")).toBeInTheDocument();
    const postCalls = apiFetchMock.mock.calls.filter(
      ([, options]) => options?.method === "POST",
    );
    expect(postCalls).toHaveLength(0);
  });

  it("NC-05 · número que no empieza por el código del banco: «El número debe empezar por el código del banco», sin POST", async () => {
    capacidades.add("gobierno_cuentas:manage");
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/tesoreria/opciones") {
        return Promise.resolve(opciones);
      }
      return Promise.reject(new Error(`URL no esperada: ${url}`));
    });
    renderPage();

    const user = userEvent.setup();
    await screen.findByLabelText(/^Denominación/);
    await user.type(screen.getByLabelText(/^Denominación/), "Fondos de funcionamiento");
    await user.selectOptions(screen.getByLabelText(/^Banco/), "b1");
    await user.selectOptions(screen.getByLabelText(/^Tipo de cuenta/), "CORRIENTE");
    await user.type(screen.getByLabelText(/^Número de cuenta/), "01770000000000000001");
    await user.selectOptions(screen.getByLabelText(/^Moneda/), "VES");
    await user.click(screen.getByRole("button", { name: "Registrar cuenta" }));

    expect(await screen.findByText("El número debe empezar por el código del banco.")).toBeInTheDocument();
    const postCalls = apiFetchMock.mock.calls.filter(
      ([, options]) => options?.method === "POST",
    );
    expect(postCalls).toHaveLength(0);
  });

  it("NC-06 · envío correcto: POST /gobierno/tesoreria/cuentas con el cuerpo exacto, vigente_hasta: null, y notificación", async () => {
    capacidades.add("gobierno_cuentas:manage");
    renderPage();

    const user = userEvent.setup();
    await screen.findByLabelText(/^Denominación/);
    await user.type(screen.getByLabelText(/^Denominación/), "Fondos de funcionamiento");
    await user.selectOptions(screen.getByLabelText(/^Banco/), "b1");
    await user.selectOptions(screen.getByLabelText(/^Tipo de cuenta/), "CORRIENTE");
    await user.type(screen.getByLabelText(/^Número de cuenta/), "01020000000000000001");
    await user.selectOptions(screen.getByLabelText(/^Moneda/), "VES");
    await user.click(screen.getByRole("button", { name: "Registrar cuenta" }));

    await waitFor(() => {
      const postCalls = apiFetchMock.mock.calls.filter(
        ([url, options]) =>
          url === "/gobierno/tesoreria/cuentas" && options?.method === "POST",
      );
      expect(postCalls).toHaveLength(1);
      expect(postCalls[0][1].body).toEqual({
        denominacion: "Fondos de funcionamiento",
        banco_id: "b1",
        tipo: "CORRIENTE",
        numero: "01020000000000000001",
        moneda: "VES",
        vigente_desde: expect.any(String),
        vigente_hasta: null,
      });
    });

    await waitFor(() => {
      expect(notifyMock).toHaveBeenCalledWith({
        type: "success",
        title: "Cuenta registrada en borrador",
      });
    });
  });

  it("NC-07 · 409 GOV_BANK_ACCOUNT_DUPLICATE: el error aparece en el campo número", async () => {
    capacidades.add("gobierno_cuentas:manage");
    apiFetchMock.mockImplementation((url: string, options?: { method?: string }) => {
      if (url === "/gobierno/tesoreria/opciones") {
        return Promise.resolve(opciones);
      }
      if (url === "/gobierno/tesoreria/cuentas" && options?.method === "POST") {
        return Promise.reject(
          new ApiError(409, {
            code: "GOV_BANK_ACCOUNT_DUPLICATE",
            message: "Ya existe una cuenta con ese número en el banco.",
            details: { numero: ["Ya existe una cuenta con ese número en el banco."] },
          }),
        );
      }
      return Promise.reject(new Error(`URL no esperada: ${url}`));
    });
    renderPage();

    const user = userEvent.setup();
    await screen.findByLabelText(/^Denominación/);
    await user.type(screen.getByLabelText(/^Denominación/), "Fondos de funcionamiento");
    await user.selectOptions(screen.getByLabelText(/^Banco/), "b1");
    await user.selectOptions(screen.getByLabelText(/^Tipo de cuenta/), "CORRIENTE");
    await user.type(screen.getByLabelText(/^Número de cuenta/), "01020000000000000001");
    await user.selectOptions(screen.getByLabelText(/^Moneda/), "VES");
    await user.click(screen.getByRole("button", { name: "Registrar cuenta" }));

    expect(await screen.findByText("Ya existe una cuenta con ese número en el banco.")).toBeInTheDocument();
    expect(screen.getByLabelText(/^Número de cuenta/)).toHaveAttribute("aria-invalid", "true");
  });

  it("NC-08 · el campo «Vigente desde» no tiene atributo min", async () => {
    capacidades.add("gobierno_cuentas:manage");
    renderPage();

    const desde = await screen.findByLabelText(/^Vigente desde/);
    expect(desde).not.toHaveAttribute("min");
  });
});
