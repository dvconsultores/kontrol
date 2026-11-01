import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import {
  AccionCompetencia,
  Competencia,
  MateriaCompetencia,
} from "@/modules/gobierno/api";
import { CompetenciaFormulario } from "./CompetenciaFormulario";
import { RetirarCompetencia } from "./RetirarCompetencia";

const COMPETENCIA_EXISTENTE: Competencia = {
  id: "c1",
  accion: "APROBAR",
  materia: "CONTRATACIONES",
  tipo_limite: "SIN_LIMITE",
  monto: null,
  moneda: null,
  fundamento: null,
};

function montarCompetencia(
  props: Partial<Parameters<typeof CompetenciaFormulario>[0]> = {},
) {
  const onGuardar = vi.fn().mockResolvedValue(undefined);
  const onCancelar = vi.fn();
  const defaults = {
    modo: "agregar" as const,
    cargoCodigo: "DIR-TES",
    cargoVigente: false,
    competencia: undefined,
    competenciasExistentes: [] as Competencia[],
    onGuardar,
    onCancelar,
    erroresServidor: {},
  };
  render(<CompetenciaFormulario {...defaults} {...props} />);
  return { onGuardar, onCancelar };
}

function montarRetirar(
  props: Partial<Parameters<typeof RetirarCompetencia>[0]> = {},
) {
  const onConfirmar = vi.fn().mockResolvedValue(undefined);
  const onCancelar = vi.fn();
  const defaults = {
    competencia: COMPETENCIA_EXISTENTE,
    cargoVigente: true,
    onConfirmar,
    onCancelar,
    erroresServidor: {},
  };
  render(<RetirarCompetencia {...defaults} {...props} />);
  return { onConfirmar, onCancelar };
}

