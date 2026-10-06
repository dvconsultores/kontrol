/**
 * RESTAURA · Recargar una pantalla no lleva a otra (FR-054-E2EDB-029, FR-001-042).
 *
 * Al recargar, la sesión se restaura en dos pasos: llega el token y después llega el
 * usuario. Entre uno y otro la aplicación no puede decidir todavía si hay sesión. Antes
 * decidía: `RouteGuard` mandaba a /login y, al llegar el usuario, el login mandaba a
 * Inicio. Aquí se detiene el segundo paso a propósito y se mira qué se pinta mientras.
 */
import { act, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiFetch = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

const { AuthProvider } = await import("./AuthContext");
const { RouteGuard } = await import("@/components/RouteGuard");

const USUARIO = { id: "u-1", username: "admin", tenant_id: "t-1" };
const visitasAlLogin: string[] = [];

function Login(): React.JSX.Element {
  visitasAlLogin.push("login");
  return <p>formulario de acceso</p>;
}

function montar(): void {
  render(
    <AuthProvider>
      <MemoryRouter initialEntries={["/comercial/listas-precio"]}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<RouteGuard />}>
            <Route path="/comercial/listas-precio" element={<p>pantalla pedida</p>} />
            <Route path="/" element={<p>inicio</p>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  );
}

/** Una respuesta que la prueba suelta cuando quiere. */
function pendiente<T>(): { promesa: Promise<T>; resolver: (valor: T) => void; rechazar: (motivo: unknown) => void } {
  let resolver!: (valor: T) => void;
  let rechazar!: (motivo: unknown) => void;
  const promesa = new Promise<T>((ok, mal) => {
    resolver = ok;
    rechazar = mal;
  });
  return { promesa, resolver, rechazar };
}

async function vaciarCola(): Promise<void> {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

describe("restauración de la sesión al recargar una ruta", () => {
  beforeEach(() => {
    apiFetch.mockReset();
    visitasAlLogin.length = 0;
  });

  it("RESTAURA-01 · con el token y todavía sin el usuario no se decide nada: ni login ni pantalla", async () => {
    const yo = pendiente<{ user: typeof USUARIO; permissions: string[] }>();
    apiFetch.mockImplementation((ruta: string) =>
      ruta === "/auth/refresh" ? Promise.resolve({ access_token: "t-1" }) : yo.promesa);

    montar();
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/auth/me"));
    await vaciarCola();

    expect(visitasAlLogin).toEqual([]);
    expect(screen.queryByText("formulario de acceso")).toBeNull();
    expect(screen.queryByText("pantalla pedida")).toBeNull();
    expect(screen.queryByText("inicio")).toBeNull();

    await act(async () => {
      yo.resolver({ user: USUARIO, permissions: ["comercial:view"] });
    });
    expect(await screen.findByText("pantalla pedida")).toBeTruthy();
    expect(visitasAlLogin, "la ruta pedida pasó por el login antes de pintarse").toEqual([]);
    expect(screen.queryByText("inicio")).toBeNull();
  });

  it("RESTAURA-02 · sin sesión que restaurar se va al login, y solo entonces", async () => {
    apiFetch.mockImplementation(() => Promise.reject(new Error("AUTH_REQUIRED")));

    montar();

    expect(await screen.findByText("formulario de acceso")).toBeTruthy();
    expect(screen.queryByText("pantalla pedida")).toBeNull();
    expect(apiFetch).not.toHaveBeenCalledWith("/auth/me");
  });

  it("RESTAURA-03 · si el token llega y el usuario no, no hay sesión: login, no la pantalla", async () => {
    const yo = pendiente<never>();
    apiFetch.mockImplementation((ruta: string) =>
      ruta === "/auth/refresh" ? Promise.resolve({ access_token: "t-1" }) : yo.promesa);

    montar();
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/auth/me"));
    await vaciarCola();
    expect(visitasAlLogin).toEqual([]);

    await act(async () => {
      yo.rechazar(new Error("AUTH_REQUIRED"));
    });
    expect(await screen.findByText("formulario de acceso")).toBeTruthy();
    expect(screen.queryByText("pantalla pedida")).toBeNull();
  });
});
