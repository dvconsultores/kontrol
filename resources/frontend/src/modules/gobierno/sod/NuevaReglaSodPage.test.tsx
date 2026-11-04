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

const { NuevaReglaSodPage } = await import("./NuevaReglaSodPage");

const CATALOGO = {
  procesos: [
    {
      proceso: "DOC-02",
      nombre: "Actos administrativos",
      objeto: "GovernmentAct",
      acciones: [
        {
          codigo: "DOC02_REGISTRAR",
          etiqueta: "Registrar el acto",
          crea_objeto: true,
        },
        {
          codigo: "DOC02_EDITAR",
          etiqueta: "Editar el borrador del acto",
          crea_objeto: false,
        },
      ],
    },
    {
      proceso: "CTL-06",
      nombre: "Hallazgos y acciones correctivas",
      objeto: "GovernmentFinding",
      acciones: [
        {
          codigo: "CTL06_REGISTRAR",
          etiqueta: "Registrar el hallazgo",
          crea_objeto: true,
        },
        {
          codigo: "CTL06_RECOMENDAR",
          etiqueta: "Añadir una recomendación",
          crea_objeto: false,
        },
        {
          codigo: "CTL06_VERIFICAR",
          etiqueta: "Verificar y cerrar",
          crea_objeto: false,
        },
      ],
    },
  ],
};

const REGLA_CREADA = {
  id: "r1",
  codigo: "SOD-2026-0001",
  nombre: "Registro y recomendación",
  descripcion:
    "Quien registra un hallazgo no recomienda sobre él.",
  proceso: "CTL-06",
  accion_a: "CTL06_REGISTRAR",
  accion_a_etiqueta: "Registrar el hallazgo",
  accion_b: "CTL06_RECOMENDAR",
  accion_b_etiqueta: "Añadir una recomendación",
  bidireccional: false,
  alcance: "MISMO_OBJETO",
  modo: "BLOQUEAR",
  vigente_desde: "2026-11-04",
  vigente_hasta: null,
  estado: "BORRADOR",
  en_vigor: false,
  version: 1,
  creada_por: "ua",
  creada_en: "2026-11-04T12:00:00Z",
  activada_por: null,
  activada_en: null,
  cerrada_por: null,
  cerrada_en: null,
  motivo_cierre: null,
  conflictos: 0,
  historia: [
    {
      tipo: "CREADA",
      detalle: null,
      registrado_por: "ua",
      registrado_en: "2026-11-04T12:00:00Z",
    },
  ],
};

