import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Acto, nombreDeActo } from "@/modules/gobierno/api";
import { DocumentSummary } from "@/modules/documentos/types";
import { RegistrarEficacia } from "./RegistrarEficacia";

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
  caracter: "GENERAL",
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
  notificaciones: null,
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

function montarRegistrarEficacia(
  acto: Acto,
  props: Partial<Parameters<typeof RegistrarEficacia>[0]> = {},
) {
  const onConfirmar = vi.fn().mockResolvedValue(undefined);
  const onCancelar = vi.fn();
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  render(
    <QueryClientProvider client={client}>
      <RegistrarEficacia
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

async function fijarFecha(campo: HTMLElement, valor: string) {
  fireEvent.change(campo, { target: { value: valor } });
}

describe("RegistrarEficacia", () => {
  beforeEach(() => {
    apiFetch.mockReset();
    apiFetch.mockResolvedValue(DOCUMENTOS);
  });

  it("EFI-01 · GENERAL: título y medio único marcado; rellenar datos y Registrar llama onConfirmar exactamente", async () => {
    const acto: Acto = {
      ...ACTO_BASE,
      caracter: "GENERAL",
      estado: "EMITIDO",
      documento_acto_id: "d1",
    };
    const { onConfirmar } = montarRegistrarEficacia(acto);

    await screen.findByText(`Registrar la publicación de ${nombreDeActo(acto)}`);
    expect(screen.getByRole("radio", { name: "Gaceta Oficial" })).toBeChecked();

    await userEvent.type(
      screen.getByLabelText(/^Referencia de la publicación/),
      "Gaceta Oficial Nº 4.512",
    );

    const fecha = screen.getByLabelText(/^Fecha de la publicación/);
    await fijarFecha(fecha, "2026-10-01");

    const soporte = screen.getByRole("combobox", { name: /^Soporte/ });
    await screen.findByRole("option", { name: "Gaceta Nº 4.512" });
    await userEvent.selectOptions(soporte, "d2");

    await userEvent.click(screen.getByRole("button", { name: "Registrar" }));

    expect(onConfirmar).toHaveBeenCalledWith({
      medio: "GACETA",
      referencia: "Gaceta Oficial Nº 4.512",
      fecha: "2026-10-01",
      documento_eficacia_id: "d2",
      fecha_eficacia: null,
    });
  });

  it("EFI-02 · GENERAL: un solo radio «Gaceta Oficial» marcado, rótulo «Fecha de la publicación», sin referencia → error y no llama onConfirmar", async () => {
    const acto: Acto = {
      ...ACTO_BASE,
      caracter: "GENERAL",
      estado: "EMITIDO",
      documento_acto_id: "d1",
    };
    const { onConfirmar } = montarRegistrarEficacia(acto);

    expect(screen.getByRole("radio", { name: "Gaceta Oficial" })).toBeChecked();
    expect(screen.queryByRole("radio", { name: "Notificación personal" })).not.toBeInTheDocument();
    expect(screen.queryByRole("radio", { name: "Publicación en prensa" })).not.toBeInTheDocument();
    expect(screen.getByLabelText(/^Fecha de la publicación/)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Registrar" }));

    await screen.findByText("Indique la referencia (de 3 a 120 caracteres)");
    expect(onConfirmar).not.toHaveBeenCalled();
  });

  it("EFI-03 · GENERAL con fecha 2026-10-01 muestra «Será eficaz desde 01/10/2026»", async () => {
    const acto: Acto = {
      ...ACTO_BASE,
      caracter: "GENERAL",
      estado: "EMITIDO",
      documento_acto_id: "d1",
    };
    montarRegistrarEficacia(acto);

    const fecha = screen.getByLabelText(/^Fecha de la publicación/);
    await fijarFecha(fecha, "2026-10-01");

    await screen.findByText("Será eficaz desde 01/10/2026");
  });

  it("EFI-04 · GENERAL con fecha de eficacia anterior a la de publicación no llama onConfirmar", async () => {
    const acto: Acto = {
      ...ACTO_BASE,
      caracter: "GENERAL",
      estado: "EMITIDO",
      documento_acto_id: "d1",
    };
    const { onConfirmar } = montarRegistrarEficacia(acto);

    const fecha = screen.getByLabelText(/^Fecha de la publicación/);
    await fijarFecha(fecha, "2026-10-01");

    const fechaEficacia = screen.getByLabelText(/^Fecha de eficacia \(opcional\)/);
    await fijarFecha(fechaEficacia, "2026-09-20");

    await userEvent.type(
      screen.getByLabelText(/^Referencia de la publicación/),
      "Gaceta Oficial Nº 4.512",
    );

    const soporte = screen.getByRole("combobox", { name: /^Soporte/ });
    await screen.findByRole("option", { name: "Gaceta Nº 4.512" });
    await userEvent.selectOptions(soporte, "d2");
    await userEvent.click(screen.getByRole("button", { name: "Registrar" }));

    await screen.findByText("No puede ser anterior a 01/10/2026");
    expect(onConfirmar).not.toHaveBeenCalled();
  });

  it("EFI-05 · GENERAL con fecha posterior a hoy muestra error y no llama onConfirmar", async () => {
    const acto: Acto = {
      ...ACTO_BASE,
      caracter: "GENERAL",
      estado: "EMITIDO",
      documento_acto_id: "d1",
    };
    const { onConfirmar } = montarRegistrarEficacia(acto);

    const fecha = screen.getByLabelText(/^Fecha de la publicación/);
    await fijarFecha(fecha, "2026-10-31");

    await userEvent.type(
      screen.getByLabelText(/^Referencia de la publicación/),
      "Gaceta Oficial Nº 4.512",
    );

    const soporte = screen.getByRole("combobox", { name: /^Soporte/ });
    await screen.findByRole("option", { name: "Gaceta Nº 4.512" });
    await userEvent.selectOptions(soporte, "d2");
    await userEvent.click(screen.getByRole("button", { name: "Registrar" }));

    await screen.findByText("La fecha no puede ser posterior a hoy");
    expect(onConfirmar).not.toHaveBeenCalled();
  });

  it("EFI-06 · GENERAL con fecha anterior a la del acto muestra error y no llama onConfirmar", async () => {
    const acto: Acto = {
      ...ACTO_BASE,
      caracter: "GENERAL",
      estado: "EMITIDO",
      documento_acto_id: "d1",
    };
    const { onConfirmar } = montarRegistrarEficacia(acto);

    const fecha = screen.getByLabelText(/^Fecha de la publicación/);
    await fijarFecha(fecha, "2026-09-01");

    await userEvent.type(
      screen.getByLabelText(/^Referencia de la publicación/),
      "Gaceta Oficial Nº 4.512",
    );

    const soporte = screen.getByRole("combobox", { name: /^Soporte/ });
    await screen.findByRole("option", { name: "Gaceta Nº 4.512" });
    await userEvent.selectOptions(soporte, "d2");
    await userEvent.click(screen.getByRole("button", { name: "Registrar" }));

    await screen.findByText("La fecha no puede ser anterior a la fecha del acto");
    expect(onConfirmar).not.toHaveBeenCalled();
  });

  it("EFI-07 · GENERAL: el select «Soporte» no ofrece el documento del propio acto (d1)", async () => {
    const acto: Acto = {
      ...ACTO_BASE,
      caracter: "GENERAL",
      estado: "EMITIDO",
      documento_acto_id: "d1",
    };
    montarRegistrarEficacia(acto);

    expect(
      await screen.findByRole("option", { name: "Gaceta Nº 4.512" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "Resolución firmada (R-10)" }))
      .not.toBeInTheDocument();
  });

  it("EFI-08 · GENERAL con confirmación válida → onConfirmar con referencia, fecha, soporte y fecha_eficacia null", async () => {
    const acto: Acto = {
      ...ACTO_BASE,
      caracter: "GENERAL",
      estado: "EMITIDO",
      documento_acto_id: "d1",
    };
    const { onConfirmar } = montarRegistrarEficacia(acto);

    await userEvent.type(
      screen.getByLabelText(/^Referencia de la publicación/),
      "Gaceta Oficial Nº 2.345",
    );

    const fecha = screen.getByLabelText(/^Fecha de la publicación/);
    await fijarFecha(fecha, "2026-10-01");

    const soporte = screen.getByRole("combobox", { name: /^Soporte/ });
    await screen.findByRole("option", { name: "Gaceta Nº 4.512" });
    await userEvent.selectOptions(soporte, "d2");

    await userEvent.click(screen.getByRole("button", { name: "Registrar" }));

    expect(onConfirmar).toHaveBeenCalledWith({
      medio: "GACETA",
      referencia: "Gaceta Oficial Nº 2.345",
      fecha: "2026-10-01",
      documento_eficacia_id: "d2",
      fecha_eficacia: null,
    });
  });
});
