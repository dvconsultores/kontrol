import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router";

import { ApiError } from "@/api/client";

import { AlertasPoliticaPage } from "./AlertasPoliticaPage";

const apiFetchMock = vi.fn();
const notify = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  ApiError: (await original<typeof import("@/api/client")>()).ApiError,
}));

let capacidades = new Set<string>();

vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({
    estado: "LISTA",
    tiene: (c: string) => capacidades.has(c),
    puede: () => true,
    motivo: () => null,
    motivoDeCapacidad: () => null,
  }),
}));

vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({ activeCompanyId: "c1", activeCompany: { id: "c1", legal_name: "Ente 1" } }),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify }),
}));

const fixturePoliticas = {
  items: [
    { fuente: "CONTRATO", activo: false, dias_anticipacion: null },
    { fuente: "HITO", activo: true, dias_anticipacion: 7 },
    { fuente: "ENTREGABLE", activo: false, dias_anticipacion: null },
  ],
  garantias_dias_por_vencer: 15,
  fases_por_defecto: ["EJECUCION"],
};

function renderComponente(): void {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter>
        <AlertasPoliticaPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiFetchMock.mockReset();
  notify.mockReset();
  capacidades = new Set(["gobierno_contratos:view", "notificaciones:configure", "alertas:view"]);
  apiFetchMock.mockImplementation(async (ruta: string, opciones?: { method?: string; body?: { items: unknown[] } }) => {
    if (ruta === "/gobierno/contratos-alertas/politicas") {
      if (opciones?.method === "PUT") {
        return { ...fixturePoliticas, items: opciones.body?.items };
      }
      return fixturePoliticas;
    }
    throw new Error(`Ruta no mockeada: ${ruta}`);
  });
});

describe("AlertasPoliticaPage", () => {
  it("muestra las reglas fijas y el borrador cargado", async () => {
    renderComponente();

    await waitFor(() => expect(screen.getByText(/por vencer desde 15 días/)).toBeTruthy());
    expect(screen.getByText(/alerta el día del vencimiento/)).toBeTruthy();
    expect(screen.getByText(/no hay calendario hábil institucional/)).toBeTruthy();

    const hitoActivo = screen.getByLabelText("Activar preaviso", { selector: "#politica-HITO-activo" }) as HTMLInputElement;
    expect(hitoActivo.checked).toBe(true);
    const hitoDias = screen.getByLabelText("Días de anticipación", { selector: "#politica-HITO-dias" }) as HTMLInputElement;
    expect(hitoDias.value).toBe("7");
  });

  it("guarda el preaviso y notifica", async () => {
    const usuario = userEvent.setup();
    renderComponente();

    await waitFor(() => expect(screen.getByText(/por vencer desde 15 días/)).toBeTruthy());

    await usuario.click(screen.getByLabelText("Activar preaviso", { selector: "#politica-CONTRATO-activo" }));
    const diasContrato = screen.getByLabelText("Días de anticipación", { selector: "#politica-CONTRATO-dias" });
    await usuario.clear(diasContrato);
    await usuario.type(diasContrato, "30");

    await usuario.click(screen.getByRole("button", { name: "Guardar preaviso" }));

    await waitFor(() =>
      expect(apiFetchMock).toHaveBeenCalledWith("/gobierno/contratos-alertas/politicas", {
        method: "PUT",
        body: {
          items: [
            { fuente: "CONTRATO", activo: true, dias_anticipacion: 30 },
            { fuente: "HITO", activo: true, dias_anticipacion: 7 },
            { fuente: "ENTREGABLE", activo: false, dias_anticipacion: null },
          ],
        },
      }),
    );
    await waitFor(() => expect(notify).toHaveBeenCalledWith(expect.objectContaining({ title: "Preaviso guardado" })));
  });

  it("muestra controles deshabilitados y oculta el botón sin notificaciones:configure", async () => {
    capacidades = new Set(["gobierno_contratos:view", "alertas:view"]);
    renderComponente();

    await waitFor(() => expect(screen.getByText(/por vencer desde 15 días/)).toBeTruthy());
    expect((screen.getByLabelText("Activar preaviso", { selector: "#politica-CONTRATO-activo" }) as HTMLInputElement).disabled).toBe(true);
    expect((screen.getByLabelText("Días de anticipación", { selector: "#politica-CONTRATO-dias" }) as HTMLInputElement).disabled).toBe(true);
    expect(screen.queryByRole("button", { name: "Guardar preaviso" })).toBeNull();
    expect(screen.getByText("Solo quien puede configurar notificaciones modifica el preaviso.")).toBeTruthy();
  });

  it("muestra el mensaje de error devuelto por el backend", async () => {
    const usuario = userEvent.setup();
    apiFetchMock.mockImplementation(async (ruta: string, opciones?: { method?: string; body?: { items: unknown[] } }) => {
      if (ruta === "/gobierno/contratos-alertas/politicas" && opciones?.method === "PUT") {
        throw new ApiError(422, { code: "GOV_CONTRACT_ALERT_POLICY_INVALID", message: "Indique los días de anticipación" });
      }
      return fixturePoliticas;
    });
    renderComponente();

    await waitFor(() => expect(screen.getByText(/por vencer desde 15 días/)).toBeTruthy());
    await usuario.click(screen.getByRole("button", { name: "Guardar preaviso" }));

    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("Indique los días de anticipación"));
  });

  it("no consulta las políticas sin gobierno_contratos:view", async () => {
    capacidades = new Set<string>();
    apiFetchMock.mockImplementation(async () => {
      throw new Error("No debería llamarse");
    });

    renderComponente();

    expect(screen.getByRole("heading", { level: 1, name: "Acceso prohibido" })).toBeTruthy();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });
});
