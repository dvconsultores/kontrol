import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { apiFetch, ApiError } from "@/api/client";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { AsyncButton } from "@/components/AsyncButton";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { DataTable } from "@/components/DataTable";
import { formatearFecha } from "@/i18n";
import { hoyDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_ESTRUCTURAS,
  ETIQUETA_ESTADO_ESTRUCTURA,
  type Estructura,
  type EstructuraResumen,
  type ListaEstructuras,
} from "@/modules/gobierno/api";

const columnasEstructuras: ColumnDef<EstructuraResumen, unknown>[] = [
  {
    id: "ejercicio",
    header: "Ejercicio",
    cell: ({ row }) => (
      <Link
        to={`/gobierno/estructura/${row.original.ejercicio}`}
        className="font-medium text-brand-700 underline"
      >
        Estructura {row.original.ejercicio}
      </Link>
    ),
  },
  {
    id: "estado",
    header: "Estado",
    cell: ({ row }) => ETIQUETA_ESTADO_ESTRUCTURA[row.original.estado],
  },
  {
    id: "unidades_activas",
    header: "Unidades activas",
    cell: ({ row }) => row.original.unidades_activas,
  },
  {
    id: "publicada_en",
    header: "Puesta en vigor",
    cell: ({ row }) => formatearFecha(row.original.publicada_en),
  },
  {
    id: "cerrada_en",
    header: "Cerrada",
    cell: ({ row }) => formatearFecha(row.original.cerrada_en),
  },
];

