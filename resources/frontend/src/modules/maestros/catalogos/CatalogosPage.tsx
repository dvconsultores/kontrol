/** Catálogo — unidades de medida y taxonomía (FR-002-010/030). */
import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/api/client";
import type { TaxonomyNode, UnitOfMeasure } from "@/api/types";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";

export function CatalogosPage(): React.JSX.Element {
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
