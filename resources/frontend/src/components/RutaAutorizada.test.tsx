import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it, vi } from "vitest";

import { AutoridadContext } from "@/app/autoridad/AutoridadContext";
import type { AutoridadValue } from "@/app/autoridad/AutoridadContext";
import type { AlcanceDeCapacidad } from "@/app/autoridad/AutoridadContext";
import type { Motivo } from "@/app/autoridad/operaciones";
import type { RequisitoDePantalla } from "@/app/autoridad/requisitos";
import { RutaAutorizada } from "@/components/RutaAutorizada";

vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({
    activeCompanyId: "empresa-1",
    companies: [
      { id: "empresa-1", code: "emp1", legal_name: "Empresa Uno" },
      { id: "empresa-2", code: "emp2", legal_name: "Empresa Dos" },
    ],
  }),
}));

function crearAutoridad(
  tiene: (capacidad: string, alcance: AlcanceDeCapacidad) => boolean,
  motivoDeCapacidad: (capacidad: string, alcance: AlcanceDeCapacidad) => Motivo | null,
  puede: (metodo: string, ruta: string) => boolean,
  motivo: (metodo: string, ruta: string) => Motivo | null,
): AutoridadValue {
  return {
    estado: "LISTA",
    tiene,
    motivoDeCapacidad,
    puede,
    motivo,
  };
}

function renderizarConRequisito(
  autoridad: AutoridadValue,
  requisito: RequisitoDePantalla | null,
): ReturnType<typeof render> {
  const router = createMemoryRouter([
    {
      path: "/",
      handle: { requisito },
      element: (
        <RutaAutorizada>
          <p>Contenido de la ruta</p>
        </RutaAutorizada>
      ),
    },
  ]);

  return render(
    <AutoridadContext.Provider value={autoridad}>
      <RouterProvider router={router} />
    </AutoridadContext.Provider>,
  );
}

describe("RutaAutorizada", () => {
  it("CARGANDO pinta el estado de carga", () => {
    const autoridad: AutoridadValue = {
      estado: "CARGANDO",
      tiene: () => true,
      motivoDeCapacidad: () => null,
      puede: () => true,
      motivo: () => null,
    };

    renderizarConRequisito(autoridad, {
      capacidad: "empresas.ver",
      alcance: "empresa",
    });

    expect(screen.queryByText("Contenido de la ruta")).toBeNull();
    expect(screen.getByRole("status")).toBeTruthy();
  });

  it("capacidad ausente con motivo COMPANY_SCOPE_FORBIDDEN → encabezado «Sin autoridad en esta empresa» y el nombre de la empresa", () => {
    const autoridad = crearAutoridad(
      () => false,
      () => "COMPANY_SCOPE_FORBIDDEN",
      () => true,
      () => null,
    );

    renderizarConRequisito(autoridad, {
      capacidad: "empresas.ver",
      alcance: "empresa",
    });

    expect(screen.getByRole("heading", { name: "Sin autoridad en esta empresa" })).toBeTruthy();
    expect(screen.getByText(/Empresa Uno/)).toBeTruthy();
  });

  it("alcance tenant → «Requiere autoridad en todas las empresas»", () => {
    const autoridad = crearAutoridad(
      () => false,
      () => "COMPANY_SCOPE_FORBIDDEN",
      () => true,
      () => null,
    );

    renderizarConRequisito(autoridad, {
      capacidad: "configuracion.gestionar",
      alcance: "tenant",
    });

    expect(
      screen.getByRole("heading", { name: "Requiere autoridad en todas las empresas" }),
    ).toBeTruthy();
  });

  it("PERMISSION_DENIED → «Acceso prohibido»", () => {
    const autoridad = crearAutoridad(
      () => false,
      () => "PERMISSION_DENIED",
      () => true,
      () => null,
    );

    renderizarConRequisito(autoridad, {
      capacidad: "empresas.ver",
      alcance: "empresa",
    });

    expect(screen.getByRole("heading", { name: "Acceso prohibido" })).toBeTruthy();
  });

  it("operación no autorizada aunque la capacidad sí → denegada", () => {
    const autoridad = crearAutoridad(
      () => true,
      () => null,
      () => false,
      () => "PERMISSION_DENIED",
    );

    renderizarConRequisito(autoridad, {
      capacidad: "empresas.ver",
      alcance: "empresa",
      operacion: ["GET", "/empresas"],
    });

    expect(screen.getByRole("heading", { name: "Acceso prohibido" })).toBeTruthy();
    expect(screen.queryByText("Contenido de la ruta")).toBeNull();
  });

  it("requisito null → contenido", () => {
    const autoridad = crearAutoridad(
      () => false,
      () => "PERMISSION_DENIED",
      () => false,
      () => "PERMISSION_DENIED",
    );

    renderizarConRequisito(autoridad, null);

    expect(screen.getByText("Contenido de la ruta")).toBeTruthy();
  });

  it("el contenedor de denegación tiene role alert", () => {
    const autoridad = crearAutoridad(
      () => false,
      () => "PERMISSION_DENIED",
      () => true,
      () => null,
    );

    renderizarConRequisito(autoridad, {
      capacidad: "empresas.ver",
      alcance: "empresa",
    });

    expect(screen.getByRole("alert")).toBeTruthy();
  });
});
