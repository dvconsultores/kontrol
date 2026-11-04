import { ApiError } from "@/api/client";
import { Button } from "@/components/Button";
import type { DetalleConflictoSod } from "@/modules/gobierno/api";

const CLAVES_DETALLE_CONFLICTO_SOD = [
  "regla_codigo",
  "regla_nombre",
  "accion",
  "accion_etiqueta",
  "accion_previa",
  "accion_previa_etiqueta",
  "objeto_tipo",
  "objeto_id",
  "previa_en",
] as const satisfies readonly (keyof DetalleConflictoSod)[];

/** Devuelve el detalle del 409 GOV_SOD_CONFLICT si `e` lo es; si no, null. */
export function detalleDeConflictoSod(e: unknown): DetalleConflictoSod | null {
  if (!(e instanceof ApiError) || e.status !== 409 || e.code !== "GOV_SOD_CONFLICT") {
    return null;
  }
  const details: Record<string, unknown> = e.details ?? {};
  const detalle: DetalleConflictoSod = {
    regla_codigo: "",
    regla_nombre: "",
    accion: "",
    accion_etiqueta: "",
    accion_previa: "",
    accion_previa_etiqueta: "",
    objeto_tipo: "",
    objeto_id: "",
    previa_en: "",
  };
  for (const clave of CLAVES_DETALLE_CONFLICTO_SOD) {
    const valor = details[clave];
    if (typeof valor === "string") {
      detalle[clave] = valor;
    }
  }
  return detalle;
}

export function ConflictoSoD({
  detalle,
  onCerrar,
}: {
  detalle: DetalleConflictoSod;
  onCerrar: () => void;
}): React.JSX.Element {
  return (
    <div
      role="alert"
      aria-labelledby="conflicto-sod-titulo"
      className="mb-4 rounded-md border border-error-300 bg-error-50 p-4 text-error-800"
    >
      <p id="conflicto-sod-titulo" className="font-semibold">
        Operación bloqueada por segregación de funciones
      </p>
      <p className="mt-1 text-sm">
        Usted ya realizó «{detalle.accion_previa_etiqueta}» sobre este registro. La regla{" "}
        {detalle.regla_codigo} · {detalle.regla_nombre} impide que la misma persona realice también «
        {detalle.accion_etiqueta}».
      </p>
      <p className="mt-1 text-sm">
        El registro no cambió. Pida a otro usuario autorizado que realice esta acción.
      </p>
      <div className="mt-3">
        <Button variant="secondary" onClick={onCerrar}>
          Entendido
        </Button>
      </div>
    </div>
  );
}
