import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { IntentoEntrada, Notificacion } from "@/modules/gobierno/api";
import type { DocumentSummary } from "@/modules/documentos/types";
import { RegistrarIntento } from "./RegistrarIntento";

const apiFetch = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

vi.mock("@/lib/fecha-de-negocio", async (original) => ({
  ...(await original<typeof import("@/lib/fecha-de-negocio")>()),
  hoyDeNegocio: () => "2026-10-30",
}));

const selectOficio = () =>
  screen.getByLabelText(/^Oficio de notificación/) as HTMLSelectElement;
const selectConstancia = (rotulo: RegExp) =>
  screen.getByLabelText(rotulo) as HTMLSelectElement;

function crearDocumento(
  id: string,
  title: string,
  status: DocumentSummary["status"] = "ACTIVE",
  document_number: string | null = null,
): DocumentSummary {
  return {
    id,
    company_id: "c1",
    document_type_id: `dt-${id}`,
    title,
    document_number,
    issuer: null,
    issued_at: null,
    expiration_date: null,
    is_expired: false,
    status,
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
  };
}

const DOCUMENTOS: DocumentSummary[] = [
  crearDocumento("d1", "Oficio 1"),
  crearDocumento("d2", "Recibo 1"),
  crearDocumento("d3", "Acta 1"),
  crearDocumento("d9", "Inactivo", "ARCHIVED"),
];

function crearNotificacion(
  documentoOficioId: string | null = null,
  intentos: Notificacion["intentos"] = [],
): Notificacion {
  return {
    id: "n1",
    acto: {
      id: "acto-1",
      tipo: "RESOLUCION",
      denominacion_tipo: null,
      numero: "DA-010-2026",
      fecha: "2026-03-10",
      estado: "EMITIDO",
    },
    tipo_persona: "NATURAL",
    nombre: "Pedro Pérez",
    identificacion: "V-7654321",
    domicilio: "Calle 1",
    apoderado_nombre: null,
    apoderado_identificacion: null,
    recursos: "Reconsideración en 15 días hábiles",
    documento_oficio_id: documentoOficioId,
    estado: "PENDIENTE",
    fecha_notificacion: null,
    medio_notificacion: null,
    motivo_anulacion: null,
    intentos,
    puede_publicar_en_prensa: true,
    version: 1,
    creado_en: "2026-03-10T00:00:00Z",
  };
}

function renderizar(
  notificacion: Notificacion,
  modo: "ENTREGADA" | "FALLIDA" | "PRENSA",
  propsAdicionales: Partial<{
    onConfirmar: (datos: IntentoEntrada) => Promise<void>;
    onCancelar: () => void;
    erroresServidor: Record<string, string[]>;
  }> = {},
) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const onConfirmar = vi.fn().mockResolvedValue(undefined);
  const onCancelar = vi.fn();
  const erroresServidor = propsAdicionales.erroresServidor ?? {};

  const vista = render(
    <QueryClientProvider client={queryClient}>
      <RegistrarIntento
        notificacion={notificacion}
        modo={modo}
        onConfirmar={propsAdicionales.onConfirmar ?? onConfirmar}
        onCancelar={propsAdicionales.onCancelar ?? onCancelar}
        erroresServidor={erroresServidor}
      />
    </QueryClientProvider>,
  );

  return { vista, onConfirmar, onCancelar };
}

