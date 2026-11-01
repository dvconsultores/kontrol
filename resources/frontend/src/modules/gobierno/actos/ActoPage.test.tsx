import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import { Acto, ETIQUETA_FALTANTE_ACTO, FaltanteActo } from "@/modules/gobierno/api";

const apiFetchMock = vi.fn();

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

const notify = vi.fn();

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify }),
}));

vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({
    activeCompanyId: "c1",
    activeCompany: { id: "c1", legal_name: "Contenedor 1" },
  }),
}));

vi.mock("@/modules/documentos/AdjuntosPanel", () => ({
  AdjuntosPanel: (p: { resourceType: string; resourceId: string }) => (
    <div data-testid="adjuntos">{`${p.resourceType}:${p.resourceId}`}</div>
  ),
}));

vi.mock("@/lib/fecha-de-negocio", async (original) => ({
  ...(await original<typeof import("@/lib/fecha-de-negocio")>()),
  hoyDeNegocio: () => "2026-10-30",
}));

vi.mock("./ActoFormulario", () => ({
  ActoFormulario: (p: {
    onGuardar: (datos: Record<string, unknown>) => Promise<void>;
    erroresServidor: Record<string, string[]>;
  }) => (
    <>
      <button
        type="button"
        onClick={() =>
          void p.onGuardar({
            numero: "DA-011-2026",
            asunto: "Asunto editado",
          })
        }
      >
        Confirmar editar
      </button>
      <output data-testid="errores-editar">
        {JSON.stringify(p.erroresServidor)}
      </output>
    </>
  ),
}));

vi.mock("./EmitirActo", () => ({
  EmitirActo: (p: {
    onConfirmar: (datos: Record<string, unknown>) => Promise<void>;
    erroresServidor: Record<string, string[]>;
  }) => (
    <>
      <button
        type="button"
        onClick={() =>
          void p.onConfirmar({
            documento_acto_id: "doc-1",
            fecha_eficacia: null,
          })
        }
      >
        Confirmar emitir
      </button>
      <output data-testid="errores-emitir">
        {JSON.stringify(p.erroresServidor)}
      </output>
    </>
  ),
}));

vi.mock("./RegistrarEficacia", () => ({
  RegistrarEficacia: (p: {
    onConfirmar: (datos: Record<string, unknown>) => Promise<void>;
    erroresServidor: Record<string, string[]>;
  }) => (
    <>
      <button
        type="button"
        onClick={() =>
          void p.onConfirmar({
            medio: "GACETA",
            referencia: "Gaceta 100",
            fecha: "2026-10-15",
            documento_eficacia_id: "doc-2",
            fecha_eficacia: "2026-10-31",
          })
        }
      >
        Confirmar registrar eficacia
      </button>
      <output data-testid="errores-eficacia">
        {JSON.stringify(p.erroresServidor)}
      </output>
    </>
  ),
}));

vi.mock("./CorregirActo", () => ({
  CorregirActo: (p: {
    onConfirmar: (datos: Record<string, unknown>) => Promise<void>;
    erroresServidor: Record<string, string[]>;
  }) => (
    <>
      <button
        type="button"
        onClick={() =>
          void p.onConfirmar({
            campo: "asunto",
            texto: "Asunto corregido",
          })
        }
      >
        Confirmar corregir
      </button>
      <output data-testid="errores-corregir">
        {JSON.stringify(p.erroresServidor)}
      </output>
    </>
  ),
}));

vi.mock("./ReferenciarActo", () => ({
  ReferenciarActo: (p: {
    modo: "revocar" | "anular";
    onConfirmar: (datos: Record<string, unknown>) => Promise<void>;
    erroresServidor: Record<string, string[]>;
  }) => (
    <>
      <button
        type="button"
        onClick={() =>
          void p.onConfirmar({
            acto_id_referencia: "ref-1",
            motivo: "Motivo de referencia",
          })
        }
      >
        Confirmar {p.modo === "revocar" ? "revocar" : "anular"}
      </button>
      <output data-testid={`errores-${p.modo}`}>
        {JSON.stringify(p.erroresServidor)}
      </output>
    </>
  ),
}));

