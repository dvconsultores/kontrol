import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ExpedienteContractualPage } from "./ExpedienteContractualPage";
import type { Expediente, PaqueteExpediente } from "./api";
import { formatearInstante } from "@/lib/fecha-de-negocio";

const apiFetchMock = vi.fn();
const descargarArchivoMock = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  ApiError: (await original<typeof import("@/api/client")>()).ApiError,
}));

vi.mock("@/api/descargas", () => ({
  descargarArchivo: (...args: unknown[]) => descargarArchivoMock(...args),
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
  useNotifications: () => ({ notify: notifyMock }),
}));

const notifyMock = vi.fn();

function expediente(over: Partial<Expediente> = {}): Expediente {
  return {
    contrato: { id: "k1", codigo: "CT-2026-0001", tipo: "CONTRATO", tipo_etiqueta: "Contrato", estado: "VIGENTE" },
    resumen: {
      codigo: "CT-2026-0001",
      tipo_etiqueta: "Contrato",
      contratista: { nombre: "Constructora Andina", documento: "1790012345001", representante: "Ana Ruiz" },
      objeto: "Construcción de puente",
      monto_original: "50000.00",
      monto_vigente: "60000.00",
      moneda: "USD",
      fecha_inicio: "2026-01-01",
      fecha_fin_original: "2026-06-30",
      fecha_fin_vigente: "2026-07-30",
      vigencia: "EN_PLAZO",
      vigencia_etiqueta: "En plazo",
      adjudicacion_referencia: "ADJ-2026-0001",
      expediente_numero: "EXP-2026-0001",
      supervisor_actual: { referencia: "S1", nombre: "María Pérez", cargo: "Directora", unidad: "Gestión" },
      cobertura: { total_asignado: "60000.00", completa: true, moneda: "USD" },
      ejecucion: { estado: "EN_EJECUCION", mensaje: "En ejecución" },
    },
    origen: {
      expediente: {
        id: "e1",
        numero: "EXP-2026-0001",
        objeto: "Construcción",
        tipo_contratacion: "Licitación",
        modalidad: "Nacional",
        unidad: "Obras",
        estado: "ADJUDICADO",
        fecha_inicio: "2025-12-01",
        enlace: "/gobierno/contrataciones/expedientes/e1",
      },
      oferta: {
        id: "o1",
        referencia: "OF-2026-0001",
        oferente: "Constructora Andina",
        documento: "1790012345001",
        recibida_en: "2025-11-15T14:30:00Z",
      },
    },
    adjudicacion: {
      id: "a1",
      referencia: "ADJ-2026-0001",
      fecha: "2025-12-20",
      resultado: "Adjudicado",
      motivacion: "Mejor oferta",
      vigente: true,
      acto: { id: "acto1", etiqueta: "Resolución de adjudicación", enlace: "/gobierno/actos/acto1" },
      cargo: "Director General",
      enlace: "/gobierno/contrataciones/expedientes/e1",
    },
    presupuesto: {
      certificados: [],
      compromisos: [],
      control: { mensaje: "Control presupuestario correcto." },
      efectos: "Este expediente no crea certificaciones ni compromisos ni cambia disponibilidades.",
    },
    instrumento: {
      original: {
        monto: "50000.00",
        moneda: "USD",
        fecha_inicio: "2026-01-01",
        fecha_fin: "2026-06-30",
        referencia_instrumento: "CT-2026-0001",
        fecha_formalizacion: "2026-01-10",
        firmante: { cargo: "Director General", funcionario: "Carlos López", conversion: "Ratificación" },
        documento: { id: "d1", titulo: "Contrato firmado", version: 1, sha256: "abc123def4567890" },
        huella: "huella-contrato-original",
        enlace: "/gobierno/contratos/k1",
      },
      vigente: { monto: "60000.00", fecha_fin: "2026-07-30", modificacion_codigo: "CT-2026-0001/AD-001" },
      fecha_consulta: "2026-02-15",
    },
    garantias: [],
    modificaciones: { cantidad: 0, historial: [] },
    supervision: { vigente: null, programada: null, historia: [] },
    ejecucion: {
      proceso: "CNT-03",
      estado: "DISPONIBLE",
      estado_ejecucion: "EN_EJECUCION",
      estado_etiqueta: "En ejecución",
      resumen: {
        valuado_conformado: "0.00",
        valuado_presentado: "0.00",
        saldo: "20000.00",
        facturado: "0.00",
        hitos_total: 2,
        hitos_cumplidos: 0,
        entregables_pendientes: 1,
      },
      inicio: null,
      terminacion: null,
      cierre: null,
      hitos: [
        {
          id: "h1",
          referencia: "HIT-01",
          descripcion: "Primera entrega",
          fecha_prevista: "2026-03-01",
          monto_previsto: "20000.00",
          porcentaje_previsto: null,
          obligatorio: true,
          estado: "VIGENTE",
          cumplido: false,
          recepcion: null,
          valuado_conformado: "0.00",
          facturado: "0.00",
          motivo_anulacion: null,
        },
      ],
      entregables: [],
      valuaciones: [],
      recepciones: [],
      facturas: [],
      enlace: "/gobierno/contratos/k1/ejecucion",
    },
    fuentes_futuras: [
      {
        proceso: "CNT-05",
        titulo: "Bloqueo de pagos por encima del monto contractual",
        estado: "SOURCE_PROCESS_NOT_AVAILABLE",
        mensaje: "El módulo aún no está disponible: el expediente no puede afirmar si hubo actuaciones de este tipo.",
      },
    ],
    terminacion: {
      proceso: "CNT-07",
      situacion: {
        estado: "VIGENTE",
        estado_etiqueta: "Vigente",
        figura: null,
        figura_etiqueta: null,
        fecha_eficacia: null,
        fecha_limite_ejecucion: null,
        cumplimiento_cnt03: false,
        alerta_acto_base: null,
      },
      actuacion: null,
      enlace: "/gobierno/contratos/k1/terminacion",
    },
    actos: [],
    documentos: [
      {
        clave: "doc1",
        tipo: "INSTRUMENTO",
        tipo_etiqueta: "Instrumento contractual",
        titulo: "Contrato firmado",
        proceso: "CNT-01",
        referencia: "CT-2026-0001",
        version: 1,
        sha256: "abc123def4567890",
        fecha: "2026-01-10",
        estado: "DISPONIBLE",
        sellado: false,
        document_id: "doc1",
        version_id: "v1",
        descarga: "/documentos/doc1/versiones/v1/descargar",
        enlace: "/documentos/doc1",
      },
      {
        clave: "doc2",
        tipo: "MODIFICACION",
        tipo_etiqueta: "Modificación contractual",
        titulo: "Adenda firmada",
        proceso: "CNT-02",
        referencia: "CT-2026-0001/AD-001",
        version: 1,
        sha256: "fedcba9876543210",
        fecha: "2026-02-10",
        estado: "DISPONIBLE",
        sellado: true,
        document_id: "doc2",
        version_id: "v2",
        descarga: null,
        enlace: "/documentos/doc2",
      },
    ],
    cronologia_total: 0,
    permisos: { auditoria: false, ver_paquetes: false, generar_paquete: false },
    ...over,
  };
}

