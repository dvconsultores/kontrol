import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, beforeEach, vi } from "vitest";

import { ApiError } from "@/api/client";

const completeLogin = vi.fn();
vi.mock("@/app/contexts/AuthContext", () => ({
  useAuth: () => ({
    completeLogin,
    isAuthenticated: false,
  }),
}));
const notify = vi.fn();
vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify }),
}));
const startEnrollment = vi.fn();
const confirmEnrollment = vi.fn();
vi.mock("@/api/mfa", () => ({
  startEnrollment: (...args: unknown[]) => startEnrollment(...args),
  confirmEnrollment: (...args: unknown[]) => confirmEnrollment(...args),
}));

import { MfaAltaPage } from "./MfaAltaPage";

function renderWithChallenge(challengeToken = "challenge-token"): ReturnType<typeof render> {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  window.history.replaceState({}, "", "/acceso/mfa/alta");
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[{ pathname: "/acceso/mfa/alta", state: { challengeToken, tenantCode: "kont", username: "admin" } }]}>
        <Routes>
          <Route path="/acceso/mfa/alta" element={<MfaAltaPage />} />
          <Route path="/login" element={<div>LOGIN</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("MfaAltaPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("sin state en la ruta pública redirige a /login", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/acceso/mfa/alta"]}>
          <Routes>
            <Route path="/acceso/mfa/alta" element={<MfaAltaPage />} />
            <Route path="/login" element={<div>LOGIN</div>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(await screen.findByText("LOGIN")).toBeInTheDocument();
  });

  it("recorrido completo desde Comenzar hasta completeLogin", async () => {
    startEnrollment.mockResolvedValue({
      otpauth_uri: "otpauth://totp/kontrol?secret=ABC",
      manual_key: "ABCDEFGH",
      qr_svg_data_uri: "data:image/svg+xml,<svg></svg>",
      expires_in: 300,
    });
    const loginResponse = {
      status: "AUTHENTICATED",
      access_token: "token",
      token_type: "bearer",
      expires_in: 300,
      must_change_password: false,
      user: { id: "u1", username: "admin" },
      recovery_codes: ["AAAA-BBBB-CCCC-DDDD"],
      recovery_codes_remaining: 10,
    };
    confirmEnrollment.mockResolvedValue(loginResponse);
    const user = userEvent.setup();
    renderWithChallenge();

    await user.click(screen.getByRole("button", { name: /Comenzar/i }));

    const img = await screen.findByAltText(/Código QR para su aplicación/i);
    expect(img).toHaveAttribute("src", "data:image/svg+xml,<svg></svg>");
    expect(screen.getByText("ABCDEFGH")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Siguiente/i }));

    const codeInput = await screen.findByLabelText(/Código de verificación/i);
    await user.type(codeInput, "123456");
    await user.click(screen.getByRole("button", { name: /Verificar/i }));

    expect(await screen.findByText("AAAA-BBBB-CCCC-DDDD")).toBeInTheDocument();
    expect(confirmEnrollment).toHaveBeenCalledTimes(1);

    const continueButton = screen.getByRole("button", { name: /Continuar/i });
    expect(continueButton).toBeDisabled();

    await user.click(screen.getByLabelText(/He guardado mis códigos/i));
    expect(continueButton).toBeEnabled();

    await user.click(continueButton);
    await waitFor(() => {
      expect(completeLogin).toHaveBeenCalledWith(loginResponse);
    });
    expect(confirmEnrollment).toHaveBeenCalledTimes(1);
  });

  it("MFA_NO_PENDING_ENROLLMENT vuelve al paso 1 con su mensaje", async () => {
    startEnrollment.mockResolvedValue({
      otpauth_uri: "otpauth://totp/kontrol?secret=ABC",
      manual_key: "ABCDEFGH",
      qr_svg_data_uri: "data:image/svg+xml,<svg></svg>",
      expires_in: 300,
    });
    confirmEnrollment.mockRejectedValue(new ApiError(404, { code: "MFA_NO_PENDING_ENROLLMENT", message: "x" }));
    const user = userEvent.setup();
    renderWithChallenge();

    await user.click(screen.getByRole("button", { name: /Comenzar/i }));
    await screen.findByText("ABCDEFGH");
    await user.click(screen.getByRole("button", { name: /Siguiente/i }));

    const codeInput = await screen.findByLabelText(/Código de verificación/i);
    await user.type(codeInput, "123456");
    await user.click(screen.getByRole("button", { name: /Verificar/i }));

    expect(await screen.findByText("El alta caducó o se reinició en otra ventana. Empiece de nuevo.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Comenzar/i })).toBeInTheDocument();
  });

  it("alta con sesión: al terminar invalida el estado MFA y vuelve a /seguridad/mfa", async () => {
    startEnrollment.mockResolvedValue({
      otpauth_uri: "otpauth://totp/kontrol?secret=ABC",
      manual_key: "ABCDEFGH",
      qr_svg_data_uri: "data:image/svg+xml,<svg></svg>",
      expires_in: 300,
    });
    confirmEnrollment.mockResolvedValue({
      recovery_codes: [
        "AAAA-BBBB-CCCC-DDDD",
        "EEEE-FFFF-GGGG-HHHH",
        "IIII-JJJJ-KKKK-LLLL",
        "MMMM-NNNN-OOOO-PPPP",
        "QQQQ-RRRR-SSSS-TTTT",
        "UUUU-VVVV-WWWW-XXXX",
        "YYYY-ZZZZ-AAAA-BBBB",
        "CCCC-DDDD-EEEE-FFFF",
        "GGGG-HHHH-IIII-JJJJ",
        "KKKK-LLLL-MMMM-NNNN",
      ],
    });
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const spy = vi.spyOn(queryClient, "invalidateQueries");
    const user = userEvent.setup();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/seguridad/mfa/alta"]}>
          <Routes>
            <Route path="/seguridad/mfa/alta" element={<MfaAltaPage />} />
            <Route path="/seguridad/mfa" element={<div>MI MFA</div>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await user.click(screen.getByRole("button", { name: /Comenzar/i }));
    await screen.findByAltText(/Código QR para su aplicación/i);
    await user.click(screen.getByRole("button", { name: /Siguiente/i }));

    const codeInput = await screen.findByLabelText(/Código de verificación/i);
    await user.type(codeInput, "123456");
    await user.click(screen.getByRole("button", { name: /Verificar/i }));

    const continueButton = await screen.findByRole("button", { name: /Continuar/i });
    await user.click(screen.getByLabelText(/He guardado mis códigos/i));
    await user.click(continueButton);

    await waitFor(() => {
      expect(spy).toHaveBeenCalledWith({ queryKey: ["security", "mfa"] });
    });
    expect(await screen.findByText("MI MFA")).toBeInTheDocument();
    expect(completeLogin).not.toHaveBeenCalled();
  });
});
