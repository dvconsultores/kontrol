import { useState } from "react";
import { Link } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_CAUSADOS,
  RUTA_POLITICAS,
  DISPARADORES,
  ESTADOS_POLITICA,
  type PoliticaCausado,
  ConfiguracionNumeracionCausados,
} from "./api";

export function PoliticasCausadoPage() {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const { notify } = useNotifications();
  const puedeVer = tiene("gobierno_presupuesto:view", "empresa");
  const puedeGestionar = tiene("gobierno_presupuesto:cause_policy", "empresa");
  const [patron, setPatron] = useState("");
  const [patronError, setPatronError] = useState<string | null>(null);
  const [guardandoPatron, setGuardandoPatron] = useState(false);

  const configuracion = useQuery({
    queryKey: [...CONSULTA_CAUSADOS, "configuracion", activeCompanyId],
    queryFn: () =>
      apiFetch<ConfiguracionNumeracionCausados>(
        "/gobierno/presupuesto/causados/configuracion",
      ),
    enabled: Boolean(activeCompanyId) && puedeVer,
    retry: false,
  });

  const politicas = useQuery({
    queryKey: [...CONSULTA_CAUSADOS, "politicas", activeCompanyId],
    queryFn: () =>
      apiFetch<PoliticaCausado[]>("/gobierno/presupuesto/politicas-causado"),
    enabled: Boolean(activeCompanyId) && puedeVer,
    retry: false,
  });

  const cabecera = (
    <PageHeader
      crumbs={[{ label: "Gobierno" }, { label: "Políticas de causado" }]}
      title="Políticas de causado"
      description="Qué hecho habilita causar cada tipo de gasto y qué se exige. Cada ente define las suyas."
      actions={
        puedeGestionar ? (
          <Link
            to={`${RUTA_POLITICAS}/nueva`}
            className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
          >
            Nueva política
          </Link>
        ) : null
      }
    />
  );

  if (!puedeVer) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState title="Sin acceso" description="No tiene permiso para ver las políticas de causado." />
      </PageContent>
    );
  }

  const guardarPatron = async () => {
    if (guardandoPatron) return;
    setPatronError(null);
    const version = configuracion.data?.version ?? 0;
    setGuardandoPatron(true);
    try {
      await apiFetch<ConfiguracionNumeracionCausados>(
        "/gobierno/presupuesto/causados/configuracion",
        {
          method: "PUT",
          body: { patron },
          ifMatch: String(version),
        },
      );
      notify({ type: "success", title: "Patrón guardado" });
      await configuracion.refetch();
    } catch (error) {
      if (error instanceof ApiError && error.fieldErrors?.patron) {
        setPatronError(error.fieldErrors.patron.join(" "));
      } else if (error instanceof ApiError) {
        setPatronError(error.message);
      } else {
        setPatronError("No fue posible guardar el patrón.");
      }
    } finally {
      setGuardandoPatron(false);
    }
  };

  if (politicas.isLoading || configuracion.isLoading) {
    return (
      <PageContent>
        {cabecera}
        <LoadingState label="Cargando políticas…" />
      </PageContent>
    );
  }

  if (politicas.isError) {
    const error = politicas.error;
    if (error instanceof ApiError && error.status === 403) {
      return (
        <PageContent>
          {cabecera}
          <EmptyState title="Sin acceso" description="No tiene permiso para ver las políticas de causado." />
        </PageContent>
      );
    }
    return (
      <PageContent>
        {cabecera}
        <ErrorState
          message="No fue posible cargar las políticas."
          onRetry={() => void politicas.refetch()}
        />
      </PageContent>
    );
  }

  if (!politicas.data) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState
          title="Aún no hay políticas de causado"
          description={puedeGestionar ? "Cree la primera para empezar a causar." : "No hay políticas de causado registradas."}
        />
      </PageContent>
    );
  }

  return (
    <PageContent>
      {cabecera}

      <section aria-labelledby="numeracion-titulo" className="mb-8">
        <h2 id="numeracion-titulo" className="text-lg font-semibold text-text-900">
          Numeración de los causados
        </h2>
        {configuracion.data?.configurado ? (
          <p className="mt-1 text-sm text-text-700">
            Patrón: <span className="font-medium">{configuracion.data.patron}</span> · Ejemplo:{" "}
            <span className="font-medium">{configuracion.data.ejemplo}</span>
          </p>
        ) : (
          <p className="mt-1 text-sm text-text-600">
            Aún no se ha definido un patrón de numeración.
          </p>
        )}
        {puedeGestionar ? (
          <form
            className="mt-3 grid gap-3 sm:grid-cols-[1fr_auto] sm:items-start"
            onSubmit={(evento) => {
              evento.preventDefault();
              void guardarPatron();
            }}
          >
            <FormField
              label="Patrón"
              htmlFor="patron-numeracion"
              error={patronError ?? undefined}
              help="Use {ANIO} y {NUMERO:n}, por ejemplo OBL/{ANIO}/{NUMERO:5}"
            >
              <TextInput
                id="patron-numeracion"
                value={patron}
                onChange={(evento) => setPatron(evento.target.value)}
                placeholder="OBL/{ANIO}/{NUMERO:5}"
              />
            </FormField>
            <Button
              type="submit"
              variant="primary"
              disabled={guardandoPatron}
            >
              {guardandoPatron ? "Guardando…" : "Guardar patrón"}
            </Button>
          </form>
        ) : null}
      </section>

      {politicas.data.length === 0 ? (
        <EmptyState
          title="Aún no hay políticas de causado"
          description={puedeGestionar ? "Cree la primera para empezar a causar." : "No hay políticas de causado registradas."}
        />
      ) : (
        <div
          className="relative overflow-x-auto"
          tabIndex={0}
          role="region"
          aria-label="Tabla de políticas de causado"
        >
          <table className="w-full min-w-[760px] border-collapse text-sm">
            <caption className="sr-only">Políticas de causado</caption>
            <thead>
              <tr className="border-b border-border-default text-left text-text-600">
                <th scope="col" className="px-3 py-2 font-medium">Código</th>
                <th scope="col" className="px-3 py-2 font-medium">Tipo de gasto</th>
                <th scope="col" className="px-3 py-2 font-medium">Nombre</th>
                <th scope="col" className="px-3 py-2 font-medium">Disparador</th>
                <th scope="col" className="px-3 py-2 font-medium">Estado</th>
                <th scope="col" className="px-3 py-2 font-medium">Vigencia</th>
              </tr>
            </thead>
            <tbody>
              {politicas.data.map((politica) => (
                <tr key={politica.id} className="border-b border-border-subtle align-top">
                  <td className="px-3 py-2">
                    <Link
                      to={`${RUTA_POLITICAS}/${politica.id}`}
                      aria-label={`Abrir la política ${politica.codigo}`}
                      className="font-medium text-brand-700 underline"
                    >
                      {politica.codigo}
                    </Link>
                  </td>
                  <td className="px-3 py-2">{politica.tipo_gasto}</td>
                  <td className="px-3 py-2 text-text-900">{politica.nombre}</td>
                  <td className="px-3 py-2">{DISPARADORES[politica.disparador]}</td>
                  <td className="px-3 py-2">{ESTADOS_POLITICA[politica.estado]}</td>
                  <td className="px-3 py-2">
                    {formatearFechaDeNegocio(politica.vigente_desde)}
                    {politica.vigente_hasta ? ` – ${formatearFechaDeNegocio(politica.vigente_hasta)}` : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </PageContent>
  );
}