describe("RegistrarIntento", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiFetch.mockResolvedValue(DOCUMENTOS);
  });

  it("INT-01 muestra la forma de entrega personal con títulos y rótulos", async () => {
    const notificacion = crearNotificacion();
    renderizar(notificacion, "ENTREGADA");

    expect(
      await screen.findByRole("heading", { level: 3 }),
    ).toHaveTextContent("Registrar la entrega personal a Pedro Pérez");

    expect(screen.getByText(/^Fecha de la entrega/)).toBeInTheDocument();
    expect(screen.getByText(/^Oficio de notificación/)).toBeInTheDocument();
    expect(screen.getByText(/^Recibo firmado/)).toBeInTheDocument();
    expect(screen.getByText(/^Recibido por/)).toBeInTheDocument();
    expect(screen.getByText(/^Cédula de quien recibe/)).toBeInTheDocument();
  });

  it("INT-02 entrega válida invoca onConfirmar con los datos de ENTREGADA", async () => {
    const notificacion = crearNotificacion();
    const { onConfirmar } = renderizar(notificacion, "ENTREGADA");

    fireEvent.change(screen.getByLabelText(/^Fecha de la entrega/), {
      target: { value: "2026-10-29" },
    });

    await within(selectOficio()).findByRole("option", { name: "Oficio 1" });
    await userEvent.selectOptions(selectOficio(), "d1");

    await within(selectConstancia(/^Recibo firmado/)).findByRole("option", {
      name: "Recibo 1",
    });
    await userEvent.selectOptions(selectConstancia(/^Recibo firmado/), "d2");

    await userEvent.type(screen.getByLabelText(/^Recibido por/), "María Gil");
    await userEvent.type(
      screen.getByLabelText(/^Cédula de quien recibe/),
      "V-7654321",
    );

    await userEvent.click(
      screen.getByRole("button", { name: "Registrar entrega" }),
    );

    expect(onConfirmar).toHaveBeenCalledWith({
      medio: "PERSONAL",
      resultado: "ENTREGADA",
      fecha: "2026-10-29",
      documento_oficio_id: "d1",
      documento_id: "d2",
      receptor_nombre: "María Gil",
      receptor_identificacion: "V-7654321",
      motivo_fallo: null,
      diario: null,
      referencia: null,
    });
  });

  it("INT-03 pide oficio y constancia y no llama si faltan", async () => {
    const notificacion = crearNotificacion();
    const { onConfirmar } = renderizar(notificacion, "ENTREGADA");

    fireEvent.change(screen.getByLabelText(/^Fecha de la entrega/), {
      target: { value: "2026-10-29" },
    });
    await userEvent.type(screen.getByLabelText(/^Recibido por/), "María Gil");
    await userEvent.type(
      screen.getByLabelText(/^Cédula de quien recibe/),
      "V-7654321",
    );

    await userEvent.click(
      screen.getByRole("button", { name: "Registrar entrega" }),
    );

    expect(screen.getByText("Seleccione el oficio")).toBeInTheDocument();
    expect(screen.getByText("Seleccione la constancia")).toBeInTheDocument();
    expect(onConfirmar).not.toHaveBeenCalled();
  });

  it("INT-04 al elegir d1 como oficio desaparece de constancia y al cambiar oficio a d2 vacía la constancia", async () => {
    const notificacion = crearNotificacion();
    renderizar(notificacion, "ENTREGADA");

    await within(selectOficio()).findByRole("option", { name: "Oficio 1" });
    await userEvent.selectOptions(selectOficio(), "d1");

    await within(selectConstancia(/^Recibo firmado/)).findByRole("option", {
      name: "Recibo 1",
    });
    await userEvent.selectOptions(selectConstancia(/^Recibo firmado/), "d2");

    expect(
      within(selectConstancia(/^Recibo firmado/)).queryByRole("option", {
        name: "Oficio 1",
      }),
    ).not.toBeInTheDocument();

    await userEvent.selectOptions(selectOficio(), "d2");
    const constancia = selectConstancia(/^Recibo firmado/);
    expect(constancia.value).toBe("");
    expect(
      within(constancia).queryByRole("option", { name: "Recibo 1" }),
    ).not.toBeInTheDocument();
  });

  it("INT-10 al convertir la constancia en oficio no se envía documento_id de oficio", async () => {
    const notificacion = crearNotificacion();
    const { onConfirmar } = renderizar(notificacion, "ENTREGADA");

    await within(selectOficio()).findByRole("option", { name: "Oficio 1" });
    await userEvent.selectOptions(selectOficio(), "d1");

    await within(selectConstancia(/^Recibo firmado/)).findByRole("option", {
      name: "Recibo 1",
    });
    await userEvent.selectOptions(selectConstancia(/^Recibo firmado/), "d2");

    await userEvent.selectOptions(selectOficio(), "d2");

    fireEvent.change(screen.getByLabelText(/^Fecha de la entrega/), {
      target: { value: "2026-10-29" },
    });

    await userEvent.type(screen.getByLabelText(/^Recibido por/), "María Gil");
    await userEvent.type(
      screen.getByLabelText(/^Cédula de quien recibe/),
      "V-7654321",
    );

    await userEvent.click(
      screen.getByRole("button", { name: "Registrar entrega" }),
    );

    expect(await screen.findByText("Seleccione la constancia")).toBeInTheDocument();
    expect(onConfirmar).not.toHaveBeenCalled();
  });

  it("INT-05 rechaza fechas antes del acto y futuras", async () => {
    const notificacion = crearNotificacion();
    renderizar(notificacion, "ENTREGADA");

    const fecha = screen.getByLabelText(/^Fecha de la entrega/);

    fireEvent.change(fecha, { target: { value: "2026-03-09" } });
    await userEvent.click(
      screen.getByRole("button", { name: "Registrar entrega" }),
    );
    expect(
      screen.getByText("La fecha no puede ser anterior a la fecha del acto"),
    ).toBeInTheDocument();

    fireEvent.change(fecha, { target: { value: "2026-10-31" } });
    await userEvent.click(
      screen.getByRole("button", { name: "Registrar entrega" }),
    );
    expect(
      screen.getByText("La fecha no puede ser posterior a hoy"),
    ).toBeInTheDocument();
  });

  it("INT-06 intento fallido valida motivo y envía resultado FALLIDA", async () => {
    const notificacion = crearNotificacion();
    const { onConfirmar } = renderizar(notificacion, "FALLIDA");

    expect(screen.getByText(/^Fecha del intento/)).toBeInTheDocument();
    expect(
      screen.getByText(/^Motivo del intento fallido/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/^Constancia del intento/),
    ).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/^Fecha del intento/), {
      target: { value: "2026-10-29" },
    });

    await within(selectOficio()).findByRole("option", { name: "Oficio 1" });
    await userEvent.selectOptions(selectOficio(), "d1");

    await within(selectConstancia(/^Constancia del intento/)).findByRole(
      "option",
      { name: "Recibo 1" },
    );
    await userEvent.selectOptions(
      selectConstancia(/^Constancia del intento/),
      "d2",
    );

    await userEvent.type(
      screen.getByLabelText(/^Motivo del intento fallido/),
      "abc",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Registrar intento fallido" }),
    );
    expect(
      screen.getByText("Debe tener entre 5 y 500 caracteres"),
    ).toBeInTheDocument();

    const motivo = "Dirección cerrada";
    await userEvent.clear(
      screen.getByLabelText(/^Motivo del intento fallido/),
    );
    await userEvent.type(
      screen.getByLabelText(/^Motivo del intento fallido/),
      `${motivo}   `,
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Registrar intento fallido" }),
    );

    expect(onConfirmar).toHaveBeenCalledWith({
      medio: "PERSONAL",
      resultado: "FALLIDA",
      fecha: "2026-10-29",
      documento_oficio_id: "d1",
      documento_id: "d2",
      receptor_nombre: null,
      receptor_identificacion: null,
      motivo_fallo: motivo,
      diario: null,
      referencia: null,
    });
  });

  it("INT-07 modo prensa fija el oficio y muestra constancias y fecha calculada", async () => {
    const notificacion = crearNotificacion("d1", [
      {
        numero: 1,
        medio: "PERSONAL",
        resultado: "FALLIDA",
        fecha: "2026-10-01",
        documento_id: "d3",
        receptor_nombre: null,
        receptor_identificacion: null,
        motivo_fallo: "No atendió",
        diario: null,
        referencia: null,
        registrado_por: null,
        creado_en: "2026-10-01T00:00:00Z",
      },
    ]);
    const { onConfirmar } = renderizar(notificacion, "PRENSA");

    expect(screen.getByText(/^Fecha de la publicación/)).toBeInTheDocument();
    expect(screen.getByText("Diario")).toBeInTheDocument();
    expect(screen.getByText(/^Edición o referencia/)).toBeInTheDocument();

    const oficio = selectOficio();
    expect(oficio).toBeDisabled();
    await waitFor(() => expect(oficio).toHaveValue("d1"));
    expect(
      screen.getByText("El oficio quedó fijado en el primer intento"),
    ).toBeInTheDocument();

    const constancia = selectConstancia(/^Ejemplar del diario/);
    await within(constancia).findByRole("option", { name: "Recibo 1" });
    expect(
      within(constancia).queryByRole("option", { name: "Oficio 1" }),
    ).not.toBeInTheDocument();
    expect(
      within(constancia).queryByRole("option", { name: "Acta 1" }),
    ).not.toBeInTheDocument();
    expect(
      within(constancia).getByRole("option", { name: "Recibo 1" }),
    ).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/^Fecha de la publicación/), {
      target: { value: "2026-10-01" },
    });
    expect(
      screen.getByText("Se entenderá notificada el 16/10/2026."),
    ).toBeInTheDocument();

    await userEvent.selectOptions(
      selectConstancia(/^Ejemplar del diario/),
      "d2",
    );
    await userEvent.type(screen.getByLabelText(/^Diario/), "Diario de prueba");
    await userEvent.type(
      screen.getByLabelText(/^Edición o referencia/),
      "Ed. 123",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Registrar publicación" }),
    );

    expect(onConfirmar).toHaveBeenCalledWith({
      medio: "PRENSA",
      resultado: "PUBLICADA",
      fecha: "2026-10-01",
      documento_oficio_id: "d1",
      documento_id: "d2",
      receptor_nombre: null,
      receptor_identificacion: null,
      motivo_fallo: null,
      diario: "Diario de prueba",
      referencia: "Ed. 123",
    });
  });

  it("INT-08a sin documentos válidos muestra aviso y deshabilita el botón", async () => {
    apiFetch.mockResolvedValue([]);
    const notificacion = crearNotificacion();
    renderizar(notificacion, "ENTREGADA");

    await screen.findByText(
      "Adjunte primero el oficio y la constancia en «Oficio y constancias».",
    );
    expect(
      screen.getByRole("button", { name: "Registrar entrega" }),
    ).toBeDisabled();
  });

  it("INT-08b con un solo documento y sin oficio fijado deshabilita el botón", async () => {
    apiFetch.mockResolvedValue([
      crearDocumento("d1", "Oficio 1"),
      crearDocumento("d2", "Recibo 1", "ARCHIVED"),
      crearDocumento("d9", "Inactivo", "ARCHIVED"),
    ]);

    const notificacionCorta = crearNotificacion();
    renderizar(notificacionCorta, "ENTREGADA");

    await within(selectOficio()).findByRole("option", { name: "Oficio 1" });
    expect(
      screen.getByRole("button", { name: "Registrar entrega" }),
    ).toBeDisabled();
  });

  it("INT-09 muestra errores de servidor para documento_id", async () => {
    const notificacion = crearNotificacion();
    renderizar(notificacion, "ENTREGADA", {
      erroresServidor: {
        documento_id: [
          "La constancia debe ser un documento distinto del oficio",
        ],
      },
    });

    expect(
      await screen.findByText(
        "La constancia debe ser un documento distinto del oficio",
      ),
    ).toBeInTheDocument();
  });
});
