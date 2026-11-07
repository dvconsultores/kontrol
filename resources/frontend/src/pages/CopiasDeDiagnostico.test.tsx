import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";

import type { BackupStatus } from "@/api/types";

const apiFetch = vi.fn();
const notify = vi.fn();

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify }),
}));

let puede = true;
vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({
    estado: "LISTA",
    tiene: () => true,
    puede: (metodo: string, ruta: string) => puede && metodo === "PUT" && ruta === "/system/backup-config",
    motivo: () => null,
    motivoDeCapacidad: () => null,
  }),
}));

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

const { CopiasDeDiagnostico, ESTADOS_RPO, edadLegible, etiquetaDeEstadoRpo, tamanoLegible } = await import("./CopiasDeDiagnostico");
const { ApiError } = await import("@/api/client");

const ESTADO: BackupStatus = {
  configured_rpo_minutes: 15,
  schedule_interval_minutes: 5,
  safety_margin_minutes: 2,
  retention_days: 30,
  retention_min_copies: 2,
  destination_type: "MOUNTED_FILESYSTEM",
  destination_label: "copia-segura",
  scheduler_enabled: true,
  version: 3,
  rpo_state: "RPO_CERTIFIED",
  last_successful_backup_at: "2025-01-01T10:00:00+00:00",
  last_valid_backup_at: "2025-01-01T09:00:00+00:00",
  last_valid_durable_off_host_backup_at: "2025-01-01T08:00:00+00:00",
  backup_age_seconds: 120,
  backup_duration_seconds: 45,
  package_size_bytes: 2_097_152,
  next_schedule_at: "2025-01-01T11:00:00+00:00",
  last_sanitized_error: null,
  retention_degraded: false,
  running: false,
};

