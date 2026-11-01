import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi, type Mock } from "vitest";

import {
  Acto,
  Autoridad,
  ETIQUETA_ACCION,
  ETIQUETA_MATERIA,
  ListaAutoridades,
} from "@/modules/gobierno/api";

const apiFetch = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

vi.mock("@/lib/fecha-de-negocio", async (original) => ({
  ...(await original<typeof import("@/lib/fecha-de-negocio")>()),
  hoyDeNegocio: () => "2026-10-30",
}));

const { ActoFormulario } = await import("./ActoFormulario");

function crearQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

const P1: Autoridad = {
  cargo_id: "p1-cargo",
  codigo: "DIR-ADM",
  denominacion: "Dirección de Administración",
  unidad_codigo: "DA",
  unidad_denominacion: "Dirección de Administración",
  estado: "VIGENTE",
  competencias: [
    { accion: "APROBAR", materia: "CONTRATACIONES" },
    { accion: "APROBAR", materia: "TESORERIA" },
  ],
};

const P2: Autoridad = {
  cargo_id: "p2-cargo",
  codigo: "ALC",
  denominacion: "Alcalde",
  unidad_codigo: "DESP",
  unidad_denominacion: "Despacho",
  estado: "VIGENTE",
  competencias: [{ accion: "APROBAR", materia: "PRESUPUESTO" }],
};

const LISTA_AUTORIDADES: ListaAutoridades = {
  fecha: "2026-10-30",
  items: [P1, P2],
};

const OPCION_P1 = `${P1.unidad_codigo} · ${P1.codigo} — ${P1.denominacion}`;
const OPCION_P2 = `${P2.unidad_codigo} · ${P2.codigo} — ${P2.denominacion}`;

const COMPETENCIA_P1_1 = `${ETIQUETA_ACCION.APROBAR} · ${ETIQUETA_MATERIA.CONTRATACIONES}`;
const COMPETENCIA_P1_2 = `${ETIQUETA_ACCION.APROBAR} · ${ETIQUETA_MATERIA.TESORERIA}`;
const COMPETENCIA_P2 = `${ETIQUETA_ACCION.APROBAR} · ${ETIQUETA_MATERIA.PRESUPUESTO}`;

type PropsActoFormulario = Parameters<typeof ActoFormulario>[0];

type RenderizarFormularioResult = ReturnType<typeof render> & {
  onGuardar: Mock;
  onCancelar: Mock;
};

function renderizarFormulario(
  props: Partial<PropsActoFormulario> = {},
): RenderizarFormularioResult {
  const queryClient = crearQueryClient();
  const onGuardar = vi.fn().mockResolvedValue(undefined);
  const onCancelar = vi.fn();

  const rendered = render(
    <QueryClientProvider client={queryClient}>
      <ActoFormulario
        modo="crear"
        onGuardar={onGuardar}
        onCancelar={onCancelar}
        erroresServidor={{}}
        {...props}
      />
    </QueryClientProvider>,
  );

  return {
    ...rendered,
    onGuardar,
    onCancelar,
  };
}

function crearActo(): Acto {
  return {
    id: "acto-1",
    tipo: "RESOLUCION",
    denominacion_tipo: null,
    numero: "DA-100-2026",
    fecha: "2026-10-30",
    lugar: "Caracas",
    cargo: {
      id: P1.cargo_id,
      codigo: P1.codigo,
      denominacion: P1.denominacion,
      unidad_codigo: P1.unidad_codigo,
      unidad_denominacion: P1.unidad_denominacion,
    },
    competencia: { accion: "APROBAR", materia: "CONTRATACIONES" },
    fundamento_competencia: "Reglamento interno, art. 12",
    funcionario: "Ana Pérez",
    titularidad: "TITULAR",
    delegacion_numero: null,
    delegacion_fecha: null,
    caracter: "PARTICULAR",
    simple_tramite: false,
    destinatario: null,
    asunto: "Designación del tesorero",
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
    creado_en: "2026-10-01T00:00:00Z",
  };
}

