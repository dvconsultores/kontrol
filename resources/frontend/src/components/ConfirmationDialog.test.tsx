import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ConfirmationDialog } from "./ConfirmationDialog";

function renderDialogo(open: boolean, onCancel = vi.fn(), onConfirm = vi.fn(async () => {})) {
  return render(
    <>
      <button>Abrir</button>
      <ConfirmationDialog
        open={open}
        title="Confirmar acción"
        description="¿Seguro que quieres continuar?"
        onCancel={onCancel}
        onConfirm={onConfirm}
      />
    </>,
  );
}

describe("ConfirmationDialog · foco y teclado", () => {
  it("enfoca el botón de confirmar al abrir", () => {
    renderDialogo(true);
    expect(screen.getByRole("button", { name: "Confirmar" })).toHaveFocus();
  });

  it("Tab desde el último botón vuelve al primero", async () => {
    const usuario = userEvent.setup();
    renderDialogo(true);
    const confirmar = screen.getByRole("button", { name: "Confirmar" });
    const cancelar = screen.getByRole("button", { name: "Cancelar" });
    cancelar.focus();
    await usuario.tab();
    expect(confirmar).toHaveFocus();
  });

  it("Shift+Tab desde el primer botón va al último", async () => {
    const usuario = userEvent.setup();
    renderDialogo(true);
    const confirmar = screen.getByRole("button", { name: "Confirmar" });
    const cancelar = screen.getByRole("button", { name: "Cancelar" });
    confirmar.focus();
    await usuario.tab({ shift: true });
    expect(cancelar).toHaveFocus();
  });

  it("Escape llama onCancel", async () => {
    const usuario = userEvent.setup();
    const onCancel = vi.fn();
    renderDialogo(true, onCancel);
    await usuario.keyboard("{Escape}");
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("al cerrar devuelve el foco al botón que lo abrió", async () => {
    const { rerender } = renderDialogo(false);
    const abrir = screen.getByRole("button", { name: "Abrir" });
    abrir.focus();
    rerender(
      <>
        <button>Abrir</button>
        <ConfirmationDialog
          open={true}
          title="Confirmar acción"
          onCancel={vi.fn()}
          onConfirm={vi.fn(async () => {})}
        />
      </>,
    );
    expect(abrir).not.toHaveFocus();
    rerender(
      <>
        <button>Abrir</button>
        <ConfirmationDialog
          open={false}
          title="Confirmar acción"
          onCancel={vi.fn()}
          onConfirm={vi.fn(async () => {})}
        />
      </>,
    );
    expect(abrir).toHaveFocus();
  });

  it("onConfirm se llama al pulsar Confirmar", async () => {
    const usuario = userEvent.setup();
    const onConfirm = vi.fn(async () => {});
    renderDialogo(true, vi.fn(), onConfirm);
    await usuario.click(screen.getByRole("button", { name: "Confirmar" }));
    expect(onConfirm).toHaveBeenCalledOnce();
  });
});
