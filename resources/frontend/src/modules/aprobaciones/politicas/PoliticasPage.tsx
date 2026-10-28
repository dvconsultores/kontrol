/**
 * Políticas de aprobación — listado por proceso y versión (Spec 045, WF-045-04).
 *
 * Las versiones cerradas se muestran: son la historia de la política, no ruido.
 * La edición ocurre en pantalla completa con URL propia (ADR-015 / P18).
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";
import { useNavigate } from "react-router";

import { Autorizado } from "@/components/Autorizado";
import { apiFetch } from "@/api/client";
import type { ApprovalPolicySummary } from "@/api/types";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";
import { formatearFechaDeInstante } from "@/lib/fecha-de-negocio";

const columnHelper = createColumnHelper<ApprovalPolicySummary>();

const STATUS_LABEL: Record<string, string> = {
  DRAFT: "Borrador",
  ACTIVE: "Activa",
  CLOSED: "Cerrada",
};

export function PoliticasPage(): React.JSX.Element {
  const { activeCompany } = useCompany();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const [processType, setProcessType] = useState("");
  const [code, setCode] = useState("");
  const [name, setName] = useState("");

  const companyId = activeCompany?.id ?? "";
  const query = useQuery({
    queryKey: ["aprobaciones", "policies", companyId],
    queryFn: () =>
      apiFetch<{ items: ApprovalPolicySummary[] }>(
        `/approvals/policies?company_id=${encodeURIComponent(companyId)}`,
      ),
    enabled: Boolean(companyId),
    retry: false,
  });

  const createPolicy = async (): Promise<void> => {
    if (!companyId) {
      notify({ type: "error", title: "Seleccione una empresa activa" });
      return;
    }
    try {
      const created = await apiFetch<ApprovalPolicySummary>("/approvals/policies", {
        method: "POST",
        body: { company_id: companyId, process_type: processType, code, name },
      });
      notify({
        type: "success",
        title: "Política creada",
        description: `${processType} v${created.version} (borrador)`,
      });
      setProcessType("");
      setCode("");
      setName("");
      void queryClient.invalidateQueries({ queryKey: ["aprobaciones", "policies"] });
      void navigate(`/aprobaciones/politicas/${created.id}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear la política";
      notify({ type: "error", title: "No fue posible crear la política", description: message });
    }
  };

  const columns = [
    columnHelper.accessor("process_type", { header: "Proceso" }),
    columnHelper.accessor("version", { header: "Versión", cell: (info) => `v${info.getValue()}` }),
    columnHelper.accessor("status", {
      header: "Estado",
      cell: (info) => STATUS_LABEL[info.getValue()] ?? info.getValue(),
    }),
    columnHelper.display({
      id: "vigencia",
      header: "Vigente",
      cell: ({ row }) =>
        row.original.valid_from
          ? `${formatearFechaDeInstante(row.original.valid_from)}${
              row.original.valid_to
                ? ` – ${formatearFechaDeInstante(row.original.valid_to)}`
                : ""
            }`
          : "—",
    }),
    columnHelper.display({
      id: "reglas",
      header: "Reglas",
      cell: ({ row }) => String(row.original.rules.length),
    }),
    columnHelper.accessor("requires_segregation", {
      header: "Segregación",
      cell: (info) => (info.getValue() ? "Sí" : "No"),
    }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => (
        <div className="flex justify-end">
          <AsyncButton
            size="sm"
            variant="secondary"
            aria-label={`Abrir política ${row.original.process_type} v${row.original.version}`}
            onClick={async () => {
              void navigate(`/aprobaciones/politicas/${row.original.id}`);
            }}
          >
            Abrir
          </AsyncButton>
        </div>
      ),
    }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Políticas de aprobación"
        description="Reglas de autorización por proceso. Las políticas se versionan: cambiarlas no altera lo ya aprobado."
        crumbs={[{ label: "Aprobaciones" }, { label: "Políticas" }]}
      />

      <Autorizado operacion={["POST", "/approvals/policies"]}>
        <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-2 text-base font-semibold text-text-900">Nueva política</h2>
          <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
            <FormField label="Tipo de proceso" required>
              <TextInput
                value={processType}
                onChange={(e) => setProcessType(e.target.value.toUpperCase())}
                placeholder="Ej. PURCHASE_ORDER"
                required
              />
            </FormField>
            <FormField label="Código" required>
              <TextInput value={code} onChange={(e) => setCode(e.target.value)} required />
            </FormField>
            <FormField label="Nombre" required>
              <TextInput value={name} onChange={(e) => setName(e.target.value)} required />
            </FormField>
            <AsyncButton type="submit" variant="primary" onClick={createPolicy}>
              Crear borrador
            </AsyncButton>
          </form>
        </section>
      </Autorizado>

      <DataTable
        data={query.data?.items ?? []}
        columns={columns}
        loading={query.isLoading}
        error={query.error instanceof Error ? query.error.message : null}
        emptyTitle="Sin políticas configuradas"
        emptyDescription="Cree una política para que las operaciones que la requieran pasen por aprobación."
        getRowId={(row) => row.id}
      />
    </PageContent>
  );
}
