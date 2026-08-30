/** Almacenes — listado, búsqueda y alta (Spec 008, FR-008-070/071).
 *
 * El alta declara qué tramos usará el almacén. Un almacén simple no declara
 * ninguno y nunca verá pestañas de estructura vacías (R-008-1).
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Eye, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router";

import { apiFetch } from "@/api/client";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";

import { LEVEL_LABEL, STRUCTURE_LEVELS, type Paged, type StructureLevel, type Warehouse } from "./types";

const WAREHOUSE_TYPES = [
  { value: "PHYSICAL", label: "Físico" },
  { value: "VIRTUAL", label: "Virtual" },
];

interface BranchOption { id: string; code: string; name: string }

export function AlmacenesPage(): React.JSX.Element {
  const { activeCompany } = useCompany();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const companyId = activeCompany?.id ?? null;

  const [query, setQuery] = useState("");
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [warehouseType, setWarehouseType] = useState("PHYSICAL");
  const [branchId, setBranchId] = useState("");
  const [levels, setLevels] = useState<Record<StructureLevel, boolean>>({
    zone: false, aisle: false, rack: false, level: false,
  });
  const [submitted, setSubmitted] = useState(false);

  const warehouses = useQuery({
    queryKey: ["organization", "warehouses", companyId, query],
    queryFn: () => apiFetch<Paged<Warehouse>>(
      `/organization/warehouses?company_id=${encodeURIComponent(companyId ?? "")}` +
      (query ? `&q=${encodeURIComponent(query)}` : "")),
    enabled: Boolean(companyId),
    retry: false,
  });
  const branches = useQuery({
    queryKey: ["organization", "branches", companyId],
    queryFn: () => apiFetch<BranchOption[]>(
      `/organization/branches?company_id=${encodeURIComponent(companyId ?? "")}`),
    enabled: Boolean(companyId),
    retry: false,
  });

  const invalid = submitted && (!code.trim() || !name.trim());

  const createWarehouse = async (): Promise<void> => {
    setSubmitted(true);
    if (!companyId || !code.trim() || !name.trim()) {
      document.querySelector<HTMLInputElement>("[data-invalid='true'] input")?.focus();
      return;
    }
    try {
      await apiFetch("/organization/warehouses", {
        method: "POST",
        body: {
          company_id: companyId, branch_id: branchId || null, code, name,
          warehouse_type: warehouseType, structure_levels: levels,
        },
      });
      notify({ type: "success", title: "Almacén creado", description: `${code} · ${name}` });
      setCode(""); setName(""); setBranchId(""); setSubmitted(false);
      setLevels({ zone: false, aisle: false, rack: false, level: false });
      void queryClient.invalidateQueries({ queryKey: ["organization", "warehouses"] });
    } catch (err) {
      notify({
        type: "error", title: "No fue posible crear el almacén",
        description: err instanceof Error ? err.message : "Error inesperado",
      });
    }
  };

  const columns = useMemo<ColumnDef<Warehouse, unknown>[]>(() => [
    { accessorKey: "code", header: "Código" },
    { accessorKey: "name", header: "Nombre" },
    {
      id: "structure", header: "Estructura",
      cell: ({ row }) => {
        const declared = row.original.declared_levels;
        return (
          <span className="text-text-600">
            {declared.length === 0
              ? "Simple · sin tramos"
              : declared.map((level) => LEVEL_LABEL[level].singular).join(" → ")}
          </span>
        );
      },
    },
    { accessorKey: "status", header: "Estado" },
    {
      id: "actions", header: "Acciones",
      cell: ({ row }) => (
        <div className="flex justify-end">
          <Link
            to={`/organizacion/almacenes/${row.original.id}`}
            aria-label={`Ver el almacén ${row.original.code}`}
            title="Ver detalle"
            className="inline-flex h-8 w-8 cursor-pointer items-center justify-center rounded-md text-text-600 hover:bg-surface-100"
          >
            <Eye className="h-4 w-4" aria-hidden="true" />
          </Link>
        </div>
      ),
    },
  ], []);

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Almacenes"
        description="Almacenes de la empresa activa y su estructura física."
        crumbs={[{ label: "Organización" }, { label: "Almacenes" }]}
      />

      {!companyId ? (
        <div className="rounded-md border border-warning-100 bg-warning-100/40 p-4 text-sm text-warning-600" role="alert">
          No hay una empresa activa. Vaya a <strong>Organización → Empresas</strong> y active la empresa para registrar almacenes.
        </div>
      ) : (
        <>
          <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
            <h2 className="mb-2 text-base font-semibold text-text-900">Registrar almacén</h2>
            <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
              <div data-invalid={submitted && !code.trim()}>
                <FormField label="Código" required error={submitted && !code.trim() ? "Campo obligatorio" : undefined}>
                  <TextInput value={code} onChange={(e) => setCode(e.target.value)} placeholder="Ej. ALM-01" required />
                </FormField>
              </div>
              <div data-invalid={submitted && !name.trim()}>
                <FormField label="Nombre" required error={submitted && !name.trim() ? "Campo obligatorio" : undefined}>
                  <TextInput value={name} onChange={(e) => setName(e.target.value)} placeholder="Nombre del almacén" required />
                </FormField>
              </div>
              <FormField label="Tipo">
                <select
                  value={warehouseType} onChange={(e) => setWarehouseType(e.target.value)}
                  aria-label="Tipo de almacén"
                  className="h-10 w-40 cursor-pointer rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                >
                  {WAREHOUSE_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </FormField>
              <FormField label="Sucursal">
                <select
                  value={branchId} onChange={(e) => setBranchId(e.target.value)}
                  aria-label="Sucursal del almacén"
                  className="h-10 w-56 cursor-pointer rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                >
                  <option value="">Sin sucursal (central)</option>
                  {(branches.data ?? []).map((b) => (
                    <option key={b.id} value={b.id}>{b.code} · {b.name}</option>
                  ))}
                </select>
              </FormField>
              <AsyncButton type="submit" variant="primary" onClick={createWarehouse} disabled={invalid}>
                Registrar
              </AsyncButton>
            </form>

            <fieldset className="mt-4 border-t border-border-default pt-3">
              <legend className="text-sm font-medium text-text-700">Tramos de la estructura</legend>
              <p className="mb-2 text-sm text-text-500">
                Marque solo los tramos que este almacén va a usar. Un almacén de una sola sala no necesita ninguno.
                Una vez creados nodos, los tramos usados ya no podrán retirarse.
              </p>
              <div className="flex flex-wrap gap-4">
                {STRUCTURE_LEVELS.map((level) => (
                  <label key={level} className="flex cursor-pointer items-center gap-2 text-sm text-text-700">
                    <input
                      type="checkbox" checked={levels[level]}
                      onChange={(e) => setLevels((prev) => ({ ...prev, [level]: e.target.checked }))}
                      className="h-4 w-4 cursor-pointer"
                    />
                    {LEVEL_LABEL[level].singular}
                  </label>
                ))}
              </div>
            </fieldset>
          </section>

          <section className="rounded-lg border border-border-default bg-surface-0 p-4">
            <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
              <h2 className="text-base font-semibold text-text-900">
                Almacenes de {activeCompany?.legal_name}
              </h2>
              <FormField label="Buscar">
                <div className="relative">
                  <Search className="pointer-events-none absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-text-500" aria-hidden="true" />
                  <TextInput
                    value={query} onChange={(e) => setQuery(e.target.value)}
                    aria-label="Buscar almacén por código o nombre"
                    placeholder="Código o nombre" className="pl-8"
                  />
                </div>
              </FormField>
            </div>
            <DataTable
              columns={columns}
              data={warehouses.data?.items ?? []}
              loading={warehouses.isLoading}
              error={warehouses.isError ? "No fue posible cargar los almacenes." : null}
              emptyTitle="Sin almacenes registrados"
              emptyDescription="Registre el primer almacén con el formulario superior."
              getRowId={(row) => row.id}
            />
          </section>
        </>
      )}
    </PageContent>
  );
}
