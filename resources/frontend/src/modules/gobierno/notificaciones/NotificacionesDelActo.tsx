import { useState } from "react";
import { Link } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, apiFetch } from "@/api/client";
import { Button } from "@/components/Button";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_ACTOS,
  CONSULTA_NOTIFICACIONES,
  ETIQUETA_ESTADO_NOTIFICACION,
  ETIQUETA_TIPO_PERSONA,
  type Acto,
  type ListaNotificaciones,
} from "@/modules/gobierno/api";
import {
  type DatosDestinatario,
  DestinatarioFormulario,
} from "./DestinatarioFormulario";

interface NotificacionesDelActoProps {
  acto: Acto;
}

export function NotificacionesDelActo({
  acto,
}: NotificacionesDelActoProps): React.JSX.Element {
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const { activeCompanyId } = useCompany();
  const queryClient = useQueryClient();

  const puedeVer = tiene("gobierno_notificaciones:view", "empresa");
  const puedeEditar = tiene("gobierno_notificaciones:edit", "empresa");

  const [mostrarFormulario, setMostrarFormulario] = useState(false);
  const [erroresServidor, setErroresServidor] = useState<
    Record<string, string[]>
  >({});

  const notificacionesQuery = useQuery<ListaNotificaciones>({
    queryKey: [
      ...CONSULTA_NOTIFICACIONES,
      activeCompanyId,
      "del-acto",
      acto.id,
    ],
    queryFn: () =>
      apiFetch<ListaNotificaciones>(
        `/gobierno/notificaciones?anio=${acto.fecha.slice(0, 4)}&acto_id=${encodeURIComponent(
          acto.id,
        )}`,
      ),
    enabled: puedeVer,
    retry: false,
  });

  if (!puedeVer) {
    return (
      <p className="text-sm text-text-600">
        No tiene permiso para ver las notificaciones del acto.
      </p>
    );
  }

  if (notificacionesQuery.isLoading) {
    return <LoadingState label="Cargando notificaciones…" />;
  }

  if (notificacionesQuery.error) {
    return (
      <ErrorState
        message="No fue posible cargar las notificaciones."
        onRetry={() => void notificacionesQuery.refetch()}
      />
    );
  }

  const notificaciones = notificacionesQuery.data?.items ?? [];
  const resumen = acto.notificaciones;

  const confirmarDestinatario = async (datos: DatosDestinatario) => {
    try {
      await apiFetch("/gobierno/notificaciones", {
        method: "POST",
        body: {
          acto_id: acto.id,
          ...datos,
        },
      });

      notify({ type: "success", title: "Destinatario agregado" });
      setMostrarFormulario(false);
      setErroresServidor({});
      await queryClient.invalidateQueries({
        queryKey: [...CONSULTA_NOTIFICACIONES],
      });
      await queryClient.invalidateQueries({ queryKey: [...CONSULTA_ACTOS] });
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 403) {
          notify({ type: "error", title: "No tiene permiso para esta acción" });
          return;
        }

        if (
          error.status === 409 &&
          error.code === "GOV_NOTIFICATION_RECIPIENT_DUPLICATE"
        ) {
          setErroresServidor({ identificacion: [error.message] });
          return;
        }

        if (error.status === 422 && error.fieldErrors) {
          setErroresServidor(error.fieldErrors);
          return;
        }

        notify({
          type: "error",
          title: "No fue posible completar la operación",
          description: error.message,
        });
        return;
      }

      notify({
        type: "error",
        title: "No fue posible completar la operación",
      });
    }
  };

  let textoResumen: string | null = null;
  if (acto.estado === "EMITIDO") {
    if (!resumen || resumen.total === 0) {
      textoResumen =
        "Agregue a cada interesado para notificarle el acto (LOPA art. 73).";
    } else if (resumen.pendientes > 0) {
      textoResumen = `Faltan ${resumen.pendientes} por notificar de ${resumen.total}.`;
    }
  } else if (acto.estado === "EFICAZ") {
    textoResumen = "Todos los destinatarios están notificados.";
  }

  return (
    <div className="grid grid-cols-1 gap-4">
      {textoResumen && (
        <p role="status" className="text-sm text-text-600">
          {textoResumen}
        </p>
      )}

      {notificaciones.length > 0 && (
        <div className="relative overflow-x-auto">
          <table className="w-full min-w-[640px] border-collapse text-sm">
            <caption className="sr-only">
              Destinatarios de la notificación
            </caption>
            <thead>
              <tr className="border-b border-border-subtle text-left text-text-600">
                <th scope="col" className="px-3 py-2 font-medium">
                  Destinatario
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Cédula o RIF
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Estado
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Intentos
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Notificada el
                </th>
              </tr>
            </thead>
            <tbody>
              {notificaciones.map((notificacion) => (
                <tr
                  key={notificacion.id}
                  className="border-b border-border-subtle align-top"
                >
                  <td className="px-3 py-2">
                    <Link
                      to={`/gobierno/notificaciones/${notificacion.id}`}
                      className="font-medium text-brand-700 underline"
                    >
                      {notificacion.nombre}
                    </Link>
                    <p className="text-xs text-text-600">
                      {ETIQUETA_TIPO_PERSONA[notificacion.tipo_persona]}
                    </p>
                  </td>
                  <td className="px-3 py-2">{notificacion.identificacion}</td>
                  <td className="px-3 py-2">
                    {ETIQUETA_ESTADO_NOTIFICACION[notificacion.estado]}
                  </td>
                  <td className="px-3 py-2">{notificacion.intentos}</td>
                  <td className="px-3 py-2">
                    {notificacion.fecha_notificacion
                      ? formatearFechaDeNegocio(
                          notificacion.fecha_notificacion,
                        )
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {puedeEditar && acto.estado === "EMITIDO" && !mostrarFormulario && (
        <div>
          <Button
            variant="primary"
            onClick={() => {
              setErroresServidor({});
              setMostrarFormulario(true);
            }}
          >
            Agregar destinatario
          </Button>
        </div>
      )}

      {mostrarFormulario && (
        <DestinatarioFormulario
          titulo="Agregar destinatario"
          textoConfirmar="Agregar destinatario"
          onConfirmar={confirmarDestinatario}
          onCancelar={() => {
            setMostrarFormulario(false);
            setErroresServidor({});
          }}
          erroresServidor={erroresServidor}
        />
      )}
    </div>
  );
}
