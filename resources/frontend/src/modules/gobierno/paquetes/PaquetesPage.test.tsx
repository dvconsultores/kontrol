import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";

const apiFetchMock = vi.fn();
const notifyMock = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

let capacidades = new Set<string>();

vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({
    estado: "LISTA",
    tiene: (c: string) => capacidades.has(c),
    puede: () => true,
    motivo: () => null,
    motivoDeCapacidad: () => null,
  }),
}));

vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({ activeCompanyId: "c1", activeCompany: { id: "c1", legal_name: "Contenedor 1" } }),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: notifyMock }),
}));

const { PaquetesPage } = await import("./PaquetesPage");

const LISTADO = {
  total: 1,
  pagina: 1,
  por_pagina: 20,
  items: [
    {
      id: "p1",
      codigo: "PA-2026-0001",
      muestra_id: "m1",
      muestra_codigo: "MU-2026-0001",
      numero_generacion: 1,
      titulo: "Paquete de auditoría · Muestra",
      generado_por: "ua",
      generado_en: "2026-02-01T10:00:00Z",
      bytes: 4096,
      huella_paquete: "b".repeat(64),
      eventos: 2,
      documentos_incluidos: 1,
      documentos_excluidos: 1,
      hallazgos: 1,
    },
  ],
};

const VALIDO = {
  resultado: "VALIDO",
  motivos: [],
  paquete: { id: "p1", codigo: "PA-2026-0001" },
  huella_archivo: "c".repeat(64),
  bytes_archivo: 4096,
  identico: true,
  verificacion_id: "v1",
};

const INVALIDO = {
  resultado: "INVALIDO",
  motivos: [{ codigo: "ARCHIVO_ALTERADO", ruta: "documentos/d1-v1.pdf" }],
  paquete: { id: "p1", codigo: "PA-2026-0001" },
  huella_archivo: "d".repeat(64),
  bytes_archivo: 4096,
  identico: false,
  verificacion_id: "v2",
};

function renderizar(ruta: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[ruta]}>
        <Routes>
          <Route path="/gobierno/paquetes" element={<PaquetesPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiFetchMock.mockReset();
  notifyMock.mockReset();
  capacidades = new Set(["gobierno_paquetes:view"]);

  apiFetchMock.mockImplementation((url: string) => {
    if (url === "/gobierno/paquetes/verificar") {
      return Promise.resolve(VALIDO);
    }
    if (url === "/gobierno/paquetes" || url.startsWith("/gobierno/paquetes?")) {
      return Promise.resolve(LISTADO);
    }
    return Promise.reject(new ApiError(404, { code: "NOT_FOUND", message: "No encontrado" }));
  });
});

