import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Cargo, Unidad } from "@/modules/gobierno/api";
import { CargoFormulario } from "./CargoFormulario";
import { DesactivarCargo } from "./DesactivarCargo";

const UNIDAD_ACTIVA: Unidad = {
  id: "da-01",
  codigo: "DA-01",
  denominacion: "Dirección de Administración",
  tipo: "UNIDAD_ADMINISTRATIVA",
  nivel: 1,
  estado: "ACTIVA",
  version: 1,
  unidad_superior_id: null,
  vigente_desde: "2026-01-01",
  vigente_hasta: null,
};

const UNIDAD_INACTIVA: Unidad = {
  id: "da-02",
  codigo: "DA-02",
  denominacion: "Dirección Inactiva",
  tipo: "UNIDAD_ADMINISTRATIVA",
  nivel: 1,
  estado: "INACTIVA",
  version: 1,
  unidad_superior_id: null,
  vigente_desde: "2026-01-01",
  vigente_hasta: "2026-12-31",
};

const UNIDADES = [UNIDAD_ACTIVA, UNIDAD_INACTIVA];

const CARGO_VIGENTE: Cargo = {
  id: "cargo-1",
  codigo: "DIR-TES",
  denominacion: "Dirección de Tesorería",
  unidad_id: "da-01",
  unidad_codigo: "DA-01",
  unidad_denominacion: "Dirección de Administración",
  estado: "VIGENTE",
  version: 1,
  vigente_desde: "2026-01-01",
  vigente_hasta: null,
  competencias: [],
  faltantes_para_activar: [],
  documento_vinculado: false,
  activado_en: null,
  activado_por: null,
  creado_en: "2026-01-01T00:00:00Z",
};

const CARGO_BORRADOR: Cargo = {
  id: "cargo-2",
  codigo: "DIR-CON",
  denominacion: "Dirección de Contabilidad",
  unidad_id: "da-01",
  unidad_codigo: "DA-01",
  unidad_denominacion: "Dirección de Administración",
  estado: "BORRADOR",
  version: 1,
  vigente_desde: "2026-01-01",
  vigente_hasta: null,
  competencias: [],
  faltantes_para_activar: [],
  documento_vinculado: false,
  activado_en: null,
  activado_por: null,
  creado_en: "2026-01-01T00:00:00Z",
};

function montarCargo(
  props: Partial<Parameters<typeof CargoFormulario>[0]> = {},
) {
  const onGuardar = vi.fn().mockResolvedValue(undefined);
  const onCancelar = vi.fn();
  const defaults = {
    modo: "crear" as const,
    ejercicio: 2026,
    unidades: UNIDADES,
    cargo: undefined,
    unidadInicial: null,
    onGuardar,
    onCancelar,
    erroresServidor: {},
  };
  render(<CargoFormulario {...defaults} {...props} />);
  return { onGuardar, onCancelar };
}

function montarDesactivar(
  props: Partial<Parameters<typeof DesactivarCargo>[0]> = {},
) {
  const onConfirmar = vi.fn().mockResolvedValue(undefined);
  const onCancelar = vi.fn();
  const defaults = {
    cargo: CARGO_VIGENTE,
    ejercicio: 2026,
    onConfirmar,
    onCancelar,
    erroresServidor: {},
  };
  render(<DesactivarCargo {...defaults} {...props} />);
  return { onConfirmar, onCancelar };
}

