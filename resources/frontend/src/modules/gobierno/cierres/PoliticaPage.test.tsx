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

const { PoliticaPage } = await import("./PoliticaPage");

const catalogoBase = {
  acciones: [{ codigo: "ORG02_CERRAR_ESTRUCTURA", etiqueta: "Cerrar estructura del ejercicio" }],
  tipos: [
    { codigo: "HALLAZGOS_ABIERTOS", etiqueta: "Hallazgos abiertos", requiere_riesgo: true },
    { codigo: "ACTOS_SIN_EFICACIA", etiqueta: "Actos sin eficacia", requiere_riesgo: false },
  ],
};

const detalleBase = {
  id: "p1",
  codigo: "PC-2026-0001",
  nombre: "Política de cierre de estructura",
  accion_cierre: "ORG02_CERRAR_ESTRUCTURA",
  fundamento: "Fundamento de la política",
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
  controles: [
    {
      id: "c1",
      tipo: "HALLAZGOS_ABIERTOS",
      riesgo_minimo: "ALTO",
      materialidad: "Materialidad significativa",
    },
  ],
  historia: [
    { evento: "CREADA", detalle: null, usuario: "ua", instante: "2026-11-04T12:00:00Z" },
  ],
};

const detalleVigente = {
  ...detalleBase,
  estado: "VIGENTE",
  efectiva_hoy: true,
  version: 2,
  activada_por: "ua",
  activada_en: "2026-11-04T13:00:00Z",
  historia: [
    ...detalleBase.historia,
    { evento: "ACTIVADA", detalle: null, usuario: "ua", instante: "2026-11-04T13:00:00Z" },
  ],
};

