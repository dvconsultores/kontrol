import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiFetch } from "@/api/client";
import { AsyncCombobox } from "./AsyncCombobox";

vi.mock("@/api/client", () => ({
  apiFetch: vi.fn(),
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const renderCombobox = () =>
  render(
    <QueryClientProvider client={queryClient}>
      <AsyncCombobox
        value={null}
        onChange={() => undefined}
        searchUrl="/maestros/catalogos/items/search"
        label="Buscar producto"
      />
    </QueryClientProvider>,
  );

beforeEach(() => {
  queryClient.clear();
  vi.mocked(apiFetch).mockReset();
});

describe("AsyncCombobox", () => {
  it("muestra estado vacío cuando no hay resultados", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 });
    const user = userEvent.setup();
    renderCombobox();

    await user.type(screen.getByRole("combobox"), "arroz");
    await waitFor(() => {
      expect(screen.getByText("Sin resultados")).toBeInTheDocument();
    });
  });

  it("muestra resultados de la búsqueda asíncrona", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      items: [
        { id: "1", code: "P-001", name: "Arroz", item_type: "PRODUCT" },
        { id: "2", code: "P-002", name: "Arroz integral", item_type: "PRODUCT" },
      ],
      total: 2,
      page: 1,
      page_size: 20,
    });
    const user = userEvent.setup();
    renderCombobox();

    await user.type(screen.getByRole("combobox"), "arroz");
    await waitFor(() => {
      expect(screen.getByRole("option", { name: /Arroz integral/ })).toBeInTheDocument();
    });
    // Verifica que la búsqueda se ejecuta contra el backend
    expect(apiFetch).toHaveBeenCalledWith(expect.stringContaining("/maestros/catalogos/items/search"));
  });
});
