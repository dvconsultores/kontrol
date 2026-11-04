import { Link, useParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";

import { apiFetch, ApiError } from "@/api/client";
import { descargarArchivo } from "@/api/descargas";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { AsyncButton } from "@/components/AsyncButton";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { formatearFecha } from "@/i18n";
import {
  CONSULTA_PAQUETES,
  ETIQUETAS_MOTIVO_EXCLUSION,
  ETIQUETAS_RESULTADO_VERIFICACION,
  ETIQUETAS_MOTIVO_VERIFICACION,
  AVISO_HUELLA_PAQUETE,
  formatearBytes,
  abreviarHuella,
  type PaqueteDetalle,
} from "@/modules/gobierno/api";

export function PaquetePage(): React.JSX.Element {
  const { paqueteId = "" } = useParams();
  const { notify } = useNotifications();
  const { activeCompanyId } = useCompany();
  const { tiene } = useAutoridad();

  const puedeVer = tiene("gobierno_paquetes:view", "empresa");

  const consultaPaquete = useQuery({
    queryKey: [...CONSULTA_PAQUETES, "detalle", activeCompanyId, paqueteId],
    queryFn: () => apiFetch<PaqueteDetalle>(`/gobierno/paquetes/${paqueteId}`),
    enabled: puedeVer && Boolean(activeCompanyId) && paqueteId !== "",
    retry: false,
  });

  const descargar = async (
    ruta: string,
    reserva: string,
    titulo: string,
  ): Promise<void> => {
    try {
      await descargarArchivo(ruta, reserva);
      notify({ type: "success", title: titulo });
    } catch (error) {
      if (error instanceof ApiError && error.status === 403) {
        notify({
          type: "error",
          title: "No puede descargar el paquete",
          description: "No tiene permiso sobre todos los documentos que incluye.",
        });
        return;
      }
      notify({ type: "error", title: "No fue posible descargar" });
    }
  };

  const p = consultaPaquete.data;
  const cabecera = (
    <PageHeader
      crumbs={[{ label: "Gobierno" }, { label: "Paquetes de auditoría", to: "/gobierno/paquetes" }]}
      title={p ? `Paquete ${p.codigo}` : "Paquete"}
      description={p?.titulo}
      actions={
        p ? (
          <div className="flex flex-wrap gap-2">
            <AsyncButton
              onClick={() =>
                descargar(
                  `/gobierno/paquetes/${p.id}/descargar`,
                  `paquete-${p.codigo}.zip`,
                  "Paquete descargado",
                )
              }
            >
              <Download className="mr-2 h-4 w-4" aria-hidden="true" />
              Descargar paquete
            </AsyncButton>
            <AsyncButton
              variant="secondary"
              onClick={() =>
                descargar(
                  `/gobierno/paquetes/${p.id}/manifiesto`,
                  `manifiesto-${p.codigo}.json`,
                  "Manifiesto descargado",
                )
              }
            >
              Descargar manifiesto
            </AsyncButton>
          </div>
        ) : undefined
      }
    />
  );

  if (!puedeVer) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para ver el paquete."
        />
      </PageContent>
    );
  }

  if (consultaPaquete.isLoading) {
    return (
      <PageContent>
        {cabecera}
        <LoadingState label="Cargando el paquete…" />
      </PageContent>
    );
  }

  if (consultaPaquete.isError) {
    const error = consultaPaquete.error;
    if (
      error instanceof ApiError &&
      error.status === 403 &&
      error.code === "MODULE_NOT_ENTITLED"
    ) {
      return (
        <PageContent>
          {cabecera}
          <EmptyState
            title="Módulo no habilitado"
            description="El módulo de Gobierno no está habilitado en la licencia."
          />
        </PageContent>
      );
    }
    if (error instanceof ApiError && error.status === 404) {
      return (
        <PageContent>
          {cabecera}
          <EmptyState
            title="Paquete no encontrado"
            description="El paquete no existe en este ente."
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        {cabecera}
        <ErrorState
          message="No fue posible cargar el paquete."
          onRetry={() => void consultaPaquete.refetch()}
        />
      </PageContent>
    );
  }

  if (!p) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState
          title="Paquete no encontrado"
          description="El paquete no existe en este ente."
        />
      </PageContent>
    );
  }

  return (
    <PageContent>
      {cabecera}

      <section aria-labelledby="paquete-datos" className="mt-6">
        <h2 id="paquete-datos" className="text-lg font-semibold text-text-900">
          Datos del paquete
        </h2>
        <dl className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <div className="rounded-md border border-border-default p-3">
            <dt className="text-xs text-text-600">Muestra</dt>
            <dd className="text-sm font-medium text-text-900">
              <Link
                to={`/gobierno/auditoria/muestras/${p.muestra_id}`}
                className="font-medium text-brand-700 underline"
              >
                {p.muestra_codigo} · {p.muestra_titulo}
              </Link>
            </dd>
          </div>
          <div className="rounded-md border border-border-default p-3">
            <dt className="text-xs text-text-600">Propósito</dt>
            <dd className="text-sm font-medium text-text-900">{p.proposito}</dd>
          </div>
          <div className="rounded-md border border-border-default p-3">
            <dt className="text-xs text-text-600">Generación n.º</dt>
            <dd className="text-sm font-medium text-text-900">{p.numero_generacion}</dd>
          </div>
          <div className="rounded-md border border-border-default p-3">
            <dt className="text-xs text-text-600">Generado por</dt>
            <dd className="text-sm font-medium text-text-900">{p.generado_por ?? "—"}</dd>
          </div>
          <div className="rounded-md border border-border-default p-3">
            <dt className="text-xs text-text-600">Generado el</dt>
            <dd className="text-sm font-medium text-text-900">{formatearFecha(p.generado_en)}</dd>
          </div>
          <div className="rounded-md border border-border-default p-3">
            <dt className="text-xs text-text-600">Tamaño</dt>
            <dd className="text-sm font-medium text-text-900">{formatearBytes(p.bytes)}</dd>
          </div>
          <div className="rounded-md border border-border-default p-3">
            <dt className="text-xs text-text-600">Archivos</dt>
            <dd className="text-sm font-medium text-text-900">{p.archivos}</dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="paquete-huellas" className="mt-6">
        <h2 id="paquete-huellas" className="text-lg font-semibold text-text-900">
          Huellas de integridad
        </h2>
        <dl className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <div className="rounded-md border border-border-default p-3">
            <dt className="text-xs text-text-600">Huella del paquete (SHA-256)</dt>
            <dd className="text-sm font-medium text-text-900 font-mono text-xs break-all">
              {p.huella_paquete}
            </dd>
          </div>
          <div className="rounded-md border border-border-default p-3">
            <dt className="text-xs text-text-600">Huella del manifiesto (SHA-256)</dt>
            <dd className="text-sm font-medium text-text-900 font-mono text-xs break-all">
              {p.huella_manifiesto}
            </dd>
          </div>
        </dl>
        <p className="text-sm text-text-600">{AVISO_HUELLA_PAQUETE}</p>
      </section>

      <section aria-labelledby="paquete-contenido" className="mt-6">
        <h2 id="paquete-contenido" className="text-lg font-semibold text-text-900">
          Contenido
        </h2>

        <div
          className="relative mt-4 overflow-x-auto"
          tabIndex={0}
          role="region"
          aria-label="Eventos del paquete"
        >
          <table className="w-full min-w-[720px] border-collapse text-sm">
            <caption className="sr-only">Eventos del paquete</caption>
            <thead>
              <tr className="border-b border-border-default text-left text-text-600">
                <th scope="col" className="px-3 py-2 font-medium">Orden</th>
                <th scope="col" className="px-3 py-2 font-medium">Fecha</th>
                <th scope="col" className="px-3 py-2 font-medium">Proceso</th>
                <th scope="col" className="px-3 py-2 font-medium">Acción</th>
                <th scope="col" className="px-3 py-2 font-medium">Usuario</th>
                <th scope="col" className="px-3 py-2 font-medium">Objeto</th>
                <th scope="col" className="px-3 py-2 font-medium">Documentos</th>
              </tr>
            </thead>
            <tbody>
              {p.contenido.eventos.map((evento) => (
                <tr key={evento.id} className="border-b border-border-subtle align-top">
                  <td className="px-3 py-2 text-text-700">{evento.orden}</td>
                  <td className="px-3 py-2 text-text-700">{formatearFecha(evento.fecha)}</td>
                  <td className="px-3 py-2 text-text-700">{evento.proceso}</td>
                  <td className="px-3 py-2 text-text-700">{evento.accion}</td>
                  <td className="px-3 py-2 text-text-700">{evento.usuario ?? "—"}</td>
                  <td className="px-3 py-2 text-text-700">{evento.objeto?.tipo ?? "—"}</td>
                  <td className="px-3 py-2 text-text-700">{evento.documentos.length}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div
          className="relative mt-4 overflow-x-auto"
          tabIndex={0}
          role="region"
          aria-label="Documentos del paquete"
        >
          <table className="w-full min-w-[720px] border-collapse text-sm">
            <caption className="sr-only">Documentos del paquete</caption>
            <thead>
              <tr className="border-b border-border-default text-left text-text-600">
                <th scope="col" className="px-3 py-2 font-medium">Documento</th>
                <th scope="col" className="px-3 py-2 font-medium">Estado</th>
                <th scope="col" className="px-3 py-2 font-medium">Motivo</th>
                <th scope="col" className="px-3 py-2 font-medium">Versión</th>
                <th scope="col" className="px-3 py-2 font-medium">Tamaño</th>
                <th scope="col" className="px-3 py-2 font-medium">Huella</th>
              </tr>
            </thead>
            <tbody>
              {p.contenido.documentos.map((documento) => (
                <tr key={documento.id} className="border-b border-border-subtle align-top">
                  <td className="px-3 py-2 text-text-700">{abreviarHuella(documento.id)}</td>
                  <td className="px-3 py-2 text-text-700">
                    {documento.estado === "INCLUIDO" ? "Incluido" : "Excluido"}
                  </td>
                  <td className="px-3 py-2 text-text-700">
                    {documento.motivo ? ETIQUETAS_MOTIVO_EXCLUSION[documento.motivo] : "—"}
                  </td>
                  <td className="px-3 py-2 text-text-700">{documento.version ?? "—"}</td>
                  <td className="px-3 py-2 text-text-700">
                    {documento.bytes !== null ? formatearBytes(documento.bytes) : "—"}
                  </td>
                  <td className="px-3 py-2 text-text-700">
                    {documento.sha256 ? abreviarHuella(documento.sha256) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {p.contenido.hallazgos.length === 0 ? (
          <p className="text-sm text-text-700">
            Ningún hallazgo se originó en esta muestra.
          </p>
        ) : (
          <div
            className="relative mt-4 overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Hallazgos del paquete"
          >
            <table className="w-full min-w-[720px] border-collapse text-sm">
              <caption className="sr-only">Hallazgos del paquete</caption>
              <thead>
                <tr className="border-b border-border-default text-left text-text-600">
                  <th scope="col" className="px-3 py-2 font-medium">Código</th>
                  <th scope="col" className="px-3 py-2 font-medium">Título</th>
                  <th scope="col" className="px-3 py-2 font-medium">Riesgo</th>
                  <th scope="col" className="px-3 py-2 font-medium">Estado</th>
                  <th scope="col" className="px-3 py-2 font-medium">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {p.contenido.hallazgos.map((hallazgo) => (
                  <tr key={hallazgo.id} className="border-b border-border-subtle align-top">
                    <td className="px-3 py-2 text-text-700">
                      <Link
                        to={`/gobierno/hallazgos/${hallazgo.id}`}
                        className="font-medium text-brand-700 underline"
                      >
                        {hallazgo.codigo}
                      </Link>
                    </td>
                    <td className="px-3 py-2 text-text-700">{hallazgo.titulo}</td>
                    <td className="px-3 py-2 text-text-700">{hallazgo.riesgo}</td>
                    <td className="px-3 py-2 text-text-700">{hallazgo.estado}</td>
                    <td className="px-3 py-2 text-text-700">{hallazgo.acciones.length}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section aria-labelledby="paquete-verificaciones" className="mt-6">
        <h2 id="paquete-verificaciones" className="text-lg font-semibold text-text-900">
          Verificaciones
        </h2>
        {p.verificaciones.length === 0 ? (
          <p className="text-sm text-text-700">
            Este paquete aún no se ha verificado. Puede hacerlo en Gobierno › Paquetes de auditoría.
          </p>
        ) : (
          <ul className="mt-2 space-y-2">
            {p.verificaciones.map((verificacion) => (
              <li key={verificacion.id} className="text-sm text-text-700">
                {formatearFecha(verificacion.verificado_en)} ·{" "}
                {ETIQUETAS_RESULTADO_VERIFICACION[verificacion.resultado]} ·{" "}
                {verificacion.verificado_por ?? "—"}
                {verificacion.identico ? " · copia idéntica" : ""}
                {verificacion.motivos.length > 0 && (
                  <ul className="mt-1 list-disc pl-5">
                    {verificacion.motivos.map((motivo) => (
                      <li key={`${motivo.codigo}-${motivo.ruta}`}>
                        {ETIQUETAS_MOTIVO_VERIFICACION[motivo.codigo] ?? motivo.codigo}
                        {motivo.ruta ? ` (${motivo.ruta})` : ""}
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </PageContent>
  );
}
