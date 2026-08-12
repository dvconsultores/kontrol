/** Lotes de declaración — agrupación de declaraciones fiscales (FR-007-013). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { TaxReturnBatchSummary } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

const columnHelper = createColumnHelper<TaxReturnBatchSummary>();

const TAX_TYPES = ["IVA", "ISLR", "IGTF", "SNR"];

export function LotesDeclaracionPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const [newTaxType, setNewTaxType] = useState("IVA");
  const [newPeriod, setNewPeriod] = useState("");

  const query = useQuery({
    queryKey: ["fiscal", "lotes-declaracion"],
    queryFn: () => apiFetch<{ items: TaxReturnBatchSummary[] }>("/fiscal/tax-return-batches"),
    retry: false,
  });

  const refresh = async (): Promise<void> => {
    await queryClient.invalidateQueries({ queryKey: ["fiscal", "lotes-declaracion"] });
  };

  const createBatch = async (): Promise<void> => {
    try {
      await apiFetch("/fiscal/tax-return-batches", {
        method: "POST",
        body: { tax_type: newTaxType, period: newPeriod, files: null, totals: null },
      });
      notify({ type: "success", title: "Lote creado", description: `${newTaxType} · ${newPeriod}` });
      setNewPeriod("");
      void refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear el lote de declaración";
      notify({ type: "error", title: "No fue posible crear el lote de declaración", description: message });
    }
  };

  const columns = [
    columnHelper.accessor("tax_type", { header: "Impuesto" }),
    columnHelper.accessor("period", { header: "Período" }),
    columnHelper.accessor("status", { header: "Estado" }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Lotes de declaración"
        description="Agrupe declaraciones fiscales por impuesto y período para control y remisión."
        crumbs={[{ label: "Fiscal" }, { label: "Lotes de declaración" }]}
      />
      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Nuevo lote</h2>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Impuesto" required>
            <select value={newTaxType} onChange={(e) => setNewTaxType(e.target.value)} className="h-10 w-40 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              {TAX_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </FormField>
          <FormField label="Período" required help="Formato AAAA-MM">
            <TextInput value={newPeriod} onChange={(e) => setNewPeriod(e.target.value)} placeholder="2026-08" required />
          </FormField>
          <AsyncButton type="submit" variant="primary" onClick={createBatch}>Crear lote</AsyncButton>
        </form>
      </section>

      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar los lotes de declaración." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin lotes de declaración"
        emptyDescription="Aún no hay lotes de declaración registrados."
      />
    </PageContent>
  );
}
