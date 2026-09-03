/**
 * DataTable — tabla sin scroll horizontal (FR-016).
 * Búsqueda general, filtro de estado, paginación >10, acciones a la derecha.
 * En móvil se adapta a tarjetas (no comprime la tabla).
 */
import {
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  useReactTable,
  type ColumnDef,
} from "@tanstack/react-table";
import { type ReactNode } from "react";

import { EmptyState } from "./EmptyState";
import { LoadingState } from "./LoadingState";
import { Pagination } from "./Pagination";

export interface DataTableProps<TData> {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- varianza de tipos de TanStack Table
  columns: ColumnDef<TData, any>[];
  data: TData[];
  loading?: boolean;
  error?: string | null;
  emptyTitle?: string;
  emptyDescription?: string;
  emptyAction?: ReactNode;
  /** Clave para construir la clave de identidad de fila. */
  getRowId?: (row: TData) => string;
  footer?: ReactNode;
}

export function DataTable<TData>({
  columns,
  data,
  loading,
  error,
  emptyTitle = "No hay registros",
  emptyDescription,
  emptyAction,
  getRowId,
  footer,
}: DataTableProps<TData>): React.JSX.Element {
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getRowId,
  });

  const { pageSize, pageIndex } = table.getState().pagination;
  const total = data.length;

  if (loading) {
    return <LoadingState rows={5} />;
  }

  if (error) {
    return (
      <div className="rounded-md border border-danger-100 bg-danger-100/40 p-4 text-sm text-danger-600" role="alert">
        {error}
      </div>
    );
  }

  if (total === 0) {
    return <EmptyState title={emptyTitle} description={emptyDescription} action={emptyAction} />;
  }

  return (
    <div>
      {/* Región desplazable accesible por teclado (WCAG 2.1.1, axe
          `scrollable-region-focusable`): una tabla ancha sin controles dentro
          no podría desplazarse sin ratón. */}
      <div className="overflow-x-auto" tabIndex={0} role="region" aria-label={`Resultados: ${total} registros`}>
        <table className="w-full border-collapse text-sm">
          <caption className="sr-only">Resultados: {total} registros</caption>
          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id} className="border-b border-border-default bg-surface-100">
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    scope="col"
                    // text-600 (6,92:1) y no text-500 (4,34:1 sobre surface-100):
                    // la cabecera incumplía WCAG 2.2 AA en toda tabla con datos.
                    className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-text-600"
                  >
                    {header.isPlaceholder
                      ? null
                      : flexRender(header.column.columnDef.header, header.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id} className="border-b border-border-default hover:bg-surface-50">
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-3 py-2 align-middle text-text-700">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
          {footer ? <tfoot>{footer}</tfoot> : null}
        </table>
      </div>
      {total > 10 ? (
        <Pagination
          pageIndex={pageIndex}
          pageSize={pageSize}
          total={total}
          onPageChange={(index) => table.setPageIndex(index)}
          onPageSizeChange={(size) => table.setPageSize(size)}
        />
      ) : null}
      <p className="mt-1 text-xs text-text-500">
        Mostrando {pageIndex * pageSize + 1}–{Math.min((pageIndex + 1) * pageSize, total)} de {total}{" "}
        registros
      </p>
    </div>
  );
}
