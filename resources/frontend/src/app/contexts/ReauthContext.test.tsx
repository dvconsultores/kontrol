import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, beforeEach, vi } from "vitest";
import { useState } from "react";

const setReauthHandler = vi.fn();
const notify = vi.fn();
const reauthenticate = vi.fn();

vi.mock("@/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/client")>();
  return {
    ...actual,
    setReauthHandler: (...args: unknown[]) => setReauthHandler(...args),
  };
});
vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify }),
}));
vi.mock("@/api/mfa", () => ({
  reauthenticate: (...args: unknown[]) => reauthenticate(...args),
}));

import { ReauthProvider } from "./ReauthContext";
import { ApiError } from "@/api/client";

function setup(): ReturnType<typeof render> {
  return render(
    <ReauthProvider>
      <TestInvoker />
    </ReauthProvider>,
  );
}

function TestInvoker(): React.JSX.Element {
  const [done, setDone] = useState<string>("");
  const handleClick = async (): Promise<void> => {
    const handler = setReauthHandler.mock.calls[0]?.[0] as (() => Promise<boolean>) | undefined;
    if (handler) {
      const ok = await handler();
      setDone(ok ? "true" : "false");
    }
  };
  return (
    <div>
      <button onClick={() => void handleClick()}>Invoke</button>
      {done ? <p>RESULT: {done}</p> : null}
    </div>
  );
}

describe("ReauthProvider", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setReauthHandler.mockClear();
    notify.mockClear();
    reauthenticate.mockClear();
  });

  it("registra el handler y resuelve true al confirmar con contraseña y código", async () => {
    reauthenticate.mockResolvedValue({});
    const user = userEvent.setup();
    setup();

    await user.click(screen.getByRole("button", { name: "Invoke" }));
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(screen.getByLabelText(/Contraseña/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Código de verificación/i)).toBeInTheDocument();

    await user.type(screen.getByLabelText(/Contraseña/i), "secret");
    await user.type(screen.getByLabelText(/Código de verificación/i), "123456");
    await user.click(screen.getByRole("button", { name: "Confirmar" }));

    await waitFor(() => {
      expect(reauthenticate).toHaveBeenCalledWith("secret", { code: "123456" });
    });
    expect(await screen.findByText("RESULT: true")).toBeInTheDocument();
  });

  it("REAUTH_FAILED mantiene el diálogo abierto con el mensaje", async () => {
    reauthenticate.mockRejectedValue(new ApiError(403, { code: "REAUTH_FAILED", message: "x" }));
    const user = userEvent.setup();
    setup();

    await user.click(screen.getByRole("button", { name: "Invoke" }));
    await screen.findByRole("dialog");

    await user.type(screen.getByLabelText(/Contraseña/i), "secret");
    await user.click(screen.getByRole("button", { name: "Confirmar" }));

    expect(await screen.findByText("Contraseña o código incorrectos.")).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("cancelar resuelve false", async () => {
    const user = userEvent.setup();
    setup();

    await user.click(screen.getByRole("button", { name: "Invoke" }));
    await screen.findByRole("dialog");
    await user.click(screen.getByRole("button", { name: "Cancelar" }));

    expect(await screen.findByText("RESULT: false")).toBeInTheDocument();
  });

  it("alternar a código de recuperación envía { recoveryCode }", async () => {
    reauthenticate.mockResolvedValue({});
    const user = userEvent.setup();
    setup();

    await user.click(screen.getByRole("button", { name: "Invoke" }));
    await screen.findByRole("dialog");
    await user.click(screen.getByRole("button", { name: "Usar un código de recuperación" }));

    expect(screen.getByLabelText(/Código de recuperación/i)).toBeInTheDocument();
    await user.type(screen.getByLabelText(/Contraseña/i), "secret");
    await user.type(screen.getByLabelText(/Código de recuperación/i), "AAAA-BBBB");
    await user.click(screen.getByRole("button", { name: "Confirmar" }));

    await waitFor(() => {
      expect(reauthenticate).toHaveBeenCalledWith("secret", { recoveryCode: "AAAA-BBBB" });
    });
    expect(await screen.findByText("RESULT: true")).toBeInTheDocument();
  });

  it("al abrir, la contraseña tiene el foco", async () => {
    reauthenticate.mockResolvedValue({});
    const user = userEvent.setup();
    setup();

    await user.click(screen.getByRole("button", { name: "Invoke" }));
    await screen.findByRole("dialog");

    expect(screen.getByLabelText(/Contraseña/i)).toHaveFocus();
  });

  it("una segunda invocación del handler vuelve a abrir el diálogo y también resuelve", async () => {
    reauthenticate.mockResolvedValue({ reauth_valid_until: "2026-01-01T00:00:00Z" });
    const user = userEvent.setup();
    setup();

    const invoke = async (): Promise<string> => {
      const handler = setReauthHandler.mock.calls[0]?.[0] as (() => Promise<boolean>) | undefined;
      if (!handler) {
        return "missing";
      }
      return (await handler()) ? "true" : "false";
    };

    await user.click(screen.getByRole("button", { name: "Invoke" }));
    await screen.findByRole("dialog");
    await user.type(screen.getByLabelText(/Contraseña/i), "secret");
    await user.click(screen.getByRole("button", { name: "Confirmar" }));
    await screen.findByText("RESULT: true");

    const segunda = invoke();
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    await user.type(screen.getByLabelText(/Contraseña/i), "secret");
    await user.click(screen.getByRole("button", { name: "Confirmar" }));
    expect(await segunda).toBe("true");
    expect(reauthenticate).toHaveBeenCalledTimes(2);
  });
});
