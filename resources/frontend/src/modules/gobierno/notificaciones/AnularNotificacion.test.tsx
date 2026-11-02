import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Notificacion } from "@/modules/gobierno/api";
import { AnularNotificacion } from "./AnularNotificacion";

const apiFetch = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

vi.mock("@/lib/fecha-de-negocio", async (original) => ({
  ...(await original<typeof import("@/lib/fecha-de-negocio")>()),
  hoyDeNegocio: () => "2026-10-30",
}));

const NOTIFICACION_MINIMA: Notificacion = {
  id: "not-1",
  acto: { id: "a1", tipo: "RESOLUCION", denominacion_tipo: null, numero: "DA-001-2026", fecha: "2026-03-10", estado: "EMITIDO" },
  tipo_persona: "NATURAL",
  nombre: "Pedro Pérez",
  identificacion: "V-12345678",
  domicilio: "Calle 1",
  apoderado_nombre: null,
  apoderado_identificacion: null,
  recursos: "Reconsideración en 15 días hábiles",
  documento_oficio_id: null,
  estado: "PENDIENTE",
  fecha_notificacion: null,
  medio_notificacion: null,
  motivo_anulacion: null,
  intentos: [],
  puede_publicar_en_prensa: false,
  version: 1,
  creado_en: "2026-03-10T12:00:00Z",
};

function renderFormulario(props: Partial<Parameters<typeof AnularNotificacion>[0]> = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const onConfirmar = vi.fn().mockResolvedValue(undefined);
  const onCancelar = vi.fn();
  const erroresServidor: Record<string, string[]> = props.erroresServidor ?? {};

  const ui = (
    <QueryClientProvider client={queryClient}>
      <AnularNotificacion
        notificacion={NOTIFICACION_MINIMA}
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

describe("AnularNotificacion", () => {
  beforeEach(() => {
    apiFetch.mockReset();
  });

  it("ANU-01 muestra el título con el nombre de la notificación y el aviso de eficacia", () => {
    renderFormulario();

    expect(
      screen.getByRole("heading", {
        level: 3,
        name: "Anular la notificación de Pedro Pérez",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "La notificación anulada deja de contar para la eficacia del acto.",
      ),
    ).toBeInTheDocument();
  });

  it("ANU-02 muestra error cuando el motivo tiene menos de 5 caracteres y no confirma", async () => {
    const user = userEvent.setup();
    const { onConfirmar } = renderFormulario();

    await user.type(screen.getByLabelText(/^Motivo de la anulación/), "Test");
    await user.click(screen.getByRole("button", { name: "Anular notificación" }));

    expect(screen.getByText("Debe tener entre 5 y 255 caracteres")).toBeInTheDocument();
    expect(onConfirmar).not.toHaveBeenCalled();
  });

  it("ANU-03 recorta el motivo con espacios alrededor y llama onConfirmar", async () => {
    const user = userEvent.setup();
    const { onConfirmar } = renderFormulario();

    await user.type(
      screen.getByLabelText(/^Motivo de la anulación/),
      "  Registrado por error  ",
    );
    await user.click(screen.getByRole("button", { name: "Anular notificación" }));

    expect(onConfirmar).toHaveBeenCalledWith("Registrado por error");
  });

  it("ANU-04 muestra el error de servidor y llama onCancelar al pulsar Cancelar", async () => {
    const user = userEvent.setup();
    const { onCancelar } = renderFormulario({
      erroresServidor: { motivo: ["Campo obligatorio"] },
    });

    expect(screen.getByText("Campo obligatorio")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Cancelar" }));

    expect(onCancelar).toHaveBeenCalledTimes(1);
  });
});
