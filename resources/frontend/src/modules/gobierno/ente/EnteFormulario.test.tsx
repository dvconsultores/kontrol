import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { type EnteDatos } from "@/modules/gobierno/api";
import { EnteFormulario } from "./EnteFormulario";

const ENTE_BORRADOR: EnteDatos = {
  denominacion: "Alcaldía del Municipio Demo",
  siglas: null,
  rif: null,
  nivel_territorial: "MUNICIPAL",
  forma_organizativa: "ADMINISTRACION_CENTRAL",
  organo_adscripcion: null,
  entidad_federal: "Lara",
  municipio: "Iribarren",
  acto_tipo: "ORDENANZA",
  acto_numero: "1",
  acto_fecha: "2020-01-15",
  acto_publicacion: "Gaceta Municipal N.º 1",
};

function montar(props: Partial<Parameters<typeof EnteFormulario>[0]> = {}): void {
  const onGuardar = vi.fn().mockResolvedValue(undefined);
  const onCancelar = vi.fn();
  render(
    <EnteFormulario
      modo="alta"
      inicial={null}
      onGuardar={onGuardar}
      onCancelar={onCancelar}
      erroresServidor={{}}
      {...props}
    />,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("EnteFormulario", () => {
  it("GEF-01 · condicionales de naturaleza según forma y nivel", async () => {
    montar();
    expect(screen.queryByLabelText("Órgano de adscripción")).toBeNull();
    expect(screen.queryByLabelText("Entidad federal")).toBeNull();
    expect(screen.queryByLabelText("Municipio")).toBeNull();

    await userEvent.selectOptions(screen.getByLabelText("Forma organizativa"), "Instituto público");
    expect(screen.getByLabelText("Órgano de adscripción")).toBeInTheDocument();

    await userEvent.selectOptions(screen.getByLabelText("Nivel político-territorial"), "Estadal");
    expect(screen.getByLabelText("Entidad federal")).toBeInTheDocument();
    expect(screen.queryByLabelText("Municipio")).toBeNull();

    await userEvent.selectOptions(screen.getByLabelText("Nivel político-territorial"), "Municipal");
    expect(screen.getByLabelText("Entidad federal")).toBeInTheDocument();
    expect(screen.getByLabelText("Municipio")).toBeInTheDocument();
  });

  it("GEF-02 · alta mínima envía solo la denominación", async () => {
    const onGuardar = vi.fn().mockResolvedValue(undefined);
    render(
      <EnteFormulario
        modo="alta"
        inicial={null}
        onGuardar={onGuardar}
        onCancelar={vi.fn()}
        erroresServidor={{}}
      />,
    );
    await userEvent.type(screen.getByLabelText(/^Denominación oficial/), "Ente Demo");
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(onGuardar).toHaveBeenCalledWith({ denominacion: "Ente Demo" }, null);
  });

  it("GEF-03 · denominación corta no guarda y muestra error", async () => {
    const onGuardar = vi.fn().mockResolvedValue(undefined);
    render(
      <EnteFormulario
        modo="alta"
        inicial={null}
        onGuardar={onGuardar}
        onCancelar={vi.fn()}
        erroresServidor={{}}
      />,
    );
    await userEvent.type(screen.getByLabelText(/^Denominación oficial/), "AB");
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(onGuardar).not.toHaveBeenCalled();
    expect(screen.getByText("Indique la denominación oficial (3 a 200 caracteres)")).toBeInTheDocument();
  });

  it("GEF-04 · edición sin cambios no guarda y avisa", async () => {
    const onGuardar = vi.fn().mockResolvedValue(undefined);
    render(
      <EnteFormulario
        modo="edicion"
        inicial={ENTE_BORRADOR}
        onGuardar={onGuardar}
        onCancelar={vi.fn()}
        erroresServidor={{}}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(onGuardar).not.toHaveBeenCalled();
    expect(screen.getByText("No hay cambios que guardar")).toBeInTheDocument();
  });

  it("GEF-05 · campo oculto se vacía al cambiar de nivel", async () => {
    const onGuardar = vi.fn().mockResolvedValue(undefined);
    render(
      <EnteFormulario
        modo="edicion"
        inicial={ENTE_BORRADOR}
        onGuardar={onGuardar}
        onCancelar={vi.fn()}
        erroresServidor={{}}
      />,
    );
    await userEvent.selectOptions(screen.getByLabelText("Nivel político-territorial"), "Nacional");
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(onGuardar).toHaveBeenCalledWith(
      { nivel_territorial: "NACIONAL", entidad_federal: null, municipio: null },
      null,
    );
  });

  it("GEF-06 · modificación exige motivo", async () => {
    const onGuardar = vi.fn().mockResolvedValue(undefined);
    render(
      <EnteFormulario
        modo="modificacion"
        inicial={ENTE_BORRADOR}
        onGuardar={onGuardar}
        onCancelar={vi.fn()}
        erroresServidor={{}}
      />,
    );
    const siglas = screen.getByLabelText("Siglas");
    await userEvent.clear(siglas);
    await userEvent.type(siglas, "AMD");
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(onGuardar).not.toHaveBeenCalled();
    expect(screen.getByText("Indique el motivo (de 5 a 255 caracteres)")).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText(/^Motivo de la modificación/), "Ajuste de siglas");
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(onGuardar).toHaveBeenCalledWith({ siglas: "AMD" }, "Ajuste de siglas");
  });

  it("GEF-07 · errores del servidor se muestran y marcan el control", () => {
    render(
      <EnteFormulario
        modo="alta"
        inicial={null}
        onGuardar={vi.fn().mockResolvedValue(undefined)}
        onCancelar={vi.fn()}
        erroresServidor={{ rif: ["RIF inválido; formato esperado: J-12345678-9"] }}
      />,
    );
    expect(screen.getByText("RIF inválido; formato esperado: J-12345678-9")).toBeInTheDocument();
    expect(screen.getByLabelText("RIF")).toHaveAttribute("aria-invalid", "true");
  });
});
