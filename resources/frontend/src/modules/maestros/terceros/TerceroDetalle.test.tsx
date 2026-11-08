import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { PartyDetail } from "./tipos";
import { ApiError } from "@/api/client";

let mockPuede = true;

const apiFetch = vi.fn();

vi.mock("@/api/client", async (original) => {
  const actual = await original<typeof import("@/api/client")>();
  return {
    ...actual,
    apiFetch: (...args: unknown[]) => apiFetch(...args),
    ApiError: actual.ApiError,
  };
});

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

const partyBase: PartyDetail = {
  id: "p-1",
  code: "T-001",
  name: "Tercero Uno",
  person_type: "JURIDICA",
  legal_name: "Razón Original",
  trade_name: null,
  tax_id: "J-123",
  roles: ["CLIENTE"],
  status: "ACTIVE",
  nationality: "V",
  residence: "Caracas",
  economic_activity: "Comercio",
  version: 3,
  allowed_actions: {
    view: true,
    edit: true,
    activate: true,
    deactivate: true,
    delete: true,
  },
  blocking_documents: [],
  supplier_approval_status: null,
};

function setup(party: PartyDetail = partyBase) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  if (!apiFetch.getMockImplementation()) apiFetch.mockImplementation(
    async (path: string, options?: { method?: string; body?: unknown }) => {
      const method = options?.method ?? "GET";
      if (path === "/maestros/terceros/p-1" && method === "GET") {
        return party;
      }
      if (
        path === "/maestros/terceros/p-1/audit?page=1&page_size=25" &&
        method === "GET"
      ) {
        return { items: [], total: 0 };
      }
      if (/\/(addresses|contacts|bank-accounts)$/.test(path) && method === "GET") {
        return { items: [] };
      }
      if (/\/(customer|supplier|carrier|driver)$/.test(path) && method === "GET") {
        return { id: "e-1", party_id: "p-1", version: 1, credit_days: 0, blocked: false };
      }

      if (
        path === "/maestros/terceros/p-1" &&
        method === "PATCH"
      ) {
        return { ...party, version: party.version + 1 };
      }
      if (
        path.startsWith("/maestros/terceros/p-1/roles/") &&
        method === "POST"
      ) {
        return { ok: true };
      }
      if (
        path.startsWith("/maestros/terceros/p-1/roles/") &&
        method === "DELETE"
      ) {
        return { ok: true };
      }
      if (path === "/maestros/terceros/p-1/activate" && method === "POST") {
        return { ok: true };
      }
      if (path === "/maestros/terceros/p-1/deactivate" && method === "POST") {
        return { ok: true };
      }
      if (path === "/maestros/terceros/p-1" && method === "DELETE") {
        return { ok: true };
      }
      throw new Error(`ruta inesperada ${path}`);
    },
  );

  const router = createMemoryRouter(
    [
      {
        path: "/maestros/terceros/:partyId",
        element: <TerceroDetallePage />,
      },
      {
        path: "/maestros/terceros",
        element: <div>listado</div>,
      },
    ],
    { initialEntries: ["/maestros/terceros/p-1"] },
  );

  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );

  return { queryClient, router };
}

let TerceroDetallePage: typeof import("./TerceroDetallePage").TerceroDetallePage;

beforeEach(async () => {
  mockPuede = true;
  apiFetch.mockReset();
  TerceroDetallePage = (
    await import("./TerceroDetallePage")
  ).TerceroDetallePage;
});

