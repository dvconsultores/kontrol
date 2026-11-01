import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Acto } from "@/modules/gobierno/api";
import { DocumentSummary } from "@/modules/documentos/types";
import { EmitirActo } from "./EmitirActo";

const apiFetch = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

vi.mock("@/lib/fecha-de-negocio", async (original) => ({
  ...(await original<typeof import("@/lib/fecha-de-negocio")>()),
  hoyDeNegocio: () => "2026-10-30",
}));

const ACTO_BASE: Acto = {
  id: "acto-1",
  tipo: "RESOLUCION",
  denominacion_tipo: null,
  numero: "DA-010-2026",
  fecha: "2026-09-15",
  lugar: "Sede",
  cargo: {
    id: "cargo-1",
    codigo: "DIR-TES",
    denominacion: "Dirección de Tesorería",
    unidad_codigo: "TES",
    unidad_denominacion: "Tesorería",
  },
  competencia: {
    accion: "APROBAR",
    materia: "CONTRATACIONES",
  },
  fundamento_competencia: "Norma",
  funcionario: "A. Funcionario",
  titularidad: "TITULAR",
  delegacion_numero: null,
  delegacion_fecha: null,
  caracter: "INTERNO",
  simple_tramite: false,
  destinatario: null,
  asunto: "Asunto del acto",
  hechos: null,
  fundamentos: null,
  decision: null,
  estado: "BORRADOR",
  faltantes_para_emitir: [],
  documento_acto_id: null,
  medio: null,
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
  creado_en: "2026-09-15T00:00:00Z",
};

const DOCUMENTOS: DocumentSummary[] = [
  {
    id: "d1",
    company_id: "c1",
    document_type_id: "dt-1",
    title: "Resolución firmada",
    document_number: "R-10",
    issuer: null,
    issued_at: null,
    expiration_date: null,
    is_expired: false,
    status: "ACTIVE",
    is_managed: false,
    external_url: null,
    version: 1,
    current_version: null,
    can_delete: false,
    delete_blocked_by: null,
    allowed_actions: [],
    description: null,
    metadata: null,
    links: [],
    link: undefined,
  },
  {
    id: "d2",
    company_id: "c1",
    document_type_id: "dt-2",
    title: "Gaceta Nº 4.512",
    document_number: null,
    issuer: null,
    issued_at: null,
    expiration_date: null,
    is_expired: false,
    status: "ACTIVE",
    is_managed: false,
    external_url: null,
    version: 1,
    current_version: null,
    can_delete: false,
    delete_blocked_by: null,
    allowed_actions: [],
    description: null,
    metadata: null,
    links: [],
    link: undefined,
  },
  {
    id: "d3",
    company_id: "c1",
    document_type_id: "dt-3",
    title: "Borrador anulado",
    document_number: null,
    issuer: null,
    issued_at: null,
    expiration_date: null,
    is_expired: false,
    status: "ARCHIVED",
    is_managed: false,
    external_url: null,
    version: 1,
    current_version: null,
    can_delete: false,
    delete_blocked_by: null,
    allowed_actions: [],
    description: null,
    metadata: null,
    links: [],
    link: undefined,
  },
];

function montarEmitirActo(acto: Acto, props: Partial<Parameters<typeof EmitirActo>[0]> = {}) {
  const onConfirmar = vi.fn().mockResolvedValue(undefined);
  const onCancelar = vi.fn();
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  render(
    <QueryClientProvider client={client}>
      <EmitirActo
        acto={acto}
        onConfirmar={onConfirmar}
        onCancelar={onCancelar}
        erroresServidor={{}}
        {...props}
      />
    </QueryClientProvider>,
  );

  return { onConfirmar, onCancelar };
}

