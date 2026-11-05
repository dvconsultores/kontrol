import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";

const apiFetchMock = vi.fn();
const notifyMock = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

vi.mock("@/modules/gobierno/tesoreria/AutorizadosCuenta", () => ({
  AutorizadosCuenta: () => <div>autorizados</div>,
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
  useCompany: () => ({ activeCompanyId: "c1", activeCompany: { id: "c1", legal_name: "Contenedor 1" } }),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: notifyMock }),
}));

import { CuentaPage } from "./CuentaPage";

const detalle = {
  id: "c1",
  codigo: "CB-2026-0001",
  denominacion: "Fondos de funcionamiento",
  banco_id: "b1",
  banco_codigo: "0102",
  banco_nombre: "Banco Uno",
  tipo: "CORRIENTE",
  moneda: "VES",
  numero_enmascarado: "••••0001",
  vigente_desde: "2026-11-01",
  vigente_hasta: null,
  estado: "BORRADOR",
  en_vigor: false,
  acto_sin_efecto: false,
  autorizados_en_vigor: 0,
  version: 3,
  acto: null,
  registrada_por: "ua",
  registrada_en: "2026-11-01T12:00:00Z",
  activada_por: null,
  activada_en: null,
  cerrada_por: null,
  cerrada_en: null,
  fecha_cierre: null,
  motivo_cierre: null,
  autorizados: [],
  historia: [{ tipo: "CREADA", detalle: null, registrado_por: "ua", registrado_en: "2026-11-01T12:00:00Z" }],
};

const acto = { id: "a1", tipo: "RESOLUCION", numero: "R-1", fecha: "2026-11-01", estado: "EMITIDO", asunto: "Apertura" };

