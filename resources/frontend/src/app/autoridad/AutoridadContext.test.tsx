import { describe, expect, it, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, act } from "@testing-library/react";
import { AutoridadProvider, useAutoridad } from "./AutoridadContext";
import { useAuth } from "@/app/contexts/AuthContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import type { Operacion } from "./operaciones";

const apiFetch = vi.fn();
const setDenial = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
  setAuthorityDenialHandler: (...args: unknown[]) => setDenial(...args),
}));

vi.mock("@/app/contexts/AuthContext", () => ({
  useAuth: vi.fn(),
}));

vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: vi.fn(),
}));

const mockedUseAuth = vi.mocked(useAuth);
const mockedUseCompany = vi.mocked(useCompany);

const CATALOGO: { operations: Operacion[] } = {
  operations: [
    {
      method: "GET",
      path: "/api/v1/maestros/unidades",
      capabilities: ["maestros:view"],
      scope: "COMPANY",
    },
    {
      method: "GET",
      path: "/api/v1/documentos",
      capabilities: ["documentos:view"],
      scope: "TENANT",
    },
  ],
};

function Sonda() {
  const { puede, tiene, motivo, estado, motivoDeCapacidad } = useAutoridad();
  return (
    <div>
      <span data-testid="estado">{estado}</span>
      <span data-testid="puede-unidades">
        {String(puede("GET", "/maestros/unidades"))}
      </span>
      <span data-testid="motivo-unidades">
        {String(motivo("GET", "/maestros/unidades"))}
      </span>
      <span data-testid="tiene-empresa">
        {String(tiene("maestros:view", "empresa"))}
      </span>
      <span data-testid="tiene-global">
        {String(tiene("maestros:view", "global"))}
      </span>
      <span data-testid="puede-documentos">
        {String(puede("GET", "/documentos"))}
      </span>
      <span data-testid="motivo-capacidad-empresa">
        {String(motivoDeCapacidad("maestros:view", "empresa"))}
      </span>
    </div>
  );
}

function montar() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return {
    ...render(
      <QueryClientProvider client={queryClient}>
        <AutoridadProvider>
          <Sonda />
        </AutoridadProvider>
      </QueryClientProvider>,
    ),
    queryClient,
  };
}

function authBase(overrides: Record<string, unknown> = {}) {
  mockedUseAuth.mockReturnValue({
    isAuthenticated: true,
    user: { id: "u1" },
    permissions: [],
    tenantPermissions: [],
    reloadMe: vi.fn(),
    ...overrides,
  } as never);
}

function companyBase(overrides: Record<string, unknown> = {}) {
  mockedUseCompany.mockReturnValue({
    activeCompanyId: "empresa-a",
    estado: "READY",
    ...overrides,
  } as never);
}

beforeEach(() => {
  vi.clearAllMocks();
  apiFetch.mockImplementation((ruta: string) => {
    if (ruta === "/auth/operations") {
      return Promise.resolve(CATALOGO);
    }
    if (ruta === "/authority/company") {
      return Promise.resolve({
        company_id: "empresa-a",
        permissions: ["maestros:view"],
      });
    }
    return Promise.reject(new Error("ruta no esperada"));
  });
  setDenial.mockReturnValue(undefined);
  authBase();
  companyBase();
});