describe("TerceroDetallePage", () => {
  it("edita solo lo cambiado con la versión y agrega un rol", async () => {
    const user = userEvent.setup();
    setup();

    expect(await screen.findByText("T-001 · Tercero Uno")).toBeTruthy();

    const razonSocial = screen.getByLabelText(/^Razón social/);
    await user.clear(razonSocial);
    await user.type(razonSocial, "Nueva");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith("/maestros/terceros/p-1", {
        method: "PATCH",
        body: { legal_name: "Nueva" },
        ifMatch: "3",
      });
    });

    await user.selectOptions(
      screen.getByLabelText("Rol a agregar"),
      "PROVEEDOR",
    );
    await user.click(screen.getByRole("button", { name: "Agregar rol" }));

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/maestros/terceros/p-1/roles/PROVEEDOR",
        { method: "POST" },
      );
    });
  });

  it("documento activo: muestra el bloqueo y no ofrece desactivar", async () => {
    const party = {
      ...partyBase,
      allowed_actions: {
        ...partyBase.allowed_actions,
        deactivate: false,
      },
      blocking_documents: [
        { module: "ventas", document: "Factura", count: 2 },
      ],
    };
    setup(party);

    expect(await screen.findByText("Factura (ventas): 2")).toBeTruthy();
    expect(
      screen.queryByRole("button", { name: "Desactivar" }),
    ).toBeNull();
  });

  it("versión desfasada avisa", async () => {
    const user = userEvent.setup();
    setup();

    expect(await screen.findByText("T-001 · Tercero Uno")).toBeTruthy();

    apiFetch.mockImplementation(
      async (path: string, options?: { method?: string; body?: unknown }) => {
        const method = options?.method ?? "GET";
        if (path === "/maestros/terceros/p-1" && method === "GET") {
          return partyBase;
        }
        if (
          path === "/maestros/terceros/p-1/audit?page=1&page_size=25" &&
          method === "GET"
        ) {
          return { items: [], total: 0 };
        }
        if (path === "/maestros/terceros/p-1" && method === "PATCH") {
          throw new ApiError(409, {
            code: "VERSION_CONFLICT",
            message: "x",
          });
        }
        throw new Error(`ruta inesperada ${path}`);
      },
    );

    const razonSocial = screen.getByLabelText(/^Razón social/);
    await user.clear(razonSocial);
    await user.type(razonSocial, "Nueva");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    expect(
      await screen.findByText(
        "Otro usuario modificó este tercero. Recargue para ver los cambios.",
      ),
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: "Recargar" })).toBeTruthy();
  });

  it("sin permiso no ofrece guardar", async () => {
    mockPuede = false;
    setup();

    expect(await screen.findByText("T-001 · Tercero Uno")).toBeTruthy();
    expect(
      screen.queryByRole("button", { name: "Guardar cambios" }),
    ).toBeNull();
    expect(
      screen.queryByRole("button", { name: "Agregar rol" }),
    ).toBeNull();
    expect(screen.queryByText("Historial")).toBeNull();
  });

  it("otra empresa o inexistente", async () => {
    apiFetch.mockImplementation(
      async (path: string, options?: { method?: string }) => {
        if (path === "/maestros/terceros/p-1" && !options?.method) {
          throw new ApiError(404, {
            code: "PARTY_NOT_FOUND",
            message: "x",
          });
        }
        throw new Error(`ruta inesperada ${path}`);
      },
    );
    setup();

    expect(
      await screen.findByText("Tercero no encontrado en esta empresa."),
    ).toBeTruthy();
  });

  it("historial muestra evento", async () => {
    const party = {
      ...partyBase,
      allowed_actions: {
        ...partyBase.allowed_actions,
        edit: false,
      },
    };

    apiFetch.mockImplementation(
      async (path: string, options?: { method?: string; body?: unknown }) => {
        const method = options?.method ?? "GET";
        if (path === "/maestros/terceros/p-1" && method === "GET") {
          return party;
        }
        if (
          path === "/maestros/terceros/p-1/audit?page=1&page_size=25" &&
          method === "GET"
        ) {
          return {
            items: [
              {
                id: "a1",
                action: "PARTY_UPDATED",
                action_label: "Tercero actualizado",
                event_time: "2024-01-01T10:00:00Z",
                username: "ana",
                request_id: null,
                reason: null,
                details: {
                  before: { name: "A" },
                  after: { name: "B" },
                },
              },
            ],
            total: 1,
          };
        }
        throw new Error(`ruta inesperada ${path}`);
      },
    );

    setup(party);

    expect(await screen.findByText("Tercero actualizado")).toBeTruthy();
    expect(screen.getByText("ana")).toBeTruthy();
    expect(screen.getByText("name: A → B")).toBeTruthy();
  });
});
