import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import { NuevoProgramaPage } from "./NuevoProgramaPage";

const apiFetchMock = vi.fn();
const notifyMock = vi.fn();
const invalidateQueriesMock = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

vi.mock("@tanstack/react-query", async (original) => ({
  ...(await original<typeof import("@tanstack/react-query")>()),
  useQueryClient: () => ({
    invalidateQueries: invalidateQueriesMock,
  }),
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

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: notifyMock }),
}));

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/gobierno/tesoreria/programacion/nueva"]}>
        <Routes>
          <Route path="/gobierno/tesoreria/programacion/nueva" element={<NuevoProgramaPage />} />
          <Route path="/gobierno/tesoreria/programacion/:id" element={<div>Programa creado</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("NPP", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    notifyMock.mockReset();
    invalidateQueriesMock.mockReset();
    invalidateQueriesMock.mockResolvedValue(undefined);
    capacidades = new Set<string>();
    apiFetchMock.mockImplementation((url: string, options?: { method?: string }) => {
      if (url === "/gobierno/tesoreria/programas" && options?.method === "POST") {
        return Promise.resolve({
          id: "p1",
          ejercicio: 2026,
          moneda: "VES",
          mes_inicial: 1,
          estado: "BORRADOR",
          version: 1,
        });
      }
      return Promise.reject(new Error(`URL no esperada: ${url}`));
    });
  });

  it("NP-01 · sin manage: «Sin acceso» y no se ve el formulario", async () => {
    renderPage();

    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
    expect(
      screen.getByText("No tiene permiso para registrar programas financieros."),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText(/^Ejercicio/)).not.toBeInTheDocument();
  });

  it("NP-02 · envío correcto: POST /gobierno/tesoreria/programas con el cuerpo exacto y notificación", async () => {
    capacidades.add("gobierno_caja:manage");
    renderPage();

    const user = userEvent.setup();
    await screen.findByLabelText(/^Ejercicio/);
    await user.clear(screen.getByLabelText(/^Ejercicio/));
    await user.type(screen.getByLabelText(/^Ejercicio/), "2026");
    await user.selectOptions(screen.getByLabelText(/^Moneda/), "VES");
    await user.selectOptions(screen.getByLabelText(/^Mes inicial/), "2");
    await user.click(screen.getByRole("button", { name: "Registrar programa" }));

    await waitFor(() => {
      const postCalls = apiFetchMock.mock.calls.filter(
        ([url, options]) =>
          url === "/gobierno/tesoreria/programas" && options?.method === "POST",
      );
      expect(postCalls).toHaveLength(1);
      expect(postCalls[0][1].body).toEqual({
        ejercicio: 2026,
        moneda: "VES",
        mes_inicial: 2,
      });
    });

    await waitFor(() => {
      expect(notifyMock).toHaveBeenCalledWith({
        type: "success",
        title: "Programa registrado",
      });
    });

    await waitFor(() => {
      expect(invalidateQueriesMock).toHaveBeenCalled();
    });

    expect(screen.getByText("Programa creado")).toBeInTheDocument();
  });

  it("NP-03 · 409 GOV_CASH_PROGRAM_DUPLICATE: error bajo ejercicio", async () => {
    capacidades.add("gobierno_caja:manage");
    apiFetchMock.mockImplementation((url: string, options?: { method?: string }) => {
      if (url === "/gobierno/tesoreria/programas" && options?.method === "POST") {
        return Promise.reject(
          new ApiError(409, {
            code: "GOV_CASH_PROGRAM_DUPLICATE",
            message: "Ya hay un programa de ese ejercicio y moneda.",
            details: {},
          }),
        );
      }
      return Promise.reject(new Error(`URL no esperada: ${url}`));
    });
    renderPage();

    const user = userEvent.setup();
    await screen.findByLabelText(/^Ejercicio/);
    await user.clear(screen.getByLabelText(/^Ejercicio/));
    await user.type(screen.getByLabelText(/^Ejercicio/), "2026");
    await user.selectOptions(screen.getByLabelText(/^Moneda/), "VES");
    await user.click(screen.getByRole("button", { name: "Registrar programa" }));

    expect(await screen.findByText("Ya hay un programa de ese ejercicio y moneda.")).toBeInTheDocument();
    expect(screen.getByLabelText(/^Ejercicio/)).toHaveAttribute("aria-invalid", "true");
  });

  it("NP-04 · 422 del servidor: fieldErrors bajo campos", async () => {
    capacidades.add("gobierno_caja:manage");
    apiFetchMock.mockImplementation((url: string, options?: { method?: string }) => {
      if (url === "/gobierno/tesoreria/programas" && options?.method === "POST") {
        return Promise.reject(
          new ApiError(422, {
            code: "VALIDATION_ERROR",
            message: "Datos inválidos",
            field_errors: {
              ejercicio: ["El ejercicio es obligatorio."],
              moneda: ["La moneda es obligatoria."],
            },
          }),
        );
      }
      return Promise.reject(new Error(`URL no esperada: ${url}`));
    });
    renderPage();

    const user = userEvent.setup();
    await screen.findByLabelText(/^Ejercicio/);
    await user.clear(screen.getByLabelText(/^Ejercicio/));
    await user.type(screen.getByLabelText(/^Ejercicio/), "2026");
    await user.selectOptions(screen.getByLabelText(/^Moneda/), "VES");
    await user.click(screen.getByRole("button", { name: "Registrar programa" }));

    expect(await screen.findByText("El ejercicio es obligatorio.")).toBeInTheDocument();
    expect(screen.getByText("La moneda es obligatoria.")).toBeInTheDocument();
  });
});
