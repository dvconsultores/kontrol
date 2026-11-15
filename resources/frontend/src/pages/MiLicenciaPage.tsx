/**
 * MiLicencia — estado de la licencia, ruta completa (FR-001-054, DOC-07 §13.1).
 * La ve quien tiene `license:view` (FR-010-113): el backend es la autoridad —`GET /license/detail`
 * responde 401/403—; aquí se decide antes de pedir nada, para no pintar ni solicitar el detalle
 * a quien no puede verlo.
 */
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { ApiError, apiFetch } from "@/api/client";
import type { InstallationRequest, LicenseStatus } from "@/api/types";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { PERMISO_DE_LICENCIA } from "@/app/contexts/LicenseContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { ErrorState } from "@/components/ErrorState";
import { ForbiddenState } from "@/components/ForbiddenState";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { formatearFechaDeInstante } from "@/lib/fecha-de-negocio";
import {
  descargarTexto,
  nombreDeArchivoDeSolicitud,
  serializarSolicitud,
  validarSolicitud,
} from "@/lib/solicitud-de-activacion";

const MENSAJE_SESION =
  "La sesión venció. Inicie sesión nuevamente para obtener la solicitud de activación.";
const MENSAJE_PERMISO =
  "No tiene permiso para consultar la solicitud de activación. Se requiere license:view.";
const MENSAJE_RED =
  "No fue posible conectar con KONTROL para obtener la solicitud de activación.";

