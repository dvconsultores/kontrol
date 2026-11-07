/** Recepciones: la pantalla sigue la máquina que publica el backend (FR-004-031). */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { notify } = vi.hoisted(() => ({ notify: vi.fn() }));

const apiFetch = vi.fn();
vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));
vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({ activeCompany: { id: "emp-a", name: "Empresa" } }),
}));
vi.mock("@/app/contexts/NotificationContext", () => ({ useNotifications: () => ({ notify }) }));
vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({
    estado: "LISTA",
    tiene: () => true,
    puede: () => true,
    motivo: () => null,
    motivoDeCapacidad: () => null,
  }),
}));

const { RecepcionesPage } = await import("./RecepcionesPage");

interface Opciones {
  method?: string;
  body?: unknown;
}

type Acciones = Record<"confirm" | "cancel" | "send_to_quality" | "record_quality" | "accept" | "close", boolean>;

const NINGUNA: Acciones = { confirm: false, cancel: false, send_to_quality: false, record_quality: false, accept: false, close: false };

function servidor(status: string, acciones: Partial<Acciones>) {
  return (path: string, opciones?: Opciones): Promise<unknown> => {
    const url = new URL(path, "http://k").pathname;
    const recepcion = {
      id: "r1",
      code: "REC-1",
      order_id: "o1",
      order_code: "OC-1",
      warehouse_id: "w1",
      status,
      quality_status: "PENDING",
      allowed_actions: { ...NINGUNA, ...acciones },
    };
    if (opciones?.method === "POST") {
      return Promise.resolve({ id: "r1", status });
    }
    if (url === "/purchasing/receipts") {
      return Promise.resolve({ items: [recepcion] });
    }
    if (url === "/purchasing/receipts/r1") {
      return Promise.resolve({ ...recepcion, lines: [] });
    }
    return Promise.resolve({ items: [], total: 0, page: 1, page_size: 20 });
  };
}

function montar() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <RecepcionesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

async function fila(): Promise<HTMLElement> {
  const celda = await screen.findByText("REC-1");
  return celda.closest("tr") as HTMLElement;
}

function posts(sufijo: string): unknown[][] {
  return apiFetch.mock.calls.filter(([path, opciones]) => {
    const opc = opciones as Opciones | undefined;
    return opc?.method === "POST" && new URL(String(path), "http://k").pathname.endsWith(sufijo);
  });
}

beforeEach(() => {
  apiFetch.mockReset();
  notify.mockReset();
});

describe("Recepciones · máquina de estados", () => {
  it.each([
    ["confirmar", { confirm: true }, "/confirm", {}],
    ["enviar a calidad", { send_to_quality: true }, "/quality", {}],
    ["conforme", { record_quality: true }, "/quality", { quality_status: "APPROVED" }],
    ["no conforme", { record_quality: true }, "/quality", { quality_status: "REJECTED" }],
    ["aceptar", { accept: true }, "/accept", {}],
    ["cerrar", { close: true }, "/close", {}],
  ])("el botón %s sigue la acción publicada", async (boton, acciones, sufijo, cuerpo) => {
    apiFetch.mockImplementation(servidor("DRAFT", acciones as Partial<Acciones>));
    montar();
    fireEvent.click(within(await fila()).getByRole("button", { name: boton }));
    await waitFor(() => expect(posts(sufijo)).toHaveLength(1));
    const [, opciones] = posts(sufijo)[0] as [string, Opciones];
    expect(opciones.body).toEqual(cuerpo);
  });

  it("sin acciones publicadas no hay botones de estado", async () => {
    apiFetch.mockImplementation(servidor("CONFIRMED", {}));
    montar();
    const dentro = within(await fila());
    expect(dentro.queryByRole("button", { name: "confirmar" })).toBeNull();
    expect(dentro.queryByRole("button", { name: "enviar a calidad" })).toBeNull();
    expect(dentro.queryByRole("button", { name: "conforme" })).toBeNull();
    expect(dentro.queryByRole("button", { name: "no conforme" })).toBeNull();
    expect(dentro.queryByRole("button", { name: "aceptar" })).toBeNull();
    expect(dentro.queryByRole("button", { name: "cerrar" })).toBeNull();
    expect(dentro.getByRole("button", { name: "detalle" })).toBeTruthy();
  });

  it("un borrador sin permiso de confirmar no muestra confirmar", async () => {
    apiFetch.mockImplementation(servidor("DRAFT", { cancel: true }));
    montar();
    const dentro = within(await fila());
    expect(dentro.queryByRole("button", { name: "confirmar" })).toBeNull();
    expect(dentro.getByRole("button", { name: "detalle" })).toBeTruthy();
  });

  it("el estado no decide: aceptar solo si el backend lo permite", async () => {
    apiFetch.mockImplementation(servidor("QUALITY_PENDING", { record_quality: true }));
    montar();
    const dentro = within(await fila());
    expect(dentro.getByRole("button", { name: "conforme" })).toBeTruthy();
    expect(dentro.queryByRole("button", { name: "aceptar" })).toBeNull();
  });

  it.each([
    ["QUALITY_PENDING", "Pendiente de calidad"],
    ["PARTIALLY_ACCEPTED", "Aceptada parcialmente"],
    ["CLOSED", "Cerrada"],
    ["CANCELLED", "Anulada"],
  ])("la fila muestra %s como %s", async (estado, etiqueta) => {
    apiFetch.mockImplementation(servidor(estado, {}));
    montar();
    const dentro = within(await fila());
    expect(dentro.getByText(etiqueta)).toBeTruthy();
  });

  it("anular exige motivo", async () => {
    apiFetch.mockImplementation(servidor("DRAFT", { confirm: true, cancel: true }));
    montar();
    fireEvent.click(within(await fila()).getByRole("button", { name: "detalle" }));
    fireEvent.click(await screen.findByRole("button", { name: "Anular recepción" }));
    await waitFor(() =>
      expect(notify).toHaveBeenCalledWith({
        type: "error",
        title: "No fue posible anular la recepción",
        description: "Indique el motivo.",
      }),
    );
    expect(posts("/cancel")).toHaveLength(0);
  });

  it("anular envía el motivo", async () => {
    apiFetch.mockImplementation(servidor("DRAFT", { confirm: true, cancel: true }));
    montar();
    fireEvent.click(within(await fila()).getByRole("button", { name: "detalle" }));
    await screen.findByRole("button", { name: "Anular recepción" });
    fireEvent.change(screen.getByLabelText(/^Motivo de anulación/), { target: { value: "Creada por error" } });
    fireEvent.click(screen.getByRole("button", { name: "Anular recepción" }));
    await waitFor(() => expect(posts("/cancel")).toHaveLength(1));
    const [, opciones] = posts("/cancel")[0] as [string, Opciones];
    expect(opciones.body).toEqual({ reason: "Creada por error" });
  });

  it("sin permiso de anular no hay anulación", async () => {
    apiFetch.mockImplementation(servidor("DRAFT", { confirm: true }));
    montar();
    fireEvent.click(within(await fila()).getByRole("button", { name: "detalle" }));
    await screen.findByRole("heading", { name: "Inspección de REC-1" });
    expect(screen.queryByRole("button", { name: "Anular recepción" })).toBeNull();
    expect(screen.queryByLabelText(/^Motivo de anulación/)).toBeNull();
  });
});
