import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { describe, expect, it, beforeEach, vi } from "vitest";

const notify = vi.fn();
vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify }),
}));

const useAuthMock = vi.fn();
vi.mock("@/app/contexts/AuthContext", () => ({
  useAuth: () => useAuthMock(),
}));

const resetUserMfa = vi.fn();
vi.mock("@/api/mfa", () => ({
  resetUserMfa: (...args: unknown[]) => resetUserMfa(...args),
}));

const apiFetch = vi.fn();
vi.mock("@/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/client")>();
  return {
    ...actual,
    apiFetch: (...args: unknown[]) => apiFetch(...args),
  };
});

import { UsuariosPage } from "./UsuariosPage";
import { ApiError } from "@/api/client";

const users = [
  { id: "u1", username: "admin", email: null, status: "ACTIVE", must_change_password: false, mfa_enabled: true, last_login: null, roles: [] },
  { id: "u2", username: "pepe", email: "pepe@example.com", status: "ACTIVE", must_change_password: false, mfa_enabled: true, last_login: null, roles: [] },
];

function setup(lista = users) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  apiFetch.mockResolvedValue(lista);
  return {
    ...render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <UsuariosPage />
        </MemoryRouter>
      </QueryClientProvider>,
    ),
    queryClient,
  };
}

describe("UsuariosPage MFA reset", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    notify.mockClear();
    resetUserMfa.mockClear();
    apiFetch.mockClear();
    useAuthMock.mockReturnValue({ user: { id: "u1" }, hasPermission: (p: string) => p === "users:mfa_reset" });
  });

  it("sin permiso no hay botón", async () => {
    useAuthMock.mockReturnValue({ user: { id: "u1" }, hasPermission: () => false });
    setup();
    await screen.findByText(/admin/);
    expect(screen.queryByRole("button", { name: "Restablecer verificación" })).not.toBeInTheDocument();
  });

  it("con permiso no aparece en la fila del propio usuario", async () => {
    setup();
    await screen.findByText(/admin/);
    const adminRow = screen.getByText(/admin/).closest("div");
    expect(adminRow).toBeInTheDocument();
    expect(within(adminRow as HTMLElement).queryByRole("button", { name: "Restablecer verificación" })).not.toBeInTheDocument();

    const pepeRow = screen.getByText(/pepe/).closest("div");
    expect(pepeRow).toBeInTheDocument();
    expect(within(pepeRow as HTMLElement).getByRole("button", { name: "Restablecer verificación" })).toBeInTheDocument();
  });

  it("confirmar llama a resetUserMfa(id)", async () => {
    resetUserMfa.mockResolvedValue(undefined);
    const { queryClient } = setup();
    const invalidar = vi.spyOn(queryClient, "invalidateQueries");
    await screen.findByText(/pepe/);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Restablecer verificación" }));

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Restablecer" }));

    await waitFor(() => {
      expect(resetUserMfa).toHaveBeenCalledWith("u2");
    });
    await waitFor(() => {
      expect(invalidar).toHaveBeenCalledWith({ queryKey: ["security", "users"] });
    });
    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith(
        expect.objectContaining({ title: "Verificación restablecida" }),
      );
    });
  });

  it("sin verificación configurada no hay botón y la fila lo dice", async () => {
    setup([
      ...users,
      { id: "u3", username: "lola", email: null, status: "ACTIVE", must_change_password: false, mfa_enabled: false, last_login: null, roles: [] },
    ]);
    const lolaRow = (await screen.findByText(/lola/)).closest("div");
    expect(lolaRow).toBeInTheDocument();
    expect(within(lolaRow as HTMLElement).getByText(/Verificación en dos pasos: no configurada/)).toBeInTheDocument();
    const buttons = screen.getAllByRole("button", { name: "Restablecer verificación" });
    expect(buttons).toHaveLength(1);
    const pepeRow = screen.getByText(/pepe/).closest("div");
    expect(pepeRow).toBeInTheDocument();
    expect(within(pepeRow as HTMLElement).getByRole("button", { name: "Restablecer verificación" })).toBeInTheDocument();
  });

  it("MFA_RESET_CEILING muestra su mensaje", async () => {
    resetUserMfa.mockRejectedValue(new ApiError(403, { code: "MFA_RESET_CEILING", message: "x" }));
    setup();
    await screen.findByText(/pepe/);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Restablecer verificación" }));
    await screen.findByRole("dialog");
    await user.click(screen.getByRole("button", { name: "Restablecer" }));

    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith(
        expect.objectContaining({
          description: "No puede restablecer a un usuario con más permisos que usted.",
        }),
      );
    });
  });
});
