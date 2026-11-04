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
  useCompany: () => ({ activeCompanyId: "c1", activeCompany: { id: "c1", legal_name: "Contenedor 1" } }),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: notifyMock }),
}));

const { ReglaSodPage } = await import("./ReglaSodPage");

const detalleBase = {
  id: "r1",
  codigo: "SOD-2026-0001",
  nombre: "Registro y recomendación",
  descripcion: "Quien registra un hallazgo no recomienda sobre él.",
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
  historia: [{ tipo: "CREADA", detalle: null, registrado_por: "ua", registrado_en: "2026-11-04T12:00:00Z" }],
} as const;

const detalleVigente = {
  ...detalleBase,
  estado: "VIGENTE",
  en_vigor: true,
  activada_por: "ua",
  activada_en: "2026-11-04T13:00:00Z",
  version: 2,
  historia: [
    ...detalleBase.historia,
    { tipo: "ACTIVADA", detalle: null, registrado_por: "ua", registrado_en: "2026-11-04T13:00:00Z" },
  ],
} as const;

function renderizar(ruta = "/gobierno/sod/r1") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[ruta]}>
        <Routes>
          <Route path="/gobierno/sod/:reglaId" element={<ReglaSodPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function responderDetalle(detalle: unknown) {
  apiFetchMock.mockImplementation(async () => detalle);
}

beforeEach(() => {
  apiFetchMock.mockReset();
  notifyMock.mockReset();
  capacidades = new Set<string>();
});

describe("ReglaSodPage", () => {
  it("RSD-01 · BORRADOR con gobierno_sod:manage y :activate muestra «Editar borrador» y «Activar regla»; «Activar regla» hace POST y notify success", async () => {
    capacidades = new Set(["gobierno_sod:manage", "gobierno_sod:activate"]);

    const detalleActivado = {
      ...detalleBase,
      estado: "VIGENTE",
      en_vigor: true,
      version: 2,
      activada_por: "ua",
      activada_en: "2026-11-04T13:00:00Z",
      historia: [
        ...detalleBase.historia,
        { tipo: "ACTIVADA", detalle: null, registrado_por: "ua", registrado_en: "2026-11-04T13:00:00Z" },
      ],
    };

    const detalleActual = detalleBase;
    apiFetchMock.mockImplementation(async (url: unknown) => {
      if (typeof url === "string" && url.endsWith("/activar")) {
        return detalleActivado;
      }
      return detalleActual;
    });

    renderizar();

    expect(await screen.findByText("Editar borrador")).toBeInTheDocument();
    expect(screen.getByText("Activar regla")).toBeInTheDocument();

    await userEvent.click(screen.getByText("Activar regla"));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/sod/reglas/r1/activar",
        expect.objectContaining({ method: "POST", body: {}, ifMatch: "1" }),
      );
    });

    await waitFor(() => {
      expect(notifyMock).toHaveBeenCalledWith({ type: "success", title: "Regla activada" });
    });
  });

  it("RSD-02 · BORRADOR solo con :view y :manage: no hay «Activar regla»", async () => {
    capacidades = new Set(["gobierno_sod:view", "gobierno_sod:manage"]);
    responderDetalle(detalleBase);

    renderizar();

    expect(await screen.findByText("Editar borrador")).toBeInTheDocument();
    expect(screen.queryByText("Activar regla")).not.toBeInTheDocument();
  });

  it("RSD-03 · activar con 409 GOV_SOD_RULE_DUPLICATE muestra un alert con el mensaje", async () => {
    capacidades = new Set(["gobierno_sod:manage", "gobierno_sod:activate"]);

    apiFetchMock.mockImplementation(async (url: unknown) => {
      if (typeof url === "string" && url.endsWith("/activar")) {
        throw new ApiError(409, { code: "GOV_SOD_RULE_DUPLICATE", message: "Conflicto" });
      }
      return detalleBase;
    });

    renderizar();

    await userEvent.click(await screen.findByText("Activar regla"));

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent(
      "Ya hay una regla vigente con esas dos acciones en este proceso. Cierre la otra antes de activar esta.",
    );
  });

  it("RSD-04 · VIGENTE con :activate: «Cerrar regla» abre el panel; con motivo corto deshabilita; con motivo válido hace POST", async () => {
    capacidades = new Set(["gobierno_sod:activate"]);

    const detalleCerrado = {
      ...detalleVigente,
      estado: "CERRADA",
      en_vigor: false,
      version: 3,
      cerrada_por: "ua",
      cerrada_en: "2026-11-04T14:00:00Z",
      motivo_cierre: "Motivo de cierre suficientemente largo",
      historia: [
        ...detalleVigente.historia,
        {
          tipo: "CERRADA",
          detalle: { motivo: "Motivo de cierre suficientemente largo" },
          registrado_por: "ua",
          registrado_en: "2026-11-04T14:00:00Z",
        },
      ],
    };

    apiFetchMock.mockImplementation(async (url: unknown) => {
      if (typeof url === "string" && url.endsWith("/cerrar")) {
        return detalleCerrado;
      }
      return detalleVigente;
    });

    renderizar();

    await userEvent.click(await screen.findByText("Cerrar regla"));

    const motivo = await screen.findByLabelText(/^Motivo/);
    const confirmar = screen.getByRole("button", { name: "Confirmar cierre" });

    expect(confirmar).toBeDisabled();

    await userEvent.type(motivo, "corto");
    expect(confirmar).toBeDisabled();

    await userEvent.clear(motivo);
    await userEvent.type(motivo, "Motivo de cierre suficientemente largo");
    await waitFor(() => expect(confirmar).toBeEnabled());

    await userEvent.click(confirmar);

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/sod/reglas/r1/cerrar",
        expect.objectContaining({
          method: "POST",
          body: { motivo: "Motivo de cierre suficientemente largo" },
          ifMatch: "2",
        }),
      );
    });

    await waitFor(() => {
      expect(notifyMock).toHaveBeenCalledWith({ type: "success", title: "Regla cerrada" });
    });
  });

  it("RSD-05 · editar: cambiar solo el nombre y guardar hace PATCH con body exacto { nombre } e ifMatch", async () => {
    capacidades = new Set(["gobierno_sod:manage", "gobierno_sod:activate"]);

    const detalleEditado = {
      ...detalleBase,
      nombre: "Nombre nuevo",
      version: 2,
    };

    apiFetchMock.mockImplementation(async (url: unknown, init: unknown) => {
      const method =
        init && typeof init === "object" && "method" in init
          ? (init as { method?: unknown }).method
          : undefined;
      if (method === "PATCH") {
        return detalleEditado;
      }
      if (typeof url === "string" && url === "/gobierno/sod/reglas/r1") {
        return detalleBase;
      }
      return detalleBase;
    });

    renderizar();

    await userEvent.click(await screen.findByText("Editar borrador"));

    const nombreInput = await screen.findByLabelText(/^Nombre/);
    await userEvent.clear(nombreInput);
    await userEvent.type(nombreInput, "Nombre nuevo");
    await userEvent.click(screen.getByText("Guardar", { selector: "button" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/sod/reglas/r1",
        expect.objectContaining({
          method: "PATCH",
          body: { nombre: "Nombre nuevo" },
          ifMatch: "1",
        }),
      );
    });
  });

  it("RSD-06 · la historia muestra la fila «Registrada» con el usuario ua; y 404 muestra «Regla no encontrada»", async () => {
    capacidades = new Set(["gobierno_sod:view"]);
    responderDetalle(detalleBase);

    const { unmount } = renderizar();

    await screen.findByRole("heading", { level: 1, name: "Regla SOD-2026-0001" });

    const region = await screen.findByRole("region", { name: "Tabla de historia de la regla" });
    expect(within(region).getByText("Registrada")).toBeInTheDocument();
    expect(within(region).getByText("ua")).toBeInTheDocument();

    unmount();

    apiFetchMock.mockImplementation(async () => {
      throw new ApiError(404, { code: "GOV_SOD_RULE_NOT_FOUND", message: "No encontrada" });
    });

    renderizar("/gobierno/sod/r1");

    const emptyState = await screen.findByText("Regla no encontrada");
    expect(emptyState).toBeInTheDocument();
  });
});