describe("ActoFormulario", () => {
  beforeEach(() => {
    apiFetch.mockReset();
    apiFetch.mockImplementation((url: string) => {
      if (url === "/gobierno/actos/autoridades?fecha=2026-10-30") {
        return Promise.resolve(LISTA_AUTORIDADES);
      }
      return Promise.reject(new Error(`URL no esperada: ${url}`));
    });
  });

  it("FRM-01 · crear: la fecha arranca en hoy de negocio, pide las autoridades de esa fecha y ofrece DA · DIR-ADM — Dirección de Administración", async () => {
    const { onGuardar } = renderizarFormulario();

    expect(screen.getByLabelText(/^Fecha del acto\b/)).toHaveValue(
      "2026-10-30",
    );

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/gobierno/actos/autoridades?fecha=2026-10-30",
      );
    });

    const cargoSelect = await screen.findByRole("combobox", {
      name: /^Cargo que lo dicta/,
    });
    expect(
      screen.getByRole("option", { name: OPCION_P1 }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: OPCION_P2 }),
    ).toBeInTheDocument();
    expect(cargoSelect).toHaveValue("");
    expect(onGuardar).not.toHaveBeenCalled();
  });

  it("FRM-02 · «Denominación» solo aparece con «Tipo de acto» = Otra decisión", async () => {
    renderizarFormulario();

    expect(
      screen.queryByLabelText(/^Denominación/),
    ).not.toBeInTheDocument();

    await userEvent.selectOptions(
      screen.getByLabelText(/^Tipo de acto/),
      "OTRA_DECISION",
    );

    expect(screen.getByLabelText(/^Denominación/)).toBeInTheDocument();

    await userEvent.selectOptions(
      screen.getByLabelText(/^Tipo de acto/),
      "RESOLUCION",
    );

    expect(
      screen.queryByLabelText(/^Denominación/),
    ).not.toBeInTheDocument();
  });

  it("FRM-03 · «Competencia» ofrece solo las del cargo elegido y se vacía al cambiar de cargo", async () => {
    renderizarFormulario();

    const cargoSelect = await screen.findByRole("combobox", {
      name: /^Cargo que lo dicta/,
    });
    const competenciaSelect = screen.getByLabelText(/^Competencia/);

    expect(competenciaSelect).toBeDisabled();

    await screen.findByRole("option", {
      name: "DA · DIR-ADM — Dirección de Administración",
    });

    await userEvent.selectOptions(cargoSelect, P1.cargo_id);

    expect(
      screen.getByRole("option", { name: COMPETENCIA_P1_1 }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: COMPETENCIA_P1_2 }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("option", { name: COMPETENCIA_P2 }),
    ).not.toBeInTheDocument();

    await userEvent.selectOptions(
      competenciaSelect,
      `${P1.competencias[0].accion}|${P1.competencias[0].materia}`,
    );
    expect(competenciaSelect).toHaveValue(
      `${P1.competencias[0].accion}|${P1.competencias[0].materia}`,
    );

    await userEvent.selectOptions(cargoSelect, P2.cargo_id);

    expect(competenciaSelect).toHaveValue("");
    expect(
      screen.getByRole("option", { name: COMPETENCIA_P2 }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("option", { name: COMPETENCIA_P1_1 }),
    ).not.toBeInTheDocument();
  });

  it("FRM-04 · los campos de delegación aparecen solo con Titularidad = Delegación y una fecha posterior a la del acto da error", async () => {
    const { onGuardar } = renderizarFormulario();

    expect(
      screen.queryByLabelText(/^Nº del acto de delegación/),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText(/^Fecha del acto de delegación/),
    ).not.toBeInTheDocument();

    await userEvent.selectOptions(
      screen.getByLabelText(/^Titularidad/),
      "DELEGACION",
    );

    const delegacionNumero = screen.getByLabelText(
      /^Nº del acto de delegación/,
    );
    const delegacionFecha = screen.getByLabelText(
      /^Fecha del acto de delegación/,
    );

    await userEvent.type(delegacionNumero, "RES-DEL-01");
    fireEvent.change(delegacionFecha, { target: { value: "2026-10-31" } });

    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));

    expect(
      screen.getByText(
        "La fecha de delegación no puede ser posterior a la fecha del acto",
      ),
    ).toBeInTheDocument();
    expect(onGuardar).not.toHaveBeenCalled();
  });

  it("FRM-05 · «De simple trámite» aparece solo con carácter Particular", async () => {
    renderizarFormulario();

    expect(
      screen.queryByLabelText(/^De simple trámite/),
    ).not.toBeInTheDocument();

    await userEvent.click(
      screen.getByRole("radio", { name: "Particular (se notifica)" }),
    );

    expect(
      screen.getByLabelText(/^De simple trámite/),
    ).toBeInTheDocument();

    await userEvent.click(
      screen.getByRole("radio", { name: "General (se publica)" }),
    );

    expect(
      screen.queryByLabelText(/^De simple trámite/),
    ).not.toBeInTheDocument();
  });

  it("FRM-06 · alta completa normaliza los datos y llama onGuardar con el objeto exacto", async () => {
    const { onGuardar } = renderizarFormulario();

    const cargoSelect = await screen.findByRole("combobox", {
      name: /^Cargo que lo dicta/,
    });

    await userEvent.selectOptions(
      screen.getByLabelText(/^Tipo de acto/),
      "RESOLUCION",
    );
    await userEvent.type(screen.getByLabelText(/^Número/), "DA-100-2026");
    await userEvent.type(screen.getByLabelText(/^Lugar/), "  Caracas  ");
    await userEvent.selectOptions(cargoSelect, P1.cargo_id);
    await userEvent.selectOptions(
      screen.getByLabelText(/^Competencia/),
      "APROBAR|CONTRATACIONES",
    );
    await userEvent.type(
      screen.getByLabelText(/^Fundamento de la competencia/),
      "Reglamento interno, art. 12",
    );
    await userEvent.type(
      screen.getByLabelText(/^Funcionario que suscribe/),
      "Ana Pérez",
    );
    await userEvent.selectOptions(
      screen.getByLabelText(/^Titularidad/),
      "TITULAR",
    );
    await userEvent.click(
      screen.getByRole("radio", { name: "Particular (se notifica)" }),
    );
    await userEvent.type(
      screen.getByLabelText(/^Asunto/),
      "Designación del tesorero",
    );

    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));

    expect(onGuardar).toHaveBeenCalledWith({
      tipo: "RESOLUCION",
      denominacion_tipo: null,
      numero: "DA-100-2026",
      fecha: "2026-10-30",
      lugar: "Caracas",
      cargo_id: P1.cargo_id,
      competencia: { accion: "APROBAR", materia: "CONTRATACIONES" },
      fundamento_competencia: "Reglamento interno, art. 12",
      funcionario: "Ana Pérez",
      titularidad: "TITULAR",
      delegacion_numero: null,
      delegacion_fecha: null,
      caracter: "PARTICULAR",
      simple_tramite: false,
      destinatario: null,
      asunto: "Designación del tesorero",
      hechos: null,
      fundamentos: null,
      decision: null,
    });
  });

  it("FRM-07 · una fecha posterior a hoy da error real bajo el campo y no llama onGuardar", async () => {
    const { onGuardar } = renderizarFormulario();

    const fechaInput = screen.getByLabelText(/^Fecha del acto\b/);
    fireEvent.change(fechaInput, { target: { value: "2026-10-31" } });

    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));

    expect(
      screen.getByText("La fecha del acto no puede ser posterior a hoy"),
    ).toBeInTheDocument();
    expect(fechaInput).toHaveAttribute("aria-invalid", "true");
    expect(onGuardar).not.toHaveBeenCalled();
  });

  it("FRM-08 · un número vacío muestra el error real bajo «Número» y no llama onGuardar", async () => {
    const { onGuardar } = renderizarFormulario();

    const numeroInput = screen.getByLabelText(/^Número/);

    await userEvent.clear(numeroInput);

    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));

    expect(
      screen.getByText("El número debe tener entre 1 y 60 caracteres"),
    ).toBeInTheDocument();
    expect(numeroInput).toHaveAttribute("aria-invalid", "true");
    expect(onGuardar).not.toHaveBeenCalled();
  });

  it("FRM-09 · editar: los campos arrancan con los valores del acto y solo cambia «Asunto»", async () => {
    const acto = crearActo();

    const { onGuardar } = renderizarFormulario({ modo: "editar", acto });

    await screen.findByRole("combobox", { name: /^Cargo que lo dicta/ });

    expect(screen.getByLabelText(/^Tipo de acto/)).toHaveValue("RESOLUCION");
    expect(screen.getByLabelText(/^Número/)).toHaveValue("DA-100-2026");
    expect(screen.getByLabelText(/^Fecha del acto\b/)).toHaveValue(
      "2026-10-30",
    );
    expect(screen.getByLabelText(/^Lugar/)).toHaveValue("Caracas");
    expect(
      screen.getByLabelText(/^Fundamento de la competencia/),
    ).toHaveValue("Reglamento interno, art. 12");
    expect(
      screen.getByLabelText(/^Funcionario que suscribe/),
    ).toHaveValue("Ana Pérez");
    expect(screen.getByLabelText(/^Titularidad/)).toHaveValue("TITULAR");
    expect(screen.getByLabelText(/^Asunto/)).toHaveValue(
      "Designación del tesorero",
    );

    const asuntoInput = screen.getByLabelText(/^Asunto/);
    await userEvent.clear(asuntoInput);
    await userEvent.type(
      asuntoInput,
      "Designación de la nueva tesorera municipal",
    );

    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));

    expect(onGuardar).toHaveBeenCalledWith({
      asunto: "Designación de la nueva tesorera municipal",
    });
  });

  it("FRM-10 · editar sin cambios muestra «No hay cambios que guardar» y no llama onGuardar", async () => {
    const acto = crearActo();

    const { onGuardar } = renderizarFormulario({ modo: "editar", acto });

    await screen.findByRole("combobox", { name: /^Cargo que lo dicta/ });
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));

    expect(screen.getByRole("status")).toHaveTextContent(
      "No hay cambios que guardar",
    );
    expect(onGuardar).not.toHaveBeenCalled();
  });

  it("FRM-11 · autoridades vacías muestran el aviso de que no hay cargos vigentes", async () => {
    apiFetch.mockResolvedValue({ fecha: "2026-10-30", items: [] });

    renderizarFormulario();

    expect(
      await screen.findByText(
        "No hay cargos vigentes en esa fecha. Revise Gobierno › Cargos y competencias.",
      ),
    ).toBeInTheDocument();
  });

  it("FRM-12 · los errores del servidor de número y competencia se muestran bajo sus campos", async () => {
    const acto = crearActo();

    renderizarFormulario({
      modo: "editar",
      acto,
      erroresServidor: {
        numero: ["Ya existe un acto con este cargo, tipo y número"],
        competencia: ["La competencia no corresponde al cargo"],
      },
    });

    await screen.findByRole("combobox", { name: /^Cargo que lo dicta/ });

    expect(
      screen.getByText(
        "Ya existe un acto con este cargo, tipo y número",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText("La competencia no corresponde al cargo"),
    ).toBeInTheDocument();
  });

  it("FRM-13 · «Cancelar» llama onCancelar", async () => {
    const { onCancelar } = renderizarFormulario();

    await userEvent.click(screen.getByRole("button", { name: "Cancelar" }));

    expect(onCancelar).toHaveBeenCalledTimes(1);
  });

  it("FRM-14 · al cambiar de cargo la competencia elegida no viaja", async () => {
    const { onGuardar } = renderizarFormulario();

    const cargoSelect = await screen.findByRole("combobox", {
      name: /^Cargo que lo dicta/,
    });

    await screen.findByRole("option", {
      name: "DA · DIR-ADM — Dirección de Administración",
    });

    await userEvent.selectOptions(
      screen.getByLabelText(/^Tipo de acto/),
      "RESOLUCION",
    );
    await userEvent.type(screen.getByLabelText(/^Número/), "DA-100-2026");
    await userEvent.type(screen.getByLabelText(/^Lugar/), "  Caracas  ");
    await userEvent.selectOptions(cargoSelect, P1.cargo_id);
    await userEvent.selectOptions(
      screen.getByLabelText(/^Competencia/),
      "APROBAR|CONTRATACIONES",
    );
    await userEvent.type(
      screen.getByLabelText(/^Fundamento de la competencia/),
      "Reglamento interno, art. 12",
    );
    await userEvent.type(
      screen.getByLabelText(/^Funcionario que suscribe/),
      "Ana Pérez",
    );
    await userEvent.selectOptions(
      screen.getByLabelText(/^Titularidad/),
      "TITULAR",
    );
    await userEvent.click(
      screen.getByRole("radio", { name: "Particular (se notifica)" }),
    );
    await userEvent.type(
      screen.getByLabelText(/^Asunto/),
      "Designación del tesorero",
    );

    await userEvent.selectOptions(cargoSelect, P2.cargo_id);

    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));

    expect(
      screen.getAllByRole("alert").some((n) => n.textContent === "Seleccione la competencia"),
    ).toBe(true);
    expect(onGuardar).not.toHaveBeenCalled();
  });
});