describe("AutoridadContext", () => {
  it("permite una operación de empresa con la capacidad devuelta por /authority/company", async () => {
    montar();
    await waitFor(() => {
      expect(screen.getByTestId("estado")).toHaveTextContent("LISTA");
    });
    expect(screen.getByTestId("puede-unidades")).toHaveTextContent("true");
    expect(screen.getByTestId("tiene-empresa")).toHaveTextContent("true");
  });

  it("deniega con COMPANY_SCOPE_FORBIDDEN cuando la capacidad solo está en global", async () => {
    authBase({ permissions: ["maestros:view"] });
    apiFetch.mockImplementation((ruta: string) => {
      if (ruta === "/auth/operations") {
        return Promise.resolve(CATALOGO);
      }
      if (ruta === "/authority/company") {
        return Promise.resolve({ company_id: "empresa-a", permissions: [] });
      }
      return Promise.reject(new Error("ruta no esperada"));
    });
    montar();
    await waitFor(() => {
      expect(screen.getByTestId("motivo-unidades")).toHaveTextContent(
        "COMPANY_SCOPE_FORBIDDEN",
      );
    });
    expect(screen.getByTestId("puede-unidades")).toHaveTextContent("false");
  });

  it("no pide /authority/company sin empresa activa y niega capacidades de empresa", async () => {
    companyBase({ activeCompanyId: null, estado: "COMPANY_SELECTION_REQUIRED" });
    montar();
    await waitFor(() => {
      expect(screen.getByTestId("estado")).toHaveTextContent("LISTA");
    });
    expect(apiFetch).not.toHaveBeenCalledWith("/authority/company");
    expect(screen.getByTestId("tiene-empresa")).toHaveTextContent("false");
  });

  it("permite operación tenant solo si está en tenantPermissions", async () => {
    authBase({ tenantPermissions: ["documentos:view"] });
    montar();
    await waitFor(() => {
      expect(screen.getByTestId("puede-documentos")).toHaveTextContent("true");
    });
  });

  it("registra manejador de denegación que invalida autoridad y llama a reloadMe una sola vez", async () => {
    const reloadMe = vi.fn();
    authBase({ reloadMe });
    const invalidateSpy = vi.spyOn(QueryClient.prototype, "invalidateQueries");
    montar();
    await waitFor(() => {
      expect(setDenial).toHaveBeenCalledTimes(1);
    });
    const manejador = setDenial.mock.calls[0][0] as () => void;
    act(() => {
      manejador();
    });
    act(() => {
      manejador();
    });
    expect(reloadMe).toHaveBeenCalledTimes(1);
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["autoridad"] });
  });

  it("trata company_id distinto al activo como autoridad de empresa vacía", async () => {
    apiFetch.mockImplementation((ruta: string) => {
      if (ruta === "/auth/operations") {
        return Promise.resolve(CATALOGO);
      }
      if (ruta === "/authority/company") {
        return Promise.resolve({ company_id: "otra-empresa", permissions: ["maestros:view"] });
      }
      return Promise.reject(new Error("ruta no esperada"));
    });
    montar();
    await waitFor(() => {
      expect(screen.getByTestId("tiene-empresa")).toHaveTextContent("false");
    });
    expect(screen.getByTestId("puede-unidades")).toHaveTextContent("false");
  });

  it("sigue CARGANDO y no ofrece nada mientras /authority/company no responde", async () => {
    authBase({
      permissions: ["maestros:view"],
      tenantPermissions: ["documentos:view"],
    });
    apiFetch.mockImplementation((ruta: string) => {
      if (ruta === "/auth/operations") {
        return Promise.resolve(CATALOGO);
      }
      if (ruta === "/authority/company") {
        return new Promise(() => {});
      }
      return Promise.reject(new Error("ruta no esperada"));
    });
    const { queryClient } = montar();
    await waitFor(() => {
      expect(queryClient.getQueryState(["auth", "operaciones"])?.status).toBe(
        "success",
      );
    });
    expect(screen.getByTestId("estado")).toHaveTextContent("CARGANDO");
    expect(screen.getByTestId("puede-documentos")).toHaveTextContent("false");
    expect(screen.getByTestId("motivo-unidades")).toHaveTextContent("null");
  });

  it("motivoDeCapacidad distingue la empresa activa del resto", async () => {
    authBase({ permissions: ["maestros:view"] });
    apiFetch.mockImplementation((ruta: string) => {
      if (ruta === "/auth/operations") {
        return Promise.resolve(CATALOGO);
      }
      if (ruta === "/authority/company") {
        return Promise.resolve({ company_id: "empresa-a", permissions: [] });
      }
      return Promise.reject(new Error("ruta no esperada"));
    });
    const primerMontaje = montar();
    await waitFor(() => {
      expect(screen.getByTestId("estado")).toHaveTextContent("LISTA");
    });
    expect(screen.getByTestId("motivo-capacidad-empresa")).toHaveTextContent(
      "COMPANY_SCOPE_FORBIDDEN",
    );
    primerMontaje.unmount();

    authBase();
    apiFetch.mockImplementation((ruta: string) => {
      if (ruta === "/auth/operations") {
        return Promise.resolve(CATALOGO);
      }
      if (ruta === "/authority/company") {
        return Promise.resolve({ company_id: "empresa-a", permissions: [] });
      }
      return Promise.reject(new Error("ruta no esperada"));
    });
    montar();
    await waitFor(() => {
      expect(screen.getByTestId("estado")).toHaveTextContent("LISTA");
    });
    expect(screen.getByTestId("motivo-capacidad-empresa")).toHaveTextContent(
      "PERMISSION_DENIED",
    );
  });
});
