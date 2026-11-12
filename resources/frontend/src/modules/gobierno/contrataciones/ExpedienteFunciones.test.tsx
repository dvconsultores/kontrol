import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.fn();

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

const { SeccionFuncionesIncompatibles } = await import("./ExpedienteFunciones");

const detalle = { id: "exp1", numero: "EX-0001" } as never;

const conflicto = {
  regla_id: "f1",
  regla_codigo: "RF-0001",
  regla_nombre: "Receptor no evalúa",
  regla_version: 1,
  rol_a: "RECEPTOR",
  rol_a_etiqueta: "Receptor de ofertas",
  rol_b: "EVALUADOR",
  rol_b_etiqueta: "Evaluador",
  actor: "u1",
  actor_nombre: "ana",
  fecha: "2026-11-12",
  evidencia: [
    { rol: "RECEPTOR", rol_etiqueta: "Receptor de ofertas", registro: "Recepción de la oferta R-0001", registro_id: "o1", fecha: "2026-11-12", etiqueta: null },
  ],
  expediente_id: "exp1",
  expediente_numero: "EX-0001",
  expediente_objeto: "Objeto",
};

function renderSeccion() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <SeccionFuncionesIncompatibles detalle={detalle} activeCompanyId="c1" />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("SeccionFuncionesIncompatibles", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    capacidades = new Set<string>(["gobierno_expedientes:view", "gobierno_sod:view"]);
  });

  it("muestra los conflictos del expediente con su evidencia", async () => {
    apiFetchMock.mockResolvedValue([conflicto]);
    renderSeccion();
    expect(await screen.findByText("RF-0001")).toBeInTheDocument();
    expect(screen.getByText("ana")).toBeInTheDocument();
    expect(screen.getByText("Recepción de la oferta R-0001 (12/11/2026)")).toBeInTheDocument();
    expect(apiFetchMock).toHaveBeenCalledWith("/gobierno/sod/funciones/expedientes/exp1");
  });

  it("sin conflictos lo dice y enlaza la matriz", async () => {
    apiFetchMock.mockResolvedValue([]);
    renderSeccion();
    expect(await screen.findByText(/Sin conflictos/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ver la matriz institucional" })).toHaveAttribute(
      "href",
      "/gobierno/sod/funciones",
    );
  });

  it("sin gobierno_sod:view no consulta y lo explica", async () => {
    capacidades = new Set<string>(["gobierno_expedientes:view"]);
    renderSeccion();
    expect(await screen.findByText(/No tiene permiso para consultar la matriz/)).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });
});
