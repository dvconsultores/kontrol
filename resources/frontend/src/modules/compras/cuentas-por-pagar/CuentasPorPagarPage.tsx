/** Cuentas por pagar — open items, pagos y aging (FR-004-070/071/073/075, WF-05). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { AgingResult, OpenItem, PagedResult, Party, PaymentSummary } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

const columnHelper = createColumnHelper<OpenItem>();

export function CuentasPorPagarPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const [newParty, setNewParty] = useState("");
  const [newAmount, setNewAmount] = useState("");
  const [advParty, setAdvParty] = useState("");
  const [advAmount, setAdvAmount] = useState("");
  const [schedParty, setSchedParty] = useState("");
  const [schedDue, setSchedDue] = useState("");
  const [schedAmount, setSchedAmount] = useState("");
  const [appSource, setAppSource] = useState("");
  const [appTarget, setAppTarget] = useState("");
  const [appAmount, setAppAmount] = useState("");

  const suppliers = useQuery({
    queryKey: ["maestros", "terceros"],
    queryFn: () => apiFetch<PagedResult<Party>>("/maestros/terceros"),
    retry: false,
  });
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

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["compras", "payments"] });
    void queryClient.invalidateQueries({ queryKey: ["compras", "open-items"] });
    void queryClient.invalidateQueries({ queryKey: ["compras", "aging"] });
  };

  const createPayment = async (): Promise<void> => {
    try {
      await apiFetch("/purchasing/payments", {
        method: "POST",
        body: { party_id: newParty, amount: Number(newAmount) || 0, currency: "VED", instruments: null },
      });
      notify({ type: "success", title: "Pago registrado", description: `${newAmount} VED` });
      setNewParty(""); setNewAmount("");
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible registrar el pago";
      notify({ type: "error", title: "No fue posible registrar el pago", description: message });
    }
  };

  const createAdvance = async (): Promise<void> => {
    try {
      await apiFetch("/purchasing/advances", {
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

  const createSchedule = async (): Promise<void> => {
    try {
      await apiFetch("/purchasing/payment-schedules", {
        method: "POST",
        body: { party_id: schedParty, due_date: schedDue || null, amount: Number(schedAmount) || 0 },
      });
      notify({ type: "success", title: "Cronograma registrado", description: `${schedAmount} VED` });
      setSchedParty(""); setSchedDue(""); setSchedAmount("");
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible registrar el cronograma";
      notify({ type: "error", title: "No fue posible registrar el cronograma", description: message });
    }
  };

  const applySource = async (): Promise<void> => {
    if (!appSource || !appTarget) return;
    try {
      await apiFetch("/purchasing/applications", {
        method: "POST",
        body: { source_type: "PAYMENT", source_id: appSource, target_open_item_id: appTarget, amount: Number(appAmount) || 0, currency: "VED", rate: null },
      });
      notify({ type: "success", title: "Aplicación registrada", description: `a ${appTarget}` });
      setAppSource(""); setAppTarget(""); setAppAmount("");
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible aplicar el pago";
      notify({ type: "error", title: "No fue posible aplicar el pago", description: message });
    }
  };

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

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Registrar pago</h2>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Proveedor" required>
            <select value={newParty} onChange={(e) => setNewParty(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(suppliers.data?.items ?? []).map((c) => (
                <option key={c.id} value={c.id}>{c.code} · {c.name}</option>
              ))}
            </select>
          </FormField>
          <FormField label="Monto (VED)" required>
            <TextInput type="number" value={newAmount} onChange={(e) => setNewAmount(e.target.value)} placeholder="0,00" required />
          </FormField>
          <AsyncButton type="submit" variant="primary" onClick={createPayment}>Registrar pago</AsyncButton>
        </form>
      </section>

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Anticipo a proveedor</h2>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Proveedor" required>
            <select value={advParty} onChange={(e) => setAdvParty(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(suppliers.data?.items ?? []).map((c) => (
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

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Cronograma de pago</h2>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Proveedor" required>
            <select value={schedParty} onChange={(e) => setSchedParty(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(suppliers.data?.items ?? []).map((c) => (
                <option key={c.id} value={c.id}>{c.code} · {c.name}</option>
              ))}
            </select>
          </FormField>
          <FormField label="Vence">
            <TextInput type="date" value={schedDue} onChange={(e) => setSchedDue(e.target.value)} />
          </FormField>
          <FormField label="Monto (VED)" required>
            <TextInput type="number" value={schedAmount} onChange={(e) => setSchedAmount(e.target.value)} placeholder="0,00" required />
          </FormField>
          <AsyncButton type="submit" variant="primary" onClick={createSchedule}>Registrar cronograma</AsyncButton>
        </form>
      </section>

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Aplicar pago a documento</h2>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Pago (fuente)" required>
            <select value={appSource} onChange={(e) => setAppSource(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(payments.data?.items ?? []).map((p) => (
                <option key={p.id} value={p.id}>{p.currency} {p.amount.toFixed(2)} · saldo {p.amount - p.applied}</option>
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
