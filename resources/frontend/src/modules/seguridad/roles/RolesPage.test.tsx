import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi, beforeEach } from "vitest";

const notify = vi.fn();
vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify }),
}));

const apiFetch = vi.fn();
vi.mock("@/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/client")>();
  return {
    ...actual,
    apiFetch: (...args: unknown[]) => apiFetch(...args),
  };
});

import { RolesPage } from "./RolesPage";
import { ApiError } from "@/api/client";

const R_SUB = {
  id: "r-sub",
  code: "R_SUB",
  name: "Sub",
  company_id: null,
  protected: false,
  status: "ACTIVE",
  permissions: ["inventario:view"],
  delegable: true,
  motivo: null,
};

const ADMIN = {
  id: "r-admin",
  code: "ADMIN",
  name: "Admin",
  company_id: null,
  protected: true,
  status: "ACTIVE",
  permissions: ["roles:edit", "users:create"],
  delegable: false,
  motivo: "AUTHORITY_CEILING_EXCEEDED",
};

const USERS = [
  {
    id: "u1",
    username: "pepe",
    roles: [{ id: "r-sub", code: "R_SUB", name: "Sub", company_id: null }],
  },
];

const COMPANIES = {
  items: [
    { id: "c1", code: "D1", legal_name: "Demo C.A." },
    { id: "c2", code: "D2", legal_name: "Demo Dos C.A." },
  ],
  total: 2,
  page: 1,
  page_size: 100,
};

