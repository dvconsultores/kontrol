/** Piezas compartidas de las pantallas de la Spec 047. */
import { clsx } from "clsx";
import { Link } from "react-router";

import { useAuth } from "@/app/contexts/AuthContext";
import { t, tValor } from "@/i18n";

import { destinoDeEnlace, type Enlace, type Severidad } from "./api";

/** El origen solo se enlaza si el usuario puede verlo; si no, no se revela nada. */
export function EnlaceOrigen({ enlace }: { enlace: Enlace }): React.JSX.Element {
  const { hasPermission } = useAuth();
  const destino = destinoDeEnlace(enlace);
  if (!destino || !hasPermission(destino.permiso)) {
    return <span className="text-sm text-text-500">{t("comun.sin_acceso_origen")}</span>;
  }
  return (
    <Link to={destino.ruta} className="text-sm font-medium text-text-900 underline underline-offset-2">
      {t("comun.abrir_origen")}
    </Link>
  );
}

const COLOR: Record<Severidad, string> = {
  INFO: "bg-surface-100 text-text-700",
  WARNING: "bg-warning-100 text-warning-700",
  CRITICAL: "bg-danger-100 text-danger-700",
};

export function EtiquetaSeveridad({ valor }: { valor: Severidad }): React.JSX.Element {
  return (
    <span className={clsx("inline-flex rounded-md px-2 py-0.5 text-xs font-medium", COLOR[valor])}>
      {tValor("severidad", valor) ?? valor}
    </span>
  );
}

export const SELECTOR =
  "h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900";
