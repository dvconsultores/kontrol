import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { PageHeader } from "@/components/PageHeader";
import { PageContent } from "@/layout/PageContent";
import { ErrorDeCarga } from "@/modules/gobierno/ocupacion/ErrorDeCarga";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_CONTRATOS,
  TIPOS_MODIFICACION,
  rutaContrato,
  rutaModificacion,
  type FichaModificacion,
  type HistoriaModificaciones,
  type TipoModificacion,
} from "./api";

function abreviarHuella(huella: string, cantidad = 16): string {
  return huella.length > cantidad ? `${huella.slice(0, cantidad)}…` : huella;
}

export function ContratoModificacionesPage() {
  const { contratoId } = useParams<{ contratoId: string }>();
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const [tipo, setTipo] = useState("");
  const [creando, setCreando] = useState(false);
  const [errorCreacion, setErrorCreacion] = useState<string | null>(null);

  const consulta = useQuery({
    queryKey: [...CONSULTA_CONTRATOS, activeCompanyId, "modificaciones", contratoId],
    queryFn: () => apiFetch<HistoriaModificaciones>(`/gobierno/contratos/${contratoId}/modificaciones`),
    enabled: Boolean(contratoId) && tiene("gobierno_contratos:view", "empresa"),
  });

  const historia = consulta.data;
  const permisos = {
    vista: tiene("gobierno_contratos:view", "empresa"),
    gestionar: tiene("gobierno_contratos:manage", "empresa"),
  };

  async function crearModificacion() {
    if (!contratoId || !tipo) return;
    setCreando(true);
    setErrorCreacion(null);
    try {
      const nueva = await apiFetch<FichaModificacion>(`/gobierno/contratos/${contratoId}/modificaciones`, {
        method: "POST",
        body: { tipo: tipo as TipoModificacion },
      });
      queryClient.setQueryData([...CONSULTA_CONTRATOS, activeCompanyId, "modificacion", nueva.id], nueva);
      void queryClient.invalidateQueries({ queryKey: [...CONSULTA_CONTRATOS, activeCompanyId] });
      navigate(rutaModificacion(contratoId, nueva.id));
    } catch (error) {
      setErrorCreacion(error instanceof ApiError ? error.message : "No se pudo crear la modificación.");
    } finally {
      setCreando(false);
    }
  }

  if (!contratoId || !permisos.vista) {
    return (
      <PageContent>
        <EmptyState title="Sin acceso" description="No tiene permiso para ver las modificaciones de este contrato." />
      </PageContent>
    );
  }

  if (consulta.isLoading) {
    return (
      <PageContent>
        <PageHeader
          crumbs={[{ label: "Gobierno" }, { label: "Contratos y órdenes", to: "/gobierno/contratos" }]}
          title="Modificaciones"
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
            crumbs={[{ label: "Gobierno" }, { label: "Contratos y órdenes", to: "/gobierno/contratos" }]}
            title="Modificaciones"
          />
          <EmptyState title="Contrato no encontrado" description="El contrato solicitado no existe o no está disponible." />
        </PageContent>
      );
    }
    return (
      <PageContent>
        <PageHeader
          crumbs={[{ label: "Gobierno" }, { label: "Contratos y órdenes", to: "/gobierno/contratos" }]}
          title="Modificaciones"
        />
        <ErrorDeCarga
          message={consulta.error instanceof Error ? consulta.error.message : "No se pudieron cargar las modificaciones."}
          onRetry={() => void consulta.refetch()}
        />
      </PageContent>
    );
  }

  if (!historia) return null;

  const plazoOriginal =
    historia.original.fecha_inicio && historia.original.fecha_fin
      ? `${formatearFechaDeNegocio(historia.original.fecha_inicio)} al ${formatearFechaDeNegocio(historia.original.fecha_fin)}`
      : "—";

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno" },
          { label: "Contratos y órdenes", to: "/gobierno/contratos" },
          { label: historia.contrato.identificacion, to: rutaContrato(contratoId) },
          { label: "Modificaciones" },
        ]}
        title={`Modificaciones · ${historia.contrato.identificacion}`}
      />

      <section aria-labelledby="condiciones-originales-titulo" className="mb-6">
        <h2 id="condiciones-originales-titulo" className="text-lg font-semibold text-text-900">
          Condiciones originales
        </h2>
        <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="font-medium text-text-600">Monto</dt>
            <dd className="text-text-900">
              {historia.original.monto} {historia.original.moneda}
            </dd>
          </div>
          <div>
            <dt className="font-medium text-text-600">Plazo</dt>
            <dd className="text-text-900">{plazoOriginal}</dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="font-medium text-text-600">Huella del contrato</dt>
            <dd className="break-words text-text-900" title={historia.original.huella ?? undefined}>
              {historia.original.huella ? abreviarHuella(historia.original.huella) : "—"}
            </dd>
          </div>
        </dl>
        <p className="mt-3 text-sm text-text-600">
          El contrato original no se modifica: cada cambio es un instrumento nuevo.
        </p>
      </section>

      <section aria-labelledby="condiciones-vigentes-titulo" className="mb-6">
        <h2 id="condiciones-vigentes-titulo" className="text-lg font-semibold text-text-900">
          Condiciones vigentes al {formatearFechaDeNegocio(historia.vigente.fecha)}
        </h2>
        <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="font-medium text-text-600">Monto vigente</dt>
            <dd className="text-text-900">
              {historia.vigente.monto} {historia.contrato.moneda}
            </dd>
          </div>
          <div>
            <dt className="font-medium text-text-600">Fin del plazo vigente</dt>
            <dd className="text-text-900">
              {historia.vigente.fecha_fin ? formatearFechaDeNegocio(historia.vigente.fecha_fin) : "—"}
            </dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="font-medium text-text-600">Según</dt>
            <dd className="text-text-900">{historia.vigente.modificacion_codigo ?? "Contrato original"}</dd>
          </div>
        </dl>
        {historia.vigente.programadas.length > 0 ? (
          <p className="mt-3 text-sm text-text-600">Programadas: {historia.vigente.programadas.join(", ")}</p>
        ) : null}
      </section>

      <section aria-labelledby="historial-titulo" className="mb-6">
        <h2 id="historial-titulo" className="text-lg font-semibold text-text-900">
          Historial
        </h2>
        {historia.historial.length === 0 ? (
          <p className="mt-3 text-sm text-text-600">Este contrato no tiene modificaciones formalizadas.</p>
        ) : (
          <ol className="mt-3 space-y-6">
            <li className="rounded-md border border-border-subtle bg-white p-4">
              <h3 className="text-sm font-semibold text-text-900">Contrato original</h3>
              <p className="mt-1 text-sm text-text-600">
                Monto {historia.original.monto} {historia.original.moneda} · plazo {plazoOriginal}
              </p>
            </li>
            {historia.historial.map((nodo) => (
              <li key={nodo.id} className="rounded-md border border-border-subtle bg-white p-4">
                <h3 className="text-sm font-semibold text-text-900">
                  {nodo.tipo_etiqueta} {nodo.codigo}
                </h3>
                <dl className="mt-2 grid gap-2 text-sm sm:grid-cols-2">
                  <div>
                    <dt className="font-medium text-text-600">Vigente desde</dt>
                    <dd className="text-text-900">{formatearFechaDeNegocio(nodo.vigente_desde)}</dd>
                  </div>
                  <div>
                    <dt className="font-medium text-text-600">Fecha del instrumento</dt>
                    <dd className="text-text-900">{formatearFechaDeNegocio(nodo.fecha_instrumento)}</dd>
                  </div>
                  {nodo.plazo ? (
                    <div className="sm:col-span-2">
                      <dt className="font-medium text-text-600">Cambio de plazo</dt>
                      <dd className="text-text-900">
                        del {formatearFechaDeNegocio(nodo.plazo.anterior)} al {formatearFechaDeNegocio(nodo.plazo.nuevo)}
                      </dd>
                    </div>
                  ) : null}
                  {nodo.monto ? (
                    <div className="sm:col-span-2">
                      <dt className="font-medium text-text-600">Cambio de monto</dt>
                      <dd className="text-text-900">
                        {nodo.monto.anterior} {historia.contrato.moneda} → {nodo.monto.nuevo}{" "}
                        {historia.contrato.moneda} ({nodo.monto.delta})
                      </dd>
                    </div>
                  ) : null}
                  {nodo.condiciones ? (
                    <div className="sm:col-span-2">
                      <dt className="font-medium text-text-600">Condiciones</dt>
                      <dd className="break-words text-text-900">{nodo.condiciones}</dd>
                    </div>
                  ) : null}
                  <div className="sm:col-span-2">
                    <dt className="font-medium text-text-600">Motivo</dt>
                    <dd className="break-words text-text-900">{nodo.motivo || "—"}</dd>
                  </div>
                  <div>
                    <dt className="font-medium text-text-600">Autoridad</dt>
                    <dd className="text-text-900">
                      {nodo.firmante.cargo}
                      {nodo.firmante.funcionario ? ` · ${nodo.firmante.funcionario}` : ""}
                    </dd>
                  </div>
                  <div>
                    <dt className="font-medium text-text-600">Documento</dt>
                    <dd className="break-words text-text-900">
                      {nodo.documento.titulo} · versión {nodo.documento.version} · huella{" "}
                      {abreviarHuella(nodo.documento.sha256, 12)}
                    </dd>
                  </div>
                  <div className="sm:col-span-2">
                    <dt className="font-medium text-text-600">Huella</dt>
                    <dd className="break-words text-text-900" title={nodo.huella}>
                      {abreviarHuella(nodo.huella)}
                    </dd>
                  </div>
                  <div className="sm:col-span-2">
                    <dt className="font-medium text-text-600">Cobertura adicional</dt>
                    <dd className="break-words text-text-900">
                      {nodo.cobertura_adicional.length > 0
                        ? nodo.cobertura_adicional.map((c) => `${c.codigo} ${c.monto}`).join(", ")
                        : "—"}
                    </dd>
                  </div>
                </dl>
                <Link
                  className="mt-3 inline-block text-sm text-brand-700 underline"
                  to={rutaModificacion(contratoId, nodo.id)}
                >
                  Ver ficha de {nodo.codigo}
                </Link>
              </li>
            ))}
          </ol>
        )}
      </section>

      {permisos.gestionar ? (
        <section aria-labelledby="nueva-modificacion-titulo" className="mb-6">
          <h2 id="nueva-modificacion-titulo" className="text-lg font-semibold text-text-900">
            Nueva modificación
          </h2>
          {historia.borrador ? (
            <Link
              className="mt-3 inline-block text-sm text-brand-700 underline"
              to={rutaModificacion(contratoId, historia.borrador.id)}
            >
              Continuar el borrador ({historia.borrador.tipo_etiqueta})
            </Link>
          ) : historia.puede_crear ? (
            <div className="mt-3">
              <FormField label="Tipo de modificación" htmlFor="modificacion-tipo">
                <select
                  id="modificacion-tipo"
                  className="w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
                  value={tipo}
                  onChange={(evento) => setTipo(evento.target.value)}
                >
                  <option value="">Seleccione</option>
                  {TIPOS_MODIFICACION.map((opcion) => (
                    <option key={opcion.codigo} value={opcion.codigo}>
                      {opcion.etiqueta}
                    </option>
                  ))}
                </select>
              </FormField>
              {errorCreacion ? (
                <div role="alert" className="mt-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                  {errorCreacion}
                </div>
              ) : null}
              <Button
                type="button"
                variant="primary"
                disabled={!tipo || creando}
                onClick={() => void crearModificacion()}
              >
                Nueva modificación
              </Button>
            </div>
          ) : (
            <p className="mt-3 text-sm text-text-600">{historia.motivo_no_crear}</p>
          )}
        </section>
      ) : null}
    </PageContent>
  );
}
