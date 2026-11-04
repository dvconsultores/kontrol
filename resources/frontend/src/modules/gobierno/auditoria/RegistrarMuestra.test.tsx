import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import type { FiltrosAuditoria } from "@/modules/gobierno/api";

const apiFetchMock = vi.fn();

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

const notify = vi.fn();

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify }),
}));

vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({
    activeCompanyId: "c1",
    activeCompany: { id: "c1", legal_name: "Contenedor 1" },
  }),
}));

const { RegistrarMuestra } = await import("./RegistrarMuestra");

function renderRegistrarMuestra(
  props: {
    filtros: FiltrosAuditoria;
    seleccion?: string[];
    onCancelar?: () => void;
    ruta?: string;
  },
) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[props.ruta ?? "/gobierno/auditoria"]}>
        <Routes>
          <Route
            path="/gobierno/auditoria"
            element={
              <RegistrarMuestra
                filtros={props.filtros}
                seleccion={props.seleccion ?? []}
                onCancelar={props.onCancelar ?? vi.fn()}
              />
            }
          />
          <Route
            path="/gobierno/auditoria/muestras/:id"
            element={<p>Destino muestras</p>}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const FILTROS: FiltrosAuditoria = { proceso: "ORG-03", texto: "  x " };

beforeEach(() => {
  apiFetchMock.mockReset();
  notify.mockReset();
  capacidades = new Set(["gobierno_auditoria:view", "gobierno_auditoria:sample"]);
  apiFetchMock.mockImplementation((url: string) => {
    if (url === "/gobierno/auditoria/muestras") {
      return Promise.resolve({
        id: "m1",
        codigo: "MU-2026-0001",
        titulo: "Muestra 1",
        criterio: "Criterio de la muestra",
        justificacion: "Justificación de la muestra",
        metodo: "ALEATORIA",
      });
    }
    return Promise.reject(
      new ApiError(500, { code: "INTERNAL", message: "Error" }),
    );
  });
});

