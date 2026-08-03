/** Pagination — solo si total > 10 (FR-019). */
import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "./Button";

export interface PaginationProps {
  pageIndex: number;
  pageSize: number;
  total: number;
  onPageChange: (index: number) => void;
  onPageSizeChange: (size: number) => void;
}

const PAGE_SIZES = [10, 25, 50, 100];

export function Pagination({
  pageIndex,
  pageSize,
  total,
  onPageChange,
  onPageSizeChange,
}: PaginationProps): React.JSX.Element {
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const hasPrev = pageIndex > 0;
  const hasNext = pageIndex < pageCount - 1;

  return (
    <nav aria-label="Paginación" className="mt-3 flex flex-wrap items-center justify-between gap-3">
      <div className="flex items-center gap-2 text-sm text-text-500">
        <label htmlFor="page-size" className="sr-only">
          Registros por página
        </label>
        <select
          id="page-size"
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
          className="h-9 rounded-md border border-border-default bg-surface-0 px-2 text-sm"
        >
          {PAGE_SIZES.map((size) => (
            <option key={size} value={size}>
              {size} por página
            </option>
          ))}
        </select>
      </div>
      <div className="flex items-center gap-1">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onPageChange(pageIndex - 1)}
          disabled={!hasPrev}
          aria-label="Página anterior"
        >
          <ChevronLeft className="size-4" aria-hidden="true" />
        </Button>
        <span className="px-2 text-sm text-text-500">
          Página {pageIndex + 1} de {pageCount}
        </span>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onPageChange(pageIndex + 1)}
          disabled={!hasNext}
          aria-label="Página siguiente"
        >
          <ChevronRight className="size-4" aria-hidden="true" />
        </Button>
      </div>
    </nav>
  );
}
