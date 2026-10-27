/** Catálogo — unidades de medida, conversiones y taxonomía (FR-002-010/030/035). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { TaxonomyNode, UnitOfMeasure } from "@/api/types";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

export function CatalogosPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();

  const [convFrom, setConvFrom] = useState("");
  const [convTo, setConvTo] = useState("");
  const [convFactor, setConvFactor] = useState("");

  const units = useQuery({
    queryKey: ["maestros", "unidades"],
    queryFn: () => apiFetch<UnitOfMeasure[]>("/maestros/catalogos/unidades"),
    retry: false,
  });
  const taxonomy = useQuery({
    queryKey: ["maestros", "taxonomia"],
    queryFn: () => apiFetch<TaxonomyNode[]>("/maestros/catalogos/taxonomia"),
    retry: false,
  });

  const createConversion = async (): Promise<void> => {
    if (!convFrom || !convTo) return;
    try {
      await apiFetch(`/maestros/catalogos/unidades/${convFrom}/conversiones`, {
        method: "POST",
        body: { from_unit_id: convFrom, to_unit_id: convTo, factor: Number(convFactor) || 1, rounding: 4 },
      });
      notify({ type: "success", title: "Conversión creada", description: `${convFrom} → ${convTo}` });
      setConvTo("");
      setConvFactor("");
      await queryClient.invalidateQueries({ queryKey: ["maestros", "unidades"] });
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear la conversión";
      notify({ type: "error", title: "No fue posible crear la conversión", description: message });
    }
  };

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Catálogo"
        description="Unidades de medida y taxonomía configurable."
        crumbs={[{ label: "Maestros" }, { label: "Catálogo" }]}
      />
      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-lg border border-border-default bg-surface-0 p-5">
          <h2 className="mb-3 text-base font-semibold text-text-900">Unidades de medida</h2>
          {units.isLoading ? <p className="text-sm text-text-500">Cargando…</p> : null}
          <ul className="divide-y divide-border-default">
            {(units.data ?? []).map((u) => (
              <li key={u.id} className="flex items-center justify-between py-2 text-sm">
                <span className="text-text-700">{u.name}</span>
                <span className="text-text-400">
                  {u.symbol} · {u.dimension}
                </span>
              </li>
            ))}
          </ul>

          {puede("POST", "/maestros/catalogos/unidades/_/conversiones") ? (
          <form className="mt-4 flex flex-wrap items-end gap-2 border-t border-border-default pt-4" onSubmit={(e) => e.preventDefault()}>
            <FormField label="De">
              <select value={convFrom} onChange={(e) => setConvFrom(e.target.value)} className="h-10 w-36 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                <option value="">Seleccionar…</option>
                {(units.data ?? []).map((u) => (
                  <option key={u.id} value={u.id}>{u.name}</option>
                ))}
              </select>
            </FormField>
            <FormField label="A">
              <select value={convTo} onChange={(e) => setConvTo(e.target.value)} className="h-10 w-36 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                <option value="">Seleccionar…</option>
                {(units.data ?? []).map((u) => (
                  <option key={u.id} value={u.id}>{u.name}</option>
                ))}
              </select>
            </FormField>
            <FormField label="Factor">
              <TextInput type="number" min="0" step="any" value={convFactor} onChange={(e) => setConvFactor(e.target.value)} placeholder="1" />
            </FormField>
            <AsyncButton type="submit" variant="secondary" onClick={createConversion}>Añadir conversión</AsyncButton>
          </form>
          ) : null}
        </section>

        <section className="rounded-lg border border-border-default bg-surface-0 p-5">
          <h2 className="mb-3 text-base font-semibold text-text-900">Taxonomía</h2>
          {taxonomy.isLoading ? <p className="text-sm text-text-500">Cargando…</p> : null}
          <ul className="divide-y divide-border-default">
            {(taxonomy.data ?? []).map((n) => (
              <li key={n.id} className="flex items-center justify-between py-2 text-sm">
                <span className="text-text-700">{n.name}</span>
                <span className="text-text-400">{n.level}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </PageContent>
  );
}
