/** EmptyState — estado vacío con mensaje y acción contextual (FR-017 §Estados). */
import { Inbox } from "lucide-react";
import type { ReactNode } from "react";

export interface EmptyStateProps {
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ title, description, action }: EmptyStateProps): React.JSX.Element {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border-default bg-surface-0 px-6 py-12 text-center">
      <Inbox className="size-10 text-text-400" aria-hidden="true" />
      <h3 className="text-base font-medium text-text-900">{title}</h3>
      {description ? <p className="max-w-md text-sm text-text-500">{description}</p> : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}
