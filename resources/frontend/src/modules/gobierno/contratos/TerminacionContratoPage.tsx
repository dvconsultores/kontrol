import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { descargarArchivo } from "@/api/descargas";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { Button } from "@/components/Button";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { EmptyState } from "@/components/EmptyState";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { PageHeader } from "@/components/PageHeader";
import { PageContent } from "@/layout/PageContent";
import { ErrorDeCarga } from "@/modules/gobierno/ocupacion/ErrorDeCarga";
import { formatearFechaDeNegocio, formatearInstante } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_CONTRATOS,
  rutaContrato,
  rutaTerminacion,
  type VistaTerminacion,
} from "./api";

function abreviarHuella(huella: string, cantidad = 12): string {
  return huella.length > cantidad ? `${huella.slice(0, cantidad)}…` : huella;
}

const MONEDA = (v: { moneda: string }) => v.moneda;

export function TerminacionContratoPage() {
  const { contratoId } = useParams<{ contratoId: string }>();
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const queryClient = useQueryClient();

  const [figura, setFigura] = useState("");
  const [formulario, setFormulario] = useState<Record<string, string>>({});
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [modalFormalizar, setModalFormalizar] = useState(false);
  const [errorFormalizar, setErrorFormalizar] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);
  const [filtroFigura, setFiltroFigura] = useState("");
  const [filtroDesde, setFiltroDesde] = useState("");
  const [filtroHasta, setFiltroHasta] = useState("");

  const permisos = {
    vista: tiene("gobierno_contratos:view", "empresa"),
    terminar: tiene("gobierno_contratos:terminate", "empresa"),
  };

  const consulta = useQuery({
    queryKey: [...CONSULTA_CONTRATOS, activeCompanyId, contratoId, "terminacion"],
    queryFn: () => apiFetch<VistaTerminacion>(rutaTerminacion(contratoId ?? "")),
    enabled: Boolean(contratoId) && permisos.vista,
  });

  const vista = consulta.data;

  function actualizarVista(respuesta: VistaTerminacion, mensaje?: string) {
    queryClient.setQueryData([...CONSULTA_CONTRATOS, activeCompanyId, contratoId, "terminacion"], respuesta);
    if (mensaje) setAviso(mensaje);
  }

  async function preparar(event: FormEvent) {
    event.preventDefault();
    if (!figura || !contratoId) return;
    setGuardando(true);
    setErrorGeneral(null);
    try {
      const respuesta = await apiFetch<VistaTerminacion>(rutaTerminacion(contratoId), {
        method: "POST",
        body: { figura },
      });
      setFigura("");
      actualizarVista(respuesta);
    } catch (error) {
      setErrorGeneral(error instanceof ApiError ? error.message : "No se pudo preparar la actuación.");
    } finally {
      setGuardando(false);
    }
  }

  async function guardarBorrador(event: FormEvent) {
    event.preventDefault();
    if (!contratoId || !vista?.borrador) return;
    setGuardando(true);
    setErrorGeneral(null);
    const cuerpo: Record<string, string | null> = {};
    for (const clave of Object.keys(formulario)) {
      cuerpo[clave] = formulario[clave] === "" ? null : formulario[clave];
    }
    try {
      const respuesta = await apiFetch<VistaTerminacion>(`${rutaTerminacion(contratoId)}/borrador`, {
        method: "PATCH",
        body: cuerpo,
        ifMatch: String(vista.borrador.version),
      });
      actualizarVista(respuesta);
    } catch (error) {
      setErrorGeneral(error instanceof ApiError ? error.message : "No se pudo guardar el borrador.");
    } finally {
      setGuardando(false);
    }
  }

  async function descartarBorrador() {
    if (!contratoId || !vista?.borrador) return;
    setGuardando(true);
    setErrorGeneral(null);
    try {
      await apiFetch<void>(`${rutaTerminacion(contratoId)}/borrador`, {
        method: "DELETE",
        ifMatch: String(vista.borrador.version),
      });
      setFormulario({});
      const respuesta = await apiFetch<VistaTerminacion>(rutaTerminacion(contratoId));
      actualizarVista(respuesta);
    } catch (error) {
      setErrorGeneral(error instanceof ApiError ? error.message : "No se pudo descartar el borrador.");
    } finally {
      setGuardando(false);
    }
  }

  async function formalizar() {
    if (!contratoId || !vista?.borrador) return;
    setGuardando(true);
    setErrorFormalizar(null);
    try {
      const respuesta = await apiFetch<VistaTerminacion>(`${rutaTerminacion(contratoId)}/formalizar`, {
        method: "POST",
        ifMatch: String(vista.borrador.version),
      });
      setModalFormalizar(false);
      setErrorFormalizar(null);
      actualizarVista(respuesta, `Formalizada: ${respuesta.formalizada?.codigo ?? ""}`);
    } catch (error) {
      setModalFormalizar(false);
      setErrorFormalizar(error instanceof ApiError ? error.message : "No se pudo formalizar.");
    } finally {
      setGuardando(false);
    }
  }

  async function descargarCsv() {
    const parametros = new URLSearchParams();
    if (filtroFigura) parametros.set("figura", filtroFigura);
    if (filtroDesde) parametros.set("desde", filtroDesde);
    if (filtroHasta) parametros.set("hasta", filtroHasta);
    const query = parametros.toString();
    await descargarArchivo(
      `/gobierno/contratos/terminaciones/reporte.csv${query ? `?${query}` : ""}`,
      "terminaciones-contractuales.csv",
    );
  }

  if (consulta.isLoading) {
    return <LoadingState label="Cargando la terminación del contrato…" />;
  }

  if (consulta.isError) {
    const error = consulta.error;
    if (error instanceof ApiError && error.status === 404) {
      return (
        <EmptyState
          title="Contrato no encontrado"
          description="El contrato solicitado no existe o no está disponible."
        />
      );
    }
    if (error instanceof ApiError && error.status === 409) {
      return (
        <EmptyState
          title="Contrato no formalizado"
          description="Solo un contrato formalizado admite terminación, resolución o rescisión"
        />
      );
    }
    return <ErrorDeCarga message={error instanceof Error ? error.message : "No se pudo cargar la terminación del contrato."} />;
  }

  if (!vista) {
    return <EmptyState title="Contrato no encontrado" description="El contrato solicitado no existe o no está disponible." />;
  }

  const figuraBorrador = vista.borrador?.figura;
  const figuraCatalogo = vista.catalogo.figuras.find((f) => f.codigo === figuraBorrador);
  const actoElegido = vista.opciones.actos.find((a) => a.id === formulario.act_id);
  const requisitosCumplidos = vista.requisitos.every((r) => r.cumplido);

  return (
    <PageContent>
      <PageHeader
        title="Terminación, resolución o rescisión"
        crumbs={[
          { label: "Gobierno", to: "/gobierno" },
          { label: "Contratos y órdenes", to: "/gobierno/contratos" },
          { label: vista.contrato.codigo, to: rutaContrato(vista.contrato.id) },
        ]}
      />

      {aviso ? (
        <div role="status" className="mb-4 rounded border border-green-300 bg-green-50 p-3 text-sm text-green-800">
          {aviso}
        </div>
      ) : null}

      {errorGeneral ? (
        <div role="alert" className="mb-4 rounded border border-red-300 bg-red-50 p-3 text-sm text-red-800">
          {errorGeneral}
        </div>
      ) : null}

      <section aria-labelledby="situacion-titulo" className="mb-6">
        <h2 id="situacion-titulo" className="text-lg font-semibold text-text-900">
          Situación actual
        </h2>
        <dl className="mt-2 grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="font-medium text-text-600">Estado</dt>
            <dd className="text-text-900">{vista.situacion.estado_etiqueta}</dd>
          </div>
          {vista.situacion.figura_etiqueta ? (
            <div>
              <dt className="font-medium text-text-600">Figura</dt>
              <dd className="text-text-900">{vista.situacion.figura_etiqueta}</dd>
            </div>
          ) : null}
          {vista.situacion.fecha_eficacia ? (
            <div>
              <dt className="font-medium text-text-600">Eficaz desde</dt>
              <dd className="text-text-900">{formatearFechaDeNegocio(vista.situacion.fecha_eficacia)}</dd>
            </div>
          ) : null}
          {vista.situacion.fecha_limite_ejecucion ? (
            <div>
              <dt className="font-medium text-text-600">Hechos de ejecución admitidos hasta</dt>
              <dd className="text-text-900">{formatearFechaDeNegocio(vista.situacion.fecha_limite_ejecucion)}</dd>
            </div>
          ) : null}
        </dl>
        {vista.situacion.cumplimiento_cnt03 ? (
          <p className="mt-2 text-sm text-text-900">
            El contrato cerró por cumplimiento en CNT-03 (LCP art. 145.1).
          </p>
        ) : null}
        {vista.situacion.alerta_acto_base ? (
          <div role="alert" className="mt-3 rounded border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
            <p>{vista.situacion.alerta_acto_base.mensaje}</p>
            <Link
              to={vista.situacion.alerta_acto_base.enlace}
              className="mt-1 inline-block font-medium text-primary-600 hover:underline"
            >
              Ver el acto
            </Link>
          </div>
        ) : null}
      </section>

      {vista.formalizada ? (
        <section aria-labelledby="formalizada-titulo" className="mb-6">
          <h2 id="formalizada-titulo" className="text-lg font-semibold text-text-900">
            Actuación formalizada
          </h2>
          <div className="mt-2 text-sm text-text-900">
            <dl className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              <div>
                <dt className="font-medium text-text-600">Código</dt>
                <dd>{vista.formalizada.codigo ?? "—"}</dd>
              </div>
              <div>
                <dt className="font-medium text-text-600">Figura</dt>
                <dd>{vista.formalizada.figura_etiqueta ?? "—"}</dd>
              </div>
              {vista.formalizada.causal_etiqueta ? (
                <div>
                  <dt className="font-medium text-text-600">Causal</dt>
                  <dd>
                    {vista.formalizada.causal_etiqueta}
                    {vista.formalizada.causal_referencia ? ` · ${vista.formalizada.causal_referencia}` : ""}
                  </dd>
                </div>
              ) : null}
              {vista.formalizada.hechos ? (
                <div>
                  <dt className="font-medium text-text-600">Hechos</dt>
                  <dd>{vista.formalizada.hechos}</dd>
                </div>
              ) : null}
              {vista.formalizada.fundamento ? (
                <div>
                  <dt className="font-medium text-text-600">Fundamento jurídico</dt>
                  <dd>{vista.formalizada.fundamento}</dd>
                </div>
              ) : null}
              {vista.formalizada.acto ? (
                <div>
                  <dt className="font-medium text-text-600">Acto decisorio</dt>
                  <dd>
                    <Link to={vista.formalizada.acto.enlace} className="text-primary-600 hover:underline">
                      {vista.formalizada.acto.etiqueta}
                    </Link>
                  </dd>
                </div>
              ) : null}
              {vista.formalizada.apertura ? (
                <div>
                  <dt className="font-medium text-text-600">Apertura del procedimiento</dt>
                  <dd>
                    <Link to={vista.formalizada.apertura.enlace} className="text-primary-600 hover:underline">
                      {vista.formalizada.apertura.etiqueta}
                    </Link>
                  </dd>
                </div>
              ) : null}
              {vista.formalizada.documento ? (
                <div>
                  <dt className="font-medium text-text-600">Documento del acuerdo</dt>
                  <dd>{vista.formalizada.documento.titulo}</dd>
                </div>
              ) : null}
              {vista.formalizada.conclusion ? (
                <div>
                  <dt className="font-medium text-text-600">Conclusión autorizada</dt>
                  <dd>
                    {vista.formalizada.conclusion.alcance}
                    {vista.formalizada.conclusion.hasta ? ` · hasta ${vista.formalizada.conclusion.hasta}` : ""}
                  </dd>
                </div>
              ) : null}
              {vista.formalizada.fecha_acto ? (
                <div>
                  <dt className="font-medium text-text-600">Fecha del acto</dt>
                  <dd>{formatearFechaDeNegocio(vista.formalizada.fecha_acto)}</dd>
                </div>
              ) : null}
              {vista.formalizada.fecha_eficacia ? (
                <div>
                  <dt className="font-medium text-text-600">Fecha de eficacia</dt>
                  <dd>{formatearFechaDeNegocio(vista.formalizada.fecha_eficacia)}</dd>
                </div>
              ) : null}
              {vista.formalizada.formalizado_en ? (
                <div>
                  <dt className="font-medium text-text-600">Registrado</dt>
                  <dd>{formatearInstante(vista.formalizada.formalizado_en)}</dd>
                </div>
              ) : null}
              {vista.formalizada.huella ? (
                <div>
                  <dt className="font-medium text-text-600">Huella</dt>
                  <dd title={vista.formalizada.huella}>{abreviarHuella(vista.formalizada.huella, 12)}</dd>
                </div>
              ) : null}
            </dl>
          </div>
        </section>
      ) : null}

      {!vista.formalizada && permisos.terminar && !vista.borrador ? (
        <section aria-labelledby="preparar-titulo" className="mb-6">
          <h2 id="preparar-titulo" className="text-lg font-semibold text-text-900">
            Preparar la actuación
          </h2>
          <form onSubmit={preparar} className="mt-3 max-w-xl">
            <FormField label="Figura jurídica" htmlFor="terminacion-figura">
              <select
                id="terminacion-figura"
                value={figura}
                onChange={(event) => setFigura(event.target.value)}
                required
                className="rounded border border-line-300 px-3 py-2 text-sm"
              >
                <option value="">Elija una figura</option>
                {vista.catalogo.figuras.map((f) => (
                  <option key={f.codigo} value={f.codigo}>
                    {f.etiqueta} · {f.fuente}
                  </option>
                ))}
              </select>
            </FormField>
            <Button type="submit" variant="primary" disabled={guardando || !figura} className="mt-3">
              Preparar
            </Button>
          </form>
        </section>
      ) : null}

      {vista.borrador ? (
        <section aria-labelledby="borrador-titulo" className="mb-6">
          <h2 id="borrador-titulo" className="text-lg font-semibold text-text-900">
            Actuación en preparación
          </h2>
          <form onSubmit={guardarBorrador} className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <FormField label="Figura jurídica" htmlFor="figura">
              <select
                id="figura"
                value={formulario.figura ?? vista.borrador.figura}
                onChange={(event) => setFormulario({ ...formulario, figura: event.target.value })}
                className="rounded border border-line-300 px-3 py-2 text-sm"
              >
                {vista.catalogo.figuras.map((f) => (
                  <option key={f.codigo} value={f.codigo}>
                    {f.etiqueta} · {f.fuente}
                  </option>
                ))}
              </select>
            </FormField>

            <FormField label="Causal" htmlFor="causal">
              <select
                id="causal"
                value={formulario.causal ?? vista.borrador.causal ?? ""}
                onChange={(event) => setFormulario({ ...formulario, causal: event.target.value })}
                className="rounded border border-line-300 px-3 py-2 text-sm"
              >
                <option value="">Elija la causal</option>
                {(figuraCatalogo?.causales ?? []).map((c) => (
                  <option key={c.codigo} value={c.codigo}>
                    {c.etiqueta} · {c.fuente}
                  </option>
                ))}
              </select>
            </FormField>

            {(formulario.causal ?? vista.borrador.causal) === "CLAUSULA_CONTRATO" ? (
              <FormField label="Cláusula del contrato" htmlFor="causal_referencia">
                <input
                  id="causal_referencia"
                  value={formulario.causal_referencia ?? vista.borrador.causal_referencia ?? ""}
                  onChange={(event) => setFormulario({ ...formulario, causal_referencia: event.target.value })}
                  className="rounded border border-line-300 px-3 py-2 text-sm"
                />
              </FormField>
            ) : null}

            <FormField label="Hechos" htmlFor="hechos">
              <textarea
                id="hechos"
                value={formulario.hechos ?? vista.borrador.hechos ?? ""}
                onChange={(event) => setFormulario({ ...formulario, hechos: event.target.value })}
                rows={3}
                className="rounded border border-line-300 px-3 py-2 text-sm"
              />
            </FormField>

            <FormField label="Fundamento jurídico" htmlFor="fundamento">
              <textarea
                id="fundamento"
                value={formulario.fundamento ?? vista.borrador.fundamento ?? ""}
                onChange={(event) => setFormulario({ ...formulario, fundamento: event.target.value })}
                rows={3}
                className="rounded border border-line-300 px-3 py-2 text-sm"
              />
            </FormField>

            <FormField label="Acto decisorio" htmlFor="act_id">
              <select
                id="act_id"
                value={formulario.act_id ?? vista.borrador.acto?.id ?? ""}
                onChange={(event) => setFormulario({ ...formulario, act_id: event.target.value })}
                className="rounded border border-line-300 px-3 py-2 text-sm"
              >
                <option value="">Elija un acto</option>
                {vista.opciones.actos.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.etiqueta} · {a.emisor_cargo} · {a.estado}
                  </option>
                ))}
              </select>
            </FormField>

            {figuraBorrador === "RESCISION_IMPUTABLE" ? (
              <FormField label="Acto de apertura del procedimiento" htmlFor="apertura_act_id">
                <select
                  id="apertura_act_id"
                  value={formulario.apertura_act_id ?? vista.borrador.apertura?.id ?? ""}
                  onChange={(event) => setFormulario({ ...formulario, apertura_act_id: event.target.value })}
                  className="rounded border border-line-300 px-3 py-2 text-sm"
                >
                  <option value="">Elija un acto</option>
                  {vista.opciones.actos.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.etiqueta} · {a.emisor_cargo} · {a.estado}
                    </option>
                  ))}
                </select>
              </FormField>
            ) : null}

            {figuraBorrador === "RESOLUCION_MUTUO_ACUERDO" ? (
              <FormField label="Documento del acuerdo" htmlFor="document_id">
                <select
                  id="document_id"
                  value={formulario.document_id ?? vista.borrador.documento?.id ?? ""}
                  onChange={(event) => setFormulario({ ...formulario, document_id: event.target.value })}
                  className="rounded border border-line-300 px-3 py-2 text-sm"
                >
                  <option value="">Elija un documento</option>
                  {vista.opciones.documentos.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.titulo}
                    </option>
                  ))}
                </select>
              </FormField>
            ) : null}

            {figuraBorrador === "RESCISION_IMPUTABLE" || figuraBorrador === "RESCISION_NO_IMPUTABLE" ? (
              <>
                <FormField label="Alcance de la conclusión autorizada" htmlFor="conclusion_alcance">
                  <textarea
                    id="conclusion_alcance"
                    value={formulario.conclusion_alcance ?? vista.borrador.conclusion?.alcance ?? ""}
                    onChange={(event) => setFormulario({ ...formulario, conclusion_alcance: event.target.value })}
                    rows={3}
                    className="rounded border border-line-300 px-3 py-2 text-sm"
                  />
                </FormField>
                <FormField label="Conclusión autorizada hasta" htmlFor="conclusion_hasta">
                  <input
                    id="conclusion_hasta"
                    type="date"
                    value={formulario.conclusion_hasta ?? vista.borrador.conclusion?.hasta ?? ""}
                    onChange={(event) => setFormulario({ ...formulario, conclusion_hasta: event.target.value })}
                    className="rounded border border-line-300 px-3 py-2 text-sm"
                  />
                </FormField>
              </>
            ) : null}

            <div className="sm:col-span-2 flex gap-3">
              <Button type="submit" variant="primary" disabled={guardando}>
                Guardar borrador
              </Button>
              <Button type="button" variant="secondary" disabled={guardando} onClick={descartarBorrador}>
                Descartar borrador
              </Button>
            </div>
          </form>

          <div className="mt-4">
            <h3 className="text-sm font-semibold text-text-900">Requisitos</h3>
            <ul className="mt-2 list-inside list-disc text-sm text-text-900">
              {vista.requisitos.map((r) => (
                <li key={r.codigo}>
                  {r.cumplido ? "Cumplido" : "Pendiente"} · {r.mensaje}
                </li>
              ))}
            </ul>
          </div>

          <div className="mt-4">
            <Button
              type="button"
              variant="primary"
              disabled={!requisitosCumplidos || !permisos.terminar || guardando}
              onClick={() => setModalFormalizar(true)}
            >
              Formalizar
            </Button>
          </div>

          <ConfirmationDialog
            open={modalFormalizar}
            title="Formalizar la terminación del contrato"
            confirmLabel="Formalizar"
            danger
            onConfirm={formalizar}
            onCancel={() => setModalFormalizar(false)}
          >
            <dl className="text-sm text-text-900">
              <div className="grid grid-cols-2 gap-1">
                <dt className="font-medium text-text-600">Contrato</dt>
                <dd>{vista.contrato.codigo}</dd>
                <dt className="font-medium text-text-600">Contratista</dt>
                <dd>{vista.contrato.contratista.nombre}</dd>
                <dt className="font-medium text-text-600">Figura</dt>
                <dd>{vista.borrador.figura_etiqueta ?? vista.borrador.figura}</dd>
                <dt className="font-medium text-text-600">Causal</dt>
                <dd>{vista.borrador.causal_etiqueta ?? vista.borrador.causal ?? "—"}</dd>
                <dt className="font-medium text-text-600">Fecha de eficacia</dt>
                <dd>{actoElegido?.fecha_eficacia ? formatearFechaDeNegocio(actoElegido.fecha_eficacia) : "—"}</dd>
                <dt className="font-medium text-text-600">Acto</dt>
                <dd>{actoElegido?.etiqueta ?? "—"}</dd>
                <dt className="font-medium text-text-600">Saldo contractual no ejecutado</dt>
                <dd>
                  {vista.consecuencias.saldo_no_ejecutado} {MONEDA(vista.consecuencias)}
                </dd>
              </div>
            </dl>
            <p className="mt-3 text-sm text-text-600">
              Esta actuación modifica la situación jurídica del contrato y no se puede editar después de formalizarse.
            </p>
            {errorFormalizar ? (
              <p role="alert" className="mt-2 text-sm text-red-700">
                {errorFormalizar}
              </p>
            ) : null}
          </ConfirmationDialog>
        </section>
      ) : null}

      <section aria-labelledby="notificaciones-titulo" className="mb-6">
        <h2 id="notificaciones-titulo" className="text-lg font-semibold text-text-900">
          Notificaciones del acto
        </h2>
        {vista.notificaciones.length === 0 ? (
          <p className="mt-2 text-sm text-text-900">
            Registre las notificaciones en Gobierno · Notificaciones (DOC-04).
          </p>
        ) : (
          <div className="relative mt-2 overflow-x-auto" role="region" tabIndex={0} aria-label="Notificaciones del acto">
            <table className="min-w-full border border-line-300 text-sm">
              <thead>
                <tr className="bg-surface-50 text-left text-text-600">
                  <th className="border-b border-line-300 px-3 py-2">Destinatario</th>
                  <th className="border-b border-line-300 px-3 py-2">Identificación</th>
                  <th className="border-b border-line-300 px-3 py-2">Tipo</th>
                  <th className="border-b border-line-300 px-3 py-2">Estado</th>
                  <th className="border-b border-line-300 px-3 py-2">Fecha</th>
                  <th className="border-b border-line-300 px-3 py-2">
                    <span className="sr-only">Acciones</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {vista.notificaciones.map((n) => (
                  <tr key={n.id} className="align-top">
                    <td className="border-b border-line-300 px-3 py-2">{n.destinatario}</td>
                    <td className="border-b border-line-300 px-3 py-2">{n.identificacion}</td>
                    <td className="border-b border-line-300 px-3 py-2">
                      {n.es_contratista ? "Contratista" : "Garante u otro"}
                    </td>
                    <td className="border-b border-line-300 px-3 py-2">{n.estado}</td>
                    <td className="border-b border-line-300 px-3 py-2">
                      {n.fecha_notificacion ? formatearFechaDeNegocio(n.fecha_notificacion) : "—"}
                    </td>
                    <td className="border-b border-line-300 px-3 py-2">
                      <Link to={n.enlace} className="text-primary-600 hover:underline">
                        Ver
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section aria-labelledby="consecuencias-titulo" className="mb-6">
        <h2 id="consecuencias-titulo" className="text-lg font-semibold text-text-900">
          Consecuencias de ejecución y financieras
        </h2>
        <dl className="mt-2 grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="font-medium text-text-600">Monto vigente</dt>
            <dd>
              {vista.consecuencias.monto_vigente} {MONEDA(vista.consecuencias)}
            </dd>
          </div>
          <div>
            <dt className="font-medium text-text-600">Valuado conformado</dt>
            <dd>
              {vista.consecuencias.valuado_conformado} {MONEDA(vista.consecuencias)}
            </dd>
          </div>
          <div>
            <dt className="font-medium text-text-600">Valuado presentado</dt>
            <dd>
              {vista.consecuencias.valuado_presentado} {MONEDA(vista.consecuencias)}
            </dd>
          </div>
          <div>
            <dt className="font-medium text-text-600">Saldo no ejecutado</dt>
            <dd>
              {vista.consecuencias.saldo_no_ejecutado} {MONEDA(vista.consecuencias)}
            </dd>
          </div>
          <div>
            <dt className="font-medium text-text-600">Saldo por valuar (CNT-03)</dt>
            <dd>
              {vista.consecuencias.saldo_por_valuar_cnt03} {MONEDA(vista.consecuencias)}
            </dd>
          </div>
          <div>
            <dt className="font-medium text-text-600">Facturado conforme</dt>
            <dd>
              {vista.consecuencias.facturado_conforme} {MONEDA(vista.consecuencias)}
            </dd>
          </div>
          <div>
            <dt className="font-medium text-text-600">Recepciones</dt>
            <dd>
              {vista.consecuencias.recepciones.total} ·{" "}
              {vista.consecuencias.recepciones.definitiva ? "definitiva" : "sin recepción definitiva"}
            </dd>
          </div>
          <div>
            <dt className="font-medium text-text-600">Estado de la ejecución</dt>
            <dd>{vista.consecuencias.estado_ejecucion_etiqueta}</dd>
          </div>
        </dl>
        {vista.consecuencias.indemnizacion ? (
          <p className="mt-2 text-sm text-text-900">
            {vista.consecuencias.indemnizacion.regla} · {vista.consecuencias.indemnizacion.estado} ·{" "}
            {vista.consecuencias.indemnizacion.mensaje}
          </p>
        ) : null}
        <p className="mt-2 text-sm text-text-900">{vista.consecuencias.efectos}</p>
        <div className="relative mt-3 overflow-x-auto" role="region" tabIndex={0} aria-label="Compromisos">
          <table className="min-w-full border border-line-300 text-sm">
            <thead>
              <tr className="bg-surface-50 text-left text-text-600">
                <th className="border-b border-line-300 px-3 py-2">Código</th>
                <th className="border-b border-line-300 px-3 py-2">Estado</th>
                <th className="border-b border-line-300 px-3 py-2">Total</th>
                <th className="border-b border-line-300 px-3 py-2">
                  <span className="sr-only">Acciones</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {vista.consecuencias.compromisos.map((c) => (
                <tr key={c.codigo}>
                  <td className="border-b border-line-300 px-3 py-2">{c.codigo}</td>
                  <td className="border-b border-line-300 px-3 py-2">{c.estado}</td>
                  <td className="border-b border-line-300 px-3 py-2">
                    {c.total} {c.moneda}
                  </td>
                  <td className="border-b border-line-300 px-3 py-2">
                    <Link to={c.enlace} className="text-primary-600 hover:underline">
                      Ir a BUD-08
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="garantias-titulo" className="mb-6">
        <h2 id="garantias-titulo" className="text-lg font-semibold text-text-900">
          Garantías
        </h2>
        {vista.garantias.length === 0 ? (
          <p className="mt-2 text-sm text-text-900">Sin garantías vinculadas.</p>
        ) : (
          <div className="relative mt-2 overflow-x-auto" role="region" tabIndex={0} aria-label="Garantías">
            <table className="min-w-full border border-line-300 text-sm">
              <thead>
                <tr className="bg-surface-50 text-left text-text-600">
                  <th className="border-b border-line-300 px-3 py-2">Referencia</th>
                  <th className="border-b border-line-300 px-3 py-2">Tipo</th>
                  <th className="border-b border-line-300 px-3 py-2">Emisor</th>
                  <th className="border-b border-line-300 px-3 py-2">Monto</th>
                  <th className="border-b border-line-300 px-3 py-2">Estado</th>
                  <th className="border-b border-line-300 px-3 py-2">Vigencia</th>
                  <th className="border-b border-line-300 px-3 py-2">
                    <span className="sr-only">Acciones</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {vista.garantias.map((g) => (
                  <tr key={g.referencia}>
                    <td className="border-b border-line-300 px-3 py-2">{g.referencia}</td>
                    <td className="border-b border-line-300 px-3 py-2">{g.tipo_etiqueta}</td>
                    <td className="border-b border-line-300 px-3 py-2">{g.emisor ?? "—"}</td>
                    <td className="border-b border-line-300 px-3 py-2">
                      {g.monto} {g.moneda}
                    </td>
                    <td className="border-b border-line-300 px-3 py-2">{g.estado_etiqueta}</td>
                    <td className="border-b border-line-300 px-3 py-2">
                      {g.vigente ? "Vigente" : "No vigente"}
                    </td>
                    <td className="border-b border-line-300 px-3 py-2">
                      <Link to={g.enlace} className="text-primary-600 hover:underline">
                        Ir a PROC-10
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section aria-labelledby="obligaciones-titulo" className="mb-6">
        <h2 id="obligaciones-titulo" className="text-lg font-semibold text-text-900">
          Obligaciones pendientes
        </h2>
        <ul className="mt-2 list-inside list-disc text-sm text-text-900">
          {vista.obligaciones.map((o) => (
            <li key={o.codigo}>
              {o.mensaje} · {o.fuente}
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="registro-titulo" className="mb-6">
        <h2 id="registro-titulo" className="text-lg font-semibold text-text-900">
          Registro de terminaciones
        </h2>
        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-4">
          <FormField label="Figura" htmlFor="filtro-figura">
            <select
              id="filtro-figura"
              value={filtroFigura}
              onChange={(event) => setFiltroFigura(event.target.value)}
              className="rounded border border-line-300 px-3 py-2 text-sm"
            >
              <option value="">Todas</option>
              {vista.catalogo.figuras.map((f) => (
                <option key={f.codigo} value={f.codigo}>
                  {f.etiqueta}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Desde" htmlFor="filtro-desde">
            <input
              id="filtro-desde"
              type="date"
              value={filtroDesde}
              onChange={(event) => setFiltroDesde(event.target.value)}
              className="rounded border border-line-300 px-3 py-2 text-sm"
            />
          </FormField>
          <FormField label="Hasta" htmlFor="filtro-hasta">
            <input
              id="filtro-hasta"
              type="date"
              value={filtroHasta}
              onChange={(event) => setFiltroHasta(event.target.value)}
              className="rounded border border-line-300 px-3 py-2 text-sm"
            />
          </FormField>
          <div className="flex items-end">
            <Button type="button" variant="secondary" onClick={descargarCsv}>
              Descargar CSV
            </Button>
          </div>
        </div>
      </section>
    </PageContent>
  );
}