describe("CompetenciaFormulario", () => {
  it("GKF-01 · agregar sin acción ni materia muestra errores y no llama a onGuardar", async () => {
    const { onGuardar } = montarCompetencia();
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(
      screen.getByText("Seleccione la acción", { ignore: "option" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Seleccione la materia", { ignore: "option" }),
    ).toBeInTheDocument();
    expect(onGuardar).not.toHaveBeenCalled();
  });

  it("GKF-02 · agregar con acción y materia ya existentes muestra error de duplicado y no llama a onGuardar", async () => {
    const { onGuardar } = montarCompetencia({
      competenciasExistentes: [
        {
          id: "c1",
          accion: "APROBAR",
          materia: "CONTRATACIONES",
          tipo_limite: "SIN_LIMITE",
          monto: null,
          moneda: null,
          fundamento: null,
        },
      ],
    });
    await userEvent.selectOptions(screen.getByLabelText(/^Acción/), "APROBAR");
    await userEvent.selectOptions(
      screen.getByLabelText(/^Materia/),
      "CONTRATACIONES",
    );
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(
      screen.getByText("El cargo ya tiene esa competencia"),
    ).toBeInTheDocument();
    expect(onGuardar).not.toHaveBeenCalled();
  });

  it("GKF-03 · MONTO inválido muestra el error correspondiente y no llama a onGuardar", async () => {
    const { onGuardar } = montarCompetencia();
    await userEvent.click(screen.getByLabelText("Hasta un monto por operación"));

    await userEvent.type(
      screen.getByLabelText(/^Monto máximo por operación/),
      "0",
    );
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(
      screen.getByText("El monto debe ser mayor que cero"),
    ).toBeInTheDocument();
    expect(onGuardar).not.toHaveBeenCalled();

    await userEvent.clear(
      screen.getByLabelText(/^Monto máximo por operación/),
    );
    await userEvent.type(
      screen.getByLabelText(/^Monto máximo por operación/),
      "1,234",
    );
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(
      screen.getByText("Indique un monto válido, con hasta dos decimales"),
    ).toBeInTheDocument();
    expect(onGuardar).not.toHaveBeenCalled();

    await userEvent.clear(
      screen.getByLabelText(/^Monto máximo por operación/),
    );
    await userEvent.type(
      screen.getByLabelText(/^Monto máximo por operación/),
      "12345678901234567",
    );
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(
      screen.getByText("El monto admite como máximo 16 dígitos enteros"),
    ).toBeInTheDocument();
    expect(onGuardar).not.toHaveBeenCalled();

    await userEvent.clear(
      screen.getByLabelText(/^Monto máximo por operación/),
    );
    await userEvent.type(
      screen.getByLabelText(/^Monto máximo por operación/),
      "50000,5",
    );
    await userEvent.selectOptions(screen.getByLabelText(/^Acción/), "APROBAR");
    await userEvent.selectOptions(
      screen.getByLabelText(/^Materia/),
      "CONTRATACIONES",
    );
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(
      screen.getByText("Seleccione la moneda", { ignore: "option" }),
    ).toBeInTheDocument();
    expect(onGuardar).not.toHaveBeenCalled();
  });

  it("GKF-04 · MONTO válido normaliza el monto y llama a onGuardar", async () => {
    const { onGuardar } = montarCompetencia();
    await userEvent.selectOptions(screen.getByLabelText(/^Acción/), "APROBAR");
    await userEvent.selectOptions(
      screen.getByLabelText(/^Materia/),
      "CONTRATACIONES",
    );
    await userEvent.click(screen.getByLabelText("Hasta un monto por operación"));
    await userEvent.type(
      screen.getByLabelText(/^Monto máximo por operación/),
      "50000,5",
    );
    await userEvent.selectOptions(screen.getByLabelText(/^Moneda/), "USD");
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(onGuardar).toHaveBeenCalledWith(
      {
        accion: "APROBAR" as AccionCompetencia,
        materia: "CONTRATACIONES" as MateriaCompetencia,
        tipo_limite: "MONTO",
        monto: "50000.50",
        moneda: "USD",
        fundamento: null,
      },
      null,
    );
  });

  it("GKF-05 · SIN_LIMITE llama a onGuardar con monto y moneda nulos", async () => {
    const { onGuardar } = montarCompetencia();
    await userEvent.selectOptions(screen.getByLabelText(/^Acción/), "APROBAR");
    await userEvent.selectOptions(
      screen.getByLabelText(/^Materia/),
      "CONTRATACIONES",
    );
    await userEvent.click(screen.getByLabelText("Hasta un monto por operación"));
    await userEvent.type(
      screen.getByLabelText(/^Monto máximo por operación/),
      "50000",
    );
    await userEvent.click(screen.getByLabelText("Sin límite"));
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(onGuardar).toHaveBeenCalledWith(
      expect.objectContaining({
        tipo_limite: "SIN_LIMITE",
        monto: null,
        moneda: null,
      }),
      null,
    );
  });

  it("GKF-06 · cargo vigente exige motivo y lo pasa como segundo argumento", async () => {
    const { onGuardar } = montarCompetencia({ cargoVigente: true });
    await userEvent.selectOptions(screen.getByLabelText(/^Acción/), "APROBAR");
    await userEvent.selectOptions(
      screen.getByLabelText(/^Materia/),
      "CONTRATACIONES",
    );
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(
      screen.getByText("Indique el motivo (de 5 a 255 caracteres)"),
    ).toBeInTheDocument();
    expect(onGuardar).not.toHaveBeenCalled();

    await userEvent.type(
      screen.getByLabelText(/^Motivo del cambio/),
      "Ajuste aprobado",
    );
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(onGuardar).toHaveBeenCalledWith(expect.anything(), "Ajuste aprobado");
  });

  it("GKF-07 · cambiar no muestra selects de acción/materia y usa los valores de la competencia", async () => {
    const competencia: Competencia = {
      id: "c1",
      accion: "APROBAR",
      materia: "CONTRATACIONES",
      tipo_limite: "MONTO",
      monto: "1000.00",
      moneda: "USD",
      fundamento: null,
    };
    const { onGuardar } = montarCompetencia({
      modo: "cambiar",
      competencia,
      cargoVigente: true,
    });
    expect(screen.queryByLabelText(/^Acción/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/^Materia/)).not.toBeInTheDocument();
    expect(screen.getByText("Aprobar · Contrataciones")).toBeInTheDocument();
    expect(screen.getByLabelText(/^Monto máximo por operación/)).toHaveValue(
      "1000.00",
    );
    await userEvent.type(
      screen.getByLabelText(/^Motivo del cambio/),
      "Ajuste aprobado",
    );
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(onGuardar).toHaveBeenCalledWith(
      expect.objectContaining({
        accion: "APROBAR",
        materia: "CONTRATACIONES",
      }),
      "Ajuste aprobado",
    );
  });
});

describe("RetirarCompetencia", () => {
  it("GRC-01 · cargo vigente exige motivo para confirmar", async () => {
    const { onConfirmar } = montarRetirar({ cargoVigente: true });
    await userEvent.click(
      screen.getByRole("button", { name: "Retirar competencia" }),
    );
    expect(
      screen.getByText("Indique el motivo (de 5 a 255 caracteres)"),
    ).toBeInTheDocument();
    expect(onConfirmar).not.toHaveBeenCalled();

    await userEvent.type(screen.getByLabelText(/^Motivo/), "Supresión del cargo");
    await userEvent.click(
      screen.getByRole("button", { name: "Retirar competencia" }),
    );
    expect(onConfirmar).toHaveBeenCalledWith("Supresión del cargo");
  });

  it("GRC-02 · cargo no vigente no muestra campo Motivo y confirma con null", async () => {
    const { onConfirmar } = montarRetirar({ cargoVigente: false });
    expect(screen.queryByLabelText(/^Motivo/)).not.toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: "Retirar competencia" }),
    );
    expect(onConfirmar).toHaveBeenCalledWith(null);
  });
});
