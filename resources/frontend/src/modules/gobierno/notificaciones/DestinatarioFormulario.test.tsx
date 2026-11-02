import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  DestinatarioFormulario,
  DatosDestinatario,
} from "./DestinatarioFormulario";

const apiFetch = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

vi.mock("@/lib/fecha-de-negocio", async (original) => ({
  ...(await original<typeof import("@/lib/fecha-de-negocio")>()),
  hoyDeNegocio: () => "2026-10-30",
}));

const DATOS_VALIDOS: DatosDestinatario = {
  tipo_persona: "NATURAL",
  nombre: "Pedro Pérez",
  identificacion: "V-12345678",
  domicilio: "Avenida Siempre Viva 742",
  apoderado_nombre: null,
  apoderado_identificacion: null,
  recursos: "No proceden recursos",
};

function renderFormulario(props: Partial<Parameters<typeof DestinatarioFormulario>[0]> = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const onConfirmar = vi.fn().mockResolvedValue(undefined);
  const onCancelar = vi.fn();
  const erroresServidor: Record<string, string[]> = props.erroresServidor ?? {};

  const ui = (
    <QueryClientProvider client={queryClient}>
      <DestinatarioFormulario
        titulo="Agregar destinatario"
        textoConfirmar="Agregar"
        onConfirmar={onConfirmar}
        onCancelar={onCancelar}
        erroresServidor={erroresServidor}
        {...props}
      />
    </QueryClientProvider>
  );

  const utils = render(ui);
  return { ...utils, onConfirmar, onCancelar };
}

describe("DestinatarioFormulario", () => {
  beforeEach(() => {
    apiFetch.mockReset();
  });

  it("DST-01 muestra errores de validación cuando el formulario está vacío y no confirma", async () => {
    const user = userEvent.setup();
    const { onConfirmar } = renderFormulario();

    await user.click(screen.getByRole("button", { name: "Agregar" }));

    expect(screen.getByText("Seleccione el tipo de persona")).toBeInTheDocument();
    expect(screen.getByText("Debe tener entre 3 y 200 caracteres")).toBeInTheDocument();
    expect(screen.getByText("Debe tener entre 5 y 20 caracteres")).toBeInTheDocument();
    expect(screen.getByText("Debe tener entre 5 y 500 caracteres")).toBeInTheDocument();
    expect(screen.getByText("Debe tener entre 5 y 2000 caracteres")).toBeInTheDocument();
    expect(onConfirmar).not.toHaveBeenCalled();
  });

  it("DST-02 recorta los textos con espacios alrededor y llama onConfirmar con los datos válidos", async () => {
    const user = userEvent.setup();
    const { onConfirmar } = renderFormulario();

    await user.click(screen.getByRole("radio", { name: "Persona natural" }));
    await user.type(screen.getByLabelText(/^Nombre o razón social/), "  Pedro Pérez  ");
    await user.type(screen.getByLabelText(/^Cédula o RIF/), "  V-12345678  ");
    await user.type(screen.getByLabelText(/^Domicilio o residencia/), "  Avenida Siempre Viva 742  ");
    await user.type(screen.getByLabelText(/^Recursos que proceden/), "  No proceden recursos  ");

    await user.click(screen.getByRole("button", { name: "Agregar" }));

    expect(onConfirmar).toHaveBeenCalledWith({
      tipo_persona: "NATURAL",
      nombre: "Pedro Pérez",
      identificacion: "V-12345678",
      domicilio: "Avenida Siempre Viva 742",
      apoderado_nombre: null,
      apoderado_identificacion: null,
      recursos: "No proceden recursos",
    });
  });

  it("DST-03 valida los campos del apoderado cuando falta uno de los dos", async () => {
    const user = userEvent.setup();
    const { onConfirmar } = renderFormulario({
      inicial: DATOS_VALIDOS,
    });

    await user.type(screen.getByLabelText(/^Apoderado \(opcional\)/), "Luis García");
    await user.click(screen.getByRole("button", { name: "Agregar" }));

    expect(screen.getByText("Indique la cédula del apoderado")).toBeInTheDocument();
    expect(onConfirmar).not.toHaveBeenCalled();

    await user.clear(screen.getByLabelText(/^Apoderado \(opcional\)/));
    await user.type(screen.getByLabelText(/^Cédula del apoderado/), "V-99999999");
    await user.click(screen.getByRole("button", { name: "Agregar" }));

    expect(screen.getByText("Indique el nombre del apoderado")).toBeInTheDocument();
    expect(onConfirmar).not.toHaveBeenCalled();
  });

  it("DST-04 precarga los campos cuando se recibe la prop inicial", () => {
    renderFormulario({ inicial: DATOS_VALIDOS });

    expect(screen.getByRole("radio", { name: "Persona natural" })).toBeChecked();
    expect(screen.getByLabelText(/^Nombre o razón social/)).toHaveValue("Pedro Pérez");
    expect(screen.getByLabelText(/^Cédula o RIF/)).toHaveValue("V-12345678");
    expect(screen.getByLabelText(/^Domicilio o residencia/)).toHaveValue(
      "Avenida Siempre Viva 742",
    );
    expect(screen.getByLabelText(/^Recursos que proceden/)).toHaveValue(
      "No proceden recursos",
    );
  });

  it("DST-05 muestra el error del servidor en identificación y limpia el error local al escribir", async () => {
    const user = userEvent.setup();
    renderFormulario({
      erroresServidor: { identificacion: ["Ya existe"] },
    });

    expect(screen.getByText("Ya existe")).toBeInTheDocument();

    const campo = screen.getByLabelText(/^Cédula o RIF/);
    await user.type(campo, "1");
    expect(screen.getByText("Ya existe")).toBeInTheDocument();
  });

  it("DST-08: muestra el error de longitud al confirmar sin datos y lo limpia al escribir", async () => {
    const user = userEvent.setup();
    renderFormulario();

    await user.click(screen.getByRole("button", { name: "Agregar" }));
    expect(await screen.findByText("Debe tener entre 5 y 20 caracteres")).toBeInTheDocument();

    await user.type(screen.getByLabelText(/^Cédula o RIF/), "V-1234");
    expect(screen.queryByText("Debe tener entre 5 y 20 caracteres")).not.toBeInTheDocument();
  });

  it("DST-06 llama onCancelar al pulsar Cancelar", async () => {
    const user = userEvent.setup();
    const { onCancelar } = renderFormulario();

    await user.click(screen.getByRole("button", { name: "Cancelar" }));

    expect(onCancelar).toHaveBeenCalledTimes(1);
  });

  it("DST-07 la ayuda de Recursos que proceden contiene el texto con comillas dobles", () => {
    renderFormulario();

    expect(
      screen.getByText(/"No proceden recursos"/, { exact: false }),
    ).toBeInTheDocument();
  });
});
