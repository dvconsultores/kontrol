import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link } from "react-router";

import { ApiError, apiFetch } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { ErrorState } from "@/components/ErrorState";
import { ForbiddenState } from "@/components/ForbiddenState";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { PageHeader } from "@/components/PageHeader";
import { PageContent } from "@/layout/PageContent";

import { CONSULTA_CONTRATOS } from "./api";

const FUENTES = ["CONTRATO", "HITO", "ENTREGABLE"] as const;
type Fuente = (typeof FUENTES)[number];

interface PoliticaItem {
  fuente: Fuente;
  activo: boolean;
  dias_anticipacion: number | null;
}

interface Politicas {
  items: PoliticaItem[];
  garantias_dias_por_vencer: number;
  fases_por_defecto: string[];
}

interface Borrador {
  activo: boolean;
  dias: string;
}

const CLAVE_BORRADOR_INICIAL: Record<Fuente, Borrador> = {
  CONTRATO: { activo: false, dias: "" },
  HITO: { activo: false, dias: "" },
  ENTREGABLE: { activo: false, dias: "" },
};

const ETIQUETAS_FUENTE: Record<Fuente, string> = {
  CONTRATO: "Contratos",
  HITO: "Hitos",
  ENTREGABLE: "Entregables",
};

export function AlertasPoliticaPage(): React.JSX.Element {
  const { activeCompanyId } = useCompany();
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();

  const puedeVer = tiene("gobierno_contratos:view", "empresa");
  const puedeConfigurar = tiene("notificaciones:configure", "empresa");
  const puedeVerAlertas = tiene("alertas:view", "empresa");

  const [borrador, setBorrador] = useState<Record<Fuente, Borrador>>(CLAVE_BORRADOR_INICIAL);
  const [errorGuardado, setErrorGuardado] = useState<string | null>(null);

  const clave = [...CONSULTA_CONTRATOS, activeCompanyId, "alertas-politicas"];

  const consulta = useQuery({
    queryKey: clave,
    queryFn: () => apiFetch<Politicas>("/gobierno/contratos-alertas/politicas"),
    enabled: Boolean(activeCompanyId) && puedeVer,
    retry: false,
  });

  useEffect(() => {
    if (consulta.data) {
      const siguiente = { ...CLAVE_BORRADOR_INICIAL };
      for (const item of consulta.data.items) {
        siguiente[item.fuente] = {
          activo: item.activo,
          dias: item.dias_anticipacion === null ? "" : String(item.dias_anticipacion),
        };
      }
      setBorrador(siguiente);
    }
  }, [consulta.data]);

  if (!puedeVer) {
    return <ForbiddenState />;
  }

  const guardar = async (): Promise<void> => {
    setErrorGuardado(null);
    const body = {
      items: FUENTES.map((fuente) => ({
        fuente,
        activo: borrador[fuente].activo,
        dias_anticipacion: borrador[fuente].dias === "" ? null : Number(borrador[fuente].dias),
      })),
    };
    try {
      const respuesta = await apiFetch<Politicas>("/gobierno/contratos-alertas/politicas", {
        method: "PUT",
        body,
      });
      queryClient.setQueryData(clave, respuesta);
      notify({
        type: "success",
        title: "Preaviso guardado",
        description: "Las alertas se recalculan en el próximo ciclo del planificador.",
      });
    } catch (error) {
      if (error instanceof ApiError) {
        setErrorGuardado(error.message);
      } else {
        setErrorGuardado("No fue posible guardar el preaviso.");
      }
    }
  };

  return (
    <PageContent>
      <PageHeader
        title="Alertas de vencimiento"
        description="Preaviso institucional de las alertas de contratos, hitos y entregables. Las alertas informan; no deciden."
        crumbs={[
          { label: "Gobierno" },
          { label: "Contratos y órdenes", to: "/gobierno/contratos" },
          { label: "Alertas de vencimiento" },
        ]}
      />

      {consulta.isLoading ? (
        <LoadingState />
      ) : consulta.isError ? (
        <ErrorState message="No fue posible consultar el preaviso." onRetry={() => void consulta.refetch()} />
      ) : (
        <>
          <section aria-labelledby="reglas-fijas-titulo" className="mb-6">
            <h2 id="reglas-fijas-titulo" className="text-lg font-semibold text-text-900">
              Reglas fijas
            </h2>
            <ul className="mt-2 flex list-inside list-disc flex-col gap-1 text-sm text-text-700">
              <li>
                Contratos, hitos y entregables: alerta el día del vencimiento y cuando vence, aunque no haya preaviso
                configurado.
              </li>
              <li>
                Garantías: por vencer desde {consulta.data?.garantias_dias_por_vencer ?? 0} días antes y vencidas (regla
                de PROC-10; no se configura aquí).
              </li>
              <li>El plazo de firma en días hábiles no genera alertas: no hay calendario hábil institucional.</li>
            </ul>
          </section>

          <section aria-labelledby="preaviso-fuente-titulo" className="mb-6">
            <h2 id="preaviso-fuente-titulo" className="text-lg font-semibold text-text-900">
              Preaviso por fuente
            </h2>
            {!puedeConfigurar ? (
              <p className="text-sm text-text-600">
                Solo quien puede configurar notificaciones modifica el preaviso.
              </p>
            ) : null}
            <div className="mt-3 flex flex-col gap-4">
              {FUENTES.map((fuente) => (
                <fieldset key={fuente} className="rounded-lg border border-border-default bg-surface-0 p-3">
                  <legend className="px-1 text-sm font-medium text-text-900">{ETIQUETAS_FUENTE[fuente]}</legend>
                  <label className="flex items-center gap-2 text-sm text-text-700">
                    <input
                      id={`politica-${fuente}-activo`}
                      type="checkbox"
                      checked={borrador[fuente].activo}
                      disabled={!puedeConfigurar}
                      onChange={(e) =>
                        setBorrador((previo) => ({
                          ...previo,
                          [fuente]: { ...previo[fuente], activo: e.target.checked },
                        }))
                      }
                    />
                    Activar preaviso
                  </label>
                  <div className="mt-2 max-w-xs">
                    <FormField label="Días de anticipación" htmlFor={`politica-${fuente}-dias`}>
                      <input
                        id={`politica-${fuente}-dias`}
                        type="number"
                        min={1}
                        max={365}
                        value={borrador[fuente].dias}
                        disabled={!puedeConfigurar}
                        className="h-10 w-full max-w-[10rem] rounded-md border border-border-default bg-surface-0 px-3 text-sm"
                        onChange={(e) =>
                          setBorrador((previo) => ({
                            ...previo,
                            [fuente]: { ...previo[fuente], dias: e.target.value },
                          }))
                        }
                      />
                    </FormField>
                  </div>
                </fieldset>
              ))}
            </div>
          </section>

          {errorGuardado ? (
            <p role="alert" className="mb-4 text-sm text-danger-600">
              {errorGuardado}
            </p>
          ) : null}

          {puedeConfigurar ? (
            <AsyncButton onClick={guardar} loadingText="Guardando…">
              Guardar preaviso
            </AsyncButton>
          ) : null}

          {puedeVerAlertas ? (
            <p className="mt-4">
              <Link to="/alertas" className="text-sm text-brand-700 underline">
                Ver alertas
              </Link>
            </p>
          ) : null}
        </>
      )}
    </PageContent>
  );
}
