import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router";
import { ApiError } from "@/api/client";

let mockPuede = true;
const apiFetch = vi.fn();
vi.mock("@/api/client", async (original) => {
  const actual = await original<typeof import("@/api/client")>();
  return {
    ...actual,
    ApiError: actual.ApiError,
    apiFetch: (...args: unknown[]) => apiFetch(...args),
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

import { TerceroExtensiones } from "./TerceroExtensiones";

const allowedActions = {
  view: true,
  edit: true,
  activate: false,
  deactivate: true,
  delete: false,
};

function renderComponent(props: {
  roles: string[];
  allowedActions?: Record<string, boolean>;
}) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <TerceroExtensiones
          partyId="p-1"
          roles={props.roles}
          editable={true}
          allowedActions={
            (props.allowedActions as typeof allowedActions) ?? allowedActions
          }
        />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function mockGet(path: string, data: unknown) {
  apiFetch.mockImplementation((...args: unknown[]) => {
    const [pathArg, options] = args as [string, { method?: string }?];
    if (pathArg === path && (options?.method ?? "GET") === "GET") {
      return Promise.resolve(data);
    }
    return Promise.reject(
      new Error(`Unexpected call: ${pathArg} ${options?.method ?? "GET"}`),
    );
  });
}



function mockGetSupplier() {
  mockGet("/maestros/terceros/p-1/supplier", {
    id: "e-1",
    party_id: "p-1",
    version: 2,
    approval_status: "PENDING_APPROVAL",
    category: "Cat A",
  });
}

function mockGetCustomer() {
  mockGet("/maestros/terceros/p-1/customer", {
    id: "e-1",
    party_id: "p-1",
    version: 2,
    credit_days: 15,
    credit_limit: "1000.50",
    blocked: false,
  });
}

function mockGetDriver() {
  mockGet("/maestros/terceros/p-1/driver", {
    id: "e-1",
    party_id: "p-1",
    version: 2,
    license: "L123",
    categories: ["A", "B"],
    expiry: "2026-12-31T00:00:00+00:00",
    restrictions: "none",
  });
}

function hasCall(path: string, method: string) {
  return apiFetch.mock.calls.some((call) => {
    const [pathArg, options] = call as [string, { method?: string }?];
    return pathArg === path && (options?.method ?? "GET") === method;
  });
}

function callCount(path: string, method: string) {
  return apiFetch.mock.calls.filter((call) => {
    const [pathArg, options] = call as [string, { method?: string }?];
    return pathArg === path && (options?.method ?? "GET") === method;
  }).length;
}

beforeEach(() => {
  mockPuede = true;
  apiFetch.mockReset();
});

describe("TerceroExtensiones", () => {
  it("edita el proveedor y lo aprueba", async () => {
    const user = userEvent.setup();
    mockGetSupplier();
    apiFetch.mockImplementation((...args: unknown[]) => {
      const [pathArg, options] = args as [string, { method?: string, body?: unknown, ifMatch?: string }?];
      const method = options?.method ?? "GET";
      if (pathArg === "/maestros/terceros/p-1/supplier" && method === "GET") {
        return Promise.resolve({
          id: "e-1",
          party_id: "p-1",
          version: 2,
          approval_status: "PENDING_APPROVAL",
          category: "Cat A",
        });
      }
      if (pathArg === "/maestros/terceros/p-1/supplier" && method === "PUT") {
        return Promise.resolve({
          id: "e-1",
          party_id: "p-1",
          version: 3,
          approval_status: "PENDING_APPROVAL",
          category: (options?.body as { category?: string } | undefined)?.category,
        });
      }
      if (
        pathArg === "/maestros/terceros/p-1/roles/PROVEEDOR/approve" &&
        method === "POST"
      ) {
        return Promise.resolve({
          id: "e-1",
          party_id: "p-1",
          version: 4,
          approval_status: "APPROVED",
        });
      }
      return Promise.reject(
        new Error(`Unexpected call: ${pathArg} ${method}`),
      );
    });

    renderComponent({
      roles: ["PROVEEDOR"],
      allowedActions: { ...allowedActions, approve: true },
    });

    expect(await screen.findByText("Estado de aprobación: Pendiente")).toBeInTheDocument();
    expect(
      screen.getByText(
        "No se pueden registrar pagos ni anticipos a este proveedor hasta aprobarlo.",
      ),
    ).toBeInTheDocument();

    const categoriaInput = screen.getByLabelText("Categoría");
    await user.clear(categoriaInput);
    await user.type(categoriaInput, "Insumos");
    await user.click(screen.getByRole("button", { name: "Guardar Proveedor" }));

    await waitFor(() => {
      expect(
        hasCall("/maestros/terceros/p-1/supplier", "PUT"),
      ).toBe(true);
    });
    const putCall = apiFetch.mock.calls.find((call) => {
      const [pathArg, options] = call as [string, { method?: string }?];
      return (
        pathArg === "/maestros/terceros/p-1/supplier" &&
        (options?.method ?? "GET") === "PUT"
      );
    });
    expect(putCall?.[1]).toMatchObject({
      method: "PUT",
      body: { category: "Insumos" },
      ifMatch: "2",
    });

    await user.click(
      await screen.findByRole("button", { name: "Aprobar proveedor" }),
    );

    await waitFor(() => {
      expect(
        hasCall(
          "/maestros/terceros/p-1/roles/PROVEEDOR/approve",
          "POST",
        ),
      ).toBe(true);
    });
    expect(
      callCount(
        "/maestros/terceros/p-1/roles/PROVEEDOR/approve",
        "POST",
      ),
    ).toBe(1);
  });

  it("aprobar sin requisitos explica qué falta", async () => {
    const user = userEvent.setup();
    apiFetch.mockImplementation((...args: unknown[]) => {
      const [pathArg, options] = args as [string, { method?: string }?];
      const method = options?.method ?? "GET";
      if (pathArg === "/maestros/terceros/p-1/supplier" && method === "GET") {
        return Promise.resolve({
          id: "e-1",
          party_id: "p-1",
          version: 2,
          approval_status: "PENDING_APPROVAL",
        });
      }
      if (
        pathArg === "/maestros/terceros/p-1/roles/PROVEEDOR/approve" &&
        method === "POST"
      ) {
        return Promise.reject(
          new ApiError(409, {
            code: "SUPPLIER_APPROVAL_PRECONDITION",
            message: "x",
            details: { missing: ["verified_bank_account"] },
          }),
        );
      }
      return Promise.reject(
        new Error(`Unexpected call: ${pathArg} ${method}`),
      );
    });

    renderComponent({
      roles: ["PROVEEDOR"],
      allowedActions: { ...allowedActions, approve: true },
    });

    await user.click(
      await screen.findByRole("button", { name: "Aprobar proveedor" }),
    );

    expect(
      await screen.findByText("Una cuenta bancaria verificada"),
    ).toBeInTheDocument();
  });

  it("cliente: el límite viaja como cadena", async () => {
    const user = userEvent.setup();
    mockGetCustomer();
    apiFetch.mockImplementation((...args: unknown[]) => {
      const [pathArg, options] = args as [string, { method?: string, body?: unknown, ifMatch?: string }?];
      const method = options?.method ?? "GET";
      if (pathArg === "/maestros/terceros/p-1/customer" && method === "GET") {
        return Promise.resolve({
          id: "e-1",
          party_id: "p-1",
          version: 2,
          credit_days: 15,
          credit_limit: "1000.50",
          blocked: false,
        });
      }
      if (pathArg === "/maestros/terceros/p-1/customer" && method === "PUT") {
        return Promise.resolve({
          id: "e-1",
          party_id: "p-1",
          version: 3,
          credit_days: 15,
          credit_limit: "2000.75",
          blocked: false,
        });
      }
      return Promise.reject(
        new Error(`Unexpected call: ${pathArg} ${method}`),
      );
    });

    renderComponent({ roles: ["CLIENTE"] });

    const limiteInput = await screen.findByLabelText("Límite de crédito");
    await user.clear(limiteInput);
    await user.type(limiteInput, "2000.75");
    await user.click(
      screen.getByRole("button", { name: "Guardar Cliente" }),
    );

    await waitFor(() => {
      expect(
        hasCall("/maestros/terceros/p-1/customer", "PUT"),
      ).toBe(true);
    });
    const putCall = apiFetch.mock.calls.find((call) => {
      const [pathArg, options] = call as [string, { method?: string }?];
      return (
        pathArg === "/maestros/terceros/p-1/customer" &&
        (options?.method ?? "GET") === "PUT"
      );
    });
    expect(putCall?.[1]).toMatchObject({
      method: "PUT",
      body: { credit_limit: "2000.75" },
      ifMatch: "2",
    });
  });

  it("cliente: bloquear exige motivo del backend", async () => {
    const user = userEvent.setup();
    mockGetCustomer();
    apiFetch.mockImplementation((...args: unknown[]) => {
      const [pathArg, options] = args as [string, { method?: string, body?: unknown, ifMatch?: string }?];
      const method = options?.method ?? "GET";
      if (pathArg === "/maestros/terceros/p-1/customer" && method === "GET") {
        return Promise.resolve({
          id: "e-1",
          party_id: "p-1",
          version: 2,
          credit_days: 15,
          credit_limit: "1000.50",
          blocked: false,
        });
      }
      if (pathArg === "/maestros/terceros/p-1/customer" && method === "PUT") {
        return Promise.reject(
          new ApiError(422, {
            code: "CUSTOMER_BLOCK_REASON_REQUIRED",
            message: "Indica el motivo del bloqueo",
            details: {},
          }),
        );
      }
      return Promise.reject(
        new Error(`Unexpected call: ${pathArg} ${method}`),
      );
    });

    renderComponent({ roles: ["CLIENTE"] });

    const bloqueadoCheckbox = await screen.findByRole("checkbox", {
      name: "Bloqueado",
    });
    await user.click(bloqueadoCheckbox);
    await user.click(
      screen.getByRole("button", { name: "Guardar Cliente" }),
    );

    expect(
      await screen.findByText("Indica el motivo del bloqueo"),
    ).toBeInTheDocument();
  });

  it("solo muestra las secciones de sus roles", async () => {
    mockGetDriver();
    apiFetch.mockImplementation((...args: unknown[]) => {
      const [pathArg, options] = args as [string, { method?: string }?];
      const method = options?.method ?? "GET";
      if (pathArg === "/maestros/terceros/p-1/driver" && method === "GET") {
        return Promise.resolve({
          id: "e-1",
          party_id: "p-1",
          version: 2,
          license: "L123",
          categories: ["A", "B"],
          expiry: "2026-12-31T00:00:00+00:00",
          restrictions: "none",
        });
      }
      return Promise.reject(
        new Error(`Unexpected call: ${pathArg} ${method}`),
      );
    });

    renderComponent({ roles: ["CONDUCTOR"] });

    expect(await screen.findByText("Conductor")).toBeInTheDocument();
    expect(screen.queryByText("Cliente")).not.toBeInTheDocument();
    expect(screen.queryByText("Proveedor")).not.toBeInTheDocument();
    expect(
      hasCall("/maestros/terceros/p-1/customer", "GET"),
    ).toBe(false);
  });

  it("rechazar exige motivo", async () => {
    const user = userEvent.setup();
    apiFetch.mockImplementation((...args: unknown[]) => {
      const [pathArg, options] = args as [string, { method?: string, body?: unknown }?];
      const method = options?.method ?? "GET";
      if (pathArg === "/maestros/terceros/p-1/supplier" && method === "GET") {
        return Promise.resolve({
          id: "e-1",
          party_id: "p-1",
          version: 2,
          approval_status: "PENDING_APPROVAL",
        });
      }
      if (
        pathArg === "/maestros/terceros/p-1/roles/PROVEEDOR/reject" &&
        method === "POST"
      ) {
        return Promise.resolve({
          id: "e-1",
          party_id: "p-1",
          version: 3,
          approval_status: "REJECTED",
        });
      }
      return Promise.reject(
        new Error(`Unexpected call: ${pathArg} ${method}`),
      );
    });

    renderComponent({
      roles: ["PROVEEDOR"],
      allowedActions: { ...allowedActions, reject: true },
    });

    await user.click(
      await screen.findByRole("button", { name: "Rechazar proveedor" }),
    );
    const motivoInput = await screen.findByLabelText("Motivo del rechazo");
    await user.type(motivoInput, "revisión");
    await user.click(
      screen.getByRole("button", { name: "Rechazar" }),
    );

    await waitFor(() => {
      expect(
        hasCall(
          "/maestros/terceros/p-1/roles/PROVEEDOR/reject",
          "POST",
        ),
      ).toBe(true);
    });
    const postCall = apiFetch.mock.calls.find((call) => {
      const [pathArg, options] = call as [string, { method?: string }?];
      return (
        pathArg === "/maestros/terceros/p-1/roles/PROVEEDOR/reject" &&
        (options?.method ?? "GET") === "POST"
      );
    });
    expect(postCall?.[1]).toMatchObject({
      method: "POST",
      body: { reason: "revisión" },
    });
  });

  it("sin permiso oculta", async () => {
    mockPuede = false;
    mockGetSupplier();
    apiFetch.mockImplementation((...args: unknown[]) => {
      const [pathArg, options] = args as [string, { method?: string }?];
      const method = options?.method ?? "GET";
      if (pathArg === "/maestros/terceros/p-1/supplier" && method === "GET") {
        return Promise.resolve({
          id: "e-1",
          party_id: "p-1",
          version: 2,
          approval_status: "PENDING_APPROVAL",
        });
      }
      return Promise.reject(
        new Error(`Unexpected call: ${pathArg} ${method}`),
      );
    });

    renderComponent({
      roles: ["PROVEEDOR"],
      allowedActions: { ...allowedActions, approve: true },
    });

    expect(await screen.findByText("Proveedor")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Aprobar proveedor" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Guardar Proveedor" }),
    ).not.toBeInTheDocument();
  });

  it("versión desfasada avisa", async () => {
    const user = userEvent.setup();
    mockGetSupplier();
    apiFetch.mockImplementation((...args: unknown[]) => {
      const [pathArg, options] = args as [string, { method?: string, body?: unknown, ifMatch?: string }?];
      const method = options?.method ?? "GET";
      if (pathArg === "/maestros/terceros/p-1/supplier" && method === "GET") {
        return Promise.resolve({
          id: "e-1",
          party_id: "p-1",
          version: 2,
          approval_status: "PENDING_APPROVAL",
          category: "Cat A",
        });
      }
      if (pathArg === "/maestros/terceros/p-1/supplier" && method === "PUT") {
        return Promise.reject(
          new ApiError(409, {
            code: "VERSION_CONFLICT",
            message: "x",
            details: {},
          }),
        );
      }
      return Promise.reject(
        new Error(`Unexpected call: ${pathArg} ${method}`),
      );
    });

    renderComponent({ roles: ["PROVEEDOR"] });

    const categoriaInput = await screen.findByLabelText("Categoría");
    await user.clear(categoriaInput);
    await user.type(categoriaInput, "Insumos");
    await user.click(
      screen.getByRole("button", { name: "Guardar Proveedor" }),
    );

    expect(
      await screen.findByText(
        "Otro usuario modificó este registro. Recargue para ver los cambios.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Recargar" }),
    ).toBeInTheDocument();
  });
});
