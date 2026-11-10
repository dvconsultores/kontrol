import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { Link } from "react-router";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { TextInput } from "@/components/TextInput";
import { formatearInstante, horaDeCaracasParaInput, instanteDesdeHoraDeCaracas } from "@/lib/fecha-de-negocio";
import type { DocumentSummary } from "@/modules/documentos/types";
import { CONSULTA_EXPEDIENTES, type ExpedienteDetalle } from "../api";

const SELECT_CLASS =
  "block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600";

type Criterio = {
  id: string;
  aspecto: "TECNICO" | "ECONOMICO" | "LEGAL";
  orden: number;
  nombre: string;
  descripcion: string | null;
  escala: "PUNTAJE" | "CUMPLE";
  puntaje_maximo: string | null;
  ponderacion: string | null;
};

type Matriz = {
  id: string;
  estado: "BORRADOR" | "BLOQUEADA";
  version: number;
  transcripcion: boolean;
  pliego: { documento_id: string; version_id: string; huella: string };
  criterios: Criterio[];
};

type Apertura = {
  id: string;
  referencia: string;
  abierta_en: string;
  abierta_por: string | null;
  acta: { documento_id: string; titulo: string; huella: string };
  observaciones: string | null;
  miembros_con_voto: number;
  asistentes_con_voto: number;
  quorum_requerido: number;
  asistentes: {
    member_id: string;
    oficial: string;
    funcion: string;
    condicion: string;
    cuenta_voto: boolean;
  }[];
  ofertas: { id: string; oferta: string }[];
};

type OfertaEstado = {
  id: string;
  oferta: string;
  oferente: string;
  situacion: "ABIERTA" | "PENDIENTE_APERTURA";
  situacion_etiqueta: string;
  sellada: boolean;
};

type Miembro = {
  id: string;
  oficial: string;
  funcion: "MIEMBRO" | "SECRETARIO";
  condicion: "PRINCIPAL" | "SUPLENTE";
  suplente_de_id: string | null;
};

type Aporte = {
  id: string;
  miembro_id: string;
  miembro: string;
  puntaje: string | null;
  cumple: boolean | null;
  observacion: string | null;
  evidencia_documento_id: string | null;
  registrado_en: string;
  reemplaza_a: string | null;
  historial_reemplazos: {
    id: string;
    puntaje: string | null;
    cumple: boolean | null;
    observacion: string | null;
    registrado_en: string;
  }[];
};

type Resultado = {
  id: string;
  puntaje: string | null;
  cumple: boolean | null;
  observacion: string | null;
  evidencia_documento_id: string | null;
  registrado_en: string;
  registrado_por: string;
  historial_reemplazos: {
    id: string;
    puntaje: string | null;
    cumple: boolean | null;
    observacion: string | null;
    registrado_en: string;
  }[];
};

type ResultadoPorOferta = {
  oferta_id: string;
  oferta: string;
  criterio_id: string;
  aspecto: string;
  criterio: string;
  escala: "PUNTAJE" | "CUMPLE";
  aportes: Aporte[];
  resultado_comision: Resultado | null;
};

type EstadoEvaluacion = {
  matriz: Matriz | null;
  aperturas: Apertura[];
  ofertas: OfertaEstado[];
  miembros: Miembro[];
  recepcion_concluida_en: string | null;
  evaluacion_concluida_en: string | null;
  siguiente_accion: string;
  resultados_por_oferta: ResultadoPorOferta[];
  resultados_faltantes: Record<string, string[]>;
  progreso: {
    ofertas_abiertas: number;
    criterios: number;
    resultados_requeridos: number;
    resultados_registrados: number;
  };
};

type DocumentoExpediente = DocumentSummary & { link: { is_frozen: boolean } };

type OfertaRecepcion = {
  id: string;
  referencia: string;
  oferente_nombre: string;
  canal_etiqueta: string;
  recibida_en: string;
  confidencialidad_etiqueta: string;
  integridad: "VERIFICADA" | "ALTERADA" | "SIN_ARCHIVO";
  situacion_etiqueta: string;
};

type DocumentoOferta = {
  version_numero: number;
  documento_id: string | null;
  titulo: string | null;
};

function huellaAbreviada(huella: string | null | undefined): string {
  if (!huella) return "—";
  return huella.length > 12 ? `${huella.slice(0, 12)}…` : huella;
}

function valorAporte(aporte: { puntaje: string | null; cumple: boolean | null }): string {
  if (aporte.puntaje !== null && aporte.puntaje !== undefined) return aporte.puntaje;
  if (aporte.cumple === true) return "Cumple";
  if (aporte.cumple === false) return "No cumple";
  return "—";
}

function mensajeError(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "Ocurrió un error inesperado";
}

function erroresDeCampos(error: unknown): Record<string, string[]> {
  if (error instanceof ApiError) return error.fieldErrors ?? {};
  return {};
}

function textoErrorPorCodigo(error: unknown): string {
  if (!(error instanceof ApiError)) return "Ocurrió un error inesperado";
  switch (error.code) {
    case "GOV_OPENING_RECEPTION_OPEN":
      return "Primero concluya la recepción de ofertas";
    case "GOV_OFFER_ALREADY_OPENED":
      return "La oferta ya fue abierta";
    case "GOV_EVAL_MATRIX_STALE":
    case "GOV_EVAL_VERSION_STALE":
    case "GOV_PROCUREMENT_FILE_STALE":
      return "Los datos cambiaron; se actualizaron, revise e intente de nuevo";
    case "GOV_EVAL_MATRIX_LOCKED":
      return "La matriz está bloqueada: los criterios no pueden cambiar";
    case "GOV_EVAL_NOT_MEMBER":
      return "Solo un miembro de la Comisión puede registrar esta evaluación";
    case "GOV_EVAL_IDENTITY_REQUIRED":
      return "Su cuenta debe estar vinculada a un funcionario institucional";
    case "GOV_OPENING_NOT_ATTENDEE":
      return "Su funcionario debe figurar entre los asistentes";
    default:
      return error.message;
  }
}

function TarjetaCriterio({
  criterio,
  onQuitar,
  puedeQuitar,
}: {
  criterio: Criterio;
  onQuitar?: () => void;
  puedeQuitar: boolean;
}) {
  return (
    <div className="rounded-lg border border-border-subtle bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 break-words">
          <h4 className="text-sm font-semibold text-text-900">{criterio.nombre}</h4>
          <p className="mt-1 text-sm text-text-600">
            {criterio.escala === "PUNTAJE"
              ? `Puntaje hasta ${criterio.puntaje_maximo ?? "—"}`
              : "Cumple / no cumple"}
            {criterio.ponderacion ? ` · Ponderación ${criterio.ponderacion}` : ""}
          </p>
          {criterio.descripcion ? (
            <p className="mt-1 min-w-0 break-words text-sm text-text-600">{criterio.descripcion}</p>
          ) : null}
        </div>
        {puedeQuitar && onQuitar ? (
          <Button variant="danger" size="sm" onClick={onQuitar} aria-label={`Quitar ${criterio.nombre}`}>
            Quitar {criterio.nombre}
          </Button>
        ) : null}
      </div>
    </div>
  );
}

