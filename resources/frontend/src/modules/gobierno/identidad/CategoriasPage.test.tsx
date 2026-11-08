import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import type {
  CategoriasListado,
  ConflictosIdentidad,
  PoliticaIdentidad,
} from "@/modules/gobierno/api";

const apiFetchMock = vi.fn();
const notifyMock = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

let capacidades = new Set<string>();

vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({
    estado: "LISTA",
    tiene: (c: string) => capacidades.has(c),
    puede: () => true,
    motivo: () => null,
    motivoDeCapacidad: () => null,
  }),
}));

vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({
    activeCompanyId: "c1",
    activeCompany: { id: "c1", legal_name: "Contenedor 1" },
  }),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: notifyMock }),
}));

const { CategoriasPage } = await import("./CategoriasPage");

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/gobierno/identidad/categorias"]}>
        <Routes>
          <Route
            path="/gobierno/identidad/categorias"
            element={<CategoriasPage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const categoriasListado: CategoriasListado = {
  items: [
    {
      id: "cat-1",
      role_id: "rol-1",
      rol_nombre: "Analista de Prueba",
      rol_codigo: "ANALISTA",
      categoria: "OPERATIVO",
      categoria_etiqueta: "Operativo",
      desde: "2024-01-01",
      hasta: null,
      status: "ACTIVA",
      version: 1,
      motivo: "Clasificación del rol de prueba.",
    },
  ],
  roles: [
    {
      id: "rol-1",
      nombre: "Analista de Prueba",
      codigo: "ANALISTA",
    },
  ],
};

const conflictosConItems: ConflictosIdentidad = {
  items: [
    {
      vinculo_id: "v1",
      codigo: "VIN-001",
      cuenta: {
        id: "cuenta-1",
        usuario: "analista.prueba",
        estado: "ACTIVA",
      },
      funcionario: {
        id: "func-1",
        codigo: "FUNC-001",
        nombre: "Funcionario de Prueba",
        documento: "12345678",
      },
      conflictos: [
        {
          regla_codigo: "REG-001",
          regla_nombre: "Regla de Prueba",
          categoria_a: "OPERATIVO",
          categoria_b: "APROBADOR",
        },
      ],
    },
  ],
};

const politicaActiva: PoliticaIdentidad = {
  exige_identidad: true,
  version: 1,
  motivo: null,
  historia: [
    {
      id: "h1",
      creado_en: "2024-01-01T10:00:00Z",
      actor: "analista.prueba",
      tipo: "CAMBIADA",
      detalle: {
        despues: { exige_identidad: true },
      },
    },
  ],
};

const politicaInactiva: PoliticaIdentidad = {
  exige_identidad: false,
  motivo: null,
  version: 2,
  historia: [
    {
      id: "h1",
      creado_en: "2024-01-01T10:00:00Z",
      actor: "analista.prueba",
      tipo: "CAMBIADA",
      detalle: {
        despues: { exige_identidad: false },
      },
    },
  ],
};

function seccionClasificacion() {
  return screen
    .getByRole("heading", { name: "Clasificación de roles" })
    .closest("section") as HTMLElement;
}


function seccionPolitica() {
  return screen
    .getByRole("heading", { name: "Exigencia de identidad del ente" })
    .closest("section") as HTMLElement;
}

describe("CategoriasPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    notifyMock.mockReset();
    capacidades = new Set([
      "gobierno_identidad:view",
      "gobierno_identidad:manage",
      "gobierno_identidad:activate",
    ]);
  });

  it("sin view muestra 'Sin acceso'", async () => {
    capacidades = new Set();

    apiFetchMock.mockImplementation((ruta: string) => {
      if (ruta === "/gobierno/identidad/categorias") {
        return Promise.resolve(categoriasListado);
      }
      return Promise.reject(new Error("Unexpected"));
    });

    renderPage();

    expect(
      await screen.findByRole("heading", { name: "Sin acceso" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "No tiene permiso para ver las categorías y separación.",
      ),
    ).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("lista de categorías con rol, categoría y estado; sin manage no hay formulario de clasificación ni botón 'Retirar'", async () => {
    capacidades = new Set(["gobierno_identidad:view"]);

    apiFetchMock.mockImplementation(
      (ruta: string, options?: { method?: string }) => {
        if (ruta === "/gobierno/identidad/categorias" && !options?.method) {
          return Promise.resolve(categoriasListado);
        }
        if (ruta === "/gobierno/identidad/conflictos" && !options?.method) {
          return Promise.resolve({ items: [] });
        }
        if (ruta === "/gobierno/identidad/politica" && !options?.method) {
          return Promise.resolve(politicaActiva);
        }
        return Promise.reject(new Error("Unexpected"));
      },
    );

    renderPage();

    const tabla = await screen.findByRole("region", {
      name: "Tabla de categorías de rol",
    });
    const fila = within(tabla).getByRole("row", {
      name: /Analista de Prueba \(ANALISTA\)/,
    });
    expect(within(fila).getByText("Operativo")).toBeInTheDocument();
    expect(within(fila).getByText("Activa")).toBeInTheDocument();

    expect(
      screen.getByRole("heading", { name: "Clasificación de roles" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Registrar categoría" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Retirar" }),
    ).not.toBeInTheDocument();
  });

  it("clasificar hace POST /gobierno/identidad/categorias con body {role_id, categoria, desde, motivo}", async () => {
    apiFetchMock.mockImplementation(
      (ruta: string, options?: { method?: string }) => {
        if (
          ruta === "/gobierno/identidad/categorias" &&
          options?.method === "POST"
        ) {
          return Promise.resolve({});
        }
        if (ruta === "/gobierno/identidad/categorias" && !options?.method) {
          return Promise.resolve(categoriasListado);
        }
        if (ruta === "/gobierno/identidad/conflictos" && !options?.method) {
          return Promise.resolve({ items: [] });
        }
        if (ruta === "/gobierno/identidad/politica" && !options?.method) {
          return Promise.resolve(politicaActiva);
        }
        return Promise.reject(new Error("Unexpected"));
      },
    );

    renderPage();

    await screen.findByRole("region", { name: "Tabla de categorías de rol" });

    const form = seccionClasificacion();
    await userEvent.selectOptions(
      within(form).getByLabelText("Rol"),
      "rol-1",
    );
    await userEvent.selectOptions(
      within(form).getByLabelText("Categoría"),
      "OPERATIVO",
    );
    await userEvent.type(within(form).getByLabelText("Desde"), "2024-02-01");
    await userEvent.type(
      within(form).getByLabelText("Motivo"),
      "Motivo de clasificación",
    );
    await userEvent.click(
      within(form).getByRole("button", { name: "Registrar categoría" }),
    );

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/identidad/categorias",
        {
          method: "POST",
          body: {
            role_id: "rol-1",
            categoria: "OPERATIVO",
            desde: "2024-02-01",
            motivo: "Motivo de clasificación",
          },
        },
      );
    });
  });

  it("si clasificar responde ApiError 409 GOV_SOD_CONFLICT con message, el message aparece en role='alert'", async () => {
    apiFetchMock.mockImplementation(
      async (ruta: string, options?: { method?: string }) => {
        if (
          ruta === "/gobierno/identidad/categorias" &&
          options?.method === "POST"
        ) {
          throw new ApiError(409, {
            code: "GOV_SOD_CONFLICT",
            message: "Conflicto de separación detectado",
          });
        }
        if (ruta === "/gobierno/identidad/categorias" && !options?.method) {
          return categoriasListado;
        }
        if (ruta === "/gobierno/identidad/conflictos" && !options?.method) {
          return { items: [] };
        }
        if (ruta === "/gobierno/identidad/politica" && !options?.method) {
          return politicaActiva;
        }
        return Promise.reject(new Error("Unexpected"));
      },
    );

    renderPage();

    await screen.findByRole("region", { name: "Tabla de categorías de rol" });

    const form = seccionClasificacion();
    await userEvent.selectOptions(
      within(form).getByLabelText("Rol"),
      "rol-1",
    );
    await userEvent.selectOptions(
      within(form).getByLabelText("Categoría"),
      "OPERATIVO",
    );
    await userEvent.type(within(form).getByLabelText("Desde"), "2024-02-01");
    await userEvent.type(
      within(form).getByLabelText("Motivo"),
      "Motivo de clasificación",
    );
    await userEvent.click(
      within(form).getByRole("button", { name: "Registrar categoría" }),
    );

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent("Conflicto de separación detectado");
  });

  it("'Retirar' abre panel en línea; enviar hace POST /gobierno/identidad/categorias/{id}/retirar con ifMatch String(version) y body {fecha, motivo}", async () => {
    apiFetchMock.mockImplementation(
      (ruta: string, options?: { method?: string }) => {
        if (
          ruta === "/gobierno/identidad/categorias/cat-1/retirar" &&
          options?.method === "POST"
        ) {
          return Promise.resolve({});
        }
        if (ruta === "/gobierno/identidad/categorias" && !options?.method) {
          return Promise.resolve(categoriasListado);
        }
        if (ruta === "/gobierno/identidad/conflictos" && !options?.method) {
          return Promise.resolve({ items: [] });
        }
        if (ruta === "/gobierno/identidad/politica" && !options?.method) {
          return Promise.resolve(politicaActiva);
        }
        return Promise.reject(new Error("Unexpected"));
      },
    );

    renderPage();

    await screen.findByRole("region", { name: "Tabla de categorías de rol" });
    await userEvent.click(screen.getByRole("button", { name: "Retirar" }));

    const panel = screen
      .getByRole("heading", { name: /Retirar categoría de/ })
      .closest("form") as HTMLElement;
    await userEvent.type(within(panel).getByLabelText("Fecha"), "2024-02-02");
    await userEvent.type(
      within(panel).getByLabelText("Motivo"),
      "Motivo de retiro",
    );
    await userEvent.click(
      within(panel).getByRole("button", { name: "Retirar" }),
    );

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/identidad/categorias/cat-1/retirar",
        {
          method: "POST",
          ifMatch: "1",
          body: {
            fecha: "2024-02-02",
            motivo: "Motivo de retiro",
          },
        },
      );
    });
  });

  it("conflictos con items muestra la tabla con enlace al vínculo", async () => {
    apiFetchMock.mockImplementation(
      (ruta: string, options?: { method?: string }) => {
        if (ruta === "/gobierno/identidad/categorias" && !options?.method) {
          return Promise.resolve(categoriasListado);
        }
        if (ruta === "/gobierno/identidad/conflictos" && !options?.method) {
          return Promise.resolve(conflictosConItems);
        }
        if (ruta === "/gobierno/identidad/politica" && !options?.method) {
          return Promise.resolve(politicaActiva);
        }
        return Promise.reject(new Error("Unexpected"));
      },
    );

    renderPage();

    const tabla = await screen.findByRole("region", {
      name: "Tabla de conflictos de separación",
    });
    const enlace = within(tabla).getByRole("link", { name: "VIN-001" });
    expect(enlace).toHaveAttribute(
      "href",
      "/gobierno/identidad/vinculos/v1",
    );
    expect(within(tabla).getByText("analista.prueba")).toBeInTheDocument();
    expect(
      within(tabla).getByText("Funcionario de Prueba"),
    ).toBeInTheDocument();
  });

  it("conflictos sin items muestra 'Sin conflictos de separación entre los vínculos vigentes.'", async () => {
    apiFetchMock.mockImplementation(
      (ruta: string, options?: { method?: string }) => {
        if (ruta === "/gobierno/identidad/categorias" && !options?.method) {
          return Promise.resolve(categoriasListado);
        }
        if (ruta === "/gobierno/identidad/conflictos" && !options?.method) {
          return Promise.resolve({ items: [] });
        }
        if (ruta === "/gobierno/identidad/politica" && !options?.method) {
          return Promise.resolve(politicaActiva);
        }
        return Promise.reject(new Error("Unexpected"));
      },
    );

    renderPage();

    expect(
      await screen.findByText(
        "Sin conflictos de separación entre los vínculos vigentes.",
      ),
    ).toBeInTheDocument();
  });

  it("política inactiva con activate: botón 'Activar la exigencia'; enviar hace POST /gobierno/identidad/politica con ifMatch String(version) y body {exige_identidad: true, motivo}", async () => {
    apiFetchMock.mockImplementation(
      (ruta: string, options?: { method?: string }) => {
        if (
          ruta === "/gobierno/identidad/politica" &&
          options?.method === "POST"
        ) {
          return Promise.resolve({});
        }
        if (ruta === "/gobierno/identidad/categorias" && !options?.method) {
          return Promise.resolve(categoriasListado);
        }
        if (ruta === "/gobierno/identidad/conflictos" && !options?.method) {
          return Promise.resolve({ items: [] });
        }
        if (ruta === "/gobierno/identidad/politica" && !options?.method) {
          return Promise.resolve(politicaInactiva);
        }
        return Promise.reject(new Error("Unexpected"));
      },
    );

    renderPage();

    await screen.findByRole("heading", {
      level: 1,
      name: "Categorías y separación",
    });

    const boton = await screen.findByRole("button", {
      name: "Activar la exigencia",
    });
    expect(boton).toBeInTheDocument();

    const form = seccionPolitica();
    await userEvent.type(
      within(form).getByLabelText("Motivo"),
      "Motivo de activación",
    );
    await userEvent.click(boton);

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/identidad/politica",
        {
          method: "POST",
          ifMatch: "2",
          body: {
            exige_identidad: true,
            motivo: "Motivo de activación",
          },
        },
      );
    });
  });

  it("sin activate no hay botón 'Activar la exigencia'", async () => {
    capacidades = new Set(["gobierno_identidad:view"]);

    apiFetchMock.mockImplementation(
      (ruta: string, options?: { method?: string }) => {
        if (ruta === "/gobierno/identidad/categorias" && !options?.method) {
          return Promise.resolve(categoriasListado);
        }
        if (ruta === "/gobierno/identidad/conflictos" && !options?.method) {
          return Promise.resolve({ items: [] });
        }
        if (ruta === "/gobierno/identidad/politica" && !options?.method) {
          return Promise.resolve(politicaInactiva);
        }
        return Promise.reject(new Error("Unexpected"));
      },
    );

    renderPage();

    await screen.findByText(
      "Inactiva: el ente aún no exige vínculo institucional para operar.",
    );
    expect(
      screen.queryByRole("button", { name: "Activar la exigencia" }),
    ).not.toBeInTheDocument();
  });

  it("el enlace a Segregación de funciones apunta a /gobierno/sod", async () => {
    apiFetchMock.mockImplementation(
      (ruta: string, options?: { method?: string }) => {
        if (ruta === "/gobierno/identidad/categorias" && !options?.method) {
          return Promise.resolve(categoriasListado);
        }
        if (ruta === "/gobierno/identidad/conflictos" && !options?.method) {
          return Promise.resolve({ items: [] });
        }
        if (ruta === "/gobierno/identidad/politica" && !options?.method) {
          return Promise.resolve(politicaActiva);
        }
        return Promise.reject(new Error("Unexpected"));
      },
    );

    renderPage();

    await screen.findByRole("region", { name: "Tabla de categorías de rol" });
    const enlace = screen.getByRole("link", {
      name: "Segregación de funciones",
    });
    expect(enlace).toHaveAttribute("href", "/gobierno/sod");
  });
});
