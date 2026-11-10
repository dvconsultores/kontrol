import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { Link } from "react-router";
import { apiFetch, ApiError } from "@/api/client";
import { descargarArchivo } from "@/api/descargas";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { formatearFechaDeNegocio, formatearInstante } from "@/lib/fecha-de-negocio";
import { CONSULTA_EXPEDIENTES, type ExpedienteDetalle } from "../api";

type CatalogoItem = { codigo: string; etiqueta: string };
type Miembro = {
  id: string;
  oficial: string;
  funcion: string;
  condicion: string;
  cuenta_voto: boolean;
};
type Oferta = {
  id: string;
  oferta: string;
  oferente: string;
  documento: string;
  rechazada: boolean;
};
type Firmante = {
  member_id: string;
  oficial: string;
  funcion: string;
  condicion: string;
  cuenta_voto: boolean;
};
type Opcion = {
  posicion: number;
  offer_id: string;
  oferta: string;
  oferente: string;
};
type Rechazo = {
  offer_id: string;
  oferta: string;
  oferente: string;
  causal: string;
  causal_etiqueta: string;
  motivacion: string;
};
type Recomendacion = {
  id: string;
  referencia: string;
  estado: string;
  estado_etiqueta: string;
  resultado_recomendado: string;
  resultado_etiqueta: string;
  causal_desierta: string | null;
  causal_etiqueta: string | null;
  motivacion: string;
  examen_legal: string;
  examen_financiero: string;
  examen_tecnico: string;
  resultado_matriz: string;
  medidas_promocion: string | null;
  firmantes: Firmante[];
  opciones: Opcion[];
  rechazos: Rechazo[];
  matriz_version: number;
  evaluacion_concluida_en: string | null;
  emitida_en: string | null;
  emitida_por: string;
  sustituye: string | null;
  motivo_sustitucion: string | null;
  sustituida_en: string | null;
  informe: { nombre: string; sha256: string; tamano: number };
};
type ActoElegible = {
  id: string;
  tipo: string;
  numero: string;
  fecha: string;
  asunto: string;
};
type ActoDecision = {
  id: string | null;
  tipo: string | null;
  numero: string | null;
  fecha: string | null;
  status: string | null;
};
type Decision = {
  id: string;
  referencia: string;
  resultado: string;
  resultado_etiqueta: string;
  estado: string;
  estado_etiqueta: string;
  recomendacion: string | null;
  oferta: string | null;
  oferente: string | null;
  posicion: number | null;
  causal: string | null;
  causal_etiqueta: string | null;
  anula: string | null;
  afectada_por: string | null;
  acto: ActoDecision | null;
  cargo: string | null;
  motivacion: string;
  decidida_en: string | null;
  decidida_por: string | null;
};
type Notificacion = {
  offer_id: string;
  oferta: string;
  oferente: string;
  documento: string;
  estado: string;
  estado_etiqueta: string;
  fecha_notificacion: string | null;
  medio: string | null;
};
type EstadoDecision = {
  expediente: { id: string; numero: string; objeto: string; version: number };
  evaluacion_concluida_en: string | null;
  comision: { id: string; nombre: string } | null;
  miembros: Miembro[];
  ofertas: Oferta[];
  recomendacion_vigente: Recomendacion | null;
  recomendaciones: Recomendacion[];
  siguiente_accion: string;
  catalogos: {
    resultados_recomendacion: CatalogoItem[];
    causales_desierta: CatalogoItem[];
    causales_rechazo: CatalogoItem[];
    resultados_decision: CatalogoItem[];
    causales_nulidad: CatalogoItem[];
  };
  decision_vigente: Decision | null;
  decisiones: Decision[];
  resultado: string | null;
  actos_elegibles: ActoElegible[];
  notificaciones: Notificacion[];
  acto_eficaz: boolean;
};

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
    case "GOV_PROCUREMENT_FILE_STALE":
      return "Los datos cambiaron; se actualizaron, revise e intente de nuevo";
    case "GOV_DECISION_INVALID_ACT":
      return "El acto seleccionado no es válido para decidir";
    case "GOV_DECISION_ACT_IN_USE":
      return "El acto ya fue utilizado en otra decisión";
    case "GOV_DECISION_OPTION_ORDER":
      return "La opción seleccionada no respeta el orden de la recomendación";
    case "GOV_DECISION_ALREADY_FINAL":
      return "El procedimiento ya tiene una decisión vigente";
    case "GOV_DECISION_COMMISSION_SIGNATORY":
      return "Quien firmó la recomendación no puede decidirla";
    case "GOV_DECISION_RECOMMENDATION_REQUIRED":
      return "Se requiere una recomendación vigente para decidir";
    case "GOV_RECOMMENDATION_QUORUM":
      return "No se alcanza el quorum de firmantes con voto";
    case "GOV_RECOMMENDATION_ALREADY_ISSUED":
      return "Ya existe una recomendación emitida";
    case "GOV_RECOMMENDATION_LOCKED_BY_DECISION":
      return "La recomendación está bloqueada por una decisión";
    case "GOV_DECISION_IDENTITY_REQUIRED":
      return "Su cuenta debe estar vinculada a un funcionario institucional";
    case "GOV_DECISION_NOT_COMMISSION_MEMBER":
      return "Solo un miembro de la Comisión puede emitir la recomendación";
    case "GOV_SOD_CONFLICT":
      return "Conflicto de separación de funciones";
    case "GOV_DECISION_NOTHING_TO_ANNUL":
      return "No hay decisión vigente que anular";
    default:
      return error.message;
  }
}

