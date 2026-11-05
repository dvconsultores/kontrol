import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import { RubrosPage } from "./RubrosPage";

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
  useCompany: () => ({
    activeCompanyId: "c1",
    activeCompany: { id: "c1", legal_name: "Contenedor 1" },
  }),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: notifyMock }),
}));

const rubro = {
  id: "r1",
  codigo: "RUB-001",
  nombre: "Rubro Uno",
  tipo: "INGRESO",
  estado: "ACTIVO",
  version: 1,
};

const listado = {
  items: [rubro],
};

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/gobierno/tesoreria/programacion/rubros"]}>
        <Routes>
          <Route
            path="/gobierno/tesoreria/programacion/rubros"
            element={<RubrosPage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("RubrosPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    notifyMock.mockReset();
    capacidades = new Set<string>();
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/tesoreria/rubros") {
        return Promise.resolve(listado);
      }
      return Promise.reject(new Error(`URL no esperada: ${url}`));
    });
  });

  it("RP-01 · sin gobierno_caja:view muestra «Sin acceso»", async () => {
    renderPage();

    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
    expect(screen.queryByText("Rubro Uno")).not.toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("RP-02 · con view muestra la tabla sin formulario ni acciones", async () => {
    capacidades.add("gobierno_caja:view");

    renderPage();

    expect(await screen.findByText("Rubro Uno")).toBeInTheDocument();
    expect(screen.getByText("RUB-001")).toBeInTheDocument();
    const tabla = screen.getByRole("region", { name: "Tabla de rubros" });
    expect(within(tabla).getByText("Ingreso")).toBeInTheDocument();
    expect(within(tabla).getByText("Activo")).toBeInTheDocument();
    expect(screen.queryByLabelText(/^Código/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/^Nombre/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/^Tipo/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Editar/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Inactivar/i })).not.toBeInTheDocument();
  });

  it("RP-03 · alta correcta envía POST con codigo, nombre y tipo", async () => {
    capacidades.add("gobierno_caja:view");
    capacidades.add("gobierno_caja:manage");

    apiFetchMock.mockImplementation(
      (url: string, options?: { method?: string; body?: unknown }) => {
        if (url === "/gobierno/tesoreria/rubros" && options?.method === "POST") {
          return Promise.resolve({ ...rubro, ...(options.body as object) });
        }
        if (url === "/gobierno/tesoreria/rubros") {
          return Promise.resolve(listado);
        }
        return Promise.reject(new Error(`URL no esperada: ${url}`));
      },
    );

    const usuario = userEvent.setup();
    renderPage();

    await screen.findByText("Rubro Uno");

    await usuario.type(screen.getByLabelText(/^Código/), "RUB-002");
    await usuario.type(screen.getByLabelText(/^Nombre/), "Rubro Dos");
    await usuario.selectOptions(screen.getByLabelText(/^Tipo/), "DESEMBOLSO");
    await usuario.click(screen.getByRole("button", { name: "Registrar rubro" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/tesoreria/rubros",
        expect.objectContaining({
          method: "POST",
          body: {
            codigo: "RUB-002",
            nombre: "Rubro Dos",
            tipo: "DESEMBOLSO",
          },
        }),
      );
    });
  });

  it("RP-04 · 409 GOV_CASH_ITEM_DUPLICATE muestra error en el campo código", async () => {
    capacidades.add("gobierno_caja:view");
    capacidades.add("gobierno_caja:manage");

    apiFetchMock.mockImplementation(
      (url: string, options?: { method?: string }) => {
        if (url === "/gobierno/tesoreria/rubros" && options?.method === "POST") {
          return Promise.reject(
            new ApiError(409, {
              code: "GOV_CASH_ITEM_DUPLICATE",
              message: "Código duplicado",
              details: {},
            }),
          );
        }
        if (url === "/gobierno/tesoreria/rubros") {
          return Promise.resolve(listado);
        }
        return Promise.reject(new Error(`URL no esperada: ${url}`));
      },
    );

    const usuario = userEvent.setup();
    renderPage();

    await screen.findByText("Rubro Uno");

    await usuario.type(screen.getByLabelText(/^Código/), "RUB-001");
    await usuario.type(screen.getByLabelText(/^Nombre/), "Rubro Dos");
    await usuario.selectOptions(screen.getByLabelText(/^Tipo/), "INGRESO");
    await usuario.click(screen.getByRole("button", { name: "Registrar rubro" }));

    expect(
      await screen.findByText("Ya existe un rubro con este código."),
    ).toBeInTheDocument();
  });

  it("RP-05 · Inactivar envía PATCH con estado INACTIVO e ifMatch", async () => {
    capacidades.add("gobierno_caja:view");
    capacidades.add("gobierno_caja:manage");

    apiFetchMock.mockImplementation(
      (
        url: string,
        options?: { method?: string; body?: unknown; ifMatch?: string },
      ) => {
        if (url === "/gobierno/tesoreria/rubros/r1" && options?.method === "PATCH") {
          return Promise.resolve({
            ...rubro,
            estado: "INACTIVO",
            ...(options.body as object),
          });
        }
        if (url === "/gobierno/tesoreria/rubros") {
          return Promise.resolve(listado);
        }
        return Promise.reject(new Error(`URL no esperada: ${url}`));
      },
    );

    const usuario = userEvent.setup();
    renderPage();

    await screen.findByText("Rubro Uno");

    await usuario.click(
      screen.getByRole("button", { name: "Inactivar el rubro Rubro Uno" }),
    );

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/tesoreria/rubros/r1",
        expect.objectContaining({
          method: "PATCH",
          body: { estado: "INACTIVO" },
          ifMatch: "1",
        }),
      );
    });
  });

  it("RP-06 · edición del nombre envía PATCH con el nuevo nombre", async () => {
    capacidades.add("gobierno_caja:view");
    capacidades.add("gobierno_caja:manage");

    apiFetchMock.mockImplementation(
      (url: string, options?: { method?: string; body?: unknown }) => {
        if (url === "/gobierno/tesoreria/rubros/r1" && options?.method === "PATCH") {
          return Promise.resolve({ ...rubro, ...(options.body as object) });
        }
        if (url === "/gobierno/tesoreria/rubros") {
          return Promise.resolve(listado);
        }
        return Promise.reject(new Error(`URL no esperada: ${url}`));
      },
    );

    const usuario = userEvent.setup();
    renderPage();

    await screen.findByText("Rubro Uno");

    await usuario.click(
      screen.getByRole("button", { name: "Editar el rubro Rubro Uno" }),
    );

    const inputNombre = screen.getByLabelText("Nombre del rubro Rubro Uno");
    await usuario.clear(inputNombre);
    await usuario.type(inputNombre, "Rubro Uno Editado");
    await usuario.click(screen.getByRole("button", { name: "Guardar" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/tesoreria/rubros/r1",
        expect.objectContaining({
          method: "PATCH",
          body: { nombre: "Rubro Uno Editado" },
          ifMatch: "1",
        }),
      );
    });
  });

  it("RP-07 · 409 GOV_CASH_PROGRAM_STALE muestra role=alert", async () => {
    capacidades.add("gobierno_caja:view");
    capacidades.add("gobierno_caja:manage");

    apiFetchMock.mockImplementation(
      (url: string, options?: { method?: string }) => {
        if (url === "/gobierno/tesoreria/rubros/r1" && options?.method === "PATCH") {
          return Promise.reject(
            new ApiError(409, {
              code: "GOV_CASH_PROGRAM_STALE",
              message: "Versión desactualizada",
              details: {},
            }),
          );
        }
        if (url === "/gobierno/tesoreria/rubros") {
          return Promise.resolve(listado);
        }
        return Promise.reject(new Error(`URL no esperada: ${url}`));
      },
    );

    const usuario = userEvent.setup();
    renderPage();

    await screen.findByText("Rubro Uno");

    await usuario.click(
      screen.getByRole("button", { name: "Inactivar el rubro Rubro Uno" }),
    );

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent(
      "El rubro fue modificado por otra persona. Se recargaron los datos; revise los cambios antes de continuar.",
    );
  });

  it("RP-08 · filtro por tipo envía la consulta correcta", async () => {
    capacidades.add("gobierno_caja:view");

    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/tesoreria/rubros?tipo=DESEMBOLSO") {
        return Promise.resolve({ items: [] });
      }
      if (url === "/gobierno/tesoreria/rubros") {
        return Promise.resolve(listado);
      }
      return Promise.reject(new Error(`URL no esperada: ${url}`));
    });

    const usuario = userEvent.setup();
    renderPage();

    await screen.findByText("Rubro Uno");

    await usuario.selectOptions(
      screen.getByLabelText("Filtrar por tipo"),
      "DESEMBOLSO",
    );

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/tesoreria/rubros?tipo=DESEMBOLSO",
      );
    });
  });

  it("RP-09 · filtro por estado envía la consulta correcta", async () => {
    capacidades.add("gobierno_caja:view");

    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/tesoreria/rubros?estado=INACTIVO") {
        return Promise.resolve({ items: [] });
      }
      if (url === "/gobierno/tesoreria/rubros") {
        return Promise.resolve(listado);
      }
      return Promise.reject(new Error(`URL no esperada: ${url}`));
    });

    const usuario = userEvent.setup();
    renderPage();

    await screen.findByText("Rubro Uno");

    await usuario.selectOptions(
      screen.getByLabelText("Filtrar por estado"),
      "INACTIVO",
    );

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/tesoreria/rubros?estado=INACTIVO",
      );
    });
  });

  it("RP-10 · 422 con field_errors muestra el texto bajo el campo código", async () => {
    capacidades.add("gobierno_caja:view");
    capacidades.add("gobierno_caja:manage");

    apiFetchMock.mockImplementation(
      (url: string, options?: { method?: string }) => {
        if (url === "/gobierno/tesoreria/rubros" && options?.method === "POST") {
          return Promise.reject(
            new ApiError(422, {
              code: "GOV_CASH_ITEM_INVALID",
              message: "Datos inválidos",
              field_errors: {
                codigo: ["Este código ya no está disponible."],
              },
              details: {},
            }),
          );
        }
        if (url === "/gobierno/tesoreria/rubros") {
          return Promise.resolve(listado);
        }
        return Promise.reject(new Error(`URL no esperada: ${url}`));
      },
    );

    const usuario = userEvent.setup();
    renderPage();

    await screen.findByText("Rubro Uno");

    await usuario.type(screen.getByLabelText(/^Código/), "RUB-009");
    await usuario.type(screen.getByLabelText(/^Nombre/), "Rubro Nueve");
    await usuario.selectOptions(screen.getByLabelText(/^Tipo/), "INGRESO");
    await usuario.click(screen.getByRole("button", { name: "Registrar rubro" }));

    expect(
      await screen.findByText("Este código ya no está disponible."),
    ).toBeInTheDocument();
  });
});
