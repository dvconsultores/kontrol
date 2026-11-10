import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";

let mockPuede = true;
const apiFetch = vi.fn();
const notify = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify, dismiss: vi.fn(), notifications: [] }),
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

import { UbicacionFisica } from "./UbicacionFisica";
import type { UbicacionFisicaRespuesta, ValidacionUbicacion } from "./tipos";

const ubicacionA = { id: "loc-a", code: "A-01", name: "Rack A", path: "W1 / Zona 1 / A-01" };
const ubicacionB = { id: "loc-b", code: "B-02", name: null, path: "W1 / Zona 2 / B-02" };

function crearRespuesta(overrides: Partial<UbicacionFisicaRespuesta> = {}): UbicacionFisicaRespuesta {
  return {
    rows: [
      {
        receipt_id: "r-1",
        receipt_code: "REC-001",
        warehouse_id: "w-1",
        product_id: "p-1",
        product_name: "Producto Uno",
        state: "DISPONIBLE",
        lot_id: null,
        serial_id: null,
        location: ubicacionA,
        quantity: "10.000000",
        on_hand_at_location: "10.000000",
        last_validation: null,
      },
    ],
    history: [],
    locations_by_warehouse: {
      "w-1": [ubicacionA, ubicacionB],
    },
    ...overrides,
  };
}

function crearValidacion(overrides: Partial<ValidacionUbicacion> = {}): ValidacionUbicacion {
  return {
    id: "val-1",
    result: "MISMATCH",
    status: "PENDING",
    stale: false,
    warehouse_id: "w-1",
    product_id: "p-1",
    product_name: "Producto Uno",
    state: "DISPONIBLE",
    lot_id: null,
    serial_id: null,
    quantity: "10.000000",
    registered_location: ubicacionA,
    observed_location: ubicacionB,
    validated_at: "2025-01-15T10:00:00Z",
    validated_by_name: "almacen1",
    import_file_id: null,
    receipt_id: "r-1",
    receipt_code: "REC-001",
    relocation: null,
    ...overrides,
  };
}

