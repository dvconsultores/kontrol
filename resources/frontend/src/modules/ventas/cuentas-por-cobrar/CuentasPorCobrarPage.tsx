/** Cuentas por cobrar — open items, cobros y aging (FR-005-040/041/046, WF-05). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";

import { apiFetch } from "@/api/client";
import type { AgingResult, OpenItem, PaymentSummary } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";

const columnHelper = createColumnHelper<OpenItem>();

export function CuentasPorCobrarPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const openItems = useQuery({
    queryKey: ["ventas", "open-items"],
    queryFn: () => apiFetch<{ items: OpenItem[] }>("/sales/open-items"),
    retry: false,
  });
  const collections = useQuery({
    queryKey: ["ventas", "collections"],
    queryFn: () => apiFetch<{ items: PaymentSummary[] }>("/sales/collections"),
    retry: false,
  });
  const aging = useQuery({
    queryKey: ["ventas", "aging"],
    queryFn: () => apiFetch<AgingResult>("/sales/aging"),
    retry: false,
  });

  const columns = [
    columnHelper.accessor("source_document", { header: "Documento" }),
    columnHelper.accessor("party_id", { header: "Cliente" }),
    columnHelper.accessor("original", { header: "Original" }),
    columnHelper.accessor("applied", { header: "Aplicado" }),
    columnHelper.accessor("balance", { header: "Saldo" }),
    columnHelper.accessor("due_date", { header: "Vence" }),
    columnHelper.accessor("status", { header: "Estado" }),
  ];

  const runCollection = async (id: string, target: string): Promise<void> => {
    await apiFetch(`/sales/collections/${id}/transition`, { method: "POST", body: { target } });
    await queryClient.invalidateQueries({ queryKey: ["ventas", "collections"] });
    notify({ type: "success", title: "Cobro actualizado", description: `Estado → ${target}` });
  };

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Cuentas por cobrar"
        description="Open items, cobros multimoneda y aging (el saldo se calcula, no se edita)."
        crumbs={[{ label: "Ventas" }, { label: "Cuentas por cobrar" }]}
      />
      <div className="mb-4 grid gap-4 sm:grid-cols-4">
        <div className="rounded-lg border border-border-default bg-surface-0 p-4">
          <p className="text-sm text-text-500">Total CxC</p>
          <p className="text-2xl font-semibold text-text-900">{aging.data?.total.toFixed(2) ?? "—"}</p>
        </div>
        {Object.entries(aging.data?.buckets ?? {}).map(([bucket, value]) => (
          <div key={bucket} className="rounded-lg border border-border-default bg-surface-0 p-4">
            <p className="text-sm text-text-500">Vencido {bucket}</p>
            <p className="text-2xl font-semibold text-text-900">{value.toFixed(2)}</p>
          </div>
        ))}
      </div>

      <h2 className="mb-2 text-base font-semibold text-text-900">Cobros</h2>
      <div className="mb-4 rounded-lg border border-border-default">
        {(collections.data?.items ?? []).map((c) => (
          <div key={c.id} className="flex items-center justify-between border-b border-border-default px-4 py-2 text-sm last:border-b-0">
            <span className="text-text-700">
              {c.currency} {c.amount.toFixed(2)} · aplicado {c.applied.toFixed(2)}
            </span>
            <span className="text-text-500">{c.status}</span>
            <span className="flex gap-1">
              {c.allowed_actions?.submit ? (
                <AsyncButton size="sm" variant="secondary" onClick={() => runCollection(c.id, "SUBMITTED")}>
                  enviar
                </AsyncButton>
              ) : null}
              {c.allowed_actions?.approve ? (
                <AsyncButton size="sm" variant="secondary" onClick={() => runCollection(c.id, "APPROVED")}>
                  aprobar
                </AsyncButton>
              ) : null}
            </span>
          </div>
        ))}
      </div>

      <DataTable
        columns={columns}
        data={openItems.data?.items ?? []}
        loading={openItems.isLoading}
        error={openItems.isError ? "No fue posible cargar los open items." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin documentos por cobrar"
        emptyDescription="No hay open items pendientes."
      />
    </PageContent>
  );
}
