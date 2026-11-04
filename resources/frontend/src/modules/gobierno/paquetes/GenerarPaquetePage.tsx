import { useState } from "react";
import { useNavigate, useParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Archive } from "lucide-react";

import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { FormField } from "@/components/FormField";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { formatearFecha } from "@/i18n";
import {
  AVISO_HUELLA_PAQUETE,
  CONSULTA_PAQUETES,
  ETIQUETAS_MOTIVO_EXCLUSION,
  ETIQUETAS_REFERENCIA_PAQUETE,
  abreviarHuella,
  formatearBytes,
  type PaqueteDetalle,
  type VistaPreviaPaquete,
} from "@/modules/gobierno/api";

export function GenerarPaquetePage(): React.JSX.Element {
  const { muestraId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { activeCompanyId } = useCompany();
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const puedeGenerar = tiene("gobierno_paquetes:generate", "empresa");

  const [proposito, setProposito] = useState("");
  const [errorCampo, setErrorCampo] = useState<string | undefined>(undefined);
  const [errorGeneral, setErrorGeneral] = useState<string | undefined>(undefined);
  const [clave, setClave] = useState(() => crypto.randomUUID());

  const consultaVistaPrevia = useQuery({
    queryKey: [...CONSULTA_PAQUETES, "vista-previa", activeCompanyId, muestraId],
    queryFn: () =>
      apiFetch<VistaPreviaPaquete>(
        `/gobierno/auditoria/muestras/${muestraId}/paquete/vista-previa`,
      ),
    enabled: puedeGenerar && Boolean(activeCompanyId) && muestraId !== "",
    retry: false,
  });

  const cabecera = (
    <PageHeader
      crumbs={[
        { label: "Gobierno" },
        { label: "Auditoría institucional", to: "/gobierno/auditoria" },
        { label: "Muestra", to: `/gobierno/auditoria/muestras/${muestraId}` },
      ]}
      title="Generar paquete de auditoría"
      description="Índice, manifiesto, huellas, metadatos de los eventos y copia de la evidencia autorizada de la muestra."
    />
  );

  async function enviar(): Promise<void> {
    const recortado = proposito.trim();
    if (recortado.length < 10 || recortado.length > 1000) {
      setErrorCampo("El propósito debe tener entre 10 y 1000 caracteres");
      return;
    }

    setErrorCampo(undefined);
    setErrorGeneral(undefined);

    try {
      const paquete = await apiFetch<PaqueteDetalle>(
        `/gobierno/auditoria/muestras/${muestraId}/paquetes`,
        {
          method: "POST",
          body: { proposito: recortado },
          idempotencyKey: clave,
        },
      );

      notify({ type: "success", title: `Paquete ${paquete.codigo} generado` });
      await queryClient.invalidateQueries({ queryKey: [...CONSULTA_PAQUETES] });
      navigate(`/gobierno/paquetes/${paquete.id}`);
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 422) {
          if (error.code === "VALIDATION_ERROR") {
            setErrorCampo(error.fieldErrors.proposito?.[0] ?? error.message);
          } else {
            setErrorGeneral(error.message);
          }
          return;
        }

        if (error.status === 409) {
          setErrorGeneral(error.message);
          setClave(crypto.randomUUID());
          return;
        }

        if (error.status === 403) {
          notify({ type: "error", title: "No tiene permiso para generar paquetes" });
          return;
        }
      }

      notify({ type: "error", title: "No fue posible generar el paquete" });
    }
  }

  if (!puedeGenerar) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para generar paquetes de auditoría."
        />
      </PageContent>
    );
  }

  if (consultaVistaPrevia.isLoading) {
    return (
      <PageContent>
        {cabecera}
        <LoadingState label="Calculando el alcance del paquete…" />
      </PageContent>
    );
  }

  if (consultaVistaPrevia.isError) {
    const error = consultaVistaPrevia.error;

    if (
      error instanceof ApiError &&
      error.status === 403 &&
      error.code === "MODULE_NOT_ENTITLED"
    ) {
      return (
        <PageContent>
          {cabecera}
          <EmptyState title="Módulo no habilitado" />
        </PageContent>
      );
    }

    if (error instanceof ApiError && error.status === 404) {
      return (
        <PageContent>
          {cabecera}
          <EmptyState
            title="Muestra no encontrada"
            description="La muestra no existe en la auditoría de este ente."
          />
        </PageContent>
      );
    }

    return (
      <PageContent>
        {cabecera}
        <ErrorState
          message="No fue posible cargar el alcance del paquete."
          onRetry={() => void consultaVistaPrevia.refetch()}
        />
      </PageContent>
    );
  }

  if (!consultaVistaPrevia.data) {
    return (
      <PageContent>
        {cabecera}
        <ErrorState
          message="No fue posible cargar el alcance del paquete."
          onRetry={() => void consultaVistaPrevia.refetch()}
        />
      </PageContent>
    );
  }

  const datos = consultaVistaPrevia.data;

  return (
    <PageContent>
      {cabecera}

      <section aria-labelledby="paquete-muestra" className="mt-6">
        <h2 id="paquete-muestra" className="text-lg font-semibold text-text-900">
          Muestra {datos.muestra.codigo}
        </h2>
        <dl className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <div className="rounded-md border border-border-default p-3">
            <dt className="text-xs text-text-600">Título</dt>
            <dd className="text-sm font-medium text-text-900">{datos.muestra.titulo}</dd>
          </div>
          <div className="rounded-md border border-border-default p-3">
            <dt className="text-xs text-text-600">Método</dt>
            <dd className="text-sm font-medium text-text-900">{datos.muestra.metodo}</dd>
          </div>
          {datos.muestra.semilla !== null && (
            <div className="rounded-md border border-border-default p-3">
              <dt className="text-xs text-text-600">Semilla</dt>
              <dd className="text-sm font-medium text-text-900">{datos.muestra.semilla}</dd>
            </div>
          )}
          <div className="rounded-md border border-border-default p-3">
            <dt className="text-xs text-text-600">Población</dt>
            <dd className="text-sm font-medium text-text-900">{datos.muestra.poblacion}</dd>
          </div>
          <div className="rounded-md border border-border-default p-3">
            <dt className="text-xs text-text-600">Tamaño</dt>
            <dd className="text-sm font-medium text-text-900">{datos.muestra.tamano}</dd>
          </div>
          <div className="rounded-md border border-border-default p-3">
            <dt className="text-xs text-text-600">Registrada por</dt>
            <dd className="text-sm font-medium text-text-900">
              {datos.muestra.creada_por ?? "—"}
            </dd>
          </div>
          <div className="rounded-md border border-border-default p-3">
            <dt className="text-xs text-text-600">Registrada el</dt>
            <dd className="text-sm font-medium text-text-900">
              {formatearFecha(datos.muestra.creada_en)}
            </dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="paquete-alcance" className="mt-6">
        <h2 id="paquete-alcance" className="text-lg font-semibold text-text-900">
          Contenido del paquete
        </h2>
        <dl className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <div className="rounded-md border border-border-default p-3">
            <dt className="text-xs text-text-600">Eventos</dt>
            <dd className="text-sm font-medium text-text-900">{datos.eventos}</dd>
          </div>
          <div className="rounded-md border border-border-default p-3">
            <dt className="text-xs text-text-600">Documentos incluidos</dt>
            <dd className="text-sm font-medium text-text-900">
              {datos.documentos_incluidos}
            </dd>
          </div>
          <div className="rounded-md border border-border-default p-3">
            <dt className="text-xs text-text-600">Documentos excluidos</dt>
            <dd className="text-sm font-medium text-text-900">
              {datos.documentos_excluidos}
            </dd>
          </div>
          <div className="rounded-md border border-border-default p-3">
            <dt className="text-xs text-text-600">Hallazgos</dt>
            <dd className="text-sm font-medium text-text-900">{datos.hallazgos}</dd>
          </div>
          <div className="rounded-md border border-border-default p-3">
            <dt className="text-xs text-text-600">Tamaño estimado</dt>
            <dd className="text-sm font-medium text-text-900">
              {formatearBytes(datos.bytes_estimados)}
            </dd>
          </div>
        </dl>

        {datos.paquetes_previos > 0 && (
          <p className="mt-3 text-sm text-text-700">
            Esta muestra ya tiene {datos.paquetes_previos} paquete(s) generado(s); se generará
            uno nuevo.
          </p>
        )}
      </section>

      {datos.excede_limite && (
        <p role="alert" className="mt-4 text-sm text-danger-600">
          {datos.motivo_limite}
        </p>
      )}

      {datos.documentos.length === 0 ? (
        <div className="mt-6">
          <EmptyState title="La muestra no referencia documentos" />
        </div>
      ) : (
        <div
          className="relative mt-4 overflow-x-auto"
          tabIndex={0}
          role="region"
          aria-label="Tabla de documentos del paquete"
        >
          <table className="w-full min-w-[720px] border-collapse text-sm">
            <caption className="sr-only">Documentos del paquete</caption>
            <thead>
              <tr className="border-b border-border-default text-left text-text-600">
                <th scope="col" className="px-3 py-2 font-medium">
                  Documento
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Estado
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Motivo
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Versión
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Tamaño
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Referencias
                </th>
              </tr>
            </thead>
            <tbody>
              {datos.documentos.map((documento) => (
                <tr key={documento.id} className="border-b border-border-subtle align-top">
                  <td className="px-3 py-2 text-text-700">
                    {abreviarHuella(documento.id)}
                  </td>
                  <td className="px-3 py-2 text-text-700">
                    {documento.estado === "INCLUIDO" ? "Incluido" : "Excluido"}
                  </td>
                  <td className="px-3 py-2 text-text-700">
                    {documento.motivo
                      ? ETIQUETAS_MOTIVO_EXCLUSION[documento.motivo]
                      : "—"}
                  </td>
                  <td className="px-3 py-2 text-text-700">
                    {documento.version ?? "—"}
                  </td>
                  <td className="px-3 py-2 text-text-700">
                    {documento.bytes !== null
                      ? formatearBytes(documento.bytes)
                      : "—"}
                  </td>
                  <td className="px-3 py-2 text-text-700">
                    {documento.referencias.length > 0
                      ? documento.referencias
                          .map((referencia) => ETIQUETAS_REFERENCIA_PAQUETE[referencia.tipo])
                          .join(", ")
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="mt-4 text-sm text-text-600">{AVISO_HUELLA_PAQUETE}</p>

      <form
        onSubmit={(e) => e.preventDefault()}
        noValidate
        className="mt-6"
      >
        <FormField
          label="Propósito"
          htmlFor="paquete-proposito"
          required
          error={errorCampo}
          help="Indique para qué y para quién se genera el paquete"
        >
          <textarea
            id="paquete-proposito"
            rows={3}
            maxLength={1000}
            value={proposito}
            onChange={(e) => {
              setProposito(e.target.value);
              if (errorCampo) setErrorCampo(undefined);
            }}
            aria-invalid={errorCampo ? true : undefined}
            className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
          />
        </FormField>

        {errorGeneral && (
          <p role="alert" className="mt-2 text-sm text-danger-600">
            {errorGeneral}
          </p>
        )}

        <div className="mt-4 flex flex-wrap gap-2">
          <AsyncButton
            variant="primary"
            disabled={datos.excede_limite}
            onClick={enviar}
          >
            <Archive className="mr-2 h-4 w-4" aria-hidden="true" />
            Generar paquete
          </AsyncButton>
          <Button
            variant="secondary"
            onClick={() => navigate(`/gobierno/auditoria/muestras/${muestraId}`)}
          >
            Cancelar
          </Button>
        </div>
      </form>
    </PageContent>
  );
}