const ORDEN_SECCIONES = [
  "Resumen",
  "Origen de contratación",
  "Adjudicación",
  "Presupuesto",
  "Instrumento contractual",
  "Garantías",
  "Modificaciones",
  "Supervisión",
  "Ejecución",
  "Terminación / resolución / rescisión",
  "Actos y documentos",
  "Cronología",
  "Auditoría",
  "Integridad",
  "Exportaciones",
];

function renderConProvider() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/gobierno/contratos/k1/expediente"]}>
        <Routes>
          <Route path="/gobierno/contratos/:contratoId/expediente" element={<ExpedienteContractualPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return queryClient;
}

beforeEach(() => {
  apiFetchMock.mockReset();
  descargarArchivoMock.mockReset();
  notifyMock.mockReset();
  capacidades = new Set(["gobierno_contratos:view"]);
});

async function cargarExpediente(data: Expediente, permisos = {}) {
  apiFetchMock.mockImplementation((ruta: string) => {
    if (String(ruta).endsWith("/expediente")) {
      return Promise.resolve({
        ...data,
        permisos: { ...data.permisos, ...permisos },
      });
    }
    if (String(ruta).includes("/expediente/cronologia")) {
      return Promise.resolve({ items: [], total: 0, limit: 50, offset: 0, procesos: [] });
    }
    return Promise.resolve({ items: [], total: 0 });
  });
}