export function MiLicenciaPage(): React.JSX.Element {
  const { notify } = useNotifications();
  const { tiene } = useAutoridad();
  const [proofRef, setProofRef] = useState("");
  const [solicitudEnCurso, setSolicitudEnCurso] = useState<"descarga" | "copia" | null>(null);

  const permitido = tiene(PERMISO_DE_LICENCIA, "global");
  const query = useQuery({
    queryKey: ["license", "detail"],
    queryFn: () => apiFetch<LicenseStatus>("/license/detail"),
    retry: false,
    enabled: permitido,
  });

  const submitProof = async (): Promise<void> => {
    await apiFetch("/license/renewal-request", {
      method: "POST",
      body: { payment_proof_ref: proofRef },
    });
    notify({
      type: "success",
      title: "Comprobante registrado",
      description: "Su comprobante de renovación fue enviado para revisión.",
    });
    setProofRef("");
    await query.refetch();
  };

  const obtenerSolicitud = async (accion: "descarga" | "copia"): Promise<void> => {
    setSolicitudEnCurso(accion);
    try {
      let solicitada: unknown;
      try {
        solicitada = await apiFetch<unknown>("/license/installation-request");
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          notify({ type: "error", title: "Solicitud de activación", description: MENSAJE_SESION });
          return;
        }
        if (error instanceof ApiError && error.status === 403) {
          notify({ type: "error", title: "Solicitud de activación", description: MENSAJE_PERMISO });
          return;
        }
        if (error instanceof ApiError) {
          notify({
            type: "error",
            title: "Solicitud de activación",
            description: "No fue posible obtener la solicitud de activación.",
          });
          return;
        }
        notify({ type: "error", title: "Solicitud de activación", description: MENSAJE_RED });
        return;
      }

      let solicitud: InstallationRequest;
      try {
        solicitud = validarSolicitud(solicitada);
      } catch {
        notify({
          type: "error",
          title: "Solicitud de activación",
          description:
            "La solicitud de activación recibida no es válida (INVALID_INSTALLATION_REQUEST).",
        });
        return;
      }

      const serializada = serializarSolicitud(solicitud);
      if (accion === "descarga") {
        try {
          descargarTexto(serializada, nombreDeArchivoDeSolicitud(solicitud.installation_id));
        } catch {
          notify({
            type: "error",
            title: "Solicitud de activación",
            description: "No fue posible descargar la solicitud de activación.",
          });
          return;
        }
        notify({
          type: "success",
          title: "Solicitud descargada",
          description: "Entregue el archivo al propietario de KONTROL por un canal controlado.",
        });
        return;
      }

      try {
        if (!navigator.clipboard) {
          throw new Error("clipboard no disponible");
        }
        await navigator.clipboard.writeText(serializada);
      } catch {
        notify({
          type: "error",
          title: "Solicitud de activación",
          description: "No fue posible copiar la solicitud al portapapeles.",
        });
        return;
      }
      notify({
        type: "success",
        title: "Solicitud copiada",
        description: "Pegue la solicitud en el canal controlado acordado con el propietario de KONTROL.",
      });
    } finally {
      setSolicitudEnCurso(null);
    }
  };

  if (!permitido) {
    return <ForbiddenState />;
  }
  if (query.isLoading) {
    return <LoadingState rows={4} />;
  }
  if (query.isError) {
    return (
      <PageContent maxWidth="md">
        <ErrorState message="No fue posible consultar el estado de la licencia." onRetry={() => void query.refetch()} />
      </PageContent>
    );
  }
  const license = query.data as LicenseStatus;

  return (
    <PageContent maxWidth="lg">
      <PageHeader
        title="Mi licencia"
        description="Estado de la licencia anual de esta instalación."
        crumbs={[{ label: "Mi licencia" }]}
      />

      <div className="grid gap-4 rounded-lg border border-border-default bg-surface-0 p-6 sm:grid-cols-2">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-text-400">Instalación</p>
          <p className="mt-1 font-mono text-sm text-text-900">{license.installation_id}</p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-text-400">Modo</p>
          <p className="mt-1 text-sm font-semibold text-text-900">
            {license.mode.replaceAll("_", " ")}
          </p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-text-400">Período pagado</p>
          <p className="mt-1 text-sm text-text-900">
            {license.period_start ? formatearFechaDeInstante(license.period_start) : "—"}
            {" a "}
            {license.period_end ? formatearFechaDeInstante(license.period_end) : "—"}
          </p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-text-400">Modo solo consulta desde</p>
          <p className="mt-1 text-sm text-text-900">
            {license.read_only_start ? formatearFechaDeInstante(license.read_only_start) : "—"}
          </p>
        </div>
      </div>

      {license.mode === "PENDING" && (
        <section
          aria-labelledby="solicitud-activacion"
          className="mt-6 rounded-lg border border-border-default bg-surface-0 p-6"
        >
          <h2 id="solicitud-activacion" className="text-base font-semibold text-text-900">
            Solicitud de activación
          </h2>
          <p className="mt-1 text-sm text-text-500">
            La solicitud contiene la identidad pública de esta instalación, necesaria para
            registrarla y emitir la licencia. Entréguela al propietario de KONTROL por un canal
            controlado.
          </p>
          <div className="mt-4 flex flex-col gap-3 sm:flex-row">
            <AsyncButton
              onClick={() => obtenerSolicitud("descarga")}
              loadingText="Descargando…"
              disabled={solicitudEnCurso !== null}
              className="w-full sm:w-auto"
            >
              Descargar solicitud
            </AsyncButton>
            <AsyncButton
              onClick={() => obtenerSolicitud("copia")}
              loadingText="Copiando…"
              disabled={solicitudEnCurso !== null}
              className="w-full sm:w-auto"
            >
              Copiar solicitud
            </AsyncButton>
          </div>
        </section>
      )}

      <section className="mt-6 rounded-lg border border-border-default bg-surface-0 p-6">
        <h2 className="text-base font-semibold text-text-900">Renovación anual</h2>
        <p className="mt-1 text-sm text-text-500">
          Realice el pago y registre el comprobante. La renovación se confirma únicamente por el propietario de KONTROL.
        </p>
        <div className="mt-4 flex flex-wrap items-end gap-3">
          <FormField label="Referencia del comprobante" className="min-w-64 flex-1">
            <TextInput
              value={proofRef}
              onChange={(e) => setProofRef(e.target.value)}
              placeholder="Banco, fecha y referencia"
            />
          </FormField>
          <AsyncButton onClick={submitProof} loadingText="Registrando…">
            Cargar comprobante
          </AsyncButton>
        </div>
      </section>
    </PageContent>
  );
}