function renderPage(
  especial?: (path: string, opts?: { method?: string }) => Promise<unknown> | undefined,
): void {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  apiFetch.mockImplementation((path: string, opts?: { method?: string }) => {
    const respuestaEspecial = especial?.(path, opts);
    if (respuestaEspecial !== undefined) return respuestaEspecial;

    if (path === "/roles") return Promise.resolve({ items: [R_SUB, ADMIN] });
    if (path === "/users") return Promise.resolve(USERS);
    if (path === "/organization/companies?page=1&page_size=100") return Promise.resolve(COMPANIES);
    if (opts?.method === "POST" && path === "/users/u1/roles") return Promise.resolve({ ok: true });
    if (opts?.method === "DELETE" && path === "/users/u1/roles/r-sub") return Promise.resolve({ ok: true });
    return Promise.reject(new Error(`Unexpected request: ${path}`));
  });

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <RolesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("RolesPage · techo de delegación", () => {
  beforeEach(() => {
    notify.mockReset();
    apiFetch.mockReset();
  });

  it("el rol no delegable aparece como opción deshabilitada y el delegable habilitado; la lista muestra los estados", async () => {
    renderPage();

    const subOption = await screen.findByRole("option", { name: /Sub \(R_SUB\)/ }) as HTMLOptionElement;
    const adminOption = await screen.findByRole("option", {
      name: /Admin \(ADMIN\) — fuera de su autoridad/,
    }) as HTMLOptionElement;
    const roleSelect = screen.getByLabelText(/^Rol\b/);

    expect(subOption.disabled).toBe(false);
    expect(adminOption.disabled).toBe(true);
    expect(screen.getByText("Puede delegarlo")).toBeInTheDocument();
    expect(screen.getByText("Fuera de su autoridad")).toBeInTheDocument();
    expect(roleSelect).toBeInTheDocument();
  });

  it("asignar R_SUB a pepe sin empresa envía body exacto {role_id: 'r-sub'}", async () => {
    const user = userEvent.setup();
    renderPage();

    await screen.findByRole("option", { name: "pepe" });
    await screen.findByRole("option", { name: /Sub \(R_SUB\)/ });
    await user.selectOptions(screen.getByLabelText(/^Usuario/), "u1");
    await user.selectOptions(screen.getByLabelText(/^Rol\b/), "r-sub");
    await user.click(screen.getByRole("button", { name: "Asignar" }));

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith("/users/u1/roles", {
        method: "POST",
        body: { role_id: "r-sub" },
      });
    });
  });

  it("asignar con empresa «Demo Dos C.A.» envía body {role_id: 'r-sub', company_id: 'c2'}", async () => {
    const user = userEvent.setup();
    renderPage();

    await screen.findByRole("option", { name: "pepe" });
    await screen.findByRole("option", { name: /Sub \(R_SUB\)/ });
    await user.selectOptions(screen.getByLabelText(/^Usuario/), "u1");
    await user.selectOptions(screen.getByLabelText(/^Rol\b/), "r-sub");
    await user.selectOptions(screen.getByLabelText(/^Empresa/), "c2");
    await user.click(screen.getByRole("button", { name: "Asignar" }));

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith("/users/u1/roles", {
        method: "POST",
        body: { role_id: "r-sub", company_id: "c2" },
      });
    });
  });

  it("el POST rechaza con SELF_ESCALATION_FORBIDDEN y notifica el mensaje correspondiente", async () => {
    const user = userEvent.setup();
    renderPage((path: string, opts?: { method?: string }) => {
      if (opts?.method === "POST" && path === "/users/u1/roles") {
        return Promise.reject(
          new ApiError(403, { code: "SELF_ESCALATION_FORBIDDEN", message: "x" }),
        );
      }
      return undefined;
    });

    await screen.findByRole("option", { name: "pepe" });
    await screen.findByRole("option", { name: /Sub \(R_SUB\)/ });
    await user.selectOptions(screen.getByLabelText(/^Usuario/), "u1");
    await user.selectOptions(screen.getByLabelText(/^Rol\b/), "r-sub");
    await user.click(screen.getByRole("button", { name: "Asignar" }));

    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith({
        type: "error",
        title: "No fue posible asignar el rol",
        description: "No puede ampliar su propia autoridad.",
      });
    });
  });

  it("pulsar «Quitar rol Sub a pepe» abre el diálogo; «Cancelar» lo cierra sin llamar al DELETE", async () => {
    const user = userEvent.setup();
    renderPage();

    const removeButton = await screen.findByRole("button", { name: "Quitar rol Sub a pepe" });
    await user.click(removeButton);
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    const deleteCallsBefore = apiFetch.mock.calls.filter(
      ([, opts]) => (opts as { method?: string } | undefined)?.method === "DELETE",
    ).length;

    await user.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    const deleteCallsAfter = apiFetch.mock.calls.filter(
      ([, opts]) => (opts as { method?: string } | undefined)?.method === "DELETE",
    ).length;
    expect(deleteCallsAfter).toBe(deleteCallsBefore);
  });

  it("confirmar «Quitar» con DELETE rechazado por LAST_SECURITY_ADMIN_REQUIRED notifica el mensaje correspondiente", async () => {
    const user = userEvent.setup();
    renderPage((path: string, opts?: { method?: string }) => {
      if (opts?.method === "DELETE" && path === "/users/u1/roles/r-sub") {
        return Promise.reject(
          new ApiError(409, { code: "LAST_SECURITY_ADMIN_REQUIRED", message: "x" }),
        );
      }
      return undefined;
    });

    const removeButton = await screen.findByRole("button", { name: "Quitar rol Sub a pepe" });
    await user.click(removeButton);
    await user.click(screen.getByRole("button", { name: "Quitar" }));

    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith({
        type: "error",
        title: "No fue posible quitar el rol",
        description:
          "La empresa debe conservar al menos un administrador de seguridad. Asigne antes ese rol a otra persona.",
      });
    });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("un código desconocido usa err.message", async () => {
    const user = userEvent.setup();
    renderPage((path: string, opts?: { method?: string }) => {
      if (opts?.method === "POST" && path === "/users/u1/roles") {
        return Promise.reject(new ApiError(400, { code: "UNKNOWN_CODE", message: "Error raro" }));
      }
      return undefined;
    });

    await screen.findByRole("option", { name: "pepe" });
    await screen.findByRole("option", { name: /Sub \(R_SUB\)/ });
    await user.selectOptions(screen.getByLabelText(/^Usuario/), "u1");
    await user.selectOptions(screen.getByLabelText(/^Rol\b/), "r-sub");
    await user.click(screen.getByRole("button", { name: "Asignar" }));

    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith({
        type: "error",
        title: "No fue posible asignar el rol",
        description: "Error raro",
      });
    });
  });
});
