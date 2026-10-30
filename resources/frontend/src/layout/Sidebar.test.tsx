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

vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({
    estado: "LISTA",
    tiene: (capacidad: string) => permisos.has(capacidad),
    puede: () => true,
    motivo: () => null,
    motivoDeCapacidad: () => "PERMISSION_DENIED",
  }),
}));

let moduloGobierno = false;

vi.mock("@/modules/gobierno/api", () => ({ useModuloGobierno: () => moduloGobierno }));

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
    moduloGobierno = false;
  });

  it("NAV-01 · con license:view la entrada Diagnóstico está, y apunta a su ruta", () => {
    permisos = new Set(["license:view"]);
    montar();
    const d = enlace("Diagnóstico");
    expect(d).not.toBeNull();
    expect(d?.getAttribute("href")).toBe("/diagnostico");
    expect(enlace("Auditoría")).toBeNull(); // la pantalla exige audit:view
  });

  it("NAV-02 · sin license:view no hay Diagnóstico, y el resto de Sistema sigue", () => {
    permisos = new Set(["organization:view", "dashboard:view"]);
    montar();
    expect(enlace("Diagnóstico")).toBeNull();
    expect(enlace("Auditoría")).toBeNull(); // la pantalla exige audit:view
    expect(enlace("Empresas")).not.toBeNull();
  });

  it("NAV-03 · sin ningún permiso quedan solo las entradas sin permiso", () => {
    montar();
    expect(enlace("Diagnóstico")).toBeNull();
    expect(enlace("Configuración central")).toBeNull();
    expect(enlace("Empresas")).toBeNull();
    expect(enlace("Inicio")).not.toBeNull();
    expect(enlace("Mi licencia")).toBeNull(); // el detalle de la licencia exige license:view (FR-010-114)
    expect(enlace("Auditoría")).toBeNull(); // la pantalla exige audit:view
  });

  it("NAV-04 · el permiso de Diagnóstico es el de la sección Licenciamiento", () => {
    permisos = new Set(["license:view"]);
    montar();
    expect(enlace("Diagnóstico")).not.toBeNull();
    expect(enlace("Configuración central")).not.toBeNull();
    expect(enlace("Empresas")).toBeNull();
  });

  it("NAV-05 · «Mi licencia» solo con license:view, y apunta a su ruta", () => {
    permisos = new Set(["license:view"]);
    montar();
    expect(enlace("Mi licencia")?.getAttribute("href")).toBe("/mi-licencia");
  });

  it("NAV-06 · con otros permisos pero sin license:view no hay «Mi licencia»", () => {
    permisos = new Set(["organization:view", "dashboard:view", "audit:view"]);
    montar();
    expect(enlace("Mi licencia")).toBeNull();
    expect(enlace("Inicio")).not.toBeNull();
  });

  it("NAV-07 · con audit:view están las dos entradas Auditoría (Sistema y Reportes), cada una con su ruta", () => {
    permisos = new Set(["audit:view"]);
    montar();
    const hrefs = screen
      .getAllByRole("link", { name: "Auditoría" })
      .map((a) => a.getAttribute("href"))
      .sort();
    expect(hrefs).toEqual(["/auditoria", "/reportes/auditoria"]);
  });
});

describe("Sidebar · Gobierno (GOV-0-01)", () => {
  beforeEach(() => {
    permisos = new Set<string>();
    moduloGobierno = false;
  });

  it("GSB-01 · módulo habilitado y gobierno_ente:view muestra el enlace y el grupo", () => {
    moduloGobierno = true;
    permisos = new Set(["gobierno_ente:view"]);
    montar();
    expect(enlace("Configuración del ente")).not.toBeNull();
    expect(screen.getByText("Gobierno")).toBeInTheDocument();
  });

  it("GSB-02 · capacidad sin módulo no muestra el enlace", () => {
    permisos = new Set(["gobierno_ente:view"]);
    montar();
    expect(enlace("Configuración del ente")).toBeNull();
  });

  it("GSB-03 · módulo sin capacidad no muestra el enlace", () => {
    moduloGobierno = true;
    montar();
    expect(enlace("Configuración del ente")).toBeNull();
  });
});
