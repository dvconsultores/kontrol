/** StatusFilter — filtro Todos/Activos/Inactivos (FR-018). */
export type StatusFilterValue = "ALL" | "ACTIVE" | "INACTIVE";

export interface StatusFilterProps {
  value: StatusFilterValue;
  onChange: (value: StatusFilterValue) => void;
}

const OPTIONS: Array<{ value: StatusFilterValue; label: string }> = [
  { value: "ALL", label: "Todos" },
  { value: "ACTIVE", label: "Activos" },
  { value: "INACTIVE", label: "Inactivos" },
];

export function StatusFilter({ value, onChange }: StatusFilterProps): React.JSX.Element {
  return (
    <div role="group" aria-label="Filtrar por estado" className="inline-flex rounded-md border border-border-default">
      {OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          aria-pressed={value === option.value}
          className={`h-9 px-3 text-sm transition-colors ${
            value === option.value
              ? "bg-brand-600 text-white"
              : "bg-surface-0 text-text-500 hover:bg-surface-100"
          } ${option.value !== "ALL" ? "border-l border-border-default" : ""}`}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
