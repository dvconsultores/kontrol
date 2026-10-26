import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { describe, expect, it, beforeEach, vi } from "vitest";

import { ApiError } from "@/api/client";
import type { MfaChallengeLogin, MfaEnrollmentLogin } from "@/api/types";

const completeLogin = vi.fn();
const mockLogin = vi.fn();
const notify = vi.fn();
vi.mock("@/app/contexts/AuthContext", () => ({
  useAuth: () => ({
    isAuthenticated: false,
    login: mockLogin,
    completeLogin,
  }),
}));
vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify }),
}));
const verifyMfa = vi.fn();
vi.mock("@/api/mfa", () => ({ verifyMfa: (...args: unknown[]) => verifyMfa(...args) }));
const apiFetch = vi.fn();
vi.mock("@/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

import { LoginPage } from "./LoginPage";

function setupChallenge(methods: MfaChallengeLogin["methods"] = ["TOTP", "RECOVERY_CODE"]): void {
  mockLogin.mockResolvedValue({
    status: "MFA_REQUIRED",
    challenge_token: "challenge-token",
    expires_in: 300,
    methods,
  } satisfies MfaChallengeLogin);
}

function renderPage(): ReturnType<typeof render> {
  return render(
    <MemoryRouter>
      <LoginPage />
    </MemoryRouter>,
  );
}

describe("LoginPage MFA", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiFetch.mockResolvedValue({ initialized: true });
  });

  it("MFA_REQUIRED muestra el paso 2 con el campo one-time-code enfocado", async () => {
    setupChallenge();
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/Empresa/i), "kont");
    await user.type(screen.getByLabelText(/Usuario/i), "admin");
    await user.type(screen.getByLabelText(/Contraseña/i), "secret");
    await user.click(screen.getByRole("button", { name: /Iniciar sesión/i }));

    const codeInput = await screen.findByLabelText(/Código de verificación/i);
    expect(codeInput).toHaveFocus();
    expect(codeInput).toHaveAttribute("autocomplete", "one-time-code");
    expect(screen.getByRole("heading", { name: "Verificación en dos pasos" })).toBeInTheDocument();
  });

  it("código mal formado no llama a verifyMfa y muestra el error", async () => {
    setupChallenge(["TOTP"]);
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/Empresa/i), "kont");
    await user.type(screen.getByLabelText(/Usuario/i), "admin");
    await user.type(screen.getByLabelText(/Contraseña/i), "secret");
    await user.click(screen.getByRole("button", { name: /Iniciar sesión/i }));

    const codeInput = await screen.findByLabelText(/Código de verificación/i);
    await user.type(codeInput, "123");
    await user.click(screen.getByRole("button", { name: /Verificar/i }));

    expect(await screen.findByText("Introduzca los 6 dígitos del código")).toBeInTheDocument();
    expect(verifyMfa).not.toHaveBeenCalled();
  });

  it("MFA_INVALID_CODE con attempts_remaining 4 muestra el mensaje", async () => {
    setupChallenge(["TOTP"]);
    verifyMfa.mockRejectedValue(
      new ApiError(401, {
        code: "MFA_INVALID_CODE",
        message: "x",
        details: { attempts_remaining: 4 },
      }),
    );
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/Empresa/i), "kont");
    await user.type(screen.getByLabelText(/Usuario/i), "admin");
    await user.type(screen.getByLabelText(/Contraseña/i), "secret");
    await user.click(screen.getByRole("button", { name: /Iniciar sesión/i }));

    const codeInput = await screen.findByLabelText(/Código de verificación/i);
    await user.type(codeInput, "123456");
    await user.click(screen.getByRole("button", { name: /Verificar/i }));

    expect(await screen.findByText("Código incorrecto. Le quedan 4 intentos.")).toBeInTheDocument();
  });

  it("alternar a código de recuperación cambia el campo y envía recoveryCode", async () => {
    setupChallenge(["TOTP", "RECOVERY_CODE"]);
    verifyMfa.mockResolvedValue({
      status: "AUTHENTICATED",
      access_token: "token",
      token_type: "bearer",
      expires_in: 300,
      must_change_password: false,
      user: { id: "u1", username: "admin" },
      recovery_codes_remaining: 5,
    });
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/Empresa/i), "kont");
    await user.type(screen.getByLabelText(/Usuario/i), "admin");
    await user.type(screen.getByLabelText(/Contraseña/i), "secret");
    await user.click(screen.getByRole("button", { name: /Iniciar sesión/i }));

    await screen.findByLabelText(/Código de verificación/i);
    await user.click(screen.getByRole("button", { name: "Usar un código de recuperación" }));

    const recoveryInput = screen.getByLabelText(/Código de recuperación/i);
    expect(recoveryInput).toHaveAttribute("id", "recovery-code");
    expect(recoveryInput).toHaveAttribute("autocomplete", "off");

    await user.type(recoveryInput, "AAAA-BBBB-CCCC-DDDD");
    await user.click(screen.getByRole("button", { name: /Verificar/i }));

    await waitFor(() => {
      expect(verifyMfa).toHaveBeenCalledWith("challenge-token", { recoveryCode: "AAAA-BBBB-CCCC-DDDD" });
    });
  });

  it("MFA_CHALLENGE_INVALID vuelve al paso 1", async () => {
    setupChallenge(["TOTP"]);
    verifyMfa.mockRejectedValue(new ApiError(401, { code: "MFA_CHALLENGE_INVALID", message: "x" }));
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/Empresa/i), "kont");
    await user.type(screen.getByLabelText(/Usuario/i), "admin");
    await user.type(screen.getByLabelText(/Contraseña/i), "secret");
    await user.click(screen.getByRole("button", { name: /Iniciar sesión/i }));

    const codeInput = await screen.findByLabelText(/Código de verificación/i);
    await user.type(codeInput, "123456");
    await user.click(screen.getByRole("button", { name: /Verificar/i }));

    expect(await screen.findByText("La verificación caducó. Inicie sesión de nuevo.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "KONTROL" })).toBeInTheDocument();
    expect(screen.getByLabelText(/Contraseña/i)).toHaveValue("");
  });

  it("MFA_ENROLLMENT_REQUIRED navega a /acceso/mfa/alta con state y no en URL", async () => {
    const navigateState: MfaEnrollmentLogin = {
      status: "MFA_ENROLLMENT_REQUIRED",
      challenge_token: "enroll-challenge",
      expires_in: 300,
    };
    mockLogin.mockResolvedValue(navigateState);
    const user = userEvent.setup();

    const EnrollmentProbe = (): React.JSX.Element => {
      const location = useLocation();
      return (
        <div>
          <p>path:{location.pathname}</p>
          <p>search:{location.search}</p>
          <p>challenge:{location.state?.challengeToken}</p>
        </div>
      );
    };

    render(
      <MemoryRouter initialEntries={["/login"]}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/acceso/mfa/alta" element={<EnrollmentProbe />} />
        </Routes>
      </MemoryRouter>,
    );

    await user.type(screen.getByLabelText(/Empresa/i), "kont");
    await user.type(screen.getByLabelText(/Usuario/i), "admin");
    await user.type(screen.getByLabelText(/Contraseña/i), "secret");
    await user.click(screen.getByRole("button", { name: /Iniciar sesión/i }));

    await waitFor(() => {
      expect(screen.queryByLabelText(/Contraseña/i)).not.toBeInTheDocument();
    });
    expect(await screen.findByText("path:/acceso/mfa/alta")).toBeInTheDocument();
    expect(screen.getByText("search:")).toBeInTheDocument();
    expect(screen.getByText("challenge:enroll-challenge")).toBeInTheDocument();
  });

  it("no escribe en localStorage ni sessionStorage", async () => {
    setupChallenge(["TOTP", "RECOVERY_CODE"]);
    verifyMfa.mockResolvedValue({
      status: "AUTHENTICATED",
      access_token: "token",
      token_type: "bearer",
      expires_in: 300,
      must_change_password: false,
      user: { id: "u1", username: "admin" },
      recovery_codes_remaining: 5,
    });
    const storageSpy = vi.spyOn(Storage.prototype, "setItem");
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/Empresa/i), "kont");
    await user.type(screen.getByLabelText(/Usuario/i), "admin");
    await user.type(screen.getByLabelText(/Contraseña/i), "secret");
    await user.click(screen.getByRole("button", { name: /Iniciar sesión/i }));

    const codeInput = await screen.findByLabelText(/Código de verificación/i);
    await user.type(codeInput, "123456");
    await user.click(screen.getByRole("button", { name: /Verificar/i }));

    await waitFor(() => {
      expect(verifyMfa).toHaveBeenCalled();
    });
    expect(storageSpy).not.toHaveBeenCalled();
  });
});