function renderPage(ruta = "/gobierno/sod/nueva") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[ruta]}>
        <Routes>
          <Route path="/gobierno/sod/nueva" element={<NuevaReglaSodPage />} />
          <Route
            path="/gobierno/sod/:reglaId"
            element={<p>Ficha de la regla</p>}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("NuevaReglaSodPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    notifyMock.mockReset();
    capacidades = new Set<string>();
  });

  it("NRS-01 · sin gobierno_sod:manage muestra «Sin acceso»", async () => {
    renderPage();

    expect(
      await screen.findByRole("heading", { name: "Sin acceso" }),
    ).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("NRS-02 · con manage, al elegir el proceso CTL-06 y la acción A «Añadir una recomendación», el select de la acción B NO ofrece «Registrar el hallazgo» ni la propia A; al marcar «En ambos sentidos» sí ofrece «Registrar el hallazgo»", async () => {
    capacidades.add("gobierno_sod:manage");
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/sod/acciones") {
        return Promise.resolve(CATALOGO);
      }
      return Promise.reject(new Error(`URL no esperada: ${url}`));
    });

    renderPage();
    const usuario = userEvent.setup();

    await screen.findByLabelText(/^Proceso/);

    await usuario.selectOptions(
      screen.getByLabelText(/^Proceso/),
      "CTL-06",
    );

    await usuario.selectOptions(
      screen.getByLabelText(/^Acción A/),
      "CTL06_RECOMENDAR",
    );

    const selectB = screen.getByLabelText(/^Acción B/) as HTMLSelectElement;
    const opcionesB = within(selectB).getAllByRole("option");
    const etiquetasB = opcionesB.map((opcion) => opcion.textContent);

    expect(etiquetasB).not.toContain("Registrar el hallazgo");
    expect(etiquetasB).not.toContain("Añadir una recomendación");

    await usuario.click(screen.getByLabelText("En ambos sentidos"));

    const opcionesBTrasMarcar = within(selectB).getAllByRole("option");
    const etiquetasBTrasMarcar = opcionesBTrasMarcar.map(
      (opcion) => opcion.textContent,
    );

    expect(etiquetasBTrasMarcar).toContain("Registrar el hallazgo");
  });

  it("NRS-03 · enviar el formulario vacío (botón «Registrar regla») muestra \"Elija el proceso.\" y no hace POST", async () => {
    capacidades.add("gobierno_sod:manage");
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/sod/acciones") {
        return Promise.resolve(CATALOGO);
      }
      return Promise.reject(new Error(`URL no esperada: ${url}`));
    });

    renderPage();
    const usuario = userEvent.setup();

    await screen.findByLabelText(/^Proceso/);

    await usuario.click(
      screen.getByRole("button", { name: "Registrar regla" }),
    );

    expect(await screen.findByText("Elija el proceso.")).toBeInTheDocument();

    const postCalls = apiFetchMock.mock.calls.filter(
      ([url, options]) =>
        url === "/gobierno/sod/reglas" &&
        options?.method === "POST",
    );
    expect(postCalls).toHaveLength(0);
  });

  it("NRS-04 · con todo válido hace POST correcto, notifica éxito y navega a la ficha", async () => {
    capacidades.add("gobierno_sod:manage");
    apiFetchMock.mockImplementation((url: string, options?: RequestInit) => {
      if (url === "/gobierno/sod/acciones") {
        return Promise.resolve(CATALOGO);
      }
      if (url === "/gobierno/sod/reglas" && options?.method === "POST") {
        return Promise.resolve(REGLA_CREADA);
      }
      return Promise.reject(new Error(`URL no esperada: ${url}`));
    });

    renderPage();
    const usuario = userEvent.setup();

    await screen.findByLabelText(/^Proceso/);

    await usuario.selectOptions(
      screen.getByLabelText(/^Proceso/),
      "CTL-06",
    );
    await usuario.selectOptions(
      screen.getByLabelText(/^Acción A/),
      "CTL06_REGISTRAR",
    );
    await usuario.selectOptions(
      screen.getByLabelText(/^Acción B/),
      "CTL06_RECOMENDAR",
    );
    await usuario.type(
      screen.getByLabelText(/^Nombre/),
      "Registro y recomendación",
    );
    await usuario.type(
      screen.getByLabelText(/^Razón/),
      "Quien registra un hallazgo no recomienda sobre él.",
    );

    await usuario.click(
      screen.getByRole("button", { name: "Registrar regla" }),
    );

    await waitFor(() => {
      expect(
        screen.getByText("Ficha de la regla"),
      ).toBeInTheDocument();
    });

    const postCalls = apiFetchMock.mock.calls.filter(
      ([url, options]) =>
        url === "/gobierno/sod/reglas" && options?.method === "POST",
    );
    expect(postCalls).toHaveLength(1);

    const body = postCalls[0][1]
      ? (postCalls[0][1] as { body?: unknown }).body
      : undefined;
    expect(body).toEqual(
      expect.objectContaining({
        proceso: "CTL-06",
        accion_a: "CTL06_REGISTRAR",
        accion_b: "CTL06_RECOMENDAR",
        bidireccional: false,
        nombre: "Registro y recomendación",
        descripcion:
          "Quien registra un hallazgo no recomienda sobre él.",
        vigente_desde: expect.any(String),
        vigente_hasta: null,
      }),
    );

    expect(notifyMock).toHaveBeenCalledWith({
      type: "success",
      title: "Regla registrada en borrador",
    });
  });

  it("NRS-05 · si el POST responde 422 GOV_SOD_RULE_INVALID se muestra un alert con ese texto", async () => {
    capacidades.add("gobierno_sod:manage");
    apiFetchMock.mockImplementation((url: string, options?: RequestInit) => {
      if (url === "/gobierno/sod/acciones") {
        return Promise.resolve(CATALOGO);
      }
      if (url === "/gobierno/sod/reglas" && options?.method === "POST") {
        return Promise.reject(
          new ApiError(422, {
            code: "GOV_SOD_RULE_INVALID",
            message:
              "Una acción que crea el objeto no puede ser la acción B",
          }),
        );
      }
      return Promise.reject(
        new ApiError(500, { code: "NOT_EXPECTED", message: "No esperada" }),
      );
    });

    renderPage();
    const usuario = userEvent.setup();

    await screen.findByLabelText(/^Proceso/);

    await usuario.selectOptions(
      screen.getByLabelText(/^Proceso/),
      "CTL-06",
    );
    await usuario.selectOptions(
      screen.getByLabelText(/^Acción A/),
      "CTL06_REGISTRAR",
    );
    await usuario.selectOptions(
      screen.getByLabelText(/^Acción B/),
      "CTL06_RECOMENDAR",
    );
    await usuario.type(
      screen.getByLabelText(/^Nombre/),
      "Registro y recomendación",
    );
    await usuario.type(
      screen.getByLabelText(/^Razón/),
      "Quien registra un hallazgo no recomienda sobre él.",
    );

    await usuario.click(
      screen.getByRole("button", { name: "Registrar regla" }),
    );

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent(
      "Una acción que crea el objeto no puede ser la acción B",
    );
  });
});
