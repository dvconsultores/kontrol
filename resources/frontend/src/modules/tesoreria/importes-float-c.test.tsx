/** Spec 038 · FLOAT-038-C — las tres pantallas que envían los importes restantes.
 *
 * Lo que se comprueba no es lo que la pantalla muestra, sino el **cuerpo real** que
 * sale por la red: si alguien vuelve a poner `Number(...)` en medio, el importe
 * exacto llega redondeado y estas pruebas lo dicen.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
const { TransferenciasPage } = await import("./transferencias/TransferenciasPage");
const { IgftPage } = await import("./igft/IgftPage");

/** Un importe que un `double` de JavaScript no representa: `Number` lo deja en …56.8. */
const EXACTO = "1234567890123456.78";

const caja = { id: "cb-1", code: "C1", name: "Caja 1", currency: "VED", status: "ACTIVE" };
const cuenta = { id: "acc-1", code: "CT-1", name: "Operativa", currency: "VED" };

function pintar(page: React.JSX.Element) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{page}</MemoryRouter>
    </QueryClientProvider>,
  );
}

/** El cuerpo del primer POST que la pantalla envió. */
function cuerpoEnviado(): Record<string, unknown> {
  const envio = apiFetch.mock.calls.find((c) => (c[1] as { method?: string } | undefined)?.method === "POST");
  expect(envio, "la pantalla no llegó a enviar nada").toBeTruthy();
  return (envio![1] as { body: Record<string, unknown> }).body;
}

beforeEach(() => {
  apiFetch.mockReset();
  notify.mockReset();
});

describe("FLOAT-038-C · el importe sale como texto exacto", () => {
  it("la apertura de caja envía el fondo como texto, no como número", async () => {
    apiFetch.mockImplementation((ruta: string) =>
      Promise.resolve(ruta === "/treasury/cashboxes" ? { items: [caja] } : { items: [] }),
    );
    pintar(<CajasPage />);
    await waitFor(() => expect(screen.getByRole("option", { name: /Caja 1/ })).toBeInTheDocument());

    await userEvent.selectOptions(screen.getByLabelText("Caja"), "cb-1");
    await userEvent.clear(screen.getByLabelText("Fondo inicial"));
    await userEvent.type(screen.getByLabelText("Fondo inicial"), EXACTO);
    await userEvent.click(screen.getByRole("button", { name: "Abrir caja" }));

    await waitFor(() => expect(cuerpoEnviado().opened_amount).toBe(EXACTO));
    expect(typeof cuerpoEnviado().opened_amount).toBe("string");
  });

  it("la transferencia envía el importe como texto exacto", async () => {
    apiFetch.mockImplementation((ruta: string) =>
      Promise.resolve(ruta === "/treasury/accounts" ? { items: [cuenta] } : { items: [] }),
    );
    pintar(<TransferenciasPage />);
    await waitFor(() => expect(screen.getAllByRole("option", { name: /Operativa/ }).length).toBeGreaterThan(0));

    // Cada tramo tiene dos selectores: el tipo (cuenta o caja) y la selección.
    const [, origen, , destino] = screen.getAllByRole("combobox");
    await userEvent.selectOptions(origen, "acc-1");
    await userEvent.selectOptions(destino, "acc-1");
    await userEvent.type(screen.getByLabelText("Monto"), EXACTO);
    await userEvent.click(screen.getByRole("button", { name: "Transferir" }));

    await waitFor(() => expect(cuerpoEnviado().amount).toBe(EXACTO));
  });

  it("un importe inválido no llega a salir a la red", async () => {
    apiFetch.mockImplementation((ruta: string) =>
      Promise.resolve(ruta === "/treasury/accounts" ? { items: [cuenta] } : { items: [] }),
    );
    pintar(<TransferenciasPage />);
    await waitFor(() => expect(screen.getAllByRole("option", { name: /Operativa/ }).length).toBeGreaterThan(0));

    // Cada tramo tiene dos selectores: el tipo (cuenta o caja) y la selección.
    const [, origen, , destino] = screen.getAllByRole("combobox");
    await userEvent.selectOptions(origen, "acc-1");
    await userEvent.selectOptions(destino, "acc-1");
    await userEvent.type(screen.getByLabelText("Monto"), "100.005");
    await userEvent.click(screen.getByRole("button", { name: "Transferir" }));

    await waitFor(() => expect(notify).toHaveBeenCalled());
    expect(apiFetch.mock.calls.some((c) => (c[1] as { method?: string } | undefined)?.method === "POST")).toBe(false);
  });

  it("el IGTF envía la base como texto y muestra el impuesto que el servidor calculó", async () => {
    apiFetch.mockImplementation((_ruta: string, opciones?: { method?: string }) => {
      if (opciones?.method === "POST") return Promise.resolve({ igft_amount: "37037.04" });
      return Promise.resolve({ items: [] });
    });
    pintar(<IgftPage />);
    await waitFor(() => expect(screen.getByLabelText("Monto base (sin IVA)")).toBeInTheDocument());

    await userEvent.type(screen.getByLabelText("Monto base (sin IVA)"), "1234568.00");
    await userEvent.click(screen.getByRole("button", { name: "Evaluar IGTF" }));

    await waitFor(() => expect(cuerpoEnviado().amount).toBe("1234568.00"));
    await waitFor(() =>
      expect(notify).toHaveBeenCalledWith(expect.objectContaining({
        description: expect.stringContaining("37.037,04"),
      })),
    );
  });
});
