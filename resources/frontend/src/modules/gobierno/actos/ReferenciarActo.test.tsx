import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Acto, ActoResumen, ListaActos } from "@/modules/gobierno/api";

const apiFetch = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

vi.mock("@/lib/fecha-de-negocio", async (original) => ({
  ...(await original<typeof import("@/lib/fecha-de-negocio")>()),
  hoyDeNegocio: () => "2026-10-30",
}));

const { ReferenciarActo } = await import("./ReferenciarActo");

const ACTO: Acto = {
  id: "acto-1",
  tipo: "RESOLUCION",
  denominacion_tipo: null,
  numero: "DA-020-2026",
  fecha: "2026-06-01",
  lugar: "Caracas",
  cargo: {
    id: "cargo-1",
    codigo: "DIR-TES",
    denominacion: "Director de Tesorería",
    unidad_codigo: "U1",
    unidad_denominacion: "Unidad 1",
  },
  competencia: {
    accion: "APROBAR",
    materia: "CONTRATACIONES",
  },
  fundamento_competencia: "Reglamento interno, art. 12",
  funcionario: "Ana Pérez",
  titularidad: "TITULAR",
  delegacion_numero: null,
  delegacion_fecha: null,
  caracter: "PARTICULAR",
  simple_tramite: false,
  destinatario: "Pedro Gil",
  asunto: "Designación del tesorero",
  hechos: "Hechos del caso",
  fundamentos: "Ordenanza, art. 3",
  decision: "Se designa",
  estado: "EFICAZ",
  faltantes_para_emitir: [],
  documento_acto_id: null,
  medio: "PERSONAL",
  referencia_publicacion: null,
  fecha_publicacion_notificacion: null,
  documento_eficacia_id: null,
  fecha_eficacia: null,
  revocado_por: null,
  anulado_por: null,
  revoca_a: [],
  anula_a: [],
  version: 1,
  emitido_en: null,
  emitido_por: null,
  creado_en: "2026-06-01T12:00:00Z",
};

const ACTO_R1: ActoResumen = {
  id: "r1",
  tipo: "RESOLUCION",
  denominacion_tipo: null,
  numero: "DA-030-2026",
  fecha: "2026-07-01",
  cargo_codigo: "DIR-TES",
  cargo_denominacion: "Director de Tesorería",
  unidad_codigo: "U1",
  caracter: "GENERAL",
  asunto: "Revocatoria",
  estado: "EFICAZ",
  fecha_eficacia: null,
};

const ACTO_R2: ActoResumen = {
  id: "r2",
  tipo: "DECRETO",
  denominacion_tipo: null,
  numero: "D-031-2026",
  fecha: "2026-07-02",
  cargo_codigo: "DIR-ADM",
  cargo_denominacion: "Director de Administración",
  unidad_codigo: "U2",
  caracter: "GENERAL",
  asunto: "Revisión de oficio",
  estado: "EMITIDO",
  fecha_eficacia: null,
};

const ACTO_R3: ActoResumen = {
  id: "r3",
  tipo: "RESOLUCION",
  denominacion_tipo: null,
  numero: "DA-032-2026",
  fecha: "2026-07-03",
  cargo_codigo: "DIR-TES",
  cargo_denominacion: "Director de Tesorería",
  unidad_codigo: "U1",
  caracter: "GENERAL",
  asunto: "Borrador reciente",
  estado: "BORRADOR",
  fecha_eficacia: null,
};

const ACTO_R4: ActoResumen = {
  id: "r4",
  tipo: "RESOLUCION",
  denominacion_tipo: null,
  numero: "DA-005-2026",
  fecha: "2026-01-10",
  cargo_codigo: "DIR-TES",
  cargo_denominacion: "Director de Tesorería",
  unidad_codigo: "U1",
  caracter: "GENERAL",
  asunto: "Acto anterior",
  estado: "EFICAZ",
  fecha_eficacia: null,
};

const ACTO_PROPIO: ActoResumen = {
  id: "acto-1",
  tipo: "RESOLUCION",
  denominacion_tipo: null,
  numero: "DA-020-2026",
  fecha: "2026-06-01",
  cargo_codigo: "DIR-TES",
  cargo_denominacion: "Director de Tesorería",
  unidad_codigo: "U1",
  caracter: "PARTICULAR",
  asunto: "Designación del tesorero",
  estado: "EFICAZ",
  fecha_eficacia: null,
};

function montarReferenciar(
  props: Partial<Parameters<typeof ReferenciarActo>[0]> = {},
) {
  const onConfirmar = vi.fn().mockResolvedValue(undefined);
  const onCancelar = vi.fn();
  const defaults = {
    acto: ACTO,
    modo: "revocar" as const,
    onConfirmar,
    onCancelar,
    erroresServidor: {},
  };
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <ReferenciarActo {...defaults} {...props} />
    </QueryClientProvider>,
  );
  return { onConfirmar, onCancelar };
}

