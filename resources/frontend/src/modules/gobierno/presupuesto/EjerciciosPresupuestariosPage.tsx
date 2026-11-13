import { useId, useState } from "react";
import { Link, useNavigate } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { hoyDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_PRESUPUESTO,
  ETIQUETAS_ESTADO_EJERCICIO,
  RUTA_EJERCICIOS,
  type EjercicioResumen,
} from "./api";

type RespuestaLista = { items: EjercicioResumen[]; total: number };

export function EjerciciosPresupuestariosPage() {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const anioId = useId();
  const puedeVer = tiene("gobierno_presupuesto:view", "empresa");
  const puedeGestionar = tiene("gobierno_presupuesto:manage", "empresa");

  const [anio, setAnio] = useState(String(Number(hoyDeNegocio().slice(0, 4)) + 1));
  const [erroresServidor, setErroresServidor] = useState<Record<string, string[]>>({});

  const consultaEjercicios = useQuery({
    queryKey: [...CONSULTA_PRESUPUESTO, activeCompanyId, "lista"],
    queryFn: () => apiFetch<RespuestaLista>(RUTA_EJERCICIOS),
    enabled: Boolean(activeCompanyId),
    retry: false,
  });

  const crearEjercicio = async () => {
    setErroresServidor({});
    try {
      const anioNumero = Number(anio);
      const nuevo = await apiFetch<import("./api").EjercicioDetalle>(RUTA_EJERCICIOS, {
        method: "POST",
        body: { anio: anioNumero },
      });
      notify({
        type: "success",
        title: `Ejercicio ${anioNumero} creado`,
      });
      void queryClient.invalidateQueries({ queryKey: [...CONSULTA_PRESUPUESTO] });
      navigate(`${RUTA_EJERCICIOS}/${nuevo.id}`);
    } catch (e) {
      if (e instanceof ApiError && e.status === 409 && e.code === "GOV_BUDGET_YEAR_EXISTS") {
        setErroresServidor({ anio: ["Ya existe el ejercicio de ese año"] });
      } else if (e instanceof ApiError && e.status === 422) {
        setErroresServidor(e.fieldErrors ?? {});
      } else {
        notify({
          type: "error",
          title: "No fue posible crear el ejercicio.",
        });
      }
    }
  };

  const cabecera = (
    <PageHeader
      crumbs={[{ label: "Gobierno" }, { label: "Presupuesto" }]}
      title="Ejercicios presupuestarios"
      description="Ejercicio, estructura programática y clasificador registrado por el ente. Lo aprobado o reconducido queda fijado."
    />
  );

  if (!puedeVer) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para ver los ejercicios presupuestarios."
        />
      </PageContent>
    );
  }

  if (consultaEjercicios.isLoading) {
    return (
      <PageContent>
        {cabecera}
        <LoadingState label="Cargando ejercicios presupuestarios…" />
      </PageContent>
    );
  }

  if (consultaEjercicios.isError) {
    const error = consultaEjercicios.error;
    if (error instanceof ApiError && error.status === 403 && error.code === "MODULE_NOT_ENTITLED") {
      return (
        <PageContent>
          {cabecera}
          <EmptyState
            title="Módulo no habilitado"
            description="El módulo de Gobierno no está habilitado en la licencia."
          />
        </PageContent>
      );
    }
    if (error instanceof ApiError && error.status === 403) {
      return (
        <PageContent>
          {cabecera}
          <EmptyState
            title="Sin acceso"
            description="No tiene permiso para ver los ejercicios presupuestarios."
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        {cabecera}
        <ErrorState
          message="No fue posible cargar los ejercicios presupuestarios."
          onRetry={() => void consultaEjercicios.refetch()}
        />
      </PageContent>
    );
  }

  const ejercicios = consultaEjercicios.data?.items ?? [];

  return (
    <PageContent>
      {cabecera}

      {puedeGestionar ? (
        <section aria-labelledby="nuevo-ejercicio-titulo" className="mb-8">
          <h2 id="nuevo-ejercicio-titulo" className="mb-4 text-lg font-semibold text-text-900">
            Nuevo ejercicio
          </h2>
          <form
            className="grid grid-cols-1 items-end gap-4 rounded-lg border border-border-default p-4 sm:grid-cols-2"
            onSubmit={(evento) => {
              evento.preventDefault();
              void crearEjercicio();
            }}
          >
            <FormField
              label="Año"
              htmlFor={anioId}
              error={erroresServidor.anio?.[0]}
            >
              <TextInput
                id={anioId}
                type="number"
                min={2000}
                max={2100}
                value={anio}
                aria-invalid={erroresServidor.anio ? true : undefined}
                onChange={(e) => setAnio(e.target.value)}
                required
              />
            </FormField>
            <AsyncButton onClick={crearEjercicio} idleText="Crear ejercicio" loadingText="Creando…" />
          </form>
        </section>
      ) : null}

      <section aria-labelledby="ejercicios-titulo">
        <h2 id="ejercicios-titulo" className="mb-4 text-lg font-semibold text-text-900">
          Ejercicios presupuestarios
        </h2>
        {ejercicios.length === 0 ? (
          <EmptyState
            title="Aún no hay ejercicios presupuestarios"
            description={
              puedeGestionar
                ? "Registre el primer ejercicio con «Nuevo ejercicio»."
                : undefined
            }
          />
        ) : (
          <div className="relative overflow-x-auto" tabIndex={0} role="region" aria-label="Tabla de ejercicios presupuestarios">
            <table className="w-full border-collapse text-left">
              <caption className="sr-only">Ejercicios presupuestarios</caption>
              <thead>
                <tr className="border-b border-border-subtle">
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">Año</th>
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">Estado</th>
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">Moneda</th>
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">Precompromiso</th>
                </tr>
              </thead>
              <tbody>
                {ejercicios.map((ejercicio) => (
                  <tr key={ejercicio.id} className="border-b border-border-subtle">
                    <td className="px-3 py-2 text-sm text-text-900">
                      <Link
                        to={`${RUTA_EJERCICIOS}/${ejercicio.id}`}
                        className="font-medium text-brand-700 hover:underline"
                      >
                        Ejercicio {ejercicio.anio}
                      </Link>
                    </td>
                    <td className="px-3 py-2 text-sm text-text-900">
                      {ETIQUETAS_ESTADO_EJERCICIO[ejercicio.estado]}
                    </td>
                    <td className="px-3 py-2 text-sm text-text-900">{ejercicio.moneda_funcional}</td>
                    <td className="px-3 py-2 text-sm text-text-900">
                      {ejercicio.precompromiso_activo ? "Activo" : "No activo"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </PageContent>
  );
}