export function SeccionDecision({
  detalle,
  activeCompanyId,
}: {
  detalle: ExpedienteDetalle;
  activeCompanyId: string | null;
}) {
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();
  const encabezadoRecomendacionRef = useRef<HTMLHeadingElement | null>(null);

  const puedeVer = tiene("gobierno_decision:view", "empresa");
  const puedeRecomendar = tiene("gobierno_decision:recommend", "empresa");
  const puedeDecidir = tiene("gobierno_decision:decide", "empresa");

  const decisionQuery = useQuery({
    queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId, "decision", detalle.id],
    queryFn: () =>
      apiFetch<EstadoDecision>(`/gobierno/contrataciones/expedientes/${detalle.id}/decision`),
    enabled: puedeVer && Boolean(activeCompanyId),
  });

  const [resultadoRecomendado, setResultadoRecomendado] = useState("");
  const [causalDesierta, setCausalDesierta] = useState("");
  const [motivacion, setMotivacion] = useState("");
  const [examenLegal, setExamenLegal] = useState("");
  const [examenFinanciero, setExamenFinanciero] = useState("");
  const [examenTecnico, setExamenTecnico] = useState("");
  const [resultadoMatriz, setResultadoMatriz] = useState("");
  const [medidasPromocion, setMedidasPromocion] = useState("");
  const [opcionesSeleccionadas, setOpcionesSeleccionadas] = useState<string[]>([]);
  const [rechazosSeleccionados, setRechazosSeleccionados] = useState<
    Record<string, { causal: string; motivacion: string }>
  >({});
  const [firmantesSeleccionados, setFirmantesSeleccionados] = useState<string[]>([]);
  const [motivoSustitucion, setMotivoSustitucion] = useState("");
  const [confirmarRecomendacion, setConfirmarRecomendacion] = useState(false);
  const [enviandoRecomendacion, setEnviandoRecomendacion] = useState(false);
  const [errorRecomendacion, setErrorRecomendacion] = useState<string | null>(null);
  const [fieldErrorsRecomendacion, setFieldErrorsRecomendacion] = useState<Record<string, string[]>>({});

  const [resultadoDecision, setResultadoDecision] = useState("");
  const [actoId, setActoId] = useState("");
  const [formularioSustitucionAbierto, setFormularioSustitucionAbierto] = useState(false);
  const [causalDesiertaDecision, setCausalDesiertaDecision] = useState("");
  const [causalNulidad, setCausalNulidad] = useState("");
  const [anulaId, setAnulaId] = useState("");
  const [motivacionDecision, setMotivacionDecision] = useState("");
  const [confirmarDecision, setConfirmarDecision] = useState(false);
  const [enviandoDecision, setEnviandoDecision] = useState(false);
  const [errorDecision, setErrorDecision] = useState<string | null>(null);
  const [fieldErrorsDecision, setFieldErrorsDecision] = useState<Record<string, string[]>>({});

  function invalidar() {
    void queryClient.invalidateQueries({ queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId] });
  }

  async function emitirRecomendacion() {
    setEnviandoRecomendacion(true);
    setErrorRecomendacion(null);
    setFieldErrorsRecomendacion({});
    try {
      const cuerpo: Record<string, unknown> = {
        resultado_recomendado: resultadoRecomendado,
        causal_desierta: resultadoRecomendado === "DECLARAR_DESIERTA" ? causalDesierta : null,
        motivacion,
        examen_legal: examenLegal,
        examen_financiero: examenFinanciero,
        examen_tecnico: examenTecnico,
        resultado_matriz: resultadoMatriz,
        medidas_promocion: medidasPromocion || null,
        firmante_ids: firmantesSeleccionados,
        opciones: opcionesSeleccionadas.map((offerId, index) => ({
          posicion: index + 1,
          offer_id: offerId,
        })),
        rechazos: Object.entries(rechazosSeleccionados).map(([offerId, r]) => ({
          offer_id: offerId,
          causal: r.causal,
          motivacion: r.motivacion,
        })),
      };
      if (estado?.recomendacion_vigente) {
        cuerpo.sustituye_id = estado.recomendacion_vigente.id;
        cuerpo.motivo_sustitucion = motivoSustitucion;
      }
      await apiFetch(`/gobierno/contrataciones/expedientes/${detalle.id}/decision/recomendaciones`, {
        method: "POST",
        body: cuerpo,
        ifMatch: String(detalle.version),
      });
      invalidar();
      notify({ type: "success", title: "Recomendación emitida" });
      setConfirmarRecomendacion(false);
      setResultadoRecomendado("");
      setCausalDesierta("");
      setMotivacion("");
      setExamenLegal("");
      setExamenFinanciero("");
      setExamenTecnico("");
      setResultadoMatriz("");
      setMedidasPromocion("");
      setOpcionesSeleccionadas([]);
      setRechazosSeleccionados({});
      setFirmantesSeleccionados([]);
      setMotivoSustitucion("");
      window.setTimeout(() => encabezadoRecomendacionRef.current?.focus(), 0);
    } catch (e) {
      setErrorRecomendacion(textoErrorPorCodigo(e));
      setFieldErrorsRecomendacion(erroresDeCampos(e));
      if (e instanceof ApiError && e.code === "GOV_PROCUREMENT_FILE_STALE") {
        invalidar();
      }
    } finally {
      setEnviandoRecomendacion(false);
    }
  }

  async function registrarDecision() {
    setEnviandoDecision(true);
    setErrorDecision(null);
    setFieldErrorsDecision({});
    try {
      const cuerpo: Record<string, unknown> = {
        resultado: resultadoDecision,
        acto_id: actoId,
        motivacion: motivacionDecision,
      };
      if (resultadoDecision === "ADJUDICADA") {
        cuerpo.recomendacion_id = estado?.recomendacion_vigente?.id;
        cuerpo.oferta_id = opcionPropuesta?.offer_id ?? "";
      } else if (resultadoDecision === "DESIERTA") {
        cuerpo.recomendacion_id = estado?.recomendacion_vigente?.id;
        cuerpo.causal_desierta = causalDesiertaDecision;
      } else if (resultadoDecision === "NULIDAD") {
        cuerpo.causal_nulidad = causalNulidad;
        cuerpo.anula_id = anulaId;
      }
      await apiFetch(`/gobierno/contrataciones/expedientes/${detalle.id}/decision/decisiones`, {
        method: "POST",
        body: cuerpo,
        ifMatch: String(detalle.version),
      });
      invalidar();
      notify({ type: "success", title: "Decisión registrada" });
      setConfirmarDecision(false);
      setResultadoDecision("");
      setActoId("");
      setFormularioSustitucionAbierto(false);
      setCausalDesiertaDecision("");
      setCausalNulidad("");
      setAnulaId("");
      setMotivacionDecision("");
    } catch (e) {
      setErrorDecision(textoErrorPorCodigo(e));
      setFieldErrorsDecision(erroresDeCampos(e));
      if (e instanceof ApiError && e.code === "GOV_PROCUREMENT_FILE_STALE") {
        invalidar();
      }
    } finally {
      setEnviandoDecision(false);
    }
  }

  if (!puedeVer) return null;

  if (decisionQuery.isLoading) {
    return (
      <section aria-labelledby="sec-decision" className="mt-6">
        <h2 id="sec-decision" className="text-lg font-semibold text-text-900">
          Recomendación y decisión
        </h2>
        <LoadingState />
      </section>
    );
  }

  if (decisionQuery.isError || !decisionQuery.data) {
    return (
      <section aria-labelledby="sec-decision" className="mt-6">
        <h2 id="sec-decision" className="text-lg font-semibold text-text-900">
          Recomendación y decisión
        </h2>
        <p role="alert" className="mt-2 text-sm text-red-700">
          {mensajeError(decisionQuery.error)}
        </p>
      </section>
    );
  }

  const estado = decisionQuery.data;
  const recomendacionVigente = estado.recomendacion_vigente;
  const decisionVigente = estado.decision_vigente;
  const ofertasNoRechazadas = estado.ofertas.filter((o) => !o.rechazada);
  const miembrosConVoto = estado.miembros.filter((m) => m.cuenta_voto);
  const quorumRequerido = Math.floor(miembrosConVoto.length / 2) + 1;
  const firmantesConVoto = firmantesSeleccionados.filter((id) =>
    miembrosConVoto.some((m) => m.id === id),
  ).length;


  const decisionesSustituidas = estado.recomendaciones.filter((r) => r.estado === "SUSTITUIDA");

  const ultimaAdjudicacionAnulada = [...estado.decisiones]
    .reverse()
    .find(
      (d) =>
        d.resultado === "ADJUDICADA" &&
        d.estado === "ANULADA" &&
        estado.decisiones.some(
          (n) =>
            n.resultado === "NULIDAD" &&
            n.anula === d.referencia &&
            n.causal === "INFORMACION_FALSA",
        ),
    );

  const opcionPropuesta = (() => {
    if (!recomendacionVigente || recomendacionVigente.opciones.length === 0) return null;
    if (ultimaAdjudicacionAnulada) {
      const siguiente = recomendacionVigente.opciones.find(
        (o) => o.posicion > (ultimaAdjudicacionAnulada.posicion ?? 0),
      );
      return siguiente ?? null;
    }
    return recomendacionVigente.opciones[0];
  })();

  const historial: { fecha: string | null; texto: string }[] = [];
  for (const r of estado.recomendaciones) {
    if (r.emitida_en) {
      historial.push({
        fecha: r.emitida_en,
        texto: `Recomendación ${r.referencia} emitida (${r.resultado_etiqueta})`,
      });
    }
    if (r.sustituida_en) {
      historial.push({
        fecha: r.sustituida_en,
        texto: `Recomendación ${r.referencia} sustituida${r.motivo_sustitucion ? `: ${r.motivo_sustitucion}` : ""}`,
      });
    }
  }
  for (const d of estado.decisiones) {
    if (d.decidida_en) {
      const acto = d.acto ? `${d.acto.tipo} ${d.acto.numero}` : "acto";
      if (d.resultado === "NULIDAD" && d.anula) {
        historial.push({
          fecha: d.decidida_en,
          texto: `Decisión ${d.referencia} anula ${d.anula} (${d.causal_etiqueta ?? d.causal ?? ""}) · ${acto}`,
        });
      } else if (d.afectada_por) {
        historial.push({
          fecha: d.decidida_en,
          texto: `Decisión ${d.referencia} (${d.resultado_etiqueta}) sustituida por ${d.afectada_por} · ${acto}`,
        });
      } else {
        historial.push({
          fecha: d.decidida_en,
          texto: `Decisión ${d.referencia} (${d.resultado_etiqueta}) · ${acto}`,
        });
      }
    }
  }
  historial.sort((a, b) => (b.fecha ?? "").localeCompare(a.fecha ?? ""));

  return (
    <section aria-labelledby="sec-decision" className="mt-6">
      <h2 id="sec-decision" className="text-lg font-semibold text-text-900">
        Recomendación y decisión
      </h2>

      <h3 className="mt-4 text-base font-semibold text-text-900">Estado</h3>
      <div className="mt-2 rounded-lg border border-border-subtle bg-white p-4">
        <dl className="grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2">
          <div className="min-w-0 break-words">
            <dt className="text-xs font-medium text-text-600">Evaluación</dt>
            <dd className="text-sm text-text-900">
              {estado.evaluacion_concluida_en
                ? `Concluida · ${formatearInstante(estado.evaluacion_concluida_en)}`
                : "Pendiente (PROC-07)"}
            </dd>
          </div>
          <div className="min-w-0 break-words">
            <dt className="text-xs font-medium text-text-600">Recomendación</dt>
            <dd className="text-sm text-text-900">
              {recomendacionVigente
                ? `${recomendacionVigente.referencia} · Emitida`
                : decisionesSustituidas.length > 0
                  ? "Sustituida"
                  : "Pendiente"}
            </dd>
          </div>
          <div className="min-w-0 break-words">
            <dt className="text-xs font-medium text-text-600">Decisión</dt>
            <dd className="text-sm text-text-900">
              {decisionVigente
                ? `${decisionVigente.referencia} · ${decisionVigente.resultado_etiqueta}`
                : "Pendiente"}
            </dd>
          </div>
          <div className="min-w-0 break-words">
            <dt className="text-xs font-medium text-text-600">Resultado</dt>
            <dd className="text-sm text-text-900">
              {decisionVigente?.resultado_etiqueta ?? "Sin resultado"}
            </dd>
          </div>
          <div className="min-w-0 break-words sm:col-span-2">
            <dt className="text-xs font-medium text-text-600">Siguiente acción</dt>
            <dd className="text-sm text-text-900">{estado.siguiente_accion}</dd>
          </div>
        </dl>
      </div>

      <h3 className="mt-4 text-base font-semibold text-text-900">Ofertas evaluadas</h3>
      <div className="mt-2 overflow-x-auto rounded-lg border border-border-subtle bg-white p-4">
        <table className="min-w-full text-sm text-text-900">
          <thead>
            <tr className="text-left text-xs text-text-600">
              <th className="py-1 pr-3 font-medium">Oferta</th>
              <th className="py-1 pr-3 font-medium">Oferente</th>
              <th className="py-1 pr-3 font-medium">Documento</th>
              <th className="py-1 font-medium">Estado</th>
            </tr>
          </thead>
          <tbody>
            {estado.ofertas.map((oferta) => (
              <tr key={oferta.id} className="border-t border-border-subtle">
                <td className="py-1 pr-3">{oferta.oferta}</td>
                <td className="py-1 pr-3">{oferta.oferente}</td>
                <td className="py-1 pr-3">{oferta.documento}</td>
                <td className="py-1">{oferta.rechazada ? "Rechazada" : ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {recomendacionVigente ? (
          <div className="mt-4 grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="min-w-0 break-words">
              <p className="text-xs font-medium text-text-600">Examen legal</p>
              <p className="text-sm text-text-900">{recomendacionVigente.examen_legal}</p>
            </div>
            <div className="min-w-0 break-words">
              <p className="text-xs font-medium text-text-600">Examen financiero</p>
              <p className="text-sm text-text-900">{recomendacionVigente.examen_financiero}</p>
            </div>
            <div className="min-w-0 break-words">
              <p className="text-xs font-medium text-text-600">Examen técnico</p>
              <p className="text-sm text-text-900">{recomendacionVigente.examen_tecnico}</p>
            </div>
            <div className="min-w-0 break-words">
              <p className="text-xs font-medium text-text-600">Resultado de la matriz</p>
              <p className="text-sm text-text-900">{recomendacionVigente.resultado_matriz}</p>
            </div>
          </div>
        ) : null}
      </div>

      <h3
        id="recomendacion-comision"
        ref={encabezadoRecomendacionRef}
        tabIndex={-1}
        className="mt-4 text-base font-semibold text-text-900 outline-none"
      >
        Recomendación de la Comisión
      </h3>

      {recomendacionVigente ? (
        <div className="mt-2 rounded-lg border border-border-subtle bg-white p-4">
          <dl className="grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="min-w-0 break-words">
              <dt className="text-xs font-medium text-text-600">Referencia</dt>
              <dd className="text-sm text-text-900">{recomendacionVigente.referencia}</dd>
            </div>
            <div className="min-w-0 break-words">
              <dt className="text-xs font-medium text-text-600">Resultado</dt>
              <dd className="text-sm text-text-900">{recomendacionVigente.resultado_etiqueta}</dd>
            </div>
            {recomendacionVigente.causal_etiqueta ? (
              <div className="min-w-0 break-words">
                <dt className="text-xs font-medium text-text-600">Causal</dt>
                <dd className="text-sm text-text-900">{recomendacionVigente.causal_etiqueta}</dd>
              </div>
            ) : null}
            <div className="min-w-0 break-words sm:col-span-2">
              <dt className="text-xs font-medium text-text-600">Motivación</dt>
              <dd className="text-sm text-text-900">{recomendacionVigente.motivacion}</dd>
            </div>
            <div className="min-w-0 break-words">
              <dt className="text-xs font-medium text-text-600">Examen legal</dt>
              <dd className="text-sm text-text-900">{recomendacionVigente.examen_legal}</dd>
            </div>
            <div className="min-w-0 break-words">
              <dt className="text-xs font-medium text-text-600">Examen financiero</dt>
              <dd className="text-sm text-text-900">{recomendacionVigente.examen_financiero}</dd>
            </div>
            <div className="min-w-0 break-words">
              <dt className="text-xs font-medium text-text-600">Examen técnico</dt>
              <dd className="text-sm text-text-900">{recomendacionVigente.examen_tecnico}</dd>
            </div>
            <div className="min-w-0 break-words">
              <dt className="text-xs font-medium text-text-600">Resultado de la matriz</dt>
              <dd className="text-sm text-text-900">{recomendacionVigente.resultado_matriz}</dd>
            </div>
            {recomendacionVigente.medidas_promocion ? (
              <div className="min-w-0 break-words sm:col-span-2">
                <dt className="text-xs font-medium text-text-600">Medidas de promoción</dt>
                <dd className="text-sm text-text-900">{recomendacionVigente.medidas_promocion}</dd>
              </div>
            ) : null}
          </dl>

          <h4 className="mt-4 text-sm font-semibold text-text-900">Opciones</h4>
          <ul className="mt-1 space-y-1 text-sm text-text-900">
            {recomendacionVigente.opciones.map((opcion) => (
              <li key={opcion.posicion}>
                Opción {opcion.posicion}: {opcion.oferta} · {opcion.oferente}
              </li>
            ))}
          </ul>

          {recomendacionVigente.rechazos.length > 0 ? (
            <>
              <h4 className="mt-4 text-sm font-semibold text-text-900">Rechazos</h4>
              <ul className="mt-1 space-y-1 text-sm text-text-900">
                {recomendacionVigente.rechazos.map((rechazo) => (
                  <li key={rechazo.offer_id}>
                    {rechazo.oferta} · {rechazo.oferente}: {rechazo.causal_etiqueta} —{" "}
                    {rechazo.motivacion}
                  </li>
                ))}
              </ul>
            </>
          ) : null}

          <h4 className="mt-4 text-sm font-semibold text-text-900">Firmantes</h4>
          <ul className="mt-1 space-y-1 text-sm text-text-900">
            {recomendacionVigente.firmantes.map((firmante) => (
              <li key={firmante.member_id}>
                {firmante.oficial} · {firmante.funcion} · {firmante.condicion}
                {firmante.cuenta_voto ? " · con voto" : " · sin voto"}
              </li>
            ))}
          </ul>

          <dl className="mt-4 grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="min-w-0 break-words">
              <dt className="text-xs font-medium text-text-600">Emitida</dt>
              <dd className="text-sm text-text-900">
                {recomendacionVigente.emitida_en
                  ? `${formatearInstante(recomendacionVigente.emitida_en)} · ${recomendacionVigente.emitida_por}`
                  : "—"}
              </dd>
            </div>
            {recomendacionVigente.sustituye ? (
              <div className="min-w-0 break-words">
                <dt className="text-xs font-medium text-text-600">Sustituye</dt>
                <dd className="text-sm text-text-900">{recomendacionVigente.sustituye}</dd>
              </div>
            ) : null}
          </dl>

          <p className="mt-3 text-sm text-text-600">Emitida: no se puede editar.</p>

          <div className="mt-3 flex flex-wrap gap-2">
            <Button
              variant="secondary"
              onClick={() =>
                void descargarArchivo(
                  `/gobierno/contrataciones/expedientes/${detalle.id}/decision/recomendaciones/${recomendacionVigente.id}/informe`,
                  recomendacionVigente.informe.nombre,
                )
              }
            >
              Descargar informe (PDF)
            </Button>
          </div>
        </div>
      ) : null}

      {decisionesSustituidas.length > 0 ? (
        <div className="mt-3 rounded-lg border border-border-subtle bg-white p-4">
          <h4 className="text-sm font-semibold text-text-900">Historial de recomendaciones sustituidas</h4>
          <ul className="mt-1 space-y-1 text-sm text-text-900">
            {decisionesSustituidas.map((r) => (
              <li key={r.id}>
                {r.referencia} · {r.estado_etiqueta}
                {r.motivo_sustitucion ? ` · ${r.motivo_sustitucion}` : ""}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {puedeRecomendar && estado.evaluacion_concluida_en && !decisionVigente ? (
        <div className="mt-3 rounded-lg border border-border-subtle bg-white p-4">
          {recomendacionVigente ? (
            !formularioSustitucionAbierto ? (
              <Button variant="secondary" onClick={() => setFormularioSustitucionAbierto(true)}>
                Sustituir recomendación
              </Button>
            ) : (
              <p className="text-sm text-text-900">
                Ya existe una recomendación emitida. Puede emitir una sustitución.
              </p>
            )
          ) : null}

          <FormField
            label="Resultado recomendado"
            htmlFor="resultado-recomendado"
            required
            error={fieldErrorsRecomendacion.resultado_recomendado?.[0]}
          >
            <select
              id="resultado-recomendado"
              value={resultadoRecomendado}
              onChange={(e) => setResultadoRecomendado(e.target.value)}
              className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              required
            >
              <option value="">Seleccione…</option>
              {estado.catalogos.resultados_recomendacion.map((c) => (
                <option key={c.codigo} value={c.codigo}>
                  {c.etiqueta}
                </option>
              ))}
            </select>
          </FormField>

          {resultadoRecomendado === "DECLARAR_DESIERTA" ? (
            <FormField
              label="Causal de desierta"
              htmlFor="causal-desierta"
              required
              error={fieldErrorsRecomendacion.causal_desierta?.[0]}
            >
              <select
                id="causal-desierta"
                value={causalDesierta}
                onChange={(e) => setCausalDesierta(e.target.value)}
                className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                required
              >
                <option value="">Seleccione…</option>
                {estado.catalogos.causales_desierta.map((c) => (
                  <option key={c.codigo} value={c.codigo}>
                    {c.etiqueta}
                  </option>
                ))}
              </select>
            </FormField>
          ) : null}

          <FormField
            label="Motivación"
            htmlFor="motivacion-recomendacion"
            required
            error={fieldErrorsRecomendacion.motivacion?.[0]}
          >
            <textarea
              id="motivacion-recomendacion"
              value={motivacion}
              onChange={(e) => setMotivacion(e.target.value)}
              className="min-h-24 w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              required
            />
          </FormField>

          <FormField
            label="Examen legal"
            htmlFor="examen-legal"
            required
            error={fieldErrorsRecomendacion.examen_legal?.[0]}
          >
            <textarea
              id="examen-legal"
              value={examenLegal}
              onChange={(e) => setExamenLegal(e.target.value)}
              className="min-h-24 w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              required
            />
          </FormField>

          <FormField
            label="Examen financiero"
            htmlFor="examen-financiero"
            required
            error={fieldErrorsRecomendacion.examen_financiero?.[0]}
          >
            <textarea
              id="examen-financiero"
              value={examenFinanciero}
              onChange={(e) => setExamenFinanciero(e.target.value)}
              className="min-h-24 w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              required
            />
          </FormField>

          <FormField
            label="Examen técnico"
            htmlFor="examen-tecnico"
            required
            error={fieldErrorsRecomendacion.examen_tecnico?.[0]}
          >
            <textarea
              id="examen-tecnico"
              value={examenTecnico}
              onChange={(e) => setExamenTecnico(e.target.value)}
              className="min-h-24 w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              required
            />
          </FormField>

          <FormField
            label="Resultado de la matriz"
            htmlFor="resultado-matriz"
            required
            error={fieldErrorsRecomendacion.resultado_matriz?.[0]}
          >
            <textarea
              id="resultado-matriz"
              value={resultadoMatriz}
              onChange={(e) => setResultadoMatriz(e.target.value)}
              className="min-h-24 w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              required
            />
          </FormField>

          <FormField
            label="Medidas de promoción"
            htmlFor="medidas-promocion"
            error={fieldErrorsRecomendacion.medidas_promocion?.[0]}
          >
            <textarea
              id="medidas-promocion"
              value={medidasPromocion}
              onChange={(e) => setMedidasPromocion(e.target.value)}
              className="min-h-24 w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
            />
          </FormField>

          {resultadoRecomendado === "ADJUDICAR" ? (
            <fieldset className="mt-4">
              <legend className="text-sm font-medium text-text-900">Opciones (hasta 3, en orden)</legend>
              {fieldErrorsRecomendacion.opciones?.[0] ? (
                <p role="alert" className="mt-1 text-sm text-red-700">
                  {fieldErrorsRecomendacion.opciones[0]}
                </p>
              ) : null}
              <div className="mt-2 space-y-2">
                {[0, 1, 2].map((index) => (
                  <FormField
                    key={index}
                    label={`Opción ${index + 1}`}
                    htmlFor={`opcion-${index}`}
                  >
                    <select
                      id={`opcion-${index}`}
                      value={opcionesSeleccionadas[index] ?? ""}
                      onChange={(e) => {
                        const valor = e.target.value;
                        setOpcionesSeleccionadas((prev) => {
                          const siguiente = [...prev];
                          siguiente[index] = valor;
                          return siguiente;
                        });
                      }}
                      className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                    >
                      <option value="">Seleccione…</option>
                      {ofertasNoRechazadas
                        .filter(
                          (o) =>
                            !opcionesSeleccionadas.includes(o.id) ||
                            opcionesSeleccionadas[index] === o.id,
                        )
                        .map((o) => (
                          <option key={o.id} value={o.id}>
                            {o.oferta} · {o.oferente}
                          </option>
                        ))}
                    </select>
                  </FormField>
                ))}
              </div>
            </fieldset>
          ) : null}

          <fieldset className="mt-4">
            <legend className="text-sm font-medium text-text-900">Rechazos</legend>
            {fieldErrorsRecomendacion.rechazos?.[0] ? (
              <p role="alert" className="mt-1 text-sm text-red-700">
                {fieldErrorsRecomendacion.rechazos[0]}
              </p>
            ) : null}
            <div className="mt-2 space-y-3">
              {estado.ofertas.map((oferta) => (
                <div key={oferta.id} className="rounded-md border border-border-subtle p-3">
                  <label className="flex items-center gap-2 text-sm text-text-900">
                    <input
                      type="checkbox"
                      checked={Boolean(rechazosSeleccionados[oferta.id])}
                      onChange={(e) =>
                        setRechazosSeleccionados((prev) => {
                          const siguiente = { ...prev };
                          if (e.target.checked) {
                            siguiente[oferta.id] = { causal: "", motivacion: "" };
                          } else {
                            delete siguiente[oferta.id];
                          }
                          return siguiente;
                        })
                      }
                    />
                    Rechazar {oferta.oferta} · {oferta.oferente}
                  </label>
                  {rechazosSeleccionados[oferta.id] ? (
                    <div className="mt-2 space-y-2">
                      <FormField
                        label="Causal de rechazo"
                        htmlFor={`causal-rechazo-${oferta.id}`}
                        required
                      >
                        <select
                          id={`causal-rechazo-${oferta.id}`}
                          value={rechazosSeleccionados[oferta.id].causal}
                          onChange={(e) =>
                            setRechazosSeleccionados((prev) => ({
                              ...prev,
                              [oferta.id]: { ...prev[oferta.id], causal: e.target.value },
                            }))
                          }
                          className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                          required
                        >
                          <option value="">Seleccione…</option>
                          {estado.catalogos.causales_rechazo.map((c) => (
                            <option key={c.codigo} value={c.codigo}>
                              {c.etiqueta}
                            </option>
                          ))}
                        </select>
                      </FormField>
                      <FormField
                        label="Motivación del rechazo"
                        htmlFor={`motivacion-rechazo-${oferta.id}`}
                        required
                      >
                        <textarea
                          id={`motivacion-rechazo-${oferta.id}`}
                          value={rechazosSeleccionados[oferta.id].motivacion}
                          onChange={(e) =>
                            setRechazosSeleccionados((prev) => ({
                              ...prev,
                              [oferta.id]: { ...prev[oferta.id], motivacion: e.target.value },
                            }))
                          }
                          className="min-h-20 w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                          required
                        />
                      </FormField>
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          </fieldset>

          <fieldset className="mt-4">
            <legend className="text-sm font-medium text-text-900">Firmantes</legend>
            {fieldErrorsRecomendacion.firmantes?.[0] ? (
              <p role="alert" className="mt-1 text-sm text-red-700">
                {fieldErrorsRecomendacion.firmantes[0]}
              </p>
            ) : null}
            <p className="mt-1 text-sm text-text-600">
              Firmantes con voto: {firmantesConVoto} de {miembrosConVoto.length} (mayoría
              requerida: {quorumRequerido})
            </p>
            <div className="mt-2 space-y-2">
              {estado.miembros.map((miembro) => (
                <label key={miembro.id} className="flex items-center gap-2 text-sm text-text-900">
                  <input
                    type="checkbox"
                    checked={firmantesSeleccionados.includes(miembro.id)}
                    onChange={(e) =>
                      setFirmantesSeleccionados((prev) =>
                        e.target.checked
                          ? [...prev, miembro.id]
                          : prev.filter((id) => id !== miembro.id),
                      )
                    }
                  />
                  {miembro.oficial} · {miembro.funcion} · {miembro.condicion}
                  {miembro.cuenta_voto ? " · con voto" : " · sin voto"}
                </label>
              ))}
            </div>
          </fieldset>

          {recomendacionVigente ? (
            <FormField
              label="Motivo de sustitución"
              htmlFor="motivo-sustitucion"
              required
              error={fieldErrorsRecomendacion.motivo_sustitucion?.[0]}
            >
              <textarea
                id="motivo-sustitucion"
                value={motivoSustitucion}
                onChange={(e) => setMotivoSustitucion(e.target.value)}
                className="min-h-20 w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                required
              />
            </FormField>
          ) : null}

          {confirmarRecomendacion ? (
            <>
              <p className="mt-3 text-sm text-text-900">
                La recomendación emitida no podrá editarse.
              </p>
              {errorRecomendacion ? (
                <p role="alert" className="mt-2 text-sm text-red-700">
                  {errorRecomendacion}
                </p>
              ) : null}
              <div className="mt-3 flex flex-wrap gap-2">
                <Button
                  variant="primary"
                  onClick={() => void emitirRecomendacion()}
                  disabled={enviandoRecomendacion}
                >
                  {enviandoRecomendacion ? "Emitiendo…" : "Confirmar emisión"}
                </Button>
                <Button variant="ghost" onClick={() => setConfirmarRecomendacion(false)}>
                  Cancelar
                </Button>
              </div>
            </>
          ) : (
            <div className="mt-4 flex flex-wrap gap-2">
              <Button variant="primary" onClick={() => setConfirmarRecomendacion(true)}>
                {recomendacionVigente ? "Emitir sustitución" : "Emitir recomendación"}
              </Button>
              {recomendacionVigente ? (
                <Button variant="secondary" onClick={() => setFormularioSustitucionAbierto(false)}>
                  Cancelar
                </Button>
              ) : null}
            </div>
          )}
        </div>
      ) : null}

      <h3 className="mt-4 text-base font-semibold text-text-900">Decisión de la autoridad</h3>

      {estado.decisiones.length > 0 ? (
        <div className="mt-2 space-y-3">
          {estado.decisiones.map((decision) => (
            <div key={decision.id} className="rounded-lg border border-border-subtle bg-white p-4">
              <dl className="grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2">
                <div className="min-w-0 break-words">
                  <dt className="text-xs font-medium text-text-600">Referencia</dt>
                  <dd className="text-sm text-text-900">{decision.referencia}</dd>
                </div>
                <div className="min-w-0 break-words">
                  <dt className="text-xs font-medium text-text-600">Resultado</dt>
                  <dd className="text-sm text-text-900">{decision.resultado_etiqueta}</dd>
                </div>
                <div className="min-w-0 break-words">
                  <dt className="text-xs font-medium text-text-600">Estado</dt>
                  <dd className="text-sm text-text-900">{decision.estado_etiqueta}</dd>
                </div>
                {decision.oferta ? (
                  <div className="min-w-0 break-words">
                    <dt className="text-xs font-medium text-text-600">Oferta</dt>
                    <dd className="text-sm text-text-900">
                      {decision.oferta} · {decision.oferente}
                    </dd>
                  </div>
                ) : null}
                {decision.posicion ? (
                  <div className="min-w-0 break-words">
                    <dt className="text-xs font-medium text-text-600">Posición</dt>
                    <dd className="text-sm text-text-900">{decision.posicion}</dd>
                  </div>
                ) : null}
                {decision.causal_etiqueta ? (
                  <div className="min-w-0 break-words">
                    <dt className="text-xs font-medium text-text-600">Causal</dt>
                    <dd className="text-sm text-text-900">{decision.causal_etiqueta}</dd>
                  </div>
                ) : null}
                {decision.anula ? (
                  <div className="min-w-0 break-words">
                    <dt className="text-xs font-medium text-text-600">Anula</dt>
                    <dd className="text-sm text-text-900">{decision.anula}</dd>
                  </div>
                ) : null}
                {decision.afectada_por ? (
                  <div className="min-w-0 break-words">
                    <dt className="text-xs font-medium text-text-600">Afectada por</dt>
                    <dd className="text-sm text-text-900">{decision.afectada_por}</dd>
                  </div>
                ) : null}
                {decision.acto ? (
                  <div className="min-w-0 break-words">
                    <dt className="text-xs font-medium text-text-600">Acto</dt>
                    <dd className="text-sm text-text-900">
                      <Link
                        to={`/gobierno/actos/${decision.acto.id}`}
                        className="text-brand-700 underline"
                      >
                        {decision.acto.tipo} {decision.acto.numero}
                      </Link>{" "}
                      · {decision.acto.fecha ? formatearFechaDeNegocio(decision.acto.fecha) : ""} ·{" "}
                      {decision.acto.status}
                    </dd>
                  </div>
                ) : null}
                {decision.cargo ? (
                  <div className="min-w-0 break-words">
                    <dt className="text-xs font-medium text-text-600">Cargo</dt>
                    <dd className="text-sm text-text-900">{decision.cargo}</dd>
                  </div>
                ) : null}
                <div className="min-w-0 break-words sm:col-span-2">
                  <dt className="text-xs font-medium text-text-600">Motivación</dt>
                  <dd className="text-sm text-text-900">{decision.motivacion}</dd>
                </div>
                <div className="min-w-0 break-words">
                  <dt className="text-xs font-medium text-text-600">Decidida</dt>
                  <dd className="text-sm text-text-900">
                    {decision.decidida_en
                      ? `${formatearInstante(decision.decidida_en)} · ${decision.decidida_por ?? ""}`
                      : "—"}
                  </dd>
                </div>
              </dl>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState title="Sin decisiones registradas" />
      )}

      {puedeDecidir ? (
        <div className="mt-3 rounded-lg border border-border-subtle bg-white p-4">
          <FormField
            label="Acto"
            htmlFor="acto-decision"
            required
            error={fieldErrorsDecision.acto_id?.[0]}
          >
            {estado.actos_elegibles.length > 0 ? (
              <select
                id="acto-decision"
                value={actoId}
                onChange={(e) => setActoId(e.target.value)}
                className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                required
              >
                <option value="">Seleccione…</option>
                {estado.actos_elegibles.map((acto) => (
                  <option key={acto.id} value={acto.id}>
                    {acto.tipo} {acto.numero} · {formatearFechaDeNegocio(acto.fecha)} · {acto.asunto}
                  </option>
                ))}
              </select>
            ) : (
              <p className="text-sm text-text-900">
                No hay actos DOC-02 emitidos de carácter particular con competencia APROBAR sobre
                CONTRATACIONES sin usar.{" "}
                <Link to="/gobierno/actos" className="text-brand-700 underline">
                  Ir a actos
                </Link>
              </p>
            )}
          </FormField>

          <fieldset className="mt-4">
            <legend className="text-sm font-medium text-text-900">Resultado</legend>
            <div className="mt-2 space-y-2">
              {estado.catalogos.resultados_decision.map((c) => (
                <label key={c.codigo} className="flex items-center gap-2 text-sm text-text-900">
                  <input
                    type="radio"
                    name="resultado-decision"
                    value={c.codigo}
                    checked={resultadoDecision === c.codigo}
                    onChange={() => setResultadoDecision(c.codigo)}
                  />
                  {c.etiqueta}
                </label>
              ))}
            </div>
          </fieldset>

          {resultadoDecision === "ADJUDICADA" ? (
            <FormField
              label="Oferta"
              htmlFor="oferta-decision"
              required
              error={fieldErrorsDecision.oferta_id?.[0]}
              help={
                opcionPropuesta
                  ? `Opción propuesta: ${opcionPropuesta.oferta} · ${opcionPropuesta.oferente}`
                  : undefined
              }
            >
              {opcionPropuesta ? (
                <select
                  id="oferta-decision"
                  key={opcionPropuesta.offer_id}
                  defaultValue={opcionPropuesta.offer_id}
                  className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                  required
                >
                  <option value={opcionPropuesta.offer_id}>
                    {opcionPropuesta.oferta} · {opcionPropuesta.oferente}
                  </option>
                </select>
              ) : (
                <p className="text-sm text-text-900">
                  No hay opción adjudicable según la recomendación vigente.
                </p>
              )}
            </FormField>
          ) : null}

          {resultadoDecision === "DESIERTA" ? (
            <FormField
              label="Causal de desierta"
              htmlFor="causal-desierta-decision"
              required
              error={fieldErrorsDecision.causal_desierta?.[0]}
            >
              <select
                id="causal-desierta-decision"
                value={causalDesiertaDecision}
                onChange={(e) => setCausalDesiertaDecision(e.target.value)}
                className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                required
              >
                <option value="">Seleccione…</option>
                {estado.catalogos.causales_desierta.map((c) => (
                  <option key={c.codigo} value={c.codigo}>
                    {c.etiqueta}
                  </option>
                ))}
              </select>
            </FormField>
          ) : null}

          {resultadoDecision === "NULIDAD" ? (
            <>
              <FormField
                label="Decisión a anular"
                htmlFor="anula-decision"
                required
                error={fieldErrorsDecision.anula_id?.[0]}
              >
                <select
                  id="anula-decision"
                  value={anulaId}
                  onChange={(e) => setAnulaId(e.target.value)}
                  className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                  required
                >
                  <option value="">Seleccione…</option>
                  {estado.decisiones
                    .filter((d) => d.estado === "VIGENTE" && d.resultado !== "NULIDAD")
                    .map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.referencia} · {d.resultado_etiqueta}
                      </option>
                    ))}
                </select>
              </FormField>
              <FormField
                label="Causal de nulidad"
                htmlFor="causal-nulidad"
                required
                error={fieldErrorsDecision.causal_nulidad?.[0]}
              >
                <select
                  id="causal-nulidad"
                  value={causalNulidad}
                  onChange={(e) => setCausalNulidad(e.target.value)}
                  className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                  required
                >
                  <option value="">Seleccione…</option>
                  {estado.catalogos.causales_nulidad.map((c) => (
                    <option key={c.codigo} value={c.codigo}>
                      {c.etiqueta}
                    </option>
                  ))}
                </select>
              </FormField>
            </>
          ) : null}

          <FormField
            label="Motivación"
            htmlFor="motivacion-decision"
            required
            error={fieldErrorsDecision.motivacion?.[0]}
          >
            <textarea
              id="motivacion-decision"
              value={motivacionDecision}
              onChange={(e) => setMotivacionDecision(e.target.value)}
              className="min-h-24 w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              required
            />
          </FormField>

          {confirmarDecision ? (
            <>
              <p className="mt-3 text-sm text-text-900">
                La decisión queda registrada con el acto indicado y no podrá editarse.
              </p>
              {errorDecision ? (
                <p role="alert" className="mt-2 text-sm text-red-700">
                  {errorDecision}
                </p>
              ) : null}
              <div className="mt-3 flex flex-wrap gap-2">
                <Button
                  variant="primary"
                  onClick={() => void registrarDecision()}
                  disabled={enviandoDecision}
                >
                  {enviandoDecision ? "Registrando…" : "Confirmar decisión"}
                </Button>
                <Button variant="ghost" onClick={() => setConfirmarDecision(false)}>
                  Cancelar
                </Button>
              </div>
            </>
          ) : (
            <div className="mt-4 flex flex-wrap gap-2">
              <Button variant="primary" onClick={() => setConfirmarDecision(true)}>
                Registrar decisión
              </Button>
            </div>
          )}
        </div>
      ) : null}

      {decisionVigente ? (
        <>
          <h3 className="mt-4 text-base font-semibold text-text-900">Notificación a los oferentes</h3>
          <div className="mt-2 rounded-lg border border-border-subtle bg-white p-4">
            <p className="text-sm text-text-600">
              El registro de notificaciones se hace en el acto administrativo (DOC-04). Aquí se
              muestra su estado; no implica entrega electrónica.{" "}
              <Link
                to={`/gobierno/actos/${decisionVigente.acto?.id ?? ""}`}
                className="text-brand-700 underline"
              >
                Registrar notificaciones en el acto
              </Link>
            </p>
            {estado.acto_eficaz ? (
              <p className="mt-2 text-sm text-text-900">
                El acto es eficaz: todos los oferentes fueron notificados.
              </p>
            ) : null}
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm text-text-900">
                <thead>
                  <tr className="text-left text-xs text-text-600">
                    <th className="py-1 pr-3 font-medium">Oferta</th>
                    <th className="py-1 pr-3 font-medium">Oferente</th>
                    <th className="py-1 pr-3 font-medium">Documento</th>
                    <th className="py-1 pr-3 font-medium">Estado</th>
                    <th className="py-1 pr-3 font-medium">Fecha</th>
                    <th className="py-1 font-medium">Medio</th>
                  </tr>
                </thead>
                <tbody>
                  {estado.notificaciones.map((notificacion) => (
                    <tr key={notificacion.offer_id} className="border-t border-border-subtle">
                      <td className="py-1 pr-3">{notificacion.oferta}</td>
                      <td className="py-1 pr-3">{notificacion.oferente}</td>
                      <td className="py-1 pr-3">{notificacion.documento}</td>
                      <td className="py-1 pr-3">{notificacion.estado_etiqueta}</td>
                      <td className="py-1 pr-3">
                        {notificacion.fecha_notificacion
                          ? formatearInstante(notificacion.fecha_notificacion)
                          : "—"}
                      </td>
                      <td className="py-1">{notificacion.medio ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : null}

      <h3 className="mt-4 text-base font-semibold text-text-900">Historial</h3>
      <div className="mt-2 rounded-lg border border-border-subtle bg-white p-4">
        {historial.length > 0 ? (
          <ul className="space-y-1 text-sm text-text-900">
            {historial.map((item, index) => (
              <li key={index}>
                {item.fecha ? `${formatearInstante(item.fecha)} · ` : ""}
                {item.texto}
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState title="Sin historial" />
        )}
      </div>

      <p className="mt-3 text-sm text-text-600">
        El contrato derivado se gestiona en CNT-01; esta sección no lo crea.
      </p>
    </section>
  );
}