describe("CargoFormulario", () => {
  it("GCF-01 · crear valida unidad elegible, código y vigencia dentro del ejercicio", async () => {
    const { onGuardar } = montarCargo();

    const selectUnidad = screen.getByLabelText(/^Unidad/);
    const opciones = Array.from(selectUnidad.querySelectorAll("option")).map(
      (o) => ({
        value: o.value,
        text: o.textContent,
      }),
    );
    expect(opciones).toContainEqual({
      value: "da-01",
      text: "DA-01 — Dirección de Administración",
    });
    expect(opciones).not.toContainEqual({
      value: "da-02",
      text: "DA-02 — Dirección Inactiva",
    });

    await userEvent.type(screen.getByLabelText(/^Código/), "?");
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(
      screen.getByText("Use de 1 a 30 letras, números, punto o guion"),
    ).toBeInTheDocument();
    expect(onGuardar).not.toHaveBeenCalled();

    await userEvent.clear(screen.getByLabelText(/^Código/));
    await userEvent.type(screen.getByLabelText(/^Código/), "DIR-TES");
    await userEvent.clear(screen.getByLabelText(/^Vigente desde/));
    await userEvent.type(
      screen.getByLabelText(/^Vigente desde/),
      "2025-12-31",
    );
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(
      screen.getByText("Debe estar dentro del ejercicio"),
    ).toBeInTheDocument();
    expect(onGuardar).not.toHaveBeenCalled();
  });

  it("GCF-02 · crear válido normaliza el código y llama a onGuardar", async () => {
    const { onGuardar } = montarCargo();
    await userEvent.type(screen.getByLabelText(/^Código/), "dir-tes");
    await userEvent.type(
      screen.getByLabelText(/^Denominación/),
      "Dirección de Tesorería",
    );
    await userEvent.selectOptions(screen.getByLabelText(/^Unidad/), "da-01");
    await userEvent.clear(screen.getByLabelText(/^Vigente desde/));
    await userEvent.type(
      screen.getByLabelText(/^Vigente desde/),
      "2026-01-01",
    );
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(onGuardar).toHaveBeenCalledWith(
      {
        codigo: "DIR-TES",
        denominacion: "Dirección de Tesorería",
        unidad_id: "da-01",
        vigente_desde: "2026-01-01",
      },
      null,
    );
  });

  it("GCF-03 · editar vigente bloquea código y vigencia, exige motivo y envía solo denominación", async () => {
    const { onGuardar } = montarCargo({
      modo: "editar",
      cargo: CARGO_VIGENTE,
    });
    expect(screen.getByLabelText(/^Código/)).toBeDisabled();
    expect(screen.getByLabelText(/^Vigente desde/)).toBeDisabled();

    await userEvent.clear(screen.getByLabelText(/^Denominación/));
    await userEvent.type(
      screen.getByLabelText(/^Denominación/),
      "Dirección de Tesorería General",
    );
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(
      screen.getByText("Indique el motivo (de 5 a 255 caracteres)"),
    ).toBeInTheDocument();
    expect(onGuardar).not.toHaveBeenCalled();

    await userEvent.type(
      screen.getByLabelText(/^Motivo del cambio/),
      "Reorganización",
    );
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(onGuardar).toHaveBeenCalledWith(
      { denominacion: "Dirección de Tesorería General" },
      "Reorganización",
    );
  });

  it("GCF-04 · editar sin cambios muestra aviso y no llama a onGuardar", async () => {
    const { onGuardar } = montarCargo({
      modo: "editar",
      cargo: CARGO_BORRADOR,
    });
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(screen.getByText("No hay cambios que guardar")).toBeInTheDocument();
    expect(onGuardar).not.toHaveBeenCalled();
  });

  it("GCF-05 · editar borrador permite cambiar el código y lo normaliza", async () => {
    const { onGuardar } = montarCargo({
      modo: "editar",
      cargo: CARGO_BORRADOR,
    });
    await userEvent.clear(screen.getByLabelText(/^Código/));
    await userEvent.type(screen.getByLabelText(/^Código/), "dir-fin");
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(onGuardar).toHaveBeenCalledWith(
      expect.objectContaining({ codigo: "DIR-FIN" }),
      null,
    );
  });
});

describe("DesactivarCargo", () => {
  it("GDC-01 · valida fecha y motivo, y confirma con los valores correctos", async () => {
    const { onConfirmar } = montarDesactivar();
    expect(screen.getByLabelText(/^Fecha de fin de vigencia/)).toHaveValue(
      "2026-12-31",
    );

    await userEvent.clear(
      screen.getByLabelText(/^Fecha de fin de vigencia/),
    );
    await userEvent.type(
      screen.getByLabelText(/^Fecha de fin de vigencia/),
      "2027-01-01",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Desactivar cargo" }),
    );
    expect(
      screen.getByText(
        "La fecha debe estar dentro del ejercicio y no antes del inicio de vigencia del cargo",
      ),
    ).toBeInTheDocument();
    expect(onConfirmar).not.toHaveBeenCalled();

    await userEvent.clear(
      screen.getByLabelText(/^Fecha de fin de vigencia/),
    );
    await userEvent.type(
      screen.getByLabelText(/^Fecha de fin de vigencia/),
      "2026-12-31",
    );
    await userEvent.type(
      screen.getByLabelText(/^Motivo/),
      "Supresión del cargo",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Desactivar cargo" }),
    );
    expect(onConfirmar).toHaveBeenCalledWith(
      "2026-12-31",
      "Supresión del cargo",
    );
  });
});
