import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/api/client";
import { PoliticaOrdenPagoPage } from "./PoliticaOrdenPagoPage";
import type { PoliticaOrdenPago } from "./api";

const apiFetchMock = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  ApiError: (await original<typeof import("@/api/client")>()).ApiError,
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
  useCompany: () => ({ activeCompanyId: "c1", activeCompany: { id: "c1", legal_name: "Ente 1" } }),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: vi.fn() }),
}));

interface TipoDocumento {
  id: string;
  nombre: string;
  codigo?: string | null;
}

const TIPOS_DOCUMENTO: TipoDocumento[] = [
  { id: "td-1", nombre: "Factura" },
  { id: "td-2", nombre: "Certificado" },
];


function crearPolitica(partial: Partial<PoliticaOrdenPago> = {}): PoliticaOrdenPago {
  return {
    id: "b47d44d0-9453-46d1-8c4f-240d88cf6bd1",
    codigo: "OPB0C26DCB4EF7",
    nombre: "Política de orden de pago de prueba",
    descripcion: null,
    tipo_gasto: null,
    requiere_expediente_completo: false,
    competencia_accion: "ORDENAR_PAGO",
    competencia_materia: "TESORERIA",
    vigente_desde: "2026-11-17",
    vigente_hasta: null,
    fundamento: "Fundamento suficiente para activar la política de orden de pago.",
    act_id: null,
    acto: null,
    tipo_regla: "INSTITUTIONAL_POLICY",
    estado: "VIGENTE",
    version: 2,
    activada_en: "2026-11-17T18:45:36.632890+00:00",
    cerrada_en: null,
    motivo_cierre: null,
    documentos: [],
    historia: [
      {
        evento: "CREADA",
        version: 1,
        fecha: "2026-11-17T18:45:36.527753+00:00",
        actor: "ord_t03",
      },
      {
        evento: "ACTIVADA",
        version: 2,
        fecha: "2026-11-17T18:45:36.623580+00:00",
        actor: "ord_t03",
      },
    ],
    ...partial,
  };
}

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

