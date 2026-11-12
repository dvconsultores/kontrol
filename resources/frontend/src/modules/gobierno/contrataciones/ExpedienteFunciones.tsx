import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_SOD_FUNCIONES,
  type ConflictoFuncion,
  type ExpedienteDetalle,
} from "../api";

/** Funciones incompatibles del expediente (PROC-11, GOV-PROC-017). */
export function SeccionFuncionesIncompatibles({
  detalle,
  activeCompanyId,
}: {
  detalle: ExpedienteDetalle;
  activeCompanyId: string | null;
}) {
  const { tiene } = useAutoridad();
  const puedeVer = tiene("gobierno_expedientes:view", "empresa");
  const puedeVerSod = tiene("gobierno_sod:view", "empresa");

  const consulta = useQuery({
    queryKey: [...CONSULTA_SOD_FUNCIONES, "expediente", activeCompanyId, detalle.id],
    queryFn: () =>
      apiFetch<ConflictoFuncion[]>(`/gobierno/sod/funciones/expedientes/${detalle.id}`),
    enabled: puedeVer && puedeVerSod && Boolean(activeCompanyId),
    retry: false,
  });

  if (!puedeVer) return null;

  return (
    <section aria-labelledby="funciones-incompatibles-titulo" className="mt-8">
      <h2 id="funciones-incompatibles-titulo" className="text-lg font-semibold text-text-900">
        Funciones incompatibles
      </h2>
      <p className="mt-1 text-sm text-text-600">
        La misma persona ejerciendo dos funciones que la matriz institucional declara incompatibles.
      </p>

      {!puedeVerSod ? (
        <p className="mt-3 text-sm text-text-600">
          No tiene permiso para consultar la matriz de funciones incompatibles.
        </p>
      ) : consulta.isLoading ? (
        <p className="mt-3 text-sm text-text-600">Consultando conflictos…</p>
      ) : consulta.isError ? (
        <p className="mt-3 text-sm text-text-600">
          {consulta.error instanceof ApiError && consulta.error.status === 403
            ? "No tiene permiso para consultar los conflictos de funciones."
            : "No fue posible consultar los conflictos de funciones."}
        </p>
      ) : (consulta.data ?? []).length === 0 ? (
        <p className="mt-3 text-sm text-text-700">
          Sin conflictos: ninguna persona ejerce dos funciones incompatibles en este expediente.{" "}
          <Link className="text-brand-700 underline" to="/gobierno/sod/funciones">
            Ver la matriz institucional
          </Link>
          .
        </p>
      ) : (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[42rem] border-collapse text-sm">
            <caption className="sr-only">Conflictos de funciones de este expediente</caption>
            <thead>
              <tr className="border-b border-border-subtle text-left text-xs uppercase tracking-wide text-text-600">
                <th scope="col" className="px-3 py-2">Regla</th>
                <th scope="col" className="px-3 py-2">Funciones</th>
                <th scope="col" className="px-3 py-2">Persona</th>
                <th scope="col" className="px-3 py-2">Evidencia</th>
              </tr>
            </thead>
            <tbody>
              {(consulta.data ?? []).map((conflicto) => (
                <tr
                  key={`${conflicto.regla_id}-${conflicto.actor}`}
                  className="border-b border-border-subtle align-top"
                >
                  <td className="px-3 py-2">{conflicto.regla_codigo}</td>
                  <td className="px-3 py-2">
                    {(conflicto.rol_a_etiqueta ?? conflicto.rol_a) +
                      " ≠ " +
                      (conflicto.rol_b_etiqueta ?? conflicto.rol_b)}
                  </td>
                  <td className="px-3 py-2">{conflicto.actor_nombre ?? conflicto.actor}</td>
                  <td className="px-3 py-2">
                    <ul className="space-y-1 text-xs text-text-600">
                      {conflicto.evidencia.map((evidencia) => (
                        <li key={`${evidencia.rol}-${evidencia.registro_id}`}>
                          {evidencia.registro} ({formatearFechaDeNegocio(evidencia.fecha)})
                        </li>
                      ))}
                    </ul>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
