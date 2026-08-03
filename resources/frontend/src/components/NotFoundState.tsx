/** NotFoundState — 404 con enlace a la lista (DOC-08 §11). */
import { FileQuestion } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "./Button";

export interface NotFoundStateProps {
  title?: string;
  backTo?: string;
  backLabel?: string;
}

export function NotFoundState({
  title = "Página no encontrada",
  backTo = "/",
  backLabel = "Volver al inicio",
}: NotFoundStateProps): React.JSX.Element {
  return (
    <div className="flex flex-col items-center justify-center gap-3 px-6 py-16 text-center">
      <FileQuestion className="size-12 text-text-400" aria-hidden="true" />
      <h1 className="text-xl font-semibold text-text-900">{title}</h1>
      <p className="max-w-md text-sm text-text-500">
        El recurso que busca no existe o fue movido. Verifique la dirección.
      </p>
      <Link to={backTo} className="mt-2">
        <Button variant="secondary">{backLabel}</Button>
      </Link>
    </div>
  );
}