describe("RegistrarMuestra", () => {
  it("REG-01 · sin gobierno_auditoria:sample muestra Sin permiso y sin formulario", () => {
    capacidades = new Set(["gobierno_auditoria:view"]);
    renderRegistrarMuestra({ filtros: FILTROS });

    expect(screen.getByText("Sin permiso")).toBeInTheDocument();
    expect(screen.queryByText("Registrar muestra")).not.toBeInTheDocument();
  });

  it("REG-02 · enviar vacío muestra errores locales y no llama a apiFetch", async () => {
    const usuario = userEvent.setup();
    renderRegistrarMuestra({ filtros: FILTROS });

    await usuario.click(
      screen.getByRole("button", { name: /Registrar muestra/ }),
    );

    expect(
      await screen.findByText("El título debe tener entre 3 y 200 caracteres."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("El criterio debe tener entre 10 y 2000 caracteres."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("La justificación debe tener entre 10 y 2000 caracteres."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Indique un tamaño entero mayor o igual a 1."),
    ).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("REG-03 · ALEATORIA envía body correcto, notifica y navega a la muestra creada", async () => {
    let cuerpo: unknown;
    apiFetchMock.mockImplementation((url: string, opciones?: RequestInit) => {
      if (url === "/gobierno/auditoria/muestras") {
        cuerpo = opciones?.body;
        return Promise.resolve({
          id: "m1",
          codigo: "MU-2026-0001",
          titulo: "Muestra 1",
          criterio: "Criterio de la muestra",
          justificacion: "Justificación de la muestra",
          metodo: "ALEATORIA",
        });
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    const usuario = userEvent.setup();
    renderRegistrarMuestra({ filtros: FILTROS });

    await usuario.type(
      screen.getByLabelText(/Título/),
      "Muestra de prueba",
    );
    await usuario.type(
      screen.getByLabelText(/Criterio de selección/),
      "Criterio válido para la muestra",
    );
    await usuario.type(
      screen.getByLabelText(/Justificación/),
      "Justificación válida para la muestra",
    );
    await usuario.type(screen.getByLabelText(/Tamaño de la muestra/), "3");
    await usuario.type(screen.getByLabelText(/Semilla/), "12345");

    await usuario.click(
      screen.getByRole("button", { name: /Registrar muestra/ }),
    );

    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith({
        type: "success",
        title: "Muestra MU-2026-0001 registrada",
      });
    });

    expect(apiFetchMock).toHaveBeenCalledWith(
      "/gobierno/auditoria/muestras",
      expect.objectContaining({
        method: "POST",
        body: expect.objectContaining({
          titulo: "Muestra de prueba",
          criterio: "Criterio válido para la muestra",
          justificacion: "Justificación válida para la muestra",
          metodo: "ALEATORIA",
          filtros: { proceso: "ORG-03", texto: "x" },
          tamano: 3,
          semilla: 12345,
        }),
      }),
    );

    expect(cuerpo).toEqual(
      expect.objectContaining({
        titulo: "Muestra de prueba",
        criterio: "Criterio válido para la muestra",
        justificacion: "Justificación válida para la muestra",
        metodo: "ALEATORIA",
        filtros: { proceso: "ORG-03", texto: "x" },
        tamano: 3,
        semilla: 12345,
      }),
    );

    expect(await screen.findByText("Destino muestras")).toBeInTheDocument();
  });

  it("REG-04 · ESPECIFICA envía eventos y sin tamano ni semilla", async () => {
    let cuerpo: unknown;
    apiFetchMock.mockImplementation((url: string, opciones?: RequestInit) => {
      if (url === "/gobierno/auditoria/muestras") {
        cuerpo = opciones?.body;
        return Promise.resolve({
          id: "m1",
          codigo: "MU-2026-0001",
          titulo: "Muestra 1",
          criterio: "Criterio de la muestra",
          justificacion: "Justificación de la muestra",
          metodo: "ESPECIFICA",
        });
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    const usuario = userEvent.setup();
    renderRegistrarMuestra({ filtros: FILTROS, seleccion: ["e1", "e2"] });

    await usuario.click(
      screen.getByRole("radio", { name: "Partidas específicas" }),
    );

    await usuario.type(
      screen.getByLabelText(/Título/),
      "Muestra específica",
    );
    await usuario.type(
      screen.getByLabelText(/Criterio de selección/),
      "Criterio válido para la muestra específica",
    );
    await usuario.type(
      screen.getByLabelText(/Justificación/),
      "Justificación válida para la muestra específica",
    );

    await usuario.click(
      screen.getByRole("button", { name: /Registrar muestra/ }),
    );

    await waitFor(() => {
      expect(notify).toHaveBeenCalled();
    });

    expect(cuerpo).toEqual(
      expect.objectContaining({
        metodo: "ESPECIFICA",
        eventos: ["e1", "e2"],
      }),
    );
    expect(cuerpo).not.toHaveProperty("tamano");
    expect(cuerpo).not.toHaveProperty("semilla");
  });

  it("REG-04b · ESPECIFICA con selección vacía muestra error y sin POST", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/auditoria/muestras") {
        return Promise.resolve({
          id: "m1",
          codigo: "MU-2026-0001",
          titulo: "Muestra 1",
          criterio: "Criterio de la muestra",
          justificacion: "Justificación de la muestra",
          metodo: "ESPECIFICA",
        });
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    const usuario = userEvent.setup();
    renderRegistrarMuestra({
      filtros: FILTROS,
      seleccion: [],
      ruta: "/gobierno/auditoria",
    });

    await usuario.click(
      screen.getByRole("radio", { name: "Partidas específicas" }),
    );
    await usuario.click(
      screen.getByRole("button", { name: /Registrar muestra/ }),
    );

    expect(
      await screen.findByText("Marque al menos una partida en la tabla."),
    ).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalledWith(
      "/gobierno/auditoria/muestras",
      expect.anything(),
    );
  });

  it("REG-05 · 422 GOV_AUDIT_INVALID_SAMPLE_SIZE muestra el mensaje junto al campo Tamaño", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/auditoria/muestras") {
        return Promise.reject(
          new ApiError(422, {
            code: "GOV_AUDIT_INVALID_SAMPLE_SIZE",
            message: "El tamaño solicitado supera la población filtrada.",
          }),
        );
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    const usuario = userEvent.setup();
    renderRegistrarMuestra({ filtros: FILTROS });

    await usuario.type(
      screen.getByLabelText(/Título/),
      "Muestra de prueba",
    );
    await usuario.type(
      screen.getByLabelText(/Criterio de selección/),
      "Criterio válido para la muestra",
    );
    await usuario.type(
      screen.getByLabelText(/Justificación/),
      "Justificación válida para la muestra",
    );
    await usuario.type(screen.getByLabelText(/Tamaño de la muestra/), "999");

    await usuario.click(
      screen.getByRole("button", { name: /Registrar muestra/ }),
    );

    expect(
      await screen.findByText("El tamaño solicitado supera la población filtrada."),
    ).toBeInTheDocument();
  });

  it("REG-06 · 422 GOV_AUDIT_EMPTY_POPULATION muestra role=alert con el mensaje", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/auditoria/muestras") {
        return Promise.reject(
          new ApiError(422, {
            code: "GOV_AUDIT_EMPTY_POPULATION",
            message: "Población vacía",
          }),
        );
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    const usuario = userEvent.setup();
    renderRegistrarMuestra({ filtros: FILTROS });

    await usuario.type(
      screen.getByLabelText(/Título/),
      "Muestra de prueba",
    );
    await usuario.type(
      screen.getByLabelText(/Criterio de selección/),
      "Criterio válido para la muestra",
    );
    await usuario.type(
      screen.getByLabelText(/Justificación/),
      "Justificación válida para la muestra",
    );
    await usuario.type(screen.getByLabelText(/Tamaño de la muestra/), "3");

    await usuario.click(
      screen.getByRole("button", { name: /Registrar muestra/ }),
    );

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent(
      "La población filtrada está vacía: amplíe los filtros.",
    );
  });

  it("REG-07 · Cancelar llama a onCancelar", async () => {
    const onCancelar = vi.fn();
    const usuario = userEvent.setup();
    renderRegistrarMuestra({ filtros: FILTROS, onCancelar });

    await usuario.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(onCancelar).toHaveBeenCalled();
  });
});
