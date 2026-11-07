import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router";

import { ApiError } from "@/api/client";

import { BloqueoDeCierre, detalleDeBloqueoDeCierre } from "./BloqueoDeCierre";

describe("detalleDeBloqueoDeCierre", () => {
  it("BDC-01 · devuelve null para Error común, ApiError 409 con otro code y ApiError 422 con code GOV_MATERIAL_CLOSE_BLOCKED", () => {
    expect(detalleDeBloqueoDeCierre(new Error("boom"))).toBeNull();
    expect(
      detalleDeBloqueoDeCierre(
        new ApiError(409, { code: "OTRO_CODE", message: "otro" }),
      ),
    ).toBeNull();
    expect(
      detalleDeBloqueoDeCierre(
        new ApiError(422, { code: "GOV_MATERIAL_CLOSE_BLOCKED", message: "otro" }),
      ),
    ).toBeNull();
  });

  it("BDC-02 · extrae el detalle y tolera controles ausentes", () => {
    const detalle = detalleDeBloqueoDeCierre(
      new ApiError(409, {
        code: "GOV_MATERIAL_CLOSE_BLOCKED",
        message: "bloqueo material",
        details: {
          politica_codigo: "POL-2026-0001",
          politica_nombre: "Cierre material",
          proceso: "ORG02_CERRAR_ESTRUCTURA",
          objeto_codigo: "EST-2026",
          total: 2,
          dueno: "Oficina de Control",
        },
      }),
    );

    expect(detalle?.politica_codigo).toBe("POL-2026-0001");
    expect(detalle?.controles).toEqual([]);
  });
});

describe("BloqueoDeCierre", () => {
  it("BDC-03 · muestra política, proceso con etiqueta, objeto, total, dueño, materialidad y pendientes de cada control, enlaces a pendientes y a lista", async () => {
    const detalle = {
      politica_codigo: "POL-2026-0001",
      politica_nombre: "Política de cierre material",
      proceso: "ORG02_CERRAR_ESTRUCTURA",
      objeto_codigo: "EST-2026",
      total: 2,
      dueno: "Oficina de Control",
      controles: [
        {
          tipo: "HALLAZGOS_ABIERTOS" as const,
          etiqueta: "Hallazgos abiertos",
          materialidad: "Puede haber fraude",
          pendientes: 1,
          muestra: [
            {
              codigo: "HAL-001",
              numero: null,
              titulo: "Hallazgo de prueba",
              asunto: null,
              ruta: "/gobierno/hallazgos/HAL-001",
            },
          ],
          ruta_lista: "/gobierno/hallazgos",
        },
        {
          tipo: "ACTOS_SIN_EFICACIA" as const,
          etiqueta: "Actos sin eficacia",
          materialidad: "Compromisos no válidos",
          pendientes: 1,
          muestra: [],
          ruta_lista: "",
        },
      ],
    };

    render(
      <MemoryRouter>
        <BloqueoDeCierre detalle={detalle} onCerrar={() => {}} />
      </MemoryRouter>,
    );

    const alert = await screen.findByRole("alert", {
      name: "Cierre bloqueado por control material",
    });
    expect(alert).toHaveTextContent("POL-2026-0001");
    expect(alert).toHaveTextContent("Política de cierre material");
    expect(alert).toHaveTextContent("Cerrar estructura del ejercicio");
    expect(alert).toHaveTextContent("EST-2026");
    expect(alert).toHaveTextContent("2 pendiente(s)");
    expect(alert).toHaveTextContent("Puede haber fraude");
    expect(alert).toHaveTextContent("Pendientes: 1");
    expect(alert).toHaveTextContent("Compromisos no válidos");
    expect(alert).toHaveTextContent("Oficina de Control");

    expect(screen.getByRole("link", { name: "HAL-001 · Hallazgo de prueba" })).toHaveAttribute(
      "href",
      "/gobierno/hallazgos/HAL-001",
    );
    expect(screen.getByRole("link", { name: "Ir a la lista" })).toHaveAttribute(
      "href",
      "/gobierno/hallazgos",
    );
  });

  it("BDC-04 · onCerrar se llama con el botón Entendido", async () => {
    const onCerrar = vi.fn();
    const detalle = {
      politica_codigo: "POL-2026-0001",
      politica_nombre: "Política de cierre material",
      proceso: "ORG02_CERRAR_ESTRUCTURA",
      objeto_codigo: "EST-2026",
      total: 0,
      dueno: "Oficina de Control",
      controles: [],
    };

    render(
      <MemoryRouter>
        <BloqueoDeCierre detalle={detalle} onCerrar={onCerrar} />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole("button", { name: "Entendido" }));
    expect(onCerrar).toHaveBeenCalledTimes(1);
  });
});
