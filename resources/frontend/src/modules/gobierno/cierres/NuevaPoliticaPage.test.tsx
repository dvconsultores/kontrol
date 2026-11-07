import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";

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

const { NuevaPoliticaPage } = await import("./NuevaPoliticaPage");

const CATALOGO = {
  acciones: [
    {
      codigo: "ORG02_CERRAR_ESTRUCTURA",
      etiqueta: "Cerrar estructura del ejercicio",
    },
    {
      codigo: "TRE02_CERRAR_PROGRAMA",
      etiqueta: "Cerrar programa financiero",
    },
  ],
  tipos: [
    {
      codigo: "HALLAZGOS_ABIERTOS",
      etiqueta: "Hallazgos abiertos",
      requiere_riesgo: true,
    },
    {
      codigo: "ACTOS_SIN_EFICACIA",
      etiqueta: "Actos sin eficacia",
      requiere_riesgo: false,
    },
  ],
};

const POLITICA_CREADA = {
  id: "p1",
  codigo: "PC-2026-0001",
  nombre: "Cierre de estructura 2026",
  accion_cierre: "ORG02_CERRAR_ESTRUCTURA",
  fundamento: "Cierre anual obligatorio de la estructura del ejercicio.",
  estado: "BORRADOR",
  vigente_desde: "2026-11-04",
  vigente_hasta: null,
  efectiva_hoy: false,
  version: 1,
  activada_por: null,
  activada_en: null,
  retirada_por: null,
  retirada_en: null,
  motivo_retiro: null,
  controles: [],
  historia: [
    {
      evento: "CREADA",
      detalle: null,
      usuario: "ua",
      instante: "2026-11-04T12:00:00Z",
    },
  ],
};

