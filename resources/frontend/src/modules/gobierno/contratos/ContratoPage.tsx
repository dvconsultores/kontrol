import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
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
import { CONSULTA_EXPEDIENTES } from "@/modules/gobierno/api";
import { CONSULTA_CONTRATOS, TIPOS_INSTRUMENTO, type Contrato, type FirmanteOpcion } from "./api";
import { SupervisionContrato } from "./SupervisionContrato";

interface ParcheContrato {
  tipo?: string;
  fecha_inicio?: string;
  fecha_fin?: string;
  referencia_instrumento?: string;
  descripcion_complementaria?: string;
  documento_id?: string | null;
}

function valorCampo(valor: string | null | undefined): string {
  return valor ?? "";
}

function abreviar(sha: string, longitud: number): string {
  return sha.length > longitud ? `${sha.slice(0, longitud)}…` : sha;
}

export function ContratoPage() {
  const { contratoId } = useParams<{ contratoId: string }>();
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const queryClient = useQueryClient();

  const [formulario, setFormulario] = useState<Record<string, string>>({});
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null);
  const [erroresCampos, setErroresCampos] = useState<Record<string, string[]>>({});
  const [folioFirmante, setFolioFirmante] = useState("");
  const [modalFormalizar, setModalFormalizar] = useState(false);
  const [errorFormalizar, setErrorFormalizar] = useState<string | null>(null);
  const [estadoFormalizado, setEstadoFormalizado] = useState<string | null>(null);
  const [montosAsignados, setMontosAsignados] = useState<Record<string, string>>({});
  const [garantiasMarcadas, setGarantiasMarcadas] = useState<Set<string>>(new Set());
  const [guardando, setGuardando] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);

  const consulta = useQuery({
    queryKey: [...CONSULTA_CONTRATOS, activeCompanyId, "ficha", contratoId],
    queryFn: () => apiFetch<Contrato>(`/gobierno/contratos/${contratoId}`),
    enabled: Boolean(contratoId) && tiene("gobierno_contratos:view", "empresa"),
  });

  const contrato = consulta.data;
  const permisos = {
    vista: tiene("gobierno_contratos:view", "empresa"),
    gestionar: tiene("gobierno_contratos:manage", "empresa"),
    formalizar: tiene("gobierno_contratos:formalize", "empresa"),
  };

  function actualizarDato(
    respuesta: Contrato,
    campo?: string,
    valor?: string,
  ) {
    queryClient.setQueryData([...CONSULTA_CONTRATOS, activeCompanyId, "ficha", contratoId], respuesta);
    void queryClient.invalidateQueries({ queryKey: [...CONSULTA_CONTRATOS, activeCompanyId] });
    setErrorGeneral(null);
    setErroresCampos({});
    setAviso("Cambios guardados.");
    if (campo) setFormulario((anterior) => ({ ...anterior, [campo]: valor ?? "" }));
  }

  async function guardarDatos(evento: FormEvent) {
    evento.preventDefault();
    if (!contrato) return;
    const parche: ParcheContrato = {};
    if (formulario.tipo && formulario.tipo !== contrato.tipo) parche.tipo = formulario.tipo;
    if (formulario.inicio && formulario.inicio !== contrato.fecha_inicio) parche.fecha_inicio = formulario.inicio;
    if (formulario.fin && formulario.fin !== contrato.fecha_fin) parche.fecha_fin = formulario.fin;
    if (formulario.referencia !== contrato.referencia_instrumento) parche.referencia_instrumento = formulario.referencia;
    if (formulario.descripcion !== contrato.descripcion_complementaria) {
      parche.descripcion_complementaria = formulario.descripcion;
    }
    if (formulario.documento !== (contrato.documento?.id ?? "SIN_DOCUMENTO")) {
      parche.documento_id = formulario.documento === "SIN_DOCUMENTO" || !formulario.documento ? null : formulario.documento;
    }
    setGuardando(true);
    setAviso(null);
    try {
      const respuesta = await apiFetch<Contrato>(`/gobierno/contratos/${contrato.id}`, {
        method: "PATCH",
        body: parche,
        ifMatch: String(contrato.version),
      });
      actualizarDato(respuesta);
    } catch (error) {
      if (error instanceof ApiError) {
        setErrorGeneral(error.message);
        setErroresCampos(error.fieldErrors ?? {});
      } else {
        setErrorGeneral("No se pudieron guardar los datos.");
      }
    } finally {
      setGuardando(false);
    }
  }

  async function guardarCobertura() {
    if (!contrato) return;
    const asignaciones = Object.entries(montosAsignados)
      .filter(([, monto]) => monto.trim() !== "")
      .map(([certificadoId, monto]) => ({ certificado_id: certificadoId, monto: monto.trim() }));
    setGuardando(true);
    setAviso(null);
    try {
      const respuesta = await apiFetch<Contrato>(`/gobierno/contratos/${contrato.id}/cobertura`, {
        method: "PUT",
        body: { asignaciones },
        ifMatch: String(contrato.version),
      });
      actualizarDato(respuesta);
    } catch (error) {
      setErrorGeneral(error instanceof ApiError ? error.message : "No se pudo guardar la cobertura.");
    } finally {
      setGuardando(false);
    }
  }

  async function guardarGarantias() {
    if (!contrato) return;
    setGuardando(true);
    setAviso(null);
    try {
      const respuesta = await apiFetch<Contrato>(`/gobierno/contratos/${contrato.id}/garantias`, {
        method: "PUT",
        body: { instrumento_ids: [...garantiasMarcadas] },
        ifMatch: String(contrato.version),
      });
      actualizarDato(respuesta);
    } catch (error) {
      setErrorGeneral(error instanceof ApiError ? error.message : "No se pudieron guardar las garantías.");
    } finally {
      setGuardando(false);
    }
  }

  async function formalizar() {
    if (!contrato) return;
    try {
      const respuesta = await apiFetch<Contrato>(`/gobierno/contratos/${contrato.id}/formalizar`, {
        method: "POST",
        body: { firmante_cargo_id: folioFirmante },
        ifMatch: String(contrato.version),
      });
      setModalFormalizar(false);
      setErrorFormalizar(null);
      setEstadoFormalizado(respuesta.codigo ?? "Formalizado");
      queryClient.setQueryData([...CONSULTA_CONTRATOS, activeCompanyId, "ficha", contratoId], respuesta);
      void queryClient.invalidateQueries({ queryKey: [...CONSULTA_CONTRATOS, activeCompanyId] });
      void queryClient.invalidateQueries({ queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId] });
    } catch (error) {
      setModalFormalizar(false);
      setErrorFormalizar(error instanceof ApiError ? error.message : "No se pudo formalizar.");
    }
  }

  if (!contratoId || !permisos.vista) {
    return (
      <PageContent>
        <EmptyState title="Sin acceso" description="No tiene permiso para ver este contrato." />
      </PageContent>
    );
  }

  if (consulta.isLoading) {
    return (
      <PageContent>
        <PageHeader crumbs={[{ label: "Gobierno" }, { label: "Contratos y órdenes", to: "/gobierno/contratos" }]} title="Contrato" />
        <LoadingState />
      </PageContent>
    );
  }

  if (consulta.isError) {
    if (consulta.error instanceof ApiError && consulta.error.status === 404) {
      return (
        <PageContent>
          <PageHeader crumbs={[{ label: "Gobierno" }, { label: "Contratos y órdenes", to: "/gobierno/contratos" }]} title="Contrato" />
          <EmptyState title="Contrato no encontrado" description="El contrato solicitado no existe o no está disponible." />
        </PageContent>
      );
    }
    return (
      <PageContent>
        <PageHeader crumbs={[{ label: "Gobierno" }, { label: "Contratos y órdenes", to: "/gobierno/contratos" }]} title="Contrato" />
        <ErrorDeCarga
          message={consulta.error instanceof Error ? consulta.error.message : "No se pudo cargar el contrato."}
          onRetry={() => void consulta.refetch()}
        />
      </PageContent>
    );
  }

  if (!contrato) return null;

  const firmanteElegido: FirmanteOpcion | undefined = contrato.opciones?.firmantes.find(
    (firmante) => firmante.cargo_id === folioFirmante,
  );

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno" },
          { label: "Contratos y órdenes", to: "/gobierno/contratos" },
          { label: contrato.identificacion },
        ]}
        title={contrato.identificacion}
        status={<span className="text-sm text-text-600">{contrato.estado_etiqueta}</span>}
      />

      {aviso && !estadoFormalizado ? (
        <div role="status" className="mb-4 rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-800">
          {aviso}
        </div>
      ) : null}
      {estadoFormalizado ? (
        <div role="status" className="mb-4 rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-800">
          Formalizado: {estadoFormalizado}
        </div>
      ) : null}

      <section aria-labelledby="origen-titulo" className="mb-6">
        <h2 id="origen-titulo" className="text-lg font-semibold text-text-900">
          Origen (solo lectura)
        </h2>
        <dl className="mt-3 grid gap-4 sm:grid-cols-2">
          <div>
            <dt className="text-sm font-medium text-text-600">Expediente</dt>
            <dd className="break-words text-sm text-text-900">
              <Link
                className="text-brand-700 underline"
                to={`/gobierno/contrataciones/expedientes/${contrato.expediente.id}`}
              >
                {contrato.expediente.numero}
              </Link>
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-600">Adjudicación</dt>
            <dd className="break-words text-sm text-text-900">
              {contrato.decision.referencia} · {formatearFechaDeNegocio(contrato.decision.fecha)} · {contrato.decision.acto}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-600">Oferta</dt>
            <dd className="break-words text-sm text-text-900">{contrato.oferta.referencia}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-600">Contratista</dt>
            <dd className="break-words text-sm text-text-900">{contrato.contratista.nombre}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-600">Documento del contratista</dt>
            <dd className="break-words text-sm text-text-900">{contrato.contratista.documento}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-600">Representante</dt>
            <dd className="break-words text-sm text-text-900">{contrato.contratista.representante ?? "—"}</dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-sm font-medium text-text-600">Objeto</dt>
            <dd className="break-words text-sm text-text-900">{contrato.objeto}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-600">Monto</dt>
            <dd className="text-sm text-text-900">
              {contrato.monto} {contrato.moneda}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-600">Moneda</dt>
            <dd className="text-sm text-text-900">{contrato.moneda}</dd>
          </div>
        </dl>
        <p className="mt-3 text-sm text-text-600">
          El objeto, el contratista, el monto y la moneda salen de la adjudicación y de la oferta: no se editan.
        </p>
        {!contrato.decision.vigente ? (
          <div role="alert" className="mt-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            La adjudicación de origen ya no está vigente: este borrador no puede formalizarse.
          </div>
        ) : null}
      </section>

      {contrato.estado === "BORRADOR" && permisos.gestionar ? (
        <>
          <section aria-labelledby="datos-titulo" className="mb-6">
            <h2 id="datos-titulo" className="text-lg font-semibold text-text-900">
              Datos del instrumento
            </h2>
            <form onSubmit={(evento) => void guardarDatos(evento)} className="mt-3 grid gap-4 sm:grid-cols-2">
              {errorGeneral ? (
                <div role="alert" className="sm:col-span-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                  {errorGeneral}
                </div>
              ) : null}
              <FormField
                label="Tipo"
                htmlFor="contrato-tipo"
                error={erroresCampos.tipo?.join(", ")}
              >
                <select
                  id="contrato-tipo"
                  className="w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
                  value={formulario.tipo ?? contrato.tipo ?? ""}
                  onChange={(evento) => setFormulario((anterior) => ({ ...anterior, tipo: evento.target.value }))}
                >
                  <option value="">Seleccione</option>
                  {TIPOS_INSTRUMENTO.map((instrumento) => (
                    <option key={instrumento.codigo} value={instrumento.codigo}>
                      {instrumento.etiqueta}
                    </option>
                  ))}
                </select>
              </FormField>
              <FormField
                label="Inicio del plazo"
                htmlFor="contrato-inicio"
                error={erroresCampos.fecha_inicio?.join(", ")}
              >
                <input
                  id="contrato-inicio"
                  type="date"
                  className="w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
                  value={formulario.inicio ?? valorCampo(contrato.fecha_inicio)}
                  onChange={(evento) => setFormulario((anterior) => ({ ...anterior, inicio: evento.target.value }))}
                />
              </FormField>
              <FormField label="Fin del plazo" htmlFor="contrato-fin" error={erroresCampos.fecha_fin?.join(", ")}>
                <input
                  id="contrato-fin"
                  type="date"
                  className="w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
                  value={formulario.fin ?? valorCampo(contrato.fecha_fin)}
                  onChange={(evento) => setFormulario((anterior) => ({ ...anterior, fin: evento.target.value }))}
                />
              </FormField>
              <FormField
                label="Referencia del instrumento"
                htmlFor="contrato-referencia"
                help="La que figura en el contrato u orden firmada"
                error={erroresCampos.referencia_instrumento?.join(", ")}
              >
                <input
                  id="contrato-referencia"
                  type="text"
                  className="w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
                  value={formulario.referencia ?? valorCampo(contrato.referencia_instrumento)}
                  onChange={(evento) => setFormulario((anterior) => ({ ...anterior, referencia: evento.target.value }))}
                />
              </FormField>
              <FormField
                label="Descripción complementaria"
                htmlFor="contrato-descripcion"
                help="No sustituye el objeto adjudicado"
                error={erroresCampos.descripcion_complementaria?.join(", ")}
                className="sm:col-span-2"
              >
                <textarea
                  id="contrato-descripcion"
                  rows={3}
                  className="w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
                  value={formulario.descripcion ?? valorCampo(contrato.descripcion_complementaria)}
                  onChange={(evento) => setFormulario((anterior) => ({ ...anterior, descripcion: evento.target.value }))}
                />
              </FormField>
              <FormField
                label="Instrumento firmado"
                htmlFor="contrato-documento"
                error={erroresCampos.documento_id?.join(", ")}
                className="sm:col-span-2"
              >
                {contrato.opciones?.documentos_elegibles?.length ? (
                  <select
                    id="contrato-documento"
                    className="w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
                    value={formulario.documento ?? contrato.documento?.id ?? "SIN_DOCUMENTO"}
                    onChange={(evento) => setFormulario((anterior) => ({ ...anterior, documento: evento.target.value }))}
                  >
                    <option value="SIN_DOCUMENTO">Sin documento</option>
                    {contrato.opciones.documentos_elegibles.map((documento) => (
                      <option key={documento.id} value={documento.id}>
                        {documento.titulo} · v{documento.version}
                      </option>
                    ))}
                  </select>
                ) : (
                  <p className="text-sm text-text-600">
                    Vincule primero el documento firmado al expediente en su sección de documentos.
                  </p>
                )}
              </FormField>
              <div className="sm:col-span-2">
                <Button type="submit" variant="primary" disabled={guardando}>
                  Guardar datos
                </Button>
              </div>
            </form>
          </section>

          <section aria-labelledby="cobertura-titulo" className="mb-6">
            <h2 id="cobertura-titulo" className="text-lg font-semibold text-text-900">
              Cobertura presupuestaria
            </h2>
            {contrato.opciones?.certificados_elegibles?.length ? (
              <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Certificaciones elegibles">
                <table className="mt-3 w-full min-w-[700px] border-collapse text-left text-sm">
                  <thead>
                    <tr className="border-b border-border-subtle text-text-600">
                      <th className="px-3 py-2 font-medium">Certificación</th>
                      <th className="px-3 py-2 font-medium">Ejercicio</th>
                      <th className="px-3 py-2 font-medium">Partida</th>
                      <th className="px-3 py-2 font-medium">Fuente</th>
                      <th className="px-3 py-2 font-medium">Saldo libre</th>
                      <th className="px-3 py-2 font-medium">Monto asignado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {contrato.opciones.certificados_elegibles.map((certificado) => {
                      const asignada = contrato.cobertura.asignaciones.find(
                        (asignacion) => asignacion.certificado_id === certificado.id,
                      );
                      return (
                        <tr key={certificado.id} className="border-b border-border-subtle align-top">
                          <td className="break-words px-3 py-2 text-text-900">{certificado.codigo}</td>
                          <td className="px-3 py-2 text-text-900">{certificado.anio}</td>
                          <td className="break-words px-3 py-2 text-text-900">{certificado.partida}</td>
                          <td className="break-words px-3 py-2 text-text-900">{certificado.fuente}</td>
                          <td className="px-3 py-2 text-text-900">
                            {certificado.saldo_libre} {certificado.moneda}
                          </td>
                          <td className="px-3 py-2">
                            <label htmlFor={`asignar-${certificado.codigo}`} className="sr-only">
                              Monto asignado a {certificado.codigo}
                            </label>
                            <input
                              id={`asignar-${certificado.codigo}`}
                              inputMode="decimal"
                              className="w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
                              value={montosAsignados[certificado.id] ?? asignada?.monto ?? ""}
                              onChange={(evento) =>
                                setMontosAsignados((anterior) => ({ ...anterior, [certificado.id]: evento.target.value }))
                              }
                            />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState
                title="Sin certificaciones elegibles"
                description={`Solo se pueden usar certificaciones de disponibilidad VIGENTES, en ${contrato.moneda} y con saldo libre.`}
              />
            )}
            {contrato.cobertura.total_asignado ? (
              <p className="mt-3 text-sm text-text-900">
                Asignado: {contrato.cobertura.total_asignado} {contrato.moneda} · Falta: {contrato.cobertura.faltante}{" "}
                {contrato.moneda}
                {contrato.cobertura.completa ? (
                  <span className="ml-2 font-medium text-green-800">Cobertura completa</span>
                ) : null}
              </p>
            ) : null}
            <p className="mt-2 text-sm text-text-600">
              Vincular la cobertura no consume la certificación: el compromiso presupuestario es una etapa posterior
              (BUD-08).
            </p>
            <div className="mt-3">
              <Button type="button" variant="secondary" disabled={guardando} onClick={() => void guardarCobertura()}>
                Guardar cobertura
              </Button>
            </div>
          </section>

          <section aria-labelledby="garantias-titulo" className="mb-6">
            <h2 id="garantias-titulo" className="text-lg font-semibold text-text-900">
              Garantías
            </h2>
            {contrato.opciones?.garantias_elegibles?.length ? (
              <div className="mt-3 grid gap-2">
                {contrato.opciones.garantias_elegibles.map((garantia) => (
                  <label
                    key={garantia.instrumento_id}
                    className="flex items-start gap-2 rounded-md border border-border-subtle bg-white p-3 text-sm text-text-900"
                  >
                    <input
                      type="checkbox"
                      className="mt-1"
                      checked={
                        garantiasMarcadas.has(garantia.instrumento_id) ||
                        contrato.garantias.some((vinculada) => vinculada.instrumento_id === garantia.instrumento_id)
                      }
                      onChange={(evento) =>
                        setGarantiasMarcadas((anterior) => {
                          const siguientes = new Set(anterior);
                          if (evento.target.checked) siguientes.add(garantia.instrumento_id);
                          else siguientes.delete(garantia.instrumento_id);
                          return siguientes;
                        })
                      }
                    />
                    <span className="break-words">
                      {garantia.referencia} · {garantia.tipo_etiqueta} · {garantia.emisor} · {garantia.monto}{" "}
                      {garantia.moneda} · vence {formatearFechaDeNegocio(garantia.vigente_hasta)}
                    </span>
                  </label>
                ))}
              </div>
            ) : (
              <p className="mt-3 text-sm text-text-600">
                No hay garantías registradas para la oferta adjudicada. Si la institución no las exige, puede
                formalizarse sin ellas.
              </p>
            )}
            <div className="mt-3">
              <Button type="button" variant="secondary" disabled={guardando} onClick={() => void guardarGarantias()}>
                Guardar garantías
              </Button>
            </div>
          </section>

          {permisos.formalizar ? (
            <section aria-labelledby="formalizacion-titulo" className="mb-6">
              <h2 id="formalizacion-titulo" className="text-lg font-semibold text-text-900">
                Formalización
              </h2>
              {contrato.pendientes.length > 0 ? (
                <>
                  <h3 className="mt-3 text-sm font-medium text-text-900">Falta para formalizar</h3>
                  <ul className="mt-2 list-inside list-disc text-sm text-text-600">
                    {contrato.pendientes.map((pendiente) => (
                      <li key={pendiente}>{pendiente}</li>
                    ))}
                  </ul>
                </>
              ) : null}
              {errorFormalizar ? (
                <div id="formalizar-error" role="alert" className="mt-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                  {errorFormalizar}
                </div>
              ) : null}
              {contrato.opciones?.firmantes?.length ? (
                <FormField label="Cargo firmante" htmlFor="contrato-firmante" className="mt-3">
                  <select
                    id="contrato-firmante"
                    className="w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
                    value={folioFirmante}
                    onChange={(evento) => setFolioFirmante(evento.target.value)}
                  >
                    <option value="">Seleccione</option>
                    {contrato.opciones.firmantes.map((firmante) => (
                      <option key={firmante.cargo_id} value={firmante.cargo_id}>
                        {firmante.cargo}
                      </option>
                    ))}
                  </select>
                </FormField>
              ) : (
                <p className="mt-3 text-sm text-text-600">
                  Ningún cargo tiene hoy la competencia Firmar sobre Contrataciones.
                </p>
              )}
              {firmanteElegido ? (
                <section aria-label="Control del límite del firmante" className="mt-3 rounded-md border border-border-subtle bg-white p-3">
                  <dl className="grid gap-2 text-sm sm:grid-cols-2">
                    <div>
                      <dt className="font-medium text-text-600">Cargo</dt>
                      <dd className="text-text-900">{firmanteElegido.cargo}</dd>
                    </div>
                    <div>
                      <dt className="font-medium text-text-600">Límite de firma</dt>
                      <dd className="text-text-900">{firmanteElegido.limite.etiqueta}</dd>
                    </div>
                    <div className="sm:col-span-2">
                      <dt className="font-medium text-text-600">Resultado</dt>
                      <dd className={firmanteElegido.control.permite ? "text-green-800" : "text-red-700"}>
                        {firmanteElegido.control.estado_etiqueta}
                      </dd>
                    </div>
                  </dl>
                  <p className={`mt-2 text-sm ${firmanteElegido.control.permite ? "text-text-600" : "text-red-700"}`}>
                    {firmanteElegido.control.mensaje}
                  </p>
                </section>
              ) : null}
              <div className="mt-3">
                <Button type="button" variant="primary" disabled={!folioFirmante} onClick={() => setModalFormalizar(true)}>
                  Formalizar
                </Button>
              </div>
              <ConfirmationDialog
                open={modalFormalizar}
                title="Formalizar el contrato u orden"
                description="Se congelarán los datos, la cobertura, las garantías y el documento. Después no podrá modificarse desde aquí (las adendas son de CNT-02)."
                confirmLabel="Formalizar"
                cancelLabel="Cancelar"
                onConfirm={async () => {
                  await formalizar();
                }}
                onCancel={() => setModalFormalizar(false)}
              />
            </section>
          ) : null}
        </>
      ) : null}

      {contrato.estado === "FORMALIZADO" ? (
        <section aria-labelledby="instrumento-formalizado-titulo" className="mb-6">
          <h2 id="instrumento-formalizado-titulo" className="text-lg font-semibold text-text-900">
            Instrumento formalizado
          </h2>
          <dl className="mt-3 grid gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-sm font-medium text-text-600">Código</dt>
              <dd className="break-words text-sm text-text-900">{contrato.codigo ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-text-600">Tipo</dt>
              <dd className="text-sm text-text-900">{contrato.tipo_etiqueta ?? "—"}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-sm font-medium text-text-600">Plazo</dt>
              <dd className="text-sm text-text-900">
                {contrato.fecha_inicio && contrato.fecha_fin
                  ? `${formatearFechaDeNegocio(contrato.fecha_inicio)} al ${formatearFechaDeNegocio(contrato.fecha_fin)}`
                  : "—"}
              </dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-sm font-medium text-text-600">Referencia</dt>
              <dd className="break-words text-sm text-text-900">{contrato.referencia_instrumento ?? "—"}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-sm font-medium text-text-600">Documento</dt>
              <dd className="break-words text-sm text-text-900">
                {contrato.documento ? (
                  <>
                    {contrato.documento.titulo} · versión {contrato.documento.version} · huella SHA-256{" "}
                    {abreviar(contrato.documento.sha256, 12)}{" "}
                    <Link className="text-brand-700 underline" to={`/documentos/${contrato.documento.id}`}>
                      Ver documento
                    </Link>
                  </>
                ) : (
                  "—"
                )}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-text-600">Firmante</dt>
              <dd className="break-words text-sm text-text-900">
                {contrato.firmante
                  ? `${contrato.firmante.cargo}${contrato.firmante.funcionario ? ` · ${contrato.firmante.funcionario}` : ""}`
                  : "—"}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-text-600">Formalizado</dt>
              <dd className="text-sm text-text-900">
                {contrato.formalizado_en ? formatearInstante(contrato.formalizado_en) : "—"}
              </dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-sm font-medium text-text-600">Huella del contrato</dt>
              <dd
                className="break-words text-sm text-text-900"
                title={contrato.huella ?? undefined}
              >
                {contrato.huella ? abreviar(contrato.huella, 16) : "—"}
              </dd>
            </div>
          </dl>

          <h3 className="mt-4 text-sm font-semibold text-text-900">Cobertura</h3>
          {contrato.cobertura.asignaciones.length > 0 ? (
            <div className="mt-2 overflow-x-auto" tabIndex={0} role="region" aria-label="Cobertura vinculada">
              <table className="w-full min-w-[600px] border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-border-subtle text-text-600">
                    <th className="px-3 py-2 font-medium">Certificación</th>
                    <th className="px-3 py-2 font-medium">Ejercicio</th>
                    <th className="px-3 py-2 font-medium">Partida</th>
                    <th className="px-3 py-2 font-medium">Fuente</th>
                    <th className="px-3 py-2 font-medium">Monto</th>
                  </tr>
                </thead>
                <tbody>
                  {contrato.cobertura.asignaciones.map((asignacion) => (
                    <tr key={asignacion.certificado_id} className="border-b border-border-subtle align-top">
                      <td className="break-words px-3 py-2 text-text-900">{asignacion.codigo}</td>
                      <td className="px-3 py-2 text-text-900">{asignacion.anio}</td>
                      <td className="break-words px-3 py-2 text-text-900">{asignacion.partida}</td>
                      <td className="break-words px-3 py-2 text-text-900">{asignacion.fuente}</td>
                      <td className="px-3 py-2 text-text-900">
                        {asignacion.monto} {asignacion.moneda}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="mt-2 text-sm text-text-600">Sin cobertura vinculada.</p>
          )}

          <h3 className="mt-4 text-sm font-semibold text-text-900">Garantías</h3>
          {contrato.garantias.length > 0 ? (
            <div className="mt-2 overflow-x-auto" tabIndex={0} role="region" aria-label="Garantías vinculadas">
              <table className="w-full min-w-[600px] border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-border-subtle text-text-600">
                    <th className="px-3 py-2 font-medium">Referencia</th>
                    <th className="px-3 py-2 font-medium">Tipo</th>
                    <th className="px-3 py-2 font-medium">Emisor</th>
                    <th className="px-3 py-2 font-medium">Monto</th>
                    <th className="px-3 py-2 font-medium">Vence</th>
                  </tr>
                </thead>
                <tbody>
                  {contrato.garantias.map((garantia) => (
                    <tr key={garantia.instrumento_id} className="border-b border-border-subtle align-top">
                      <td className="break-words px-3 py-2 text-text-900">{garantia.referencia}</td>
                      <td className="break-words px-3 py-2 text-text-900">{garantia.tipo_etiqueta}</td>
                      <td className="break-words px-3 py-2 text-text-900">{garantia.emisor}</td>
                      <td className="px-3 py-2 text-text-900">
                        {garantia.monto} {garantia.moneda}
                      </td>
                      <td className="px-3 py-2 text-text-900">{formatearFechaDeNegocio(garantia.vigente_hasta)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="mt-2 text-sm text-text-600">Sin garantías vinculadas.</p>
          )}

          <p className="mt-3 text-sm text-text-600">
            Las adendas, prórrogas y variaciones se registrarán como documentos nuevos (CNT-02): este registro no se
            modifica.
          </p>
        </section>
      ) : null}
      {contrato.estado === "FORMALIZADO" ? <SupervisionContrato contratoId={contrato.id} /> : null}

      {contrato.estado === "BORRADOR" && !permisos.gestionar ? (
        <section aria-labelledby="vinculaciones-titulo" className="mb-6">
          <h2 id="vinculaciones-titulo" className="text-lg font-semibold text-text-900">
            Cobertura y garantías vinculadas
          </h2>
          <h3 className="mt-3 text-sm font-semibold text-text-900">Cobertura</h3>
          {contrato.cobertura.asignaciones.length > 0 ? (
            <div className="mt-2 overflow-x-auto" tabIndex={0} role="region" aria-label="Cobertura del instrumento formalizado">
              <table className="w-full min-w-[600px] border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-border-subtle text-text-600">
                    <th className="px-3 py-2 font-medium">Certificación</th>
                    <th className="px-3 py-2 font-medium">Ejercicio</th>
                    <th className="px-3 py-2 font-medium">Partida</th>
                    <th className="px-3 py-2 font-medium">Fuente</th>
                    <th className="px-3 py-2 font-medium">Monto</th>
                  </tr>
                </thead>
                <tbody>
                  {contrato.cobertura.asignaciones.map((asignacion) => (
                    <tr key={asignacion.certificado_id} className="border-b border-border-subtle align-top">
                      <td className="break-words px-3 py-2 text-text-900">{asignacion.codigo}</td>
                      <td className="px-3 py-2 text-text-900">{asignacion.anio}</td>
                      <td className="break-words px-3 py-2 text-text-900">{asignacion.partida}</td>
                      <td className="break-words px-3 py-2 text-text-900">{asignacion.fuente}</td>
                      <td className="px-3 py-2 text-text-900">
                        {asignacion.monto} {asignacion.moneda}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="mt-2 text-sm text-text-600">Sin cobertura vinculada.</p>
          )}

          <h3 className="mt-4 text-sm font-semibold text-text-900">Garantías</h3>
          {contrato.garantias.length > 0 ? (
            <ul className="mt-2 list-inside list-disc text-sm text-text-900">
              {contrato.garantias.map((garantia) => (
                <li key={garantia.instrumento_id} className="break-words">
                  {garantia.referencia} · {garantia.tipo_etiqueta} · {garantia.emisor} · {garantia.monto}{" "}
                  {garantia.moneda} · vence {formatearFechaDeNegocio(garantia.vigente_hasta)}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-text-600">Sin garantías vinculadas.</p>
          )}

          {contrato.pendientes.length > 0 ? (
            <>
              <h3 className="mt-4 text-sm font-semibold text-text-900">Falta para formalizar</h3>
              <ul className="mt-2 list-inside list-disc text-sm text-text-600">
                {contrato.pendientes.map((pendiente) => (
                  <li key={pendiente}>{pendiente}</li>
                ))}
              </ul>
            </>
          ) : null}
        </section>
      ) : null}
    </PageContent>
  );
}
