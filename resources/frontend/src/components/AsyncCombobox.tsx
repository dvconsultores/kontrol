/**
 * AsyncCombobox — búsqueda asíncrona para catálogos grandes (FR-002-043).
 * Debounce 300-500 ms, ejecución backend, paginación, cancelación de
 * consultas obsoletas y estados loading/empty/error (DOC-08 §9.2).
 */
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
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
  /** id del input; si viene, no se pinta la etiqueta sr-only. */
  id?: string;
  /** Se combina con el id del error. */
  "aria-describedby"?: string;
  /** Con value, GET `${resolveUrl}/${value}` devuelve { code, name }. */
  resolveUrl?: string;
  /** Forma parte de todas las claves de consulta. */
  scopeKey?: string;
  /** Parámetros adicionales de la búsqueda; forman parte de la clave. */
  extraParams?: Readonly<Record<string, string>>;
}

interface ResolvedItem {
  code: string;
  name: string;
}

interface SearchPage {
  items: CatalogItemSearchResult[];
  page: number;
  page_size: number;
  total: number;
}

const DEBOUNCE_MS = 300;

function formatItemLabel(code: string, name: string): string {
  return `${code} · ${name}`;
}

export function AsyncCombobox({
  value,
  onChange,
  searchUrl,
  placeholder = "Buscar…",
  label = "Buscar",
  itemType,
  invalid,
  error,
  id,
  "aria-describedby": describedBy,
  resolveUrl,
  scopeKey,
  extraParams,
}: AsyncComboboxProps): React.JSX.Element {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [debounced, setDebounced] = useState("");
  const [known, setKnown] = useState<{ id: string; label: string } | null>(null);
  const listboxId = useId();
  const inputId = id ?? `${listboxId}-input`;
  const rootRef = useRef<HTMLDivElement>(null);

  const valueRef = useRef(value);
  const onChangeRef = useRef(onChange);
  const scopeKeyRef = useRef(scopeKey);

  useEffect(() => {
    valueRef.current = value;
  }, [value]);

  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  useEffect(() => {
    if (scopeKeyRef.current !== scopeKey && valueRef.current) {
      onChangeRef.current(null);
    }
    scopeKeyRef.current = scopeKey;
  }, [scopeKey]);

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

  const search = useInfiniteQuery<SearchPage>({
    queryKey: [
      "async-search",
      searchUrl,
      scopeKey ?? null,
      debounced,
      itemType ?? null,
      extraParams ?? null,
    ],
    queryFn: async ({ pageParam }) => {
      const params = new URLSearchParams({
        q: debounced,
        page_size: "20",
        page: String(pageParam),
      });
      if (itemType) {
        params.set("item_type", itemType);
      }
      for (const [nombre, valor] of Object.entries(extraParams ?? {})) {
        params.set(nombre, valor);
      }
      return apiFetch<PagedResult<CatalogItemSearchResult>>(
        `${searchUrl}?${params.toString()}`,
      );
    },
    initialPageParam: 1,
    getNextPageParam: (lastPage, allPages) => {
      const loaded = allPages.reduce((count, page) => count + page.items.length, 0);
      return loaded < lastPage.total ? allPages.length + 1 : undefined;
    },
    enabled: debounced.length > 0 || open,
    retry: false,
  });

  const resolveItem = useQuery<ResolvedItem>({
    queryKey: ["async-resolve", resolveUrl, scopeKey ?? null, value],
    queryFn: async () => {
      return apiFetch<ResolvedItem>(`${resolveUrl}/${value}`);
    },
    enabled: Boolean(resolveUrl && value && known?.id !== value),
    retry: false,
  });

  useEffect(() => {
    if (resolveItem.data && value) {
      setKnown({ id: value, label: formatItemLabel(resolveItem.data.code, resolveItem.data.name) });
    }
  }, [resolveItem.data, value]);

  const displayValue = query !== "" ? query : value && known?.id === value ? known.label : "";

  const inputDescribedBy = [describedBy, error ? `${inputId}-error` : undefined]
    .filter(Boolean)
    .join(" ") || undefined;

  const allItems = search.data?.pages.flatMap((page) => page.items) ?? [];
  const total = search.data?.pages.at(-1)?.total ?? 0;
  const isFirstPageLoading = search.isLoading;
  const isFirstPageError = search.isError && !search.isFetchNextPageError;
  const hasNextPage = search.hasNextPage;
  const isFetchingNextPage = search.isFetchingNextPage;
  const nextPageError = search.isFetchNextPageError;

  return (
    <div ref={rootRef} className="relative">
      {id ? null : (
        <label htmlFor={inputId} className="sr-only">
          {label}
        </label>
      )}
      <div className="relative">
        <Search
          className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-text-400"
          aria-hidden="true"
        />
        <input
          id={inputId}
          role="combobox"
          aria-expanded={open}
          aria-controls={listboxId}
          aria-invalid={invalid || undefined}
          aria-describedby={inputDescribedBy}
          value={displayValue}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
            if (value) {
              onChange(null);
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
          {isFirstPageLoading ? (
            <li className="flex items-center gap-2 px-3 py-2 text-sm text-text-500" role="status">
              <Loader2 className="size-4 animate-spin" aria-hidden="true" />
              Buscando…
            </li>
          ) : isFirstPageError ? (
            <li className="px-3 py-2 text-sm text-danger-600" role="alert">
              No fue posible completar la búsqueda
            </li>
          ) : allItems.length === 0 ? (
            <li className="px-3 py-2 text-sm text-text-500">Sin resultados</li>
          ) : (
            <>
              {allItems.map((item) => (
                <li key={item.id} role="presentation">
                  <button
                    type="button"
                    role="option"
                    aria-selected={value === item.id}
                    onClick={() => {
                      setKnown({ id: item.id, label: formatItemLabel(item.code, item.name) });
                      setQuery("");
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
              ))}
              {hasNextPage ? (
                <li className="px-3 py-2 text-sm text-text-500">
                  Mostrando {allItems.length} de {total}
                </li>
              ) : null}
              {hasNextPage ? (
                <li>
                  <button
                    type="button"
                    onClick={() => search.fetchNextPage()}
                    disabled={isFetchingNextPage}
                    className="w-full px-3 py-2 text-left text-sm text-brand-600 hover:bg-brand-50 disabled:text-text-400"
                  >
                    Cargar más resultados
                  </button>
                </li>
              ) : null}
              {nextPageError ? (
                <li className="px-3 py-2 text-sm text-danger-600" role="alert">
                  No fue posible cargar más resultados
                </li>
              ) : null}
            </>
          )}
        </ul>
      ) : null}

      {error ? (
        <p id={`${inputId}-error`} className="mt-1 text-sm text-danger-600" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
