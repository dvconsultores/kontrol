import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Button } from "@/components/Button";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import { CONSULTA_EXPEDIENTES, type ExpedienteDetalle } from "../api";

type DocumentoEstado = {
  id: string;
  titulo: string;
  version: number;
};

type ActoElegible = {
  id: string;
  etiqueta: string;
  fecha: string;
  asunto: string;
};

type ReglaGarantia = {
  codigo: string;
  nombre: string;
  fuente: string;
  tipo: string;
  tipo_etiqueta: string;
  forma: string;
  base: string | null;
  base_etiqueta: string | null;
  porcentaje_min: string | null;
  porcentaje_max: string | null;
  moneda_exigida: string | null;
  vigencia_exigida: string;
  retencion_alternativa_pct: string | null;
  permite_sustitucion: boolean;
  requiere_adjudicacion: boolean;
  condicion_liberacion: string;
  condicion_ejecucion: string;
};

type SujetoGarantia = {
  offer_id: string;
  oferta: string;
  oferente: string;
  garantias: string[];
  cubierto: boolean;
};

type RequisitoGarantia = {
  id: string;
  referencia: string;
  tipo: string;
  tipo_etiqueta: string;
  nombre: string | null;
  etapa: string;
  etapa_etiqueta: string;
  regla: ReglaGarantia;
  forma: string;
  porcentaje: string | null;
  monto_fijo: string | null;
  moneda: string | null;
  vigencia_minima_hasta: string | null;
  fundamento: string;
  documento: DocumentoEstado;
  registrado_en: string;
  pendiente_adjudicacion: boolean;
  sujetos: SujetoGarantia[];
};

type CriterioGarantia = {
  criterio: string;
  resultado: string;
  detalle: string;
};

type EventoGarantia = {
  id: string;
  accion: string;
  accion_etiqueta: string;
  fecha: string;
  registrada_en: string;
  actor: string;
  motivo: string | null;
  garantia: string;
  nueva_garantia: string | null;
  acto: { id: string; etiqueta: string } | null;
  documento: DocumentoEstado | null;
  monto: string | null;
  moneda: string | null;
  precondicion: string | null;
  precondicion_etiqueta: string | null;
  precondicion_detalle: string | null;
};

type GarantiaInstrumento = {
  id: string;
  referencia: string;
  requisito_id: string;
  requisito: string;
  tipo: string;
  tipo_etiqueta: string;
  nombre: string | null;
  etapa: string;
  etapa_etiqueta: string;
  offer_id: string;
  oferta: string;
  oferente: string;
  decision: string | null;
  emisor: { id: string; nombre: string; tipo: string; tipo_etiqueta: string; rif: string };
  referencia_emisor: string;
  monto: string;
  moneda: string;
  fecha_emision: string;
  vigente_desde: string;
  vigente_hasta: string;
  dias_restantes: number;
  vigencia: string;
  vigencia_etiqueta: string;
  estado: string;
  estado_etiqueta: string;
  origen: string;
  antecesor: string | null;
  sucesor: string | null;
  suficiencia: string | null;
  suficiencia_etiqueta: string | null;
  criterios: CriterioGarantia[];
  documento: DocumentoEstado;
  observacion: string | null;
  acciones: string[];
  historial: EventoGarantia[];
};

type EmisorGarantia = {
  id: string;
  nombre: string;
  tipo: string;
  tipo_etiqueta: string;
  rif: string;
};

type OfertaGarantia = {
  id: string;
  referencia: string;
  oferente: string;
};

type EstadoGarantias = {
  expediente_id: string;
  version: number;
  estado_expediente: string;
  hoy: string;
  adjudicacion: {
    decision_id: string;
    decision: string;
    offer_id: string;
    oferta: string;
    oferente: string;
  } | null;
  resumen: {
    requisitos: number;
    registradas: number;
    suficientes: number;
    insuficientes: number;
    no_evaluables: number;
    por_vencer: number;
    vencidas: number;
    liberadas: number;
    ejecutadas: number;
    sin_garantia: number;
  };
  requisitos: RequisitoGarantia[];
  garantias: GarantiaInstrumento[];
  ofertas: OfertaGarantia[];
  emisores: EmisorGarantia[];
  documentos: DocumentoEstado[];
  actos_elegibles: ActoElegible[];
  reglas: ReglaGarantia[];
};

type BancosRespuesta = {
  emisores: EmisorGarantia[];
  bancos: { id: string; codigo: string; nombre: string }[];
};

type FormularioAbierto =
  | { tipo: "requisito" }
  | { tipo: "emisor" }
  | { tipo: "garantia" }
  | { tipo: "accion"; garantiaId: string; accion: string }
  | null;

function erroresDeCampos(error: unknown): Record<string, string[]> {
  if (error instanceof ApiError) return error.fieldErrors ?? {};
  return {};
}

function textoErrorPorCodigo(error: unknown): string {
  if (!(error instanceof ApiError)) return "Ocurrió un error inesperado";
  switch (error.code) {
    case "GOV_GUARANTEE_ACTIVE_EXISTS":
      return "Ya existe una garantía activa para ese requisito y oferente";
    case "GOV_GUARANTEE_AWARD_REQUIRED":
      return "Se requiere una adjudicación vigente para registrar esta garantía";
    case "GOV_GUARANTEE_DUPLICATE":
      return "Ya existe una garantía con ese emisor y número de instrumento";
    case "GOV_GUARANTEE_EXECUTED":
      return "La garantía ya fue ejecutada";
    case "GOV_GUARANTEE_INVALID":
      return "Revise los datos del formulario";
    case "GOV_GUARANTEE_INVALID_ACT":
      return "El acto seleccionado no es válido para esta actuación";
    case "GOV_GUARANTEE_ISSUER_DUPLICATE":
      return "Ya existe un emisor con ese RIF";
    case "GOV_GUARANTEE_ISSUER_REGISTERED":
      return "El emisor ya está registrado";
    case "GOV_GUARANTEE_NOT_ACTIVE":
      return "La garantía no está activa";
    case "GOV_GUARANTEE_NOT_FOUND":
      return "Garantía no encontrada";
    case "GOV_GUARANTEE_REGISTERED":
      return "La garantía ya está registrada";
    case "GOV_GUARANTEE_RELEASED":
      return "La garantía ya fue liberada";
    case "GOV_GUARANTEE_RENEWED":
      return "La garantía ya fue renovada";
    case "GOV_GUARANTEE_REQUIREMENT_REGISTERED":
      return "El requisito ya está registrado";
    case "GOV_GUARANTEE_SUBSTITUTED":
      return "La garantía ya fue sustituida";
    case "GOV_GUARANTEE_SUBSTITUTION_NOT_ALLOWED":
      return "La regla no permite sustituir esta garantía";
    case "GOV_PROCUREMENT_FILE_STALE":
      return "Los datos cambiaron; se actualizaron, revise e intente de nuevo";
    case "GOV_SOD_CONFLICT":
      return "La segregación de funciones del ente impide esta actuación";
    default:
      return "Ocurrió un error inesperado";
  }
}

function formatearMonto(valor: string, moneda: string): string {
  return `${new Intl.NumberFormat("es-VE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(valor))} ${moneda}`;
}