export function EjerciciosPage(): React.JSX.Element {
  const { activeCompanyId } = useCompany();
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [ejercicio, setEjercicio] = useState<string>(
    String(Number(hoyDeNegocio().slice(0, 4))),
  );
  const [copiarDe, setCopiarDe] = useState<string>("");
  const [errorEjercicio, setErrorEjercicio] = useState<string | null>(null);
  const [errorCopiarDe, setErrorCopiarDe] = useState<string | null>(null);

  const lista = useQuery({
    queryKey: [...CONSULTA_ESTRUCTURAS, activeCompanyId],
    queryFn: () => apiFetch<ListaEstructuras>("/gobierno/estructuras"),
    enabled: Boolean(activeCompanyId),
    retry: false,
  });

  const puedeEditar = tiene("gobierno_estructura:edit", "empresa");

  const opcionesCopia = useMemo(() => {
    if (!lista.data) return [];
    return lista.data.items.filter(
      (item) =>
        item.estado === "VIGENTE" || item.estado === "CERRADA",
    );
  }, [lista.data]);

  const crumbs = [{ label: "Gobierno" }, { label: "Estructura organizativa" }];

  const guardar = async () => {
    setErrorEjercicio(null);
    setErrorCopiarDe(null);

    const ejercicioNumero = Number(ejercicio);
    if (
      !Number.isInteger(ejercicioNumero) ||
      ejercicio.length !== 4 ||
      ejercicioNumero < 1000 ||
      ejercicioNumero > 9999
    ) {
      setErrorEjercicio("Indique un año de cuatro cifras");
      return;
    }

    try {
      await apiFetch<Estructura>("/gobierno/estructuras", {
        method: "POST",
        body: {
          ejercicio: ejercicioNumero,
          copiar_de: copiarDe ? Number(copiarDe) : null,
        },
      });
      notify({ type: "success", title: "Estructura abierta en borrador" });
      await queryClient.invalidateQueries({
        queryKey: [...CONSULTA_ESTRUCTURAS, activeCompanyId],
      });
      navigate(`/gobierno/estructura/${ejercicioNumero}`);
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 409 && error.code === "GOV_STRUCTURE_ALREADY_EXISTS") {
          setErrorEjercicio("Ya existe la estructura de ese ejercicio");
        } else if (
          error.status === 422 &&
          error.code === "GOV_STRUCTURE_COPY_SOURCE_INVALID"
        ) {
          setErrorCopiarDe(error.message);
        } else if (error.status === 422 && error.code === "VALIDATION_ERROR") {
          setErrorEjercicio(error.fieldErrors.ejercicio?.[0] ?? null);
          setErrorCopiarDe(error.fieldErrors.copiar_de?.[0] ?? null);
        } else if (error.status === 403) {
          notify({
            type: "error",
            title: "No tiene permiso para esta acción",
          });
        } else {
          notify({
            type: "error",
            title: "No fue posible abrir la estructura",
            description: error.message,
          });
        }
      } else {
        notify({
          type: "error",
          title: "No fue posible abrir la estructura",
        });
      }
    }
  };

  if (lista.isLoading) {
    return (
      <PageContent>
        <PageHeader
          crumbs={crumbs}
          title="Estructura organizativa"
          description="Unidades del ente por ejercicio (del 1 de enero al 31 de diciembre)"
        />
        <LoadingState label="Cargando estructuras…" />
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
              title="Estructura organizativa"
              description="Unidades del ente por ejercicio (del 1 de enero al 31 de diciembre)"
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
              title="Estructura organizativa"
              description="Unidades del ente por ejercicio (del 1 de enero al 31 de diciembre)"
            />
            <EmptyState
              title="Sin acceso"
              description="No tiene permiso para ver la estructura organizativa."
            />
          </PageContent>
        );
      }
      if (error.status === 404 && error.code === "GOV_ENTITY_NOT_FOUND") {
        return (
          <PageContent>
            <PageHeader
              crumbs={crumbs}
              title="Estructura organizativa"
              description="Unidades del ente por ejercicio (del 1 de enero al 31 de diciembre)"
            />
            <EmptyState
              title="Primero configure el ente"
              description="La estructura organizativa pertenece al ente: regístrelo en Gobierno › Configuración del ente."
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
          title="Estructura organizativa"
          description="Unidades del ente por ejercicio (del 1 de enero al 31 de diciembre)"
        />
        <ErrorState
          message="No fue posible cargar las estructuras."
          onRetry={() => void lista.refetch()}
        />
      </PageContent>
    );
  }

  return (
    <PageContent>
      <PageHeader
        crumbs={crumbs}
        title="Estructura organizativa"
        description="Unidades del ente por ejercicio (del 1 de enero al 31 de diciembre)"
      />

      {puedeEditar && (
        <section
          aria-labelledby="abrir-estructura"
          className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4"
        >
          <h2 id="abrir-estructura" className="mb-4 text-lg font-semibold">
            Abrir la estructura de un ejercicio
          </h2>
          <form
            noValidate
            onSubmit={(evento) => {
              evento.preventDefault();
            }}
            aria-labelledby="abrir-estructura"
            className="grid grid-cols-1 gap-4 md:grid-cols-2"
          >
            <FormField
              label="Ejercicio"
              htmlFor="ejercicio"
              required
              error={errorEjercicio ?? undefined}
              help="Del 1 de enero al 31 de diciembre"
            >
              <TextInput
                id="ejercicio"
                type="number"
                inputMode="numeric"
                value={ejercicio}
                onChange={(evento) => setEjercicio(evento.target.value)}
                invalid={Boolean(errorEjercicio)}
              />
            </FormField>
            <FormField
              label="Copiar del ejercicio"
              htmlFor="copiar-de"
              error={errorCopiarDe ?? undefined}
              help="Opcional: parte de las unidades activas de otro ejercicio"
            >
              <select
                id="copiar-de"
                value={copiarDe}
                onChange={(evento) => setCopiarDe(evento.target.value)}
                aria-invalid={Boolean(errorCopiarDe)}
                className={`h-10 w-full rounded-md border bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600 ${
                  errorCopiarDe ? "border-danger-600" : "border-border-default"
                }`}
              >
                <option value="">No copiar: empezar vacía</option>
                {opcionesCopia.map((item) => (
                  <option key={item.ejercicio} value={item.ejercicio}>
                    {item.ejercicio} · {ETIQUETA_ESTADO_ESTRUCTURA[item.estado]}
                  </option>
                ))}
              </select>
            </FormField>
            <div className="md:col-span-2">
              <AsyncButton onClick={guardar} loadingText="Abriendo…">
                Abrir estructura
              </AsyncButton>
            </div>
          </form>
        </section>
      )}

      <section
        aria-labelledby="estructuras-por-ejercicio"
        className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4"
      >
        <h2
          id="estructuras-por-ejercicio"
          className="mb-4 text-lg font-semibold"
        >
          Estructuras por ejercicio
        </h2>
        <DataTable
          columns={columnasEstructuras}
          data={lista.data?.items ?? []}
          emptyTitle="Aún no hay estructuras"
          getRowId={(fila) => String(fila.ejercicio)}
        />
      </section>
    </PageContent>
  );
}