describe("EmitirActo", () => {
  beforeEach(() => {
    apiFetch.mockReset();
    apiFetch.mockResolvedValue(DOCUMENTOS);
  });

  it("EMI-01 · INTERNO: el campo «Fecha de eficacia» arranca en la fecha del acto; elegir d1 y pulsar «Emitir» llama onConfirmar exactamente", async () => {
    const { onConfirmar } = montarEmitirActo(ACTO_BASE);

    const fechaEficacia = await screen.findByLabelText(/^Fecha de eficacia/);
    expect(fechaEficacia).toHaveValue("2026-09-15");

    const selectDocumento = await screen.findByLabelText(/^PDF firmado del acto/);
    await screen.findByRole("option", { name: "Resolución firmada (R-10)" });
    await userEvent.selectOptions(selectDocumento, "d1");
    await userEvent.click(screen.getByRole("button", { name: "Emitir" }));

    expect(onConfirmar).toHaveBeenCalledWith({
      documento_acto_id: "d1",
      fecha_eficacia: "2026-09-15",
    });
  });

  it("EMI-02 · INTERNO con fecha de eficacia anterior a la fecha del acto muestra error y no llama onConfirmar", async () => {
    const { onConfirmar } = montarEmitirActo(ACTO_BASE);

    const selectDocumento = await screen.findByLabelText(/^PDF firmado del acto/);
    await screen.findByRole("option", { name: "Resolución firmada (R-10)" });
    await userEvent.selectOptions(selectDocumento, "d1");

    const fechaEficacia = screen.getByLabelText(/^Fecha de eficacia/);
    fireEvent.change(fechaEficacia, { target: { value: "2026-09-01" } });

    await userEvent.click(screen.getByRole("button", { name: "Emitir" }));

    await screen.findByText(
      "La eficacia no puede ser anterior a la fecha del acto",
    );
    expect(onConfirmar).not.toHaveBeenCalled();
  });

  it("EMI-03 · PARTICULAR: no hay «Fecha de eficacia»; muestra texto de notificación; onConfirmar recibe fecha_eficacia null", async () => {
    const acto = { ...ACTO_BASE, caracter: "PARTICULAR" as const };
    const { onConfirmar } = montarEmitirActo(acto);

    expect(screen.queryByLabelText(/^Fecha de eficacia/)).not.toBeInTheDocument();
    await screen.findByText("Quedará pendiente de notificación.");

    const selectDocumento = await screen.findByLabelText(/^PDF firmado del acto/);
    await screen.findByRole("option", { name: "Resolución firmada (R-10)" });
    await userEvent.selectOptions(selectDocumento, "d1");
    await userEvent.click(screen.getByRole("button", { name: "Emitir" }));

    expect(onConfirmar).toHaveBeenCalledWith({
      documento_acto_id: "d1",
      fecha_eficacia: null,
    });
  });

  it("EMI-04 · GENERAL: muestra «Quedará pendiente de publicación en Gaceta.»", async () => {
    const acto = { ...ACTO_BASE, caracter: "GENERAL" as const };
    montarEmitirActo(acto);

    await screen.findByText("Quedará pendiente de publicación en Gaceta.");
  });

  it("EMI-05 · el select «PDF firmado del acto» ofrece los documentos ACTIVE y no ofrece el ARCHIVED", async () => {
    montarEmitirActo(ACTO_BASE);

    const select = await screen.findByLabelText(/^PDF firmado del acto/);
    expect(
      await screen.findByRole("option", { name: "Resolución firmada (R-10)" }),
    ).toBeInTheDocument();
    expect(
      await screen.findByRole("option", { name: "Gaceta Nº 4.512" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("option", { name: "Borrador anulado" }),
    ).not.toBeInTheDocument();
    expect(select).toHaveValue("");
  });

  it("EMI-06 · sin documentos ACTIVE muestra aviso y botón «Emitir» deshabilitado", async () => {
    apiFetch.mockResolvedValue([DOCUMENTOS[2]]);
    montarEmitirActo(ACTO_BASE);

    await screen.findByText("Adjunte primero el documento en «Documentos del acto».");
    expect(screen.getByRole("button", { name: "Emitir" })).toBeDisabled();
  });

  it("EMI-07 · erroresServidor en documento_acto_id se muestra y select aria-invalid", async () => {
    montarEmitirActo(ACTO_BASE, {
      erroresServidor: { documento_acto_id: ["El documento no pertenece al acto"] },
    });

    await screen.findByText("El documento no pertenece al acto");
    const selectDocumento = await screen.findByLabelText(/^PDF firmado del acto/);
    await screen.findByRole("option", { name: "Resolución firmada (R-10)" });
    expect(selectDocumento).toHaveAttribute("aria-invalid", "true");
  });

  it("EMI-08 · «Cancelar» llama onCancelar", async () => {
    const { onCancelar } = montarEmitirActo(ACTO_BASE);

    await userEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(onCancelar).toHaveBeenCalled();
  });
});
