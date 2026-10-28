/** Existencias — saldos con filtros (FR-003-010/012, WF-01).
 *  La búsqueda es de servidor (FR-001-272): cada término produce su propia
 *  petición y la página vuelve a 1 (página base 0 → page=1) al buscar. */
import { useQuery } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { ApiError, apiFetch } from "@/api/client";
import type { InventoryBalance, PagedResult } from "@/api/types";
import { DataTable } from "@/components/DataTable";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { Pagination } from "@/components/Pagination";
import { SearchInput } from "@/components/SearchInput";

const columnHelper = createColumnHelper<InventoryBalance>();

function producto(fila: InventoryBalance): string {
  if (fila.product_code && fila.product_name) {
    return `${fila.product_code} — ${fila.product_name}`;
  }
  if (fila.product_code) {
    return fila.product_code;
  }
  return fila.product_id;
}

export function ExistenciasPage(): React.JSX.Element {
  const [search, setSearch] = useState("");
  const [pagina, setPagina] = useState(0);
  const [tamano, setTamano] = useState(10);

  const buscar = (valor: string): void => {
    setSearch(valor);
    setPagina(0);
  };

  const query = useQuery({
    queryKey: ["inventario", "existencias", search, pagina, tamano],
    queryFn: () => {
      const parametros = new URLSearchParams();
      if (search) parametros.set("q", search);
      parametros.set("page", String(pagina + 1));
      parametros.set("page_size", String(tamano));
      return apiFetch<PagedResult<InventoryBalance>>(`/inventory/balances?${parametros.toString()}`);
    },
    retry: false,
  });

  const columns = [
    columnHelper.accessor((fila) => producto(fila), { id: "producto", header: "Producto" }),
    columnHelper.accessor("warehouse_id", { header: "Almacén" }),
    columnHelper.accessor("lot_id", { header: "Lote" }),
    columnHelper.accessor("state", { header: "Estado" }),
    columnHelper.accessor("qty_on_hand", { header: "Físico" }),
    columnHelper.accessor("qty_reserved", { header: "Reservado" }),
    columnHelper.accessor("qty_available", { header: "Disponible" }),
  ];

  const mensajeError =
    query.error instanceof ApiError && query.error.status >= 400 && query.error.status <= 499
      ? query.error.message
      : "No fue posible cargar las existencias.";

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Existencias"
        description="Saldos por producto, almacén, lote y estado (disponible = físico − reservas)."
        crumbs={[{ label: "Inventario" }, { label: "Existencias" }]}
      />
      <div className="mb-4">
        <SearchInput
          value={search}
          onChange={buscar}
          placeholder="Buscar por producto…"
          label="Buscar por producto"
        />
      </div>
      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? mensajeError : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin existencias"
        emptyDescription={
          search ? "No hay saldos que coincidan con la búsqueda." : "No hay saldos registrados para los filtros actuales."
        }
        manualPagination
      />
      {query.data && query.data.total > 10 ? (
        <Pagination
          pageIndex={pagina}
          pageSize={tamano}
          total={query.data.total}
          onPageChange={setPagina}
          onPageSizeChange={(valor) => {
            setTamano(valor);
            setPagina(0);
          }}
        />
      ) : null}
    </PageContent>
  );
}
