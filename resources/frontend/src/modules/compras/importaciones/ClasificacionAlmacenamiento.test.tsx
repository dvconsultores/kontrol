import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

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

vi.mock("@/utils/descarga", () => ({
  descargarArchivo: vi.fn().mockResolvedValue("archivo.pdf"),
  mensajeDeDescarga: vi.fn().mockReturnValue("Error de descarga"),
}));

import { ClasificacionAlmacenamiento } from "./ClasificacionAlmacenamiento";
import type { AlmacenamientoRespuesta } from "./tipos";

function crearRespuesta(overrides: Partial<AlmacenamientoRespuesta> = {}): AlmacenamientoRespuesta {
  return {
    rows: [
      {
        receipt_id: "r-1",
        receipt_code: "REC-001",
        warehouse_id: "w-1",
        product_id: "p-1",
        product_name: "Producto Uno",
        state: "DISPONIBLE",
        pending_base: "10.000000",
        policy: { mode: "ENFORCED", on_no_rule: "BLOCK", version: null },
        profile: null,
        classification: null,
        labels: [],
        label_required: false,
        candidates: [],
        can_putaway: true,
        blocking_reason: null,
      },
    ],
    ...overrides,
  };
}

function crearClasificacion(overrides: Partial<AlmacenamientoRespuesta["rows"][number]["classification"]> = {}): NonNullable<AlmacenamientoRespuesta["rows"][number]["classification"]> {
  return {
    id: "clas-1",
    result: "CLASSIFIED",
    status: "CURRENT",
    rule_code: "REGLA-01",
    rule_name: "Regla de fríos",
    label_policy: "REQUIRED",
    target_label: "Zona Fríos (Z1)",
    reasons: ["Cumple la regla"],
    missing_criteria: [],
    stale: false,
    classified_at: "2025-01-15T10:00:00Z",
    classified_by_name: "operador",
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

describe("ClasificacionAlmacenamiento", () => {
  beforeEach(() => {
    mockPuede = true;
    apiFetch.mockReset();
    notify.mockReset();
  });

  it("sin filas muestra 'Sin mercancía pendiente de ubicar.'", async () => {
    apiFetch.mockResolvedValue({ rows: [] });
    renderizar(<ClasificacionAlmacenamiento importacionId="imp-1" onCambios={vi.fn()} />);
    expect(await screen.findByText("Sin mercancía pendiente de ubicar.")).toBeInTheDocument();
  });

  it("fila sin clasificar muestra 'Sin clasificar' y botón Clasificar hace POST", async () => {
    const user = userEvent.setup();
    const respuesta = crearRespuesta();
    apiFetch.mockResolvedValue(respuesta);
    renderizar(<ClasificacionAlmacenamiento importacionId="imp-1" onCambios={vi.fn()} />);
    const fila = await screen.findByRole("group", { name: "Producto Uno · REC-001" });
    expect(within(fila).getByText("Sin clasificar")).toBeInTheDocument();
    await user.click(within(fila).getByRole("button", { name: "Clasificar" }));
    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/importaciones/imp-1/storage/classify",
        expect.objectContaining({
          method: "POST",
          body: { receipt_id: "r-1", product_id: "p-1", state: "DISPONIBLE" },
        }),
      );
    });
  });

  it("CLASSIFIED REQUIRED sin etiqueta muestra estado y Generar etiqueta hace POST", async () => {
    const user = userEvent.setup();
    const respuesta = crearRespuesta({
      rows: [
        {
          ...crearRespuesta().rows[0],
          classification: crearClasificacion(),
          candidates: [{ id: "loc-1", code: "Z1-A1", name: "Rack A", path: "W1 / Zona Fríos / A1", zone_id: "z-1" }],
          can_putaway: false,
          blocking_reason: "Sin etiqueta",
        },
      ],
    });
    apiFetch.mockResolvedValue(respuesta);
    renderizar(<ClasificacionAlmacenamiento importacionId="imp-1" onCambios={vi.fn()} />);
    const fila = await screen.findByRole("group", { name: "Producto Uno · REC-001" });
    expect(within(fila).getByText("Zona determinada: Zona Fríos (Z1)")).toBeInTheDocument();
    expect(within(fila).getByText("Etiqueta requerida")).toBeInTheDocument();
    expect(within(fila).getByText("Sin etiqueta")).toBeInTheDocument();
    await user.click(within(fila).getByRole("button", { name: "Generar etiqueta" }));
    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/importaciones/imp-1/storage/labels",
        expect.objectContaining({
          method: "POST",
          body: { classification_id: "clas-1" },
        }),
      );
    });
    const botonUbicar = within(fila).getByRole("button", { name: "Ubicar Producto Uno" });
    expect(botonUbicar).toBeDisabled();
  });

  it("con etiqueta y can_putaway permite ubicar", async () => {
    const user = userEvent.setup();
    const respuesta = crearRespuesta({
      rows: [
        {
          ...crearRespuesta().rows[0],
          classification: crearClasificacion({ label_policy: "REQUIRED" }),
          labels: [{ id: "lab-1", reference: "ET-001", file_name: "etiqueta.pdf", generated_at: "2025-01-15T10:00:00Z" }],
          candidates: [{ id: "loc-1", code: "Z1-A1", name: "Rack A", path: "W1 / Zona Fríos / A1", zone_id: "z-1" }],
          can_putaway: true,
        },
      ],
    });
    apiFetch.mockResolvedValue(respuesta);
    renderizar(<ClasificacionAlmacenamiento importacionId="imp-1" onCambios={vi.fn()} />);
    const fila = await screen.findByRole("group", { name: "Producto Uno · REC-001" });
    await user.selectOptions(within(fila).getByLabelText(/^Ubicación de destino/), "loc-1");
    await user.click(within(fila).getByRole("button", { name: "Ubicar Producto Uno" }));
    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/importaciones/imp-1/storage/putaway",
        expect.objectContaining({
          method: "POST",
          body: {
            receipt_id: "r-1",
            product_id: "p-1",
            state: "DISPONIBLE",
            target_location_id: "loc-1",
            quantity: "10.000000",
          },
        }),
      );
    });
  });

  it("NO_RULE muestra el mensaje correspondiente", async () => {
    const respuesta = crearRespuesta({
      rows: [
        {
          ...crearRespuesta().rows[0],
          classification: crearClasificacion({ result: "NO_RULE", target_label: "", rule_code: "", rule_name: "" }),
        },
      ],
    });
    apiFetch.mockResolvedValue(respuesta);
    renderizar(<ClasificacionAlmacenamiento importacionId="imp-1" onCambios={vi.fn()} />);
    expect(await screen.findByText("No existe una regla de almacenamiento aplicable")).toBeInTheDocument();
  });

  it("mockPuede false oculta botones de acción", async () => {
    mockPuede = false;
    const respuesta = crearRespuesta();
    apiFetch.mockResolvedValue(respuesta);
    renderizar(<ClasificacionAlmacenamiento importacionId="imp-1" onCambios={vi.fn()} />);
    const fila = await screen.findByRole("group", { name: "Producto Uno · REC-001" });
    expect(within(fila).queryByRole("button", { name: "Clasificar" })).not.toBeInTheDocument();
    expect(within(fila).queryByRole("button", { name: "Generar etiqueta" })).not.toBeInTheDocument();
    expect(within(fila).queryByRole("button", { name: "Ubicar Producto Uno" })).not.toBeInTheDocument();
  });
});
