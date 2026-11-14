import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";

const apiFetchMock = vi.fn();
const notify = vi.hoisted(() => vi.fn());

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  ApiError: (await original<typeof import("@/api/client")>()).ApiError,
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
  useNotifications: () => ({ notify }),
}));

import { AlertasAtipicasPage } from "./AlertasAtipicasPage";
import { ApiError } from "@/api/client";

const datosPrueba = {
  aviso: "Aviso importante para Control Interno.",
  tipos: [
    {
      codigo: "DUPLICIDAD",
      etiqueta: "Duplicidad",
      descripcion: "Operaciones duplicadas.",
      disponible: true,
      motivo_no_disponible: null,
      requisito_habilitante: null,
      total: 1,
      pendientes: 1,
    },
    {
      codigo: "PROVEEDOR_RELACIONADO",
      etiqueta: "Proveedor relacionado",
      descripcion: "Proveedor con vínculos.",
      disponible: true,
      motivo_no_disponible: null,
      requisito_habilitante: null,
      total: 1,
      pendientes: 0,
    },
    {
      codigo: "AUTOAPROBACION",
      etiqueta: "Autoaprobación",
      descripcion: "Aprobación por el mismo sujeto.",
      disponible: true,
      motivo_no_disponible: null,
      requisito_habilitante: null,
      total: 1,
      pendientes: 1,
    },
    {
      codigo: "FRACCIONAMIENTO",
      etiqueta: "Fraccionamiento",
      descripcion: "División de operaciones.",
      disponible: false,
      motivo_no_disponible: "Falta configuración.",
      requisito_habilitante: "Configurar umbrales",
      total: 0,
      pendientes: 0,
    },
    {
      codigo: "OVERRIDE_FRECUENTE",
      etiqueta: "Override frecuente",
      descripcion: "Anulaciones frecuentes.",
      disponible: false,
      motivo_no_disponible: "Requiere auditoría previa.",
      requisito_habilitante: "Activar logs",
      total: 0,
      pendientes: 0,
    },
  ],
  alertas: [
    {
      clave: "DUPLICIDAD:aaaa:bbbb",
      tipo: "DUPLICIDAD",
      tipo_etiqueta: "Duplicidad",
      fecha: "2025-01-15T10:00:00Z",
      titulo: "Posible duplicidad en pagos",
      detalle: "Dos pagos similares al mismo proveedor.",
      sujetos: [{ etiqueta: "Proveedor", valor: "Proveedor Uno" }],
      estado: "PENDIENTE",
      vigente: true,
      es_sujeto: false,
      revision: null,
    },
    {
      clave: "AUTOAPROBACION:cccc:dddd",
      tipo: "AUTOAPROBACION",
      tipo_etiqueta: "Autoaprobación",
      fecha: "2025-01-16T10:00:00Z",
      titulo: "Aprobación por el mismo usuario",
      detalle: "El usuario aprobó su propia solicitud.",
      sujetos: [{ etiqueta: "Usuario", valor: "Usuario Uno" }],
      estado: "PENDIENTE",
      vigente: true,
      es_sujeto: true,
      revision: null,
    },
    {
      clave: "PROVEEDOR_RELACIONADO:eeee:ffff",
      tipo: "PROVEEDOR_RELACIONADO",
      tipo_etiqueta: "Proveedor relacionado",
      fecha: "2025-01-10T10:00:00Z",
      titulo: "Proveedor con vínculo",
      detalle: "Proveedor relacionado con un empleado.",
      sujetos: [{ etiqueta: "Proveedor", valor: "Proveedor Dos" }],
      estado: "REVISADA",
      vigente: false,
      es_sujeto: false,
      revision: {
        resultado: "REQUIERE_SEGUIMIENTO",
        resultado_etiqueta: "Requiere seguimiento",
        observacion: "Se requiere seguimiento adicional.",
        revisada_por: "Auditor Uno",
        revisada_en: "2025-01-12T10:00:00Z",
      },
    },
  ],
};

function renderizar() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AlertasAtipicasPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  capacidades = new Set(["gobierno_alertas:view", "gobierno_alertas:review"]);

  apiFetchMock.mockImplementation((ruta: string, opciones?: { method?: string; body?: unknown }) => {
    if (ruta === "/gobierno/control/alertas" && (!opciones || opciones.method === undefined)) {
      return Promise.resolve(datosPrueba);
    }
    if (
      ruta === "/gobierno/control/alertas/revisiones" &&
      opciones?.method === "POST"
    ) {
      const body = opciones.body as { clave: string };
      const alerta = datosPrueba.alertas.find((a) => a.clave === body.clave);
      return Promise.resolve(alerta ?? datosPrueba.alertas[0]);
    }
    return Promise.reject(new Error("Ruta no esperada"));
  });
});

