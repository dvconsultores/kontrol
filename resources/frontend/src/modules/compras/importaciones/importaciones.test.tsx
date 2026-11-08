import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryRouter, RouterProvider } from "react-router";
import { ApiError } from "@/api/client";

let mockPuede = true;
const apiFetch = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: vi.fn() }),
}));

vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({ activeCompany: { id: "emp-a", name: "Empresa A" } }),
}));

vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({
    estado: "LISTA",
    tiene: () => true,
    puede: () => mockPuede,
    motivo: () => null,
    motivoDeCapacidad: () => null,
  }),
}));

vi.mock("@/modules/documentos/AdjuntosPanel", () => ({
  AdjuntosPanel: () => null,
}));

vi.mock("@/modules/maestros/terceros/SelectorDeTercero", () => ({
  SelectorDeTercero: ({ value, onChange }: { value: string; onChange: (id: string) => void }) => (
    <input
      aria-label="Proveedor"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  ),
}));


const detalleNegociando = {
  id: "i-1",
  code: "IMP-001",
  status: "NEGOTIATING",
  logistics: null,
  currency: "VED",
  supplier_id: "prov-1",
  supplier_name: "Proveedor Uno",
  order_id: null,
  order_code: null,
  agent_party_id: null,
  carrier_party_id: null,
  transport_document: null,
  origin: null,
  destination: null,
  incoterm: "FOB",
  incoterm_place: "Puerto",
  payment_conditions: "30 días",
  delivery_conditions: "Entrega en puerto",
  expected_dispatch_date: null,
  expected_arrival_date: null,
  actual_departure_date: null,
  notes: null,
  cancel_reason: null,
  next_action: "Completa la negociación o vincula la orden.",
  allowed_actions: {
    edit: true,
    link_order: true,
    add_document: false,
    confirm_documents: false,
    confirm_dispatch: false,
    cancel: true,
  },
  documents: [],
  tracking_events: [],
  financial: [],
  corrections: [],
  summary: {
    pending: [],
    documents_validated: 0,
    documents_required: 1,
    open_corrections: 0,
    financial_count: 0,
    agent_name: null,
    carrier_name: null,
  },
  version: 2,
};

const listadoImportaciones = {
  items: [
    {
      id: "i-1",
      code: "IMP-001",
      status: "NEGOTIATING",
      currency: "VED",
      supplier_id: "prov-1",
      supplier_name: "Proveedor Uno",
      order_id: null,
      order_code: null,
      incoterm: "FOB",
      expected_arrival_date: null,
      created_at: "2025-01-01T00:00:00Z",
      version: 2,
    },
  ],
  total: 1,
  page: 1,
  page_size: 10,
};

const ordenesAprobadas = {
  items: [
    { id: "o-1", code: "OC-001", currency: "VED" },
  ],
  total: 1,
  page: 1,
  page_size: 100,
};

function crearRouter(rutaInicial: string) {
  return createMemoryRouter(
    [
      {
        path: "/compras/importaciones",
        lazy: async () => {
          const { ImportacionesPage } = await import("./ImportacionesPage");
          return { Component: ImportacionesPage };
        },
      },
      {
        path: "/compras/importaciones/nueva",
        lazy: async () => {
          const { ImportacionNuevaPage } = await import("./ImportacionNuevaPage");
          return { Component: ImportacionNuevaPage };
        },
      },
      {
        path: "/compras/importaciones/:importId",
        lazy: async () => {
          const { ImportacionDetallePage } = await import("./ImportacionDetallePage");
          return { Component: ImportacionDetallePage };
        },
      },
      {
        path: "/compras/ordenes",
        element: <div>Página de órdenes</div>,
      },
    ],
    { initialEntries: [rutaInicial] },
  );
}

function renderizar(rutaInicial: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const router = crearRouter(rutaInicial);
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}


function llamadasDe(path: string, method?: string) {
  return apiFetch.mock.calls.filter(([p, options]) => {
    const coincidePath = typeof p === "string" && p.startsWith(path);
    const coincideMethod = method ? options?.method === method : true;
    return coincidePath && coincideMethod;
  });
}

