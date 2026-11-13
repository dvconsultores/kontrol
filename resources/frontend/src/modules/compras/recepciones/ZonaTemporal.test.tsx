import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiFetch = vi.fn();
vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({ estado: "LISTA", tiene: () => true, puede: () => true, motivo: () => null, motivoDeCapacidad: () => null }),
}));

const { ApiError } = await import("@/api/client");
const { ZonaTemporal } = await import("./ZonaTemporal");

beforeEach(() => apiFetch.mockReset());

function renderZonaTemporal(onGuardada: () => void | Promise<void>) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ZonaTemporal receiptId="r1" codigo="REC-1" onGuardada={onGuardada} />
    </QueryClientProvider>,
  );
}

describe("ZonaTemporal", () => {
  it("lists options and posts the chosen one", async () => {
    apiFetch.mockResolvedValueOnce({
      items: [
        { id: "l1", label: "A - Primera" },
        { id: "l2", label: "B - Segunda" },
      ],
    });
    const onGuardada = vi.fn().mockResolvedValue(undefined);
    renderZonaTemporal(onGuardada);

    const select = await screen.findByLabelText("Zona temporal de REC-1");
    expect(select).not.toBeNull();

    await screen.findByRole("option", { name: "B - Segunda" });
    fireEvent.change(select, { target: { value: "l2" } });
    fireEvent.click(
      screen.getByRole("button", {
        name: "Registrar zona temporal de REC-1",
      }),
    );

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        "/purchasing/receipts/r1/temporary-zone",
        { method: "POST", body: { temporary_location_id: "l2" } },
      ),
    );
    await waitFor(() => expect(onGuardada).toHaveBeenCalled());
  });

  it("shows alert and does not POST when no option is chosen", async () => {
    apiFetch.mockResolvedValueOnce({ items: [{ id: "l1", label: "A" }] });
    const onGuardada = vi.fn().mockResolvedValue(undefined);
    renderZonaTemporal(onGuardada);

    await screen.findByLabelText("Zona temporal de REC-1");
    fireEvent.click(
      screen.getByRole("button", {
        name: "Registrar zona temporal de REC-1",
      }),
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Elija la zona temporal.",
    );
    expect(apiFetch).not.toHaveBeenCalledWith(
      "/purchasing/receipts/r1/temporary-zone",
      expect.anything(),
    );
    expect(onGuardada).not.toHaveBeenCalled();
  });

  it("shows backend message when POST rejects", async () => {
    apiFetch.mockResolvedValueOnce({ items: [{ id: "l1", label: "A" }] });
    apiFetch.mockRejectedValueOnce(
      new ApiError(409, {
        code: "LOCATION_NOT_ELIGIBLE",
        message: "La ubicación no está activa (estado INACTIVE).",
      }),
    );
    const onGuardada = vi.fn().mockResolvedValue(undefined);
    renderZonaTemporal(onGuardada);

    const select = await screen.findByLabelText("Zona temporal de REC-1");
    await screen.findByRole("option", { name: "A" });
    fireEvent.change(select, { target: { value: "l1" } });
    fireEvent.click(
      screen.getByRole("button", {
        name: "Registrar zona temporal de REC-1",
      }),
    );

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        "La ubicación no está activa (estado INACTIVE).",
      ),
    );
    expect(onGuardada).not.toHaveBeenCalled();
  });
});