export function SeccionGarantias({
  detalle,
  activeCompanyId,
}: {
  detalle: ExpedienteDetalle;
  activeCompanyId: string | null;
}) {
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();

  const puedeVer = tiene("gobierno_garantias:view", "empresa");
  const puedeGestionar = tiene("gobierno_garantias:manage", "empresa");
  const puedeLiberar = tiene("gobierno_garantias:release", "empresa");
  const puedeEjecutar = tiene("gobierno_garantias:execute", "empresa");

  const [formulario, setFormulario] = useState<FormularioAbierto>(null);
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});
  const [enviando, setEnviando] = useState(false);
  const [confirmando, setConfirmando] = useState(false);

  const [reqRegla, setReqRegla] = useState("");
  const [reqPorcentaje, setReqPorcentaje] = useState("");
  const [reqMonto, setReqMonto] = useState("");
  const [reqMoneda, setReqMoneda] = useState("");
  const [reqNombre, setReqNombre] = useState("");
  const [reqVigencia, setReqVigencia] = useState("");
  const [reqFundamento, setReqFundamento] = useState("");
  const [reqDocumento, setReqDocumento] = useState("");

  const [emiTipo, setEmiTipo] = useState("");
  const [emiBanco, setEmiBanco] = useState("");
  const [emiNombre, setEmiNombre] = useState("");
  const [emiRif, setEmiRif] = useState("");

  const [garRequisito, setGarRequisito] = useState("");
  const [garOferta, setGarOferta] = useState("");
  const [garEmisor, setGarEmisor] = useState("");
  const [garReferencia, setGarReferencia] = useState("");
  const [garMonto, setGarMonto] = useState("");
  const [garMoneda, setGarMoneda] = useState("");
  const [garEmision, setGarEmision] = useState("");
  const [garDesde, setGarDesde] = useState("");
  const [garHasta, setGarHasta] = useState("");
  const [garDocumento, setGarDocumento] = useState("");
  const [garObservacion, setGarObservacion] = useState("");

  const [accionMonto, setAccionMonto] = useState("");
  const [accionMoneda, setAccionMoneda] = useState("");
  const [accionEmisor, setAccionEmisor] = useState("");
  const [accionReferencia, setAccionReferencia] = useState("");
  const [accionEmision, setAccionEmision] = useState("");
  const [accionDesde, setAccionDesde] = useState("");
  const [accionHasta, setAccionHasta] = useState("");
  const [accionDocumento, setAccionDocumento] = useState("");
  const [accionMotivo, setAccionMotivo] = useState("");
  const [accionActo, setAccionActo] = useState("");

  const estadoQuery = useQuery({
    queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId, "garantias", detalle.id],
    queryFn: () =>
      apiFetch<EstadoGarantias>(
        `/gobierno/contrataciones/expedientes/${detalle.id}/garantias`,
      ),
    enabled: puedeVer && Boolean(activeCompanyId),
  });

  const bancosQuery = useQuery({
    queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId, "garantias-emisores"],
    queryFn: () =>
      apiFetch<BancosRespuesta>(`/gobierno/contrataciones/garantias/emisores`),
    enabled:
      puedeGestionar &&
      Boolean(activeCompanyId) &&
      formulario?.tipo === "emisor" &&
      emiTipo === "BANCO",
  });

  function invalidar() {
    void queryClient.invalidateQueries({
      queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId],
    });
  }

  function limpiarErrores() {
    setErrorGeneral(null);
    setFieldErrors({});
  }

  function cerrarFormulario() {
    setFormulario(null);
    setConfirmando(false);
    limpiarErrores();
  }

  async function enviar(
    ruta: string,
    cuerpo: Record<string, unknown>,
    titulo: string,
    conVersion: boolean,
  ) {
    setEnviando(true);
    limpiarErrores();
    try {
      await apiFetch(ruta, {
        method: "POST",
        body: cuerpo,
        ifMatch: conVersion ? String(estadoQuery.data?.version ?? detalle.version) : undefined,
      });
      invalidar();
      notify({ type: "success", title: titulo });
      cerrarFormulario();
    } catch (e) {
      setErrorGeneral(textoErrorPorCodigo(e));
      setFieldErrors(erroresDeCampos(e));
      if (e instanceof ApiError && e.code === "GOV_PROCUREMENT_FILE_STALE") {
        invalidar();
      }
    } finally {
      setEnviando(false);
    }
  }

  if (!puedeVer) return null;

  if (estadoQuery.isLoading) {
    return (
      <section aria-labelledby="sec-garantias" className="mt-6">
        <h2 id="sec-garantias" className="text-lg font-semibold text-text-900">
          Garantías y cauciones
        </h2>
        <LoadingState />
      </section>
    );
  }

  if (estadoQuery.isError || !estadoQuery.data) {
    return (
      <section aria-labelledby="sec-garantias" className="mt-6">
        <h2 id="sec-garantias" className="text-lg font-semibold text-text-900">
          Garantías y cauciones
        </h2>
        <p role="alert" className="mt-2 text-sm text-red-700">
          No se pudo cargar la sección de garantías.
        </p>
      </section>
    );
  }

  const estado = estadoQuery.data;
  const reglaElegida = estado.reglas.find((r) => r.codigo === reqRegla);
  const requisitoElegido = estado.requisitos.find((r) => r.id === garRequisito);


  return (
    <section aria-labelledby="sec-garantias" className="mt-6">
      <h2 id="sec-garantias" className="text-lg font-semibold text-text-900">
        Garantías y cauciones
      </h2>

      <p className="mt-2 text-sm text-text-900">
        {estado.adjudicacion
          ? `Adjudicación vigente: ${estado.adjudicacion.decision} · ${estado.adjudicacion.oferta} (${estado.adjudicacion.oferente})`
          : "Sin adjudicación vigente: las garantías de formalización esperan la decisión (PROC-08)."}
      </p>

      <h3 className="mt-4 text-base font-semibold text-text-900">Resumen</h3>
      <dl
        aria-label="Resumen de garantías"
        className="mt-2 grid grid-cols-2 gap-2 rounded-lg border border-border-subtle bg-white p-4 sm:grid-cols-5"
      >
        <div>
          <dt className="text-sm text-text-600">Requisitos</dt>
          <dd className="text-sm font-semibold text-text-900">{estado.resumen.requisitos}</dd>
        </div>
        <div>
          <dt className="text-sm text-text-600">Registradas</dt>
          <dd className="text-sm font-semibold text-text-900">{estado.resumen.registradas}</dd>
        </div>
        <div>
          <dt className="text-sm text-text-600">Suficientes</dt>
          <dd className="text-sm font-semibold text-text-900">{estado.resumen.suficientes}</dd>
        </div>
        <div>
          <dt className="text-sm text-text-600">Insuficientes</dt>
          <dd className="text-sm font-semibold text-text-900">{estado.resumen.insuficientes}</dd>
        </div>
        <div>
          <dt className="text-sm text-text-600">No evaluables</dt>
          <dd className="text-sm font-semibold text-text-900">{estado.resumen.no_evaluables}</dd>
        </div>
        <div>
          <dt className="text-sm text-text-600">Por vencer</dt>
          <dd className="text-sm font-semibold text-text-900">{estado.resumen.por_vencer}</dd>
        </div>
        <div>
          <dt className="text-sm text-text-600">Vencidas</dt>
          <dd className="text-sm font-semibold text-text-900">{estado.resumen.vencidas}</dd>
        </div>
        <div>
          <dt className="text-sm text-text-600">Liberadas</dt>
          <dd className="text-sm font-semibold text-text-900">{estado.resumen.liberadas}</dd>
        </div>
        <div>
          <dt className="text-sm text-text-600">Ejecutadas</dt>
          <dd className="text-sm font-semibold text-text-900">{estado.resumen.ejecutadas}</dd>
        </div>
        <div>
          <dt className="text-sm text-text-600">Sujetos sin garantía</dt>
          <dd className="text-sm font-semibold text-text-900">{estado.resumen.sin_garantia}</dd>
        </div>
      </dl>

      <h3 className="mt-4 text-base font-semibold text-text-900">Requisitos</h3>
      {estado.requisitos.length === 0 ? (
        <p className="mt-2 text-sm text-text-900">No hay requisitos de garantía registrados.</p>
      ) : (
        <div className="mt-2 space-y-3">
          {estado.requisitos.map((requisito) => (
            <article
              key={requisito.id}
              className="rounded-lg border border-border-subtle bg-white p-4"
            >
              <h4 className="text-sm font-semibold text-text-900 break-words">
                {requisito.referencia} · {requisito.tipo_etiqueta}
                {requisito.nombre ? ` · ${requisito.nombre}` : ""}
              </h4>
              <dl className="mt-2 space-y-1">
                <div>
                  <dt className="text-sm text-text-600">Regla</dt>
                  <dd className="text-sm text-text-900 break-words">
                    {requisito.regla.nombre} ({requisito.regla.fuente})
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-text-600">Exigencia</dt>
                  <dd className="text-sm text-text-900 break-words">
                    {requisito.forma === "PORCENTAJE"
                      ? `${requisito.porcentaje} % del ${requisito.regla.base_etiqueta ?? ""}`
                      : requisito.forma === "MONTO_FIJO" && requisito.monto_fijo && requisito.moneda
                        ? formatearMonto(requisito.monto_fijo, requisito.moneda)
                        : requisito.nombre ?? ""}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-text-600">Vigencia mínima</dt>
                  <dd className="text-sm text-text-900">
                    {requisito.vigencia_minima_hasta
                      ? formatearFechaDeNegocio(requisito.vigencia_minima_hasta)
                      : "No fijada"}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-text-600">Vigencia exigida por la norma</dt>
                  <dd className="text-sm text-text-900 break-words">
                    {requisito.regla.vigencia_exigida}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-text-600">Fundamento</dt>
                  <dd className="text-sm text-text-900 break-words">{requisito.fundamento}</dd>
                </div>
                <div>
                  <dt className="text-sm text-text-600">Documento</dt>
                  <dd className="text-sm text-text-900 break-words">
                    {requisito.documento.titulo}, versión {requisito.documento.version}
                  </dd>
                </div>
                {requisito.regla.retencion_alternativa_pct ? (
                  <div>
                    <dt className="text-sm text-text-600">Retención alternativa</dt>
                    <dd className="text-sm text-text-900 break-words">
                      {requisito.regla.retencion_alternativa_pct} % sobre los pagos; no se registra
                      aquí
                    </dd>
                  </div>
                ) : null}
              </dl>
              <div className="mt-2">
                <p className="text-sm font-semibold text-text-900">Sujetos</p>
                {requisito.pendiente_adjudicacion ? (
                  <p className="text-sm text-text-900">Pendiente de adjudicación</p>
                ) : (
                  <ul className="mt-1 list-disc pl-5 text-sm text-text-900">
                    {requisito.sujetos.map((sujeto) => (
                      <li key={sujeto.offer_id} className="break-words">
                        {sujeto.oferta} · {sujeto.oferente}:{" "}
                        {sujeto.garantias.length > 0 ? sujeto.garantias.join(", ") : "sin garantía"}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </article>
          ))}
        </div>
      )}

      {puedeGestionar && estado.estado_expediente === "ABIERTO" ? (
        <div className="mt-3">
          {formulario?.tipo === "requisito" ? (
            <div className="rounded-lg border border-border-subtle bg-white p-4">
              <FormField
                label="Regla"
                htmlFor="req-regla"
                required
                error={fieldErrors.regla_codigo?.[0]}
                help={reglaElegida ? reglaElegida.fuente : undefined}
              >
                <select
                  id="req-regla"
                  value={reqRegla}
                  onChange={(e) => setReqRegla(e.target.value)}
                  className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                  required
                >
                  <option value="">Seleccione…</option>
                  {estado.reglas.map((regla) => (
                    <option key={regla.codigo} value={regla.codigo}>
                      {regla.tipo_etiqueta} · {regla.nombre}
                    </option>
                  ))}
                </select>
              </FormField>
              {reglaElegida?.forma === "PORCENTAJE" ? (
                <FormField
                  label="Porcentaje (%)"
                  htmlFor="req-porcentaje"
                  required
                  error={fieldErrors.porcentaje?.[0]}
                  help={`Rango legal: ${reglaElegida.porcentaje_min ?? "—"} a ${reglaElegida.porcentaje_max ?? "—"}`}
                >
                  <input
                    id="req-porcentaje"
                    type="number"
                    step="0.01"
                    value={reqPorcentaje}
                    onChange={(e) => setReqPorcentaje(e.target.value)}
                    className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                    required
                  />
                </FormField>
              ) : null}
              {reglaElegida?.forma === "MONTO_FIJO" ? (
                <>
                  <FormField
                    label="Monto exigido"
                    htmlFor="req-monto"
                    required
                    error={fieldErrors.monto_fijo?.[0]}
                  >
                    <input
                      id="req-monto"
                      type="number"
                      step="0.01"
                      value={reqMonto}
                      onChange={(e) => setReqMonto(e.target.value)}
                      className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                      required
                    />
                  </FormField>
                  <FormField
                    label="Moneda"
                    htmlFor="req-moneda"
                    required
                    error={fieldErrors.moneda?.[0]}
                  >
                    <select
                      id="req-moneda"
                      value={reqMoneda}
                      onChange={(e) => setReqMoneda(e.target.value)}
                      className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                      required
                    >
                      <option value="">Seleccione…</option>
                      {reglaElegida.moneda_exigida ? (
                        <option value={reglaElegida.moneda_exigida}>
                          {reglaElegida.moneda_exigida}
                        </option>
                      ) : (
                        <>
                          <option value="VES">VES</option>
                          <option value="USD">USD</option>
                          <option value="EUR">EUR</option>
                        </>
                      )}
                    </select>
                  </FormField>
                </>
              ) : null}
              {reglaElegida?.tipo === "OTRA" ? (
                <FormField
                  label="Nombre de la garantía"
                  htmlFor="req-nombre"
                  required
                  error={fieldErrors.nombre?.[0]}
                >
                  <input
                    id="req-nombre"
                    value={reqNombre}
                    onChange={(e) => setReqNombre(e.target.value)}
                    className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                    required
                  />
                </FormField>
              ) : null}
              <FormField
                label="Vigente al menos hasta"
                htmlFor="req-vigencia"
                error={fieldErrors.vigencia_minima_hasta?.[0]}
              >
                <input
                  id="req-vigencia"
                  type="date"
                  value={reqVigencia}
                  onChange={(e) => setReqVigencia(e.target.value)}
                  className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                />
              </FormField>
              <FormField
                label="Fundamento (pliego o condiciones)"
                htmlFor="req-fundamento"
                required
                error={fieldErrors.fundamento?.[0]}
              >
                <textarea
                  id="req-fundamento"
                  value={reqFundamento}
                  onChange={(e) => setReqFundamento(e.target.value)}
                  className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                  required
                />
              </FormField>
              <FormField
                label="Documento soporte"
                htmlFor="req-documento"
                required
                error={fieldErrors.documento_id?.[0]}
              >
                {estado.documentos.length > 0 ? (
                  <select
                    id="req-documento"
                    value={reqDocumento}
                    onChange={(e) => setReqDocumento(e.target.value)}
                    className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                    required
                  >
                    <option value="">Seleccione…</option>
                    {estado.documentos.map((doc) => (
                      <option key={doc.id} value={doc.id}>
                        {doc.titulo} · versión {doc.version}
                      </option>
                    ))}
                  </select>
                ) : (
                  <p className="text-sm text-text-900">
                    Vincule primero el documento al expediente en la sección de documentos.
                  </p>
                )}
              </FormField>
              {errorGeneral ? (
                <p role="alert" className="mt-2 text-sm text-red-700">
                  {errorGeneral}
                </p>
              ) : null}
              <div className="mt-3 flex flex-wrap gap-2">
                <Button
                  variant="primary"
                  disabled={enviando}
                  onClick={() =>
                    void enviar(
                      `/gobierno/contrataciones/expedientes/${detalle.id}/garantias/requisitos`,
                      {
                        regla_codigo: reqRegla,
                        fundamento: reqFundamento,
                        documento_id: reqDocumento,
                        porcentaje: reqPorcentaje || null,
                        monto_fijo: reqMonto || null,
                        moneda: reqMoneda || null,
                        nombre: reqNombre || null,
                        vigencia_minima_hasta: reqVigencia || null,
                      },
                      "Requisito registrado",
                      true,
                    )
                  }
                >
                  {enviando ? "Registrando…" : "Registrar requisito"}
                </Button>
                <Button variant="ghost" onClick={cerrarFormulario}>
                  Cancelar
                </Button>
              </div>
            </div>
          ) : (
            <Button variant="secondary" onClick={() => setFormulario({ tipo: "requisito" })}>
              Nuevo requisito
            </Button>
          )}
        </div>
      ) : null}

      <h3 className="mt-4 text-base font-semibold text-text-900">Emisores</h3>
      {estado.emisores.length === 0 ? (
        <p className="mt-2 text-sm text-text-900">No hay emisores registrados.</p>
      ) : (
        <ul className="mt-2 list-disc pl-5 text-sm text-text-900">
          {estado.emisores.map((emisor) => (
            <li key={emisor.id} className="break-words">
              {emisor.nombre} · {emisor.tipo_etiqueta} · RIF {emisor.rif}
            </li>
          ))}
        </ul>
      )}
      {puedeGestionar ? (
        <div className="mt-3">
          {formulario?.tipo === "emisor" ? (
            <div className="rounded-lg border border-border-subtle bg-white p-4">
              <FormField
                label="Tipo de emisor"
                htmlFor="emi-tipo"
                required
                error={fieldErrors.tipo?.[0]}
              >
                <select
                  id="emi-tipo"
                  value={emiTipo}
                  onChange={(e) => setEmiTipo(e.target.value)}
                  className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                  required
                >
                  <option value="">Seleccione…</option>
                  <option value="BANCO">Banco</option>
                  <option value="ASEGURADORA">Aseguradora</option>
                  <option value="SOCIEDAD_GARANTIAS_RECIPROCAS">
                    Sociedad de Garantías Recíprocas
                  </option>
                  <option value="OTRO">Otro</option>
                </select>
              </FormField>
              {emiTipo === "BANCO" ? (
                <FormField
                  label="Banco"
                  htmlFor="emi-banco"
                  required
                  error={fieldErrors.banco_id?.[0]}
                >
                  <select
                    id="emi-banco"
                    value={emiBanco}
                    onChange={(e) => setEmiBanco(e.target.value)}
                    className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                    required
                  >
                    <option value="">Seleccione…</option>
                    {(bancosQuery.data?.bancos ?? []).map((banco) => (
                      <option key={banco.id} value={banco.id}>
                        {banco.nombre}
                      </option>
                    ))}
                  </select>
                </FormField>
              ) : null}
              <FormField
                label="Nombre"
                htmlFor="emi-nombre"
                error={fieldErrors.nombre?.[0]}
              >
                <input
                  id="emi-nombre"
                  value={emiNombre}
                  onChange={(e) => setEmiNombre(e.target.value)}
                  className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                />
              </FormField>
              <FormField label="RIF" htmlFor="emi-rif" required error={fieldErrors.rif?.[0]}>
                <input
                  id="emi-rif"
                  value={emiRif}
                  onChange={(e) => setEmiRif(e.target.value)}
                  className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                  required
                />
              </FormField>
              {errorGeneral ? (
                <p role="alert" className="mt-2 text-sm text-red-700">
                  {errorGeneral}
                </p>
              ) : null}
              <div className="mt-3 flex flex-wrap gap-2">
                <Button
                  variant="primary"
                  disabled={enviando}
                  onClick={() =>
                    void enviar(
                      `/gobierno/contrataciones/garantias/emisores`,
                      {
                        tipo: emiTipo,
                        rif: emiRif,
                        nombre: emiNombre || null,
                        banco_id: emiTipo === "BANCO" ? emiBanco : null,
                      },
                      "Emisor registrado",
                      false,
                    )
                  }
                >
                  {enviando ? "Registrando…" : "Registrar emisor"}
                </Button>
                <Button variant="ghost" onClick={cerrarFormulario}>
                  Cancelar
                </Button>
              </div>
            </div>
          ) : (
            <Button variant="secondary" onClick={() => setFormulario({ tipo: "emisor" })}>
              Nuevo emisor
            </Button>
          )}
        </div>
      ) : null}

      <h3 className="mt-4 text-base font-semibold text-text-900">Garantías</h3>
      {puedeGestionar &&
      estado.estado_expediente === "ABIERTO" &&
      estado.requisitos.length > 0 ? (
        <div className="mt-3">
          {formulario?.tipo === "garantia" ? (
            <div className="rounded-lg border border-border-subtle bg-white p-4">
              <FormField
                label="Requisito"
                htmlFor="gar-requisito"
                required
                error={fieldErrors.requisito_id?.[0]}
              >
                <select
                  id="gar-requisito"
                  value={garRequisito}
                  onChange={(e) => setGarRequisito(e.target.value)}
                  className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                  required
                >
                  <option value="">Seleccione…</option>
                  {estado.requisitos.map((requisito) => (
                    <option key={requisito.id} value={requisito.id}>
                      {requisito.referencia} · {requisito.tipo_etiqueta}
                    </option>
                  ))}
                </select>
              </FormField>
              <FormField
                label="Oferente"
                htmlFor="gar-oferta"
                required
                error={fieldErrors.oferta_id?.[0]}
              >
                <select
                  id="gar-oferta"
                  value={garOferta}
                  onChange={(e) => setGarOferta(e.target.value)}
                  className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                  required
                >
                  <option value="">Seleccione…</option>
                  {requisitoElegido?.regla.requiere_adjudicacion && estado.adjudicacion
                    ? estado.ofertas
                        .filter((o) => o.id === estado.adjudicacion?.offer_id)
                        .map((oferta) => (
                          <option key={oferta.id} value={oferta.id}>
                            {oferta.referencia} · {oferta.oferente}
                          </option>
                        ))
                    : estado.ofertas.map((oferta) => (
                        <option key={oferta.id} value={oferta.id}>
                          {oferta.referencia} · {oferta.oferente}
                        </option>
                      ))}
                </select>
              </FormField>
              <FormField
                label="Emisor"
                htmlFor="gar-emisor"
                required
                error={fieldErrors.emisor_id?.[0]}
              >
                <select
                  id="gar-emisor"
                  value={garEmisor}
                  onChange={(e) => setGarEmisor(e.target.value)}
                  className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                  required
                >
                  <option value="">Seleccione…</option>
                  {estado.emisores.map((emisor) => (
                    <option key={emisor.id} value={emisor.id}>
                      {emisor.nombre} · {emisor.tipo_etiqueta} · RIF {emisor.rif}
                    </option>
                  ))}
                </select>
              </FormField>
              <FormField
                label="Número del instrumento"
                htmlFor="gar-referencia"
                required
                error={fieldErrors.referencia_emisor?.[0]}
              >
                <input
                  id="gar-referencia"
                  value={garReferencia}
                  onChange={(e) => setGarReferencia(e.target.value)}
                  className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                  required
                />
              </FormField>
              <FormField label="Monto" htmlFor="gar-monto" required error={fieldErrors.monto?.[0]}>
                <input
                  id="gar-monto"
                  type="number"
                  step="0.01"
                  value={garMonto}
                  onChange={(e) => setGarMonto(e.target.value)}
                  className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                  required
                />
              </FormField>
              <FormField
                label="Moneda"
                htmlFor="gar-moneda"
                required
                error={fieldErrors.moneda?.[0]}
              >
                <select
                  id="gar-moneda"
                  value={garMoneda}
                  onChange={(e) => setGarMoneda(e.target.value)}
                  className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                  required
                >
                  <option value="">Seleccione…</option>
                  <option value="VES">VES</option>
                  <option value="USD">USD</option>
                  <option value="EUR">EUR</option>
                </select>
              </FormField>
              <FormField
                label="Fecha de emisión"
                htmlFor="gar-emision"
                required
                error={fieldErrors.fecha_emision?.[0]}
              >
                <input
                  id="gar-emision"
                  type="date"
                  value={garEmision}
                  onChange={(e) => setGarEmision(e.target.value)}
                  className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                  required
                />
              </FormField>
              <FormField
                label="Vigente desde"
                htmlFor="gar-desde"
                required
                error={fieldErrors.vigente_desde?.[0]}
              >
                <input
                  id="gar-desde"
                  type="date"
                  value={garDesde}
                  onChange={(e) => setGarDesde(e.target.value)}
                  className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                  required
                />
              </FormField>
              <FormField
                label="Vigente hasta"
                htmlFor="gar-hasta"
                required
                error={fieldErrors.vigente_hasta?.[0]}
              >
                <input
                  id="gar-hasta"
                  type="date"
                  value={garHasta}
                  onChange={(e) => setGarHasta(e.target.value)}
                  className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                  required
                />
              </FormField>
              <FormField
                label="Documento del instrumento"
                htmlFor="gar-documento"
                required
                error={fieldErrors.documento_id?.[0]}
              >
                <select
                  id="gar-documento"
                  value={garDocumento}
                  onChange={(e) => setGarDocumento(e.target.value)}
                  className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                  required
                >
                  <option value="">Seleccione…</option>
                  {estado.documentos.map((doc) => (
                    <option key={doc.id} value={doc.id}>
                      {doc.titulo} · versión {doc.version}
                    </option>
                  ))}
                </select>
              </FormField>
              <FormField
                label="Observación"
                htmlFor="gar-observacion"
                error={fieldErrors.observacion?.[0]}
              >
                <textarea
                  id="gar-observacion"
                  value={garObservacion}
                  onChange={(e) => setGarObservacion(e.target.value)}
                  className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                />
              </FormField>
              {errorGeneral ? (
                <p role="alert" className="mt-2 text-sm text-red-700">
                  {errorGeneral}
                </p>
              ) : null}
              <div className="mt-3 flex flex-wrap gap-2">
                <Button
                  variant="primary"
                  disabled={enviando}
                  onClick={() =>
                    void enviar(
                      `/gobierno/contrataciones/expedientes/${detalle.id}/garantias`,
                      {
                        requisito_id: garRequisito,
                        oferta_id: garOferta,
                        emisor_id: garEmisor,
                        referencia_emisor: garReferencia,
                        monto: garMonto,
                        moneda: garMoneda,
                        fecha_emision: garEmision,
                        vigente_desde: garDesde,
                        vigente_hasta: garHasta,
                        documento_id: garDocumento,
                        observacion: garObservacion || null,
                      },
                      "Garantía registrada",
                      true,
                    )
                  }
                >
                  {enviando ? "Registrando…" : "Registrar"}
                </Button>
                <Button variant="ghost" onClick={cerrarFormulario}>
                  Cancelar
                </Button>
              </div>
            </div>
          ) : (
            <Button variant="secondary" onClick={() => setFormulario({ tipo: "garantia" })}>
              Registrar garantía
            </Button>
          )}
        </div>
      ) : null}

      {estado.garantias.length === 0 ? (
        <p className="mt-2 text-sm text-text-900">No hay garantías registradas.</p>
      ) : (
        <div className="mt-2 space-y-3">
          {estado.garantias.map((garantia) => {
            const requisitoDeGarantia = estado.requisitos.find(
              (r) => r.id === garantia.requisito_id,
            );
            const abierta =
              formulario?.tipo === "accion" && formulario.garantiaId === garantia.id;
            return (
              <article
                key={garantia.id}
                aria-labelledby={`gar-${garantia.id}`}
                className="rounded-lg border border-border-subtle bg-white p-4"
              >
                <h4 id={`gar-${garantia.id}`} className="text-sm font-semibold text-text-900 break-words">
                  {garantia.referencia} · {garantia.tipo_etiqueta}{" "}
                  <span className="font-normal text-text-600">{garantia.estado_etiqueta}</span>
                </h4>
                <dl className="mt-2 space-y-1">
                  <div>
                    <dt className="text-sm text-text-600">Sujeto</dt>
                    <dd className="text-sm text-text-900 break-words">
                      {garantia.oferta} · {garantia.oferente}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm text-text-600">Etapa</dt>
                    <dd className="text-sm text-text-900">{garantia.etapa_etiqueta}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-text-600">Emisor</dt>
                    <dd className="text-sm text-text-900 break-words">
                      {garantia.emisor.nombre} ({garantia.emisor.tipo_etiqueta}), RIF{" "}
                      {garantia.emisor.rif}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm text-text-600">Número del instrumento</dt>
                    <dd className="text-sm text-text-900 break-words">
                      {garantia.referencia_emisor}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm text-text-600">Monto</dt>
                    <dd className="text-sm text-text-900">
                      {formatearMonto(garantia.monto, garantia.moneda)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm text-text-600">Vigencia</dt>
                    <dd className="text-sm text-text-900">
                      del {formatearFechaDeNegocio(garantia.vigente_desde)} al{" "}
                      {formatearFechaDeNegocio(garantia.vigente_hasta)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm text-text-600">Días restantes</dt>
                    <dd className="text-sm text-text-900">
                      {garantia.vigencia === "VENCIDA"
                        ? `Vencida hace ${-garantia.dias_restantes} días`
                        : garantia.dias_restantes}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm text-text-600">Estado de vigencia</dt>
                    <dd className="text-sm text-text-900">{garantia.vigencia_etiqueta}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-text-600">Documento</dt>
                    <dd className="text-sm text-text-900 break-words">
                      {garantia.documento.titulo}, versión {garantia.documento.version}
                    </dd>
                  </div>
                  {garantia.antecesor ? (
                    <div>
                      <dt className="text-sm text-text-600">Renueva o sustituye a</dt>
                      <dd className="text-sm text-text-900">{garantia.antecesor}</dd>
                    </div>
                  ) : null}
                  {garantia.sucesor ? (
                    <div>
                      <dt className="text-sm text-text-600">Reemplazada por</dt>
                      <dd className="text-sm text-text-900">{garantia.sucesor}</dd>
                    </div>
                  ) : null}
                </dl>
                {garantia.suficiencia ? (
                  <div className="mt-2">
                    <p className="text-sm font-semibold text-text-900">
                      Suficiencia: {garantia.suficiencia_etiqueta}
                    </p>
                    <ul aria-label="Criterios de suficiencia" className="mt-1 list-disc pl-5 text-sm text-text-900">
                      {garantia.criterios.map((criterio) => (
                        <li key={criterio.criterio} className="break-words">
                          {criterio.criterio}:{" "}
                          {criterio.resultado === "CUMPLE"
                            ? "Cumple"
                            : criterio.resultado === "NO_CUMPLE"
                              ? "No cumple"
                              : "No evaluable"}{" "}
                          — {criterio.detalle}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {garantia.vigencia === "POR_VENCER" ? (
                  <p className="mt-2 text-sm font-semibold text-amber-700">
                    Por vencer: quedan {garantia.dias_restantes} días.
                  </p>
                ) : null}
                {garantia.vigencia === "VENCIDA" ? (
                  <p className="mt-2 text-sm font-semibold text-red-700">Vencida.</p>
                ) : null}
                {garantia.suficiencia === "INSUFICIENTE" ? (
                  <p className="mt-2 text-sm font-semibold text-red-700">
                    Insuficiente: revise los criterios.
                  </p>
                ) : null}
                {garantia.suficiencia === "NO_EVALUABLE" ? (
                  <p className="mt-2 text-sm font-semibold text-amber-700">
                    No evaluable: falta un dato que la plataforma no registra.
                  </p>
                ) : null}

                {garantia.acciones.length > 0 ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {garantia.acciones.includes("RENOVAR") && puedeGestionar ? (
                      <Button
                        variant="secondary"
                        onClick={() =>
                          setFormulario({ tipo: "accion", garantiaId: garantia.id, accion: "RENOVAR" })
                        }
                      >
                        Renovar
                      </Button>
                    ) : null}
                    {garantia.acciones.includes("SUSTITUIR") && puedeGestionar ? (
                      <Button
                        variant="secondary"
                        onClick={() =>
                          setFormulario({ tipo: "accion", garantiaId: garantia.id, accion: "SUSTITUIR" })
                        }
                      >
                        Sustituir
                      </Button>
                    ) : null}
                    {garantia.acciones.includes("LIBERAR") && puedeLiberar ? (
                      <Button
                        variant="secondary"
                        onClick={() =>
                          setFormulario({ tipo: "accion", garantiaId: garantia.id, accion: "LIBERAR" })
                        }
                      >
                        Liberar
                      </Button>
                    ) : null}
                    {garantia.acciones.includes("EJECUTAR") && puedeEjecutar ? (
                      <Button
                        variant="danger"
                        onClick={() =>
                          setFormulario({ tipo: "accion", garantiaId: garantia.id, accion: "EJECUTAR" })
                        }
                      >
                        Ejecutar
                      </Button>
                    ) : null}
                  </div>
                ) : null}

                {abierta && formulario?.tipo === "accion" ? (
                  <div className="mt-3 rounded-lg border border-border-subtle bg-white p-4">
                    {formulario.accion === "RENOVAR" ? (
                      <>
                        <FormField
                          label="Nuevo vencimiento"
                          htmlFor={`ren-hasta-${garantia.id}`}
                          required
                          error={fieldErrors.vigente_hasta?.[0]}
                        >
                          <input
                            id={`ren-hasta-${garantia.id}`}
                            type="date"
                            value={accionHasta}
                            onChange={(e) => setAccionHasta(e.target.value)}
                            className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                            required
                          />
                        </FormField>
                        <FormField
                          label="Documento de la renovación"
                          htmlFor={`ren-documento-${garantia.id}`}
                          required
                          error={fieldErrors.documento_id?.[0]}
                        >
                          <select
                            id={`ren-documento-${garantia.id}`}
                            value={accionDocumento}
                            onChange={(e) => setAccionDocumento(e.target.value)}
                            className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                            required
                          >
                            <option value="">Seleccione…</option>
                            {estado.documentos.map((doc) => (
                              <option key={doc.id} value={doc.id}>
                                {doc.titulo} · versión {doc.version}
                              </option>
                            ))}
                          </select>
                        </FormField>
                        <FormField
                          label="Monto (opcional)"
                          htmlFor={`ren-monto-${garantia.id}`}
                          error={fieldErrors.monto?.[0]}
                        >
                          <input
                            id={`ren-monto-${garantia.id}`}
                            type="number"
                            step="0.01"
                            value={accionMonto}
                            onChange={(e) => setAccionMonto(e.target.value)}
                            className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                          />
                        </FormField>
                        <FormField
                          label="Motivo"
                          htmlFor={`ren-motivo-${garantia.id}`}
                          required
                          error={fieldErrors.motivo?.[0]}
                        >
                          <textarea
                            id={`ren-motivo-${garantia.id}`}
                            value={accionMotivo}
                            onChange={(e) => setAccionMotivo(e.target.value)}
                            className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                            required
                          />
                        </FormField>
                        {errorGeneral ? (
                          <p role="alert" className="mt-2 text-sm text-red-700">
                            {errorGeneral}
                          </p>
                        ) : null}
                        <div className="mt-3 flex flex-wrap gap-2">
                          <Button
                            variant="primary"
                            disabled={enviando}
                            onClick={() =>
                              void enviar(
                                `/gobierno/contrataciones/expedientes/${detalle.id}/garantias/${garantia.id}/renovar`,
                                {
                                  vigente_hasta: accionHasta,
                                  documento_id: accionDocumento,
                                  motivo: accionMotivo,
                                  monto: accionMonto || null,
                                },
                                "Garantía renovada",
                                true,
                              )
                            }
                          >
                            {enviando ? "Renovando…" : "Renovar garantía"}
                          </Button>
                          <Button variant="ghost" onClick={cerrarFormulario}>
                            Cancelar
                          </Button>
                        </div>
                      </>
                    ) : null}
                    {formulario.accion === "SUSTITUIR" ? (
                      <>
                        <FormField
                          label="Emisor"
                          htmlFor={`sus-emisor-${garantia.id}`}
                          required
                          error={fieldErrors.emisor_id?.[0]}
                        >
                          <select
                            id={`sus-emisor-${garantia.id}`}
                            value={accionEmisor}
                            onChange={(e) => setAccionEmisor(e.target.value)}
                            className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                            required
                          >
                            <option value="">Seleccione…</option>
                            {estado.emisores.map((emisor) => (
                              <option key={emisor.id} value={emisor.id}>
                                {emisor.nombre} · {emisor.tipo_etiqueta} · RIF {emisor.rif}
                              </option>
                            ))}
                          </select>
                        </FormField>
                        <FormField
                          label="Número del instrumento"
                          htmlFor={`sus-referencia-${garantia.id}`}
                          required
                          error={fieldErrors.referencia_emisor?.[0]}
                        >
                          <input
                            id={`sus-referencia-${garantia.id}`}
                            value={accionReferencia}
                            onChange={(e) => setAccionReferencia(e.target.value)}
                            className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                            required
                          />
                        </FormField>
                        <FormField
                          label="Monto"
                          htmlFor={`sus-monto-${garantia.id}`}
                          required
                          error={fieldErrors.monto?.[0]}
                        >
                          <input
                            id={`sus-monto-${garantia.id}`}
                            type="number"
                            step="0.01"
                            value={accionMonto}
                            onChange={(e) => setAccionMonto(e.target.value)}
                            className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                            required
                          />
                        </FormField>
                        <FormField
                          label="Moneda"
                          htmlFor={`sus-moneda-${garantia.id}`}
                          required
                          error={fieldErrors.moneda?.[0]}
                        >
                          <select
                            id={`sus-moneda-${garantia.id}`}
                            value={accionMoneda}
                            onChange={(e) => setAccionMoneda(e.target.value)}
                            className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                            required
                          >
                            <option value="">Seleccione…</option>
                            <option value="VES">VES</option>
                            <option value="USD">USD</option>
                            <option value="EUR">EUR</option>
                          </select>
                        </FormField>
                        <FormField
                          label="Fecha de emisión"
                          htmlFor={`sus-emision-${garantia.id}`}
                          required
                          error={fieldErrors.fecha_emision?.[0]}
                        >
                          <input
                            id={`sus-emision-${garantia.id}`}
                            type="date"
                            value={accionEmision}
                            onChange={(e) => setAccionEmision(e.target.value)}
                            className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                            required
                          />
                        </FormField>
                        <FormField
                          label="Vigente desde"
                          htmlFor={`sus-desde-${garantia.id}`}
                          required
                          error={fieldErrors.vigente_desde?.[0]}
                        >
                          <input
                            id={`sus-desde-${garantia.id}`}
                            type="date"
                            value={accionDesde}
                            onChange={(e) => setAccionDesde(e.target.value)}
                            className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                            required
                          />
                        </FormField>
                        <FormField
                          label="Vigente hasta"
                          htmlFor={`sus-hasta-${garantia.id}`}
                          required
                          error={fieldErrors.vigente_hasta?.[0]}
                        >
                          <input
                            id={`sus-hasta-${garantia.id}`}
                            type="date"
                            value={accionHasta}
                            onChange={(e) => setAccionHasta(e.target.value)}
                            className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                            required
                          />
                        </FormField>
                        <FormField
                          label="Documento del instrumento"
                          htmlFor={`sus-documento-${garantia.id}`}
                          required
                          error={fieldErrors.documento_id?.[0]}
                        >
                          <select
                            id={`sus-documento-${garantia.id}`}
                            value={accionDocumento}
                            onChange={(e) => setAccionDocumento(e.target.value)}
                            className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                            required
                          >
                            <option value="">Seleccione…</option>
                            {estado.documentos.map((doc) => (
                              <option key={doc.id} value={doc.id}>
                                {doc.titulo} · versión {doc.version}
                              </option>
                            ))}
                          </select>
                        </FormField>
                        <FormField
                          label="Motivo"
                          htmlFor={`sus-motivo-${garantia.id}`}
                          required
                          error={fieldErrors.motivo?.[0]}
                        >
                          <textarea
                            id={`sus-motivo-${garantia.id}`}
                            value={accionMotivo}
                            onChange={(e) => setAccionMotivo(e.target.value)}
                            className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                            required
                          />
                        </FormField>
                        {errorGeneral ? (
                          <p role="alert" className="mt-2 text-sm text-red-700">
                            {errorGeneral}
                          </p>
                        ) : null}
                        <div className="mt-3 flex flex-wrap gap-2">
                          <Button
                            variant="primary"
                            disabled={enviando}
                            onClick={() =>
                              void enviar(
                                `/gobierno/contrataciones/expedientes/${detalle.id}/garantias/${garantia.id}/sustituir`,
                                {
                                  emisor_id: accionEmisor,
                                  referencia_emisor: accionReferencia,
                                  monto: accionMonto,
                                  moneda: accionMoneda,
                                  fecha_emision: accionEmision,
                                  vigente_desde: accionDesde,
                                  vigente_hasta: accionHasta,
                                  documento_id: accionDocumento,
                                  motivo: accionMotivo,
                                },
                                "Garantía sustituida",
                                true,
                              )
                            }
                          >
                            {enviando ? "Sustituyendo…" : "Sustituir garantía"}
                          </Button>
                          <Button variant="ghost" onClick={cerrarFormulario}>
                            Cancelar
                          </Button>
                        </div>
                      </>
                    ) : null}
                    {formulario.accion === "LIBERAR" ? (
                      <>
                        <p className="text-sm text-text-900">
                          Condición legal: {requisitoDeGarantia?.regla.condicion_liberacion}
                        </p>
                        <FormField
                          label="Acto (DOC-02)"
                          htmlFor={`lib-acto-${garantia.id}`}
                          required
                          error={fieldErrors.acto_id?.[0]}
                        >
                          {estado.actos_elegibles.length > 0 ? (
                            <select
                              id={`lib-acto-${garantia.id}`}
                              value={accionActo}
                              onChange={(e) => setAccionActo(e.target.value)}
                              className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                              required
                            >
                              <option value="">Seleccione…</option>
                              {estado.actos_elegibles.map((acto) => (
                                <option key={acto.id} value={acto.id}>
                                  {acto.etiqueta} · {formatearFechaDeNegocio(acto.fecha)} ·{" "}
                                  {acto.asunto}
                                </option>
                              ))}
                            </select>
                          ) : (
                            <p className="text-sm text-text-900">
                              No hay actos elegibles.{" "}
                              <Link to="/gobierno/actos" className="text-brand-700 underline">
                                Ir a actos
                              </Link>
                            </p>
                          )}
                        </FormField>
                        <FormField
                          label="Motivo"
                          htmlFor={`lib-motivo-${garantia.id}`}
                          required
                          error={fieldErrors.motivo?.[0]}
                        >
                          <textarea
                            id={`lib-motivo-${garantia.id}`}
                            value={accionMotivo}
                            onChange={(e) => setAccionMotivo(e.target.value)}
                            className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                            required
                          />
                        </FormField>
                        <FormField
                          label="Documento soporte (opcional)"
                          htmlFor={`lib-documento-${garantia.id}`}
                          error={fieldErrors.documento_id?.[0]}
                        >
                          <select
                            id={`lib-documento-${garantia.id}`}
                            value={accionDocumento}
                            onChange={(e) => setAccionDocumento(e.target.value)}
                            className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                          >
                            <option value="">Seleccione…</option>
                            {estado.documentos.map((doc) => (
                              <option key={doc.id} value={doc.id}>
                                {doc.titulo} · versión {doc.version}
                              </option>
                            ))}
                          </select>
                        </FormField>
                        {confirmando ? (
                          <>
                            <p className="mt-3 text-sm text-text-900">
                              La liberación no se puede deshacer.
                            </p>
                            {errorGeneral ? (
                              <p role="alert" className="mt-2 text-sm text-red-700">
                                {errorGeneral}
                              </p>
                            ) : null}
                            <div className="mt-3 flex flex-wrap gap-2">
                              <Button
                                variant="primary"
                                disabled={enviando}
                                onClick={() =>
                                  void enviar(
                                    `/gobierno/contrataciones/expedientes/${detalle.id}/garantias/${garantia.id}/liberar`,
                                    {
                                      acto_id: accionActo,
                                      motivo: accionMotivo,
                                      documento_id: accionDocumento || null,
                                    },
                                    "Garantía liberada",
                                    true,
                                  )
                                }
                              >
                                {enviando ? "Liberando…" : "Confirmar liberación"}
                              </Button>
                              <Button variant="ghost" onClick={() => setConfirmando(false)}>
                                Cancelar
                              </Button>
                            </div>
                          </>
                        ) : (
                          <div className="mt-3 flex flex-wrap gap-2">
                            <Button variant="primary" onClick={() => setConfirmando(true)}>
                              Liberar garantía
                            </Button>
                            <Button variant="ghost" onClick={cerrarFormulario}>
                              Cancelar
                            </Button>
                          </div>
                        )}
                      </>
                    ) : null}
                    {formulario.accion === "EJECUTAR" ? (
                      <>
                        <p className="text-sm text-text-900">
                          Condición legal: {requisitoDeGarantia?.regla.condicion_ejecucion}
                        </p>
                        <FormField
                          label="Acto (DOC-02)"
                          htmlFor={`eje-acto-${garantia.id}`}
                          required
                          error={fieldErrors.acto_id?.[0]}
                        >
                          {estado.actos_elegibles.length > 0 ? (
                            <select
                              id={`eje-acto-${garantia.id}`}
                              value={accionActo}
                              onChange={(e) => setAccionActo(e.target.value)}
                              className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                              required
                            >
                              <option value="">Seleccione…</option>
                              {estado.actos_elegibles.map((acto) => (
                                <option key={acto.id} value={acto.id}>
                                  {acto.etiqueta} · {formatearFechaDeNegocio(acto.fecha)} ·{" "}
                                  {acto.asunto}
                                </option>
                              ))}
                            </select>
                          ) : (
                            <p className="text-sm text-text-900">
                              No hay actos elegibles.{" "}
                              <Link to="/gobierno/actos" className="text-brand-700 underline">
                                Ir a actos
                              </Link>
                            </p>
                          )}
                        </FormField>
                        <FormField
                          label="Motivo"
                          htmlFor={`eje-motivo-${garantia.id}`}
                          required
                          error={fieldErrors.motivo?.[0]}
                        >
                          <textarea
                            id={`eje-motivo-${garantia.id}`}
                            value={accionMotivo}
                            onChange={(e) => setAccionMotivo(e.target.value)}
                            className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                            required
                          />
                        </FormField>
                        <FormField
                          label="Monto ejecutado"
                          htmlFor={`eje-monto-${garantia.id}`}
                          required
                          error={fieldErrors.monto_ejecutado?.[0]}
                          help={`Hasta ${formatearMonto(garantia.monto, garantia.moneda)}`}
                        >
                          <input
                            id={`eje-monto-${garantia.id}`}
                            type="number"
                            step="0.01"
                            value={accionMonto}
                            onChange={(e) => setAccionMonto(e.target.value)}
                            className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                            required
                          />
                        </FormField>
                        <FormField
                          label="Documento soporte (opcional)"
                          htmlFor={`eje-documento-${garantia.id}`}
                          error={fieldErrors.documento_id?.[0]}
                        >
                          <select
                            id={`eje-documento-${garantia.id}`}
                            value={accionDocumento}
                            onChange={(e) => setAccionDocumento(e.target.value)}
                            className="w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                          >
                            <option value="">Seleccione…</option>
                            {estado.documentos.map((doc) => (
                              <option key={doc.id} value={doc.id}>
                                {doc.titulo} · versión {doc.version}
                              </option>
                            ))}
                          </select>
                        </FormField>
                        {confirmando ? (
                          <>
                            <p className="mt-3 text-sm text-text-900">
                              La ejecución no se puede deshacer.
                            </p>
                            {errorGeneral ? (
                              <p role="alert" className="mt-2 text-sm text-red-700">
                                {errorGeneral}
                              </p>
                            ) : null}
                            <div className="mt-3 flex flex-wrap gap-2">
                              <Button
                                variant="primary"
                                disabled={enviando}
                                onClick={() =>
                                  void enviar(
                                    `/gobierno/contrataciones/expedientes/${detalle.id}/garantias/${garantia.id}/ejecutar`,
                                    {
                                      acto_id: accionActo,
                                      motivo: accionMotivo,
                                      monto_ejecutado: accionMonto,
                                      documento_id: accionDocumento || null,
                                    },
                                    "Garantía ejecutada",
                                    true,
                                  )
                                }
                              >
                                {enviando ? "Ejecutando…" : "Confirmar ejecución"}
                              </Button>
                              <Button variant="ghost" onClick={() => setConfirmando(false)}>
                                Cancelar
                              </Button>
                            </div>
                          </>
                        ) : (
                          <div className="mt-3 flex flex-wrap gap-2">
                            <Button variant="primary" onClick={() => setConfirmando(true)}>
                              Ejecutar garantía
                            </Button>
                            <Button variant="ghost" onClick={cerrarFormulario}>
                              Cancelar
                            </Button>
                          </div>
                        )}
                      </>
                    ) : null}
                  </div>
                ) : null}

                {garantia.historial.length > 0 ? (
                  <details className="mt-3">
                    <summary className="cursor-pointer text-sm font-semibold text-text-900">
                      Historial ({garantia.historial.length})
                    </summary>
                    <ol className="mt-2 list-decimal pl-5 text-sm text-text-900">
                      {garantia.historial.map((evento) => (
                        <li key={evento.id} className="break-words">
                          {formatearFechaDeNegocio(evento.fecha)} · {evento.accion_etiqueta} ·{" "}
                          {evento.garantia}
                          {evento.nueva_garantia ? ` → ${evento.nueva_garantia}` : ""}
                          <div className="text-text-600">Por {evento.actor}</div>
                          {evento.motivo ? <div>Motivo: {evento.motivo}</div> : null}
                          {evento.documento ? (
                            <div>
                              Documento: {evento.documento.titulo}, versión{" "}
                              {evento.documento.version}
                            </div>
                          ) : null}
                          {evento.acto ? (
                            <div>
                              Acto:{" "}
                              <Link
                                to={`/gobierno/actos/${evento.acto.id}`}
                                className="text-brand-700 underline"
                              >
                                {evento.acto.etiqueta}
                              </Link>
                            </div>
                          ) : null}
                          {evento.monto && evento.moneda ? (
                            <div>Monto ejecutado: {formatearMonto(evento.monto, evento.moneda)}</div>
                          ) : null}
                          {evento.precondicion ? (
                            <div>
                              Precondición: {evento.precondicion_etiqueta}.{" "}
                              {evento.precondicion_detalle}
                            </div>
                          ) : null}
                        </li>
                      ))}
                    </ol>
                  </details>
                ) : null}
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
