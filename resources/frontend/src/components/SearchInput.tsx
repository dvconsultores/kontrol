/** SearchInput — búsqueda general por pantalla (FR-017). */
import { Search, X } from "lucide-react";
import { forwardRef } from "react";

export interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  label?: string;
}

export const SearchInput = forwardRef<HTMLInputElement, SearchInputProps>(function SearchInput(
  { value, onChange, placeholder = "Buscar en esta pantalla…", label = "Buscar" },
  ref,
) {
  return (
    <div className="relative w-full max-w-sm">
      <label htmlFor="general-search" className="sr-only">
        {label}
      </label>
      <Search
        className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-text-400"
        aria-hidden="true"
      />
      <input
        ref={ref}
        id="general-search"
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="h-10 w-full rounded-md border border-border-default bg-surface-0 pl-9 pr-9 text-sm focus:border-brand-600 focus:outline-brand-600"
      />
      {value ? (
        <button
          type="button"
          onClick={() => onChange("")}
          aria-label="Limpiar búsqueda"
          className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-text-400 hover:text-text-700"
        >
          <X className="size-4" aria-hidden="true" />
        </button>
      ) : null}
    </div>
  );
});
