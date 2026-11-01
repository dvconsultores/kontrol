import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Acto } from "@/modules/gobierno/api";
import { CorregirActo } from "./CorregirActo";

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

function montarCorregir(
  props: Partial<Parameters<typeof CorregirActo>[0]> = {},
) {
  const onConfirmar = vi.fn().mockResolvedValue(undefined);
  const onCancelar = vi.fn();
  const defaults = {
    acto: ACTO,
    onConfirmar,
    onCancelar,
    erroresServidor: {},
  };
  render(<CorregirActo {...defaults} {...props} />);
  return { onConfirmar, onCancelar };
}

describe("CorregirActo", () => {
  it("COR-01 · los campos arrancan con los valores del acto", () => {
    montarCorregir();
    expect(screen.getByLabelText(/^Lugar/)).toHaveValue("Caracas");
    expect(screen.getByLabelText(/^Asunto/)).toHaveValue(
      "Designación del tesorero",
    );
    expect(screen.getByLabelText(/^Decisión/)).toHaveValue("Se designa");
  });

  it("COR-02 · cambiar «Asunto» y escribir el motivo → onConfirmar con lo cambiado", async () => {
    const { onConfirmar } = montarCorregir();
    await userEvent.clear(screen.getByLabelText(/^Asunto/));
    await userEvent.type(
      screen.getByLabelText(/^Asunto/),
      "  Designación de la tesorera  ",
    );
    await userEvent.type(
      screen.getByLabelText(/^Motivo de la corrección/),
      "Error de transcripción",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Guardar corrección" }),
    );
    expect(onConfirmar).toHaveBeenCalledWith({
      asunto: "Designación de la tesorera",
      motivo: "Error de transcripción",
    });
  });

  it("COR-03 · vaciar «Destinatario» (opcional) y motivo válido → onConfirmar con null", async () => {
    const { onConfirmar } = montarCorregir();
    await userEvent.clear(screen.getByLabelText(/^Destinatario/));
    await userEvent.type(
      screen.getByLabelText(/^Motivo de la corrección/),
      "Se omitió el destinatario",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Guardar corrección" }),
    );
    expect(onConfirmar).toHaveBeenCalledWith({
      destinatario: null,
      motivo: "Se omitió el destinatario",
    });
  });

  it("COR-04 · sin cambios y con motivo → aviso y no se llama onConfirmar", async () => {
    const { onConfirmar } = montarCorregir();
    await userEvent.type(
      screen.getByLabelText(/^Motivo de la corrección/),
      "Motivo válido",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Guardar corrección" }),
    );
    expect(screen.getByText("No hay cambios que guardar")).toBeInTheDocument();
    expect(onConfirmar).not.toHaveBeenCalled();
  });

  it("COR-05 · motivo de 3 caracteres con un cambio → error y no se llama onConfirmar", async () => {
    const { onConfirmar } = montarCorregir();
    await userEvent.clear(screen.getByLabelText(/^Asunto/));
    await userEvent.type(screen.getByLabelText(/^Asunto/), "Nuevo asunto");
    await userEvent.type(screen.getByLabelText(/^Motivo de la corrección/), "abc");
    await userEvent.click(
      screen.getByRole("button", { name: "Guardar corrección" }),
    );
    expect(
      screen.getByText("Indique el motivo (de 5 a 255 caracteres)"),
    ).toBeInTheDocument();
    expect(onConfirmar).not.toHaveBeenCalled();
  });

  it("COR-06 · erroresServidor se muestra y «Asunto» tiene aria-invalid", () => {
    montarCorregir({
      erroresServidor: { asunto: ["El asunto es demasiado corto"] },
    });
    expect(
      screen.getByText("El asunto es demasiado corto"),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/^Asunto/)).toHaveAttribute(
      "aria-invalid",
      "true",
    );
  });

  it("COR-07 · «Cancelar» llama onCancelar", async () => {
    const { onCancelar } = montarCorregir();
    await userEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(onCancelar).toHaveBeenCalled();
  });
});
