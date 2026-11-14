import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiFetch = vi.fn();
vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({
    estado: "LISTA",
    tiene: () => true,
    puede: () => true,
    motivo: () => null,
    motivoDeCapacidad: () => null,
  }),
}));

const notify = vi.fn();
vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify, dismiss: vi.fn(), notifications: [] }),
}));

import { ApiError } from "@/api/client";
import { ConfirmacionPage } from "./ConfirmacionPage";

const item = {
  receipt_line_id: "l1",
  product_id: "6f1c2d3e-0000-4000-8000-000000000001",
  product_code: "P-1",
  product_name: "Arroz",
  base_quantity_received: "100.000000",
  base_quantity_ordered: "500.000000",
  counted_base_quantity: "100.000000",
  counted: true,
  matches_order: false,
  matches_physical: true,
  difference_kinds: [] as string[],
  already_confirmed_base: "0.000000",
  pending_base: "100.000000",
  base_quantity_accepted: "80.000000",
  pending_decision_base: "80.000000",
};

function mockApi(posteado?: () => ReturnType<typeof apiFetch>) {
  apiFetch.mockImplementation((url: string, opts?: { method?: string; body?: unknown }) => {
    if (url === "/purchasing/receipts") {
      return Promise.resolve({
        items: [{ id: "r1", code: "RC-1", status: "PARTIALLY_ACCEPTED" }],
      });
    }
    if (url === "/purchasing/settings/receipt-count") {
      return Promise.resolve({
        receipt_count_same_user_allowed: false,
        independent_count_required: true,
      });
    }
    if (url === "/purchasing/receipts/r1/conciliacion") {
      return Promise.resolve({
        confirmation_status: "PENDIENTE",
        ready_for_confirmation: true,
        incidents: { total: 0, unresolved: 0, ready_for_confirmation: true },
        quality_status: "APPROVED",
        packing_list_match: null,
        lines_pending_count: [],
        items: [item],
      });
    }
    if (url === "/purchasing/receipts/r1/confirmacion-inventario") {
      if (opts?.method === "POST") {
        if (posteado) return posteado();
        return Promise.resolve({ items: [] });
      }
      return Promise.resolve({ items: [] });
    }
    return Promise.reject(new Error(`No mock para ${url}`));
  });
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter(
    [{ path: "/inventario/confirmacion", element: <ConfirmacionPage /> }],
    { initialEntries: ["/inventario/confirmacion?recepcion=r1"] },
  );
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiFetch.mockReset();
  notify.mockReset();
});

describe("ConfirmacionPage", () => {
  it("muestra producto, cantidad aceptada y pendiente sin UUID", async () => {
    mockApi();
    renderPage();
    await screen.findByText(/P-1 · Arroz/);
    expect(screen.getByText("Cantidad aceptada: 80")).toBeTruthy();
    expect(screen.getByText("Pendiente por decidir: 80")).toBeTruthy();
    expect(document.body.textContent ?? "").not.toContain("6f1c2d3e");
  });

  it("50 disponible + 10 rechazada => pendiente 20 y botón deshabilitado", async () => {
    mockApi();
    renderPage();
    await screen.findByText(/P-1 · Arroz/);
    fireEvent.change(screen.getByLabelText(/A disponible/), { target: { value: "50" } });
    fireEvent.change(screen.getByLabelText(/^Rechazada/), { target: { value: "10" } });
    expect(screen.getByText("Pendiente por decidir: 20")).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Confirmar inventario" }).hasAttribute("disabled"),
    ).toBe(true);
  });

  it("70 + 20 excede lo aceptado", async () => {
    mockApi();
    renderPage();
    await screen.findByText(/P-1 · Arroz/);
    fireEvent.change(screen.getByLabelText(/A disponible/), { target: { value: "70" } });
    fireEvent.change(screen.getByLabelText(/^Rechazada/), { target: { value: "20" } });
    expect(screen.getByText("Excede lo aceptado en 10.")).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Confirmar inventario" }).hasAttribute("disabled"),
    ).toBe(true);
  });

  it("60 + 20 exige motivo y envía las dos decisiones completas", async () => {
    mockApi();
    renderPage();
    await screen.findByText(/P-1 · Arroz/);
    const boton = () => screen.getByRole("button", { name: "Confirmar inventario" });
    fireEvent.change(screen.getByLabelText(/A disponible/), { target: { value: "60" } });
    fireEvent.change(screen.getByLabelText(/^Rechazada/), { target: { value: "20" } });
    expect(boton().hasAttribute("disabled")).toBe(true);
    fireEvent.change(screen.getByLabelText(/Motivo del rechazo/), {
      target: { value: "No apto" },
    });
    await waitFor(() => expect(boton().hasAttribute("disabled")).toBe(false));
    fireEvent.click(boton());
    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        "/purchasing/receipts/r1/confirmacion-inventario",
        {
          method: "POST",
          body: {
            decisions: [
              { receipt_line_id: "l1", target_state: "DISPONIBLE", base_quantity: "60" },
              {
                receipt_line_id: "l1",
                target_state: "RECHAZADO",
                base_quantity: "20",
                reason: "No apto",
              },
            ],
          },
        },
      ),
    );
  });

  it("muestra tal cual el mensaje del backend cuando falta repartir", async () => {
    mockApi(() =>
      Promise.reject(
        new ApiError(422, {
          code: "RECEIPT_CONFIRMATION_INCOMPLETE",
          message:
            "Debe decidirse la totalidad de la cantidad aceptada antes de confirmar el inventario.",
        }),
      ),
    );
    renderPage();
    await screen.findByText(/P-1 · Arroz/);
    fireEvent.change(screen.getByLabelText(/A disponible/), { target: { value: "60" } });
    fireEvent.change(screen.getByLabelText(/^Rechazada/), { target: { value: "20" } });
    fireEvent.change(screen.getByLabelText(/Motivo del rechazo/), {
      target: { value: "No apto" },
    });
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Confirmar inventario" }).hasAttribute("disabled"),
      ).toBe(false),
    );
    fireEvent.click(screen.getByRole("button", { name: "Confirmar inventario" }));
    await waitFor(() =>
      expect(notify).toHaveBeenCalledWith({
        type: "error",
        title: "No se confirmó el inventario",
        description:
          "Debe decidirse la totalidad de la cantidad aceptada antes de confirmar el inventario.",
      }),
    );
  });
});
