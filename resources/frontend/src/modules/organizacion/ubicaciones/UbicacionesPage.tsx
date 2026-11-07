/** Ubicaciones — búsqueda global y orden físico (Spec 008, FR-008-074).
 *
 * Dos vistas de lo mismo: buscar una ubicación concreta, y ver el recorrido
 * físico en el orden determinista que consumirá la Spec 031.
 */
import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Search } from "lucide-react";
import { useMemo, useState } from "react";

import { apiFetch } from "@/api/client";
import { useCompany } from "@/app/contexts/CompanyContext";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";
import { AvisoDeAlmacenes } from "@/modules/organizacion/almacenes/AvisoDeAlmacenes";
import { useAlmacenesDeEmpresa } from "@/modules/organizacion/almacenes/useAlmacenesDeEmpresa";

import type { Paged, WarehouseLocation } from "../almacenes/types";

interface OrderedLocation {
  id: string;
  code: string;
  status: string;
  display_path: string;
  physical_order: (number | null)[];
}

export function UbicacionesPage(): React.JSX.Element {
  const { activeCompany } = useCompany();
  const companyId = activeCompany?.id ?? null;
  const [warehouseId, setWarehouseId] = useState("");
  const [query, setQuery] = useState("");
  const [view, setView] = useState<"search" | "ordered">("search");

  const warehouses = useAlmacenesDeEmpresa(companyId);

  const locations = useQuery({
    queryKey: ["organization", "locations", warehouseId, query],
    queryFn: () => apiFetch<Paged<WarehouseLocation>>(
      "/organization/locations?limit=100" +
      (warehouseId ? `&warehouse_id=${encodeURIComponent(warehouseId)}` : "") +
      (query ? `&q=${encodeURIComponent(query)}` : "")),
    enabled: Boolean(companyId) && view === "search", retry: false,
  });

  const ordered = useQuery({
    queryKey: ["organization", "ordered", warehouseId],
    queryFn: () => apiFetch<Paged<OrderedLocation>>(
      `/organization/locations/ordered?warehouse_id=${encodeURIComponent(warehouseId)}&limit=200`),
    enabled: Boolean(warehouseId) && view === "ordered", retry: false,
  });

  const searchColumns = useMemo<ColumnDef<WarehouseLocation, unknown>[]>(() => [
    { accessorKey: "code", header: "Código" },
    { id: "path", header: "Ubicación física", cell: ({ row }) => row.original.display_path },
    { accessorKey: "status", header: "Estado" },
  ], []);

  const orderedColumns = useMemo<ColumnDef<OrderedLocation, unknown>[]>(() => [
    { id: "n", header: "#", cell: ({ row }) => row.index + 1 },
    { accessorKey: "code", header: "Código" },
    { id: "path", header: "Recorrido", cell: ({ row }) => row.original.display_path },
    { accessorKey: "status", header: "Estado" },
  ], []);

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Ubicaciones"
        description="Búsqueda de ubicaciones y recorrido físico del almacén."
        crumbs={[{ label: "Organización" }, { label: "Ubicaciones" }]}
      />

      {!companyId ? (
        <div className="rounded-md border border-warning-100 bg-warning-100/40 p-4 text-sm text-warning-600" role="alert">
          No hay una empresa activa. Vaya a <strong>Organización → Empresas</strong> y active la empresa.
        </div>
      ) : (
        <section className="rounded-lg border border-border-default bg-surface-0 p-4">
          <div className="mb-3 flex flex-wrap items-end gap-3">
            <AvisoDeAlmacenes consulta={warehouses} />
            <FormField label="Almacén">
              <select
                value={warehouseId} onChange={(e) => setWarehouseId(e.target.value)}
                aria-label="Filtrar por almacén"
                className="h-10 w-64 cursor-pointer rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
              >
                <option value="">Todos los almacenes</option>
                {(warehouses.data?.items ?? []).map((w) => (
                  <option key={w.id} value={w.id}>{w.code} · {w.name}</option>
                ))}
              </select>
            </FormField>
            {view === "search" ? (
              <FormField label="Buscar">
                <div className="relative">
                  <Search className="pointer-events-none absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-text-500" aria-hidden="true" />
                  <TextInput
                    value={query} onChange={(e) => setQuery(e.target.value)}
                    aria-label="Buscar ubicación por código o nombre"
                    placeholder="Código o nombre" className="pl-8"
                  />
                </div>
              </FormField>
            ) : null}
            <FormField label="Vista">
              <select
                value={view} onChange={(e) => setView(e.target.value as "search" | "ordered")}
                aria-label="Vista de ubicaciones"
                className="h-10 w-48 cursor-pointer rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
              >
                <option value="search">Búsqueda</option>
                <option value="ordered">Orden físico</option>
              </select>
            </FormField>
          </div>

          {view === "ordered" && !warehouseId ? (
            <p className="text-sm text-text-500">
              Seleccione un almacén para ver su recorrido físico.
            </p>
          ) : view === "ordered" ? (
            <DataTable
              columns={orderedColumns} data={ordered.data?.items ?? []}
              loading={ordered.isLoading}
              error={ordered.isError ? "No fue posible cargar el recorrido." : null}
              emptyTitle="Sin ubicaciones en este almacén"
              getRowId={(row) => row.id}
            />
          ) : (
            <DataTable
              columns={searchColumns} data={locations.data?.items ?? []}
              loading={locations.isLoading}
              error={locations.isError ? "No fue posible cargar las ubicaciones." : null}
              emptyTitle="Sin ubicaciones"
              emptyDescription="Cree ubicaciones desde el detalle del almacén."
              getRowId={(row) => row.id}
            />
          )}
        </section>
      )}
    </PageContent>
  );
}
