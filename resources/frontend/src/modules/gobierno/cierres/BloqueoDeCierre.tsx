import { Link } from "react-router";

import { ApiError } from "@/api/client";
import { Button } from "@/components/Button";
import {
  ETIQUETAS_ACCION_CIERRE,
  ETIQUETAS_TIPO_CONTROL_CIERRE,
  type DetalleBloqueoCierre,
} from "@/modules/gobierno/api";

function cadenaDeDetalle(valor: unknown): string {
  return typeof valor === "string" ? valor : "";
}

function numeroDeDetalle(valor: unknown): number {
  return typeof valor === "number" && Number.isFinite(valor) ? valor : 0;
}

function listaDeControles(valor: unknown): DetalleBloqueoCierre["controles"] {
  return Array.isArray(valor) ? (valor as DetalleBloqueoCierre["controles"]) : [];
}

/** Devuelve el detalle del 409 GOV_MATERIAL_CLOSE_BLOCKED si `e` lo es; si no, null. */
export function detalleDeBloqueoDeCierre(e: unknown): DetalleBloqueoCierre | null {
  if (!(e instanceof ApiError) || e.status !== 409 || e.code !== "GOV_MATERIAL_CLOSE_BLOCKED") {
    return null;
  }
  const details: Record<string, unknown> = e.details ?? {};
  const controles = listaDeControles(details.controles).map((control) => ({
    tipo: cadenaDeDetalle(control?.tipo) as DetalleBloqueoCierre["controles"][number]["tipo"],
    etiqueta: cadenaDeDetalle(control?.etiqueta),
    materialidad: cadenaDeDetalle(control?.materialidad),
    pendientes: numeroDeDetalle(control?.pendientes),
    muestra: Array.isArray(control?.muestra)
      ? (control.muestra as DetalleBloqueoCierre["controles"][number]["muestra"])
      : [],
    ruta_lista: cadenaDeDetalle(control?.ruta_lista),
  }));

  return {
    politica_codigo: cadenaDeDetalle(details.politica_codigo),
    politica_nombre: cadenaDeDetalle(details.politica_nombre),
    proceso: cadenaDeDetalle(details.proceso),
    objeto_codigo: cadenaDeDetalle(details.objeto_codigo),
    total: numeroDeDetalle(details.total),
    dueno: cadenaDeDetalle(details.dueno),
    controles,
  };
}

export function BloqueoDeCierre({
  detalle,
  onCerrar,
}: {
  detalle: DetalleBloqueoCierre;
  onCerrar: () => void;
}): React.JSX.Element {
  const etiquetaProceso =
    detalle.proceso in ETIQUETAS_ACCION_CIERRE
      ? ETIQUETAS_ACCION_CIERRE[detalle.proceso as keyof typeof ETIQUETAS_ACCION_CIERRE]
      : null;

  return (
    <div
      role="alert"
      aria-labelledby="bloqueo-de-cierre-titulo"
      className="mb-4 rounded-md border border-error-300 bg-error-50 p-4 text-error-800"
    >
      <p id="bloqueo-de-cierre-titulo" className="font-semibold">
        Cierre bloqueado por control material
      </p>
      <p className="mt-1 text-sm">
        La política {detalle.politica_codigo} · {detalle.politica_nombre} impide
        {etiquetaProceso ? ` «${etiquetaProceso}»` : ""} de {detalle.objeto_codigo}: hay{" "}
        {detalle.total} pendiente(s).
      </p>
      {detalle.controles.map((control) => (
        <div key={`${control.tipo}-${control.etiqueta}`} className="mt-3">
          <p className="font-semibold">
            {control.etiqueta || ETIQUETAS_TIPO_CONTROL_CIERRE[control.tipo] || control.tipo}
          </p>
          <p className="mt-1 text-sm">Por qué es material: {control.materialidad}</p>
          <p className="mt-1 text-sm">Pendientes: {control.pendientes}</p>
          {control.muestra.length > 0 ? (
            <ul className="mt-1 list-disc pl-5 text-sm">
              {control.muestra.map((pendiente) => (
                <li key={pendiente.ruta}>
                  <Link to={pendiente.ruta} className="underline">
                    {pendiente.codigo || pendiente.numero || ""} ·{" "}
                    {pendiente.titulo || pendiente.asunto || ""}
                  </Link>
                </li>
              ))}
            </ul>
          ) : null}
          {control.ruta_lista ? (
            <p className="mt-1 text-sm">
              <Link to={control.ruta_lista} className="underline">
                Ir a la lista
              </Link>
            </p>
          ) : null}
        </div>
      ))}
      <p className="mt-1 text-sm">Quién es dueño: {detalle.dueno}</p>
      <p className="mt-1 text-sm">
        El registro no cambió. Resuelva los pendientes y vuelva a intentar el cierre.
      </p>
      <div className="mt-3">
        <Button variant="secondary" onClick={onCerrar}>
          Entendido
        </Button>
      </div>
    </div>
  );
}
