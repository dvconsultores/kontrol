import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";

import type { EstadoDePerfil } from "@/app/perfil/superficies";

import { RutaDePerfil } from "./RutaDePerfil";

let perfilMock: EstadoDePerfil = { estado: "RESUELTO", perfil: "EMPRESA" };

vi.mock("@/modules/gobierno/api", () => ({
  usePerfilDeInstalacion: () => perfilMock,
}));

function montar(ruta: string): void {
  render(
    <MemoryRouter initialEntries={[ruta]}>
      <RutaDePerfil>
        <p>Contenido permitido</p>
      </RutaDePerfil>
    </MemoryRouter>,
  );
}

describe("RutaDePerfil", () => {
  it("GOVPROF-15 · GOBIERNO en ruta de empresa muestra Acceso prohibido", () => {
    perfilMock = { estado: "RESUELTO", perfil: "GOBIERNO" };
    montar("/ventas/ordenes");
    expect(screen.getByRole("heading", { name: "Acceso prohibido" })).toBeInTheDocument();
    expect(screen.queryByText("Contenido permitido")).toBeNull();
  });

  it("GOBIERNO en ruta de gobierno deja pasar al hijo", () => {
    perfilMock = { estado: "RESUELTO", perfil: "GOBIERNO" };
    montar("/gobierno/ente");
    expect(screen.getByText("Contenido permitido")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Acceso prohibido" })).toBeNull();
  });

  it("GOBIERNO en ruta compartida deja pasar al hijo", () => {
    perfilMock = { estado: "RESUELTO", perfil: "GOBIERNO" };
    montar("/mi-licencia");
    expect(screen.getByText("Contenido permitido")).toBeInTheDocument();
  });

  it("EMPRESA en ruta de gobierno muestra Acceso prohibido", () => {
    perfilMock = { estado: "RESUELTO", perfil: "EMPRESA" };
    montar("/gobierno/ente");
    expect(screen.getByRole("heading", { name: "Acceso prohibido" })).toBeInTheDocument();
  });

  it("MIXTO deja pasar a gobierno y empresa", () => {
    perfilMock = { estado: "RESUELTO", perfil: "MIXTO" };
    montar("/gobierno/ente");
    expect(screen.getByText("Contenido permitido")).toBeInTheDocument();
    cleanup();
    montar("/ventas/ordenes");
    expect(screen.getByText("Contenido permitido")).toBeInTheDocument();
  });

  it("RESOLVIENDO en ruta de empresa muestra loading y no pinta el hijo", () => {
    perfilMock = { estado: "RESOLVIENDO" };
    montar("/ventas/ordenes");
    expect(screen.queryByText("Contenido permitido")).toBeNull();
    expect(screen.queryByRole("heading", { name: "Acceso prohibido" })).toBeNull();
  });

  it("GOVPROF-ERR · ERROR en ruta de empresa no pinta el hijo y explica el fallo (fail-closed)", () => {
    perfilMock = { estado: "ERROR" };
    montar("/ventas/ordenes");
    expect(screen.queryByText("Contenido permitido")).toBeNull();
    expect(
      screen.getByText(/No fue posible determinar el perfil de producto/),
    ).toBeInTheDocument();
    cleanup();
    montar("/gobierno/ente");
    expect(screen.queryByText("Contenido permitido")).toBeNull();
    expect(
      screen.getByText(/No fue posible determinar el perfil de producto/),
    ).toBeInTheDocument();
  });

  it("ERROR en ruta compartida deja pasar al hijo", () => {
    perfilMock = { estado: "ERROR" };
    montar("/mi-licencia");
    expect(screen.getByText("Contenido permitido")).toBeInTheDocument();
  });

  it("RESOLVIENDO en ruta compartida deja pasar al hijo", () => {
    perfilMock = { estado: "RESOLVIENDO" };
    montar("/mi-licencia");
    expect(screen.getByText("Contenido permitido")).toBeInTheDocument();
  });
});
