/**
 * NAV · El menú no enseña Diagnóstico a quien no puede verlo (FR-001-233).
 * Ocultar una entrada es solo cosmética: la autorización real la impone el backend, que es
 * la autoridad. Aquí comprobamos únicamente que el menú respeta el permiso declarado, de modo
 * que nadie vea accesos para los que no está autorizado.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

describe("Sidebar · Gobierno · estructura (GOV-0-02)", () => {
  beforeEach(() => {
    permisos = new Set<string>();
    moduloGobierno = false;
  });

  it("GSB-04 · módulo habilitado y gobierno_estructura:view muestra el enlace", () => {
    moduloGobierno = true;
    permisos = new Set(["gobierno_estructura:view"]);
    montar();
    expect(enlace("Estructura organizativa")).not.toBeNull();
  });

  it("GSB-05 · capacidad sin módulo no muestra el enlace", () => {
    permisos = new Set(["gobierno_estructura:view"]);
    montar();
    expect(enlace("Estructura organizativa")).toBeNull();
  });
});

describe("Sidebar · Gobierno · cargos (GOV-0-03)", () => {
  beforeEach(() => {
    permisos = new Set<string>();
    moduloGobierno = false;
  });

  it("GSB-06 · módulo habilitado y gobierno_cargos:view muestra el enlace", () => {
    moduloGobierno = true;
    permisos = new Set(["gobierno_cargos:view"]);
    montar();
    const d = enlace("Cargos y competencias");
    expect(d).not.toBeNull();
    expect(d?.getAttribute("href")).toBe("/gobierno/cargos");
  });

  it("GSB-07 · capacidad sin módulo no muestra el enlace", () => {
    permisos = new Set(["gobierno_cargos:view"]);
    montar();
    expect(enlace("Cargos y competencias")).toBeNull();
  });
});

describe("Sidebar · Gobierno › Actos administrativos", () => {
  beforeEach(() => {
    permisos = new Set<string>();
    moduloGobierno = false;
  });

  it("GSB-08 · módulo habilitado y gobierno_actos:view muestra el enlace", () => {
    moduloGobierno = true;
    permisos = new Set(["gobierno_actos:view"]);
    montar();
    const d = enlace("Actos administrativos");
    expect(d).not.toBeNull();
    expect(d?.getAttribute("href")).toBe("/gobierno/actos");
  });

  it("GSB-09 · capacidad sin módulo no muestra el enlace", () => {
    permisos = new Set(["gobierno_actos:view"]);
    montar();
    expect(enlace("Actos administrativos")).toBeNull();
  });

  it("GSB-10 · módulo habilitado y gobierno_notificaciones:view muestra «Notificaciones administrativas»", () => {
    moduloGobierno = true;
    permisos = new Set(["gobierno_notificaciones:view"]);
    montar();
    expect(enlace("Notificaciones administrativas")).toBeTruthy();
    expect(enlace("Notificaciones administrativas")).toHaveAttribute("href", "/gobierno/notificaciones");
  });

  it("GSB-11 · capacidad sin módulo no muestra el enlace de notificaciones", () => {
    permisos = new Set(["gobierno_notificaciones:view"]);
    montar();
    expect(enlace("Notificaciones administrativas")).toBeNull();
  });

  it("GSB-12 · módulo habilitado y gobierno_autoridad:view muestra «Matriz de autoridad»", () => {
    moduloGobierno = true;
    permisos = new Set(["gobierno_autoridad:view"]);
    montar();
    const item = enlace("Matriz de autoridad");
    expect(item).not.toBeNull();
    expect(item?.getAttribute("href")).toBe("/gobierno/autoridad");
  });

  it("GSB-13 · gobierno_cargos:view sin gobierno_autoridad:view no muestra la matriz", () => {
    moduloGobierno = true;
    permisos = new Set(["gobierno_cargos:view"]);
    montar();
    expect(enlace("Matriz de autoridad")).toBeNull();
    expect(enlace("Cargos y competencias")).not.toBeNull();
  });

  it("GSB-14 · módulo habilitado y gobierno_auditoria:view muestra «Auditoría institucional»", () => {
    moduloGobierno = true;
    permisos = new Set(["gobierno_auditoria:view"]);
    montar();
    const item = enlace("Auditoría institucional");
    expect(item).not.toBeNull();
    expect(item?.getAttribute("href")).toBe("/gobierno/auditoria");
  });

  it("GSB-15 · audit:view sin gobierno_auditoria:view no muestra «Auditoría institucional»", () => {
    moduloGobierno = true;
    permisos = new Set(["audit:view"]);
    montar();
    expect(enlace("Auditoría institucional")).toBeNull();
  });
});

// Las pruebas existentes renderizan <Sidebar /> sin props: se añade cobertura
// de las nuevas props sin tocar las existentes.
it("sin props, el nav principal sigue presente", () => {
  render(<MemoryRouter><Sidebar /></MemoryRouter>);
  expect(screen.getByRole("navigation", { name: "Menú principal" })).toBeInTheDocument();
});

it("con onClose, muestra el control «Cerrar menú» y dispara el callback", async () => {
  const onClose = vi.fn();
  render(<MemoryRouter><Sidebar onClose={onClose} /></MemoryRouter>);
  const cerrar = screen.getByRole("button", { name: "Cerrar menú" });
  await userEvent.click(cerrar);
  expect(onClose).toHaveBeenCalledTimes(1);
});

it("sin autoFocus no añade tabIndex al aside", () => {
  const { container } = render(<MemoryRouter><Sidebar /></MemoryRouter>);
  expect(container.querySelector("aside")?.hasAttribute("tabindex")).toBe(false);
});
