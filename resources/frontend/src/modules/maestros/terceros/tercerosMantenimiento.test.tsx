import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import { TerceroNuevoPage } from "./TerceroNuevoPage";
import { TercerosPage } from "./TercerosPage";

const apiFetch = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: vi.fn() }),
}));

vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({
    estado: "LISTA",
    tiene: () => true,
    puede: () => true,
    motivo: () => null,
    motivoDeCapacidad: () => null,
  }),
}));

function renderNuevo() {
  const router = createMemoryRouter(
    [
      {
        path: "/maestros/terceros/nuevo",
        element: <TerceroNuevoPage />,
      },
      {
        path: "/maestros/terceros/:partyId",
        element: <div>detalle cargado</div>,
      },
    ],
    { initialEntries: ["/maestros/terceros/nuevo"] },
  );

  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

function renderListado() {
  const router = createMemoryRouter(
    [
      {
        path: "/maestros/terceros",
        element: <TercerosPage />,
      },
    ],
    { initialEntries: ["/maestros/terceros"] },
  );

  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiFetch.mockReset();
});

describe("terceros mantenimiento", () => {
  it("alta guarda una vez y llega al detalle", async () => {
    apiFetch.mockResolvedValueOnce({
      id: "p-1",
      code: "T-001",
      name: "Tercero de prueba",
      person_type: "NATURAL",
      legal_name: null,
      trade_name: null,
      tax_id: "J-00123456-1",
      roles: ["PROVEEDOR"],
      status: "ACTIVE",
      allowed_actions: [],
      nationality: null,
      residence: null,
      economic_activity: null,
      version: 1,
    });

    renderNuevo();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/^Código/), "T-001");
    await user.type(screen.getByLabelText(/^Nombre \*/), "Tercero de prueba");
    await user.click(screen.getByLabelText("Proveedor"));
    await user.type(screen.getByLabelText(/^RIF/), "J-00123456-1");
    await user.click(screen.getByRole("button", { name: "Guardar tercero" }));

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledTimes(1);
    });

    expect(apiFetch).toHaveBeenCalledWith("/maestros/terceros", {
      method: "POST",
      body: {
        code: "T-001",
        name: "Tercero de prueba",
        person_type: "JURIDICA",
        roles: ["PROVEEDOR"],
        tax_id: "J-00123456-1",
        legal_name: null,
        trade_name: null,
      },
    });

    expect(await screen.findByText("detalle cargado")).toBeVisible();
    expect(screen.queryByText("¿Descartar los cambios sin guardar?")).not.toBeInTheDocument();
  });

  it("sin rol no llama", async () => {
    renderNuevo();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/^Código/), "T-001");
    await user.type(screen.getByLabelText(/^Nombre \*/), "Tercero de prueba");
    await user.click(screen.getByRole("button", { name: "Guardar tercero" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Seleccione al menos un rol.");
    expect(apiFetch).not.toHaveBeenCalled();
  });

  it("duplicado muestra el motivo y el enlace", async () => {
    apiFetch.mockRejectedValueOnce(
      new ApiError(409, {
        code: "PARTY_DUPLICATE_TAX_ID",
        message: "RIF duplicado",
        details: { party_id: "p-9" },
      }),
    );

    renderNuevo();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/^Código/), "T-001");
    await user.type(screen.getByLabelText(/^Nombre \*/), "Tercero de prueba");
    await user.click(screen.getByLabelText("Proveedor"));
    await user.click(screen.getByRole("button", { name: "Guardar tercero" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("RIF duplicado");
    expect(screen.getByRole("link", { name: "Ver tercero existente" })).toHaveAttribute(
      "href",
      "/maestros/terceros/p-9",
    );
  });

  it("listado pagina en servidor y filtra", async () => {
    apiFetch.mockResolvedValueOnce({
      items: [],
      total: 60,
      page: 1,
      page_size: 25,
    });
    apiFetch.mockResolvedValueOnce({
      items: [],
      total: 2,
      page: 1,
      page_size: 25,
    });

    renderListado();
    const user = userEvent.setup();

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        expect.stringContaining("page=1"),
      );
    });

    expect(apiFetch.mock.calls[0][0]).toContain("page_size=25");
    expect(apiFetch.mock.calls[0][0]).not.toContain("status=");

    await user.click(screen.getByRole("button", { name: "Inactivos" }));

    await waitFor(() => {
      expect(apiFetch).toHaveBeenLastCalledWith(
        expect.stringContaining("status=INACTIVE"),
      );
    });

    expect(apiFetch.mock.calls[1][0]).toContain("page=1");
  });
});
