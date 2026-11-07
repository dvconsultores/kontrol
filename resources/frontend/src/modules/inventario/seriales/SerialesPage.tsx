/** Seriales — trazabilidad por número de serie/IMEI/MAC (FR-003-040/041, WF-06). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { CatalogItemSummary, PagedResult, ProductSerial } from "@/api/types";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Autorizado } from "@/components/Autorizado";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { AvisoDeAlmacenes } from "@/modules/organizacion/almacenes/AvisoDeAlmacenes";
import { useAlmacenesDeEmpresa } from "@/modules/organizacion/almacenes/useAlmacenesDeEmpresa";


const columnHelper = createColumnHelper<ProductSerial>();

export function SerialesPage(): React.JSX.Element {
  const { activeCompany } = useCompany();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const [newProduct, setNewProduct] = useState("");
  const [newSerial, setNewSerial] = useState("");
  const [newImei1, setNewImei1] = useState("");
  const [newImei2, setNewImei2] = useState("");
  const [newMac, setNewMac] = useState("");
  const [newWarehouse, setNewWarehouse] = useState("");
  const [search, setSearch] = useState("");

  const companyId = activeCompany?.id ?? null;

  const serialsUrl = search ? `/inventory/serials?q=${encodeURIComponent(search)}` : "/inventory/serials";

  const query = useQuery({
    queryKey: ["inventario", "seriales", search],
    queryFn: () => apiFetch<{ items: ProductSerial[] }>(serialsUrl),
    retry: false,
  });
  const products = useQuery({
    queryKey: ["maestros", "productos"],
    queryFn: () => apiFetch<PagedResult<CatalogItemSummary>>(`/maestros/catalogos/items?status=ACTIVE`),
    retry: false,
  });
  const warehouses = useAlmacenesDeEmpresa(companyId);

  const refresh = async (): Promise<void> => {
    await queryClient.invalidateQueries({ queryKey: ["inventario", "seriales"] });
  };

  const createSerial = async (): Promise<void> => {
    try {
      await apiFetch("/inventory/serials", {
        method: "POST",
        body: {
          product_id: newProduct, serial: newSerial,
          imei1: newImei1 || null, imei2: newImei2 || null, mac: newMac || null,
          lot_id: null, warehouse_id: newWarehouse || null,
        },
      });
      notify({ type: "success", title: "Serial creado", description: newSerial });
      setNewProduct(""); setNewSerial(""); setNewImei1(""); setNewImei2(""); setNewMac(""); setNewWarehouse("");
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear el serial";
      notify({ type: "error", title: "No fue posible crear el serial", description: message });
    }
  };

  const columns = [
    columnHelper.accessor("serial", { header: "Serial" }),
    columnHelper.accessor("product_id", { header: "Producto" }),
    columnHelper.accessor("imei1", { header: "IMEI 1" }),
    columnHelper.accessor("imei2", { header: "IMEI 2" }),
    columnHelper.accessor("mac", { header: "MAC" }),
    columnHelper.accessor("warehouse_id", { header: "Almacén" }),
    columnHelper.accessor("status", { header: "Estado" }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Seriales"
        description="Trazabilidad por número de serie, IMEI y MAC para productos con seguimiento individual."
        crumbs={[{ label: "Inventario" }, { label: "Seriales" }]}
      />
      <Autorizado operacion={["POST", "/inventory/serials"]}>
      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Registrar serial</h2>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Producto" required>
            <select value={newProduct} onChange={(e) => setNewProduct(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(products.data?.items ?? []).map((p) => (
                <option key={p.id} value={p.id}>{p.code} · {p.name}</option>
              ))}
            </select>
          </FormField>
          <FormField label="Número de serie" required>
            <TextInput value={newSerial} onChange={(e) => setNewSerial(e.target.value)} placeholder="SN-0001" required />
          </FormField>
          <FormField label="IMEI 1">
            <TextInput value={newImei1} onChange={(e) => setNewImei1(e.target.value)} placeholder="Opcional" />
          </FormField>
          <FormField label="IMEI 2">
            <TextInput value={newImei2} onChange={(e) => setNewImei2(e.target.value)} placeholder="Opcional" />
          </FormField>
          <FormField label="MAC">
            <TextInput value={newMac} onChange={(e) => setNewMac(e.target.value)} placeholder="Opcional" />
          </FormField>
          <AvisoDeAlmacenes consulta={warehouses} />
          <FormField label="Almacén">
            <select value={newWarehouse} onChange={(e) => setNewWarehouse(e.target.value)} className="h-10 w-48 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(warehouses.data?.items ?? []).map((w) => (
                <option key={w.id} value={w.id}>{w.code} · {w.name}</option>
              ))}
            </select>
          </FormField>
          <AsyncButton type="submit" variant="primary" onClick={createSerial}>Registrar</AsyncButton>
        </form>
      </section>
      </Autorizado>

      <div className="mb-4 flex items-center gap-2">
        <TextInput
          value={search}
          onChange={(e) => { setSearch(e.target.value); }}
          placeholder="Buscar por serial o IMEI…"
          className="w-72"
        />
        <AsyncButton variant="secondary" onClick={refresh}>Buscar</AsyncButton>
      </div>

      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar los seriales." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin seriales"
        emptyDescription="Aún no hay seriales registrados."
      />
    </PageContent>
  );
}
