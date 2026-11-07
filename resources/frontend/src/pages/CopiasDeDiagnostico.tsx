/** Copias de seguridad en Diagnóstico: estado derivado y política (FR-001-083). */
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { ApiError, apiFetch } from "@/api/client";
import type { BackupStatus } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Autorizado } from "@/components/Autorizado";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { formatearInstante } from "@/lib/fecha-de-negocio";

export const ESTADOS_RPO: Record<string, { etiqueta: string; correcto: boolean }> = {
  DISABLED: { etiqueta: "Planificación deshabilitada", correcto: false },
  MISCONFIGURED: { etiqueta: "Configuración incompleta", correcto: false },
  NO_VALID_BACKUP: { etiqueta: "Sin copia válida", correcto: false },
  LOCAL_ONLY: { etiqueta: "Solo copia local", correcto: false },
  RPO_BREACHED: { etiqueta: "RPO incumplido", correcto: false },
  DEGRADED: { etiqueta: "Degradado", correcto: false },
  RPO_AT_RISK: { etiqueta: "RPO en riesgo", correcto: false },
  RPO_MET: { etiqueta: "RPO cumplido", correcto: true },
  RPO_CERTIFIED: { etiqueta: "RPO certificado", correcto: true },
};

export function etiquetaDeEstadoRpo(estado: string): string {
  return ESTADOS_RPO[estado]?.etiqueta ?? estado;
}

export const MENSAJES_DE_POLITICA: Record<string, string> = {
  RPO_REQUIRED: "El RPO es obligatorio.",
  RPO_ABOVE_MAXIMUM: "El RPO no puede superar 15 minutos.",
  RPO_INVALID: "El RPO no es válido.",
  INTERVAL_REQUIRED: "El intervalo es obligatorio.",
  INTERVAL_INVALID: "El intervalo no es válido.",
  MARGIN_REQUIRED: "El margen es obligatorio.",
  MARGIN_INVALID: "El margen no es válido.",
  INTERVAL_EXCEEDS_RPO: "El intervalo y el margen deben quedar por debajo del RPO.",
  RETENTION_REQUIRED: "La retención es obligatoria.",
  RETENTION_INVALID: "La retención no es válida.",
  DESTINATION_REQUIRED: "El destino es obligatorio.",
  DESTINATION_UNSUPPORTED: "El destino no es compatible.",
  DESTINATION_LABEL_INVALID: "La etiqueta del destino no es válida.",
};

export function edadLegible(segundos: number | null): string {
  if (segundos === null) return "—";
  if (segundos >= 60) return `${Math.floor(segundos / 60)} min`;
  return `${segundos} s`;
}

export function tamanoLegible(bytes: number | null): string {
  if (bytes === null) return "—";
  if (bytes >= 1_048_576) return `${(bytes / 1_048_576).toFixed(1)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${bytes} B`;
}

