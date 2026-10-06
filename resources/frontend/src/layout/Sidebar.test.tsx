/**
 * NAV · El menú no enseña Diagnóstico a quien no puede verlo (FR-001-233).
 * Ocultar una entrada es solo cosmética: la autorización real la impone el backend, que es
 * la autoridad. Aquí comprobamos únicamente que el menú respeta el permiso declarado, de modo
 * que nadie vea accesos para los que no está autorizado.
 */
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

let permisos = new Set<string>();

vi.mock("@/app/contexts/AuthContext", () => ({
  useAuth: () => ({ hasPermission: (permiso: string) => permisos.has(permiso) }),
}));

const { Sidebar } = await import("./Sidebar");

function montar(): void {
  render(
    <MemoryRouter>
      <Sidebar />
    </MemoryRouter>,
  );
}

function enlace(nombre: string): HTMLElement | null {
  return screen.queryByRole("link", { name: nombre });
}

describe("Sidebar · Diagnóstico", () => {
  beforeEach(() => {
    permisos = new Set<string>();
  });

  it("NAV-01 · con license:view la entrada Diagnóstico está, y apunta a su ruta", () => {
    permisos = new Set(["license:view"]);
    montar();
    const d = enlace("Diagnóstico");
    expect(d).not.toBeNull();
    expect(d?.getAttribute("href")).toBe("/diagnostico");
    expect(enlace("Auditoría")).not.toBeNull();
  });

  it("NAV-02 · sin license:view no hay Diagnóstico, y el resto de Sistema sigue", () => {
    permisos = new Set(["organization:view", "dashboard:view"]);
    montar();
    expect(enlace("Diagnóstico")).toBeNull();
    expect(enlace("Auditoría")).not.toBeNull();
    expect(enlace("Empresas")).not.toBeNull();
  });

  it("NAV-03 · sin ningún permiso quedan solo las entradas sin permiso", () => {
    montar();
    expect(enlace("Diagnóstico")).toBeNull();
    expect(enlace("Configuración central")).toBeNull();
    expect(enlace("Empresas")).toBeNull();
    expect(enlace("Inicio")).not.toBeNull();
    expect(enlace("Mi licencia")).not.toBeNull();
    expect(enlace("Auditoría")).not.toBeNull();
  });

  it("NAV-04 · el permiso de Diagnóstico es el de la sección Licenciamiento", () => {
    permisos = new Set(["license:view"]);
    montar();
    expect(enlace("Diagnóstico")).not.toBeNull();
    expect(enlace("Configuración central")).not.toBeNull();
    expect(enlace("Empresas")).toBeNull();
  });
});