function renderizar(ruta = "/gobierno/cierres/p1") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[ruta]}>
        <Routes>
          <Route path="/gobierno/cierres/:politicaId" element={<PoliticaPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function responderDetalle(detalle: unknown, catalogo: unknown = catalogoBase) {
  apiFetchMock.mockImplementation(async (url: unknown) => {
    if (typeof url === "string" && url.includes("/catalogo")) {
      return catalogo;
    }
    return detalle;
  });
}

beforeEach(() => {
  apiFetchMock.mockReset();
  notifyMock.mockReset();
  capacidades = new Set<string>();
});

describe("PoliticaPage", () => {
  it("PC-01 · BORRADOR con gobierno_cierre:manage y :activate muestra «Editar», «Añadir control», «Activar» y «Retirar»; «Activar» hace POST y notify success", async () => {
    capacidades = new Set(["gobierno_cierre:manage", "gobierno_cierre:activate"]);

    const detalleActivado = {
      ...detalleBase,
      estado: "VIGENTE",
      efectiva_hoy: true,
      version: 2,
      activada_por: "ua",
      activada_en: "2026-11-04T13:00:00Z",
      historia: [
        ...detalleBase.historia,
        { evento: "ACTIVADA", detalle: null, usuario: "ua", instante: "2026-11-04T13:00:00Z" },
      ],
    };

    const detalleActual = detalleBase;
    apiFetchMock.mockImplementation(async (url: unknown) => {
      if (typeof url === "string" && url.includes("/catalogo")) {
        return catalogoBase;
      }
      if (typeof url === "string" && url.endsWith("/activar")) {
        return detalleActivado;
      }
      return detalleActual;
    });

    renderizar();

    expect(await screen.findByText("Editar")).toBeInTheDocument();
    expect(screen.getByText("Añadir control")).toBeInTheDocument();
    expect(screen.getByText("Activar")).toBeInTheDocument();
    expect(screen.getByText("Retirar")).toBeInTheDocument();

    await userEvent.click(screen.getByText("Activar"));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/cierres/politicas/p1/activar",
        expect.objectContaining({ method: "POST", body: {}, ifMatch: "1" }),
      );
    });

    await waitFor(() => {
      expect(notifyMock).toHaveBeenCalledWith({ type: "success", title: "Política activada" });
    });
  });

  it("PC-02 · BORRADOR solo con :view y :manage: no hay «Activar» ni «Retirar»", async () => {
    capacidades = new Set(["gobierno_cierre:view", "gobierno_cierre:manage"]);
    responderDetalle(detalleBase);

    renderizar();

    expect(await screen.findByText("Editar")).toBeInTheDocument();
    expect(screen.queryByText("Activar")).not.toBeInTheDocument();
    expect(screen.queryByText("Retirar")).not.toBeInTheDocument();
  });

  it("PC-03 · activar con 409 GOV_CLOSURE_POLICY_ACTIVE_EXISTS muestra un alert con el mensaje", async () => {
    capacidades = new Set(["gobierno_cierre:manage", "gobierno_cierre:activate"]);

    apiFetchMock.mockImplementation(async (url: unknown) => {
      if (typeof url === "string" && url.includes("/catalogo")) {
        return catalogoBase;
      }
      if (typeof url === "string" && url.endsWith("/activar")) {
        throw new ApiError(409, { code: "GOV_CLOSURE_POLICY_ACTIVE_EXISTS", message: "Conflicto" });
      }
      return detalleBase;
    });

    renderizar();

    await userEvent.click(await screen.findByText("Activar"));

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent(
      "Ya hay una política vigente para esa acción de cierre.",
    );
  });

  it("PC-11 · activar con 409 GOV_CLOSURE_POLICY_STALE muestra un alert con el mensaje", async () => {
    capacidades = new Set(["gobierno_cierre:manage", "gobierno_cierre:activate"]);

    apiFetchMock.mockImplementation(async (url: unknown) => {
      if (typeof url === "string" && url.includes("/catalogo")) {
        return catalogoBase;
      }
      if (typeof url === "string" && url.endsWith("/activar")) {
        throw new ApiError(409, { code: "GOV_CLOSURE_POLICY_STALE", message: "Conflicto" });
      }
      return detalleBase;
    });

    renderizar();

    await userEvent.click(await screen.findByText("Activar"));

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent(
      "Otra persona modificó esta política. Recargue para ver los cambios.",
    );
  });

  it("PC-12 · activar con 409 GOV_SOD_CONFLICT muestra un alert con el mensaje", async () => {
    capacidades = new Set(["gobierno_cierre:manage", "gobierno_cierre:activate"]);

    apiFetchMock.mockImplementation(async (url: unknown) => {
      if (typeof url === "string" && url.includes("/catalogo")) {
        return catalogoBase;
      }
      if (typeof url === "string" && url.endsWith("/activar")) {
        throw new ApiError(409, {
          code: "GOV_SOD_CONFLICT",
          message: "Conflicto",
          details: {
            regla_codigo: "SOD-1",
            regla_nombre: "Regla",
            accion_etiqueta: "Activar",
            accion_previa_etiqueta: "Registrar",
          },
        });
      }
      return detalleBase;
    });

    renderizar();

    await userEvent.click(await screen.findByText("Activar"));

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent(
      "Operación bloqueada por segregación de funciones",
    );
  });

  it("PC-13 · sin controles, Activar está deshabilitado", async () => {
    capacidades = new Set(["gobierno_cierre:manage", "gobierno_cierre:activate"]);
    responderDetalle({ ...detalleBase, controles: [] });
    renderizar();

    expect(await screen.findByRole("button", { name: "Activar" })).toBeDisabled();
    expect(screen.getByText("Añada al menos un control para activar")).toBeInTheDocument();
  });

  it("PC-04 · VIGENTE con :activate: «Retirar» abre el panel; con motivo corto deshabilita; con motivo válido hace POST", async () => {
    capacidades = new Set(["gobierno_cierre:activate"]);

    const detalleRetirado = {
      ...detalleVigente,
      estado: "RETIRADA",
      efectiva_hoy: false,
      version: 3,
      retirada_por: "ua",
      retirada_en: "2026-11-04T14:00:00Z",
      motivo_retiro: "Motivo de retiro suficientemente largo",
      historia: [
        ...detalleVigente.historia,
        {
          evento: "RETIRADA",
          detalle: { motivo: "Motivo de retiro suficientemente largo" },
          usuario: "ua",
          instante: "2026-11-04T14:00:00Z",
        },
      ],
    };

    apiFetchMock.mockImplementation(async (url: unknown) => {
      if (typeof url === "string" && url.includes("/catalogo")) {
        return catalogoBase;
      }
      if (typeof url === "string" && url.endsWith("/retirar")) {
        return detalleRetirado;
      }
      return detalleVigente;
    });

    renderizar();

    await userEvent.click(await screen.findByText("Retirar"));

    const motivo = await screen.findByLabelText(/^Motivo/);
    const confirmar = screen.getByRole("button", { name: "Confirmar retiro" });

    expect(confirmar).toBeDisabled();

    await userEvent.type(motivo, "corto");
    expect(confirmar).toBeDisabled();

    await userEvent.clear(motivo);
    await userEvent.type(motivo, "Motivo de retiro suficientemente largo");
    await waitFor(() => expect(confirmar).toBeEnabled());

    await userEvent.click(confirmar);

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/cierres/politicas/p1/retirar",
        expect.objectContaining({
          method: "POST",
          body: { motivo: "Motivo de retiro suficientemente largo" },
          ifMatch: "2",
        }),
      );
    });

    await waitFor(() => {
      expect(notifyMock).toHaveBeenCalledWith({ type: "success", title: "Política retirada" });
    });
  });

  it("PC-05 · editar: cambiar solo el nombre y guardar hace PATCH con body exacto { nombre } e ifMatch", async () => {
    capacidades = new Set(["gobierno_cierre:manage", "gobierno_cierre:activate"]);

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
      if (typeof url === "string" && url.includes("/catalogo")) {
        return catalogoBase;
      }
      return detalleBase;
    });

    renderizar();

    await userEvent.click(await screen.findByText("Editar"));

    const nombreInput = await screen.findByLabelText(/^Nombre/);
    await userEvent.clear(nombreInput);
    await userEvent.type(nombreInput, "Nombre nuevo");
    await userEvent.click(screen.getByText("Guardar", { selector: "button" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/cierres/politicas/p1",
        expect.objectContaining({
          method: "PATCH",
          body: { nombre: "Nombre nuevo" },
          ifMatch: "1",
        }),
      );
    });
  });

  it("PC-06 · añadir control: seleccionar tipo, riesgo y materialidad hace POST con body exacto", async () => {
    capacidades = new Set(["gobierno_cierre:manage", "gobierno_cierre:activate"]);

    const detalleConControlNuevo = {
      ...detalleBase,
      version: 2,
      controles: [
        ...detalleBase.controles,
        {
          id: "c2",
          tipo: "HALLAZGOS_ABIERTOS",
          riesgo_minimo: "MEDIO",
          materialidad: "Nueva materialidad significativa",
        },
      ],
    };

    apiFetchMock.mockImplementation(async (url: unknown, init: unknown) => {
      const method =
        init && typeof init === "object" && "method" in init
          ? (init as { method?: unknown }).method
          : undefined;
      if (method === "POST" && typeof url === "string" && url.endsWith("/controles")) {
        return detalleConControlNuevo;
      }
      if (typeof url === "string" && url.includes("/catalogo")) {
        return catalogoBase;
      }
      return detalleBase;
    });

    renderizar();

    await userEvent.click(await screen.findByText("Añadir control"));

    const tipoSelect = await screen.findByLabelText(/^Tipo/);
    await userEvent.selectOptions(tipoSelect, "HALLAZGOS_ABIERTOS");

    const riesgoSelect = await screen.findByLabelText(/^Riesgo mínimo/);
    await userEvent.selectOptions(riesgoSelect, "MEDIO");

    const materialidadTextarea = await screen.findByLabelText(/^Materialidad/);
    await userEvent.type(materialidadTextarea, "Nueva materialidad significativa");

    const guardarButton = screen.getByText("Guardar", { selector: "button" });
    await waitFor(() => expect(guardarButton).toBeEnabled());
    await userEvent.click(guardarButton);

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/cierres/politicas/p1/controles",
        expect.objectContaining({
          method: "POST",
          body: {
            tipo: "HALLAZGOS_ABIERTOS",
            riesgo_minimo: "MEDIO",
            materialidad: "Nueva materialidad significativa",
          },
          ifMatch: "1",
        }),
      );
    });
  });

  it("PC-07 · quitar control hace DELETE con URL exacta e If-Match", async () => {
    capacidades = new Set(["gobierno_cierre:manage", "gobierno_cierre:activate"]);

    const detalleSinControl = {
      ...detalleBase,
      version: 2,
      controles: [],
    };

    apiFetchMock.mockImplementation(async (url: unknown, init: unknown) => {
      const method =
        init && typeof init === "object" && "method" in init
          ? (init as { method?: unknown }).method
          : undefined;
      if (method === "DELETE") {
        return detalleSinControl;
      }
      if (typeof url === "string" && url.includes("/catalogo")) {
        return catalogoBase;
      }
      return detalleBase;
    });

    renderizar();

    const quitarButton = await screen.findByText("Quitar control");
    await userEvent.click(quitarButton);

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/cierres/politicas/p1/controles/c1",
        expect.objectContaining({
          method: "DELETE",
          ifMatch: "1",
        }),
      );
    });

    await waitFor(() => {
      expect(notifyMock).toHaveBeenCalledWith({ type: "success", title: "Control quitado" });
    });
  });

  it("PC-08 · la historia muestra la fila «Registrada» con el usuario ua; y 404 muestra «Política no encontrada»", async () => {
    capacidades = new Set(["gobierno_cierre:view"]);
    responderDetalle(detalleBase);

    const { unmount } = renderizar();

    await screen.findByRole("heading", { level: 1, name: "Política PC-2026-0001" });

    const region = await screen.findByRole("region", { name: "Tabla de historia de la política" });
    expect(within(region).getByText("Registrada")).toBeInTheDocument();
    expect(within(region).getByText("ua")).toBeInTheDocument();

    unmount();

    apiFetchMock.mockImplementation(async () => {
      throw new ApiError(404, { code: "GOV_CLOSURE_POLICY_NOT_FOUND", message: "No encontrada" });
    });

    renderizar("/gobierno/cierres/p1");

    const emptyState = await screen.findByText("Política no encontrada");
    expect(emptyState).toBeInTheDocument();
  });

  it("PC-09 · sin permiso (403) muestra «Sin acceso»", async () => {
    capacidades = new Set(["gobierno_cierre:view"]);
    apiFetchMock.mockImplementation(async (url: unknown) => {
      if (typeof url === "string" && url.includes("/catalogo")) {
        return catalogoBase;
      }
      throw new ApiError(403, { code: "FORBIDDEN", message: "Sin permiso" });
    });

    renderizar();

    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
  });

  it("PC-10 · error de carga muestra «No fue posible cargar la política.»", async () => {
    capacidades = new Set(["gobierno_cierre:view"]);
    apiFetchMock.mockImplementation(async () => {
      throw new Error("Error de red");
    });

    renderizar();

    expect(await screen.findByText("No fue posible cargar la política.")).toBeInTheDocument();
  });
});
