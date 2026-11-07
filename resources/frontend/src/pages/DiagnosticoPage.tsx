/** Diagnóstico — estado de servicios e instalación (FR-001-084). */
import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/api/client";
import type { DiagnosticsResponse } from "@/api/types";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { ErrorState } from "@/components/ErrorState";
import { ForbiddenState } from "@/components/ForbiddenState";
import { LoadingState } from "@/components/LoadingState";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { CopiasDeDiagnostico } from "@/pages/CopiasDeDiagnostico";

interface Fila {
  nombre: string;
  valor: string;
  correcto: boolean;
}

/** Las filas del diagnóstico, a partir de lo que responde el servidor. */
export function filasDeDiagnostico(d: DiagnosticsResponse): Fila[] {
  return [
    { nombre: "Entorno", valor: d.environment, correcto: true },
    { nombre: "Base de datos", valor: d.database.ok ? "ok" : "sin conexión", correcto: d.database.ok },
    { nombre: "Instalación", valor: d.installation.state ?? "sin identidad", correcto: d.installation.state !== null },
    { nombre: "Identificador", valor: d.installation.id ?? "—", correcto: d.installation.id !== null },
    { nombre: "Licencia", valor: d.license.mode ?? "sin licencia", correcto: d.license.activated },
  ];
}

/** El permiso que gobierna leer la identidad y la licencia de la instalación: el del diagnóstico. */
export const PERMISO_DE_DIAGNOSTICO = "license:view";

export function DiagnosticoPage(): React.JSX.Element {
  const { tiene } = useAutoridad();
  // El backend es la autoridad (401/403); aquí se decide antes de pedir nada, para no
  // pintar ni solicitar el diagnóstico a quien no puede verlo (FR-001-042).
  const permitido = tiene(PERMISO_DE_DIAGNOSTICO, "global");
  const query = useQuery({
    queryKey: ["diagnostics"],
    queryFn: () => apiFetch<DiagnosticsResponse>("/system/diagnostics"),
    enabled: permitido,
    retry: false,
  });

  if (!permitido) {
    return <ForbiddenState />;
  }

  return (
    <PageContent maxWidth="md">
      <PageHeader
        title="Diagnóstico"
        description="Estado de los servicios de esta instalación."
        crumbs={[{ label: "Diagnóstico" }]}
      />
      {query.isLoading ? <LoadingState rows={4} /> : null}
      {query.isError ? (
        <ErrorState message="No fue posible obtener el diagnóstico." onRetry={() => void query.refetch()} />
      ) : null}
      {query.data ? (
        <div className="rounded-lg border border-border-default bg-surface-0 p-6">
          <p className="text-xs font-medium uppercase tracking-wide text-text-400">Versión</p>
          <p className="mt-1 text-sm font-semibold text-text-900">{query.data.version}</p>
          <ul className="mt-4 space-y-2">
            {filasDeDiagnostico(query.data).map((fila) => (
              <li key={fila.nombre} className="flex items-center justify-between border-b border-border-default py-2">
                <span className="text-sm text-text-700">{fila.nombre}</span>
                <span
                  className={`rounded px-2 py-0.5 text-xs font-medium ${
                    fila.correcto ? "bg-success-100 text-success-600" : "bg-danger-100 text-danger-600"
                  }`}
                >
                  {fila.valor}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {query.data ? <CopiasDeDiagnostico estado={query.data.backup} /> : null}
    </PageContent>
  );
}