describe("ExpedienteContractualPage", () => {
  it("renderiza los 15 h2 en orden y la navegación", async () => {
    await cargarExpediente(expediente());
    renderConProvider();

    await screen.findByRole("heading", { name: "Expediente contractual · CT-2026-0001" });
    const headings = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
    expect(headings).toEqual(ORDEN_SECCIONES);

    const nav = screen.getByRole("navigation", { name: "Secciones del expediente" });
    expect(within(nav).getByRole("link", { name: "Resumen" })).toHaveAttribute("href", "#resumen");
    expect(within(nav).getByRole("link", { name: "Integridad" })).toHaveAttribute("href", "#integridad");
  });

  it("distingue Condiciones originales 50000.00 y Condiciones vigentes 60000.00", async () => {
    await cargarExpediente(expediente());
    renderConProvider();

    await screen.findByRole("heading", { name: "Expediente contractual · CT-2026-0001" });
    expect(screen.getAllByText("50000.00 USD")[0]).toBeInTheDocument();
    expect(screen.getAllByText("60000.00 USD")[0]).toBeInTheDocument();
  });

  it("la sección Ejecución muestra los datos proyectados y el mensaje honesto de CNT-05", async () => {
    await cargarExpediente(expediente());
    renderConProvider();

    expect(await screen.findByText("Estado de la ejecución: En ejecución")).toBeInTheDocument();
    expect(screen.getByText("HIT-01")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Abrir la ejecución del contrato" })).toHaveAttribute(
      "href",
      "/gobierno/contratos/k1/ejecucion",
    );
    expect(
      screen.getByText(
        "El módulo aún no está disponible: el expediente no puede afirmar si hubo actuaciones de este tipo.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText("No hubo")).not.toBeInTheDocument();
  });

  it("Comprobar huellas llama a la ruta de integridad y muestra «No coincide»", async () => {
    await cargarExpediente(expediente());
    apiFetchMock.mockImplementation((ruta: string) => {
      if (String(ruta).endsWith("/expediente")) return Promise.resolve(expediente());
      if (String(ruta).endsWith("/expediente/integridad")) {
        return Promise.resolve({
          verificado_en: "2026-02-15T10:00:00Z",
          resumen: { VERIFIED: 0, MISSING: 0, MISMATCH: 1, NOT_APPLICABLE: 0 },
          documentos: [
            { clave: "doc1", titulo: "Contrato firmado", tipo: "INSTRUMENTO", sha256_registrado: "abc123def4567890", resultado: "MISMATCH", detalle: "No coincide" },
          ],
        });
      }
      return Promise.resolve({ items: [], total: 0 });
    });
    const user = userEvent.setup();
    renderConProvider();

    await screen.findByRole("heading", { name: "Expediente contractual · CT-2026-0001" });
    await user.click(screen.getByRole("button", { name: "Comprobar huellas" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith("/gobierno/contratos/k1/expediente/integridad");
    });
    expect((await screen.findAllByText("No coincide"))[0]).toBeInTheDocument();
  });

  it("Generar paquete llama con POST, body proposito e idempotencyKey definido", async () => {
    await cargarExpediente(expediente(), { generar_paquete: true });
    const user = userEvent.setup();
    renderConProvider();

    await screen.findByRole("heading", { name: "Expediente contractual · CT-2026-0001" });
    await user.type(screen.getByLabelText("Propósito del paquete"), "Paquete para control fiscal");
    await user.click(screen.getByRole("button", { name: "Generar paquete" }));

    await waitFor(() => {
      const llamada = apiFetchMock.mock.calls.find(([, opciones]) => opciones?.method === "POST");
      expect(llamada).toBeTruthy();
      expect(llamada?.[0]).toBe("/gobierno/contratos/k1/expediente/paquetes");
      expect(llamada?.[1].body).toEqual({ proposito: "Paquete para control fiscal" });
      expect(llamada?.[1].idempotencyKey).toBeDefined();
    });
  });

  it("Descargar de un documento llama a descargarArchivo con su descarga", async () => {
    await cargarExpediente(expediente());
    descargarArchivoMock.mockResolvedValue("ok");
    const user = userEvent.setup();
    renderConProvider();

    await screen.findByRole("heading", { name: "Expediente contractual · CT-2026-0001" });
    const fila = screen.getByText("Contrato firmado").closest("tr");
    expect(fila).toBeTruthy();
    await user.click(within(fila as HTMLElement).getByRole("button", { name: "Descargar" }));

    await waitFor(() => {
      expect(descargarArchivoMock).toHaveBeenCalledWith("/documentos/doc1/versiones/v1/descargar", "Contrato firmado");
    });
  });

  it("un documento sellado no ofrece descarga y lo anuncia", async () => {
    await cargarExpediente(expediente());
    renderConProvider();
    await screen.findByRole("heading", { name: "Expediente contractual · CT-2026-0001" });
    const fila = screen.getByText("Adenda firmada").closest("tr");
    expect(fila).toBeTruthy();
    expect(within(fila as HTMLElement).getByText("Sellado · la autoridad documental no lo entrega (huella registrada)")).toBeInTheDocument();
    expect(within(fila as HTMLElement).queryByRole("button", { name: "Descargar" })).toBeNull();
  });

  it("409 muestra mensaje de solo formalizados", async () => {
    const { ApiError } = await import("@/api/client");
    apiFetchMock.mockRejectedValue(new ApiError(409, { code: "GOV_CONTRACT_DOSSIER_NOT_FORMALIZED", message: "Solo formalizados" }));
    renderConProvider();

    expect(await screen.findByText("El expediente contractual existe solo para contratos formalizados.")).toBeInTheDocument();
  });

  it("sin permiso de auditoría muestra el texto y NO llama a la ruta de auditoría", async () => {
    await cargarExpediente(expediente(), { auditoria: false });
    renderConProvider();

    expect(
      await screen.findByText("Necesita el permiso de auditoría institucional para ver estos eventos."),
    ).toBeInTheDocument();
    // La primera llamada es a la ruta del expediente; no debe existir llamada a auditoría.
    expect(
      apiFetchMock.mock.calls.some(([ruta]) => String(ruta).includes("/expediente/auditoria")),
    ).toBe(false);
  });

  it("los instantes se muestran con fecha y hora, nunca como «—»", async () => {
    const PAQ: PaqueteExpediente = {
      id: "p1",
      codigo: "EC-2026-0001",
      numero_generacion: 1,
      proposito: "Control fiscal",
      generado_en: "2026-02-15T09:00:00Z",
      generado_por: "auditor",
      corte: "2026-02-15T09:00:00Z",
      eventos: 3,
      documentos_incluidos: 1,
      documentos_excluidos: 1,
      archivos: 8,
      bytes: 1024,
      huella_paquete: "aaaabbbbccccdddd",
      huella_manifiesto: "eeeeffff00001111",
      nombre_archivo: "EC-2026-0001.zip",
      ultima_verificacion: { resultado: "VALIDO", verificado_en: "2026-02-15T10:00:00Z" },
    };

    apiFetchMock.mockImplementation((ruta: string) => {
      if (String(ruta).endsWith("/expediente")) {
        return Promise.resolve({ ...expediente(), permisos: { auditoria: false, ver_paquetes: true, generar_paquete: false } });
      }
      if (String(ruta).includes("/expediente/paquetes")) {
        return Promise.resolve({ items: [PAQ], total: 1 });
      }
      return Promise.resolve({ items: [], total: 0, limit: 50, offset: 0, procesos: [] });
    });

    renderConProvider();
    await screen.findByRole("heading", { name: "Expediente contractual · CT-2026-0001" });

    expect(screen.getByText(formatearInstante("2025-11-15T14:30:00Z"))).toBeInTheDocument();
    expect(await screen.findByText(formatearInstante("2026-02-15T09:00:00Z"))).toBeInTheDocument();
    expect(screen.getByText(`Válido · ${formatearInstante("2026-02-15T10:00:00Z")}`)).toBeInTheDocument();
    expect(screen.queryByText("Válido · —")).toBeNull();
  });
});
