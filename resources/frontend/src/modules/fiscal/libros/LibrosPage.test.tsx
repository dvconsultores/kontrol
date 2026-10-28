import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiFetch = vi.fn();
const notify = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({
    estado: "LISTA",
    tiene: () => true,
    puede: () => true,
    motivo: () => null,
    motivoDeCapacidad: () => null,
  }),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify }),
}));

const { LibrosPage } = await import("./LibrosPage");

function montar(): void {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <LibrosPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  apiFetch.mockImplementation((ruta: string) => {
    if (typeof ruta === "string" && ruta.startsWith("/fiscal/books/")) {
      return Promise.resolve({
        tax_type: "VENTAS",
        period: "2026-10",
        count: 1,
        total: 10,
        rows: [],
        period_applied: false,
        period_rule: "LEGAL_VALIDATION_REQUIRED",
      });
    }
    if (typeof ruta === "string" && ruta === "/fiscal/periods") {
      return Promise.resolve({ items: [] });
    }
    return Promise.reject(new Error(`ruta inesperada ${ruta}`));
  });
});

describe("LibrosPage", () => {
  it("LIB-01 avisa que el libro no filtra por período", async () => {
    montar();

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalled();
    });

    fireEvent.change(screen.getAllByPlaceholderText("2026-01")[0], { target: { value: "2026-10" } });

    expect((await screen.findByRole("status")).textContent).toContain("no se filtra por período");
  });

  it("LIB-02 sin período no hay aviso", async () => {
    montar();

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalled();
    });

    expect(screen.queryByText(/no se filtra por período/)).toBeNull();
  });
});
