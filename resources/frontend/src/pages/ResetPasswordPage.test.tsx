import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it, beforeEach, vi } from "vitest";

import { ApiError } from "@/api/client";

const notify = vi.fn();
vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify }),
}));

const apiFetch = vi.fn();
vi.mock("@/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

import { ResetPasswordPage } from "./ResetPasswordPage";

function renderPage(): ReturnType<typeof render> {
  return render(
    <MemoryRouter initialEntries={["/reset-password"]}>
      <Routes>
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/login" element={<div>LOGIN</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ResetPasswordPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiFetch.mockReset();
  });

  it("solicitar con campos vacíos no llama a la API y marca los dos campos", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: /Solicitar recuperación/i }));

    expect(apiFetch).not.toHaveBeenCalled();
    expect(screen.getByText("Indique la empresa")).toBeInTheDocument();
    expect(screen.getByText("Indique el usuario")).toBeInTheDocument();
  });

  it("tras solicitar muestra el aviso neutro y no muestra ningún token", async () => {
    apiFetch.mockResolvedValue({ ok: true, reset_token: "NO-DEBE-VERSE" });
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/Empresa \(código\)/i), "kont");
    await user.type(screen.getByLabelText(/Usuario/i), "admin");
    await user.click(screen.getByRole("button", { name: /Solicitar recuperación/i }));

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith("/auth/password-reset/request", {
        method: "POST",
        body: { tenant_code: "kont", username: "admin" },
      });
    });

    expect(screen.getByRole("status")).toHaveTextContent(/Si la cuenta puede recuperarse/);
    expect(screen.queryByText("NO-DEBE-VERSE")).not.toBeInTheDocument();
  });

  it("Tengo un código lleva al paso del código", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: /Tengo un código/i }));

    expect(screen.getByLabelText(/Código de recuperación de contraseña/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Nueva contraseña/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Confirmar nueva contraseña/i)).toBeInTheDocument();
  });

  it("contraseñas distintas no llaman a la API", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: /Tengo un código/i }));
    await user.type(screen.getByLabelText(/Código de recuperación de contraseña/i), "c0d1g0");
    await user.type(screen.getByLabelText(/^Nueva contraseña/), "NuevaClave2026x");
    await user.type(screen.getByLabelText(/Confirmar nueva contraseña/i), "OtraClave2026x");
    await user.click(screen.getByRole("button", { name: /Restablecer contraseña/i }));

    expect(apiFetch).not.toHaveBeenCalled();
    expect(screen.getByText("Las contraseñas no coinciden")).toBeInTheDocument();
  });

  it("éxito: envía token y contraseña, borra el código y muestra el paso hecho; Ir al inicio de sesión navega a /login", async () => {
    apiFetch.mockResolvedValue({ ok: true });
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: /Tengo un código/i }));

    const codeInput = screen.getByLabelText(/Código de recuperación de contraseña/i);
    const passwordInput = screen.getByLabelText(/^Nueva contraseña/);
    const confirmInput = screen.getByLabelText(/Confirmar nueva contraseña/i);

    await user.type(codeInput, "c0d1g0");
    await user.type(passwordInput, "NuevaClave2026x");
    await user.type(confirmInput, "NuevaClave2026x");
    await user.click(screen.getByRole("button", { name: /Restablecer contraseña/i }));

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith("/auth/password-reset/confirm", {
        method: "POST",
        body: { token: "c0d1g0", new_password: "NuevaClave2026x" },
      });
    });

    expect(screen.getByRole("status")).toHaveTextContent(/Por seguridad se cerraron todas sus sesiones/);
    expect(screen.queryByDisplayValue("c0d1g0")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Ir al inicio de sesión/i }));
    expect(screen.getByText("LOGIN")).toBeInTheDocument();
  });

  it("RESET_TOKEN_EXPIRED muestra su mensaje y vacía el código", async () => {
    apiFetch.mockRejectedValue(new ApiError(400, { code: "RESET_TOKEN_EXPIRED", message: "x" }));
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: /Tengo un código/i }));

    const codeInput = screen.getByLabelText(/Código de recuperación de contraseña/i);
    await user.type(codeInput, "c0d1g0");
    await user.type(screen.getByLabelText(/^Nueva contraseña/), "NuevaClave2026x");
    await user.type(screen.getByLabelText(/Confirmar nueva contraseña/i), "NuevaClave2026x");
    await user.click(screen.getByRole("button", { name: /Restablecer contraseña/i }));

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalled();
    });

    expect(screen.getByText(/El código caducó \(dura 15 minutos\)/)).toBeInTheDocument();
    expect(codeInput).toHaveValue("");
  });

  it("RESET_TOKEN_USED muestra su mensaje", async () => {
    apiFetch.mockRejectedValue(new ApiError(400, { code: "RESET_TOKEN_USED", message: "x" }));
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: /Tengo un código/i }));
    await user.type(screen.getByLabelText(/Código de recuperación de contraseña/i), "c0d1g0");
    await user.type(screen.getByLabelText(/^Nueva contraseña/), "NuevaClave2026x");
    await user.type(screen.getByLabelText(/Confirmar nueva contraseña/i), "NuevaClave2026x");
    await user.click(screen.getByRole("button", { name: /Restablecer contraseña/i }));

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalled();
    });

    expect(screen.getByText(/Ese código ya se usó o fue reemplazado por otro más reciente/)).toBeInTheDocument();
  });

  it("RESET_TOKEN_INVALID muestra su mensaje y conserva el código", async () => {
    apiFetch.mockRejectedValue(new ApiError(400, { code: "RESET_TOKEN_INVALID", message: "x" }));
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: /Tengo un código/i }));

    const codeInput = screen.getByLabelText(/Código de recuperación de contraseña/i);
    await user.type(codeInput, "c0d1g0");
    await user.type(screen.getByLabelText(/^Nueva contraseña/), "NuevaClave2026x");
    await user.type(screen.getByLabelText(/Confirmar nueva contraseña/i), "NuevaClave2026x");
    await user.click(screen.getByRole("button", { name: /Restablecer contraseña/i }));

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalled();
    });

    expect(screen.getByText(/El código no es válido/)).toBeInTheDocument();
    expect(codeInput).toHaveValue("c0d1g0");
  });

  it("PASSWORD_POLICY muestra los mensajes del campo", async () => {
    apiFetch.mockRejectedValue(
      new ApiError(422, {
        code: "PASSWORD_POLICY",
        field_errors: { new_password: ["Debe incluir al menos un número"] },
        message: "x",
      }),
    );
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: /Tengo un código/i }));
    await user.type(screen.getByLabelText(/Código de recuperación de contraseña/i), "c0d1g0");
    await user.type(screen.getByLabelText(/^Nueva contraseña/), "NuevaClave2026x");
    await user.type(screen.getByLabelText(/Confirmar nueva contraseña/i), "NuevaClave2026x");
    await user.click(screen.getByRole("button", { name: /Restablecer contraseña/i }));

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalled();
    });

    expect(screen.getByText("Debe incluir al menos un número")).toBeInTheDocument();
  });

  it("no escribe en localStorage ni sessionStorage", async () => {
    const storageSpy = vi.spyOn(Storage.prototype, "setItem");

    const user = userEvent.setup();
    renderPage();

    apiFetch.mockResolvedValue({ ok: true, reset_token: "NO-DEBE-VERSE" });
    await user.type(screen.getByLabelText(/Empresa \(código\)/i), "kont");
    await user.type(screen.getByLabelText(/Usuario/i), "admin");
    await user.click(screen.getByRole("button", { name: /Solicitar recuperación/i }));

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith("/auth/password-reset/request", expect.anything());
    });

    apiFetch.mockResolvedValue({ ok: true });
    await user.click(screen.getByRole("button", { name: /Tengo un código/i }));
    await user.type(screen.getByLabelText(/Código de recuperación de contraseña/i), "c0d1g0");
    await user.type(screen.getByLabelText(/^Nueva contraseña/), "NuevaClave2026x");
    await user.type(screen.getByLabelText(/Confirmar nueva contraseña/i), "NuevaClave2026x");
    await user.click(screen.getByRole("button", { name: /Restablecer contraseña/i }));

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent(/Por seguridad se cerraron todas sus sesiones/);
    });

    expect(storageSpy).not.toHaveBeenCalled();

    storageSpy.mockRestore();
  });
});
