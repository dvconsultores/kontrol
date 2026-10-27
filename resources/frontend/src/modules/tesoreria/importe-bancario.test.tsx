/** Spec 038 · FLOAT-038-A — la pantalla envía y muestra el importe bancario como texto exacto. */
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

const { IngresosEgresosPage } = await import("./ingresos-egresos/IngresosEgresosPage");
const { ConciliacionPage } = await import("./conciliacion/ConciliacionPage");

/** Un importe que un `double` de JavaScript no representa: `Number` lo deja en …56.8. */
const EXACTO = "1234567890123456.78";
const MOSTRADO = "1.234.567.890.123.456,78";

const cuenta = { id: "acc-1", code: "CT-1", name: "Operativa", currency: "VED" };
const movimiento = {
  id: "bt-1", account_id: "acc-1", txn_date: "2026-09-14", value_date: "2026-09-14", direction: "IN",
  amount: EXACTO, currency: "VED", reference: "REF-EXACTA", source: "ADJUSTMENT", payment_id: null,
  commission: null, status: "PENDING",
};
const conciliacion = {
  id: "rec-1", account_id: "acc-1", statement_date: null, statement_ref: "EXT-1", opening_balance: null,
  closing_balance: null, status: "DRAFT", approved_by: null, approved_at: null, allowed_actions: {}, lines: [],
};

function responder(ruta: string, opciones?: { method?: string; body?: Record<string, unknown> }): Promise<unknown> {
  if (opciones?.method === "POST") return Promise.resolve({ ...movimiento, amount: opciones.body?.amount });
  if (ruta === "/treasury/accounts") return Promise.resolve({ items: [cuenta] });
  if (ruta === "/treasury/bank-transactions") return Promise.resolve({ items: [movimiento] });
  if (ruta === "/treasury/reconciliations") return Promise.resolve({ items: [conciliacion] });
  return Promise.resolve({ items: [] });
}

function montar(elemento: React.ReactNode): void {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>{elemento}</MemoryRouter>
    </QueryClientProvider>,
  );
}

const envios = (): Array<Record<string, unknown>> =>
  apiFetch.mock.calls
    .filter(([ruta, opciones]) => ruta === "/treasury/bank-transactions" && opciones?.method === "POST")
    .map(([, opciones]) => opciones.body as Record<string, unknown>);

async function formularioDeAjuste(): Promise<HTMLFormElement> {
  const boton = await screen.findByRole("button", { name: "Registrar ajuste" });
  const form = boton.closest("form") as HTMLFormElement;
  await within(form).findByRole("option", { name: "Operativa (CT-1)" });
  return form;
}

/**
 * Pulsa «Registrar ajuste» y espera a que el botón termine.
 *
 * `AsyncButton` vuelve a habilitarse en un `finally`, después de la petición: solo
 * entonces se sabe qué se envió y qué se notificó, y ningún `setState` queda
 * pendiente cuando el entorno se desmonta.
 */
async function registrarAjuste(user: ReturnType<typeof userEvent.setup>, form: HTMLFormElement): Promise<void> {
  const boton = within(form).getByRole("button", { name: "Registrar ajuste" });
  await user.click(boton);
  await waitFor(() => expect(boton).toBeEnabled());
}

describe("Ingresos y egresos · importe bancario", () => {
  beforeEach(() => {
    apiFetch.mockReset();
    apiFetch.mockImplementation(responder);
    notify.mockReset();
  });

  it("envía el importe como texto exacto, sin pasar por Number", async () => {
    const user = userEvent.setup();
    montar(<IngresosEgresosPage />);
    const form = await formularioDeAjuste();

    await user.selectOptions(within(form).getByLabelText("Cuenta"), "acc-1");
    await user.type(within(form).getByLabelText("Monto"), EXACTO);
    await registrarAjuste(user, form);

    expect(envios()).toHaveLength(1);
    const [cuerpo] = envios();
    expect(typeof cuerpo.amount).toBe("string");
    expect(cuerpo.amount).toBe(EXACTO);
  });

  it("no envía un importe con más de dos decimales: no lo redondea", async () => {
    const user = userEvent.setup();
    montar(<IngresosEgresosPage />);
    const form = await formularioDeAjuste();

    await user.selectOptions(within(form).getByLabelText("Cuenta"), "acc-1");
    await user.type(within(form).getByLabelText("Monto"), "0.005");
    await registrarAjuste(user, form);

    expect(notify).toHaveBeenCalledWith(expect.objectContaining({ type: "error" }));
    expect(envios()).toHaveLength(0);
  });

  it("muestra en la tabla el importe exacto que devolvió el servidor", async () => {
    montar(<IngresosEgresosPage />);
    expect(await screen.findByText(MOSTRADO)).toBeInTheDocument();
    expect(screen.queryByText(/1\.234\.567\.890\.123\.456,8\b/)).toBeNull();
  });
});

describe("Conciliación · importe bancario", () => {
  beforeEach(() => {
    apiFetch.mockReset();
    apiFetch.mockImplementation(responder);
  });

  it("la lista de movimientos muestra el importe exacto", async () => {
    const user = userEvent.setup();
    montar(<ConciliacionPage />);
    await user.click(await screen.findByRole("button", { name: "detalle" }));
    expect(
      await screen.findByRole("option", { name: `2026-09-14 · ${MOSTRADO} · REF-EXACTA` }),
    ).toBeInTheDocument();
  });
});

describe("guarda del camino del importe bancario", () => {
  const leer = (relativo: string): string => readFileSync(resolve(__dirname, relativo), "utf8");

  it("la pantalla de ajustes no convierte el importe a número", () => {
    const fuente = leer("ingresos-egresos/IngresosEgresosPage.tsx");
    expect(fuente).not.toMatch(/(Number|parseFloat)\(\s*(amount|importe)\b/);
    expect(fuente).not.toMatch(/[:=(,]\s*\+\s*(amount|importe)\b/);
  });

  it("la conciliación no formatea el importe bancario con toFixed", () => {
    expect(leer("conciliacion/ConciliacionPage.tsx")).not.toMatch(/\.amount\.toFixed/);
  });
});
