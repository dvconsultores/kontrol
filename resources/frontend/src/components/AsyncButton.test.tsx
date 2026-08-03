import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AsyncButton } from "./AsyncButton";

describe("AsyncButton", () => {
  it("muestra loader y deshabilita mientras ejecuta (FR-003/004)", async () => {
    const user = userEvent.setup();
    let resolve!: () => void;
    const onClick = vi.fn(
      () =>
        new Promise<void>((r) => {
          resolve = r;
        }),
    );
    render(
      <AsyncButton onClick={onClick} loadingText="Guardando…">
        Guardar
      </AsyncButton>,
    );

    await user.click(screen.getByRole("button", { name: "Guardar" }));
    expect(onClick).toHaveBeenCalledTimes(1);

    const loadingButton = screen.getByRole("button", { name: /Guardando/ });
    expect(loadingButton).toBeDisabled();
    expect(screen.getByText("Guardando…")).toBeInTheDocument();

    resolve();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Guardar" })).toBeEnabled();
    });
  });

  it("previene doble envío (FR-004)", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn(async () => {
      await new Promise((r) => setTimeout(r, 20));
    });
    render(<AsyncButton onClick={onClick}>Procesar</AsyncButton>);

    const button = screen.getByRole("button", { name: "Procesar" });
    await user.click(button);
    await user.click(button);
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
