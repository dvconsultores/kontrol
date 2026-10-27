/** Cuentas por cobrar — open items, cobros y aging (FR-005-040/041/046, WF-05). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { AgingResult, OpenItem, PagedResult, Party, PaymentSummary } from "@/api/types";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Autorizado } from "@/components/Autorizado";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

const columnHelper = createColumnHelper<OpenItem>();

export function CuentasPorCobrarPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();

  const [newParty, setNewParty] = useState("");
  const [newAmount, setNewAmount] = useState("");
  const [advParty, setAdvParty] = useState("");
  const [advAmount, setAdvAmount] = useState("");
  const [appSource, setAppSource] = useState("");
  const [appTarget, setAppTarget] = useState("");
  const [appAmount, setAppAmount] = useState("");

  const customers = useQuery({
    queryKey: ["maestros", "terceros"],
    queryFn: () => apiFetch<PagedResult<Party>>("/maestros/terceros"),
    retry: false,
  });
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

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["ventas", "collections"] });
    void queryClient.invalidateQueries({ queryKey: ["ventas", "open-items"] });
    void queryClient.invalidateQueries({ queryKey: ["ventas", "aging"] });
  };

  const createCollection = async (): Promise<void> => {
    try {
      await apiFetch("/sales/collections", {
        method: "POST",
        body: { party_id: newParty, amount: Number(newAmount) || 0, currency: "VED", instruments: null },
      });
      notify({ type: "success", title: "Cobro registrado", description: `${newAmount} VED` });
      setNewParty(""); setNewAmount("");
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible registrar el cobro";
      notify({ type: "error", title: "No fue posible registrar el cobro", description: message });
    }
  };

  const createAdvance = async (): Promise<void> => {
    try {
      await apiFetch("/sales/customer-advances", {
        method: "POST",
        body: { party_id: advParty, amount: Number(advAmount) || 0, currency: "VED" },
      });
      notify({ type: "success", title: "Anticipo registrado", description: `${advAmount} VED` });
      setAdvParty(""); setAdvAmount("");
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible registrar el anticipo";
      notify({ type: "error", title: "No fue posible registrar el anticipo", description: message });
    }
  };

  const applySource = async (): Promise<void> => {
    if (!appSource || !appTarget) return;
    try {
      await apiFetch("/sales/applications", {
        method: "POST",
        body: { source_type: "PAYMENT", source_id: appSource, target_open_item_id: appTarget, amount: Number(appAmount) || 0, currency: "VED", rate: null },
      });
      notify({ type: "success", title: "Aplicación registrada", description: `a ${appTarget}` });
      setAppSource(""); setAppTarget(""); setAppAmount("");
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible aplicar el cobro";
      notify({ type: "error", title: "No fue posible aplicar el cobro", description: message });
    }
  };

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

      <Autorizado operacion={["POST", "/sales/collections"]}>
        <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-2 text-base font-semibold text-text-900">Registrar cobro</h2>
          <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
            <FormField label="Cliente" required>
              <select value={newParty} onChange={(e) => setNewParty(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                <option value="">Seleccionar…</option>
                {(customers.data?.items ?? []).map((c) => (
                  <option key={c.id} value={c.id}>{c.code} · {c.name}</option>
                ))}
              </select>
            </FormField>
            <FormField label="Monto (VED)" required>
              <TextInput type="number" value={newAmount} onChange={(e) => setNewAmount(e.target.value)} placeholder="0,00" required />
            </FormField>
            <AsyncButton type="submit" variant="primary" onClick={createCollection}>Registrar cobro</AsyncButton>
          </form>
        </section>
      </Autorizado>

      <Autorizado operacion={["POST", "/sales/customer-advances"]}>
        <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-2 text-base font-semibold text-text-900">Anticipo de cliente</h2>
          <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
            <FormField label="Cliente" required>
              <select value={advParty} onChange={(e) => setAdvParty(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                <option value="">Seleccionar…</option>
                {(customers.data?.items ?? []).map((c) => (
                  <option key={c.id} value={c.id}>{c.code} · {c.name}</option>
                ))}
              </select>
            </FormField>
            <FormField label="Monto (VED)" required>
              <TextInput type="number" value={advAmount} onChange={(e) => setAdvAmount(e.target.value)} placeholder="0,00" required />
            </FormField>
            <AsyncButton type="submit" variant="primary" onClick={createAdvance}>Registrar anticipo</AsyncButton>
          </form>
        </section>
      </Autorizado>

      <Autorizado operacion={["POST", "/sales/applications"]}>
        <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-2 text-base font-semibold text-text-900">Aplicar cobro a documento</h2>
          <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
            <FormField label="Cobro (fuente)" required>
              <select value={appSource} onChange={(e) => setAppSource(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                <option value="">Seleccionar…</option>
                {(collections.data?.items ?? []).map((c) => (
                  <option key={c.id} value={c.id}>{c.currency} {c.amount.toFixed(2)} · saldo {c.amount - c.applied}</option>
                ))}
              </select>
            </FormField>
            <FormField label="Documento a aplicar" required>
              <select value={appTarget} onChange={(e) => setAppTarget(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                <option value="">Seleccionar…</option>
                {(openItems.data?.items ?? []).map((o) => (
                  <option key={o.id} value={o.id}>{o.source_document ?? o.id} · saldo {o.balance}</option>
                ))}
              </select>
            </FormField>
            <FormField label="Monto" required>
              <TextInput type="number" value={appAmount} onChange={(e) => setAppAmount(e.target.value)} placeholder="0,00" required />
            </FormField>
            <AsyncButton type="submit" variant="secondary" onClick={applySource}>Aplicar</AsyncButton>
          </form>
        </section>
      </Autorizado>

      <h2 className="mb-2 text-base font-semibold text-text-900">Cobros</h2>
      <div className="mb-4 rounded-lg border border-border-default">
        {(collections.data?.items ?? []).map((c) => (
          <div key={c.id} className="flex items-center justify-between border-b border-border-default px-4 py-2 text-sm last:border-b-0">
            <span className="text-text-700">
              {c.currency} {c.amount.toFixed(2)} · aplicado {c.applied.toFixed(2)}
            </span>
            <span className="text-text-500">{c.status}</span>
            <span className="flex gap-1">
              {c.allowed_actions?.submit && puede("POST", `/sales/collections/${c.id}/transition`) ? (
                <AsyncButton size="sm" variant="secondary" onClick={() => runCollection(c.id, "SUBMITTED")}>
                  enviar
                </AsyncButton>
              ) : null}
              {c.allowed_actions?.approve && puede("POST", `/sales/collections/${c.id}/transition`) ? (
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
