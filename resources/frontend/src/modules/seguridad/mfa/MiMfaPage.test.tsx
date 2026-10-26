import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, beforeEach, vi } from "vitest";

const notify = vi.fn();
vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify }),
}));

const getMfaStatus = vi.fn();
const regenerateRecoveryCodes = vi.fn();
const removeOwnFactor = vi.fn();
vi.mock("@/api/mfa", () => ({
  getMfaStatus: (...args: unknown[]) => getMfaStatus(...args),
  regenerateRecoveryCodes: (...args: unknown[]) => regenerateRecoveryCodes(...args),
  removeOwnFactor: (...args: unknown[]) => removeOwnFactor(...args),
}));

import { MiMfaPage } from "./MiMfaPage";

function setup(data: unknown) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  getMfaStatus.mockResolvedValue(data);
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/seguridad/mfa"]}>
        <Routes>
          <Route path="/seguridad/mfa" element={<MiMfaPage />} />
          <Route path="/seguridad/mfa/alta" element={<div>ALTA PAGE</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("MiMfaPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    notify.mockClear();
    getMfaStatus.mockClear();
    regenerateRecoveryCodes.mockClear();
    removeOwnFactor.mockClear();
  });

  it("sin factor y required muestra el aviso y Configurar", async () => {
    setup({ enabled: false, required: true, activated_at: null, recovery_codes_remaining: 0, policy_class: "PRIVILEGED" });
    expect(await screen.findByText("Desactivada")).toBeInTheDocument();
    expect(screen.getByText("Su rol exige verificación en dos pasos.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Configurar" })).toBeInTheDocument();
  });

  it("con factor muestra la fecha y N códigos", async () => {
    setup({ enabled: true, required: true, activated_at: "2025-01-15T10:00:00Z", recovery_codes_remaining: 9, policy_class: "PRIVILEGED" });
    expect(await screen.findByText(/Activa desde/i)).toBeInTheDocument();
    expect(screen.getByText(/Códigos de recuperación disponibles:/i)).toBeInTheDocument();
    expect(screen.getByText("9")).toBeInTheDocument();
  });

  it("con required NO muestra «Quitar la verificación»", async () => {
    setup({ enabled: true, required: true, activated_at: "2025-01-15T10:00:00Z", recovery_codes_remaining: 9, policy_class: "PRIVILEGED" });
    await screen.findByText(/Activa desde/i);
    expect(screen.queryByRole("button", { name: "Quitar la verificación" })).not.toBeInTheDocument();
    expect(screen.getByText("Su política no permite quitarla")).toBeInTheDocument();
  });

  it("STANDARD con factor: quitar → confirmación → removeOwnFactor", async () => {
    setup({ enabled: true, required: false, activated_at: "2025-01-15T10:00:00Z", recovery_codes_remaining: 9, policy_class: "STANDARD" });
    await screen.findByText(/Activa desde/i);
    const btn = screen.getByRole("button", { name: "Quitar la verificación" });
    expect(btn).toBeInTheDocument();

    const user = userEvent.setup();
    await user.click(btn);
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    removeOwnFactor.mockResolvedValue(undefined);

    await user.click(screen.getByRole("button", { name: "Quitar" }));
    await waitFor(() => {
      expect(removeOwnFactor).toHaveBeenCalledTimes(1);
    });
    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith(
        expect.objectContaining({ title: "Verificación quitada" }),
      );
    });
  });

  it("regenerar muestra los códigos nuevos", async () => {
    setup({ enabled: true, required: true, activated_at: "2025-01-15T10:00:00Z", recovery_codes_remaining: 2, policy_class: "PRIVILEGED" });
    await screen.findByText(/Activa desde/i);
    regenerateRecoveryCodes.mockResolvedValue({ recovery_codes: ["AAAA-BBBB-CCCC-DDDD"] });
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Generar códigos nuevos" }));

    expect(await screen.findByText("AAAA-BBBB-CCCC-DDDD")).toBeInTheDocument();
    expect(screen.getByLabelText(/He guardado mis códigos/i)).toBeInTheDocument();
  });
});
