import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";

import { EstadoDeEmpresa } from "./EstadoDeEmpresa";

let modulo = false;

vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({
    estado: "COMPANY_SELECTION_REQUIRED",
    companies: [
      {
        id: "c1",
        code: "C1",
        legal_name: "Contenedor uno",
        rif: "J-1",
        status: "ACTIVE",
      },
    ],
    selectCompany: vi.fn(),
    refreshCompanies: vi.fn(),
  }),
}));

vi.mock("@/modules/gobierno/api", () => ({
  useModuloGobierno: () => modulo,
}));

function montar(ruta: string) {
  render(
    <MemoryRouter initialEntries={[ruta]}>
      <EstadoDeEmpresa />
    </MemoryRouter>,
  );
}

describe("EstadoDeEmpresa · compuerta de contexto (GOV0-UI-01)", () => {
  it("GUI-01 · en /gobierno/estructura con el módulo usa el texto de ente", () => {
    modulo = true;
    montar("/gobierno/estructura");
    expect(
      screen.getByRole("heading", { name: "Seleccione un ente" }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("elegir-empresa-C1")).toBeInTheDocument();
  });

  it("GUI-02 · en rutas privadas no gubernamentales usa el texto de empresa", () => {
    modulo = true;
    montar("/ventas/ordenes");
    expect(
      screen.getByRole("heading", { name: "Seleccione una empresa" }),
    ).toBeInTheDocument();
  });

  it("GUI-03 · en /gobierno/ente sin el módulo usa el texto de empresa", () => {
    modulo = false;
    montar("/gobierno/ente");
    expect(
      screen.getByRole("heading", { name: "Seleccione una empresa" }),
    ).toBeInTheDocument();
  });
});
