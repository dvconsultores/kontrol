/** PageHeader — título, descripción, estado y acciones (DOC-08 §5). */
import type { ReactNode } from "react";

import { Breadcrumbs, type Crumb } from "./Breadcrumbs";

export interface PageHeaderProps {
  crumbs?: Crumb[];
  title: string;
  description?: string;
  status?: ReactNode;
  actions?: ReactNode;
}

export function PageHeader({ crumbs, title, description, status, actions }: PageHeaderProps): React.JSX.Element {
  return (
    <header className="mb-6">
      {crumbs && crumbs.length > 0 ? <Breadcrumbs crumbs={crumbs} /> : null}
      <div className="mt-2 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-text-900">{title}</h1>
            {status}
          </div>
          {description ? <p className="mt-1 max-w-2xl text-sm text-text-500">{description}</p> : null}
        </div>
        {actions ? (
          <div className="flex min-w-0 flex-wrap items-center gap-2">{actions}</div>
        ) : null}
      </div>
    </header>
  );
}