const { ActoPage } = await import("./ActoPage");

const ACTO_BASE: Acto = {
  id: "acto-1",
  tipo: "RESOLUCION",
  denominacion_tipo: null,
  numero: "DA-010-2026",
  fecha: "2026-09-15",
  lugar: "Sede central",
  cargo: {
    id: "cargo-1",
    codigo: "DIR-ADM",
    denominacion: "Dirección de Administración",
    unidad_codigo: "DA",
    unidad_denominacion: "Dirección de Administración",
  },
  competencia: {
    accion: "APROBAR",
    materia: "CONTRATACIONES",
  },
  fundamento_competencia: "Artículo 10",
  funcionario: "Fulano de Tal",
  titularidad: "TITULAR",
  delegacion_numero: null,
  delegacion_fecha: null,
  caracter: "PARTICULAR",
  simple_tramite: true,
  destinatario: "Destinatario SA",
  asunto: "Asunto del acto",
  hechos: "Unos hechos",
  fundamentos: "Unos fundamentos",
  decision: "Una decisión",
  estado: "BORRADOR",
  faltantes_para_emitir: [],
  documento_acto_id: null,
  medio: null,
  referencia_publicacion: null,
  fecha_publicacion_notificacion: null,
  documento_eficacia_id: null,
  fecha_eficacia: null,
  revocado_por: null,
  anulado_por: null,
  revoca_a: [],
  anula_a: [],
  version: 3,
  emitido_en: null,
  emitido_por: null,
  creado_en: "2026-09-01T10:00:00Z",
};

const VERSIONES = {
  items: [
    {
      version: 3,
      estado: "BORRADOR" as const,
      motivo: "Primera edición",
      actor: "fulano@mail.test",
      creado_en: "2026-10-20T10:00:00Z",
      instantanea: ACTO_BASE,
    },
    {
      version: 2,
      estado: "BORRADOR" as const,
      motivo: "Corrección de asunto",
      actor: "fulano@mail.test",
      creado_en: "2026-10-21T10:00:00Z",
      instantanea: ACTO_BASE,
    },
  ],
  total: 2,
};

function crearQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

function montar(acto: Acto, versiones = VERSIONES) {
  apiFetchMock.mockImplementation((url: string) => {
    if (url === "/gobierno/actos/acto-1") {
      return Promise.resolve(acto);
    }
    if (url === "/gobierno/actos/acto-1/versiones") {
      return Promise.resolve(versiones);
    }
    return Promise.reject(new Error(`URL no esperada: ${url}`));
  });

  const queryClient = crearQueryClient();

  const utils = render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/gobierno/actos/acto-1"]}>
        <Routes>
          <Route path="/gobierno/actos/:actoId" element={<ActoPage />} />
          <Route path="/gobierno/actos" element={<p>Lista de actos</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );

  return { utils, queryClient };
}

beforeEach(() => {
  apiFetchMock.mockReset();
  notify.mockReset();
  capacidades = new Set([
    "gobierno_actos:view",
    "gobierno_actos:edit",
    "gobierno_actos:issue",
    "gobierno_actos:annul",
  ]);
});

