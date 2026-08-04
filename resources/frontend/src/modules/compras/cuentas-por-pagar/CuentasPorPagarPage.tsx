/** Cuentas por pagar — open items, pagos y aging (FR-004-070/071/073/075, WF-05). */
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

export function CuentasPorPagarPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const openItems = useQuery({
    queryKey: ["compras", "open-items"],
    queryFn: () => apiFetch<{ items: OpenItem[] }>("/purchasing/open-items"),
    retry: false,
  });
  const payments = useQuery({
    queryKey: ["compras", "payments"],
    queryFn: () => apiFetch<{ items: PaymentSummary[] }>("/purchasing/payments"),
    retry: false,
  });
  const aging = useQuery({
    queryKey: ["compras", "aging"],
    queryFn: () => apiFetch<AgingResult>("/purchasing/aging"),
    retry: false,
  });

  const columns = [
    columnHelper.accessor("source_document", { header: "Documento" }),
    columnHelper.accessor("party_id", { header: "Proveedor" }),
    columnHelper.accessor("original", { header: "Original" }),
    columnHelper.accessor("applied", { header: "Aplicado" }),
    columnHelper.accessor("balance", { header: "Saldo" }),
    columnHelper.accessor("due_date", { header: "Vence" }),
    columnHelper.accessor("status", { header: "Estado" }),
  ];

  const runPayment = async (id: string, target: string): Promise<void> => {
    await apiFetch(`/purchasing/payments/${id}/transition`, { method: "POST", body: { target } });
    await queryClient.invalidateQueries({ queryKey: ["compras", "payments"] });
    notify({ type: "success", title: "Pago actualizado", description: `Estado → ${target}` });
  };

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Cuentas por pagar"
        description="Open items, pagos con aprobación y aging (el saldo se calcula, no se edita)."
        crumbs={[{ label: "Compras" }, { label: "Cuentas por pagar" }]}
      />
      <div className="mb-4 grid gap-4 sm:grid-cols-4">
        <div className="rounded-lg border border-border-default bg-surface-0 p-4">
          <p className="text-sm text-text-500">Total CxP</p>
          <p className="text-2xl font-semibold text-text-900">{aging.data?.total.toFixed(2) ?? "—"}</p>
        </div>
        {Object.entries(aging.data?.buckets ?? {}).map(([bucket, value]) => (
          <div key={bucket} className="rounded-lg border border-border-default bg-surface-0 p-4">
            <p className="text-sm text-text-500">Vencido {bucket}</p>
            <p className="text-2xl font-semibold text-text-900">{value.toFixed(2)}</p>
          </div>
        ))}
      </div>

      <h2 className="mb-2 text-base font-semibold text-text-900">Pagos</h2>
      <div className="mb-4 rounded-lg border border-border-default">
        {(payments.data?.items ?? []).map((p) => (
          <div key={p.id} className="flex items-center justify-between border-b border-border-default px-4 py-2 text-sm last:border-b-0">
            <span className="text-text-700">
              {p.currency} {p.amount.toFixed(2)} · aplicado {p.applied.toFixed(2)}
            </span>
            <span className="text-text-500">{p.status}</span>
            <span className="flex gap-1">
              {p.allowed_actions?.submit ? (
                <AsyncButton size="sm" variant="secondary" onClick={() => runPayment(p.id, "SUBMITTED")}>
                  enviar
                </AsyncButton>
              ) : null}
              {p.allowed_actions?.approve ? (
                <AsyncButton size="sm" variant="secondary" onClick={() => runPayment(p.id, "APPROVED")}>
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
        emptyTitle="Sin documentos por pagar"
        emptyDescription="No hay open items pendientes."
      />
    </PageContent>
  );
}
