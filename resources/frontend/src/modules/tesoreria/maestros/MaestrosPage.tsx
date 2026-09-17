/** Maestros financieros de tesorería (FR-006-012, DOC-02 §3). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import { hoyDeNegocio } from "@/lib/fecha-de-negocio";
import type {
  CashboxSummary,
  CurrencySummary,
  FinancialAccountSummary,
  FinancialBankSummary,
  PaymentMethodSummary,
  TreasuryInstrumentSummary,
} from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { FormField } from "@/components/FormField";
import { MoneyInput } from "@/components/MoneyInput";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

const TABS = ["Bancos", "Cuentas", "Cajas", "Métodos", "Instrumentos", "Monedas"] as const;
type Tab = (typeof TABS)[number];

export function MaestrosPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const [tab, setTab] = useState<Tab>("Bancos");

  const banks = useQuery({
    queryKey: ["tesoreria", "banks"],
    queryFn: () => apiFetch<{ items: FinancialBankSummary[] }>("/treasury/banks"),
    retry: false,
  });
  const accounts = useQuery({
    queryKey: ["tesoreria", "accounts"],
    queryFn: () => apiFetch<{ items: FinancialAccountSummary[] }>("/treasury/accounts"),
    retry: false,
  });
  const cashboxes = useQuery({
    queryKey: ["tesoreria", "cashboxes"],
    queryFn: () => apiFetch<{ items: CashboxSummary[] }>("/treasury/cashboxes"),
    retry: false,
  });
  const methods = useQuery({
    queryKey: ["tesoreria", "payment-methods"],
    queryFn: () => apiFetch<{ items: PaymentMethodSummary[] }>("/treasury/payment-methods"),
    retry: false,
  });
  const instruments = useQuery({
    queryKey: ["tesoreria", "instruments"],
    queryFn: () => apiFetch<{ items: TreasuryInstrumentSummary[] }>("/treasury/instruments"),
    retry: false,
  });
  const currencies = useQuery({
    queryKey: ["tesoreria", "currencies"],
    queryFn: () => apiFetch<{ items: CurrencySummary[] }>("/treasury/currencies"),
    retry: false,
  });

  // Formularios
  const [bankName, setBankName] = useState("");
  const [accName, setAccName] = useState("");
  const [accBank, setAccBank] = useState("");
  const [cashboxName, setCashboxName] = useState("");
  const [methodName, setMethodName] = useState("");
  const [instrumentName, setInstrumentName] = useState("");
  const [instrumentMethod, setInstrumentMethod] = useState("");
  const [currencyCode, setCurrencyCode] = useState("");
  const [rate, setRate] = useState("");

  const invalidateAll = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["tesoreria"] });
  };

  const createBank = async (): Promise<void> => {
    await apiFetch("/treasury/banks", { method: "POST", body: { code: bankName.replace(/\s+/g, "-").toUpperCase(), name: bankName } });
    notify({ type: "success", title: "Banco creado", description: bankName });
    setBankName("");
    invalidateAll();
  };

  const createAccount = async (): Promise<void> => {
    await apiFetch("/treasury/accounts", { method: "POST", body: { bank_id: accBank, code: accName.replace(/\s+/g, "-").toUpperCase(), name: accName } });
    notify({ type: "success", title: "Cuenta creada", description: accName });
    setAccName("");
    invalidateAll();
  };

  const createCashbox = async (): Promise<void> => {
    await apiFetch("/treasury/cashboxes", { method: "POST", body: { code: cashboxName.replace(/\s+/g, "-").toUpperCase(), name: cashboxName } });
    notify({ type: "success", title: "Caja creada", description: cashboxName });
    setCashboxName("");
    invalidateAll();
  };

  const createMethod = async (): Promise<void> => {
    await apiFetch("/treasury/payment-methods", { method: "POST", body: { code: methodName.replace(/\s+/g, "-").toUpperCase(), name: methodName, kind: "OTHER" } });
    notify({ type: "success", title: "Método creado", description: methodName });
    setMethodName("");
    invalidateAll();
  };

  const createInstrument = async (): Promise<void> => {
    await apiFetch("/treasury/instruments", { method: "POST", body: { method_id: instrumentMethod, code: instrumentName.replace(/\s+/g, "-").toUpperCase(), name: instrumentName } });
    notify({ type: "success", title: "Instrumento creado", description: instrumentName });
    setInstrumentName("");
    invalidateAll();
  };

  const createCurrency = async (): Promise<void> => {
    await apiFetch("/treasury/currencies", { method: "POST", body: { code: currencyCode.toUpperCase(), name: currencyCode.toUpperCase() } });
    notify({ type: "success", title: "Moneda creada", description: currencyCode.toUpperCase() });
    setCurrencyCode("");
    invalidateAll();
  };

  const loadRate = async (currencyId: string): Promise<void> => {
    await apiFetch("/treasury/exchange-rates", { method: "POST", body: { currency_id: currencyId, rate_date: hoyDeNegocio(), rate: Number(rate) || 0 } });
    notify({ type: "success", title: "Tasa registrada", description: `Tasa ${rate} cargada.` });
    setRate("");
    invalidateAll();
  };

  const item = (label: string, body: React.JSX.Element): React.JSX.Element => (
    <div className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
      <h3 className="mb-3 text-sm font-semibold text-text-900">{label}</h3>
      {body}
    </div>
  );

  const row = (label: string, value: string): React.JSX.Element => (
    <div key={label} className="flex items-center justify-between border-b border-border-default px-4 py-2 text-sm last:border-b-0">
      <span className="text-text-700">{label}</span>
      <span className="text-text-500">{value}</span>
    </div>
  );

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Maestros financieros"
        description="Bancos, cuentas, cajas, métodos e instrumentos, monedas y tasas (FR-006-012)."
        crumbs={[{ label: "Tesorería" }, { label: "Maestros" }]}
      />

      <nav aria-label="Maestros financieros" className="mb-4 flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            aria-pressed={tab === t}
            className={`h-9 rounded-md border px-3 text-sm transition-colors ${
              tab === t ? "border-brand-600 bg-brand-600 text-white" : "border-border-default bg-surface-0 text-text-500 hover:bg-surface-100"
            }`}
          >
            {t}
          </button>
        ))}
      </nav>

      {tab === "Bancos" ? (
        <>
          {item("Registrar banco", (
            <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
              <FormField label="Nombre">
                <TextInput value={bankName} onChange={(e) => setBankName(e.target.value)} />
              </FormField>
              <AsyncButton type="submit" variant="secondary" onClick={createBank}>Crear</AsyncButton>
            </form>
          ))}
          {item("Bancos", (
            <div>{(banks.data?.items ?? []).map((b) => row(b.name, `${b.code} · ${b.status}`))}</div>
          ))}
        </>
      ) : null}

      {tab === "Cuentas" ? (
        <>
          {item("Registrar cuenta", (
            <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
              <FormField label="Banco">
                <select value={accBank} onChange={(e) => setAccBank(e.target.value)} className="h-10 w-52 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                  <option value="">Seleccionar…</option>
                  {(banks.data?.items ?? []).map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
                </select>
              </FormField>
              <FormField label="Nombre">
                <TextInput value={accName} onChange={(e) => setAccName(e.target.value)} />
              </FormField>
              <AsyncButton type="submit" variant="secondary" onClick={createAccount}>Crear</AsyncButton>
            </form>
          ))}
          {item("Cuentas", (
            <div>{(accounts.data?.items ?? []).map((a) => row(`${a.name} · ${a.currency}`, `${a.code} · ${a.status}`))}</div>
          ))}
        </>
      ) : null}

      {tab === "Cajas" ? (
        <>
          {item("Registrar caja", (
            <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
              <FormField label="Nombre">
                <TextInput value={cashboxName} onChange={(e) => setCashboxName(e.target.value)} />
              </FormField>
              <AsyncButton type="submit" variant="secondary" onClick={createCashbox}>Crear</AsyncButton>
            </form>
          ))}
          {item("Cajas", (
            <div>{(cashboxes.data?.items ?? []).map((c) => row(`${c.name} · ${c.currency}`, `${c.code} · ${c.status}`))}</div>
          ))}
        </>
      ) : null}

      {tab === "Métodos" ? (
        <>
          {item("Registrar método de pago", (
            <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
              <FormField label="Nombre">
                <TextInput value={methodName} onChange={(e) => setMethodName(e.target.value)} />
              </FormField>
              <AsyncButton type="submit" variant="secondary" onClick={createMethod}>Crear</AsyncButton>
            </form>
          ))}
          {item("Métodos", (
            <div>{(methods.data?.items ?? []).map((m) => row(`${m.name} · ${m.kind}`, `${m.code} · ${m.status}`))}</div>
          ))}
        </>
      ) : null}

      {tab === "Instrumentos" ? (
        <>
          {item("Registrar instrumento", (
            <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
              <FormField label="Método">
                <select value={instrumentMethod} onChange={(e) => setInstrumentMethod(e.target.value)} className="h-10 w-52 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                  <option value="">Seleccionar…</option>
                  {(methods.data?.items ?? []).map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
                </select>
              </FormField>
              <FormField label="Nombre">
                <TextInput value={instrumentName} onChange={(e) => setInstrumentName(e.target.value)} />
              </FormField>
              <AsyncButton type="submit" variant="secondary" onClick={createInstrument}>Crear</AsyncButton>
            </form>
          ))}
          {item("Instrumentos", (
            <div>{(instruments.data?.items ?? []).map((i) => row(i.name, `${i.code} · ${i.status}`))}</div>
          ))}
        </>
      ) : null}

      {tab === "Monedas" ? (
        <>
          {item("Registrar moneda", (
            <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
              <FormField label="Código ISO">
                <TextInput value={currencyCode} onChange={(e) => setCurrencyCode(e.target.value)} placeholder="Ej. USD" />
              </FormField>
              <AsyncButton type="submit" variant="secondary" onClick={createCurrency}>Crear</AsyncButton>
            </form>
          ))}
          {item("Monedas y tasas", (
            <div>
              {(currencies.data?.items ?? []).map((c) => (
                <div key={c.id} className="flex flex-wrap items-center justify-between gap-2 border-b border-border-default px-4 py-2 text-sm last:border-b-0">
                  <span className="text-text-700">{c.code} · {c.name ?? ""}</span>
                  <span className="flex items-center gap-2">
                    <MoneyInput className="w-28" value={rate} onChange={(e) => setRate(e.target.value)} placeholder="Tasa" />
                    <AsyncButton size="sm" variant="secondary" onClick={() => loadRate(c.id)}>cargar tasa</AsyncButton>
                  </span>
                </div>
              ))}
              {(currencies.data?.items ?? []).length === 0 ? <p className="px-4 py-2 text-sm text-text-500">Sin monedas aún.</p> : null}
            </div>
          ))}
        </>
      ) : null}
    </PageContent>
  );
}
