import { useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router";
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
import {
  CONSULTA_CONTRATOS,
  TIPOS_MODIFICACION,
  rutaContrato,
  rutaModificaciones,
  type FichaModificacion,
  type FirmanteOpcion,
} from "./api";

function abreviarHuella(huella: string, cantidad = 16): string {
  return huella.length > cantidad ? `${huella.slice(0, cantidad)}…` : huella;
}

export function ModificacionPage() {
  const { contratoId, modificacionId } = useParams<{ contratoId: string; modificacionId: string }>();
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const [formulario, setFormulario] = useState<Record<string, string>>({});
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null);
  const [erroresCampos, setErroresCampos] = useState<Record<string, string[]>>({});
  const [folioFirmante, setFolioFirmante] = useState("");
  const [modalFormalizar, setModalFormalizar] = useState(false);
  const [errorFormalizar, setErrorFormalizar] = useState<string | null>(null);
  const [montosAsignados, setMontosAsignados] = useState<Record<string, string>>({});
  const [modalDescartar, setModalDescartar] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);

  const consulta = useQuery({
    queryKey: [...CONSULTA_CONTRATOS, activeCompanyId, "modificacion", modificacionId],
    queryFn: () =>
      apiFetch<FichaModificacion>(`/gobierno/contratos/${contratoId}/modificaciones/${modificacionId}`),
    enabled: Boolean(contratoId) && Boolean(modificacionId) && tiene("gobierno_contratos:view", "empresa"),
  });

  const ficha = consulta.data;
  const permisos = {
    vista: tiene("gobierno_contratos:view", "empresa"),
    gestionar: tiene("gobierno_contratos:manage", "empresa"),
    formalizar: tiene("gobierno_contratos:formalize", "empresa"),
  };

  function actualizarFicha(respuesta: FichaModificacion, mensaje?: string) {
    queryClient.setQueryData(
      [...CONSULTA_CONTRATOS, activeCompanyId, "modificacion", modificacionId],
      respuesta,
    );
    void queryClient.invalidateQueries({ queryKey: [...CONSULTA_CONTRATOS, activeCompanyId] });
    setErrorGeneral(null);
    setErroresCampos({});
    setAviso(mensaje ?? "Cambios guardados.");
  }

  async function guardarDatos(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    if (!ficha) return;
    setGuardando(true);
    setErrorGeneral(null);
    setErroresCampos({});
    setAviso(null);

    const cuerpo: Record<string, string | null> = {};
    const campos = [
      "tipo",
      "fecha_instrumento",
      "vigente_desde",
      "motivo",
      "nueva_fecha_fin",
      "delta_monto",
      "condiciones",
      "referencia_instrumento",
      "documento_id",
    ] as const;

    for (const campo of campos) {
      if (formulario[campo] !== undefined) {
        cuerpo[campo] = formulario[campo] === "" || formulario[campo] === "SIN_DOCUMENTO" ? null : formulario[campo];
      }
    }

    try {
      const respuesta = await apiFetch<FichaModificacion>(
        `/gobierno/contratos/${contratoId}/modificaciones/${modificacionId}`,
        {
          method: "PATCH",
          body: cuerpo,
          ifMatch: String(ficha.version),
        },
      );
      setFormulario({});
      actualizarFicha(respuesta);
    } catch (error) {
      if (error instanceof ApiError && error.fieldErrors) {
        setErroresCampos(error.fieldErrors);
        setErrorGeneral(error.message);
      } else {
        setErrorGeneral(error instanceof ApiError ? error.message : "No se pudieron guardar los datos.");
      }
    } finally {
      setGuardando(false);
    }
  }

  async function guardarCobertura() {
    if (!ficha) return;
    setGuardando(true);
    setErrorGeneral(null);
    setErroresCampos({});
    setAviso(null);

    const asignaciones = Object.entries(montosAsignados)
      .filter(([, monto]) => monto.trim() !== "")
      .map(([certificado_id, monto]) => ({ certificado_id, monto }));

    try {
      const respuesta = await apiFetch<FichaModificacion>(
        `/gobierno/contratos/${contratoId}/modificaciones/${modificacionId}/cobertura`,
        {
          method: "PUT",
          body: { asignaciones },
          ifMatch: String(ficha.version),
        },
      );
      setMontosAsignados({});
      actualizarFicha(respuesta);
    } catch (error) {
      setErrorGeneral(error instanceof ApiError ? error.message : "No se pudo guardar la cobertura.");
    } finally {
      setGuardando(false);
    }
  }

  async function formalizar() {
    if (!ficha) return;
    setGuardando(true);
    setErrorFormalizar(null);
    try {
      const respuesta = await apiFetch<FichaModificacion>(
        `/gobierno/contratos/${contratoId}/modificaciones/${modificacionId}/formalizar`,
        {
          method: "POST",
          body: { firmante_cargo_id: folioFirmante },
          ifMatch: String(ficha.version),
        },
      );
      setModalFormalizar(false);
      setErrorFormalizar(null);
      actualizarFicha(respuesta, `Formalizada: ${respuesta.codigo ?? respuesta.identificacion}`);
      void queryClient.invalidateQueries({ queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId] });
    } catch (error) {
      setModalFormalizar(false);
      setErrorFormalizar(error instanceof ApiError ? error.message : "No se pudo formalizar.");
    } finally {
      setGuardando(false);
    }
  }

  async function descartar() {
    if (!ficha) return;
    setGuardando(true);
    setErrorGeneral(null);
    try {
      await apiFetch<void>(`/gobierno/contratos/${contratoId}/modificaciones/${modificacionId}`, {
        method: "DELETE",
        ifMatch: String(ficha.version),
      });
      setModalDescartar(false);
      void queryClient.invalidateQueries({ queryKey: [...CONSULTA_CONTRATOS, activeCompanyId] });
      navigate(rutaModificaciones(contratoId ?? ""));
    } catch (error) {
      setErrorGeneral(error instanceof ApiError ? error.message : "No se pudo descartar el borrador.");
    } finally {
      setGuardando(false);
    }
  }

  if (!contratoId || !modificacionId || !permisos.vista) {
    return (
      <PageContent>
        <EmptyState title="Sin acceso" description="No tiene permiso para ver esta modificación." />
      </PageContent>
    );
  }

  if (consulta.isLoading) {
    return (
      <PageContent>
        <PageHeader
          crumbs={[
            { label: "Gobierno" },
            { label: "Contratos y órdenes", to: "/gobierno/contratos" },
            { label: "Modificaciones", to: rutaModificaciones(contratoId) },
          ]}
          title="Modificación"
        />
        <LoadingState />
      </PageContent>
    );
  }

  if (consulta.isError) {
    if (consulta.error instanceof ApiError && consulta.error.status === 404) {
      return (
        <PageContent>
          <PageHeader
            crumbs={[
              { label: "Gobierno" },
              { label: "Contratos y órdenes", to: "/gobierno/contratos" },
              { label: "Modificaciones", to: rutaModificaciones(contratoId) },
            ]}
            title="Modificación"
          />
          <EmptyState title="Modificación no encontrada" description="La modificación solicitada no existe o no está disponible." />
        </PageContent>
      );
    }
    return (
      <PageContent>
        <PageHeader
          crumbs={[
            { label: "Gobierno" },
            { label: "Contratos y órdenes", to: "/gobierno/contratos" },
            { label: "Modificaciones", to: rutaModificaciones(contratoId) },
          ]}
          title="Modificación"
        />
        <ErrorDeCarga
          message={consulta.error instanceof Error ? consulta.error.message : "No se pudo cargar la modificación."}
          onRetry={() => void consulta.refetch()}
        />
      </PageContent>
    );
  }

  if (!ficha) return null;

  const firmanteElegido: FirmanteOpcion | undefined = ficha.opciones?.firmantes.find(
    (firmante) => firmante.cargo_id === folioFirmante,
  );

  const esBorrador = ficha.estado === "BORRADOR";

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno" },
          { label: "Contratos y órdenes", to: "/gobierno/contratos" },
          { label: ficha.contrato.codigo ?? "Contrato", to: rutaContrato(contratoId) },
          { label: "Modificaciones", to: rutaModificaciones(contratoId) },
          { label: ficha.identificacion },
        ]}
        title={ficha.identificacion}
        status={ficha.estado_etiqueta}
      />

      {aviso ? (
        <div role="status" className="mb-6 rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-800">
          {aviso}
        </div>
      ) : null}

      {errorGeneral ? (
        <div role="alert" className="mb-6 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {errorGeneral}
        </div>
      ) : null}

      <section aria-labelledby="cambio-titulo" className="mb-6">
        <h2 id="cambio-titulo" className="text-lg font-semibold text-text-900">
          {esBorrador ? "Cambio propuesto" : "Cambio formalizado"}
        </h2>
        <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="font-medium text-text-600">Monto vigente antes</dt>
            <dd className="text-text-900">
              {ficha.base.monto} {ficha.moneda}
            </dd>
          </div>
          <div>
            <dt className="font-medium text-text-600">Monto efectivo nuevo</dt>
            <dd className="text-text-900">
              {ficha.propuesta.monto_nuevo ? `${ficha.propuesta.monto_nuevo} ${ficha.moneda}` : "—"}
            </dd>
          </div>
          <div>
            <dt className="font-medium text-text-600">Fin del plazo antes</dt>
            <dd className="text-text-900">
              {ficha.base.fecha_fin ? formatearFechaDeNegocio(ficha.base.fecha_fin) : "—"}
            </dd>
          </div>
          <div>
            <dt className="font-medium text-text-600">Fin del plazo nuevo</dt>
            <dd className="text-text-900">
              {ficha.propuesta.fecha_fin_nueva ? formatearFechaDeNegocio(ficha.propuesta.fecha_fin_nueva) : "—"}
            </dd>
          </div>
        </dl>
        <p className="mt-3 text-sm text-text-600">
          El contrato original no cambia: las condiciones vigentes se derivan de la historia de modificaciones.
        </p>
      </section>

      {esBorrador && permisos.gestionar ? (
        <form onSubmit={(evento) => void guardarDatos(evento)} aria-labelledby="datos-modificacion-titulo" className="mb-6">
          <h2 id="datos-modificacion-titulo" className="text-lg font-semibold text-text-900">
            Datos de la modificación
          </h2>
          <div className="mt-3 grid gap-4 sm:grid-cols-2">
            <FormField label="Tipo de modificación" htmlFor="modificacion-tipo" error={erroresCampos.tipo?.join(", ")}>
              <select
                id="modificacion-tipo"
                className="w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
                value={formulario.tipo ?? ficha.tipo}
                onChange={(evento) => setFormulario((anterior) => ({ ...anterior, tipo: evento.target.value }))}
              >
                {TIPOS_MODIFICACION.map((opcion) => (
                  <option key={opcion.codigo} value={opcion.codigo}>
                    {opcion.etiqueta}
                  </option>
                ))}
              </select>
            </FormField>
            <FormField label="Fecha del instrumento" htmlFor="modificacion-fecha-instrumento" error={erroresCampos.fecha_instrumento?.join(", ")}>
              <input
                id="modificacion-fecha-instrumento"
                type="date"
                className="w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
                value={formulario.fecha_instrumento ?? ficha.fecha_instrumento ?? ""}
                onChange={(evento) =>
                  setFormulario((anterior) => ({ ...anterior, fecha_instrumento: evento.target.value }))
                }
              />
            </FormField>
            <FormField label="Vigente desde" htmlFor="modificacion-vigente-desde" error={erroresCampos.vigente_desde?.join(", ")}>
              <input
                id="modificacion-vigente-desde"
                type="date"
                className="w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
                value={formulario.vigente_desde ?? ficha.vigente_desde ?? ""}
                onChange={(evento) =>
                  setFormulario((anterior) => ({ ...anterior, vigente_desde: evento.target.value }))
                }
              />
            </FormField>
            <FormField label="Nueva fecha de fin" htmlFor="modificacion-nueva-fecha-fin" help="Solo para extender el plazo" error={erroresCampos.nueva_fecha_fin?.join(", ")}>
              <input
                id="modificacion-nueva-fecha-fin"
                type="date"
                className="w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
                value={formulario.nueva_fecha_fin ?? ficha.nueva_fecha_fin ?? ""}
                onChange={(evento) =>
                  setFormulario((anterior) => ({ ...anterior, nueva_fecha_fin: evento.target.value }))
                }
              />
            </FormField>
            <FormField label="Cambio de monto" htmlFor="modificacion-delta" help={`Positivo para aumentar, negativo para disminuir, en ${ficha.moneda}`} error={erroresCampos.delta_monto?.join(", ")}>
              <input
                id="modificacion-delta"
                type="text"
                inputMode="decimal"
                className="w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
                value={formulario.delta_monto ?? ficha.delta_monto ?? ""}
                onChange={(evento) => setFormulario((anterior) => ({ ...anterior, delta_monto: evento.target.value }))}
              />
            </FormField>
            <FormField label="Referencia del instrumento" htmlFor="modificacion-referencia" error={erroresCampos.referencia_instrumento?.join(", ")}>
              <input
                id="modificacion-referencia"
                type="text"
                className="w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
                value={formulario.referencia_instrumento ?? ficha.referencia_instrumento ?? ""}
                onChange={(evento) =>
                  setFormulario((anterior) => ({ ...anterior, referencia_instrumento: evento.target.value }))
                }
              />
            </FormField>
            <FormField label="Documento" htmlFor="modificacion-documento" error={erroresCampos.documento_id?.join(", ")}>
              {ficha.opciones?.documentos_elegibles?.length ? (
                <select
                  id="modificacion-documento"
                  className="w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
                  value={formulario.documento_id ?? ficha.documento?.id ?? "SIN_DOCUMENTO"}
                  onChange={(evento) => setFormulario((anterior) => ({ ...anterior, documento_id: evento.target.value }))}
                >
                  <option value="SIN_DOCUMENTO">Sin documento</option>
                  {ficha.opciones.documentos_elegibles.map((documento) => (
                    <option key={documento.id} value={documento.id}>
                      {documento.titulo} · v{documento.version}
                    </option>
                  ))}
                </select>
              ) : (
                <p className="mt-1 text-sm text-text-600">
                  Vincule primero el documento firmado al expediente en su sección de documentos.
                </p>
              )}
            </FormField>
            <div className="sm:col-span-2">
              <FormField label="Motivo" htmlFor="modificacion-motivo" error={erroresCampos.motivo?.join(", ")}>
                <textarea
                  id="modificacion-motivo"
                  className="w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
                  rows={3}
                  value={formulario.motivo ?? ficha.motivo ?? ""}
                  onChange={(evento) => setFormulario((anterior) => ({ ...anterior, motivo: evento.target.value }))}
                />
              </FormField>
            </div>
            <div className="sm:col-span-2">
              <FormField label="Condiciones modificadas" htmlFor="modificacion-condiciones" error={erroresCampos.condiciones?.join(", ")}>
                <textarea
                  id="modificacion-condiciones"
                  className="w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
                  rows={3}
                  value={formulario.condiciones ?? ficha.condiciones ?? ""}
                  onChange={(evento) => setFormulario((anterior) => ({ ...anterior, condiciones: evento.target.value }))}
                />
              </FormField>
            </div>
          </div>
          <div className="mt-3">
            <Button type="submit" variant="primary" disabled={guardando}>
              Guardar datos
            </Button>
          </div>
        </form>
      ) : null}

      {esBorrador && permisos.gestionar ? (
        <section aria-labelledby="cobertura-adicional-titulo" className="mb-6">
          <h2 id="cobertura-adicional-titulo" className="text-lg font-semibold text-text-900">
            Cobertura adicional
          </h2>
          <p className="mt-3 text-sm text-text-600">
            Requerida: {ficha.cobertura.requerida_adicional} {ficha.moneda} · Asignada:{" "}
            {ficha.cobertura.total_asignado} {ficha.moneda}
            {ficha.cobertura.completa ? " · Cobertura completa" : ""}
          </p>
          {ficha.opciones?.certificados_elegibles?.length ? (
            <>
              <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Certificaciones elegibles">
                <table className="mt-3 w-full min-w-[600px] border-collapse text-left text-sm">
                  <thead className="bg-surface-subtle text-text-600">
                    <tr>
                      <th className="border-b border-border-subtle px-3 py-2 font-medium">Certificación</th>
                      <th className="border-b border-border-subtle px-3 py-2 font-medium">Ejercicio</th>
                      <th className="border-b border-border-subtle px-3 py-2 font-medium">Partida</th>
                      <th className="border-b border-border-subtle px-3 py-2 font-medium">Fuente</th>
                      <th className="border-b border-border-subtle px-3 py-2 font-medium">Saldo libre</th>
                      <th className="border-b border-border-subtle px-3 py-2 font-medium">Monto asignado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ficha.opciones.certificados_elegibles.map((certificado) => {
                      const asignado = ficha.cobertura.asignaciones.find(
                        (asignacion) => asignacion.certificado_id === certificado.id,
                      );
                      const inicial = montosAsignados[certificado.id] ?? asignado?.monto ?? "";
                      return (
                        <tr key={certificado.id} className="border-b border-border-subtle last:border-b-0">
                          <td className="px-3 py-2 text-text-900">{certificado.codigo}</td>
                          <td className="px-3 py-2 text-text-900">{certificado.anio}</td>
                          <td className="px-3 py-2 text-text-900">{certificado.partida}</td>
                          <td className="px-3 py-2 text-text-900">{certificado.fuente}</td>
                          <td className="px-3 py-2 text-text-900">
                            {certificado.saldo_libre} {certificado.moneda}
                          </td>
                          <td className="px-3 py-2">
                            <label className="sr-only" htmlFor={`asignar-${certificado.codigo}`}>
                              Monto asignado a {certificado.codigo}
                            </label>
                            <input
                              id={`asignar-${certificado.codigo}`}
                              type="text"
                              inputMode="decimal"
                              className="w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
                              value={inicial}
                              onChange={(evento) =>
                                setMontosAsignados((anterior) => ({
                                  ...anterior,
                                  [certificado.id]: evento.target.value,
                                }))
                              }
                            />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <div className="mt-3">
                <Button type="button" variant="secondary" disabled={guardando} onClick={() => void guardarCobertura()}>
                  Guardar cobertura
                </Button>
              </div>
            </>
          ) : (
            <p className="mt-3 text-sm text-text-600">No hay certificaciones elegibles disponibles.</p>
          )}
          <p className="mt-3 text-sm text-text-600">
            Vincular cobertura no consume la certificación ni crea compromisos presupuestarios (BUD-08).
          </p>
        </section>
      ) : null}

      {esBorrador && ficha.compromisos.aplica ? (
        <section aria-labelledby="compromisos-titulo" className="mb-6">
          <h2 id="compromisos-titulo" className="text-lg font-semibold text-text-900">
            Compromisos presupuestarios
          </h2>
          <p className={`mt-3 text-sm ${ficha.compromisos.permite ? "text-text-600" : "text-red-700"}`}>
            {ficha.compromisos.mensaje ??
              `Total: ${ficha.compromisos.total ?? "—"} ${ficha.compromisos.moneda ?? ""}`}
          </p>
        </section>
      ) : null}

      {esBorrador && permisos.formalizar ? (
        <section aria-labelledby="formalizacion-modificacion-titulo" className="mb-6">
          <h2 id="formalizacion-modificacion-titulo" className="text-lg font-semibold text-text-900">
            Formalización
          </h2>
          {ficha.pendientes.length > 0 ? (
            <>
              <h3 className="mt-3 text-sm font-medium text-text-900">Falta para formalizar</h3>
              <ul className="mt-2 list-inside list-disc text-sm text-text-600">
                {ficha.pendientes.map((pendiente) => (
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
          {ficha.opciones?.firmantes?.length ? (
            <FormField label="Cargo firmante" htmlFor="modificacion-firmante" className="mt-3">
              <select
                id="modificacion-firmante"
                className="w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
                value={folioFirmante}
                onChange={(evento) => setFolioFirmante(evento.target.value)}
              >
                <option value="">Seleccione</option>
                {ficha.opciones.firmantes.map((firmante) => (
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
            <Button
              type="button"
              variant="primary"
              disabled={!folioFirmante || guardando}
              onClick={() => setModalFormalizar(true)}
            >
              Formalizar
            </Button>
          </div>
          <ConfirmationDialog
            open={modalFormalizar}
            title="Formalizar la modificación"
            description="Se asignará el código, se sellará el documento y la modificación quedará congelada. El contrato original no cambia."
            confirmLabel="Formalizar"
            cancelLabel="Cancelar"
            onConfirm={async () => {
              await formalizar();
            }}
            onCancel={() => setModalFormalizar(false)}
          />
        </section>
      ) : null}

      {esBorrador && permisos.gestionar ? (
        <section aria-labelledby="descartar-borrador-titulo" className="mb-6">
          <h2 id="descartar-borrador-titulo" className="text-lg font-semibold text-text-900">
            Descartar borrador
          </h2>
          <div className="mt-3">
            <Button type="button" variant="secondary" disabled={guardando} onClick={() => setModalDescartar(true)}>
              Descartar borrador
            </Button>
          </div>
          <ConfirmationDialog
            open={modalDescartar}
            title="Descartar el borrador"
            description="Se eliminará este borrador. Las modificaciones formalizadas no se ven afectadas."
            confirmLabel="Descartar"
            cancelLabel="Cancelar"
            onConfirm={async () => {
              await descartar();
            }}
            onCancel={() => setModalDescartar(false)}
          />
        </section>
      ) : null}

      {!esBorrador ? (
        <section aria-labelledby="instrumento-formalizado-titulo" className="mb-6">
          <h2 id="instrumento-formalizado-titulo" className="text-lg font-semibold text-text-900">
            Instrumento formalizado
          </h2>
          <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="font-medium text-text-600">Código</dt>
              <dd className="text-text-900">{ficha.codigo ?? "—"}</dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Tipo</dt>
              <dd className="text-text-900">{ficha.tipo_etiqueta}</dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Fecha del instrumento</dt>
              <dd className="text-text-900">
                {ficha.fecha_instrumento ? formatearFechaDeNegocio(ficha.fecha_instrumento) : "—"}
              </dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Vigente desde</dt>
              <dd className="text-text-900">{ficha.vigente_desde ? formatearFechaDeNegocio(ficha.vigente_desde) : "—"}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="font-medium text-text-600">Motivo</dt>
              <dd className="break-words text-text-900">{ficha.motivo || "—"}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="font-medium text-text-600">Condiciones</dt>
              <dd className="break-words text-text-900">{ficha.condiciones || "—"}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="font-medium text-text-600">Referencia</dt>
              <dd className="break-words text-text-900">{ficha.referencia_instrumento || "—"}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="font-medium text-text-600">Documento</dt>
              <dd className="break-words text-text-900">
                {ficha.documento ? (
                  <>
                    {ficha.documento.titulo} · versión {ficha.documento.version} · huella SHA-256{" "}
                    {abreviarHuella(ficha.documento.sha256, 12)}{" "}
                    <Link className="text-brand-700 underline" to={`/documentos/${ficha.documento.id}`}>
                      Ver documento
                    </Link>
                  </>
                ) : (
                  "—"
                )}
              </dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Firmante</dt>
              <dd className="break-words text-text-900">
                {ficha.firmante ? `${ficha.firmante.cargo}${ficha.firmante.funcionario ? ` · ${ficha.firmante.funcionario}` : ""}` : "—"}
              </dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Límite de firma</dt>
              <dd className="text-text-900">{ficha.firmante?.limite ?? "—"}</dd>
            </div>
            {ficha.firmante?.conversion ? (
              <div className="sm:col-span-2">
                <dt className="font-medium text-text-600">Conversión</dt>
                <dd className="break-words text-text-900">
                  Comparado en VES con tasa oficial BCV:{" "}
                  {ficha.firmante.conversion.tasas
                    .map((tasa) => `${tasa.moneda} ${tasa.valor} del ${formatearFechaDeNegocio(tasa.fecha_efectiva)}`)
                    .join("; ")}{" "}
                  · monto {ficha.firmante.conversion.total_ves ?? "—"} VES, límite{" "}
                  {ficha.firmante.conversion.limite_ves ?? "—"} VES
                </dd>
              </div>
            ) : null}
            <div>
              <dt className="font-medium text-text-600">Formalizada</dt>
              <dd className="text-text-900">{ficha.formalizado_en ? formatearInstante(ficha.formalizado_en) : "—"}</dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Huella</dt>
              <dd className="break-words text-text-900" title={ficha.huella ?? undefined}>
                {ficha.huella ? abreviarHuella(ficha.huella) : "—"}
              </dd>
            </div>
          </dl>
          {ficha.cobertura.asignaciones.length > 0 ? (
            <div className="overflow-x-auto mt-3" tabIndex={0} role="region" aria-label="Cobertura adicional formalizada">
              <table className="w-full min-w-[600px] border-collapse text-left text-sm">
                <thead className="bg-surface-subtle text-text-600">
                  <tr>
                    <th className="border-b border-border-subtle px-3 py-2 font-medium">Certificación</th>
                    <th className="border-b border-border-subtle px-3 py-2 font-medium">Monto asignado</th>
                    <th className="border-b border-border-subtle px-3 py-2 font-medium">Ejercicio</th>
                    <th className="border-b border-border-subtle px-3 py-2 font-medium">Partida</th>
                    <th className="border-b border-border-subtle px-3 py-2 font-medium">Fuente</th>
                    <th className="border-b border-border-subtle px-3 py-2 font-medium">Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {ficha.cobertura.asignaciones.map((asignacion) => (
                    <tr key={asignacion.certificado_id} className="border-b border-border-subtle last:border-b-0">
                      <td className="px-3 py-2 text-text-900">{asignacion.codigo}</td>
                      <td className="px-3 py-2 text-text-900">
                        {asignacion.monto} {asignacion.moneda}
                      </td>
                      <td className="px-3 py-2 text-text-900">{asignacion.anio ?? "—"}</td>
                      <td className="px-3 py-2 text-text-900">{asignacion.partida}</td>
                      <td className="px-3 py-2 text-text-900">{asignacion.fuente}</td>
                      <td className="px-3 py-2 text-text-900">{asignacion.estado ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </section>
      ) : null}
    </PageContent>
  );
}
