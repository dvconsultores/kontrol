/** LoadingState — skeleton coherente con el contenido (FR-028). */

export interface LoadingStateProps {
  rows?: number;
  label?: string;
}

export function LoadingState({ rows = 5, label = "Cargando…" }: LoadingStateProps): React.JSX.Element {
  return (
    <div className="flex flex-col gap-3" role="status" aria-live="polite">
      <span className="sr-only">{label}</span>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="h-10 animate-pulse rounded-md bg-surface-200"
          style={{ opacity: 1 - i * 0.12 }}
        />
      ))}
    </div>
  );
}
