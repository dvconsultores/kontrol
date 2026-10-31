/**
 * NotificationContext · sin duplicados (FR-001-063).
 * Verifica que no haya dos avisos iguales a la vez y que, al descartar
 * uno, el mismo aviso pueda volver a mostrarse.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { NotificationProvider, useNotifications } from "./NotificationContext";

function Sonda(): React.JSX.Element {
  const { notifications, notify, dismiss } = useNotifications();
  return (
    <div>
      <button
        onClick={() => notify({ type: "success", title: "Unidad registrada" })}
      >
        notificar
      </button>
      <button onClick={() => dismiss(notifications[0]?.id ?? "")}>
        descartar primero
      </button>
      <ul>
        {notifications.map((n) => (
          <li key={n.id}>{n.title}</li>
        ))}
      </ul>
    </div>
  );
}

describe("NotificationContext · sin duplicados (FR-001-063)", () => {
  it("NOT-01 · dos notify iguales seguidos muestran un solo aviso", async () => {
    const user = userEvent.setup();
    render(
      <NotificationProvider>
        <Sonda />
      </NotificationProvider>,
    );

    await user.click(screen.getByRole("button", { name: "notificar" }));
    await user.click(screen.getByRole("button", { name: "notificar" }));

    expect(screen.getAllByText("Unidad registrada")).toHaveLength(1);
  });

  it("NOT-02 · notify, dismiss y el mismo notify vuelve a mostrarse", async () => {
    const user = userEvent.setup();
    render(
      <NotificationProvider>
        <Sonda />
      </NotificationProvider>,
    );

    await user.click(screen.getByRole("button", { name: "notificar" }));
    await user.click(screen.getByRole("button", { name: "descartar primero" }));
    await user.click(screen.getByRole("button", { name: "notificar" }));

    expect(screen.getAllByText("Unidad registrada")).toHaveLength(1);
  });

  it("NOT-03 · avisos con distinta descripción conviven", async () => {
    const user = userEvent.setup();
    function SondaConDescripcion(): React.JSX.Element {
      const { notifications, notify } = useNotifications();
      return (
        <div>
          <button
            onClick={() =>
              notify({
                type: "success",
                title: "Unidad registrada",
                description: "primera",
              })
            }
          >
            notificar primera
          </button>
          <button
            onClick={() =>
              notify({
                type: "success",
                title: "Unidad registrada",
                description: "segunda",
              })
            }
          >
            notificar segunda
          </button>
          <ul>
            {notifications.map((n) => (
              <li key={n.id}>{n.description}</li>
            ))}
          </ul>
        </div>
      );
    }

    render(
      <NotificationProvider>
        <SondaConDescripcion />
      </NotificationProvider>,
    );

    await user.click(screen.getByRole("button", { name: "notificar primera" }));
    await user.click(screen.getByRole("button", { name: "notificar segunda" }));

    expect(screen.getByText("primera")).toBeTruthy();
    expect(screen.getByText("segunda")).toBeTruthy();
  });
});
