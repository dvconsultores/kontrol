/**
 * AsyncCombobox — búsqueda asíncrona para catálogos grandes (FR-002-043).
 * Debounce 300-500 ms, ejecución backend, paginación, cancelación de
 * consultas obsoletas y estados loading/empty/error (DOC-08 §9.2).
 */
import { useQuery } from "@tanstack/react-query";
import { useEffect, useId, useRef, useState } from "react";
import { Check, ChevronDown, Loader2, Search } from "lucide-react";

import { apiFetch } from "@/api/client";
import type { CatalogItemSearchResult, PagedResult } from "@/api/types";

export interface AsyncComboboxProps {
  value: string | null;
  onChange: (value: string | null, item?: CatalogItemSearchResult) => void;
  /** URL del endpoint de búsqueda (sin query). */
  searchUrl: string;
  placeholder?: string;
  label?: string;
  itemType?: "PRODUCT" | "SERVICE";
  invalid?: boolean;
  error?: string;
}

const DEBOUNCE_MS = 300;

export function AsyncCombobox({
  value,
  onChange,
  searchUrl,
  placeholder = "Buscar…",
  label = "Buscar",
  itemType,
  invalid,
  error,
}: AsyncComboboxProps): React.JSX.Element {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [debounced, setDebounced] = useState("");
  const listboxId = useId();
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(query), DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [query]);

  // Cerrar al hacer clic fuera
  useEffect(() => {
    const onDocClick = (e: MouseEvent): void => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  const search = useQuery({
    queryKey: ["async-search", searchUrl, debounced, itemType],
    queryFn: async () => {
      const params = new URLSearchParams({ q: debounced, page_size: "20" });
      if (itemType) {
        params.set("item_type", itemType);
      }
      return apiFetch<PagedResult<CatalogItemSearchResult>>(
        `${searchUrl}?${params.toString()}`,
      );
    },
    enabled: debounced.length > 0 || open,
    retry: false,
  });

  return (
    <div ref={rootRef} className="relative">
      <label htmlFor={`${listboxId}-input`} className="sr-only">
        {label}
      </label>
      <div className="relative">
        <Search
          className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-text-400"
          aria-hidden="true"
        />
        <input
          id={`${listboxId}-input`}
          role="combobox"
          aria-expanded={open}
          aria-controls={listboxId}
          aria-invalid={invalid || undefined}
          aria-describedby={error ? `${listboxId}-error` : undefined}
          value={value ?? query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
            if (value) {
              onChange(null); // nuevo término de búsqueda
            }
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={(e) => {
            if (e.key === "Escape") {
              setOpen(false);
            }
          }}
          placeholder={placeholder}
          className={`h-10 w-full rounded-md border bg-surface-0 pl-9 pr-10 text-sm ${
            invalid ? "border-danger-600" : "border-border-default"
          } focus:border-brand-600 focus:outline-brand-600`}
        />
        <ChevronDown
          className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-text-400"
          aria-hidden="true"
        />
      </div>

      {open ? (
        <ul
          id={listboxId}
          role="listbox"
          className="absolute z-40 mt-1 max-h-64 w-full overflow-auto rounded-md border border-border-default bg-surface-0 shadow-lg"
        >
          {search.isLoading ? (
            <li className="flex items-center gap-2 px-3 py-2 text-sm text-text-500" role="status">
              <Loader2 className="size-4 animate-spin" aria-hidden="true" />
              Buscando…
            </li>
          ) : search.isError ? (
            <li className="px-3 py-2 text-sm text-danger-600" role="alert">
              No fue posible completar la búsqueda
            </li>
          ) : (search.data?.items.length ?? 0) === 0 ? (
            <li className="px-3 py-2 text-sm text-text-500">Sin resultados</li>
          ) : (
            search.data?.items.map((item) => (
              <li key={item.id} role="option" aria-selected={value === item.id}>
                <button
                  type="button"
                  onClick={() => {
                    onChange(item.id, item);
                    setOpen(false);
                  }}
                  className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-brand-50"
                >
                  <span>
                    <span className="font-medium text-text-900">{item.name}</span>
                    <span className="ml-2 text-xs text-text-400">{item.code}</span>
                  </span>
                  {value === item.id ? (
                    <Check className="size-4 text-brand-600" aria-hidden="true" />
                  ) : null}
                </button>
              </li>
            ))
          )}
        </ul>
      ) : null}

      {error ? (
        <p id={`${listboxId}-error`} className="mt-1 text-sm text-danger-600" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
