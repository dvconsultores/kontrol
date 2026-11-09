import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { TextInput } from "@/components/TextInput";
import {
  formatearInstante,
  horaDeCaracasParaInput,
  instanteDesdeHoraDeCaracas,
} from "@/lib/fecha-de-negocio";
import { AdjuntosPanel } from "@/modules/documentos/AdjuntosPanel";
import type { DocumentSummary } from "@/modules/documentos/types";
import {
  CONSULTA_EXPEDIENTES,
  type ExpedienteDetalle,
  type ExpedienteOpciones,
} from "../api";

type OfertaResumen = {
  id: string;
  referencia: string;
  oferente_nombre: string;
  oferente_documento: string;
  identidad_etiqueta: string;
  representante: string | null;
  tipo_sobre: string;
  tipo_sobre_etiqueta: string;
  canal: string;
  canal_etiqueta: string;
  recibida_en: string;
  registrada_en: string;
  receptor: string;
  registrado_por: string | null;
  confidencial: boolean;
  confidencialidad_etiqueta: string;
  fundamento_confidencialidad: string;
  situacion: string;
  situacion_etiqueta: string;
  condicion_sobre: string | null;
  documentos_total: number;
  integridad: "VERIFICADA" | "ALTERADA" | "SIN_ARCHIVO";
};

type OfertaDetalle = OfertaResumen & {
  documentos: {
    version_numero: number;
    huella: string;
    integridad: "VERIFICADA" | "ALTERADA" | "SIN_ARCHIVO";
    documento_id: string | null;
    titulo: string | null;
  }[];
};

type OfertasListado = {
  items: OfertaResumen[];
  total: number;
  canales: { codigo: string; etiqueta: string }[];
  tipos_sobre: { codigo: string; etiqueta: string }[];
  recepcion_concluida_en: string | null;
  puede_recibir_sin_sello: boolean;
  aviso_identidad: string;
};

type DocumentoVinculado = DocumentSummary & {
  link: {
    id: string;
    role: string | null;
    is_frozen: boolean;
    frozen_version_id: string | null;
  };
};

const selectClass =
  "block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600";

function traducirIntegridad(codigo: string): string {
  if (codigo === "VERIFICADA") return "Integridad verificada";
  if (codigo === "ALTERADA") return "Integridad no verificada";
  return "Sobre físico sin archivo";
}