function renderizar(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

describe("UbicacionFisica", () => {
  beforeEach(() => {
    mockPuede = true;
    apiFetch.mockReset();
    notify.mockReset();
  });

  it("muestra la ubicación registrada, la ruta y Sin validar", async () => {
    apiFetch.mockResolvedValue(crearRespuesta());
    renderizar(<UbicacionFisica importacionId="imp-1" onCambios={vi.fn()} />);

    expect(await screen.findByText("Ubicación registrada: A-01")).toBeTruthy();
    expect(screen.getByText("W1 / Zona 1 / A-01")).toBeTruthy();
    expect(screen.getByRole("status")).toHaveTextContent("Sin validar");
  });

  it("valida con la ubicación A y notifica éxito", async () => {
    const onCambios = vi.fn();
    apiFetch.mockImplementation((ruta: string) => {
      if (ruta.endsWith("/validate")) {
        return Promise.resolve(
          crearValidacion({ result: "MATCH", observed_location: ubicacionA }),
        );
      }
      return Promise.resolve(crearRespuesta());
    });
    renderizar(<UbicacionFisica importacionId="imp-1" onCambios={onCambios} />);

    const usuario = userEvent.setup();
    await usuario.selectOptions(
      await screen.findByLabelText("Ubicación encontrada"),
      "loc-a",
    );
    await usuario.click(
      screen.getByRole("button", { name: "Validar ubicación física" }),
    );

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/importaciones/imp-1/physical-locations/validate",
        expect.objectContaining({
          method: "POST",
          body: expect.objectContaining({
            receipt_id: "r-1",
            product_id: "p-1",
            state: "DISPONIBLE",
            registered_location_id: "loc-a",
            observed_location_id: "loc-a",
            quantity: "10.000000",
          }),
        }),
      );
    });
    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith({
        type: "success",
        title: "Ubicación física validada",
      });
    });
    expect(onCambios).toHaveBeenCalled();
  });

  it("muestra No coincide y el botón Reubicar por error con validación MISMATCH PENDING", async () => {
    apiFetch.mockResolvedValue(
      crearRespuesta({
        rows: [
          {
            ...crearRespuesta().rows[0],
            last_validation: crearValidacion(),
          },
        ],
      }),
    );
    renderizar(<UbicacionFisica importacionId="imp-1" onCambios={vi.fn()} />);

    expect(await screen.findByText("No coincide")).toBeTruthy();
    expect(screen.getByText("Registrada: A-01")).toBeTruthy();
    expect(screen.getByText("Encontrada: B-02")).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Reubicar por error" }),
    ).toBeTruthy();
  });

  it("reubica con motivo y notifica éxito", async () => {
    apiFetch.mockResolvedValueOnce(
      crearRespuesta({
        rows: [
          {
            ...crearRespuesta().rows[0],
            last_validation: crearValidacion(),
          },
        ],
      }),
    );
    apiFetch.mockResolvedValueOnce(
      crearValidacion({ status: "RELOCATED", relocation: {
        movement_id: "m-1",
        quantity: "10.000000",
        reason: "Error de colocación",
        relocated_at: "2025-01-15T11:00:00Z",
        relocated_by_name: "almacen1",
        source_location: ubicacionA,
        target_location: ubicacionB,
      } }),
    );
    renderizar(<UbicacionFisica importacionId="imp-1" onCambios={vi.fn()} />);

    const usuario = userEvent.setup();
    await usuario.click(
      await screen.findByRole("button", { name: "Reubicar por error" }),
    );

    expect(await screen.findByText("Origen")).toBeTruthy();
    expect(screen.getByText("A-01")).toBeTruthy();
    expect(screen.getByText("Destino")).toBeTruthy();
    expect(screen.getByText("B-02")).toBeTruthy();

    await usuario.click(
      screen.getByRole("button", { name: "Confirmar reubicación" }),
    );
    expect(
      await screen.findByText("Escribe el motivo de la reubicación."),
    ).toBeTruthy();
    expect(apiFetch).not.toHaveBeenCalledWith(
      "/inventory/location-validations/val-1/relocate",
      expect.anything(),
    );

    await usuario.type(screen.getByLabelText(/^Motivo/), "Error de colocación");
    await usuario.click(
      screen.getByRole("button", { name: "Confirmar reubicación" }),
    );

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/inventory/location-validations/val-1/relocate",
        expect.objectContaining({
          method: "POST",
          body: { quantity: "10.000000", reason: "Error de colocación" },
        }),
      );
    });
    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "success",
          title: expect.stringContaining("Reubicación realizada"),
        }),
      );
    });
  });

  it("con stale true muestra aviso y no muestra Reubicar por error", async () => {
    apiFetch.mockResolvedValue(
      crearRespuesta({
        rows: [
          {
            ...crearRespuesta().rows[0],
            last_validation: crearValidacion({ stale: true }),
          },
        ],
      }),
    );
    renderizar(<UbicacionFisica importacionId="imp-1" onCambios={vi.fn()} />);

    expect(
      await screen.findByText("La existencia cambió después de la validación: valide de nuevo"),
    ).toBeTruthy();
    expect(
      screen.queryByRole("button", { name: "Reubicar por error" }),
    ).toBeNull();
  });

  it("con mockPuede false no muestra botones de validar ni reubicar", async () => {
    mockPuede = false;
    apiFetch.mockResolvedValue(
      crearRespuesta({
        rows: [
          {
            ...crearRespuesta().rows[0],
            last_validation: crearValidacion(),
          },
        ],
      }),
    );
    renderizar(<UbicacionFisica importacionId="imp-1" onCambios={vi.fn()} />);

    expect(await screen.findByText("Ubicación registrada: A-01")).toBeTruthy();
    expect(
      screen.queryByRole("button", { name: "Validar ubicación física" }),
    ).toBeNull();
    expect(
      screen.queryByRole("button", { name: "Reubicar por error" }),
    ).toBeNull();
  });

  it("muestra el historial con reubicación sin UUIDs", async () => {
    apiFetch.mockResolvedValue(
      crearRespuesta({
        history: [
          crearValidacion({
            status: "RELOCATED",
            relocation: {
              movement_id: "m-1",
              quantity: "10.000000",
              reason: "Error de colocación",
              relocated_at: "2025-01-15T11:00:00Z",
              relocated_by_name: "almacen1",
              source_location: ubicacionA,
              target_location: ubicacionB,
            },
          }),
        ],
      }),
    );
    renderizar(<UbicacionFisica importacionId="imp-1" onCambios={vi.fn()} />);

    const historial = await screen.findByLabelText("Historial de ubicación física");
    expect(within(historial).getAllByText(/A-01 → B-02/).length).toBeGreaterThan(0);
    expect(within(historial).getByText(/No coincide/)).toBeTruthy();
    expect(
      within(historial).getByText(/Reubicado 10\.000000: A-01 → B-02 · Motivo: Error de colocación/),
    ).toBeTruthy();
    expect(historial.textContent).not.toMatch(/[0-9a-f]{8}-[0-9a-f]{4}-/);
  });

  it("maneja LOCATION_VALIDATION_STALE en relocate y refresca", async () => {
    apiFetch.mockResolvedValueOnce(
      crearRespuesta({
        rows: [
          {
            ...crearRespuesta().rows[0],
            last_validation: crearValidacion(),
          },
        ],
      }),
    );
    apiFetch.mockRejectedValueOnce(
      new ApiError(409, {
        code: "LOCATION_VALIDATION_STALE",
        message: "stale",
      }),
    );
    apiFetch.mockResolvedValueOnce(crearRespuesta());
    renderizar(<UbicacionFisica importacionId="imp-1" onCambios={vi.fn()} />);

    const usuario = userEvent.setup();
    await usuario.click(
      await screen.findByRole("button", { name: "Reubicar por error" }),
    );
    await usuario.type(screen.getByLabelText(/^Motivo/), "Error de colocación");
    await usuario.click(
      screen.getByRole("button", { name: "Confirmar reubicación" }),
    );

    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith({
        type: "warning",
        title: "La existencia cambió después de la validación. Valide de nuevo.",
      });
    });
    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/importaciones/imp-1/physical-locations",
      );
    });
  });
});
