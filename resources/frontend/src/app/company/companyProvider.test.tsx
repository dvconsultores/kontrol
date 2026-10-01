/**
 * Resolución de la empresa activa (ARCH-MC-001, N6).
 *
 * Se prueba el comportamiento que decide en qué empresa arranca una pestaña:
 * cuándo se resuelve sola, cuándo hay que preguntar, y qué pasa cuando la
 * preferencia guardada ya no vale.
 */
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CompanyProvider, useCompany } from "@/app/contexts/CompanyContext";
import { setAccessToken } from "@/api/client";

const A = { id: "aaa", code: "A", legal_name: "Empresa A CA", rif: "J-1", status: "ACTIVE" };
const B = { id: "bbb", code: "B", legal_name: "Empresa B CA", rif: "J-2", status: "ACTIVE" };
const INACTIVA = { ...B, id: "ccc", code: "C", legal_name: "Empresa C CA", status: "INACTIVE" };

const fetchOriginal = globalThis.fetch;

vi.mock("@/app/contexts/AuthContext", () => ({
  useAuth: () => ({
    isAuthenticated: true,
    isReady: true,
    user: { id: "u-1", username: "ua" },
  }),
}));

/** La API responde el sobre de listados; el proveedor recorre sus páginas. */
function servir(empresas: unknown[], tamano = 100): void {
  globalThis.fetch = vi.fn(async (entrada: RequestInfo | URL) => {
    const url = new URL(String(entrada), "http://k");
    const page = Number(url.searchParams.get("page") ?? "1");
    const page_size = Number(url.searchParams.get("page_size") ?? String(tamano));
    const items = empresas.slice((page - 1) * page_size, page * page_size);
    return new Response(JSON.stringify({ items, total: empresas.length, page, page_size }), {
      status: 200, headers: { "content-type": "application/json" },
    });
  }) as unknown as typeof fetch;
}

function Sonda(): React.JSX.Element {
  const { estado, activeCompanyId, companies } = useCompany();
  return (
    <div>
      <span data-testid="estado">{estado}</span>
      <span data-testid="activa">{activeCompanyId ?? "ninguna"}</span>
      <span data-testid="cuantas">{companies.length}</span>
    </div>
  );
}

function montar(): void {
  render(
    <CompanyProvider>
      <Sonda />
    </CompanyProvider>,
  );
}

beforeEach(() => {
  setAccessToken("token");
  window.localStorage.clear();
  window.sessionStorage.clear();
});

afterEach(() => {
  globalThis.fetch = fetchOriginal;
  window.localStorage.clear();
  window.sessionStorage.clear();
});

describe("la resolución de la empresa activa", () => {
  it("resuelve sola cuando hay una única empresa", async () => {
    servir([A]);
    montar();
    await waitFor(() => expect(screen.getByTestId("estado").textContent).toBe("READY"));
    expect(screen.getByTestId("activa").textContent).toBe("aaa");
  });

  it("pide elegir cuando hay varias y ninguna preferencia", async () => {
    // No elige la primera: decidir por el usuario en qué empresa opera es
    // exactamente lo que no debe hacerse.
    servir([A, B]);
    montar();
    await waitFor(() =>
      expect(screen.getByTestId("estado").textContent).toBe("COMPANY_SELECTION_REQUIRED"));
    expect(screen.getByTestId("activa").textContent).toBe("ninguna");
  });

  it("restaura la preferencia cuando sigue autorizada", async () => {
    window.localStorage.setItem("kontrol.company-preference.v2:u-1", "bbb");
    servir([A, B]);
    montar();
    await waitFor(() => expect(screen.getByTestId("estado").textContent).toBe("READY"));
    expect(screen.getByTestId("activa").textContent).toBe("bbb");
  });

  it("descarta la preferencia que ya no está autorizada", async () => {
    // Ayer tenía acceso a B; hoy no. La preferencia no concede nada.
    window.localStorage.setItem("kontrol.company-preference.v2:u-1", "bbb");
    servir([A]);
    montar();
    await waitFor(() => expect(screen.getByTestId("estado").textContent).toBe("READY"));
    expect(screen.getByTestId("activa").textContent).toBe("aaa");
    expect(window.localStorage.getItem("kontrol.company-preference.v2:u-1")).toBe("aaa");
  });

  it("no restaura una empresa desactivada", async () => {
    window.localStorage.setItem("kontrol.company-preference.v2:u-1", "ccc");
    servir([A, B, INACTIVA]);
    montar();
    await waitFor(() =>
      expect(screen.getByTestId("estado").textContent).toBe("COMPANY_SELECTION_REQUIRED"));
  });

  it("prefiere el contexto de esta pestaña sobre la preferencia global", async () => {
    // La preferencia es de todo el navegador; el contexto es de esta pestaña.
    // Si mandara la preferencia, abrir una segunda pestaña y cambiar de empresa
    // ahí arrastraría a la primera.
    window.localStorage.setItem("kontrol.company-preference.v2:u-1", "aaa");
    window.sessionStorage.setItem("kontrol.company-tab.v1", "u-1|bbb");
    servir([A, B]);
    montar();
    await waitFor(() => expect(screen.getByTestId("estado").textContent).toBe("READY"));
    expect(screen.getByTestId("activa").textContent).toBe("bbb");
  });

  it("no opera con una empresa inventada en el almacenamiento", async () => {
    // Manipular el almacenamiento no concede acceso: el id no está en la lista
    // autorizada, así que no se adopta.
    window.sessionStorage.setItem("kontrol.company-tab.v1", "u-1|empresa-inventada");
    window.localStorage.setItem("kontrol.company-preference.v2:u-1", "otra-inventada");
    servir([A, B]);
    montar();
    await waitFor(() =>
      expect(screen.getByTestId("estado").textContent).toBe("COMPANY_SELECTION_REQUIRED"));
    expect(screen.getByTestId("activa").textContent).toBe("ninguna");
  });

  it("declara que no hay empresas cuando la lista viene vacía", async () => {
    servir([]);
    montar();
    await waitFor(() => expect(screen.getByTestId("estado").textContent).toBe("NO_COMPANIES"));
  });

  it("no hereda el contexto que otro usuario dejó en esta pestaña", async () => {
    // La pestaña puede reutilizarse tras un cierre de sesión. Lo guardado lleva
    // el identificador de quien lo eligió, así que no se adopta.
    window.sessionStorage.setItem("kontrol.company-tab.v1", "u-otro|bbb");
    servir([A, B]);
    montar();
    await waitFor(() =>
      expect(screen.getByTestId("estado").textContent).toBe("COMPANY_SELECTION_REQUIRED"));
  });

  it("no hereda la preferencia de otro usuario", async () => {
    // La preferencia se guarda bajo el identificador de quien la eligió.
    window.localStorage.setItem("kontrol.company-preference.v2:u-otro", "bbb");
    servir([A, B]);
    montar();
    await waitFor(() =>
      expect(screen.getByTestId("estado").textContent).toBe("COMPANY_SELECTION_REQUIRED"));
  });
});
