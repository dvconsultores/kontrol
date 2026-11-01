import { useMemo } from "react";
import { Link } from "react-router";
import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { apiFetch, ApiError } from "@/api/client";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { DataTable } from "@/components/DataTable";
import {
  CONSULTA_ESTRUCTURAS,
  ETIQUETA_ESTADO_ESTRUCTURA,
  type EstructuraResumen,
  type ListaEstructuras,
} from "@/modules/gobierno/api";

const columnasEjercicios: ColumnDef<EstructuraResumen, unknown>[] = [
  {
    id: "ejercicio",
    header: "Ejercicio",
    cell: ({ row }) => (
      <Link
        to={`/gobierno/cargos/${row.original.ejercicio}`}
        className="font-medium text-brand-700 underline"
      >
        Cargos {row.original.ejercicio}
      </Link>
    ),
  },
  {
    id: "estado",
    header: "Estado de la estructura",
    cell: ({ row }) => ETIQUETA_ESTADO_ESTRUCTURA[row.original.estado],
  },
];

export function CargosEjerciciosPage(): React.JSX.Element {
  const { activeCompanyId } = useCompany();
  const { tiene } = useAutoridad();

  const crumbs = [{ label: "Gobierno" }, { label: "Cargos y competencias" }];

  const lista = useQuery({
    queryKey: [...CONSULTA_ESTRUCTURAS, activeCompanyId],
    queryFn: () => apiFetch<ListaEstructuras>("/gobierno/estructuras"),
    enabled: Boolean(activeCompanyId),
    retry: false,
  });

  const puedeVer = tiene("gobierno_cargos:view", "empresa");

  const itemsOrdenados = useMemo(() => {
    if (!lista.data) return [];
    return [...lista.data.items].sort((a, b) => b.ejercicio - a.ejercicio);
  }, [lista.data]);

  if (lista.isLoading) {
    return (
      <PageContent>
        <PageHeader
          crumbs={crumbs}
          title="Cargos y competencias"
          description="Elija el ejercicio para registrar los cargos del ente, sus competencias y sus límites de firma o aprobación."
        />
        <LoadingState label="Cargando ejercicios…" />
      </PageContent>
    );
  }

  if (lista.isError) {
    const error = lista.error;
    if (error instanceof ApiError) {
      if (error.status === 403 && error.code === "MODULE_NOT_ENTITLED") {
        return (
          <PageContent>
            <PageHeader
              crumbs={crumbs}
              title="Cargos y competencias"
              description="Elija el ejercicio para registrar los cargos del ente, sus competencias y sus límites de firma o aprobación."
            />
            <EmptyState
              title="El módulo de Gobierno no está habilitado"
              description="La licencia de esta instalación no incluye el módulo de Gobierno."
            />
          </PageContent>
        );
      }
      if (error.status === 403) {
        return (
          <PageContent>
            <PageHeader
              crumbs={crumbs}
              title="Cargos y competencias"
              description="Elija el ejercicio para registrar los cargos del ente, sus competencias y sus límites de firma o aprobación."
            />
            <EmptyState
              title="Sin acceso"
              description="No tiene permiso para ver los cargos y competencias."
            />
          </PageContent>
        );
      }
      if (error.status === 404 && error.code === "GOV_ENTITY_NOT_FOUND") {
        return (
          <PageContent>
            <PageHeader
              crumbs={crumbs}
              title="Cargos y competencias"
              description="Elija el ejercicio para registrar los cargos del ente, sus competencias y sus límites de firma o aprobación."
            />
            <EmptyState
              title="Primero configure el ente"
              description="Los cargos y competencias pertenecen al ente: regístrelo en Gobierno › Configuración del ente."
              action={
                <Link
                  to="/gobierno/ente"
                  className="font-medium text-brand-700 underline"
                >
                  Ir a Configuración del ente
                </Link>
              }
            />
          </PageContent>
        );
      }
    }
    return (
      <PageContent>
        <PageHeader
          crumbs={crumbs}
          title="Cargos y competencias"
          description="Elija el ejercicio para registrar los cargos del ente, sus competencias y sus límites de firma o aprobación."
        />
        <ErrorState
          message="No fue posible cargar las estructuras."
          onRetry={() => void lista.refetch()}
        />
      </PageContent>
    );
  }

  if (!puedeVer) {
    return (
      <PageContent>
        <PageHeader
          crumbs={crumbs}
          title="Cargos y competencias"
          description="Elija el ejercicio para registrar los cargos del ente, sus competencias y sus límites de firma o aprobación."
        />
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para ver los cargos y competencias."
        />
      </PageContent>
    );
  }

  return (
    <PageContent>
      <PageHeader
        crumbs={crumbs}
        title="Cargos y competencias"
        description="Elija el ejercicio para registrar los cargos del ente, sus competencias y sus límites de firma o aprobación."
      />

      <section
        aria-labelledby="ejercicios-con-estructura"
        className="rounded-lg border border-border-default bg-surface-0 p-4"
      >
        <h2
          id="ejercicios-con-estructura"
          className="mb-4 text-lg font-semibold"
        >
          Ejercicios con estructura organizativa
        </h2>
        <DataTable
          columns={columnasEjercicios}
          data={itemsOrdenados}
          emptyTitle="Aún no hay estructuras"
          emptyDescription="Los cargos se registran sobre la estructura organizativa de cada ejercicio."
          emptyAction={
            <Link
              to="/gobierno/estructura"
              className="font-medium text-brand-700 underline"
            >
              Ir a Estructura organizativa
            </Link>
          }
          getRowId={(fila) => String(fila.ejercicio)}

        />
      </section>
    </PageContent>
  );
}