describe("ReferenciarActo", () => {
  beforeEach(() => {
    apiFetch.mockReset();
  });

  it("REF-01 · modo revocar muestra título, cita LOPA art. 82 y pide 2026", async () => {
    apiFetch.mockResolvedValue({
      anio: 2026,
      items: [],
      total: 0,
    } satisfies ListaActos);
    montarReferenciar();
    expect(
      screen.getByRole("heading", {
        name: "Registrar la revocación de Resolución Nº DA-020-2026",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/LOPA art\. 82/),
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith("/gobierno/actos?anio=2026");
    });
  });

  it("REF-02 · ofrece solo r1 y r2 con texto formateado", async () => {
    apiFetch.mockResolvedValue({
      anio: 2026,
      items: [ACTO_R1, ACTO_R2, ACTO_R3, ACTO_R4, ACTO_PROPIO],
      total: 5,
    } satisfies ListaActos);
    montarReferenciar();
    await screen.findByRole("option", {
      name: "Resolución Nº DA-030-2026 — 01/07/2026 — Revocatoria",
    });
    const select = screen.getByLabelText(/^Acto de referencia/);
    expect(select).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /DA-030-2026/ })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /D-031-2026/ })).toBeInTheDocument();
    expect(
      screen.getByRole("option", {
        name: "Resolución Nº DA-030-2026 — 01/07/2026 — Revocatoria",
      }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /DA-032-2026/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /DA-005-2026/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /DA-020-2026/ })).not.toBeInTheDocument();
  });

  it("REF-03 · elegir r1 y motivo → onConfirmar exacto", async () => {
    apiFetch.mockResolvedValue({
      anio: 2026,
      items: [ACTO_R1, ACTO_R2],
      total: 2,
    } satisfies ListaActos);
    const { onConfirmar } = montarReferenciar();
    await screen.findByRole("option", {
      name: "Resolución Nº DA-030-2026 — 01/07/2026 — Revocatoria",
    });
    await userEvent.selectOptions(
      screen.getByLabelText(/^Acto de referencia/),
      "r1",
    );
    await userEvent.type(
      screen.getByLabelText(/^Motivo/),
      "Revocado por cambio de titular",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Registrar revocación" }),
    );
    expect(onConfirmar).toHaveBeenCalledWith({
      acto_id_referencia: "r1",
      motivo: "Revocado por cambio de titular",
    });
  });

  it("REF-04 · lista sin candidatos muestra aviso y botón deshabilitado", async () => {
    apiFetch.mockResolvedValue({
      anio: 2026,
      items: [ACTO_R3, ACTO_R4, ACTO_PROPIO],
      total: 3,
    } satisfies ListaActos);
    montarReferenciar();
    expect(
      await screen.findByText(
        "No hay actos emitidos que puedan servir de referencia en ese año.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Registrar revocación" }),
    ).toBeDisabled();
  });

  it("REF-05 · modo anular: título, LOPA 83, botón y cambio de año a 2025", async () => {
    apiFetch.mockResolvedValue({
      anio: 2025,
      items: [],
      total: 0,
    } satisfies ListaActos);
    montarReferenciar({ modo: "anular" });
    expect(
      screen.getByRole("heading", {
        name: "Registrar la nulidad de Resolución Nº DA-020-2026",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText(/LOPA art\. 83/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Registrar nulidad" }),
    ).toBeInTheDocument();
    await userEvent.selectOptions(
      screen.getByLabelText(/^Año del acto que declara la nulidad/),
      "2025",
    );
    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith("/gobierno/actos?anio=2025");
    });
  });

  it("REF-06 · motivo de 3 caracteres → error y no se llama onConfirmar", async () => {
    apiFetch.mockResolvedValue({
      anio: 2026,
      items: [ACTO_R1, ACTO_R2],
      total: 2,
    } satisfies ListaActos);
    const { onConfirmar } = montarReferenciar();
    await screen.findByRole("option", {
      name: "Resolución Nº DA-030-2026 — 01/07/2026 — Revocatoria",
    });
    await userEvent.selectOptions(
      screen.getByLabelText(/^Acto de referencia/),
      "r1",
    );
    await userEvent.type(screen.getByLabelText(/^Motivo/), "abc");
    await userEvent.click(
      screen.getByRole("button", { name: "Registrar revocación" }),
    );
    expect(
      screen.getByText("Indique el motivo (de 5 a 255 caracteres)"),
    ).toBeInTheDocument();
    expect(onConfirmar).not.toHaveBeenCalled();
  });
});