describe("importaciones", () => {
  beforeEach(() => {
    mockPuede = true;
    apiFetch.mockReset();
  });

  it("expediente: negocia, vincula y confirma", async () => {
    apiFetch.mockImplementation(async (path: string) => {
      if (path === "/importaciones/i-1") return detalleNegociando;
      if (path.startsWith("/importaciones/eligible-orders"))
        return ordenesAprobadas;
      if (path.startsWith("/importaciones/i-1/audit")) return { items: [], total: 0 };
      throw new Error(`No mockeado: ${path}`);
    });

    const usuario = userEvent.setup();
    renderizar("/compras/importaciones/i-1");

    await screen.findAllByText("En negociación");
    expect(screen.getByText("Completa la negociación o vincula la orden.")).toBeTruthy();

    const condicionesPago = screen.getByLabelText(/Condiciones de pago/i);
    await usuario.clear(condicionesPago);
    await usuario.type(condicionesPago, "Pago a 60 días");

    await usuario.click(screen.getByRole("button", { name: "Guardar negociación" }));

    await waitFor(() => {
      const patch = llamadasDe("/importaciones/i-1", "PATCH");
      expect(patch).toHaveLength(1);
      expect(patch[0]?.[1]).toMatchObject({
        body: { payment_conditions: "Pago a 60 días" },
        ifMatch: "2",
      });
    });

    const combo = screen.getByRole("combobox", { name: "Orden aprobada" });
    await usuario.click(combo);
    await usuario.type(combo, "OC-001");
    await usuario.click(screen.getByRole("option", { name: /OC-001/ }));
    await usuario.click(screen.getByRole("button", { name: "Vincular orden" }));

    await waitFor(() => {
      const post = llamadasDe("/importaciones/i-1/order", "POST");
      expect(post).toHaveLength(1);
      expect(post[0]?.[1]).toMatchObject({ body: { order_id: "o-1" } });
    });
  });

  it("vincular sin negociación explica qué falta", async () => {
    apiFetch.mockImplementation(async (path: string) => {
      if (path === "/importaciones/i-1") return detalleNegociando;
      if (path.startsWith("/importaciones/eligible-orders"))
        return ordenesAprobadas;
      if (path.startsWith("/importaciones/i-1/audit")) return { items: [], total: 0 };
      if (path.startsWith("/importaciones/i-1/order"))
        throw new ApiError(409, {
          code: "IMPORT_NEGOTIATION_INCOMPLETE",
          message: "Falta negociación",
          details: { missing: ["incoterm"] },
        });
      throw new Error(`No mockeado: ${path}`);
    });

    const usuario = userEvent.setup();
    renderizar("/compras/importaciones/i-1");

    await screen.findAllByText("En negociación");
    const combo = screen.getByRole("combobox", { name: "Orden aprobada" });
    await usuario.click(combo);
    await usuario.type(combo, "OC-001");
    await usuario.click(screen.getByRole("option", { name: /OC-001/ }));
    await usuario.click(screen.getByRole("button", { name: "Vincular orden" }));

    const alerta = await screen.findByRole("alert");
    expect(alerta.textContent).toContain("Completa la negociación");
    expect(alerta.textContent).toContain("INCOTERM");
  });

  it("confirmar sin validar explica qué falta", async () => {
    apiFetch.mockImplementation(async (path: string) => {
      if (path === "/importaciones/i-1") {
        return {
          ...detalleNegociando,
          allowed_actions: {
            ...detalleNegociando.allowed_actions,
            confirm_documents: true,
          },
          documents: [
            {
              id: "doc-1",
              kind: "CERTIFICATE",
              name: "Packing list",
              required: true,
              reference: null,
              status: "PENDING",
              observation: null,
              version: 1,
              attachments: [],
              allowed_actions: { receive: false, validate: false, observe: false },
            },
          ],
        };
      }
      if (path.startsWith("/importaciones/i-1/audit")) return { items: [], total: 0 };
      if (path.startsWith("/importaciones/i-1/confirm-documents"))
        throw new ApiError(409, {
          code: "IMPORT_DOCUMENTS_INCOMPLETE",
          message: "Faltan documentos",
          details: { missing: ["Packing list"] },
        });
      throw new Error(`No mockeado: ${path}`);
    });

    const usuario = userEvent.setup();
    renderizar("/compras/importaciones/i-1");

    await screen.findAllByText("En negociación");
    await usuario.click(screen.getByRole("button", { name: "Confirmar documentación" }));

    expect(await screen.findByText(/Falta validar: Packing list/)).toBeTruthy();
  });

  it("resumen muestra pendientes y botón de confirmar despacho", async () => {
    const detalleDocumentosCompletos = {
      ...detalleNegociando,
      status: "DOCUMENTS_COMPLETE" as const,
      agent_party_id: null,
      carrier_party_id: null,
      transport_document: null,
      origin: null,
      destination: null,
      actual_departure_date: null,
      summary: {
        pending: ["Registrar salida real"],
        documents_validated: 1,
        documents_required: 1,
        open_corrections: 0,
        financial_count: 1,
        agent_name: null,
        carrier_name: null,
      },
      tracking_events: [],
      financial: [],
      corrections: [],
      allowed_actions: {
        edit: true,
        link_order: true,
        add_document: false,
        confirm_documents: false,
        confirm_dispatch: true,
        cancel: false,
      },
    };

    apiFetch.mockImplementation(async (path: string) => {
      if (path === "/importaciones/i-1") return detalleDocumentosCompletos;
      if (path.startsWith("/importaciones/i-1/audit")) return { items: [], total: 0 };
      if (path.startsWith("/importaciones/i-1/financial-candidates")) {
        return { items: [], total: 0, page: 1, page_size: 20 };
      }
      throw new Error(`No mockeado: ${path}`);
    });

    renderizar("/compras/importaciones/i-1");

    expect(await screen.findByText("Registrar salida real")).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Confirmar despacho" }),
    ).toBeVisible();
  });

  it("registrar pago con proveedor no aprobado muestra enlace al proveedor", async () => {
    const detalleOrdenado = {
      ...detalleNegociando,
      status: "ORDERED" as const,
      agent_party_id: null,
      carrier_party_id: null,
      transport_document: null,
      origin: null,
      destination: null,
      actual_departure_date: null,
      summary: {
        pending: [],
        documents_validated: 0,
        documents_required: 1,
        open_corrections: 0,
        financial_count: 0,
        agent_name: null,
        carrier_name: null,
      },
      tracking_events: [],
      financial: [],
      corrections: [],
      allowed_actions: {
        edit: true,
        link_order: true,
        add_document: false,
        confirm_documents: true,
        confirm_dispatch: false,
        cancel: true,
      },
    };

    apiFetch.mockImplementation(async (path: string, options?: { method?: string; body?: unknown }) => {
      if (path === "/importaciones/i-1") return detalleOrdenado;
      if (path.startsWith("/importaciones/i-1/audit")) return { items: [], total: 0 };
      if (path.startsWith("/importaciones/i-1/financial-candidates")) {
        return { items: [], total: 0, page: 1, page_size: 20 };
      }
      if (path === "/importaciones/i-1/payments" && options?.method === "POST") {
        throw new ApiError(409, {
          code: "SUPPLIER_NOT_APPROVED",
          message: "El proveedor no está aprobado.",
          details: { supplier_id: "prov-1" },
        });
      }
      throw new Error(`No mockeado: ${path}`);
    });

    renderizar("/compras/importaciones/i-1");

    await screen.findByLabelText(/^Monto/);
    await userEvent.type(screen.getByLabelText(/^Monto/), "100");
    await userEvent.click(
      screen.getByRole("button", { name: /^Registrar$/ }),
    );

    const alerta = await screen.findByRole("alert");
    expect(alerta.textContent).toContain("El proveedor no está aprobado.");
    expect(screen.getByRole("link", { name: "Ver proveedor" })).toHaveAttribute(
      "href",
      "/maestros/terceros/prov-1",
    );
  });

  it("sin permiso oculta acciones", async () => {
    mockPuede = false;
    apiFetch.mockImplementation(async (path: string) => {
      if (path === "/importaciones/i-1") return detalleNegociando;
      if (path.startsWith("/importaciones/i-1/audit")) return { items: [], total: 0 };
      throw new Error(`No mockeado: ${path}`);
    });

    renderizar("/compras/importaciones/i-1");

    await screen.findAllByText("En negociación");
    expect(screen.queryByRole("button", { name: "Guardar negociación" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Vincular orden" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Confirmar documentación" })).toBeNull();
    expect(llamadasDe("/importaciones/i-1/audit")).toHaveLength(0);
  });

  it("alta guarda una vez y llega al expediente, sin diálogo", async () => {
    apiFetch.mockImplementation(async (path: string) => {
      if (path === "/importaciones") return { id: "i-1" };
      if (path === "/importaciones/i-1") return detalleNegociando;
      if (path.startsWith("/importaciones/i-1/audit")) return { items: [], total: 0 };
      throw new Error(`No mockeado: ${path}`);
    });

    const usuario = userEvent.setup();
    renderizar("/compras/importaciones/nueva");

    await usuario.type(await screen.findByLabelText(/^Código \*/), "IMP-001");
    await usuario.type(screen.getByLabelText("Proveedor"), "prov-1");
    await usuario.click(screen.getByRole("button", { name: "Guardar" }));

    await waitFor(() => {
      expect(screen.getAllByText("En negociación").length).toBeGreaterThan(0);
    });

    const posts = llamadasDe("/importaciones", "POST");
    expect(posts).toHaveLength(1);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("listado pagina en servidor y muestra nombres, no ids", async () => {
    apiFetch.mockImplementation(async (path: string) => {
      if (path.startsWith("/importaciones?")) return listadoImportaciones;
      throw new Error(`No mockeado: ${path}`);
    });

    renderizar("/compras/importaciones");

    await screen.findByText("IMP-001");
    expect(screen.getByText("Proveedor Uno")).toBeTruthy();
    expect(screen.queryByText("prov-1")).toBeNull();
    expect(llamadasDe("/importaciones?")).toHaveLength(1);
  });

  it("otra empresa o inexistente muestra mensaje", async () => {
    apiFetch.mockImplementation(async (path: string) => {
      if (path === "/importaciones/i-1")
        throw new ApiError(404, { code: "NOT_FOUND", message: "No existe" });
      throw new Error(`No mockeado: ${path}`);
    });

    renderizar("/compras/importaciones/i-1");

    expect(
      await screen.findByText("Importación no encontrada en esta empresa."),
    ).toBeTruthy();
  });
});
