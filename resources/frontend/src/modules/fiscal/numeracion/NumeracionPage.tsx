/** Numeración y números de control — series y lotes con asignación atómica (FR-007-010/011/012). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { ControlBatchSummary, ControlNumberSummary, NumberSeriesSummary } from "@/api/types";
import { Autorizado } from "@/components/Autorizado";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

export function NumeracionPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const [docType, setDocType] = useState("INVOICE");
  const [prefix, setPrefix] = useState("FV");
  const [rangeFrom, setRangeFrom] = useState("1001");
  const [rangeTo, setRangeTo] = useState("1100");

  const series = useQuery({
    queryKey: ["fiscal", "number-series"],
    queryFn: () => apiFetch<{ items: NumberSeriesSummary[] }>("/fiscal/number-series"),
    retry: false,
  });
  const batches = useQuery({
    queryKey: ["fiscal", "control-batches"],
    queryFn: () => apiFetch<{ items: ControlBatchSummary[] }>("/fiscal/control-batches"),
    retry: false,
  });
  const controls = useQuery({
    queryKey: ["fiscal", "control-numbers"],
    queryFn: () => apiFetch<{ items: ControlNumberSummary[] }>("/fiscal/control-numbers"),
    retry: false,
  });

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["fiscal"] });
  };

  const createSeries = async (): Promise<void> => {
    await apiFetch("/fiscal/number-series", { method: "POST", body: { document_type: docType, prefix } });
    notify({ type: "success", title: "Serie creada", description: `${prefix} · ${docType}` });
    refresh();
  };

  const createBatch = async (): Promise<void> => {
    await apiFetch("/fiscal/control-batches", { method: "POST", body: { range_from: rangeFrom, range_to: rangeTo, printer: "IMP-1" } });
    notify({ type: "success", title: "Lote creado", description: `Rango ${rangeFrom}–${rangeTo}` });
    refresh();
  };

  const section = (title: string, body: React.JSX.Element): React.JSX.Element => (
    <div className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
      <h2 className="mb-2 text-base font-semibold text-text-900">{title}</h2>
      {body}
    </div>
  );

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Numeración y números de control"
        description="Series/correlativos y lotes de imprenta con asignación atómica e inalterable (FR-007-010/012)."
        crumbs={[{ label: "Fiscal" }, { label: "Numeración" }]}
      />

      <Autorizado operacion={["POST", "/fiscal/number-series"]}>
        {section("Crear serie", (
          <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
            <FormField label="Tipo de documento">
              <select value={docType} onChange={(e) => setDocType(e.target.value)} className="h-10 w-44 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                <option value="INVOICE">Factura</option>
                <option value="CREDIT_NOTE">Nota de crédito</option>
                <option value="DEBIT_NOTE">Nota de débito</option>
              </select>
            </FormField>
            <FormField label="Prefijo">
              <TextInput value={prefix} onChange={(e) => setPrefix(e.target.value)} />
            </FormField>
            <AsyncButton type="submit" variant="secondary" onClick={createSeries}>
              Crear serie
            </AsyncButton>
          </form>
        ))}
      </Autorizado>

      {section("Series", (
        <div>
          {(series.data?.items ?? []).map((s) => (
            <div key={s.id} className="flex items-center justify-between border-b border-border-default px-4 py-2 text-sm last:border-b-0">
              <span className="text-text-700">{s.prefix ?? ""} · {s.document_type}</span>
              <span className="text-text-500">siguiente: {s.next_number}</span>
            </div>
          ))}
          {(series.data?.items ?? []).length === 0 ? <p className="text-sm text-text-500">Sin series.</p> : null}
        </div>
      ))}

      <Autorizado operacion={["POST", "/fiscal/control-batches"]}>
        {section("Crear lote de control", (
          <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
            <FormField label="Desde">
              <TextInput value={rangeFrom} onChange={(e) => setRangeFrom(e.target.value)} />
            </FormField>
            <FormField label="Hasta">
              <TextInput value={rangeTo} onChange={(e) => setRangeTo(e.target.value)} />
            </FormField>
            <AsyncButton type="submit" variant="secondary" onClick={createBatch}>
              Cargar lote
            </AsyncButton>
          </form>
        ))}
      </Autorizado>

      {section("Lotes de control", (
        <div>
          {(batches.data?.items ?? []).map((b) => (
            <div key={b.id} className="flex items-center justify-between border-b border-border-default px-4 py-2 text-sm last:border-b-0">
              <span className="text-text-700">{b.printer ?? "Imprenta"} · {b.range_from}–{b.range_to}</span>
              <span className="text-text-500">{b.status}</span>
            </div>
          ))}
          {(batches.data?.items ?? []).length === 0 ? <p className="text-sm text-text-500">Sin lotes.</p> : null}
        </div>
      ))}

      {section("Números de control (últimos)", (
        <div>
          {(controls.data?.items ?? []).slice(0, 50).map((c) => (
            <div key={c.id} className="flex items-center justify-between border-b border-border-default px-4 py-1.5 text-sm last:border-b-0">
              <span className="text-text-700">{c.value}</span>
              <span className="text-text-500">{c.state}</span>
            </div>
          ))}
          {(controls.data?.items ?? []).length === 0 ? <p className="text-sm text-text-500">Sin números de control cargados.</p> : null}
        </div>
      ))}
    </PageContent>
  );
}
