/** ForbiddenState — acceso prohibido; no revela información de la entidad (DOC-08 §11). */
import { ShieldX } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "./Button";

export function ForbiddenState(): React.JSX.Element {
  return (
    <div className="flex flex-col items-center justify-center gap-3 px-6 py-16 text-center">
      <ShieldX className="size-12 text-warning-600" aria-hidden="true" />
      <h1 className="text-xl font-semibold text-text-900">Acceso prohibido</h1>
      <p className="max-w-md text-sm text-text-500">
        No tiene permiso para acceder a este recurso. Si considera que es un error, contacte a su
        administrador.
      </p>
      <Link to="/" className="mt-2">
        <Button variant="secondary">Volver al inicio</Button>
      </Link>
    </div>
  );
}
