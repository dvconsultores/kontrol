import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
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

const { TerceroDatos } = await import("./TerceroDatos");

function crearCliente() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

function renderizar(editable: boolean) {
  const cliente = crearCliente();
  render(
    <QueryClientProvider client={cliente}>
      <MemoryRouter>
        <TerceroDatos partyId="p-1" editable={editable} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return cliente;
}

function implementarGet({
  addresses = [],
  contacts = [],
  bankAccounts = [],
}: {
  addresses?: unknown[];
  contacts?: unknown[];
  bankAccounts?: unknown[];
} = {}) {
  apiFetch.mockImplementation(
    (ruta: string, opciones?: { method?: string }) => {
      const metodo = opciones?.method ?? "GET";

      if (metodo === "GET" && ruta === "/maestros/terceros/p-1/addresses") {
        return Promise.resolve({ items: addresses });
      }
      if (metodo === "GET" && ruta === "/maestros/terceros/p-1/contacts") {
        return Promise.resolve({ items: contacts });
      }
      if (
        metodo === "GET" &&
        ruta === "/maestros/terceros/p-1/bank-accounts"
      ) {
        return Promise.resolve({ items: bankAccounts });
      }

      return Promise.reject(
        new Error(`Petición no prevista: ${metodo} ${ruta}`),
      );
    },
  );
}

beforeEach(() => {
  mockPuede = true;
  apiFetch.mockReset();
});

describe("TerceroDatos", () => {
  it("agrega y edita una dirección, un contacto con ceros y verifica una cuenta", async () => {
    const usuario = userEvent.setup();

    implementarGet({
      addresses: [
        {
          id: "d-1",
          validity: "ACTIVE",
          version: 4,
          address: "Av. 1",
          city: "Caracas",
          is_fiscal: false,
          is_delivery: false,
        },
      ],
      contacts: [],
      bankAccounts: [
        {
          id: "c-1",
          validity: "ACTIVE",
          version: 1,
          bank: "Banco",
          account_number: "****0001",
          verified: false,
        },
      ],
    });

    renderizar(true);

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalled();
    });

    await usuario.click(
      screen.getByRole("button", { name: "Agregar en Direcciones" }),
    );

    await usuario.type(screen.getByLabelText(/Dirección/), "Av. 1");
    await usuario.click(screen.getByRole("checkbox", { name: "Fiscal" }));

    apiFetch.mockClear();
    apiFetch.mockImplementationOnce(() =>
      Promise.resolve({
        id: "d-2",
        validity: "ACTIVE",
        version: 1,
        address: "Av. 1",
        is_fiscal: true,
      }),
    );

    await usuario.click(screen.getByRole("button", { name: "Guardar" }));

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/maestros/terceros/p-1/addresses",
        expect.objectContaining({
          method: "POST",
          body: { address: "Av. 1", is_fiscal: true },
        }),
      );
    });

    await waitFor(() => {
      expect(
        screen.queryByRole("button", { name: "Agregar en Contactos" }),
      ).toBeTruthy();
    });

    await usuario.click(
      screen.getByRole("button", { name: "Agregar en Contactos" }),
    );

    await usuario.type(screen.getByLabelText(/Teléfono/), "04121234567");

    apiFetch.mockClear();
    apiFetch.mockImplementationOnce(() =>
      Promise.resolve({
        id: "c-2",
        validity: "ACTIVE",
        version: 1,
        phone: "04121234567",
      }),
    );

    await usuario.click(screen.getByRole("button", { name: "Guardar" }));

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/maestros/terceros/p-1/contacts",
        expect.objectContaining({
          method: "POST",
          body: { phone: "04121234567" },
        }),
      );
    });

    const evidencia = screen.getByLabelText(
      /Evidencia de Banco \*\*\*\*0001/,
    );
    await usuario.type(evidencia, "constancia");

    apiFetch.mockClear();
    apiFetch.mockImplementationOnce(() => Promise.resolve({}));

    await usuario.click(screen.getByRole("button", { name: "Verificar Banco" }));

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/maestros/terceros/p-1/bank-accounts/c-1/verify",
        expect.objectContaining({
          method: "POST",
          body: { evidence: "constancia" },
        }),
      );
    });
  });

  it("editar envía solo lo cambiado y la versión", async () => {
    const usuario = userEvent.setup();

    implementarGet({
      addresses: [
        {
          id: "d-1",
          validity: "ACTIVE",
          version: 4,
          address: "Av. 1",
          city: "Caracas",
          is_fiscal: false,
          is_delivery: false,
        },
      ],
    });

    renderizar(true);

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalled();
    });

    await usuario.click(await screen.findByRole("button", { name: "Editar Av. 1" }));

    const ciudad = screen.getByLabelText(/Ciudad/);
    await usuario.clear(ciudad);
    await usuario.type(ciudad, "Valencia");

    apiFetch.mockClear();
    apiFetch.mockImplementationOnce(() =>
      Promise.resolve({ id: "d-1", validity: "ACTIVE", version: 5 }),
    );

    await usuario.click(screen.getByRole("button", { name: "Guardar" }));

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/maestros/terceros/p-1/addresses/d-1",
        expect.objectContaining({
          method: "PATCH",
          body: { city: "Valencia" },
          ifMatch: "4",
        }),
      );
    });
  });

  it("versión desfasada avisa", async () => {
    const usuario = userEvent.setup();

    implementarGet({
      addresses: [
        {
          id: "d-1",
          validity: "ACTIVE",
          version: 4,
          address: "Av. 1",
          city: "Caracas",
        },
      ],
    });

    renderizar(true);

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalled();
    });

    await usuario.click(await screen.findByRole("button", { name: "Editar Av. 1" }));

    const ciudad = screen.getByLabelText(/Ciudad/);
    await usuario.clear(ciudad);
    await usuario.type(ciudad, "Valencia");

    apiFetch.mockClear();
    apiFetch.mockImplementationOnce(() =>
      Promise.reject(
        new ApiError(409, {
          code: "VERSION_CONFLICT",
          message: "x",
        }),
      ),
    );

    await usuario.click(screen.getByRole("button", { name: "Guardar" }));

    await waitFor(() => {
      expect(
        screen.getByText(
          "Otro usuario modificó este registro. Recargue para ver los cambios.",
        ),
      ).toBeTruthy();
    });

    expect(screen.getByRole("button", { name: "Recargar" })).toBeTruthy();
  });

  it("contacto no exige nada en cliente pero muestra el error del backend", async () => {
    const usuario = userEvent.setup();

    implementarGet();

    renderizar(true);

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalled();
    });

    await usuario.click(
      screen.getByRole("button", { name: "Agregar en Contactos" }),
    );

    apiFetch.mockClear();
    apiFetch.mockImplementationOnce(() =>
      Promise.reject(
        new ApiError(422, {
          code: "PARTY_CONTACT_EMPTY",
          message: "Indica al menos nombre, teléfono o correo",
        }),
      ),
    );

    await usuario.click(screen.getByRole("button", { name: "Guardar" }));

    await waitFor(() => {
      expect(
        screen.getByText("Indica al menos nombre, teléfono o correo"),
      ).toBeTruthy();
    });
  });

  it("sin edición no ofrece acciones y muestra el número enmascarado", async () => {
    implementarGet({
      bankAccounts: [
        {
          id: "c-1",
          validity: "ACTIVE",
          version: 1,
          bank: "Banco",
          account_number: "****0001",
          verified: false,
        },
      ],
    });

    renderizar(false);

    await waitFor(() => {
      expect(screen.getByText("Banco ****0001")).toBeTruthy();
    });

    expect(
      screen.queryByRole("button", { name: "Agregar en Direcciones" }),
    ).toBeNull();
    expect(screen.queryByRole("button", { name: /Desactivar/ })).toBeNull();
  });

  it("sin permiso oculta", async () => {
    mockPuede = false;

    implementarGet({
      bankAccounts: [
        {
          id: "c-1",
          validity: "ACTIVE",
          version: 1,
          bank: "Banco",
          account_number: "****0001",
          verified: false,
        },
      ],
    });

    renderizar(true);

    await waitFor(() => {
      expect(screen.getByText("Banco ****0001")).toBeTruthy();
    });

    expect(
      screen.queryByRole("button", { name: "Agregar en Direcciones" }),
    ).toBeNull();
    expect(screen.queryByRole("button", { name: /Verificar/ })).toBeNull();
  });
});
