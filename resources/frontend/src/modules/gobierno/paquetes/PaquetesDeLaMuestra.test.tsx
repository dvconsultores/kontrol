import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";

const apiFetchMock = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({ activeCompanyId: "c1", activeCompany: { id: "c1", legal_name: "Contenedor 1" } }),
}));

const { PaquetesDeLaMuestra } = await import("./PaquetesDeLaMuestra");

function renderizar() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <PaquetesDeLaMuestra muestraId="m1" />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiFetchMock.mockReset();
});

describe("PaquetesDeLaMuestra", () => {
  it("PDM-01 lista los paquetes de la muestra", async () => {
    apiFetchMock.mockResolvedValue({
      total: 1,
      pagina: 1,
      por_pagina: 100,
      items: [
        {
          id: "p1",
          codigo: "PA-2026-0001",
          muestra_id: "m1",
          muestra_codigo: "MU-2026-0001",
          numero_generacion: 1,
          titulo: "t",
          generado_por: "ua",
          generado_en: "2026-02-01T10:00:00Z",
          bytes: 4096,
          huella_paquete: "b".repeat(64),
          eventos: 2,
          documentos_incluidos: 1,
          documentos_excluidos: 0,
          hallazgos: 0,
        },
      ],
    });

    renderizar();

    expect(screen.getByRole("heading", { name: "Paquetes de esta muestra" })).toBeInTheDocument();

    const enlace = await screen.findByRole("link", { name: "PA-2026-0001" });
    expect(enlace).toHaveAttribute("href", "/gobierno/paquetes/p1");
    await waitFor(() =>
      expect(apiFetchMock).toHaveBeenCalledWith("/gobierno/paquetes?muestra_id=m1&por_pagina=100"),
    );
  });

  it("PDM-02 muestra el estado vacío", async () => {
    apiFetchMock.mockResolvedValue({ total: 0, pagina: 1, por_pagina: 100, items: [] });

    renderizar();

    expect(
      await screen.findByText("Aún no se ha generado ningún paquete para esta muestra"),
    ).toBeInTheDocument();
  });

  it("PDM-03 muestra el error de carga", async () => {
    apiFetchMock.mockRejectedValue(new ApiError(500, { code: "INTERNAL", message: "x" }));

    renderizar();

    expect(await screen.findByText("No fue posible cargar los paquetes.")).toBeInTheDocument();
  });
});
