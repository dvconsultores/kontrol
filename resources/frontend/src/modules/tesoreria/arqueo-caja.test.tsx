/** Spec 038 · FLOAT-038-B — la pantalla de cajas envía el conteo como texto y no tolera un céntimo. */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiFetch = vi.fn();
const notify = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));
vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify }),
}));
vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({
    estado: "LISTA",
    puede: () => true,
    tiene: () => true,
    motivo: () => null,
    motivoDeCapacidad: () => null,
  }),
}));

const { CajasPage } = await import("./cajas/CajasPage");

/** Un importe que un `double` de JavaScript no representa: `Number` lo deja en …56.8. */
const EXACTO = "1234567890123456.78";
const MOSTRADO = "1.234.567.890.123.456,78";

const acciones = (extra: Record<string, boolean>) => ({
  view: true, arqueo: false, pre_close: false, close: false, reject: false, ...extra,
});
const sesion = (id: string, extra: Record<string, unknown>) => ({
  id, cashbox_id: `caja-${id}`, opened_by: null, opened_at: "2026-09-15", closed_at: null,
  opened_amount: "0.00", counted_amount: null, expected_amount: "0.00", difference: null,
  status: "OPEN", approval_note: null, movements: [], allowed_actions: acciones({}), ...extra,
});

const abierta = sesion("abierta", { expected_amount: EXACTO, allowed_actions: acciones({ arqueo: true }) });
const faltaUnCentimo = sesion("falta", {
  status: "PRE_CLOSED", opened_amount: "100.00", expected_amount: "100.00", counted_amount: "99.99",
  difference: "-0.01", allowed_actions: acciones({ close: true, reject: true }),
});
const cuadrada = sesion("cuadra", {
  status: "PRE_CLOSED", opened_amount: "100.00", expected_amount: "100.00", counted_amount: "100.00",
  difference: "0.00", allowed_actions: acciones({ close: true, reject: true }),
});

function responder(ruta: string, opciones?: { method?: string; body?: Record<string, unknown> }): Promise<unknown> {
  if (opciones?.method === "POST") return Promise.resolve({ ...abierta, status: "ARCHED" });
  if (ruta === "/treasury/cash-sessions") return Promise.resolve({ items: [abierta, faltaUnCentimo, cuadrada] });
  return Promise.resolve({ items: [] });
}

function montar(): void {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <CajasPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const arqueos = (): Array<Record<string, unknown>> =>
  apiFetch.mock.calls
    .filter(([ruta, opciones]) => String(ruta).endsWith("/arqueo") && opciones?.method === "POST")
    .map(([, opciones]) => opciones.body as Record<string, unknown>);

async function fila(id: string): Promise<HTMLElement> {
  return (await screen.findByText(`caja-${id}`)).closest("tr") as HTMLElement;
}

describe("Cajas · arqueo", () => {
  beforeEach(() => {
    apiFetch.mockReset();
    apiFetch.mockImplementation(responder);
    notify.mockReset();
  });

  it("envía el conteo como texto exacto, sin pasar por Number", async () => {
    const user = userEvent.setup();
    montar();
    await user.click(within(await fila("abierta")).getByRole("button", { name: "arqueo" }));

    const conteo = screen.getByLabelText("Conteo");
    expect(conteo).toHaveValue(EXACTO);
    await user.clear(conteo);
    await user.type(conteo, EXACTO);
    await user.click(screen.getByRole("button", { name: "Registrar arqueo" }));

    await waitFor(() => expect(arqueos()).toHaveLength(1));
    await waitFor(() => expect(screen.queryByRole("button", { name: "Registrar arqueo" })).toBeNull());
    const [cuerpo] = arqueos();
    expect(typeof cuerpo.counted_amount).toBe("string");
    expect(cuerpo.counted_amount).toBe(EXACTO);
  });

  it("no envía un conteo con más de dos decimales: no lo redondea", async () => {
    const user = userEvent.setup();
    montar();
    await user.click(within(await fila("abierta")).getByRole("button", { name: "arqueo" }));

    const conteo = screen.getByLabelText("Conteo");
    await user.clear(conteo);
    await user.type(conteo, "100.005");
    const boton = screen.getByRole("button", { name: "Registrar arqueo" });
    await user.click(boton);

    await waitFor(() => expect(boton).toBeEnabled());
    expect(notify).toHaveBeenCalledWith(expect.objectContaining({ type: "error" }));
    expect(arqueos()).toHaveLength(0);
  });

  it("muestra los importes exactos que devolvió el servidor", async () => {
    montar();
    expect(within(await fila("abierta")).getByText(MOSTRADO)).toBeInTheDocument();
  });
});

describe("Cajas · cierre", () => {
  beforeEach(() => {
    apiFetch.mockReset();
    apiFetch.mockImplementation(responder);
  });

  it("un céntimo de diferencia exige aprobación: no hay tolerancia", async () => {
    const user = userEvent.setup();
    montar();
    await user.click(within(await fila("falta")).getByRole("button", { name: "cerrar" }));

    expect(screen.getByText(/Diferencia: -0,01/)).toBeInTheDocument();
    const aprobar = screen.getByRole("checkbox", { name: /Aprobar diferencia de -0,01/ });
    expect(aprobar).toBeChecked();
    await user.click(aprobar);
    expect(screen.getByRole("button", { name: "Cerrar caja" })).toBeDisabled();
  });

  it("si cuadra exacto no pide aprobación", async () => {
    const user = userEvent.setup();
    montar();
    await user.click(within(await fila("cuadra")).getByRole("button", { name: "cerrar" }));

    expect(screen.queryByRole("checkbox", { name: /Aprobar diferencia/ })).toBeNull();
    expect(screen.getByRole("button", { name: "Cerrar caja" })).toBeEnabled();
  });
});

describe("guarda del camino del conteo", () => {
  const fuente = readFileSync(resolve(__dirname, "cajas/CajasPage.tsx"), "utf8");

  it("el conteo no se convierte a número", () => {
    expect(fuente).not.toMatch(/(Number|parseFloat)\(\s*(countedAmount|conteo)\b/);
    expect(fuente).not.toMatch(/[:=(,]\s*\+\s*(countedAmount|conteo)\b/);
  });

  it("los importes de la sesión no se formatean con toFixed ni se comparan como números", () => {
    expect(fuente).not.toMatch(/(expected_amount|counted_amount|difference|diff)\S*\.toFixed/);
    expect(fuente).not.toMatch(/difference \?\? 0\)?\s*!==?\s*0/);
  });
});
