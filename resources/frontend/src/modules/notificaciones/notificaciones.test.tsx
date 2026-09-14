/** Pantallas y utilidades de la Spec 047. */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { destinoDeEnlace, etiquetaCategoria, textoDeMensaje, type Enlace } from "./api";

const apiFetch = vi.fn();
let empresaActiva: string | null = "aaa";

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));
vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({ activeCompanyId: empresaActiva }),
}));

const { NotificationBell } = await import("./NotificationBell");
const { esClaveDeEmpresa } = await import("@/app/company/queryScope");

function montar(elemento: React.ReactNode): QueryClient {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>{elemento}</MemoryRouter>
    </QueryClientProvider>,
  );
  return qc;
}

describe("textoDeMensaje", () => {
  it("un mensaje que el servidor no pudo componer nunca muestra la clave cruda", () => {
    const texto = textoDeMensaje({ key: "approval.x", params: {}, text: null, render_error: "MESSAGE_KEY_UNKNOWN" });
    expect(texto).toBe("Mensaje no disponible");
    expect(texto).not.toContain("approval.x");
  });
});

describe("destinoDeEnlace", () => {
  const enlace = (route_key: string): Enlace => ({
    source_type: "ApprovalRequest", source_id: "r-1", source_item_id: null, route_key,
  });

  it("lleva la aprobación a su bandeja y exige su permiso", () => {
    expect(destinoDeEnlace(enlace("approval_inbox"))).toEqual({
      ruta: "/aprobaciones/bandeja", permiso: "aprobaciones:view",
    });
  });

  it("una ruta desconocida no se inventa", () => {
    expect(destinoDeEnlace(enlace("desconocida"))).toBeNull();
  });
});

describe("etiquetaCategoria", () => {
  it("traduce las categorías conocidas y deja el código en las demás", () => {
    expect(etiquetaCategoria("task.reminder")).toBe("Recordatorio de tarea");
    expect(etiquetaCategoria("otra.cosa")).toBe("otra.cosa");
  });
});

describe("NotificationBell", () => {
  beforeEach(() => {
    apiFetch.mockReset();
    empresaActiva = "aaa";
  });

  it("muestra el número que cuenta el servidor, sin traer la lista", async () => {
    apiFetch.mockResolvedValue({ unread_notifications: 3, open_tasks: 0, overdue_tasks: 0, active_alerts: 0 });
    montar(<NotificationBell />);
    expect(await screen.findByLabelText("Notificaciones sin leer: 3")).toBeInTheDocument();
    expect(screen.getByTestId("campana-contador")).toHaveTextContent("3");
    expect(apiFetch).toHaveBeenCalledWith("/notifications/counts");
    expect(apiFetch.mock.calls.every(([ruta]) => !String(ruta).startsWith("/notifications?"))).toBe(true);
  });

  it("sin nada por leer no pinta el contador", async () => {
    apiFetch.mockResolvedValue({ unread_notifications: 0, open_tasks: 0, overdue_tasks: 0, active_alerts: 0 });
    montar(<NotificationBell />);
    expect(await screen.findByLabelText("Notificaciones sin leer: 0")).toBeInTheDocument();
    expect(screen.queryByTestId("campana-contador")).toBeNull();
  });

  it("sobrevive a la purga de consultas que hace el shell al cambiar de empresa", async () => {
    // `AppShell` cancela y retira las consultas de empresa en un efecto del padre,
    // que corre **después** del efecto con el que la campana ya pidió sus datos.
    let responder: (valor: unknown) => void = () => undefined;
    apiFetch.mockImplementationOnce(() => new Promise((r) => { responder = r; }));
    apiFetch.mockResolvedValue({ unread_notifications: 3, open_tasks: 0, overdue_tasks: 0, active_alerts: 0 });
    const qc = montar(<NotificationBell />);
    await waitFor(() => expect(apiFetch).toHaveBeenCalledTimes(1));
    await act(async () => {
      void qc.cancelQueries({ predicate: (q) => esClaveDeEmpresa(q.queryKey) });
      qc.removeQueries({ predicate: (q) => esClaveDeEmpresa(q.queryKey) });
      responder({ unread_notifications: 3, open_tasks: 0, overdue_tasks: 0, active_alerts: 0 });
    });
    expect(await screen.findByLabelText("Notificaciones sin leer: 3", {}, { timeout: 2000 })).toBeInTheDocument();
  });

  it("sin empresa activa no pregunta nada", () => {
    empresaActiva = null;
    montar(<NotificationBell />);
    expect(screen.queryByTestId("campana")).toBeNull();
    expect(apiFetch).not.toHaveBeenCalled();
  });
});
