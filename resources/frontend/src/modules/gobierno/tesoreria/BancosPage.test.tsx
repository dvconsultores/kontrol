import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import { BancosPage } from "./BancosPage";

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

const banco = {
  id: "b1",
  codigo: "0102",
  nombre: "Banco Uno",
  estado: "ACTIVO",
  version: 1,
};

const listado = {
  items: [banco],
};

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/gobierno/tesoreria/bancos"]}>
        <Routes>
          <Route path="/gobierno/tesoreria/bancos" element={<BancosPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("BancosPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    notifyMock.mockReset();
    capacidades = new Set<string>();
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/tesoreria/bancos") {
        return Promise.resolve(listado);
      }
      return Promise.reject(new Error(`URL no esperada: ${url}`));
    });
  });

  it("BP-01 · sin gobierno_cuentas:view muestra «Sin acceso»", async () => {
    renderPage();

    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
    expect(screen.queryByText("Banco Uno")).not.toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("BP-02 · con view muestra la tabla sin formulario ni acciones", async () => {
    capacidades.add("gobierno_cuentas:view");

    renderPage();

    expect(await screen.findByText("Banco Uno")).toBeInTheDocument();
    expect(screen.getByText("0102")).toBeInTheDocument();
    expect(screen.getByText("Activo")).toBeInTheDocument();
    expect(screen.queryByLabelText("Código")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Editar/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Inactivar/i })).not.toBeInTheDocument();
  });

  it("BP-03 · alta correcta envía POST con codigo y nombre", async () => {
    capacidades.add("gobierno_cuentas:view");
    capacidades.add("gobierno_cuentas:manage");

    apiFetchMock.mockImplementation((url: string, options?: { method?: string; body?: unknown }) => {
      if (url === "/gobierno/tesoreria/bancos" && options?.method === "POST") {
        return Promise.resolve({ ...banco, ...(options.body as object) });
      }
      if (url === "/gobierno/tesoreria/bancos") {
        return Promise.resolve(listado);
      }
      return Promise.reject(new Error(`URL no esperada: ${url}`));
    });

    const usuario = userEvent.setup();
    renderPage();

    await screen.findByText("Banco Uno");

    await usuario.type(screen.getByLabelText(/^Código/), "0103");
    await usuario.type(screen.getByLabelText(/^Nombre/), "Banco Dos");
    await usuario.click(screen.getByRole("button", { name: "Registrar banco" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/tesoreria/bancos",
        expect.objectContaining({
          method: "POST",
          body: { codigo: "0103", nombre: "Banco Dos" },
        }),
      );
    });
  });

  it("BP-04 · código de 3 dígitos muestra error y no envía POST", async () => {
    capacidades.add("gobierno_cuentas:view");
    capacidades.add("gobierno_cuentas:manage");

    const usuario = userEvent.setup();
    renderPage();

    await screen.findByText("Banco Uno");

    await usuario.type(screen.getByLabelText(/^Código/), "010");
    await usuario.type(screen.getByLabelText(/^Nombre/), "Banco Dos");
    await usuario.click(screen.getByRole("button", { name: "Registrar banco" }));

    expect(await screen.findByText("El código debe tener 4 dígitos")).toBeInTheDocument();

    const postCalls = apiFetchMock.mock.calls.filter(
      ([, options]) => options?.method === "POST",
    );
    expect(postCalls).toHaveLength(0);
  });

  it("BP-05 · 409 GOV_BANK_CODE_DUPLICATE muestra error en el campo código", async () => {
    capacidades.add("gobierno_cuentas:view");
    capacidades.add("gobierno_cuentas:manage");

    apiFetchMock.mockImplementation((url: string, options?: { method?: string }) => {
      if (url === "/gobierno/tesoreria/bancos" && options?.method === "POST") {
        return Promise.reject(
          new ApiError(409, {
            code: "GOV_BANK_CODE_DUPLICATE",
            message: "Código duplicado",
            details: {},
          }),
        );
      }
      if (url === "/gobierno/tesoreria/bancos") {
        return Promise.resolve(listado);
      }
      return Promise.reject(new Error(`URL no esperada: ${url}`));
    });

    const usuario = userEvent.setup();
    renderPage();

    await screen.findByText("Banco Uno");

    await usuario.type(screen.getByLabelText(/^Código/), "0102");
    await usuario.type(screen.getByLabelText(/^Nombre/), "Banco Dos");
    await usuario.click(screen.getByRole("button", { name: "Registrar banco" }));

    expect(
      await screen.findByText("Ya existe un banco con este código."),
    ).toBeInTheDocument();
  });

  it("BP-06 · Inactivar envía PATCH con estado INACTIVO e ifMatch", async () => {
    capacidades.add("gobierno_cuentas:view");
    capacidades.add("gobierno_cuentas:manage");

    apiFetchMock.mockImplementation((url: string, options?: { method?: string; body?: unknown; ifMatch?: string }) => {
      if (url === "/gobierno/tesoreria/bancos/b1" && options?.method === "PATCH") {
        return Promise.resolve({ ...banco, estado: "INACTIVO", ...(options.body as object) });
      }
      if (url === "/gobierno/tesoreria/bancos") {
        return Promise.resolve(listado);
      }
      return Promise.reject(new Error(`URL no esperada: ${url}`));
    });

    const usuario = userEvent.setup();
    renderPage();

    await screen.findByText("Banco Uno");

    await usuario.click(
      screen.getByRole("button", { name: "Inactivar el banco Banco Uno" }),
    );

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/tesoreria/bancos/b1",
        expect.objectContaining({
          method: "PATCH",
          body: { estado: "INACTIVO" },
          ifMatch: "1",
        }),
      );
    });
  });

  it("BP-07 · edición del nombre envía PATCH con el nuevo nombre", async () => {
    capacidades.add("gobierno_cuentas:view");
    capacidades.add("gobierno_cuentas:manage");

    apiFetchMock.mockImplementation((url: string, options?: { method?: string; body?: unknown }) => {
      if (url === "/gobierno/tesoreria/bancos/b1" && options?.method === "PATCH") {
        return Promise.resolve({ ...banco, ...(options.body as object) });
      }
      if (url === "/gobierno/tesoreria/bancos") {
        return Promise.resolve(listado);
      }
      return Promise.reject(new Error(`URL no esperada: ${url}`));
    });

    const usuario = userEvent.setup();
    renderPage();

    await screen.findByText("Banco Uno");

    await usuario.click(
      screen.getByRole("button", { name: "Editar el banco Banco Uno" }),
    );

    const inputNombre = screen.getByLabelText("Nombre del banco Banco Uno");
    await usuario.clear(inputNombre);
    await usuario.type(inputNombre, "Banco Uno Editado");
    await usuario.click(screen.getByRole("button", { name: "Guardar" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/tesoreria/bancos/b1",
        expect.objectContaining({
          method: "PATCH",
          body: { nombre: "Banco Uno Editado" },
          ifMatch: "1",
        }),
      );
    });
  });

  it("BP-08 · 409 GOV_BANK_ACCOUNT_STALE muestra role=alert", async () => {
    capacidades.add("gobierno_cuentas:view");
    capacidades.add("gobierno_cuentas:manage");

    apiFetchMock.mockImplementation((url: string, options?: { method?: string }) => {
      if (url === "/gobierno/tesoreria/bancos/b1" && options?.method === "PATCH") {
        return Promise.reject(
          new ApiError(409, {
            code: "GOV_BANK_ACCOUNT_STALE",
            message: "Versión desactualizada",
            details: {},
          }),
        );
      }
      if (url === "/gobierno/tesoreria/bancos") {
        return Promise.resolve(listado);
      }
      return Promise.reject(new Error(`URL no esperada: ${url}`));
    });

    const usuario = userEvent.setup();
    renderPage();

    await screen.findByText("Banco Uno");

    await usuario.click(
      screen.getByRole("button", { name: "Inactivar el banco Banco Uno" }),
    );

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent(
      "El banco fue modificado por otra persona. Se recargaron los datos; revise los cambios antes de continuar.",
    );
  });
});
