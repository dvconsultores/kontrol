/** Liberación de versión — changelog, gates y liberación (FR-011-010..013). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { HomologationRecordSummary, ReleaseVersionSummary } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { ErrorState } from "@/components/ErrorState";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

const columnHelper = createColumnHelper<ReleaseVersionSummary>();

const GATE_LABELS: Record<string, string> = {
  tests: "Pruebas",
  security: "Seguridad",
  backup: "Respaldo",
};

export function VersionesPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const [version, setVersion] = useState("");
  const [changelog, setChangelog] = useState("");
  const [gatesPassed, setGatesPassed] = useState<Record<string, boolean>>({
    tests: true,
    security: true,
    backup: true,
  });
  const [releaseHomologationId, setReleaseHomologationId] = useState("");
  const [releaseNotes, setReleaseNotes] = useState("");

  const releases = useQuery({
    queryKey: ["homologacion", "releases"],
    queryFn: () => apiFetch<{ items: ReleaseVersionSummary[] }>("/homologation/releases"),
    retry: false,
  });
  const records = useQuery({
    queryKey: ["homologacion", "records"],
    queryFn: () => apiFetch<{ items: HomologationRecordSummary[] }>("/homologation/records"),
    retry: false,
  });

  const invalidate = async (): Promise<void> => {
    await queryClient.invalidateQueries({ queryKey: ["homologacion"] });
  };

  const approvedRecords = (records.data?.items ?? []).filter((r) => r.homologated);

  const createRelease = async (): Promise<void> => {
    await apiFetch("/homologation/releases", {
      method: "POST",
      body: {
        version,
        changelog: { summary: changelog },
        gates: Object.fromEntries(Object.entries(gatesPassed).map(([k, v]) => [k, { passed: v }])),
        notes: null,
      },
    });
    notify({ type: "success", title: "Versión creada", description: `${version} en borrador.` });
    setVersion("");
    setChangelog("");
    await invalidate();
  };

  const promote = (id: string): Promise<void> =>
    apiFetch(`/homologation/releases/${id}/promote`, { method: "POST" }).then(async () => {
      notify({ type: "success", title: "Promovida", description: "La versión quedó como candidata." });
      await invalidate();
    });

  const releaseIt = (id: string): Promise<void> =>
    apiFetch<ReleaseVersionSummary>(`/homologation/releases/${id}/release`, {
      method: "POST",
      body: { homologation_id: releaseHomologationId || null, notes: releaseNotes || null },
    }).then((result) => {
      if (result.status === "RELEASED") {
        notify({ type: "success", title: "Liberada", description: `La versión ${result.version} fue liberada.` });
      } else {
        notify({ type: "error", title: "Bloqueada", description: (result.blocked_reasons?.reasons ?? []).join(", ") });
      }
      setReleaseHomologationId("");
      setReleaseNotes("");
      return invalidate();
    });

  if (releases.isLoading) {
    return <LoadingState rows={4} />;
  }
  if (releases.isError) {
    return (
      <PageContent maxWidth="md">
        <ErrorState message="No fue posible cargar las versiones." onRetry={() => void releases.refetch()} />
      </PageContent>
    );
  }

  const columns = [
    columnHelper.accessor("version", { header: "Versión" }),
    columnHelper.accessor("status", { header: "Estado" }),
    columnHelper.accessor("changelog", {
      header: "Changelog",
      cell: (info) => String((info.getValue() as Record<string, unknown>).summary ?? "—"),
    }),
    columnHelper.accessor("homologation_id", { header: "Homologación" }),
    columnHelper.accessor("released_by", { header: "Liberado por" }),
    columnHelper.accessor("released_at", {
      header: "Fecha",
      cell: (info) => (info.getValue() ? new Date(info.getValue() as string).toLocaleString("es-VE") : "—"),
    }),
    columnHelper.accessor("blocked_reasons", {
      header: "Bloqueos",
      cell: (info) => {
        const reasons = info.getValue()?.reasons ?? [];
        return reasons.length ? reasons.join(", ") : "—";
      },
    }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: (info) => {
        const row = info.row.original;
        return (
          <div className="flex flex-wrap gap-2">
            {row.status === "DRAFT" ? (
              <AsyncButton onClick={() => promote(row.id)} variant="secondary" loadingText="…">
                Promover
              </AsyncButton>
            ) : null}
            {row.status === "CANDIDATE" ? (
              <AsyncButton onClick={() => releaseIt(row.id)} variant="primary" loadingText="…">
                Liberar
              </AsyncButton>
            ) : null}
          </div>
        );
      },
    }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Versiones y liberación"
        description="La liberación a producción exige homologación aprobada, gates verdes y licencia válida."
        crumbs={[{ label: "Homologación" }, { label: "Versiones" }]}
      />

      <section className="rounded-lg border border-border-default bg-surface-0 p-6">
        <h2 className="text-base font-semibold text-text-900">Nueva versión</h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <FormField label="Versión (x.y.z)">
            <TextInput value={version} onChange={(e) => setVersion(e.target.value)} placeholder="1.1.0" />
          </FormField>
          <FormField label="Changelog (resumen)">
            <TextInput value={changelog} onChange={(e) => setChangelog(e.target.value)} placeholder="Descripción de cambios" />
          </FormField>
        </div>
        <div className="mt-4 flex flex-wrap gap-4">
          {Object.entries(GATE_LABELS).map(([key, label]) => (
            <label key={key} className="flex items-center gap-2 text-sm text-text-700">
              <input
                type="checkbox"
                checked={gatesPassed[key] ?? false}
                onChange={(e) => setGatesPassed((prev) => ({ ...prev, [key]: e.target.checked }))}
              />
              {label}
            </label>
          ))}
        </div>
        <div className="mt-4">
          <AsyncButton onClick={createRelease} loadingText="Creando…">
            Crear versión
          </AsyncButton>
        </div>
      </section>

      <section className="mt-6 rounded-lg border border-border-default bg-surface-0 p-6">
        <h2 className="text-base font-semibold text-text-900">Liberar versión</h2>
        <p className="mt-1 text-sm text-text-500">Seleccione la homologación aprobada que documenta esta versión.</p>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <FormField label="Homologación aprobada">
            <select
              value={releaseHomologationId}
              onChange={(e) => setReleaseHomologationId(e.target.value)}
              className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
            >
              <option value="">— Seleccione —</option>
              {approvedRecords.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.fiscal_version} · {r.formal_act_ref ?? "sin acto"}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Notas de liberación">
            <TextInput value={releaseNotes} onChange={(e) => setReleaseNotes(e.target.value)} placeholder="Observaciones (opcional)" />
          </FormField>
        </div>
      </section>

      <div className="mt-6">
        <DataTable
          columns={columns}
          data={releases.data?.items ?? []}
          loading={false}
          error={null}
          getRowId={(row) => row.id}
          emptyTitle="Sin versiones"
          emptyDescription="Cree la primera versión para iniciar el ciclo de liberación."
        />
      </div>
    </PageContent>
  );
}