const opciones = {
  bancos: [{ id: "b1", codigo: "0102", nombre: "Banco Uno" }],
  cargos: [{ id: "g1", codigo: "DIR", denominacion: "Director", unidad: "Dirección" }],
  actos: [acto],
};

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/gobierno/tesoreria/cuentas/c1"]}>
        <Routes>
          <Route path="/gobierno/tesoreria/cuentas/:cuentaId" element={<CuentaPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("CuentaPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    notifyMock.mockReset();
    capacidades = new Set<string>();
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/tesoreria/cuentas/c1") {
        return Promise.resolve(detalle);
      }
      if (url === "/gobierno/tesoreria/opciones") {
        return Promise.resolve(opciones);
      }
      return Promise.reject(new Error(`URL inesperada: ${url}`));
    });
  });

  it("CF-01: sin view muestra Sin acceso", async () => {
    renderPage();
    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
    expect(screen.queryByText("Cuenta CB-2026-0001")).not.toBeInTheDocument();
  });

  it("CF-02: con view solo muestra datos y oculta acciones de gestión", async () => {
    capacidades.add("gobierno_cuentas:view");
    renderPage();
    expect(await screen.findByRole("heading", { name: "Cuenta CB-2026-0001" })).toBeInTheDocument();
    expect(screen.getByText("••••0001")).toBeInTheDocument();
    expect(screen.queryByText("Ver número completo")).not.toBeInTheDocument();
    expect(screen.queryByText("Activar cuenta")).not.toBeInTheDocument();
    expect(screen.queryByText("Editar borrador")).not.toBeInTheDocument();
    expect(screen.queryByText("Vincular acto")).not.toBeInTheDocument();
  });

  it("CF-03: 404 muestra Cuenta no encontrada", async () => {
    capacidades.add("gobierno_cuentas:view");
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/tesoreria/cuentas/c1") {
        return Promise.reject(new ApiError(404, { code: "GOV_BANK_ACCOUNT_NOT_FOUND", message: "No encontrada" }));
      }
      return Promise.reject(new Error(`URL inesperada: ${url}`));
    });
    renderPage();
    expect(await screen.findByText("Cuenta no encontrada")).toBeInTheDocument();
  });

  it("CF-04: con manage, Ver número completo muestra el número y Ocultar número lo retira", async () => {
    capacidades.add("gobierno_cuentas:view");
    capacidades.add("gobierno_cuentas:manage");
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/tesoreria/cuentas/c1") return Promise.resolve(detalle);
      if (url === "/gobierno/tesoreria/opciones") return Promise.resolve(opciones);
      if (url === "/gobierno/tesoreria/cuentas/c1/numero") return Promise.resolve({ numero: "01020000000000000001" });
      return Promise.reject(new Error(`URL inesperada: ${url}`));
    });
    renderPage();
    const boton = await screen.findByText("Ver número completo");
    await userEvent.click(boton);
    expect(await screen.findByText("01020000000000000001")).toBeInTheDocument();
    expect(apiFetchMock).toHaveBeenCalledWith("/gobierno/tesoreria/cuentas/c1/numero");
    await userEvent.click(screen.getByText("Ocultar número"));
    expect(screen.queryByText("01020000000000000001")).not.toBeInTheDocument();
  });

  it("CF-05: Vincular acto deshabilitado sin selección y POST con acto elegido", async () => {
    capacidades.add("gobierno_cuentas:view");
    capacidades.add("gobierno_cuentas:manage");
    renderPage();
    const botonVincular = await screen.findByRole("button", { name: "Vincular acto" });
    expect(botonVincular).toBeDisabled();
    const select = screen.getByLabelText(/Acto vigente/);
    await userEvent.selectOptions(select, "a1");
    await userEvent.click(botonVincular);
    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith("/gobierno/tesoreria/cuentas/c1/acto", {
        method: "POST",
        body: { acto_id: "a1" },
        ifMatch: "3",
      });
    });
  });

  it("CF-06: Activar cuenta con activate hace POST a /activar", async () => {
    capacidades.add("gobierno_cuentas:view");
    capacidades.add("gobierno_cuentas:activate");
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/tesoreria/cuentas/c1") return Promise.resolve(detalle);
      if (url === "/gobierno/tesoreria/cuentas/c1/activar") return Promise.resolve({ ...detalle, estado: "VIGENTE", en_vigor: true });
      return Promise.reject(new Error(`URL inesperada: ${url}`));
    });
    renderPage();
    const botonActivar = await screen.findByRole("button", { name: "Activar cuenta" });
    await userEvent.click(botonActivar);
    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith("/gobierno/tesoreria/cuentas/c1/activar", {
        method: "POST",
        body: {},
        ifMatch: "3",
      });
    });
  });

  it("CF-07: 409 NOT_READY muestra alerta con faltantes", async () => {
    capacidades.add("gobierno_cuentas:view");
    capacidades.add("gobierno_cuentas:manage");
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/tesoreria/cuentas/c1") return Promise.resolve(detalle);
      if (url === "/gobierno/tesoreria/opciones") return Promise.resolve(opciones);
      if (url === "/gobierno/tesoreria/cuentas/c1/acto") {
        return Promise.reject(
          new ApiError(409, {
            code: "GOV_BANK_ACCOUNT_NOT_READY",
            message: "No está lista",
            details: { faltan: ["acto", "autorizado"] },
          }),
        );
      }
      return Promise.reject(new Error(`URL inesperada: ${url}`));
    });
    renderPage();
    const botonVincular = await screen.findByRole("button", { name: "Vincular acto" });
    const select = screen.getByLabelText(/Acto vigente/);
    await userEvent.selectOptions(select, "a1");
    await userEvent.click(botonVincular);
    expect(
      await screen.findByText(
        "Para continuar la cuenta necesita: un acto habilitante vigente, al menos un cargo autorizado en vigor.",
      ),
    ).toBeInTheDocument();
  });

  it("CF-08: 409 STALE muestra alerta de recarga y vuelve a pedir detalle", async () => {
    capacidades.add("gobierno_cuentas:view");
    capacidades.add("gobierno_cuentas:manage");
    let detalleLlamadas = 0;
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/tesoreria/cuentas/c1") {
        detalleLlamadas += 1;
        return Promise.resolve(detalle);
      }
      if (url === "/gobierno/tesoreria/opciones") return Promise.resolve(opciones);
      if (url === "/gobierno/tesoreria/cuentas/c1/acto") {
        return Promise.reject(
          new ApiError(409, {
            code: "GOV_BANK_ACCOUNT_STALE",
            message: "Versión antigua",
          }),
        );
      }
      return Promise.reject(new Error(`URL inesperada: ${url}`));
    });
    renderPage();
    const botonVincular = await screen.findByRole("button", { name: "Vincular acto" });
    const select = screen.getByLabelText(/Acto vigente/);
    await userEvent.selectOptions(select, "a1");
    await userEvent.click(botonVincular);
    expect(
      await screen.findByText(
        "La cuenta cambió desde que la abrió. Se recargaron los datos; revise y vuelva a intentarlo.",
      ),
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(detalleLlamadas).toBeGreaterThanOrEqual(2);
    });
  });

  it("CF-09: 409 SOD_CONFLICT muestra alerta de segregación", async () => {
    capacidades.add("gobierno_cuentas:view");
    capacidades.add("gobierno_cuentas:activate");
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/tesoreria/cuentas/c1") return Promise.resolve(detalle);
      if (url === "/gobierno/tesoreria/cuentas/c1/activar") {
        return Promise.reject(
          new ApiError(409, {
            code: "GOV_SOD_CONFLICT",
            message: "Conflicto de segregación",
            details: {
              conflicto_id: "s1",
              accion_a: "accionA",
              accion_b: "accionB",
              accion_a_etiqueta: "Acción A",
              accion_b_etiqueta: "Acción B",
              mismo_objeto: true,
              autor: "usuarioA",
            },
          }),
        );
      }
      return Promise.reject(new Error(`URL inesperada: ${url}`));
    });
    renderPage();
    const botonActivar = await screen.findByRole("button", { name: "Activar cuenta" });
    await userEvent.click(botonActivar);
    expect(await screen.findByText("Operación bloqueada por segregación de funciones")).toBeInTheDocument();
  });

  it("CF-10: acto_sin_efecto muestra aviso de acto revocado o anulado", async () => {
    capacidades.add("gobierno_cuentas:view");
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/tesoreria/cuentas/c1") {
        return Promise.resolve({ ...detalle, acto_sin_efecto: true, acto });
      }
      return Promise.reject(new Error(`URL inesperada: ${url}`));
    });
    renderPage();
    expect(await screen.findByText(/El acto habilitante fue revocado o anulado/)).toBeInTheDocument();
  });

  it("CF-11: VIGENTE con 0 autorizados muestra aviso", async () => {
    capacidades.add("gobierno_cuentas:view");
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/tesoreria/cuentas/c1") {
        return Promise.resolve({ ...detalle, estado: "VIGENTE", en_vigor: true, autorizados_en_vigor: 0 });
      }
      return Promise.reject(new Error(`URL inesperada: ${url}`));
    });
    renderPage();
    expect(
      await screen.findByText("Esta cuenta vigente no tiene cargos autorizados en vigor."),
    ).toBeInTheDocument();
  });

  it("CF-12: Inactivar con motivo corto valida y con motivo válido hace POST", async () => {
    capacidades.add("gobierno_cuentas:view");
    capacidades.add("gobierno_cuentas:activate");
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/tesoreria/cuentas/c1") {
        return Promise.resolve({ ...detalle, estado: "VIGENTE", en_vigor: true });
      }
      if (url === "/gobierno/tesoreria/cuentas/c1/inactivar") {
        return Promise.resolve({ ...detalle, estado: "INACTIVA", en_vigor: false });
      }
      return Promise.reject(new Error(`URL inesperada: ${url}`));
    });
    renderPage();
    const botonInactivar = await screen.findByRole("button", { name: "Inactivar cuenta" });
    await userEvent.click(botonInactivar);
    const textarea = screen.getByLabelText(/^Motivo/);
    await userEvent.type(textarea, "corto");
    expect(screen.getByText("El motivo debe tener entre 10 y 500 caracteres.")).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalledWith(
      "/gobierno/tesoreria/cuentas/c1/inactivar",
      expect.anything(),
    );
    await userEvent.clear(textarea);
    await userEvent.type(textarea, "Motivo de prueba válido");
    await userEvent.click(screen.getByRole("button", { name: "Confirmar inactivación" }));
    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith("/gobierno/tesoreria/cuentas/c1/inactivar", {
        method: "POST",
        body: { motivo: "Motivo de prueba válido" },
        ifMatch: "3",
      });
    });
  });

  it("CF-13: Cerrar cuenta envía motivo y fecha_cierre", async () => {
    capacidades.add("gobierno_cuentas:view");
    capacidades.add("gobierno_cuentas:activate");
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/tesoreria/cuentas/c1") {
        return Promise.resolve({ ...detalle, estado: "VIGENTE", en_vigor: true });
      }
      if (url === "/gobierno/tesoreria/cuentas/c1/cerrar") {
        return Promise.resolve({ ...detalle, estado: "CERRADA", en_vigor: false });
      }
      return Promise.reject(new Error(`URL inesperada: ${url}`));
    });
    renderPage();
    const botonCerrar = await screen.findByRole("button", { name: "Cerrar cuenta" });
    await userEvent.click(botonCerrar);
    const textarea = screen.getByLabelText(/^Motivo/);
    await userEvent.type(textarea, "Motivo de cierre válido");
    const fechaInput = screen.getByLabelText(/Fecha de cierre/);
    await userEvent.clear(fechaInput);
    await userEvent.type(fechaInput, "2026-11-15");
    await userEvent.click(screen.getByRole("button", { name: "Confirmar cierre" }));
    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith("/gobierno/tesoreria/cuentas/c1/cerrar", {
        method: "POST",
        body: { motivo: "Motivo de cierre válido", fecha_cierre: "2026-11-15" },
        ifMatch: "3",
      });
    });
  });

  it("CF-14: CERRADA muestra mensaje y ninguna acción", async () => {
    capacidades.add("gobierno_cuentas:view");
    capacidades.add("gobierno_cuentas:manage");
    capacidades.add("gobierno_cuentas:activate");
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/tesoreria/cuentas/c1") {
        return Promise.resolve({
          ...detalle,
          estado: "CERRADA",
          en_vigor: false,
          fecha_cierre: "2026-11-15",
          cerrada_por: "ua",
          motivo_cierre: "Motivo de cierre válido",
        });
      }
      return Promise.reject(new Error(`URL inesperada: ${url}`));
    });
    renderPage();
    expect(await screen.findByText("Una cuenta cerrada no se reabre.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Editar borrador" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Activar cuenta" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Inactivar cuenta" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reactivar cuenta" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cerrar cuenta" })).not.toBeInTheDocument();
  });

  it("CF-15: edición con número de 19 dígitos valida y PATCH sin numero al dejarlo vacío", async () => {
    capacidades.add("gobierno_cuentas:view");
    capacidades.add("gobierno_cuentas:manage");
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/tesoreria/cuentas/c1") return Promise.resolve(detalle);
      if (url === "/gobierno/tesoreria/opciones") return Promise.resolve(opciones);
      return Promise.reject(new Error(`URL inesperada: ${url}`));
    });
    renderPage();
    const botonEditar = await screen.findByRole("button", { name: "Editar borrador" });
    await userEvent.click(botonEditar);
    const numeroInput = screen.getByLabelText(/Número de cuenta/);
    await userEvent.type(numeroInput, "0102000000000000001");
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(screen.getByText("El número debe tener 20 dígitos.")).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalledWith(
      "/gobierno/tesoreria/cuentas/c1",
      expect.objectContaining({ method: "PATCH" }),
    );
    await userEvent.clear(numeroInput);
    const denominacion = screen.getByLabelText(/^Denominación/);
    await userEvent.clear(denominacion);
    await userEvent.type(denominacion, "Fondos de terceros");
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() => {
      const llamada = apiFetchMock.mock.calls.find(
        (call) => call[0] === "/gobierno/tesoreria/cuentas/c1" && (call[1] as { method?: string })?.method === "PATCH",
      );
      expect(llamada).toBeDefined();
      expect((llamada?.[1] as { body?: Record<string, unknown> }).body).not.toHaveProperty("numero");
    });
  });

  it("CF-16: historia con INACTIVADA y motivo muestra etiqueta y motivo", async () => {
    capacidades.add("gobierno_cuentas:view");
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/tesoreria/cuentas/c1") {
        return Promise.resolve({
          ...detalle,
          historia: [
            {
              tipo: "INACTIVADA",
              detalle: { motivo: "Motivo de prueba" },
              registrado_por: "ua",
              registrado_en: "2026-11-05T12:00:00Z",
            },
          ],
        });
      }
      return Promise.reject(new Error(`URL inesperada: ${url}`));
    });
    renderPage();
    expect(await screen.findByText("Inactivada")).toBeInTheDocument();
    expect(screen.getByText("Motivo de prueba")).toBeInTheDocument();
  });
});
