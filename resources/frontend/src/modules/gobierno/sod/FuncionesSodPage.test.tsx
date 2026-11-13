import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.fn();
const notifyMock = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
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
  useNotifications: () => ({ notify: notifyMock }),
}));

const { FuncionesSodPage } = await import("./FuncionesSodPage");

const catalogo = {
  proceso: "PROC-03",
  funciones: [
    { codigo: "SOLICITANTE", etiqueta: "Solicitante (registra el expediente y el requiriente)", fuente: "Expediente y responsables REQUIRENTE (PROC-03)", disponible: true, requisito_habilitante: null },
    { codigo: "RECEPTOR", etiqueta: "Receptor de ofertas", fuente: "Recepción de ofertas (PROC-06)", disponible: true, requisito_habilitante: null },
    { codigo: "EVALUADOR", etiqueta: "Evaluador (comisión, apertura, aportes y recomendación)", fuente: "Comisión y evaluación", disponible: true, requisito_habilitante: null },
    { codigo: "ADJUDICADOR", etiqueta: "Adjudicador (decide el resultado)", fuente: "Decisiones del procedimiento", disponible: true, requisito_habilitante: null },
    { codigo: "PAGADOR", etiqueta: "Pagador", fuente: "No disponible en Gobierno", disponible: false, requisito_habilitante: "GOV-TRE-004 (TRE-04): el pago no existe en Gobierno" },
  ],
};

const regla = {
  id: "f1",
  codigo: "RF-0001",
  nombre: "Receptor no evalúa",
  proceso: "PROC-03",
  rol_a: "RECEPTOR",
  rol_a_etiqueta: "Receptor de ofertas",
  rol_b: "EVALUADOR",
  rol_b_etiqueta: "Evaluador (comisión, apertura, aportes y recomendación)",
  vigente_desde: "2026-11-12",
  vigente_hasta: null,
  estado: "VIGENTE",
  en_vigor: true,
  version: 2,
  descripcion: "Quien recibe las ofertas no puede evaluarlas.",
  fundamento: "N20 y N23.",
  historia: [],
};

const reglas = { items: [regla], total: 1, hoy: "2026-11-12" };

const conflicto = {
  regla_id: "f1",
  regla_codigo: "RF-0001",
  regla_nombre: "Receptor no evalúa",
  regla_version: 2,
  rol_a: "RECEPTOR",
  rol_a_etiqueta: "Receptor de ofertas",
  rol_b: "EVALUADOR",
  rol_b_etiqueta: "Evaluador (comisión, apertura, aportes y recomendación)",
  actor: "u1",
  actor_nombre: "ana",
  fecha: "2026-11-12",
  evidencia: [
    { rol: "RECEPTOR", rol_etiqueta: "Receptor de ofertas", registro: "Recepción de la oferta R-0001", registro_id: "o1", fecha: "2026-11-12", etiqueta: null },
    { rol: "EVALUADOR", rol_etiqueta: "Evaluador", registro: "Resultado de evaluación registrado", registro_id: "e1", fecha: "2026-11-12", etiqueta: null },
  ],
  expediente_id: "exp1",
  expediente_numero: "EX-0001",
  expediente_objeto: "Objeto",
};

const conflictos = { items: [conflicto], total: 1, desde: "2026-01-01", hasta: "2026-11-12" };

function responder(url: string) {
  if (url.startsWith("/gobierno/sod/funciones/conflictos")) return conflictos;
  if (url.startsWith("/gobierno/sod/funciones/reglas")) return reglas;
  return catalogo;
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/gobierno/sod/funciones"]}>
        <Routes>
          <Route path="/gobierno/sod/funciones" element={<FuncionesSodPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("FSP", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    notifyMock.mockReset();
    capacidades = new Set<string>();
    apiFetchMock.mockImplementation((url: string) => Promise.resolve(responder(url)));
  });

  it("FSP-01 · muestra la matriz, la incompatibilidad y los conflictos", async () => {
    capacidades.add("gobierno_sod:view");

    renderPage();

    expect(await screen.findByText("RF-0001 · Receptor no evalúa")).toBeInTheDocument();
    expect(screen.getAllByText(/Receptor de ofertas ≠ Evaluador/).length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "EX-0001" })).toHaveAttribute(
      "href",
      "/gobierno/contrataciones/expedientes/exp1",
    );
    expect(screen.getAllByText("Recepción de la oferta R-0001 (12/11/2026)").length).toBeGreaterThan(0);
  });

  it("FSP-02 · publica las funciones no disponibles con su requisito habilitante", async () => {
    capacidades.add("gobierno_sod:view");

    renderPage();

    expect(await screen.findByText(/Pagador/)).toBeInTheDocument();
    expect(screen.getByText(/GOV-TRE-004/)).toBeInTheDocument();
  });

  it("FSP-03 · sin manage no hay formulario; con manage aparece", async () => {
    capacidades.add("gobierno_sod:view");
    const { unmount } = renderPage();
    await screen.findByText("RF-0001 · Receptor no evalúa");
    expect(screen.queryByRole("heading", { name: "Declarar un par de funciones incompatibles" })).not.toBeInTheDocument();
    unmount();

    capacidades.add("gobierno_sod:manage");
    renderPage();
    expect(
      await screen.findByRole("heading", { name: "Declarar un par de funciones incompatibles" }),
    ).toBeInTheDocument();
  });

  it("FSP-04 · sin view muestra «Sin acceso» y no consulta", async () => {
    capacidades.clear();
    renderPage();
    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("FSP-05 · cerrar una regla vigente exige motivo y envía If-Match", async () => {
    capacidades.add("gobierno_sod:view");
    capacidades.add("gobierno_sod:activate");
    const user = userEvent.setup();
    renderPage();

    const cerrar = await screen.findByRole("button", { name: "Cerrar regla" });
    await user.click(cerrar);
    const motivo = screen.getByLabelText("Motivo del cierre");
    await user.type(motivo, "La matriz institucional cambió de criterio.");
    apiFetchMock.mockResolvedValueOnce({ ...regla, estado: "CERRADA", en_vigor: false, version: 3 });
    await user.click(screen.getByRole("button", { name: "Confirmar cierre" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/sod/funciones/reglas/f1/cerrar",
        expect.objectContaining({
          method: "POST",
          body: { motivo: "La matriz institucional cambió de criterio." },
          ifMatch: "2",
        }),
      );
    });
  });

  it("FSP-06 · la exportación pide el CSV del período consultado", async () => {
    capacidades.add("gobierno_sod:view");
    const user = userEvent.setup();
    renderPage();

    const desde = await screen.findByLabelText("Desde");
    await user.type(desde, "2026-11-01");
    apiFetchMock.mockResolvedValueOnce({ blob: new Blob(["a"]), contentDisposition: 'attachment; filename="x.csv"' });
    await user.click(screen.getByRole("button", { name: "Exportar CSV" }));

    await waitFor(() => {
      const llamadas = apiFetchMock.mock.calls.map((c) => c[0] as string);
      expect(llamadas.some((url) => url.includes("/gobierno/sod/funciones/conflictos.csv?desde=2026-11-01"))).toBe(true);
    });
  });
});