describe("AlertasAtipicasPage", () => {
  it("muestra el aviso, la tabla de tipos y las alertas; la clave no aparece", async () => {
    renderizar();

    await waitFor(() => {
      expect(screen.getByRole("note")).toHaveTextContent("Aviso importante para Control Interno.");
    });

    const tablaTipos = screen.getByRole("table", { name: "Tipos de alerta" });
    expect(within(tablaTipos).getAllByText("No disponible")).toHaveLength(2);
    expect(within(tablaTipos).getByText(/Requiere: Configurar umbrales/)).toBeInTheDocument();

    expect(screen.getByText("Posible duplicidad en pagos")).toBeInTheDocument();
    expect(screen.getByText("Aprobación por el mismo usuario")).toBeInTheDocument();
    expect(screen.getByText("Proveedor con vínculo")).toBeInTheDocument();

    expect(screen.queryByText(/DUPLICIDAD:aaaa/)).toBeNull();
  });

  it("sin permiso de vista muestra Sin acceso y no llama a apiFetch", async () => {
    capacidades = new Set([]);
    renderizar();

    expect(screen.getByText("Sin acceso")).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("sin permiso de revisión no hay botón Revisar; con permiso hay exactamente 1", async () => {
    capacidades = new Set(["gobierno_alertas:view"]);
    const primero = renderizar();

    await waitFor(() => {
      expect(screen.getByText("Posible duplicidad en pagos")).toBeInTheDocument();
    });

    expect(screen.queryByRole("button", { name: "Revisar" })).toBeNull();

    primero.unmount();

    capacidades = new Set(["gobierno_alertas:view", "gobierno_alertas:review"]);
    renderizar();

    await waitFor(() => {
      expect(screen.getByText("Posible duplicidad en pagos")).toBeInTheDocument();
    });

    const botonesRevisar = screen.getAllByRole("button", { name: "Revisar" });
    expect(botonesRevisar).toHaveLength(1);

    expect(
      screen.getByText("No puede revisar esta alerta porque es sujeto de ella."),
    ).toBeInTheDocument();
  });

  it("revisa una alerta con éxito", async () => {
    const user = userEvent.setup();
    renderizar();

    await waitFor(() => {
      expect(screen.getByText("Posible duplicidad en pagos")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Revisar" }));

    const radioSinObservacion = screen.getByRole("radio", { name: "Sin observación" });
    await user.click(radioSinObservacion);

    const textarea = screen.getByLabelText("Observación");
    await user.type(textarea, "Revisada con la unidad, sin hallazgos.");

    await user.click(screen.getByRole("button", { name: "Registrar revisión" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith("/gobierno/control/alertas/revisiones", {
        method: "POST",
        body: {
          clave: "DUPLICIDAD:aaaa:bbbb",
          resultado: "SIN_OBSERVACION",
          observacion: "Revisada con la unidad, sin hallazgos.",
        },
      });
    });

    expect(notify).toHaveBeenCalledWith({ type: "success", title: "Revisión registrada" });
  });

  it("botón deshabilitado con observación corta", async () => {
    const user = userEvent.setup();
    renderizar();

    await waitFor(() => {
      expect(screen.getByText("Posible duplicidad en pagos")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Revisar" }));
    await user.click(screen.getByRole("radio", { name: "Sin observación" }));

    const textarea = screen.getByLabelText("Observación");
    await user.type(textarea, "corta");

    expect(screen.getByRole("button", { name: "Registrar revisión" })).toBeDisabled();
  });

  it("muestra error de ApiError 409 GOV_ALERT_SELF_REVIEW", async () => {
    const user = userEvent.setup();
    renderizar();

    await waitFor(() => {
      expect(screen.getByText("Posible duplicidad en pagos")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Revisar" }));
    await user.click(screen.getByRole("radio", { name: "Sin observación" }));
    await user.type(
      screen.getByLabelText("Observación"),
      "Observación con más de diez caracteres.",
    );

    apiFetchMock.mockRejectedValueOnce(
      new ApiError(409, {
        code: "GOV_ALERT_SELF_REVIEW",
        message:
          "No puede revisar una alerta de la que es sujeto. Debe hacerlo otro usuario de Control Interno.",
      }),
    );

    await user.click(screen.getByRole("button", { name: "Registrar revisión" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "No puede revisar una alerta de la que es sujeto. Debe hacerlo otro usuario de Control Interno.",
      );
    });
  });

  it("la alerta revisada muestra revisada por, ya no se detecta y enlace a hallazgo", async () => {
    renderizar();

    await waitFor(() => {
      expect(screen.getByText("Proveedor con vínculo")).toBeInTheDocument();
    });

    expect(
      screen.getByText(/Revisada por Auditor Uno el .*Requiere seguimiento\./),
    ).toBeInTheDocument();
    expect(screen.getByText("Ya no se detecta.")).toBeInTheDocument();

    const enlaceHallazgo = screen.getByRole("link", { name: "Registrar hallazgo" });
    expect(enlaceHallazgo).toHaveAttribute("href", "/gobierno/hallazgos/nuevo");
  });

  it("filtra por estado Revisadas", async () => {
    const user = userEvent.setup();
    renderizar();

    await waitFor(() => {
      expect(screen.getByText("Posible duplicidad en pagos")).toBeInTheDocument();
    });

    const selectEstado = screen.getByLabelText("Estado");
    await user.selectOptions(selectEstado, "REVISADA");

    expect(screen.queryByText("Posible duplicidad en pagos")).toBeNull();
    expect(screen.queryByText("Aprobación por el mismo usuario")).toBeNull();
    expect(screen.getByText("Proveedor con vínculo")).toBeInTheDocument();
  });
});