function renderizar(ruta: string) {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[ruta]}>
        <Routes>
          <Route path="/gobierno/tesoreria/politicas-orden-pago/nueva" element={<PoliticaOrdenPagoPage />} />
          <Route path="/gobierno/tesoreria/politicas-orden-pago/:politicaId" element={<PoliticaOrdenPagoPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("PoliticaOrdenPagoPage", () => {
  let politicaActual: PoliticaOrdenPago | null;

  beforeEach(() => {
    queryClient.clear();
    capacidades = new Set(["gobierno_ordenes_pago:view", "gobierno_ordenes_pago:policy"]);
    politicaActual = null;
    apiFetchMock.mockReset();
    apiFetchMock.mockImplementation((ruta: string, opciones?: { method?: string; body?: unknown; ifMatch?: string }) => {
      if (ruta === "/documentos/tipos" && !opciones) {
        return Promise.resolve(TIPOS_DOCUMENTO);
      }

      const matchBase = ruta.match(/^\/gobierno\/tesoreria\/politicas-orden-pago\/([^/]+)$/);
      if (matchBase) {
        const id = matchBase[1];
        const method = opciones?.method ?? "GET";
        if (method === "GET") {
          if (politicaActual && politicaActual.id === id) {
            return Promise.resolve({ ...politicaActual });
          }
          return Promise.reject(new ApiError(404, { code: "NOT_FOUND", message: "No encontrada", field_errors: {}, request_id: "r1" }));
        }
        if (method === "PUT") {
          if (politicaActual && politicaActual.id === id) {
            politicaActual = {
              ...politicaActual,
              ...(opciones?.body as Partial<PoliticaOrdenPago>),
              version: politicaActual.version + 1,
              estado: politicaActual.estado,
            };
            return Promise.resolve({ ...politicaActual });
          }
          return Promise.reject(new ApiError(404, { code: "NOT_FOUND", message: "No encontrada", field_errors: {}, request_id: "r1" }));
        }
      }

      const matchAccion = ruta.match(/^\/gobierno\/tesoreria\/politicas-orden-pago\/([^/]+)\/(activar|cerrar)$/);
      if (matchAccion) {
        const id = matchAccion[1];
        const accion = matchAccion[2];
        if (politicaActual && politicaActual.id === id && opciones?.method === "POST") {
          if (accion === "activar") {
            politicaActual = {
              ...politicaActual,
              estado: "VIGENTE",
              version: politicaActual.version + 1,
              fundamento: (opciones.body as { fundamento: string }).fundamento,
              activada_en: "2026-11-17T18:45:36.632890+00:00",
              historia: [
                { evento: "ACTIVADA", version: politicaActual.version + 1, fecha: "2026-11-17T18:45:36.623580+00:00", actor: "ord_t03" },
                ...politicaActual.historia,
              ],
            };
            return Promise.resolve({ ...politicaActual });
          }
          politicaActual = {
            ...politicaActual,
            estado: "CERRADA",
            version: politicaActual.version + 1,
            motivo_cierre: (opciones.body as { motivo: string }).motivo,
            cerrada_en: "2026-11-17T18:45:36.632890+00:00",
            historia: [
              { evento: "CERRADA", version: politicaActual.version + 1, fecha: "2026-11-17T18:45:36.623580+00:00", actor: "ord_t03" },
              ...politicaActual.historia,
            ],
          };
          return Promise.resolve({ ...politicaActual });
        }
        return Promise.reject(new ApiError(404, { code: "NOT_FOUND", message: "No encontrada", field_errors: {}, request_id: "r1" }));
      }

      if (ruta === "/gobierno/tesoreria/politicas-orden-pago" && opciones?.method === "POST") {
        const body = opciones.body as Record<string, unknown>;
        politicaActual = crearPolitica({
          id: "nueva-id",
          codigo: body.codigo as string,
          nombre: body.nombre as string,
          descripcion: (body.descripcion as string | null) ?? null,
          tipo_gasto: (body.tipo_gasto as string | null) ?? null,
          requiere_expediente_completo: body.requiere_expediente_completo as boolean,
          vigente_desde: body.vigente_desde as string,
          vigente_hasta: (body.vigente_hasta as string | null) ?? null,
          fundamento: (body.fundamento as string | null) ?? null,
          tipo_regla: body.tipo_regla as string,
          estado: "BORRADOR",
          version: 1,
          activada_en: null,
          cerrada_en: null,
          motivo_cierre: null,
          documentos: (body.documentos as unknown[]) ?? [],
          historia: [
            { evento: "CREADA", version: 1, fecha: "2026-11-17T18:45:36.527753+00:00", actor: "ord_t03" },
          ],
        });
        return Promise.resolve({ ...politicaActual });
      }

      return Promise.reject(new Error("Ruta no esperada: " + (opciones?.method ?? "GET") + " " + ruta));
    });
  });

  it("alta: registra una nueva política y navega a la ficha", async () => {
    const usuario = userEvent.setup();
    renderizar("/gobierno/tesoreria/politicas-orden-pago/nueva");

    expect(await screen.findByRole("heading", { level: 1, name: "Nueva política de orden de pago" })).toBeInTheDocument();

    await usuario.type(screen.getByLabelText(/^Código/), "POL-OP-01");
    await usuario.type(screen.getByLabelText(/^Nombre/), "Política de compra");
    const vigenteDesde = screen.getByLabelText(/^Vigente desde/);
    await usuario.clear(vigenteDesde);
    await usuario.type(vigenteDesde, "2026-01-01");
    await usuario.selectOptions(screen.getByLabelText(/^Tipo de regla/), "INSTITUTIONAL_POLICY");

    expect(screen.getByDisplayValue("ORDENAR_PAGO · TESORERIA")).toBeDisabled();

    await usuario.type(screen.getByLabelText("Fundamento"), "Fundamento de la política");

    await usuario.click(screen.getByRole("button", { name: "Añadir documento" }));
    await usuario.selectOptions(screen.getByLabelText(/^Documento 1$/), "td-1");
    await usuario.click(screen.getByRole("checkbox", { name: "Obligatorio" }));

    await usuario.click(screen.getByRole("button", { name: "Guardar" }));

    await screen.findByRole("heading", { level: 1, name: "Política de compra" });
    expect(await screen.findByRole("button", { name: "Activar" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Guardar" })).not.toBeInTheDocument();

    expect(apiFetchMock).toHaveBeenCalledWith(
      "/gobierno/tesoreria/politicas-orden-pago",
      expect.objectContaining({
        method: "POST",
        body: expect.objectContaining({
          codigo: "POL-OP-01",
          nombre: "Política de compra",
          vigente_desde: "2026-01-01",
          tipo_regla: "INSTITUTIONAL_POLICY",
          competencia_accion: "ORDENAR_PAGO",
          competencia_materia: "TESORERIA",
          documentos: [{ document_type_id: "td-1", obligatorio: true, etapa: "EMISION", condicion: null }],
        }),
      }),
    );
  });

  it("competencia fija: aparece como texto, no como campo editable", async () => {
    renderizar("/gobierno/tesoreria/politicas-orden-pago/nueva");
    expect(await screen.findByDisplayValue("ORDENAR_PAGO · TESORERIA")).toBeDisabled();
  });

  it("validación 422 en alta: muestra el mensaje del campo", async () => {
    apiFetchMock.mockImplementation(async (ruta: string, opciones?: { method?: string; body?: unknown }) => {
      if (ruta === "/documentos/tipos" && !opciones) {
        return TIPOS_DOCUMENTO;
      }
      if (ruta === "/gobierno/tesoreria/politicas-orden-pago" && opciones?.method === "POST") {
        throw new ApiError(422, {
          code: "GOV_PAYMENT_ORDER_POLICY_INVALID",
          message: "Datos inválidos",
          field_errors: { codigo: ["Código ya usado"] },
          request_id: "r1",
        });
      }
      return Promise.reject(new Error("Ruta no esperada: " + (opciones?.method ?? "GET") + " " + ruta));
    });

    const usuario = userEvent.setup();
    renderizar("/gobierno/tesoreria/politicas-orden-pago/nueva");
    await screen.findByRole("heading", { level: 1, name: "Nueva política de orden de pago" });

    await usuario.type(screen.getByLabelText(/^Código/), "POL-OP-01");
    await usuario.type(screen.getByLabelText(/^Nombre/), "Política de compra");
    const vigenteDesde = screen.getByLabelText(/^Vigente desde/);
    await usuario.clear(vigenteDesde);
    await usuario.type(vigenteDesde, "2026-01-01");

    await usuario.click(screen.getByRole("button", { name: "Guardar" }));

    expect(await screen.findByText("Código ya usado")).toBeInTheDocument();
  });

  it("edición de BORRADOR: cambia el nombre y guarda con ifMatch", async () => {
    politicaActual = crearPolitica({ estado: "BORRADOR", version: 1, codigo: "POL-BOR", nombre: "Borrador inicial", vigente_desde: "2026-02-01", documentos: [], historia: [{ evento: "CREADA", version: 1, fecha: "2026-02-01T10:00:00+00:00", actor: "ord_t03" }] });

    const usuario = userEvent.setup();
    renderizar(`/gobierno/tesoreria/politicas-orden-pago/${politicaActual.id}`);

    await screen.findByRole("heading", { level: 1, name: "Borrador inicial" });

    await usuario.click(screen.getByRole("button", { name: "Editar" }));

    const nombre = screen.getByLabelText(/^Nombre/);
    await usuario.clear(nombre);
    await usuario.type(nombre, "Borrador actualizado");

    await usuario.click(screen.getByRole("button", { name: "Guardar" }));

    await screen.findByRole("heading", { level: 1, name: "Borrador actualizado" });

    expect(apiFetchMock).toHaveBeenCalledWith(
      `/gobierno/tesoreria/politicas-orden-pago/${politicaActual.id}`,
      expect.objectContaining({
        method: "PUT",
        ifMatch: "1",
        body: expect.objectContaining({ nombre: "Borrador actualizado" }),
      }),
    );
  });

  it("activar: BORRADOR, diálogo con validación de fundamento y POST /activar", async () => {
    politicaActual = crearPolitica({ estado: "BORRADOR", version: 1, codigo: "POL-BOR", nombre: "Borrador para activar", vigente_desde: "2026-02-01", fundamento: null, documentos: [], historia: [{ evento: "CREADA", version: 1, fecha: "2026-02-01T10:00:00+00:00", actor: "ord_t03" }] });

    const usuario = userEvent.setup();
    renderizar(`/gobierno/tesoreria/politicas-orden-pago/${politicaActual.id}`);

    await screen.findByRole("heading", { level: 1, name: "Borrador para activar" });

    await usuario.click(screen.getByRole("button", { name: "Activar" }));

    const dialogo = await screen.findByRole("dialog");
    expect(within(dialogo).getByText(/El acto administrativo es opcional\./)).toBeInTheDocument();

    const fundamento = within(dialogo).getByLabelText(/^Fundamento de la activación/);
    await usuario.type(fundamento, "Corto");
    await usuario.click(within(dialogo).getByRole("button", { name: "Activar" }));
    expect(await within(dialogo).findByText("El fundamento debe tener entre 20 y 2000 caracteres.")).toBeInTheDocument();

    await usuario.clear(fundamento);
    await usuario.type(fundamento, "Fundamento válido para activar la política.");
    await usuario.click(within(dialogo).getByRole("button", { name: "Activar" }));

    await screen.findByText("Vigente");

    expect(apiFetchMock).toHaveBeenCalledWith(
      `/gobierno/tesoreria/politicas-orden-pago/${politicaActual.id}/activar`,
      expect.objectContaining({
        method: "POST",
        ifMatch: "1",
        body: { fundamento: "Fundamento válido para activar la política." },
      }),
    );
  });

  it("cerrar: VIGENTE, diálogo con validación de motivo y POST /cerrar", async () => {
    politicaActual = crearPolitica({ estado: "VIGENTE", version: 2, codigo: "POL-VIG", nombre: "Política vigente" });

    const usuario = userEvent.setup();
    renderizar(`/gobierno/tesoreria/politicas-orden-pago/${politicaActual.id}`);

    await screen.findByRole("heading", { level: 1, name: "Política vigente" });

    await usuario.click(screen.getByRole("button", { name: "Cerrar" }));

    const dialogo = await screen.findByRole("dialog");
    expect(within(dialogo).getByText("Cerrar la política")).toBeInTheDocument();

    const motivo = within(dialogo).getByLabelText(/^Motivo del cierre/);
    await usuario.type(motivo, "Corto");
    await usuario.click(within(dialogo).getByRole("button", { name: "Cerrar" }));
    expect(await within(dialogo).findByText("El motivo debe tener entre 10 y 500 caracteres.")).toBeInTheDocument();

    await usuario.clear(motivo);
    await usuario.type(motivo, "Motivo válido para cerrar la política.");
    await usuario.click(within(dialogo).getByRole("button", { name: "Cerrar" }));

    await screen.findByText("Cerrada");

    expect(apiFetchMock).toHaveBeenCalledWith(
      `/gobierno/tesoreria/politicas-orden-pago/${politicaActual.id}/cerrar`,
      expect.objectContaining({
        method: "POST",
        ifMatch: "2",
        body: { motivo: "Motivo válido para cerrar la política." },
      }),
    );
  });

  it("VIGENTE no es editable: no hay botón de guardar cambios ni campos editables", async () => {
    politicaActual = crearPolitica({ estado: "VIGENTE", version: 2, codigo: "POL-VIG", nombre: "Política vigente" });

    renderizar(`/gobierno/tesoreria/politicas-orden-pago/${politicaActual.id}`);

    await screen.findByRole("heading", { level: 1, name: "Política vigente" });

    expect(screen.queryByRole("button", { name: "Guardar" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Editar" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/^Código/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/^Nombre/)).not.toBeInTheDocument();
  });

  it("documentos exigidos y vigencia en la ficha: lista el tipo y la vigencia", async () => {
    politicaActual = crearPolitica({
      estado: "VIGENTE",
      codigo: "POL-DOC",
      nombre: "Política con documentos",
      vigente_desde: "2026-03-01",
      vigente_hasta: null,
      documentos: [{ document_type_id: "td-1", obligatorio: true, etapa: "EMISION", condicion: null }],
    });

    renderizar(`/gobierno/tesoreria/politicas-orden-pago/${politicaActual.id}`);

    await screen.findByRole("heading", { level: 1, name: "Política con documentos" });

    const seccionDocumentos = screen.getByRole("heading", { level: 2, name: "Documentos exigidos" }).closest("section")!;
    expect(within(seccionDocumentos).getByText("Factura")).toBeInTheDocument();
    expect(within(seccionDocumentos).getByText(/EMISION/)).toBeInTheDocument();
    expect(within(seccionDocumentos).getByText(/Obligatorio/)).toBeInTheDocument();

    expect(screen.getByText("Vigencia:")).toBeInTheDocument();
    expect(screen.getByText(/01\/03\/2026/)).toBeInTheDocument();
  });

  it("historia: muestra los eventos CREADA y ACTIVADA con su actor", async () => {
    politicaActual = crearPolitica({ estado: "VIGENTE", codigo: "POL-HIS", nombre: "Política histórica" });

    renderizar(`/gobierno/tesoreria/politicas-orden-pago/${politicaActual.id}`);

    await screen.findByRole("heading", { level: 1, name: "Política histórica" });

    const seccionHistoria = screen.getByRole("heading", { level: 2, name: "Historia" }).closest("section")!;
    expect(within(seccionHistoria).getByText("CREADA")).toBeInTheDocument();
    expect(within(seccionHistoria).getByText("ACTIVADA")).toBeInTheDocument();
    expect(within(seccionHistoria).getAllByText(/ord_t03/).length).toBeGreaterThan(0);
  });

  it("sin policy: no aparecen Activar ni Cerrar", async () => {
    capacidades = new Set(["gobierno_ordenes_pago:view"]);
    politicaActual = crearPolitica({ estado: "BORRADOR", codigo: "POL-SIN-PERMISO", nombre: "Sin permiso de gestión" });

    renderizar(`/gobierno/tesoreria/politicas-orden-pago/${politicaActual.id}`);

    await screen.findByRole("heading", { level: 1, name: "Sin permiso de gestión" });

    expect(screen.queryByRole("button", { name: "Activar" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cerrar" })).not.toBeInTheDocument();
  });

  it("403 al activar: muestra el mensaje de permiso", async () => {
    politicaActual = crearPolitica({ estado: "BORRADOR", version: 1, codigo: "POL-403", nombre: "Política con 403" });

    apiFetchMock.mockImplementation(async (ruta: string, opciones?: { method?: string; body?: unknown; ifMatch?: string }) => {
      if (ruta === "/documentos/tipos" && !opciones) {
        return TIPOS_DOCUMENTO;
      }
      const matchBase = ruta.match(/^\/gobierno\/tesoreria\/politicas-orden-pago\/([^/]+)$/);
      if (matchBase && (opciones?.method ?? "GET") === "GET") {
        return { ...politicaActual };
      }
      if (ruta === `/gobierno/tesoreria/politicas-orden-pago/${politicaActual!.id}/activar` && opciones?.method === "POST") {
        throw new ApiError(403, { code: "FORBIDDEN", message: "No tiene permiso para activar esta política.", field_errors: {}, request_id: "r1" });
      }
      return Promise.reject(new Error("Ruta no esperada: " + (opciones?.method ?? "GET") + " " + ruta));
    });

    const usuario = userEvent.setup();
    renderizar(`/gobierno/tesoreria/politicas-orden-pago/${politicaActual.id}`);

    await screen.findByRole("heading", { level: 1, name: "Política con 403" });

    await usuario.click(screen.getByRole("button", { name: "Activar" }));

    const dialogo = await screen.findByRole("dialog");
    const fundamento = within(dialogo).getByLabelText(/^Fundamento de la activación/);
    await usuario.type(fundamento, "Fundamento válido para activar la política.");
    await usuario.click(within(dialogo).getByRole("button", { name: "Activar" }));

    expect(await within(dialogo).findByText("No tiene permiso para activar esta política.")).toBeInTheDocument();
  });

  it("409 al cerrar: muestra el mensaje de conflicto", async () => {
    politicaActual = crearPolitica({ estado: "VIGENTE", version: 2, codigo: "POL-409", nombre: "Política con 409" });

    apiFetchMock.mockImplementation(async (ruta: string, opciones?: { method?: string; body?: unknown; ifMatch?: string }) => {
      if (ruta === "/documentos/tipos" && !opciones) {
        return TIPOS_DOCUMENTO;
      }
      const matchBase = ruta.match(/^\/gobierno\/tesoreria\/politicas-orden-pago\/([^/]+)$/);
      if (matchBase && (opciones?.method ?? "GET") === "GET") {
        return { ...politicaActual };
      }
      if (ruta === `/gobierno/tesoreria/politicas-orden-pago/${politicaActual!.id}/cerrar` && opciones?.method === "POST") {
        throw new ApiError(409, { code: "CONFLICT", message: "La política fue modificada por otro usuario.", field_errors: {}, request_id: "r1" });
      }
      return Promise.reject(new Error("Ruta no esperada: " + (opciones?.method ?? "GET") + " " + ruta));
    });

    const usuario = userEvent.setup();
    renderizar(`/gobierno/tesoreria/politicas-orden-pago/${politicaActual.id}`);

    await screen.findByRole("heading", { level: 1, name: "Política con 409" });

    await usuario.click(screen.getByRole("button", { name: "Cerrar" }));

    const dialogo = await screen.findByRole("dialog");
    const motivo = within(dialogo).getByLabelText(/^Motivo del cierre/);
    await usuario.type(motivo, "Motivo válido para cerrar la política.");
    await usuario.click(within(dialogo).getByRole("button", { name: "Cerrar" }));

    expect(await within(dialogo).findByText("La política fue modificada por otro usuario.")).toBeInTheDocument();
  });

  it("sin gobierno_ordenes_pago:view → Sin acceso y la API no se llama", async () => {
    capacidades = new Set([]);

    renderizar("/gobierno/tesoreria/politicas-orden-pago/b47d44d0-9453-46d1-8c4f-240d88cf6bd1");

    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });
});