function FormularioCriterio({
  onGuardar,
  enviando,
  error,
}: {
  onGuardar: (criterio: {
    aspecto: Criterio["aspecto"];
    orden: number;
    nombre: string;
    descripcion: string | null;
    escala: Criterio["escala"];
    puntaje_maximo: string | null;
    ponderacion: string | null;
  }) => void;
  enviando: boolean;
  error: string | null;
}) {
  const [aspecto, setAspecto] = useState<Criterio["aspecto"]>("TECNICO");
  const [orden, setOrden] = useState("1");
  const [nombre, setNombre] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [escala, setEscala] = useState<Criterio["escala"]>("PUNTAJE");
  const [puntajeMaximo, setPuntajeMaximo] = useState("");
  const [ponderacion, setPonderacion] = useState("");

  function enviar() {
    onGuardar({
      aspecto,
      orden: Number(orden),
      nombre,
      descripcion: descripcion.trim() === "" ? null : descripcion,
      escala,
      puntaje_maximo: escala === "PUNTAJE" ? puntajeMaximo : null,
      ponderacion: ponderacion.trim() === "" ? null : ponderacion,
    });
  }

  return (
    <div className="rounded-lg border border-border-subtle bg-white p-4">
      <h4 className="text-sm font-semibold text-text-900">Añadir criterio</h4>
      <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <FormField label="Aspecto" htmlFor="nuevo-criterio-aspecto" required>
          <select
            id="nuevo-criterio-aspecto"
            className={SELECT_CLASS}
            value={aspecto}
            onChange={(e) => setAspecto(e.target.value as Criterio["aspecto"])}
          >
            <option value="TECNICO">Técnico</option>
            <option value="ECONOMICO">Económico</option>
            <option value="LEGAL">Legal</option>
          </select>
        </FormField>
        <FormField label="Orden" htmlFor="nuevo-criterio-orden" required>
          <TextInput
            id="nuevo-criterio-orden"
            type="number"
            min={1}
            value={orden}
            onChange={(e) => setOrden(e.target.value)}
          />
        </FormField>
        <FormField label="Nombre" htmlFor="nuevo-criterio-nombre" required>
          <TextInput
            id="nuevo-criterio-nombre"
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
          />
        </FormField>
        <FormField label="Descripción" htmlFor="nuevo-criterio-descripcion">
          <TextInput
            id="nuevo-criterio-descripcion"
            value={descripcion}
            onChange={(e) => setDescripcion(e.target.value)}
          />
        </FormField>
        <FormField label="Escala" htmlFor="nuevo-criterio-escala" required>
          <select
            id="nuevo-criterio-escala"
            className={SELECT_CLASS}
            value={escala}
            onChange={(e) => setEscala(e.target.value as Criterio["escala"])}
          >
            <option value="PUNTAJE">Puntaje</option>
            <option value="CUMPLE">Cumple</option>
          </select>
        </FormField>
        {escala === "PUNTAJE" ? (
          <FormField label="Puntaje máximo" htmlFor="nuevo-criterio-puntaje" required>
            <TextInput
              id="nuevo-criterio-puntaje"
              inputMode="decimal"
              value={puntajeMaximo}
              onChange={(e) => setPuntajeMaximo(e.target.value)}
            />
          </FormField>
        ) : null}
        <FormField label="Ponderación" htmlFor="nuevo-criterio-ponderacion">
          <TextInput
            id="nuevo-criterio-ponderacion"
            inputMode="decimal"
            value={ponderacion}
            onChange={(e) => setPonderacion(e.target.value)}
          />
        </FormField>
      </div>
      {error ? (
        <p role="alert" className="mt-2 text-sm text-red-700">
          {error}
        </p>
      ) : null}
      <div className="mt-3 flex flex-wrap gap-2">
        <Button variant="primary" onClick={enviar} disabled={enviando}>
          {enviando ? "Guardando…" : "Guardar criterio"}
        </Button>
      </div>
    </div>
  );
}

function FormularioAporte({
  oferta,
  criterio,
  escala,
  miembros,
  documentos,
  tipo,
  onGuardar,
  enviando,
  error,
  fieldErrors,
}: {
  oferta: string;
  criterio: string;
  escala: "PUNTAJE" | "CUMPLE";
  miembros: Miembro[];
  documentos: DocumentoExpediente[];
  tipo: "aporte" | "resultado";
  onGuardar: (cuerpo: {
    miembro_id: string;
    puntaje: string | null;
    cumple: boolean | null;
    observacion: string | null;
    evidencia_documento_id: string | null;
  }) => void;
  enviando: boolean;
  error: string | null;
  fieldErrors: Record<string, string[]>;
}) {
  const prefijo = `${tipo}-${oferta}-${criterio}`;
  const [miembroId, setMiembroId] = useState("");
  const [puntaje, setPuntaje] = useState("");
  const [cumple, setCumple] = useState<"true" | "false" | "">("");
  const [observacion, setObservacion] = useState("");
  const [evidencia, setEvidencia] = useState("");

  const miembrosDisponibles =
    tipo === "aporte" ? miembros.filter((m) => m.funcion === "MIEMBRO") : miembros;

  function enviar() {
    onGuardar({
      miembro_id: miembroId,
      puntaje: escala === "PUNTAJE" ? puntaje : null,
      cumple: escala === "CUMPLE" ? cumple === "true" : null,
      observacion: observacion.trim() === "" ? null : observacion,
      evidencia_documento_id: evidencia === "" ? null : evidencia,
    });
  }

  return (
    <div className="mt-3 rounded-lg border border-border-subtle bg-white p-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <FormField
          label="Evaluador"
          htmlFor={`${prefijo}-miembro`}
          required
          error={fieldErrors.miembro_id?.[0]}
        >
          <select
            id={`${prefijo}-miembro`}
            className={SELECT_CLASS}
            value={miembroId}
            onChange={(e) => setMiembroId(e.target.value)}
          >
            <option value="">Seleccione…</option>
            {miembrosDisponibles.map((m) => (
              <option key={m.id} value={m.id}>
                {m.oficial} · {m.funcion === "MIEMBRO" ? "Miembro" : "Secretario"} · {m.condicion === "PRINCIPAL" ? "Principal" : "Suplente"}
              </option>
            ))}
          </select>
        </FormField>
        {escala === "PUNTAJE" ? (
          <FormField
            label="Puntaje"
            htmlFor={`${prefijo}-puntaje`}
            required
            help="Hasta el máximo del criterio, con dos decimales"
            error={fieldErrors.puntaje?.[0]}
          >
            <TextInput
              id={`${prefijo}-puntaje`}
              inputMode="decimal"
              value={puntaje}
              onChange={(e) => setPuntaje(e.target.value)}
            />
          </FormField>
        ) : (
          <fieldset>
            <legend className="text-sm font-medium text-text-900">Cumplimiento</legend>
            <div className="mt-2 flex flex-wrap gap-4">
              <label className="flex items-center gap-2 text-sm text-text-900">
                <input
                  type="radio"
                  name={`${prefijo}-cumple`}
                  value="true"
                  checked={cumple === "true"}
                  onChange={() => setCumple("true")}
                />
                Cumple
              </label>
              <label className="flex items-center gap-2 text-sm text-text-900">
                <input
                  type="radio"
                  name={`${prefijo}-cumple`}
                  value="false"
                  checked={cumple === "false"}
                  onChange={() => setCumple("false")}
                />
                No cumple
              </label>
            </div>
            {fieldErrors.cumple?.[0] ? (
              <p role="alert" className="mt-2 text-sm text-red-700">
                {fieldErrors.cumple[0]}
              </p>
            ) : null}
          </fieldset>
        )}
        <FormField label="Observación" htmlFor={`${prefijo}-observacion`}>
          <TextInput
            id={`${prefijo}-observacion`}
            value={observacion}
            onChange={(e) => setObservacion(e.target.value)}
          />
        </FormField>
        <FormField label="Evidencia" htmlFor={`${prefijo}-evidencia`}>
          <select
            id={`${prefijo}-evidencia`}
            className={SELECT_CLASS}
            value={evidencia}
            onChange={(e) => setEvidencia(e.target.value)}
          >
            <option value="">Sin evidencia</option>
            {documentos.map((d) => (
              <option key={d.id} value={d.id}>
                {d.title}
              </option>
            ))}
          </select>
        </FormField>
      </div>
      {error ? (
        <p role="alert" className="mt-2 text-sm text-red-700">
          {error}
        </p>
      ) : null}
      <div className="mt-3 flex flex-wrap gap-2">
        <Button variant="primary" onClick={enviar} disabled={enviando}>
          {enviando ? "Guardando…" : tipo === "aporte" ? "Guardar aporte" : "Guardar resultado"}
        </Button>
      </div>
    </div>
  );
}

