import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { UnidadFormulario } from "./UnidadFormulario";
import { EstadoEstructura, Unidad } from "@/modules/gobierno/api";

const DESP: Unidad = {
  id: "desp",
  codigo: "DESP",
  denominacion: "Despacho",
  tipo: "ORGANO",
  nivel: 0,
  estado: "ACTIVA",
  version: 1,
  unidad_superior_id: null,
  vigente_desde: "2026-01-01",
  vigente_hasta: null,
};

const DA: Unidad = {
  id: "da",
  codigo: "DA-01",
  denominacion: "Dirección Administrativa",
  tipo: "UNIDAD_ADMINISTRATIVA",
  nivel: 1,
  estado: "ACTIVA",
  version: 1,
  unidad_superior_id: "desp",
  vigente_desde: "2026-01-01",
  vigente_hasta: null,
};

const CG1: Unidad = {
  id: "cg1",
  codigo: "CG-01",
  denominacion: "Centro Gestor Uno",
  tipo: "CENTRO_GESTOR",
  nivel: 2,
  estado: "ACTIVA",
  version: 1,
  unidad_superior_id: "da",
  vigente_desde: "2026-01-01",
  vigente_hasta: null,
};

const SEDE: Unidad = {
  id: "sede",
  codigo: "SEDE",
  denominacion: "Sede",
  tipo: "SEDE",
  nivel: 0,
  estado: "INACTIVA",
  version: 1,
  unidad_superior_id: null,
  vigente_desde: "2026-01-01",
  vigente_hasta: "2026-12-31",
};

const UNIDADES = [DESP, DA, CG1, SEDE];

function montar(props: Partial<Parameters<typeof UnidadFormulario>[0]> = {}) {
  const onGuardar = vi.fn().mockResolvedValue(undefined);
  const onCancelar = vi.fn();
  const defaults = {
    modo: "editar" as const,
    estadoEstructura: "BORRADOR" as EstadoEstructura,
    ejercicio: 2026,
    unidades: UNIDADES,
    unidad: DA,
    onGuardar,
    onCancelar,
    erroresServidor: {},
  };
  render(<UnidadFormulario {...defaults} {...props} />);
  return { onGuardar, onCancelar };
}

describe("UnidadFormulario · estructura organizativa (GOV-0-02)", () => {
  it("GUF-01 · en edición, «Depende de» no ofrece la propia unidad, sus descendientes ni inactivas", () => {
    montar();
    const select = screen.getByLabelText(/^Depende de/);
    const opciones = Array.from(select.querySelectorAll("option")).map(
      (o) => o.textContent,
    );
    expect(opciones).toContain("El ente (sin unidad superior)");
    expect(opciones).toContain("DESP · Despacho");
    expect(opciones).not.toContain("DA-01 · Dirección Administrativa");
    expect(opciones).not.toContain("CG-01 · Centro Gestor Uno");
    expect(opciones).not.toContain("SEDE · Sede");
  });

  it("GUF-02 · crear en borrador normaliza el código y guarda sin motivo", async () => {
    const { onGuardar } = montar({
      modo: "crear",
      unidad: undefined,
      superiorInicial: null,
    });
    await userEvent.type(screen.getByLabelText(/^Código/), "nuevo-1");
    await userEvent.type(
      screen.getByLabelText(/^Denominación/),
      "Unidad nueva",
    );
    await userEvent.selectOptions(
      screen.getByLabelText(/^Tipo de unidad/),
      "DEPENDENCIA",
    );
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(onGuardar).toHaveBeenCalledWith(
      expect.objectContaining({
        codigo: "NUEVO-1",
        denominacion: "Unidad nueva",
        tipo: "DEPENDENCIA",
        unidad_superior_id: null,
      }),
      null,
    );
    expect(screen.getByLabelText(/^Vigente desde/)).toHaveValue("2026-01-01");
  });

  it("GUF-03 · en estructura vigente el código queda bloqueado y el motivo es obligatorio", async () => {
    const { onGuardar } = montar({ estadoEstructura: "VIGENTE" });
    expect(screen.getByLabelText(/^Código/)).toBeDisabled();
    await userEvent.clear(screen.getByLabelText(/^Denominación/));
    await userEvent.type(
      screen.getByLabelText(/^Denominación/),
      "Dirección Administrativa General",
    );
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(onGuardar).not.toHaveBeenCalled();
    expect(
      screen.getByText("Indique el motivo (de 5 a 255 caracteres)"),
    ).toBeInTheDocument();
    await userEvent.type(
      screen.getByLabelText(/^Motivo del cambio/),
      "Reorganización",
    );
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(onGuardar).toHaveBeenCalledWith(
      { denominacion: "Dirección Administrativa General" },
      "Reorganización",
    );
  });

  it("GUF-04 · sin cambios no llama a onGuardar y avisa", async () => {
    const { onGuardar } = montar();
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(onGuardar).not.toHaveBeenCalled();
    expect(screen.getByText("No hay cambios que guardar")).toBeInTheDocument();
  });

  it("GUF-05 · muestra el error del servidor y marca el campo inválido", () => {
    montar({
      erroresServidor: {
        codigo: ["Ya existe una unidad con ese código en esta estructura"],
      },
    });
    expect(
      screen.getByText("Ya existe una unidad con ese código en esta estructura"),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/^Código/)).toHaveAttribute(
      "aria-invalid",
      "true",
    );
  });
});