function TarjetaOferta({
  oferta,
  expedienteId,
  activeCompanyId,
}: {
  oferta: OfertaResumen;
  expedienteId: string;
  activeCompanyId: string | null;
}) {
  const [abierta, setAbierta] = useState(false);
  const detalleQuery = useQuery({
    queryKey: [
      ...CONSULTA_EXPEDIENTES,
      activeCompanyId,
      "ofertas",
      expedienteId,
      oferta.id,
    ],
    queryFn: () =>
      apiFetch<OfertaDetalle>(
        `/gobierno/contrataciones/expedientes/${expedienteId}/ofertas/${oferta.id}`,
      ),
    enabled: abierta,
  });

  return (
    <li className="rounded-lg border border-border-subtle bg-white p-4">
      <dl className="grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="min-w-0 break-words">
          <dt className="text-xs font-medium text-text-600">Referencia</dt>
          <dd className="text-sm font-semibold text-text-900">
            {oferta.referencia}
          </dd>
        </div>
        <div className="min-w-0 break-words">
          <dt className="text-xs font-medium text-text-600">Oferente</dt>
          <dd className="text-sm text-text-900">
            {oferta.oferente_nombre} · {oferta.oferente_documento}
          </dd>
        </div>
        <div className="min-w-0 break-words">
          <dt className="text-xs font-medium text-text-600">Identidad</dt>
          <dd className="text-sm text-text-900">{oferta.identidad_etiqueta}</dd>
        </div>
        <div className="min-w-0 break-words">
          <dt className="text-xs font-medium text-text-600">Tipo de sobre</dt>
          <dd className="text-sm text-text-900">{oferta.tipo_sobre_etiqueta}</dd>
        </div>
        <div className="min-w-0 break-words">
          <dt className="text-xs font-medium text-text-600">Canal</dt>
          <dd className="text-sm text-text-900">{oferta.canal_etiqueta}</dd>
        </div>
        <div className="min-w-0 break-words">
          <dt className="text-xs font-medium text-text-600">Recibida</dt>
          <dd className="text-sm text-text-900">
            {formatearInstante(oferta.recibida_en)}
          </dd>
        </div>
        <div className="min-w-0 break-words">
          <dt className="text-xs font-medium text-text-600">Receptor</dt>
          <dd className="text-sm text-text-900">{oferta.receptor}</dd>
        </div>
        {oferta.registrado_por && (
          <div className="min-w-0 break-words">
            <dt className="text-xs font-medium text-text-600">Registrada por</dt>
            <dd className="text-sm text-text-900">{oferta.registrado_por}</dd>
          </div>
        )}
        <div className="min-w-0 break-words">
          <dt className="text-xs font-medium text-text-600">Confidencialidad</dt>
          <dd className="text-sm text-text-900">
            {oferta.confidencialidad_etiqueta}
          </dd>
        </div>
        <div className="min-w-0 break-words">
          <dt className="text-xs font-medium text-text-600">Integridad</dt>
          <dd
            className={`text-sm ${
              oferta.integridad === "ALTERADA"
                ? "font-semibold text-red-700"
                : "text-text-900"
            }`}
          >
            {traducirIntegridad(oferta.integridad)}
          </dd>
        </div>
        <div className="min-w-0 break-words">
          <dt className="text-xs font-medium text-text-600">Situación</dt>
          <dd className="text-sm text-text-900">{oferta.situacion_etiqueta}</dd>
        </div>
        <div className="min-w-0 break-words">
          <dt className="text-xs font-medium text-text-600">Documentos</dt>
          <dd className="text-sm text-text-900">{oferta.documentos_total}</dd>
        </div>
      </dl>
      <div className="mt-3 flex flex-wrap gap-2">
        <Button
          variant="secondary"
          type="button"
          onClick={() => setAbierta(!abierta)}
          aria-label={`${abierta ? "Ocultar detalle" : "Ver detalle"} de ${oferta.referencia}`}
        >
          {abierta ? "Ocultar detalle" : "Ver detalle"}
        </Button>
      </div>
      {abierta && detalleQuery.data && (
        <div className="mt-4 border-t border-border-subtle pt-4">
          <dl className="grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="min-w-0 break-words">
              <dt className="text-xs font-medium text-text-600">
                Fundamento de confidencialidad
              </dt>
              <dd className="text-sm text-text-900">
                {detalleQuery.data.fundamento_confidencialidad}
              </dd>
            </div>
            {detalleQuery.data.condicion_sobre && (
              <div className="min-w-0 break-words">
                <dt className="text-xs font-medium text-text-600">
                  Condición del sobre
                </dt>
                <dd className="text-sm text-text-900">
                  {detalleQuery.data.condicion_sobre}
                </dd>
              </div>
            )}
          </dl>
          <h3 className="mt-4 text-sm font-semibold text-text-900">
            Documentos de la oferta
          </h3>
          <ul className="mt-2 space-y-2">
            {detalleQuery.data.documentos.map((doc) => (
              <li key={`${doc.documento_id ?? "sin"}-${doc.version_numero}`} className="text-sm text-text-900">
                {doc.titulo ?? "Contenido sellado hasta la apertura"}
                {doc.version_numero > 0 && (
                  <span className="text-text-600"> · Versión {doc.version_numero}</span>
                )}
                {doc.titulo && (
                  <span className="ml-2 text-xs text-text-600 break-all">
                    Huella: {doc.huella}
                  </span>
                )}
                <span className="ml-2 text-xs text-text-600">
                  {traducirIntegridad(doc.integridad)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </li>
  );
}

function FormularioOferta({
  expedienteId,
  detalle,
  opciones,
  listado,
  activeCompanyId,
  onCancelar,
  onAviso,
}: {
  expedienteId: string;
  detalle: ExpedienteDetalle;
  opciones: ExpedienteOpciones;
  listado: OfertasListado;
  activeCompanyId: string | null;
  onCancelar: () => void;
  onAviso: (texto: string) => void;
}) {
  const { notify } = useNotifications();
  const queryClient = useQueryClient();
  const { tiene } = useAutoridad();
  const [enviando, setEnviando] = useState(false);
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null);
  const [erroresCampos, setErroresCampos] = useState<Record<string, string[]>>({});
  const [form, setForm] = useState({
    oferente_nombre: "",
    oferente_documento: "",
    representante: "",
    tipo_sobre: "",
    canal: "",
    recibida_en: horaDeCaracasParaInput(),
    funcionario_id: "",
    condicion_sobre: "",
    confidencial: true,
    motivo_sin_sello: "",
    documento_ids: [] as string[],
  });

  const documentosQuery = useQuery({
    queryKey: ["documentos", "por-recurso", "GovernmentProcurementFile", expedienteId],
    queryFn: () =>
      apiFetch<DocumentoVinculado[]>(
        `/documentos/por-recurso/GovernmentProcurementFile/${expedienteId}`,
      ),
    enabled: tiene("documentos:view", "empresa"),
  });

  const setCampo = (campo: string, valor: string | boolean | string[]) => {
    setForm((prev) => ({ ...prev, [campo]: valor }));
  };

  const enviar = async () => {
    setEnviando(true);
    setErrorGeneral(null);
    setErroresCampos({});

    const recibida = instanteDesdeHoraDeCaracas(form.recibida_en);
    if (!recibida) {
      setErroresCampos({ recibida_en: ["La fecha debe tener un valor válido"] });
      setEnviando(false);
      return;
    }

    try {
      const respuesta = await apiFetch<OfertaDetalle>(
        `/gobierno/contrataciones/expedientes/${expedienteId}/ofertas`,
        {
          method: "POST",
          body: {
            oferente_nombre: form.oferente_nombre,
            oferente_documento: form.oferente_documento,
            representante: form.representante || null,
            tipo_sobre: form.tipo_sobre,
            canal: form.canal,
            recibida_en: recibida,
            funcionario_id: form.funcionario_id,
            condicion_sobre: form.condicion_sobre || null,
            confidencial: form.confidencial,
            motivo_sin_sello: form.motivo_sin_sello || null,
            documento_ids: form.documento_ids,
          },
          ifMatch: String(detalle.version),
        },
      );
      onAviso(
        `Oferta ${respuesta.referencia} registrada. Siguiente paso: pendiente de apertura.`,
      );
      notify({ type: "success", title: "Oferta registrada" });
      queryClient.invalidateQueries({ queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId] });
      queryClient.invalidateQueries({ queryKey: ["documentos"] });
      onCancelar();
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.code === "GOV_PROCUREMENT_FILE_STALE") {
          setErrorGeneral("El expediente cambió; recárguelo");
          queryClient.invalidateQueries({ queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId] });
        } else if (err.fieldErrors && Object.keys(err.fieldErrors).length > 0) {
          setErroresCampos(err.fieldErrors);
        } else {
          setErrorGeneral(err.message || "No fue posible registrar la oferta");
        }
      } else {
        setErrorGeneral("No fue posible registrar la oferta");
      }
    } finally {
      setEnviando(false);
    }
  };

  const errorDocumentos = erroresCampos.documento_ids?.join(", ");
  const errorComision = erroresCampos.comision?.join(", ");
  const errorConfidencial = erroresCampos.confidencial?.join(", ");
  const errorSinControl =
    errorGeneral || errorComision || errorConfidencial;

  return (
    <div className="mt-4 rounded-lg border border-border-subtle bg-white p-4">
      <h3 className="text-base font-semibold text-text-900">Recibir oferta</h3>

      {errorSinControl && (
        <p role="alert" className="mt-2 text-sm text-red-700">
          {errorSinControl}
        </p>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void enviar();
        }}
        className="mt-4 grid min-w-0 grid-cols-1 gap-4 sm:grid-cols-2"
      >
        <FormField
          label="Oferente"
          htmlFor="oferente_nombre"
          required
          error={erroresCampos.oferente_nombre?.[0]}
        >
          <TextInput
            id="oferente_nombre"
            value={form.oferente_nombre}
            onChange={(e) => setCampo("oferente_nombre", e.target.value)}
          />
        </FormField>
        <FormField
          label="Documento del oferente"
          htmlFor="oferente_documento"
          required
          help="Declarado por el oferente"
          error={erroresCampos.oferente_documento?.[0]}
        >
          <TextInput
            id="oferente_documento"
            value={form.oferente_documento}
            onChange={(e) => setCampo("oferente_documento", e.target.value)}
          />
        </FormField>
        <FormField
          label="Representante"
          htmlFor="representante"
          error={erroresCampos.representante?.[0]}
        >
          <TextInput
            id="representante"
            value={form.representante}
            onChange={(e) => setCampo("representante", e.target.value)}
          />
        </FormField>
        <FormField
          label="Tipo de sobre"
          htmlFor="tipo_sobre"
          required
          error={erroresCampos.tipo_sobre?.[0]}
        >
          <select
            id="tipo_sobre"
            className={selectClass}
            value={form.tipo_sobre}
            onChange={(e) => setCampo("tipo_sobre", e.target.value)}
          >
            <option value="">Seleccione</option>
            {listado.tipos_sobre.map((t) => (
              <option key={t.codigo} value={t.codigo}>
                {t.etiqueta}
              </option>
            ))}
          </select>
        </FormField>
        <FormField
          label="Canal"
          htmlFor="canal"
          required
          error={erroresCampos.canal?.[0]}
        >
          <select
            id="canal"
            className={selectClass}
            value={form.canal}
            onChange={(e) => setCampo("canal", e.target.value)}
          >
            <option value="">Seleccione</option>
            {listado.canales.map((c) => (
              <option key={c.codigo} value={c.codigo}>
                {c.etiqueta}
              </option>
            ))}
          </select>
        </FormField>
        <FormField
          label="Fecha y hora de recepción"
          htmlFor="recibida_en"
          required
          error={erroresCampos.recibida_en?.[0]}
        >
          <TextInput
            id="recibida_en"
            type="datetime-local"
            value={form.recibida_en}
            onChange={(e) => setCampo("recibida_en", e.target.value)}
          />
        </FormField>
        <FormField
          label="Funcionario receptor"
          htmlFor="funcionario_id"
          required
          error={erroresCampos.funcionario_id?.[0]}
        >
          <select
            id="funcionario_id"
            className={selectClass}
            value={form.funcionario_id}
            onChange={(e) => setCampo("funcionario_id", e.target.value)}
          >
            <option value="">Seleccione</option>
            {opciones.funcionarios.map((f) => (
              <option key={f.id} value={f.id}>
                {f.nombre}
                {f.cargos.length > 0 ? ` · ${f.cargos.join(", ")}` : ""}
              </option>
            ))}
          </select>
        </FormField>
        <FormField
          label="Condición del sobre"
          htmlFor="condicion_sobre"
          help="Obligatoria si es un sobre físico sin archivo"
          error={erroresCampos.condicion_sobre?.[0]}
        >
          <TextInput
            id="condicion_sobre"
            value={form.condicion_sobre}
            onChange={(e) => setCampo("condicion_sobre", e.target.value)}
          />
        </FormField>
        <fieldset className="sm:col-span-2">
          <legend className="text-sm font-medium text-text-900">
            Documentos de la oferta
          </legend>
          {errorDocumentos && (
            <p role="alert" className="mt-1 text-sm text-red-700">
              {errorDocumentos}
            </p>
          )}
          <div className="mt-2 space-y-2">
            {documentosQuery.data?.filter((d) => !d.link.is_frozen).length === 0 && (
              <p className="text-sm text-text-600">
                No hay documentos disponibles en el expediente.
              </p>
            )}
            {documentosQuery.data
              ?.filter((d) => !d.link.is_frozen)
              .map((doc) => (
                <label key={doc.id} className="flex items-start gap-2 text-sm text-text-900">
                  <input
                    type="checkbox"
                    checked={form.documento_ids.includes(doc.id)}
                    onChange={(e) => {
                      const ids = e.target.checked
                        ? [...form.documento_ids, doc.id]
                        : form.documento_ids.filter((id) => id !== doc.id);
                      setCampo("documento_ids", ids);
                    }}
                  />
                  <span className="min-w-0 break-words">{doc.title}</span>
                </label>
              ))}
          </div>
          {tiene("gobierno_expedientes:manage", "empresa") && (
            <div className="mt-4">
              <AdjuntosPanel
                resourceType="GovernmentProcurementFile"
                resourceId={expedienteId}
                title="Cargar documento de la oferta"
                onChange={() => {
                  queryClient.invalidateQueries({ queryKey: ["documentos"] });
                  queryClient.invalidateQueries({
                    queryKey: [
                      "documentos",
                      "por-recurso",
                      "GovernmentProcurementFile",
                      expedienteId,
                    ],
                  });
                }}
              />
            </div>
          )}
        </fieldset>
        <div className="sm:col-span-2">
          {!listado.puede_recibir_sin_sello ? (
            <p className="text-sm text-text-900">
              Esta oferta quedará sellada hasta la apertura
            </p>
          ) : (
            <>
              <label className="flex items-start gap-2 text-sm text-text-900">
                <input
                  type="checkbox"
                  checked={form.confidencial}
                  onChange={(e) => setCampo("confidencial", e.target.checked)}
                />
                <span>Sellar hasta la apertura</span>
              </label>
              {!form.confidencial && (
                <FormField
                  label="Motivo para no sellar"
                  htmlFor="motivo_sin_sello"
                  required
                  error={erroresCampos.motivo_sin_sello?.[0]}
                >
                  <TextInput
                    id="motivo_sin_sello"
                    value={form.motivo_sin_sello}
                    onChange={(e) => setCampo("motivo_sin_sello", e.target.value)}
                  />
                </FormField>
              )}
            </>
          )}
          {form.confidencial && form.documento_ids.length > 0 && (
            <p className="mt-2 text-sm text-amber-700">
              Al guardar, los documentos marcados quedan sellados: nadie podrá
              consultarlos hasta la apertura.
            </p>
          )}
        </div>
        <div className="flex flex-wrap gap-2 sm:col-span-2">
          <Button variant="primary" type="submit" disabled={enviando}>
            Guardar
          </Button>
          <Button variant="secondary" type="button" onClick={onCancelar}>
            Cancelar
          </Button>
        </div>
      </form>
    </div>
  );
}

export function SeccionOfertas({
  detalle,
  opciones,
  activeCompanyId,
}: {
  detalle: ExpedienteDetalle;
  opciones: ExpedienteOpciones | undefined;
  activeCompanyId: string | null;
}) {
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();
  const [formularioAbierto, setFormularioAbierto] = useState(false);
  const [concluirAbierto, setConcluirAbierto] = useState(false);
  const [motivoConclusion, setMotivoConclusion] = useState("");
  const [enviandoConclusion, setEnviandoConclusion] = useState(false);
  const [errorConclusion, setErrorConclusion] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  const puedeVer = tiene("gobierno_ofertas:view", "empresa");
  const puedeRecibir = tiene("gobierno_ofertas:receive", "empresa");

  const listadoQuery = useQuery({
    queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId, "ofertas", detalle.id],
    queryFn: () =>
      apiFetch<OfertasListado>(
        `/gobierno/contrataciones/expedientes/${detalle.id}/ofertas`,
      ),
    enabled: !!puedeVer,
  });

  if (!puedeVer) return null;

  const listado = listadoQuery.data;
  const puedeMostrarFormulario =
    puedeRecibir && detalle.status === "ABIERTO" && !listado?.recepcion_concluida_en;

  const concluir = async () => {
    setEnviandoConclusion(true);
    setErrorConclusion(null);
    try {
      await apiFetch<{
        recepcion_concluida_en: string;
        version: number;
      }>(`/gobierno/contrataciones/expedientes/${detalle.id}/ofertas/concluir`, {
        method: "POST",
        body: { motivo: motivoConclusion || null },
        ifMatch: String(detalle.version),
      });
      notify({ type: "success", title: "Recepción concluida" });
      queryClient.invalidateQueries({ queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId] });
      setConcluirAbierto(false);
      setMotivoConclusion("");
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.code === "GOV_PROCUREMENT_FILE_STALE") {
          setErrorConclusion("El expediente cambió; recárguelo");
          queryClient.invalidateQueries({ queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId] });
        } else {
          setErrorConclusion(err.message || "No fue posible concluir la recepción");
        }
      } else {
        setErrorConclusion("No fue posible concluir la recepción");
      }
    } finally {
      setEnviandoConclusion(false);
    }
  };

  return (
    <section aria-labelledby="sec-ofertas" className="mt-6">
      <h2 id="sec-ofertas" className="text-lg font-semibold text-text-900">
        Ofertas
      </h2>
      {listadoQuery.isLoading && <LoadingState />}
      {listadoQuery.isError && (
        <p role="alert" className="mt-2 text-sm text-red-700">
          No fue posible cargar las ofertas
        </p>
      )}
      {listado && (
        <>
          {listado.aviso_identidad && (
            <p className="mt-2 text-sm text-text-700">{listado.aviso_identidad}</p>
          )}
          {listado.recepcion_concluida_en && (
            <p className="mt-2 text-sm font-medium text-text-900">
              Recepción concluida · {formatearInstante(listado.recepcion_concluida_en)}
            </p>
          )}
          <div className="mt-3 flex flex-wrap gap-2">
            {puedeMostrarFormulario && (
              <Button
                variant="primary"
                type="button"
                onClick={() => {
                  setAviso(null);
                  setFormularioAbierto(true);
                }}
              >
                Recibir oferta
              </Button>
            )}
            {!listado.recepcion_concluida_en && puedeRecibir && (
              <Button
                variant="secondary"
                type="button"
                onClick={() => setConcluirAbierto(true)}
              >
                Concluir recepción
              </Button>
            )}
          </div>
          {concluirAbierto && (
            <div className="mt-4 rounded-lg border border-border-subtle bg-white p-4">
              <h3 className="text-base font-semibold text-text-900">
                Concluir recepción
              </h3>
              {errorConclusion && (
                <p role="alert" className="mt-2 text-sm text-red-700">
                  {errorConclusion}
                </p>
              )}
              <FormField label="Motivo" htmlFor="motivo_conclusion">
                <TextInput
                  id="motivo_conclusion"
                  value={motivoConclusion}
                  onChange={(e) => setMotivoConclusion(e.target.value)}
                />
              </FormField>
              <div className="mt-3 flex flex-wrap gap-2">
                <Button
                  variant="primary"
                  type="button"
                  disabled={enviandoConclusion}
                  onClick={() => void concluir()}
                >
                  Confirmar conclusión
                </Button>
                <Button
                  variant="secondary"
                  type="button"
                  onClick={() => setConcluirAbierto(false)}
                >
                  Cancelar
                </Button>
              </div>
            </div>
          )}
          {listado.total === 0 && !formularioAbierto && (
            <EmptyState title="Sin ofertas recibidas" />
          )}
          {formularioAbierto && opciones && (
            <FormularioOferta
              expedienteId={detalle.id}
              detalle={detalle}
              opciones={opciones}
              listado={listado}
              activeCompanyId={activeCompanyId}
              onCancelar={() => {
                setFormularioAbierto(false);
              }}
              onAviso={setAviso}
            />
          )}
          {aviso && (
            <p role="status" className="mt-2 text-sm text-green-700">
              {aviso}
            </p>
          )}
          {listado.items.length > 0 && (
            <ul className="mt-4 space-y-3">
              {listado.items.map((oferta) => (
                <TarjetaOferta
                  key={oferta.id}
                  oferta={oferta}
                  expedienteId={detalle.id}
                  activeCompanyId={activeCompanyId}
                />
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}