describe("PaquetesPage", () => {
  it("PQS-01 sin gobierno_paquetes:view muestra Sin acceso y oculta verificación", async () => {
    capacidades = new Set([]);
    renderizar("/gobierno/paquetes");

    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Verificar un paquete" })).toBeNull();
  });

  it("PQS-02 listado muestra enlace, métricas y código de muestra", async () => {
    renderizar("/gobierno/paquetes");

    const link = await screen.findByRole("link", { name: "Abrir el paquete PA-2026-0001" });
    expect(link).toHaveAttribute("href", "/gobierno/paquetes/p1");
    expect(screen.getByText("2 eventos · 1 documentos · 1 hallazgos")).toBeInTheDocument();
    expect(screen.getByText("MU-2026-0001")).toBeInTheDocument();
  });

  it("PQS-03 vacío muestra mensaje y mantiene el encabezado de verificación", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/paquetes/verificar") {
        return Promise.resolve(VALIDO);
      }
      if (url === "/gobierno/paquetes" || url.startsWith("/gobierno/paquetes?")) {
        return Promise.resolve({ total: 0, pagina: 1, por_pagina: 20, items: [] });
      }
      return Promise.reject(new ApiError(404, { code: "NOT_FOUND", message: "No encontrado" }));
    });

    renderizar("/gobierno/paquetes");

    expect(await screen.findByText("Aún no se ha generado ningún paquete")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Verificar un paquete" })).toBeInTheDocument();
  });

  it("PQS-04 verificar válido envía FormData y muestra estado con enlace", async () => {
    renderizar("/gobierno/paquetes");
    await screen.findByRole("link", { name: "Abrir el paquete PA-2026-0001" });

    const fichero = new File(["PK"], "paquete.zip", { type: "application/zip" });
    await userEvent.upload(screen.getByLabelText(/^Archivo del paquete/), fichero);
    await userEvent.click(screen.getByRole("button", { name: "Verificar" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/paquetes/verificar",
        expect.objectContaining({ method: "POST" }),
      );
    });

    const llamadaVerificar = apiFetchMock.mock.calls.find(
      (call) => call[0] === "/gobierno/paquetes/verificar",
    );
    expect(llamadaVerificar).toBeDefined();
    expect((llamadaVerificar?.[1] as { body: unknown }).body).toBeInstanceOf(FormData);

    const status = await screen.findByRole("status");
    expect(within(status).getByText(/Resultado: Válido/)).toBeInTheDocument();
    expect(
      within(status).getByText("La copia es idéntica byte a byte a la registrada."),
    ).toBeInTheDocument();
    expect(within(status).getByRole("link", { name: "PA-2026-0001" })).toBeInTheDocument();
  });

  it("PQS-05 verificar inválido muestra motivos y no contiene idéntica", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/paquetes/verificar") {
        return Promise.resolve(INVALIDO);
      }
      if (url === "/gobierno/paquetes" || url.startsWith("/gobierno/paquetes?")) {
        return Promise.resolve(LISTADO);
      }
      return Promise.reject(new ApiError(404, { code: "NOT_FOUND", message: "No encontrado" }));
    });

    renderizar("/gobierno/paquetes");
    await screen.findByRole("link", { name: "Abrir el paquete PA-2026-0001" });

    const fichero = new File(["PK"], "paquete.zip", { type: "application/zip" });
    await userEvent.upload(screen.getByLabelText(/^Archivo del paquete/), fichero);
    await userEvent.click(screen.getByRole("button", { name: "Verificar" }));

    const status = await screen.findByRole("status");
    expect(within(status).getByText(/Resultado: Inválido/)).toBeInTheDocument();
    expect(
      within(status).getByText("Archivo alterado · documentos/d1-v1.pdf"),
    ).toBeInTheDocument();
    expect(within(status).queryByText(/idéntica/)).toBeNull();
  });

  it("PQS-06 verificar 422 muestra alerta con el mensaje", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/paquetes/verificar") {
        return Promise.reject(
          new ApiError(422, {
            code: "GOV_PACKAGE_UPLOAD_INVALID",
            message: "El archivo no es un ZIP legible",
          }),
        );
      }
      if (url === "/gobierno/paquetes" || url.startsWith("/gobierno/paquetes?")) {
        return Promise.resolve(LISTADO);
      }
      return Promise.reject(new ApiError(404, { code: "NOT_FOUND", message: "No encontrado" }));
    });

    renderizar("/gobierno/paquetes");
    await screen.findByRole("link", { name: "Abrir el paquete PA-2026-0001" });

    const fichero = new File(["PK"], "paquete.zip", { type: "application/zip" });
    await userEvent.upload(screen.getByLabelText(/^Archivo del paquete/), fichero);
    await userEvent.click(screen.getByRole("button", { name: "Verificar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("El archivo no es un ZIP legible");
  });

  it("PQS-07 módulo no habilitado muestra Módulo no habilitado", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/paquetes/verificar") {
        return Promise.resolve(VALIDO);
      }
      if (url === "/gobierno/paquetes" || url.startsWith("/gobierno/paquetes?")) {
        return Promise.reject(
          new ApiError(403, { code: "MODULE_NOT_ENTITLED", message: "x" }),
        );
      }
      return Promise.reject(new ApiError(404, { code: "NOT_FOUND", message: "No encontrado" }));
    });

    renderizar("/gobierno/paquetes");

    expect(await screen.findByText("Módulo no habilitado")).toBeInTheDocument();
  });
});