describe("ActoPage", () => {
  it("ACP-01 · BORRADOR con view+edit+issue y faltantes [\"HECHOS\",\"DOCUMENTO_ACTO\"] muestra encabezado, requisitos y «Emitir» deshabilitado", async () => {
    const acto: Acto = {
      ...ACTO_BASE,
      faltantes_para_emitir: ["HECHOS", "DOCUMENTO_ACTO"] as FaltanteActo[],
    };
    montar(acto);

    expect(
      await screen.findByRole("heading", { name: "Resolución Nº DA-010-2026" }),
    ).toBeTruthy();

    expect(screen.getByText("Para emitirlo falta:")).toBeTruthy();

    const seccion = screen.getByRole("region", { name: /Historial del acto/ });
    const requisitos = screen.getByText("Para emitirlo falta:").closest("section");
    expect(requisitos).toBeTruthy();
    if (requisitos) {
      expect(within(requisitos).getByText("Los hechos")).toBeTruthy();
      expect(within(requisitos).getByText("El PDF firmado del acto")).toBeTruthy();
    }

    expect(screen.getByRole("button", { name: "Editar" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Eliminar" })).toBeTruthy();

    const emitir = screen.getByRole("button", { name: "Emitir" });
    expect(emitir).toBeTruthy();
    expect((emitir as HTMLButtonElement).disabled).toBe(true);
    expect(seccion).toBeTruthy();
  });

  it("ACP-02 · BORRADOR con faltantes [\"DOCUMENTO_ACTO\"] permite emitir y llama a POST /emitir con If-Match 3", async () => {
    const acto: Acto = {
      ...ACTO_BASE,
      faltantes_para_emitir: ["DOCUMENTO_ACTO"] as FaltanteActo[],
    };
    montar(acto);

    const emitir = await screen.findByRole("button", { name: "Emitir" });
    expect((emitir as HTMLButtonElement).disabled).toBe(false);

    apiFetchMock.mockResolvedValueOnce({
      ...acto,
      estado: "EMITIDO",
      version: 4,
    });

    await userEvent.click(emitir);
    await userEvent.click(screen.getByRole("button", { name: "Confirmar emitir" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/actos/acto-1/emitir",
        expect.objectContaining({
          method: "POST",
          ifMatch: "3",
          body: {
            documento_acto_id: "doc-1",
            fecha_eficacia: null,
          },
        }),
      );
    });

    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith(
        expect.objectContaining({ type: "success", title: "Acto emitido" }),
      );
    });
  });

  it("ACP-03 · «Editar» → «Confirmar editar» → PATCH /gobierno/actos/acto-1 con If-Match 3", async () => {
    const acto: Acto = {
      ...ACTO_BASE,
      faltantes_para_emitir: ["DOCUMENTO_ACTO"] as FaltanteActo[],
    };
    montar(acto);

    apiFetchMock.mockResolvedValueOnce({ ...acto, version: 4 });

    await userEvent.click(await screen.findByRole("button", { name: "Editar" }));
    await userEvent.click(screen.getByRole("button", { name: "Confirmar editar" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/actos/acto-1",
        expect.objectContaining({
          method: "PATCH",
          ifMatch: "3",
          body: {
            numero: "DA-011-2026",
            asunto: "Asunto editado",
          },
        }),
      );
    });
  });

  it("ACP-04 · «Eliminar» → diálogo con texto real → confirmar → DELETE con If-Match 3 y navega a la lista", async () => {
    const acto: Acto = {
      ...ACTO_BASE,
      faltantes_para_emitir: ["DOCUMENTO_ACTO"] as FaltanteActo[],
    };
    montar(acto);

    apiFetchMock.mockResolvedValueOnce(undefined);

    await userEvent.click(await screen.findByRole("button", { name: "Eliminar" }));

    const dialogo = await screen.findByRole("dialog");
    expect(within(dialogo).getByText("¿Eliminar este borrador?")).toBeTruthy();

    await userEvent.click(within(dialogo).getByRole("button", { name: "Eliminar" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/actos/acto-1",
        expect.objectContaining({
          method: "DELETE",
          ifMatch: "3",
        }),
      );
    });

    expect(await screen.findByText("Lista de actos")).toBeTruthy();
  });

  it("ACP-05 · EMITIDO GENERAL muestra aviso real y botones de escritura, sin «Editar» ni «Eliminar»", async () => {
    const acto: Acto = {
      ...ACTO_BASE,
      estado: "EMITIDO",
      caracter: "GENERAL",
      faltantes_para_emitir: [],
    };
    montar(acto);

    expect(
      await screen.findByText(/Emitido, pendiente de publicación en Gaceta/),
    ).toBeTruthy();

    expect(screen.getByRole("button", { name: "Registrar la publicación" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Corregir error material" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Registrar revocación" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Registrar nulidad" })).toBeTruthy();

    expect(screen.queryByRole("button", { name: "Editar" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Eliminar" })).toBeNull();
  });

  it("ACP-06a · EFICAZ con fecha_eficacia 2026-03-12 muestra «Eficaz desde 12/03/2026»", async () => {
    const acto: Acto = {
      ...ACTO_BASE,
      estado: "EFICAZ",
      fecha_eficacia: "2026-03-12",
      faltantes_para_emitir: [],
    };
    montar(acto);

    expect(
      await screen.findByText(/Eficaz desde 12\/03\/2026/),
    ).toBeTruthy();
  });

  it("ACP-06b · EFICAZ con fecha_eficacia 2026-11-15 muestra «Eficaz a partir de 15/11/2026»", async () => {
    const acto: Acto = {
      ...ACTO_BASE,
      estado: "EFICAZ",
      fecha_eficacia: "2026-11-15",
      faltantes_para_emitir: [],
    };
    montar(acto);

    expect(
      await screen.findByText(/Eficaz a partir de 15\/11\/2026/),
    ).toBeTruthy();
  });

  it("ACP-07 · REVOCADO con revocado_por muestra «Revocado por …» con enlace y sin botones de escritura", async () => {
    const acto: Acto = {
      ...ACTO_BASE,
      estado: "REVOCADO",
      revocado_por: {
        id: "r1",
        tipo: "DECRETO",
        numero: "D-050-2026",
        fecha: "2026-10-01",
      },
      faltantes_para_emitir: [],
    };
    montar(acto);

    const aviso = await screen.findByText(/Revocado por/);
    expect(aviso.textContent).toContain("Revocado por");
    expect(aviso.textContent).toContain("Decreto Nº D-050-2026");
    expect(aviso.textContent).toContain("01/10/2026");

    const enlace = within(aviso).getByRole("link", { name: "Decreto Nº D-050-2026" });
    expect(enlace.getAttribute("href")).toBe("/gobierno/actos/r1");

    expect(screen.queryByRole("button", { name: "Editar" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Eliminar" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Emitir" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Registrar revocación" })).toBeNull();
  });

  it("ACP-08 · solo gobierno_actos:view en BORRADOR no muestra botones de escritura", async () => {
    capacidades = new Set(["gobierno_actos:view"]);

    const acto: Acto = {
      ...ACTO_BASE,
      faltantes_para_emitir: ["DOCUMENTO_ACTO"] as FaltanteActo[],
    };
    montar(acto);

    await screen.findByRole("heading", { name: "Resolución Nº DA-010-2026" });

    expect(screen.queryByRole("button", { name: "Editar" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Eliminar" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Emitir" })).toBeNull();
  });

  it("ACP-09 · 404 GOV_ACT_NOT_FOUND muestra «El acto no existe…» y enlace «Volver a Actos administrativos»", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/actos/acto-1/versiones") {
        return Promise.resolve(VERSIONES);
      }
      return Promise.reject(
        new ApiError(404, { code: "GOV_ACT_NOT_FOUND", message: "No encontrado" }),
      );
    });

    const queryClient = crearQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/gobierno/actos/acto-1"]}>
          <Routes>
            <Route path="/gobierno/actos/:actoId" element={<ActoPage />} />
            <Route path="/gobierno/actos" element={<p>Lista de actos</p>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(
      await screen.findByText("El acto no existe o no pertenece a este ente"),
    ).toBeTruthy();

    const enlace = screen.getByRole("link", { name: "Volver a Actos administrativos" });
    expect(enlace.getAttribute("href")).toBe("/gobierno/actos");
    expect(screen.getByRole("heading", { level: 1, name: "Acto administrativo" })).toBeInTheDocument();
  });

  it("ACP-10 · emitir responde 409 GOV_ACT_STALE → aparece ConflictState con botón «Recargar datos»", async () => {
    const acto: Acto = {
      ...ACTO_BASE,
      faltantes_para_emitir: ["DOCUMENTO_ACTO"] as FaltanteActo[],
    };
    montar(acto);

    const emitir = await screen.findByRole("button", { name: "Emitir" });
    await userEvent.click(emitir);

    apiFetchMock.mockRejectedValueOnce(
      new ApiError(409, { code: "GOV_ACT_STALE", message: "Versión desactualizada" }),
    );

    await userEvent.click(screen.getByRole("button", { name: "Confirmar emitir" }));

    expect(
      await screen.findByText(
        "Otra persona cambió el acto mientras trabajaba. Se cargó la versión vigente.",
      ),
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: "Recargar datos" })).toBeTruthy();
  });

  it("ACP-11 · emitir responde 422 con details { faltantes: [\"DECISION\"] } → aviso con «La decisión»", async () => {
    const acto: Acto = {
      ...ACTO_BASE,
      faltantes_para_emitir: ["DOCUMENTO_ACTO"] as FaltanteActo[],
    };
    montar(acto);

    const emitir = await screen.findByRole("button", { name: "Emitir" });
    await userEvent.click(emitir);

    apiFetchMock.mockRejectedValueOnce(
      new ApiError(422, {
        code: "GOV_ACT_INCOMPLETE",
        message: "Faltan datos",
        details: { faltantes: ["DECISION"] as FaltanteActo[] },
      }),
    );

    await userEvent.click(screen.getByRole("button", { name: "Confirmar emitir" }));

    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "error",
          title: "Falta información para esta acción",
          description: ETIQUETA_FALTANTE_ACTO.DECISION,
        }),
      );
    });
  });

  it("ACP-12 · titularidad DELEGACION con número y fecha muestra «Por delegación» con D-7 y 05/01/2026", async () => {
    const acto: Acto = {
      ...ACTO_BASE,
      titularidad: "DELEGACION",
      delegacion_numero: "D-7",
      delegacion_fecha: "2026-01-05",
      faltantes_para_emitir: [],
    };
    montar(acto);

    await screen.findByRole("heading", { name: "Resolución Nº DA-010-2026" });

    const termino = screen.getByText("Por delegación", { selector: "dt" });
    expect(termino).toBeTruthy();
    expect(termino.nextElementSibling?.textContent).toContain(
      "acto Nº D-7 del 05/01/2026",
    );
  });

  it("ACP-13 · el historial muestra las 2 versiones con versión y motivo", async () => {
    const acto: Acto = {
      ...ACTO_BASE,
      faltantes_para_emitir: ["DOCUMENTO_ACTO"] as FaltanteActo[],
    };
    montar(acto);

    await screen.findByRole("heading", { name: "Resolución Nº DA-010-2026" });

    const historial = screen.getByRole("region", { name: /Historial del acto/ });
    const filas = within(historial).getAllByRole("row");
    expect(filas).toHaveLength(3);

    const valores = within(historial).getAllByRole("cell");
    const versiones = valores.filter((c) => c.textContent === "3" || c.textContent === "2");
    expect(versiones).toHaveLength(2);

    expect(within(historial).getByText("Primera edición")).toBeTruthy();
    expect(within(historial).getByText("Corrección de asunto")).toBeTruthy();
  });

  it("ACP-14 · AdjuntosPanel recibe resourceType GovernmentAct y resourceId acto-1", async () => {
    const acto: Acto = {
      ...ACTO_BASE,
      faltantes_para_emitir: ["DOCUMENTO_ACTO"] as FaltanteActo[],
    };
    montar(acto);

    expect(await screen.findByTestId("adjuntos")).toBeTruthy();
    expect(screen.getByTestId("adjuntos").textContent).toBe("GovernmentAct:acto-1");
  });

  it("ACP-15 · EMITIDO PARTICULAR: «Registrar revocación» → «Confirmar revocar» → POST /revocar con If-Match", async () => {
    const acto: Acto = {
      ...ACTO_BASE,
      estado: "EMITIDO",
      caracter: "PARTICULAR",
      faltantes_para_emitir: [],
    };
    montar(acto);

    const revocar = await screen.findByRole("button", { name: "Registrar revocación" });
    await userEvent.click(revocar);

    apiFetchMock.mockResolvedValueOnce({ ...acto, estado: "REVOCADO", version: 4 });

    await userEvent.click(screen.getByRole("button", { name: "Confirmar revocar" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/actos/acto-1/revocar",
        expect.objectContaining({
          method: "POST",
          ifMatch: "3",
          body: {
            acto_id_referencia: "ref-1",
            motivo: "Motivo de referencia",
          },
        }),
      );
    });
  });
});
