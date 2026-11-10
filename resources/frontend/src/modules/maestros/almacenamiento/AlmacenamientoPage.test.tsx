import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

let mockPuede = true;
const apiFetch = vi.fn();
const notify = vi.fn();
let mockAlmacenes: Array<{ id: string; code: string; name: string; status: string }> = [];

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify, dismiss: vi.fn(), notifications: [] }),
}));

vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({ activeCompany: { id: "emp-1" } }),
}));

vi.mock("@/modules/organizacion/almacenes/useAlmacenesDeEmpresa", () => ({
  useAlmacenesDeEmpresa: () => ({
    data: { items: mockAlmacenes },
    isSuccess: true,
    isLoading: false,
    isError: false,
  }),
}));

vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({
    estado: "LISTA",
    tiene: () => true,
    puede: () => mockPuede,
    motivo: () => null,
    motivoDeCapacidad: () => null,
  }),
}));

vi.mock("@/modules/maestros/catalogo/SelectorDeArticulo", () => ({
  SelectorDeArticulo: ({ value, onChange }: { value: string; onChange: (id: string) => void }) => (
    <input
      aria-label="Producto"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      data-testid="selector-articulo"
    />
  ),
}));

import { AlmacenamientoPage } from "./AlmacenamientoPage";

function renderizar(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

function mockRespuestas() {
  apiFetch.mockImplementation((url: string) => {
    if (url === "/storage/conditions") {
      return Promise.resolve({ items: [] });
    }
    if (url === "/storage/size-classes") {
      return Promise.resolve({ items: [] });
    }
    if (url === "/storage/rules") {
      return Promise.resolve({ items: [] });
    }
    if (url === "/organization/zone-types") {
      return Promise.resolve([]);
    }
    if (url === "/maestros/unidades?dimension=MASA") {
      return Promise.resolve({ items: [] });
    }
    if (url === "/maestros/unidades?dimension=PESO") {
      return Promise.resolve({ items: [] });
    }
    if (url === "/maestros/unidades?dimension=VOLUMEN") {
      return Promise.resolve({ items: [] });
    }
    return Promise.reject(new Error(`URL no mockeada: ${url}`));
  });
}

describe("AlmacenamientoPage", () => {
  beforeEach(() => {
    mockPuede = true;
    apiFetch.mockReset();
    notify.mockReset();
    mockRespuestas();
  });

  it("renderiza los cinco títulos de sección", async () => {
    renderizar(<AlmacenamientoPage />);
    expect(await screen.findByRole("heading", { name: "Condiciones especiales" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Clases de tamaño" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Perfil de almacenamiento del producto" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Reglas de almacenamiento" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Política del almacén" })).toBeInTheDocument();
  });

  it("crear condición hace POST /storage/conditions con {code, name}", async () => {
    const user = userEvent.setup();
    renderizar(<AlmacenamientoPage />);
    await screen.findByRole("heading", { name: "Condiciones especiales" });
    await user.type(await screen.findByPlaceholderText("FRAGIL"), "FRAGIL");
    await user.type(screen.getByPlaceholderText("Frágil"), "Frágil");
    await user.click(screen.getByRole("button", { name: "Crear condición" }));
    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/storage/conditions",
        expect.objectContaining({
          method: "POST",
          body: { code: "FRAGIL", name: "Frágil" },
        }),
      );
    });
  });

  it("crear regla con destino 'Tipo de zona' envía target_zone_type_id", async () => {
    const user = userEvent.setup();
    apiFetch.mockImplementation((url: string) => {
      if (url === "/storage/conditions") return Promise.resolve({ items: [] });
      if (url === "/storage/size-classes") return Promise.resolve({ items: [] });
      if (url === "/storage/rules") return Promise.resolve({ items: [] });
      if (url === "/organization/zone-types") {
        return Promise.resolve([{ id: "zt-1", code: "FRIO", name: "Frío", status: "ACTIVE" }]);
      }
      if (url === "/maestros/unidades?dimension=MASA") return Promise.resolve({ items: [] });
      if (url === "/maestros/unidades?dimension=PESO") return Promise.resolve({ items: [] });
      if (url === "/maestros/unidades?dimension=VOLUMEN") return Promise.resolve({ items: [] });
      return Promise.reject(new Error(`URL no mockeada: ${url}`));
    });

    renderizar(<AlmacenamientoPage />);
    await screen.findByRole("heading", { name: "Reglas de almacenamiento" });
    await user.type(await screen.findByPlaceholderText("REGLA-01"), "REGLA-01");
    await user.type(screen.getByPlaceholderText("Regla de fríos"), "Regla de fríos");
    await user.selectOptions(screen.getByLabelText(/^Tipo de destino/), "ZONE_TYPE");
    await user.selectOptions(screen.getByLabelText("Tipo de zona"), "zt-1");
    await user.click(screen.getByRole("button", { name: "Crear regla" }));
    await waitFor(() => {
      const llamada = apiFetch.mock.calls.find((c) => c[0] === "/storage/rules" && (c[1] as { method?: string } | undefined)?.method === "POST");
      expect(llamada).toBeTruthy();
      expect(llamada![1]).toMatchObject({
        method: "POST",
        body: expect.objectContaining({ target_zone_type_id: "zt-1" }),
      });
      expect(llamada![1].body).not.toHaveProperty("target_zone_id");
    });
  });

  it("guardar política envía PUT con mode ENFORCED y on_no_rule BLOCK", async () => {
    const user = userEvent.setup();
    mockAlmacenes = [{ id: "w-1", code: "W1", name: "Almacén 1", status: "ACTIVE" }];
    apiFetch.mockImplementation((url: string) => {
      if (url === "/storage/conditions") return Promise.resolve({ items: [] });
      if (url === "/storage/size-classes") return Promise.resolve({ items: [] });
      if (url === "/storage/rules") return Promise.resolve({ items: [] });
      if (url === "/organization/zone-types") return Promise.resolve([]);
      if (url === "/maestros/unidades?dimension=MASA") return Promise.resolve({ items: [] });
      if (url === "/maestros/unidades?dimension=PESO") return Promise.resolve({ items: [] });
      if (url === "/maestros/unidades?dimension=VOLUMEN") return Promise.resolve({ items: [] });
      if (url === "/storage/warehouse-policies/w-1") {
        return Promise.resolve({ warehouse_id: "w-1", mode: "DISABLED", on_no_rule: "BLOCK", version: null });
      }
      return Promise.reject(new Error(`URL no mockeada: ${url}`));
    });

    renderizar(<AlmacenamientoPage />);
    await screen.findByRole("heading", { name: "Política del almacén" });
    await user.selectOptions(await screen.findByLabelText(/^Almacén de la política/), "w-1");
    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith("/storage/warehouse-policies/w-1");
    });
    const clasificacion = await screen.findByLabelText(/^Clasificación/);
    await waitFor(() => expect(clasificacion).toBeEnabled());
    await user.selectOptions(clasificacion, "ENFORCED");
    const sinRegla = await screen.findByLabelText(/^Sin regla aplicable/);
    await waitFor(() => expect(sinRegla).toBeEnabled());
    await user.selectOptions(sinRegla, "BLOCK");
    await user.click(screen.getByRole("button", { name: "Guardar política" }));
    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/storage/warehouse-policies/w-1",
        expect.objectContaining({
          method: "PUT",
          body: { expected_version: null, mode: "ENFORCED", on_no_rule: "BLOCK" },
        }),
      );
    });
  });
});