function renderPage(ruta = "/gobierno/cierres/nueva") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[ruta]}>
        <Routes>
          <Route
            path="/gobierno/cierres/nueva"
            element={<NuevaPoliticaPage />}
          />
          <Route
            path="/gobierno/cierres/:politicaId"
            element={<p>Ficha de la política</p>}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("NuevaPoliticaPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    notifyMock.mockReset();
    capacidades = new Set<string>();
  });

  it("NPC-01 · sin gobierno_cierre:manage muestra «Sin acceso»", async () => {
    renderPage();

    expect(
      await screen.findByRole("heading", { name: "Sin acceso" }),
    ).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("NPC-02 · con manage, al cargar el catálogo se muestran las acciones del backend", async () => {
    capacidades.add("gobierno_cierre:manage");
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/cierres/catalogo") {
        return Promise.resolve(CATALOGO);
      }
      return Promise.reject(new Error(`URL no esperada: ${url}`));
    });

    renderPage();

    await screen.findByLabelText(/^Acción de cierre/);

    const selectAccion = screen.getByLabelText(
      /^Acción de cierre/,
    ) as HTMLSelectElement;
    const opciones = within(selectAccion).getAllByRole("option");
    const etiquetas = opciones.map((opcion) => opcion.textContent);

    expect(etiquetas).toContain("Cerrar estructura del ejercicio");
    expect(etiquetas).toContain("Cerrar programa financiero");
  });

  it("NPC-03 · enviar el formulario vacío (botón «Crear política») muestra \"Elija la acción de cierre.\" y no hace POST", async () => {
    capacidades.add("gobierno_cierre:manage");
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/cierres/catalogo") {
        return Promise.resolve(CATALOGO);
      }
      return Promise.reject(new Error(`URL no esperada: ${url}`));
    });

    renderPage();
    const usuario = userEvent.setup();

    await screen.findByLabelText(/^Acción de cierre/);

    await usuario.click(
      screen.getByRole("button", { name: "Crear política" }),
    );

    expect(
      await screen.findByText("Elija la acción de cierre."),
    ).toBeInTheDocument();

    const postCalls = apiFetchMock.mock.calls.filter(
      ([url, options]) =>
        url === "/gobierno/cierres/politicas" &&
        options?.method === "POST",
    );
    expect(postCalls).toHaveLength(0);
  });

  it("NPC-04 · con todo válido hace POST correcto, notifica éxito y navega a la ficha", async () => {
    capacidades.add("gobierno_cierre:manage");
    apiFetchMock.mockImplementation((url: string, options?: RequestInit) => {
      if (url === "/gobierno/cierres/catalogo") {
        return Promise.resolve(CATALOGO);
      }
      if (
        url === "/gobierno/cierres/politicas" &&
        options?.method === "POST"
      ) {
        return Promise.resolve(POLITICA_CREADA);
      }
      return Promise.reject(new Error(`URL no esperada: ${url}`));
    });

    renderPage();
    const usuario = userEvent.setup();

    await screen.findByLabelText(/^Acción de cierre/);

    await usuario.selectOptions(
      screen.getByLabelText(/^Acción de cierre/),
      "ORG02_CERRAR_ESTRUCTURA",
    );
    await usuario.type(
      screen.getByLabelText(/^Nombre de la política/),
      "Cierre de estructura 2026",
    );
    await usuario.type(
      screen.getByLabelText(/^Fundamento/),
      "Cierre anual obligatorio de la estructura del ejercicio.",
    );

    await usuario.click(
      screen.getByRole("button", { name: "Crear política" }),
    );

    await waitFor(() => {
      expect(
        screen.getByText("Ficha de la política"),
      ).toBeInTheDocument();
    });

    const postCalls = apiFetchMock.mock.calls.filter(
      ([url, options]) =>
        url === "/gobierno/cierres/politicas" && options?.method === "POST",
    );
    expect(postCalls).toHaveLength(1);

    const body = postCalls[0][1]
      ? (postCalls[0][1] as { body?: unknown }).body
      : undefined;
    expect(body).toEqual(
      expect.objectContaining({
        nombre: "Cierre de estructura 2026",
        accion_cierre: "ORG02_CERRAR_ESTRUCTURA",
        fundamento: "Cierre anual obligatorio de la estructura del ejercicio.",
        vigente_desde: expect.any(String),
        vigente_hasta: null,
      }),
    );

    const headers = postCalls[0][1] as { headers?: Record<string, string> };
    expect(headers.headers).toBeUndefined();

    expect(notifyMock).toHaveBeenCalledWith({
      type: "success",
      title: "Política registrada en borrador",
    });
  });

  it("NPC-05 · si el POST responde 422 con error de validación se muestra el mensaje", async () => {
    capacidades.add("gobierno_cierre:manage");
    apiFetchMock.mockImplementation((url: string, options?: RequestInit) => {
      if (url === "/gobierno/cierres/catalogo") {
        return Promise.resolve(CATALOGO);
      }
      if (
        url === "/gobierno/cierres/politicas" &&
        options?.method === "POST"
      ) {
        return Promise.reject(
          new ApiError(422, {
            code: "VALIDATION_ERROR",
            message: "El nombre debe tener entre 3 y 200 caracteres.",
            field_errors: {
              nombre: ["El nombre debe tener entre 3 y 200 caracteres."],
            },
          }),
        );
      }
      return Promise.reject(
        new ApiError(500, { code: "NOT_EXPECTED", message: "No esperada" }),
      );
    });

    renderPage();
    const usuario = userEvent.setup();

    await screen.findByLabelText(/^Acción de cierre/);

    await usuario.selectOptions(
      screen.getByLabelText(/^Acción de cierre/),
      "ORG02_CERRAR_ESTRUCTURA",
    );
    await usuario.type(
      screen.getByLabelText(/^Nombre de la política/),
      "Cierre de estructura 2026",
    );
    await usuario.type(
      screen.getByLabelText(/^Fundamento/),
      "Cierre anual obligatorio de la estructura del ejercicio.",
    );

    await usuario.click(
      screen.getByRole("button", { name: "Crear política" }),
    );

    expect(
      await screen.findByText(
        "El nombre debe tener entre 3 y 200 caracteres.",
      ),
    ).toBeInTheDocument();
  });

  it("NPC-06 · si el POST responde 422 con error general se muestra un alert con el mensaje", async () => {
    capacidades.add("gobierno_cierre:manage");
    apiFetchMock.mockImplementation((url: string, options?: RequestInit) => {
      if (url === "/gobierno/cierres/catalogo") {
        return Promise.resolve(CATALOGO);
      }
      if (
        url === "/gobierno/cierres/politicas" &&
        options?.method === "POST"
      ) {
        return Promise.reject(
          new ApiError(422, {
            code: "GOV_CLOSURE_POLICY_INVALID",
            message: "La política no cumple los requisitos.",
          }),
        );
      }
      return Promise.reject(
        new ApiError(500, { code: "NOT_EXPECTED", message: "No esperada" }),
      );
    });

    renderPage();
    const usuario = userEvent.setup();

    await screen.findByLabelText(/^Acción de cierre/);

    await usuario.selectOptions(
      screen.getByLabelText(/^Acción de cierre/),
      "ORG02_CERRAR_ESTRUCTURA",
    );
    await usuario.type(
      screen.getByLabelText(/^Nombre de la política/),
      "Cierre de estructura 2026",
    );
    await usuario.type(
      screen.getByLabelText(/^Fundamento/),
      "Cierre anual obligatorio de la estructura del ejercicio.",
    );

    await usuario.click(
      screen.getByRole("button", { name: "Crear política" }),
    );

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent(
      "La política no cumple los requisitos.",
    );
  });

  it("NPC-07 · si el POST responde 403 se notifica y no navega", async () => {
    capacidades.add("gobierno_cierre:manage");
    apiFetchMock.mockImplementation((url: string, options?: RequestInit) => {
      if (url === "/gobierno/cierres/catalogo") {
        return Promise.resolve(CATALOGO);
      }
      if (
        url === "/gobierno/cierres/politicas" &&
        options?.method === "POST"
      ) {
        return Promise.reject(
          new ApiError(403, {
            code: "FORBIDDEN",
            message: "No tiene permiso",
          }),
        );
      }
      return Promise.reject(
        new ApiError(500, { code: "NOT_EXPECTED", message: "No esperada" }),
      );
    });

    renderPage();
    const usuario = userEvent.setup();

    await screen.findByLabelText(/^Acción de cierre/);

    await usuario.selectOptions(
      screen.getByLabelText(/^Acción de cierre/),
      "ORG02_CERRAR_ESTRUCTURA",
    );
    await usuario.type(
      screen.getByLabelText(/^Nombre de la política/),
      "Cierre de estructura 2026",
    );
    await usuario.type(
      screen.getByLabelText(/^Fundamento/),
      "Cierre anual obligatorio de la estructura del ejercicio.",
    );

    await usuario.click(
      screen.getByRole("button", { name: "Crear política" }),
    );

    await waitFor(() => {
      expect(notifyMock).toHaveBeenCalledWith({
        type: "error",
        title: "No tiene permiso para registrar políticas",
      });
    });
  });
});