function TarjetaEvaluacionCriterio({
  item,
  miembros,
  documentos,
  puedeEvaluar,
  evaluacionConcluida,
  onRegistrar,
}: {
  item: ResultadoPorOferta;
  miembros: Miembro[];
  documentos: DocumentoExpediente[];
  puedeEvaluar: boolean;
  evaluacionConcluida: boolean;
  onRegistrar: (
    tipo: "aporte" | "resultado",
    cuerpo: {
      miembro_id: string;
      puntaje: string | null;
      cumple: boolean | null;
      observacion: string | null;
      evidencia_documento_id: string | null;
    },
  ) => void;
}) {
  const [formulario, setFormulario] = useState<"aporte" | "resultado" | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});

  async function guardar(tipo: "aporte" | "resultado", cuerpo: {
    miembro_id: string;
    puntaje: string | null;
    cumple: boolean | null;
    observacion: string | null;
    evidencia_documento_id: string | null;
  }) {
    setEnviando(true);
    setError(null);
    setFieldErrors({});
    try {
      await onRegistrar(tipo, cuerpo);
      setFormulario(null);
    } catch (e) {
      setError(textoErrorPorCodigo(e));
      setFieldErrors(erroresDeCampos(e));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="rounded-lg border border-border-subtle bg-white p-4">
      <div className="min-w-0 break-words">
        <h4 className="text-sm font-semibold text-text-900">{item.criterio}</h4>
        <p className="mt-1 text-sm text-text-600">
          {item.aspecto === "TECNICO" ? "Técnico" : item.aspecto === "ECONOMICO" ? "Económico" : item.aspecto === "LEGAL" ? "Legal" : item.aspecto} · {item.escala === "PUNTAJE" ? "Puntaje" : "Cumple / no cumple"}
        </p>
      </div>
      <div className="mt-3">
        <p className="text-xs font-medium text-text-600">Aportes</p>
        {item.aportes.length === 0 ? (
          <p className="mt-1 text-sm text-text-600">Sin aportes</p>
        ) : (
          <ul className="mt-2 space-y-2">
            {item.aportes.map((aporte) => (
              <li key={aporte.id} className="rounded-md border border-border-subtle p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium text-text-900">{aporte.miembro}</span>
                  <span className="text-sm text-text-900">{valorAporte(aporte)}</span>
                  <span className="text-xs font-medium text-green-700">Vigente</span>
                </div>
                {aporte.observacion ? (
                  <p className="mt-1 min-w-0 break-words text-sm text-text-600">{aporte.observacion}</p>
                ) : null}
                <p className="mt-1 text-xs text-text-600">{formatearInstante(aporte.registrado_en)}</p>
                {aporte.historial_reemplazos.length > 0 ? (
                  <details className="mt-2">
                    <summary className="cursor-pointer text-sm text-text-600">
                      Historial ({aporte.historial_reemplazos.length})
                    </summary>
                    <ul className="mt-2 space-y-1">
                      {aporte.historial_reemplazos.map((h) => (
                        <li key={h.id} className="text-sm text-text-600">
                          {valorAporte(h)} · {formatearInstante(h.registrado_en)}
                          {h.observacion ? ` · ${h.observacion}` : ""}
                        </li>
                      ))}
                    </ul>
                  </details>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="mt-4 rounded-md border border-brand-600 bg-brand-50 p-3">
        <p className="text-xs font-semibold text-brand-700">Resultado de la Comisión</p>
        {item.resultado_comision ? (
          <div className="mt-2">
            <p className="text-sm font-medium text-text-900">{valorAporte(item.resultado_comision)}</p>
            {item.resultado_comision.observacion ? (
              <p className="mt-1 min-w-0 break-words text-sm text-text-600">
                {item.resultado_comision.observacion}
              </p>
            ) : null}
            <p className="mt-1 text-xs text-text-600">
              Registrado por {item.resultado_comision.registrado_por} ·{" "}
              {formatearInstante(item.resultado_comision.registrado_en)}
            </p>
            {item.resultado_comision.historial_reemplazos.length > 0 ? (
              <details className="mt-2">
                <summary className="cursor-pointer text-sm text-text-600">
                  Historial ({item.resultado_comision.historial_reemplazos.length})
                </summary>
                <ul className="mt-2 space-y-1">
                  {item.resultado_comision.historial_reemplazos.map((h) => (
                    <li key={h.id} className="text-sm text-text-600">
                      {valorAporte(h)} · {formatearInstante(h.registrado_en)}
                      {h.observacion ? ` · ${h.observacion}` : ""}
                    </li>
                  ))}
                </ul>
              </details>
            ) : null}
          </div>
        ) : (
          <p className="mt-1 text-sm text-text-600">Pendiente</p>
        )}
      </div>
      {puedeEvaluar && !evaluacionConcluida ? (
        <div className="mt-3 flex flex-wrap gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setFormulario(formulario === "aporte" ? null : "aporte")}
            aria-label={`Registrar aporte de ${item.criterio} para ${item.oferta}`}
          >
            Registrar aporte
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setFormulario(formulario === "resultado" ? null : "resultado")}
            aria-label={`Registrar resultado de la Comisión de ${item.criterio} para ${item.oferta}`}
          >
            Registrar resultado de la Comisión
          </Button>
        </div>
      ) : null}
      {formulario ? (
        <FormularioAporte
          oferta={item.oferta}
          criterio={item.criterio_id}
          escala={item.escala}
          miembros={miembros}
          documentos={documentos}
          tipo={formulario}
          onGuardar={(cuerpo) => guardar(formulario, cuerpo)}
          enviando={enviando}
          error={error}
          fieldErrors={fieldErrors}
        />
      ) : null}
    </div>
  );
}

export function SeccionEvaluacion({
  detalle,
  activeCompanyId,
}: {
  detalle: ExpedienteDetalle;
  activeCompanyId: string | null;
}) {
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();
  const encabezadoAperturaRef = useRef<HTMLHeadingElement | null>(null);

  const puedeVer = tiene("gobierno_evaluacion:view", "empresa");
  const puedeCriterios = tiene("gobierno_evaluacion:criteria", "empresa");
  const puedeAbrir = tiene("gobierno_evaluacion:open", "empresa");
  const puedeEvaluar = tiene("gobierno_evaluacion:evaluate", "empresa");
  const puedeVerDocumentos = tiene("documentos:view", "empresa");

  const evaluacionQuery = useQuery({
    queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId, "evaluacion", detalle.id],
    queryFn: () =>
      apiFetch<EstadoEvaluacion>(`/gobierno/contrataciones/expedientes/${detalle.id}/evaluacion`),
    enabled: puedeVer && Boolean(activeCompanyId),
  });

  const documentosQuery = useQuery({
    queryKey: ["documentos", "por-recurso", "GovernmentProcurementFile", detalle.id],
    queryFn: () =>
      apiFetch<DocumentoExpediente[]>(
        `/documentos/por-recurso/GovernmentProcurementFile/${detalle.id}`,
      ),
    enabled: puedeVerDocumentos && Boolean(activeCompanyId),
  });

  const ofertasRecepcionQuery = useQuery({
    queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId, "ofertas", detalle.id],
    queryFn: () =>
      apiFetch<{ items: OfertaRecepcion[] }>(`/gobierno/contrataciones/expedientes/${detalle.id}/ofertas`),
    enabled: puedeVer && Boolean(activeCompanyId),
  });

  const [enviandoMatriz, setEnviandoMatriz] = useState(false);
  const [errorMatriz, setErrorMatriz] = useState<string | null>(null);
  const [fieldErrorsMatriz, setFieldErrorsMatriz] = useState<Record<string, string[]>>({});
  const [pliegoId, setPliegoId] = useState("");

  const [enviandoCriterio, setEnviandoCriterio] = useState(false);
  const [errorCriterio, setErrorCriterio] = useState<string | null>(null);
  const [fieldErrorsCriterio, setFieldErrorsCriterio] = useState<Record<string, string[]>>({});
  const [confirmarBloqueo, setConfirmarBloqueo] = useState(false);
  const [enviandoBloqueo, setEnviandoBloqueo] = useState(false);
  const [errorBloqueo, setErrorBloqueo] = useState<string | null>(null);

  const [mostrarApertura, setMostrarApertura] = useState(false);
  const [enviandoApertura, setEnviandoApertura] = useState(false);
  const [errorApertura, setErrorApertura] = useState<string | null>(null);
  const [fieldErrorsApertura, setFieldErrorsApertura] = useState<Record<string, string[]>>({});
  const [exitoApertura, setExitoApertura] = useState<string | null>(null);
  const [confirmarApertura, setConfirmarApertura] = useState(false);
  const [ofertasSeleccionadas, setOfertasSeleccionadas] = useState<string[]>([]);
  const [asistentesSeleccionados, setAsistentesSeleccionados] = useState<string[]>([]);
  const [actaId, setActaId] = useState("");
  const [fechaApertura, setFechaApertura] = useState(horaDeCaracasParaInput());
  const [observacionesApertura, setObservacionesApertura] = useState("");

  const [enviandoConclusion, setEnviandoConclusion] = useState(false);
  const [errorConclusion, setErrorConclusion] = useState<string | null>(null);
  const [confirmarConclusion, setConfirmarConclusion] = useState(false);

  const [documentosOferta, setDocumentosOferta] = useState<Record<string, DocumentoOferta[]>>({});
  const [cargandoDocumentosOferta, setCargandoDocumentosOferta] = useState<string | null>(null);

  if (!puedeVer) return null;

  const estado = evaluacionQuery.data;
  const documentos = documentosQuery.data ?? [];
  const recepciones = ofertasRecepcionQuery.data?.items ?? [];

  function invalidar() {
    void queryClient.invalidateQueries({ queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId] });
    void queryClient.invalidateQueries({ queryKey: ["documentos"] });
  }

  async function registrarMatriz() {
    setEnviandoMatriz(true);
    setErrorMatriz(null);
    setFieldErrorsMatriz({});
    try {
      await apiFetch(`/gobierno/contrataciones/expedientes/${detalle.id}/evaluacion/matriz`, {
        method: "POST",
        body: { pliego_documento_id: pliegoId },
        ifMatch: String(detalle.version),
      });
      invalidar();
      notify({ type: "success", title: "Matriz registrada" });
    } catch (e) {
      setErrorMatriz(textoErrorPorCodigo(e));
      setFieldErrorsMatriz(erroresDeCampos(e));
      if (e instanceof ApiError && ["GOV_EVAL_MATRIX_STALE", "GOV_EVAL_VERSION_STALE", "GOV_PROCUREMENT_FILE_STALE"].includes(e.code)) {
        invalidar();
      }
    } finally {
      setEnviandoMatriz(false);
    }
  }

  async function guardarCriterio(criterio: {
    aspecto: Criterio["aspecto"];
    orden: number;
    nombre: string;
    descripcion: string | null;
    escala: Criterio["escala"];
    puntaje_maximo: string | null;
    ponderacion: string | null;
  }) {
    if (!estado?.matriz) return;
    setEnviandoCriterio(true);
    setErrorCriterio(null);
    setFieldErrorsCriterio({});
    try {
      await apiFetch(`/gobierno/contrataciones/expedientes/${detalle.id}/evaluacion/matriz/criterios`, {
        method: "POST",
        body: criterio,
        ifMatch: String(estado.matriz.version),
      });
      invalidar();
      notify({ type: "success", title: "Criterio añadido" });
    } catch (e) {
      setErrorCriterio(textoErrorPorCodigo(e));
      setFieldErrorsCriterio(erroresDeCampos(e));
      if (e instanceof ApiError && ["GOV_EVAL_MATRIX_STALE", "GOV_EVAL_VERSION_STALE", "GOV_PROCUREMENT_FILE_STALE"].includes(e.code)) {
        invalidar();
      }
    } finally {
      setEnviandoCriterio(false);
    }
  }

  async function quitarCriterio(criterioId: string) {
    if (!estado?.matriz) return;
    setErrorCriterio(null);
    setFieldErrorsCriterio({});
    try {
      await apiFetch(
        `/gobierno/contrataciones/expedientes/${detalle.id}/evaluacion/matriz/criterios/${criterioId}`,
        {
          method: "DELETE",
          ifMatch: String(estado.matriz.version),
        },
      );
      invalidar();
      notify({ type: "success", title: "Criterio eliminado" });
    } catch (e) {
      setErrorCriterio(textoErrorPorCodigo(e));
      setFieldErrorsCriterio(erroresDeCampos(e));
      if (e instanceof ApiError && ["GOV_EVAL_MATRIX_STALE", "GOV_EVAL_VERSION_STALE", "GOV_PROCUREMENT_FILE_STALE"].includes(e.code)) {
        invalidar();
      }
    }
  }

  async function bloquearMatriz() {
    if (!estado?.matriz) return;
    setEnviandoBloqueo(true);
    setErrorBloqueo(null);
    try {
      await apiFetch(`/gobierno/contrataciones/expedientes/${detalle.id}/evaluacion/matriz/bloquear`, {
        method: "POST",
        body: {},
        ifMatch: String(estado.matriz.version),
      });
      invalidar();
      notify({ type: "success", title: "Matriz bloqueada" });
      setConfirmarBloqueo(false);
    } catch (e) {
      setErrorBloqueo(textoErrorPorCodigo(e));
      if (e instanceof ApiError && ["GOV_EVAL_MATRIX_STALE", "GOV_EVAL_VERSION_STALE", "GOV_PROCUREMENT_FILE_STALE"].includes(e.code)) {
        invalidar();
      }
    } finally {
      setEnviandoBloqueo(false);
    }
  }

  async function abrirOfertas() {
    setEnviandoApertura(true);
    setErrorApertura(null);
    setFieldErrorsApertura({});
    setExitoApertura(null);
    const instante = instanteDesdeHoraDeCaracas(fechaApertura);
    try {
      await apiFetch(`/gobierno/contrataciones/expedientes/${detalle.id}/evaluacion/aperturas`, {
        method: "POST",
        body: {
          abierta_en: instante,
          oferta_ids: ofertasSeleccionadas,
          miembro_ids: asistentesSeleccionados,
          acta_documento_id: actaId,
          observaciones: observacionesApertura.trim() === "" ? null : observacionesApertura,
        },
        ifMatch: String(detalle.version),
      });
      invalidar();
      notify({ type: "success", title: "Ofertas abiertas" });
      setExitoApertura("Ofertas abiertas");
      setMostrarApertura(false);
      setConfirmarApertura(false);
      setOfertasSeleccionadas([]);
      setAsistentesSeleccionados([]);
      setActaId("");
      setObservacionesApertura("");
      setFechaApertura(horaDeCaracasParaInput());
      requestAnimationFrame(() => encabezadoAperturaRef.current?.focus());
    } catch (e) {
      setErrorApertura(textoErrorPorCodigo(e));
      setFieldErrorsApertura(erroresDeCampos(e));
      if (e instanceof ApiError && ["GOV_EVAL_MATRIX_STALE", "GOV_EVAL_VERSION_STALE", "GOV_PROCUREMENT_FILE_STALE"].includes(e.code)) {
        invalidar();
      }
    } finally {
      setEnviandoApertura(false);
    }
  }

  async function registrarEvaluacion(
    tipo: "aporte" | "resultado",
    ofertaId: string,
    criterioId: string,
    cuerpo: {
      miembro_id: string;
      puntaje: string | null;
      cumple: boolean | null;
      observacion: string | null;
      evidencia_documento_id: string | null;
    },
  ) {
    if (!estado?.matriz) return;
    const ruta =
      tipo === "aporte"
        ? `/gobierno/contrataciones/expedientes/${detalle.id}/evaluacion/aportes`
        : `/gobierno/contrataciones/expedientes/${detalle.id}/evaluacion/resultados`;
    await apiFetch(ruta, {
      method: "POST",
      body: {
        oferta_id: ofertaId,
        criterio_id: criterioId,
        miembro_id: cuerpo.miembro_id,
        matriz_version: estado.matriz.version,
        puntaje: cuerpo.puntaje,
        cumple: cuerpo.cumple,
        observacion: cuerpo.observacion,
        evidencia_documento_id: cuerpo.evidencia_documento_id,
      },
      ifMatch: String(detalle.version),
    });
    invalidar();
    notify({
      type: "success",
      title: tipo === "aporte" ? "Aporte registrado" : "Resultado de la Comisión registrado",
    });
  }

  async function concluirEvaluacion() {
    setEnviandoConclusion(true);
    setErrorConclusion(null);
    try {
      await apiFetch(`/gobierno/contrataciones/expedientes/${detalle.id}/evaluacion/concluir`, {
        method: "POST",
        body: {},
        ifMatch: String(detalle.version),
      });
      invalidar();
      notify({ type: "success", title: "Evaluación concluida" });
      setConfirmarConclusion(false);
    } catch (e) {
      setErrorConclusion(textoErrorPorCodigo(e));
      if (e instanceof ApiError && ["GOV_EVAL_MATRIX_STALE", "GOV_EVAL_VERSION_STALE", "GOV_PROCUREMENT_FILE_STALE"].includes(e.code)) {
        invalidar();
      }
    } finally {
      setEnviandoConclusion(false);
    }
  }

  async function cargarDocumentosOferta(ofertaId: string) {
    setCargandoDocumentosOferta(ofertaId);
    try {
      const data = await apiFetch<{ documentos: DocumentoOferta[] }>(
        `/gobierno/contrataciones/expedientes/${detalle.id}/ofertas/${ofertaId}`,
      );
      setDocumentosOferta((prev) => ({ ...prev, [ofertaId]: data.documentos }));
    } catch {
      notify({ type: "error", title: "No se pudieron cargar los documentos de la oferta" });
    } finally {
      setCargandoDocumentosOferta(null);
    }
  }

  if (evaluacionQuery.isLoading) {
    return (
      <section aria-labelledby="sec-evaluacion" className="mt-6">
        <h2 id="sec-evaluacion" className="text-lg font-semibold text-text-900">
          Apertura y evaluación
        </h2>
        <LoadingState />
      </section>
    );
  }

  if (evaluacionQuery.isError || !estado) {
    return (
      <section aria-labelledby="sec-evaluacion" className="mt-6">
        <h2 id="sec-evaluacion" className="text-lg font-semibold text-text-900">
          Apertura y evaluación
        </h2>
        <p role="alert" className="mt-2 text-sm text-red-700">
          {mensajeError(evaluacionQuery.error)}
        </p>
      </section>
    );
  }

  const recepcionPorId = new Map(recepciones.map((r) => [r.id, r]));
  const ofertasPendientes = estado.ofertas.filter((o) => o.situacion === "PENDIENTE_APERTURA");
  const ofertasAbiertas = estado.ofertas.filter((o) => o.situacion === "ABIERTA");
  const miembrosConVoto = estado.miembros.filter(
    (m) => m.funcion === "MIEMBRO" && m.condicion === "PRINCIPAL",
  );
  const quorumRequerido = Math.floor(miembrosConVoto.length / 2) + 1;
  const principalesMarcados = new Set(
    asistentesSeleccionados
      .map((id) => estado.miembros.find((m) => m.id === id))
      .filter((m): m is Miembro => Boolean(m))
      .filter((m) => m.funcion === "MIEMBRO" && m.condicion === "PRINCIPAL")
      .map((m) => m.id),
  );
  const presentesConVoto = asistentesSeleccionados.filter((id) => {
    const miembro = estado.miembros.find((m) => m.id === id);
    if (!miembro) return false;
    if (miembro.funcion !== "MIEMBRO") return false;
    if (miembro.condicion === "PRINCIPAL") return true;
    return miembro.suplente_de_id !== null && !principalesMarcados.has(miembro.suplente_de_id);
  }).length;
  const hayQuorum = presentesConVoto >= quorumRequerido;
  const progresoCompleto =
    estado.progreso.resultados_requeridos > 0 &&
    estado.progreso.resultados_registrados >= estado.progreso.resultados_requeridos;

  const criteriosPorAspecto = (aspecto: Criterio["aspecto"]) =>
    estado.matriz?.criterios
      .filter((c) => c.aspecto === aspecto)
      .sort((a, b) => a.orden - b.orden) ?? [];

  return (
    <section aria-labelledby="sec-evaluacion" className="mt-6">
      <h2 id="sec-evaluacion" className="text-lg font-semibold text-text-900">
        Apertura y evaluación
      </h2>

      <h3 className="mt-4 text-base font-semibold text-text-900">Estado</h3>
      <div className="mt-2 rounded-lg border border-border-subtle bg-white p-4">
        <dl className="grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2">
          <div className="min-w-0 break-words">
            <dt className="text-xs font-medium text-text-600">Recepción de ofertas</dt>
            <dd className="text-sm text-text-900">
              {estado.recepcion_concluida_en
                ? `Concluida · ${formatearInstante(estado.recepcion_concluida_en)}`
                : "Pendiente"}
            </dd>
          </div>
          <div className="min-w-0 break-words">
            <dt className="text-xs font-medium text-text-600">Matriz</dt>
            <dd className="text-sm text-text-900">
              {estado.matriz
                ? `${estado.matriz.estado === "BLOQUEADA" ? "Bloqueada" : "Borrador"} · versión ${estado.matriz.version}${estado.matriz.transcripcion ? " · Transcripción del pliego" : ""}`
                : "Sin registrar"}
            </dd>
          </div>
          <div className="min-w-0 break-words">
            <dt className="text-xs font-medium text-text-600">Apertura</dt>
            <dd className="text-sm text-text-900">
              {estado.aperturas.length > 0
                ? `Realizada: ${estado.aperturas.length} de ${estado.ofertas.length} ofertas abiertas`
                : "Pendiente"}
            </dd>
          </div>
          <div className="min-w-0 break-words">
            <dt className="text-xs font-medium text-text-600">Evaluación</dt>
            <dd className="text-sm text-text-900">
              {estado.evaluacion_concluida_en
                ? `Concluida · ${formatearInstante(estado.evaluacion_concluida_en)}`
                : estado.progreso.resultados_requeridos > 0
                  ? `En progreso: ${estado.progreso.resultados_registrados} de ${estado.progreso.resultados_requeridos} resultados`
                  : "Pendiente"}
            </dd>
          </div>
          <div className="min-w-0 break-words sm:col-span-2">
            <dt className="text-xs font-medium text-text-600">Comisión</dt>
            <dd className="text-sm text-text-900">
              {estado.miembros.length === 0 ? (
                "Sin comisión vinculada"
              ) : (
                <ul className="mt-1 space-y-1">
                  {estado.miembros.map((m) => (
                    <li key={m.id}>
                      {m.oficial} · {m.funcion === "MIEMBRO" ? "Miembro" : m.funcion === "SECRETARIO" ? "Secretario" : m.funcion} · {m.condicion === "PRINCIPAL" ? "Principal" : m.condicion === "SUPLENTE" ? "Suplente" : m.condicion}
                    </li>
                  ))}
                </ul>
              )}
            </dd>
          </div>
          <div className="min-w-0 break-words sm:col-span-2">
            <dt className="text-xs font-medium text-text-600">Siguiente acción</dt>
            <dd className="text-sm font-semibold text-text-900">{estado.siguiente_accion}</dd>
          </div>
        </dl>
      </div>

      <h3 className="mt-4 text-base font-semibold text-text-900">Ofertas</h3>
      {estado.ofertas.length === 0 ? (
        <EmptyState title="Sin ofertas" description="No hay ofertas registradas en este expediente." />
      ) : (
        <ul className="mt-2 space-y-2">
          {estado.ofertas.map((oferta) => {
            const recepcion = recepcionPorId.get(oferta.id);
            const integridadTexto =
              recepcion?.integridad === "VERIFICADA"
                ? "Integridad verificada"
                : recepcion?.integridad === "ALTERADA"
                  ? "Integridad no verificada"
                  : "Sobre físico sin archivo";
            return (
              <li key={oferta.id} className="rounded-lg border border-border-subtle bg-white p-4">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0 break-words">
                    <h4 className="text-sm font-semibold text-text-900">{oferta.oferta}</h4>
                    <p className="mt-1 text-sm text-text-600">{oferta.oferente}</p>
                  </div>
                  <span className="text-sm text-text-900">
                    {oferta.situacion === "ABIERTA" ? "Abierta" : "Sellada hasta la apertura"}
                  </span>
                </div>
                <dl className="mt-3 grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2">
                  <div className="min-w-0 break-words">
                    <dt className="text-xs font-medium text-text-600">Canal</dt>
                    <dd className="text-sm text-text-900">{recepcion?.canal_etiqueta ?? "—"}</dd>
                  </div>
                  <div className="min-w-0 break-words">
                    <dt className="text-xs font-medium text-text-600">Fecha de recepción</dt>
                    <dd className="text-sm text-text-900">
                      {recepcion ? formatearInstante(recepcion.recibida_en) : "—"}
                    </dd>
                  </div>
                  <div className="min-w-0 break-words">
                    <dt className="text-xs font-medium text-text-600">Integridad</dt>
                    <dd className="text-sm text-text-900">{integridadTexto}</dd>
                  </div>
                  <div className="min-w-0 break-words">
                    <dt className="text-xs font-medium text-text-600">Confidencialidad</dt>
                    <dd className="text-sm text-text-900">
                      {recepcion?.confidencialidad_etiqueta ?? "—"}
                    </dd>
                  </div>
                </dl>
                {oferta.situacion === "ABIERTA" ? (
                  <div className="mt-3">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => void cargarDocumentosOferta(oferta.id)}
                      disabled={cargandoDocumentosOferta === oferta.id}
                      aria-label={`Ver documentos de ${oferta.oferta}`}
                    >
                      {cargandoDocumentosOferta === oferta.id
                        ? "Cargando…"
                        : `Ver documentos de ${oferta.oferta}`}
                    </Button>
                    {documentosOferta[oferta.id] ? (
                      <ul className="mt-2 space-y-1">
                        {documentosOferta[oferta.id].map((doc, idx) => (
                          <li key={`${doc.documento_id ?? "sellado"}-${idx}`} className="text-sm text-text-900">
                            {doc.documento_id ? (
                              <Link to={`/documentos/${doc.documento_id}`} className="text-brand-700 underline">
                                {doc.titulo ?? doc.documento_id}
                              </Link>
                            ) : (
                              "Contenido sellado hasta la apertura"
                            )}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}

      <h3 className="mt-4 text-base font-semibold text-text-900">Matriz de evaluación</h3>
      {!estado.matriz ? (
        puedeCriterios && detalle.status === "ABIERTO" ? (
          <div className="mt-2 rounded-lg border border-border-subtle bg-white p-4">
            <FormField label="Pliego de condiciones" htmlFor="matriz-pliego" required error={fieldErrorsMatriz.pliego_documento_id?.[0]}>
              <select
                id="matriz-pliego"
                className={SELECT_CLASS}
                value={pliegoId}
                onChange={(e) => setPliegoId(e.target.value)}
              >
                <option value="">Seleccione…</option>
                {documentos.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.title}
                  </option>
                ))}
              </select>
            </FormField>
            {errorMatriz ? (
              <p role="alert" className="mt-2 text-sm text-red-700">
                {errorMatriz}
              </p>
            ) : null}
            <div className="mt-3 flex flex-wrap gap-2">
              <Button variant="primary" onClick={() => void registrarMatriz()} disabled={enviandoMatriz}>
                {enviandoMatriz ? "Registrando…" : "Registrar matriz"}
              </Button>
            </div>
          </div>
        ) : (
          <p className="mt-2 text-sm text-text-600">Sin registrar</p>
        )
      ) : (
        <div className="mt-2 space-y-3">
          <div className="rounded-lg border border-border-subtle bg-white p-4">
            <dl className="grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="min-w-0 break-words">
                <dt className="text-xs font-medium text-text-600">Pliego</dt>
                <dd className="text-sm text-text-900">
                  <Link to={`/documentos/${estado.matriz.pliego.documento_id}`} className="text-brand-700 underline">
                    {estado.matriz.pliego.documento_id}
                  </Link>{" "}
                  · {huellaAbreviada(estado.matriz.pliego.huella)}
                </dd>
              </div>
              <div className="min-w-0 break-words">
                <dt className="text-xs font-medium text-text-600">Estado</dt>
                <dd className="text-sm text-text-900">
                  {estado.matriz.estado === "BLOQUEADA" ? "Bloqueada" : "Borrador"} · versión{" "}
                  {estado.matriz.version}
                </dd>
              </div>
            </dl>
          </div>
          {(["TECNICO", "ECONOMICO", "LEGAL"] as const).map((aspecto) => {
            const criterios = criteriosPorAspecto(aspecto);
            const titulo = aspecto === "TECNICO" ? "Técnico" : aspecto === "ECONOMICO" ? "Económico" : "Legal";
            return (
              <div key={aspecto}>
                <h4 className="text-sm font-semibold text-text-900">{titulo}</h4>
                {criterios.length === 0 ? (
                  <p className="mt-1 text-sm text-text-600">Sin criterios</p>
                ) : (
                  <ul className="mt-2 space-y-2">
                    {criterios.map((criterio) => (
                      <li key={criterio.id}>
                        <TarjetaCriterio
                          criterio={criterio}
                          puedeQuitar={estado.matriz?.estado === "BORRADOR" && puedeCriterios}
                          onQuitar={() => void quitarCriterio(criterio.id)}
                        />
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            );
          })}
          {estado.matriz.estado === "BORRADOR" && puedeCriterios ? (
            <>
              <FormularioCriterio
                onGuardar={(criterio) => void guardarCriterio(criterio)}
                enviando={enviandoCriterio}
                error={errorCriterio}
              />
              {Object.keys(fieldErrorsCriterio).length > 0 ? (
                <p role="alert" className="mt-2 text-sm text-red-700">
                  {Object.values(fieldErrorsCriterio).flat().join(" ")}
                </p>
              ) : null}
              <div className="rounded-lg border border-border-subtle bg-white p-4">
                {confirmarBloqueo ? (
                  <>
                    <p className="text-sm text-text-900">
                      Al bloquear, los criterios quedan fijos: no se podrán alterar después de
                      recibidas las ofertas.
                    </p>
                    {errorBloqueo ? (
                      <p role="alert" className="mt-2 text-sm text-red-700">
                        {errorBloqueo}
                      </p>
                    ) : null}
                    <div className="mt-3 flex flex-wrap gap-2">
                      <Button variant="primary" onClick={() => void bloquearMatriz()} disabled={enviandoBloqueo}>
                        {enviandoBloqueo ? "Bloqueando…" : "Confirmar bloqueo"}
                      </Button>
                      <Button variant="ghost" onClick={() => setConfirmarBloqueo(false)}>
                        Cancelar
                      </Button>
                    </div>
                  </>
                ) : (
                  <Button variant="primary" onClick={() => setConfirmarBloqueo(true)}>
                    Bloquear matriz
                  </Button>
                )}
              </div>
            </>
          ) : (
            <p className="text-sm text-text-600">Matriz bloqueada: criterios fijos para la evaluación</p>
          )}
        </div>
      )}

      <h3
        id="sec-evaluacion-apertura"
        className="mt-4 text-base font-semibold text-text-900"
        ref={encabezadoAperturaRef}
        tabIndex={-1}
      >
        Apertura de ofertas
      </h3>
      {estado.aperturas.length === 0 ? (
        <p className="mt-2 text-sm text-text-600">Sin aperturas registradas</p>
      ) : (
        <ul className="mt-2 space-y-2">
          {estado.aperturas.map((apertura) => (
            <li key={apertura.id} className="rounded-lg border border-border-subtle bg-white p-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <h4 className="text-sm font-semibold text-text-900">{apertura.referencia}</h4>
                <span className="text-sm text-text-600">{formatearInstante(apertura.abierta_en)}</span>
              </div>
              <dl className="mt-3 grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2">
                <div className="min-w-0 break-words">
                  <dt className="text-xs font-medium text-text-600">Registrada por</dt>
                  <dd className="text-sm text-text-900">{apertura.abierta_por ?? "—"}</dd>
                </div>
                <div className="min-w-0 break-words">
                  <dt className="text-xs font-medium text-text-600">Acta</dt>
                  <dd className="text-sm text-text-900">
                    <Link to={`/documentos/${apertura.acta.documento_id}`} className="text-brand-700 underline">
                      {apertura.acta.titulo}
                    </Link>{" "}
                    · {huellaAbreviada(apertura.acta.huella)}
                  </dd>
                </div>
                <div className="min-w-0 break-words">
                  <dt className="text-xs font-medium text-text-600">Quórum</dt>
                  <dd className="text-sm text-text-900">
                    {apertura.asistentes_con_voto} de {apertura.miembros_con_voto} miembros con voto
                    (requerido {apertura.quorum_requerido})
                  </dd>
                </div>
                <div className="min-w-0 break-words">
                  <dt className="text-xs font-medium text-text-600">Asistentes</dt>
                  <dd className="text-sm text-text-900">
                    <ul className="mt-1 space-y-1">
                      {apertura.asistentes.map((asistente) => (
                        <li key={asistente.member_id}>
                          {asistente.oficial} · {asistente.funcion} · {asistente.condicion}
                        </li>
                      ))}
                    </ul>
                  </dd>
                </div>
                <div className="min-w-0 break-words">
                  <dt className="text-xs font-medium text-text-600">Ofertas abiertas</dt>
                  <dd className="text-sm text-text-900">
                    <ul className="mt-1 space-y-1">
                      {apertura.ofertas.map((oferta) => (
                        <li key={oferta.id}>{oferta.oferta}</li>
                      ))}
                    </ul>
                  </dd>
                </div>
              </dl>
              {apertura.observaciones ? (
                <p className="mt-2 min-w-0 break-words text-sm text-text-600">{apertura.observaciones}</p>
              ) : null}
            </li>
          ))}
        </ul>
      )}
      {puedeAbrir &&
      ofertasPendientes.length > 0 &&
      estado.recepcion_concluida_en &&
      estado.matriz?.estado === "BLOQUEADA" &&
      detalle.status === "ABIERTO" ? (
        <div className="mt-3 rounded-lg border border-border-subtle bg-white p-4">
          {mostrarApertura ? (
            <>
              <fieldset>
                <legend className="text-sm font-medium text-text-900">Ofertas a abrir</legend>
                <div className="mt-2 space-y-2">
                  {ofertasPendientes.map((oferta) => (
                    <label key={oferta.id} className="flex items-center gap-2 text-sm text-text-900">
                      <input
                        type="checkbox"
                        checked={ofertasSeleccionadas.includes(oferta.id)}
                        onChange={(e) =>
                          setOfertasSeleccionadas((prev) =>
                            e.target.checked
                              ? [...prev, oferta.id]
                              : prev.filter((id) => id !== oferta.id),
                          )
                        }
                      />
                      {oferta.oferta} · {oferta.oferente}
                    </label>
                  ))}
                </div>
              </fieldset>
              <fieldset className="mt-4">
                <legend className="text-sm font-medium text-text-900">Asistentes</legend>
                <div className="mt-2 space-y-2">
                  {estado.miembros.map((miembro) => (
                    <label key={miembro.id} className="flex items-center gap-2 text-sm text-text-900">
                      <input
                        type="checkbox"
                        checked={asistentesSeleccionados.includes(miembro.id)}
                        onChange={(e) =>
                          setAsistentesSeleccionados((prev) =>
                            e.target.checked
                              ? [...prev, miembro.id]
                              : prev.filter((id) => id !== miembro.id),
                          )
                        }
                      />
                      {miembro.oficial} · {miembro.funcion === "MIEMBRO" ? "Miembro" : miembro.funcion === "SECRETARIO" ? "Secretario" : miembro.funcion} · {miembro.condicion === "PRINCIPAL" ? "Principal" : miembro.condicion === "SUPLENTE" ? "Suplente" : miembro.condicion}
                    </label>
                  ))}
                </div>
              </fieldset>
              <p role="status" className="mt-3 text-sm text-text-900">
                Presentes con voto: {presentesConVoto} de {miembrosConVoto.length} · Quórum requerido:{" "}
                {quorumRequerido} · {hayQuorum ? "Hay quórum" : "Sin quórum"}
              </p>
              <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
                <FormField label="Acta de apertura" htmlFor="apertura-acta" required error={fieldErrorsApertura.acta_documento_id?.[0]}>
                  <select
                    id="apertura-acta"
                    className={SELECT_CLASS}
                    value={actaId}
                    onChange={(e) => setActaId(e.target.value)}
                  >
                    <option value="">Seleccione…</option>
                    {documentos
                      .filter((d) => !d.link.is_frozen)
                      .map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.title}
                        </option>
                      ))}
                  </select>
                </FormField>
                <FormField label="Fecha y hora" htmlFor="apertura-fecha" required error={fieldErrorsApertura.abierta_en?.[0]}>
                  <TextInput
                    id="apertura-fecha"
                    type="datetime-local"
                    value={fechaApertura}
                    onChange={(e) => setFechaApertura(e.target.value)}
                  />
                </FormField>
                <FormField label="Observaciones" htmlFor="apertura-observaciones">
                  <TextInput
                    id="apertura-observaciones"
                    value={observacionesApertura}
                    onChange={(e) => setObservacionesApertura(e.target.value)}
                  />
                </FormField>
              </div>
              {errorApertura ? (
                <p role="alert" className="mt-2 text-sm text-red-700">
                  {errorApertura}
                </p>
              ) : null}
              {Object.keys(fieldErrorsApertura).some((k) =>
                ["asistentes", "comision", "criterios", "oferta_ids", "body", "miembro_id"].includes(k),
              ) ? (
                <p role="alert" className="mt-2 text-sm text-red-700">
                  {Object.entries(fieldErrorsApertura)
                    .filter(([k]) => ["asistentes", "comision", "criterios", "oferta_ids", "body", "miembro_id"].includes(k))
                    .flatMap(([, v]) => v)
                    .join(" ")}
                </p>
              ) : null}
              {confirmarApertura ? (
                <div className="mt-3">
                  <p className="text-sm text-text-900">
                    Esta acción abrirá las ofertas seleccionadas y liberará su contenido para los
                    usuarios autorizados.
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button variant="primary" onClick={() => void abrirOfertas()} disabled={enviandoApertura}>
                      {enviandoApertura ? "Abriendo…" : "Confirmar apertura"}
                    </Button>
                    <Button variant="ghost" onClick={() => setConfirmarApertura(false)}>
                      Cancelar
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button variant="primary" onClick={() => setConfirmarApertura(true)}>
                    Abrir ofertas
                  </Button>
                  <Button variant="ghost" onClick={() => setMostrarApertura(false)}>
                    Cancelar
                  </Button>
                </div>
              )}
            </>
          ) : (
            <Button variant="primary" onClick={() => setMostrarApertura(true)}>
              Registrar apertura
            </Button>
          )}
          {exitoApertura ? (
            <p role="status" className="mt-2 text-sm text-green-700">
              {exitoApertura}
            </p>
          ) : null}
        </div>
      ) : null}

      <h3 className="mt-4 text-base font-semibold text-text-900">Evaluación</h3>
      {ofertasAbiertas.length === 0 ? (
        <p className="mt-2 text-sm text-text-600">No hay ofertas abiertas para evaluar.</p>
      ) : (
        <div className="mt-2 space-y-4">
          <p className="text-sm text-text-600">
            Aportes de los evaluadores: cada miembro registra su valoración. Resultado de la
            Comisión: valoración consolidada que decide la Comisión; no se promedia.
          </p>
          {ofertasAbiertas.map((oferta) => {
            const items = estado.resultados_por_oferta.filter((r) => r.oferta_id === oferta.id);
            return (
              <div key={oferta.id}>
                <h4 className="text-sm font-semibold text-text-900">
                  Oferta {oferta.oferta} · {oferta.oferente}
                </h4>
                <div className="mt-2 space-y-2">
                  {items.map((item) => (
                    <TarjetaEvaluacionCriterio
                      key={item.criterio_id}
                      item={item}
                      miembros={estado.miembros}
                      documentos={documentos}
                      puedeEvaluar={puedeEvaluar}
                      evaluacionConcluida={Boolean(estado.evaluacion_concluida_en)}
                      onRegistrar={(tipo, cuerpo) =>
                        registrarEvaluacion(tipo, oferta.id, item.criterio_id, cuerpo)
                      }
                    />
                  ))}
                </div>
              </div>
            );
          })}
          <p className="text-sm text-text-900">
            {estado.progreso.resultados_registrados} de {estado.progreso.resultados_requeridos}{" "}
            resultados de la Comisión registrados
          </p>
          {estado.evaluacion_concluida_en ? (
            <p className="text-sm text-text-900">
              Evaluación concluida · {formatearInstante(estado.evaluacion_concluida_en)}. Pendiente de
              recomendación y adjudicación.
            </p>
          ) : (
            puedeEvaluar &&
            progresoCompleto && (
              <div className="rounded-lg border border-border-subtle bg-white p-4">
                {confirmarConclusion ? (
                  <>
                    <p className="text-sm text-text-900">
                      Concluir cierra la evaluación de las ofertas. La recomendación y la
                      adjudicación son un paso posterior.
                    </p>
                    {errorConclusion ? (
                      <p role="alert" className="mt-2 text-sm text-red-700">
                        {errorConclusion}
                      </p>
                    ) : null}
                    <div className="mt-3 flex flex-wrap gap-2">
                      <Button
                        variant="primary"
                        onClick={() => void concluirEvaluacion()}
                        disabled={enviandoConclusion}
                      >
                        {enviandoConclusion ? "Concluyendo…" : "Confirmar conclusión"}
                      </Button>
                      <Button variant="ghost" onClick={() => setConfirmarConclusion(false)}>
                        Cancelar
                      </Button>
                    </div>
                  </>
                ) : (
                  <Button variant="primary" onClick={() => setConfirmarConclusion(true)}>
                    Concluir evaluación
                  </Button>
                )}
              </div>
            )
          )}
        </div>
      )}
    </section>
  );
}