function renderConProveedores(ui: ReactElement) {
  const queryClient = new QueryClient();
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("CopiasDeDiagnostico", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    puede = true;
  });

  it("pinta «Sin copia válida» para NO_VALID_BACKUP", () => {
    renderConProveedores(<CopiasDeDiagnostico estado={{ ...ESTADO, rpo_state: "NO_VALID_BACKUP" }} />);
    expect(screen.getByText("Sin copia válida")).toBeTruthy();
  });

  it.each(Object.entries(ESTADOS_RPO))("muestra la etiqueta para %s", (estado, { etiqueta }) => {
    renderConProveedores(<CopiasDeDiagnostico estado={{ ...ESTADO, rpo_state: estado }} />);
    expect(screen.getByText(etiqueta)).toBeTruthy();
  });

  it.each(["RPO_CERTIFIED", "RPO_MET"])("%s lleva clase de éxito", (estado) => {
    renderConProveedores(<CopiasDeDiagnostico estado={{ ...ESTADO, rpo_state: estado }} />);
    const span = screen.getByText(etiquetaDeEstadoRpo(estado));
    expect(span.className).toContain("bg-success-100");
    expect(span.className).toContain("text-success-600");
  });

  it.each(["LOCAL_ONLY", "RPO_AT_RISK", "DEGRADED"])("%s no lleva clase de éxito", (estado) => {
    renderConProveedores(<CopiasDeDiagnostico estado={{ ...ESTADO, rpo_state: estado }} />);
    const span = screen.getByText(etiquetaDeEstadoRpo(estado));
    expect(span.className).not.toContain("bg-success-100");
    expect(span.className).toContain("bg-danger-100");
  });

  it("código desconocido se muestra tal cual", () => {
    renderConProveedores(<CopiasDeDiagnostico estado={{ ...ESTADO, rpo_state: "DESCONOCIDO" }} />);
    expect(screen.getByText("DESCONOCIDO")).toBeTruthy();
  });

  it("muestra antigüedad, duración, tamaño y destino legibles", () => {
    renderConProveedores(<CopiasDeDiagnostico estado={ESTADO} />);
    expect(screen.getByText("2 min")).toBeTruthy();
    expect(screen.getByText("45 s")).toBeTruthy();
    expect(screen.getByText("2.0 MB")).toBeTruthy();
    expect(screen.getByText("copia-segura")).toBeTruthy();
  });

  it("sin copias muestra —, «Sin destino» y «Ninguno»", () => {
    const sinCopias = {
      ...ESTADO,
      rpo_state: "DISABLED",
      last_successful_backup_at: null,
      last_valid_backup_at: null,
      last_valid_durable_off_host_backup_at: null,
      backup_age_seconds: null,
      backup_duration_seconds: null,
      package_size_bytes: null,
      next_schedule_at: null,
      destination_label: null,
      last_sanitized_error: null,
    };
    renderConProveedores(<CopiasDeDiagnostico estado={sinCopias} />);
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
    expect(screen.getByText("Sin destino")).toBeTruthy();
    expect(screen.getByText("Ninguno")).toBeTruthy();
  });

  it("retención degradada muestra el aviso; «Copia en curso» si running", () => {
    renderConProveedores(<CopiasDeDiagnostico estado={{ ...ESTADO, retention_degraded: true, running: true }} />);
    expect(screen.getByText("La retención está degradada: revise el destino.")).toBeTruthy();
    expect(screen.getByText("Copia en curso")).toBeTruthy();
  });

  it("sin permiso no hay formulario y el estado sigue visible", () => {
    puede = false;
    renderConProveedores(<CopiasDeDiagnostico estado={ESTADO} />);
    expect(screen.queryByLabelText("RPO (minutos)")).toBeNull();
    expect(screen.getByText(etiquetaDeEstadoRpo(ESTADO.rpo_state))).toBeTruthy();
  });

  it("muestra el último error saneado", () => {
    renderConProveedores(<CopiasDeDiagnostico estado={{ ...ESTADO, last_sanitized_error: "PG_DUMP_FAILED" }} />);
    expect(screen.getByText("PG_DUMP_FAILED")).toBeTruthy();
    expect(screen.queryByText("Ninguno")).toBeNull();
  });

  it("con permiso sobre esa operación aparece el formulario", () => {
    renderConProveedores(<CopiasDeDiagnostico estado={ESTADO} />);
    expect(screen.getByLabelText("RPO (minutos)")).toBeTruthy();
  });

  it("no pinta ninguna ruta", () => {
    const { container } = renderConProveedores(<CopiasDeDiagnostico estado={ESTADO} />);
    expect(container.textContent).not.toContain("/data");
    expect(container.textContent).not.toContain("KONTROL");
  });

  it("guardar envía el cuerpo exacto con version", async () => {
    apiFetch.mockResolvedValue({});
    renderConProveedores(<CopiasDeDiagnostico estado={ESTADO} />);
    const boton = screen.getByRole("button", { name: "Guardar" });
    fireEvent.click(boton);
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/system/backup-config", {
      method: "PUT",
      body: {
        configured_rpo_minutes: 15,
        schedule_interval_minutes: 5,
        safety_margin_minutes: 2,
        retention_days: 30,
        retention_min_copies: 2,
        destination_label: "copia-segura",
        destination_type: "MOUNTED_FILESYSTEM",
        scheduler_enabled: true,
        version: 3,
      },
    }));
    await waitFor(() => expect(notify).toHaveBeenCalled());
  });

  it("campo vacío se envía como null", async () => {
    apiFetch.mockResolvedValue({});
    renderConProveedores(<CopiasDeDiagnostico estado={ESTADO} />);
    fireEvent.change(screen.getByLabelText("RPO (minutos)"), { target: { value: "" } });
    const boton = screen.getByRole("button", { name: "Guardar" });
    fireEvent.click(boton);
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/system/backup-config", expect.objectContaining({
      body: expect.objectContaining({ configured_rpo_minutes: null }),
    })));
  });

  it("BACKUP_POLICY_INVALID con RPO_ABOVE_MAXIMUM muestra su mensaje en role alert", async () => {
    apiFetch.mockRejectedValue(
      new ApiError(422, { code: "BACKUP_POLICY_INVALID", message: "x", details: { errors: ["RPO_ABOVE_MAXIMUM"] } })
    );
    renderConProveedores(<CopiasDeDiagnostico estado={ESTADO} />);
    const boton = screen.getByRole("button", { name: "Guardar" });
    fireEvent.click(boton);
    const alerta = await screen.findByRole("alert");
    expect(within(alerta).getByText("El RPO no puede superar 15 minutos.")).toBeTruthy();
  });

  it("VERSION_CONFLICT muestra su mensaje", async () => {
    apiFetch.mockRejectedValue(new ApiError(409, { code: "VERSION_CONFLICT", message: "x" }));
    renderConProveedores(<CopiasDeDiagnostico estado={ESTADO} />);
    const boton = screen.getByRole("button", { name: "Guardar" });
    fireEvent.click(boton);
    expect(await screen.findByText("Otra persona cambió la configuración: revise los datos.")).toBeTruthy();
  });

  it("edadLegible y tamanoLegible con sus límites", () => {
    expect(edadLegible(null)).toBe("—");
    expect(edadLegible(59)).toBe("59 s");
    expect(edadLegible(60)).toBe("1 min");
    expect(edadLegible(119)).toBe("1 min");
    expect(tamanoLegible(null)).toBe("—");
    expect(tamanoLegible(1023)).toBe("1023 B");
    expect(tamanoLegible(1024)).toBe("1.0 KB");
    expect(tamanoLegible(1_048_575)).toBe("1024.0 KB");
    expect(tamanoLegible(1_048_576)).toBe("1.0 MB");
  });
});