export function CopiasDeDiagnostico({ estado }: { estado: BackupStatus }): React.JSX.Element {
  const { notify } = useNotifications();
  const queryClient = useQueryClient();
  const [rpo, setRpo] = useState(estado.configured_rpo_minutes?.toString() ?? "");
  const [intervalo, setIntervalo] = useState(estado.schedule_interval_minutes?.toString() ?? "");
  const [margen, setMargen] = useState(estado.safety_margin_minutes?.toString() ?? "");
  const [retencion, setRetencion] = useState(estado.retention_days?.toString() ?? "");
  const [copiasMinimas, setCopiasMinimas] = useState(estado.retention_min_copies?.toString() ?? "");
  const [etiquetaDestino, setEtiquetaDestino] = useState(estado.destination_label ?? "");
  const [planificacionHabilitada, setPlanificacionHabilitada] = useState(estado.scheduler_enabled);
  const [errores, setErrores] = useState<string[]>([]);
  const [mensajeAlerta, setMensajeAlerta] = useState<string | null>(null);

  const estadoRpo = ESTADOS_RPO[estado.rpo_state];
  const etiqueta = etiquetaDeEstadoRpo(estado.rpo_state);
  const correcto = estadoRpo?.correcto ?? false;

  const guardar = async (): Promise<void> => {
    setErrores([]);
    setMensajeAlerta(null);
    const body = {
      configured_rpo_minutes: rpo === "" ? null : Number(rpo),
      schedule_interval_minutes: intervalo === "" ? null : Number(intervalo),
      safety_margin_minutes: margen === "" ? null : Number(margen),
      retention_days: retencion === "" ? null : Number(retencion),
      retention_min_copies: copiasMinimas === "" ? null : Number(copiasMinimas),
      destination_label: etiquetaDestino === "" ? null : etiquetaDestino,
      destination_type: etiquetaDestino ? "MOUNTED_FILESYSTEM" : null,
      scheduler_enabled: planificacionHabilitada,
      version: estado.version,
    };
    try {
      await apiFetch("/system/backup-config", { method: "PUT", body });
      notify({ type: "success", title: "Configuración guardada", description: "La política de copias se actualizó correctamente." });
      await queryClient.invalidateQueries({ queryKey: ["diagnostics"] });
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.code === "BACKUP_POLICY_INVALID") {
          const codigos = error.details?.errors;
          const lista = Array.isArray(codigos) ? codigos.filter((c): c is string => typeof c === "string") : [];
          setErrores(lista.map((codigo) => MENSAJES_DE_POLITICA[codigo] ?? codigo));
        } else if (error.code === "VERSION_CONFLICT") {
          setMensajeAlerta("Otra persona cambió la configuración: revise los datos.");
          await queryClient.invalidateQueries({ queryKey: ["diagnostics"] });
        } else {
          throw error;
        }
      } else {
        throw error;
      }
    }
  };

  return (
    <section aria-labelledby="titulo-copias" className="mt-6 rounded-lg border border-border-default bg-surface-0 p-6">
      <h2 id="titulo-copias" className="text-base font-semibold text-text-900">Copias de seguridad</h2>
      <p role="status">
        <span className={`rounded px-2 py-0.5 text-xs font-medium ${correcto ? "bg-success-100 text-success-600" : "bg-danger-100 text-danger-600"}`}>
          {etiqueta}
        </span>
        {estado.running ? " Copia en curso" : null}
      </p>
      <dl className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <dt className="text-sm font-medium text-text-500">Última copia correcta</dt>
          <dd className="text-sm text-text-900">{formatearInstante(estado.last_successful_backup_at)}</dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-text-500">Última copia válida</dt>
          <dd className="text-sm text-text-900">{formatearInstante(estado.last_valid_backup_at)}</dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-text-500">Última copia durable fuera del anfitrión</dt>
          <dd className="text-sm text-text-900">{formatearInstante(estado.last_valid_durable_off_host_backup_at)}</dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-text-500">Antigüedad</dt>
          <dd className="text-sm text-text-900">{edadLegible(estado.backup_age_seconds)}</dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-text-500">Duración</dt>
          <dd className="text-sm text-text-900">{edadLegible(estado.backup_duration_seconds)}</dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-text-500">Tamaño</dt>
          <dd className="text-sm text-text-900">{tamanoLegible(estado.package_size_bytes)}</dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-text-500">Próxima copia</dt>
          <dd className="text-sm text-text-900">{formatearInstante(estado.next_schedule_at)}</dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-text-500">Destino</dt>
          <dd className="text-sm text-text-900">{estado.destination_label ?? "Sin destino"}</dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-text-500">Último error</dt>
          <dd className="text-sm text-text-900">{estado.last_sanitized_error ?? "Ninguno"}</dd>
        </div>
      </dl>
      {estado.retention_degraded ? (
        <p className="mt-4 text-sm text-danger-600">La retención está degradada: revise el destino.</p>
      ) : null}
      <Autorizado operacion={["PUT", "/system/backup-config"]}>
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField label="RPO (minutos)" help="Máximo 15 minutos">
            <TextInput value={rpo} onChange={(event) => setRpo(event.target.value)} inputMode="numeric" />
          </FormField>
          <FormField label="Intervalo (minutos)">
            <TextInput value={intervalo} onChange={(event) => setIntervalo(event.target.value)} inputMode="numeric" />
          </FormField>
          <FormField label="Margen (minutos)">
            <TextInput value={margen} onChange={(event) => setMargen(event.target.value)} inputMode="numeric" />
          </FormField>
          <FormField label="Retención (días)">
            <TextInput value={retencion} onChange={(event) => setRetencion(event.target.value)} inputMode="numeric" />
          </FormField>
          <FormField label="Copias mínimas">
            <TextInput value={copiasMinimas} onChange={(event) => setCopiasMinimas(event.target.value)} inputMode="numeric" />
          </FormField>
          <FormField label="Etiqueta del destino">
            <TextInput value={etiquetaDestino} onChange={(event) => setEtiquetaDestino(event.target.value)} />
          </FormField>
          <label className="flex items-center gap-2 text-sm text-text-900">
            <input
              type="checkbox"
              checked={planificacionHabilitada}
              onChange={(event) => setPlanificacionHabilitada(event.target.checked)}
            />
            Planificación habilitada
          </label>
          {errores.length > 0 ? (
            <ul role="alert" className="text-sm text-danger-600">
              {errores.map((error) => (
                <li key={error}>{error}</li>
              ))}
            </ul>
          ) : null}
          {mensajeAlerta ? (
            <p role="alert" className="text-sm text-danger-600">{mensajeAlerta}</p>
          ) : null}
          <AsyncButton onClick={guardar} loadingText="Guardando…">
            Guardar
          </AsyncButton>
        </div>
      </Autorizado>
    </section>
  );
}
