import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi, Mock } from "vitest";

import { CompanySelector } from "./CompanySelector";
import { useCompany } from "@/app/contexts/CompanyContext";

let gobiernoHabilitado = false;

vi.mock("@/modules/gobierno/api", async (original) => ({
  ...(await original<typeof import("@/modules/gobierno/api")>()),
  useModuloGobierno: () => gobiernoHabilitado,
}));

vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: vi.fn(),
}));

const mockUseCompany = useCompany as Mock;

const companies = [
  {
    id: "empresa-a",
    legal_name: "Demo C.A.",
    code: "D1",
    rif: "J-00000000-0",
    status: "ACTIVE",
  },
  {
    id: "empresa-b",
    legal_name: "Otra C.A.",
    code: "D2",
    rif: "J-00000000-1",
    status: "ACTIVE",
  },
];

function mockCompanyContext(activeCompany: (typeof companies)[0]) {
  mockUseCompany.mockReturnValue({
    companies,
    activeCompany,
    estado: null,
    selectCompany: vi.fn(),
  });
}

describe("CompanySelector", () => {
  it("CSEL-01 · con Gobierno habilitado anuncia \"Cambiar de ente\"", () => {
    gobiernoHabilitado = true;
    mockCompanyContext(companies[0]);
    render(<CompanySelector />);

    const boton = screen.getByTestId("selector-empresa");
    expect(boton).toHaveAttribute(
      "aria-label",
      "Ente activo: Demo C.A.. Cambiar de ente",
    );
  });

  it("CSEL-02 · sin Gobierno anuncia \"Cambiar de empresa\"", () => {
    gobiernoHabilitado = false;
    mockCompanyContext(companies[0]);
    render(<CompanySelector />);

    const boton = screen.getByTestId("selector-empresa");
    expect(boton).toHaveAttribute(
      "aria-label",
      "Empresa activa: Demo C.A.. Cambiar de empresa",
    );
  });
});
