import { useState } from "react";
import { Link } from "react-router";
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { TextInput } from "@/components/TextInput";
import { FormField } from "@/components/FormField";
import { Button } from "@/components/Button";
import {
  CONSULTA_CAJA,
  ETIQUETAS_TIPO_RUBRO,
  ETIQUETAS_ESTADO_RUBRO,
  consultaDeRubros,
} from "@/modules/gobierno/api";
import type {
  RubrosListado,
  RubroEntrada,
  RubroCambios,
  TipoRubro,
  EstadoRubro,
  Rubro,
} from "@/modules/gobierno/api";

const OPCIONES_TIPO_RUBRO: Array<{ valor: TipoRubro; etiqueta: string }> = [
  { valor: "INGRESO", etiqueta: "Ingreso" },
  { valor: "DESEMBOLSO", etiqueta: "Desembolso" },
];

export function RubrosPage(): React.JSX.Element {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();

  const [codigo, setCodigo] = useState("");
  const [nombre, setNombre] = useState("");
  const [tipo, setTipo] = useState<TipoRubro | "">("");
  const [errorCodigo, setErrorCodigo] = useState<string | null>(null);
  const [errorNombre, setErrorNombre] = useState<string | null>(null);
  const [errorTipo, setErrorTipo] = useState<string | null>(null);
  const [editandoId, setEditandoId] = useState<string | null>(null);
  const [editandoNombre, setEditandoNombre] = useState("");
  const [errorEdicion, setErrorEdicion] = useState<string | null>(null);
  const [avisoVersion, setAvisoVersion] = useState<string | null>(null);

  const [filtroTipo, setFiltroTipo] = useState<TipoRubro | "">("");
  const [filtroEstado, setFiltroEstado] = useState<EstadoRubro | "">("");

  const puedeVer = tiene("gobierno_caja:view", "empresa");
  const puedeGestionar = tiene("gobierno_caja:manage", "empresa");

  const filtros = {
    ...(filtroTipo ? { tipo: filtroTipo } : {}),
    ...(filtroEstado ? { estado: filtroEstado } : {}),
  };

  const consultaRubros = useQuery({
    queryKey: [...CONSULTA_CAJA, "rubros", activeCompanyId, filtros],
    queryFn: () =>
      apiFetch<RubrosListado>(
        `/gobierno/tesoreria/rubros${consultaDeRubros(filtros)}`,
      ),
    enabled: puedeVer && Boolean(activeCompanyId),
    placeholderData: keepPreviousData,
    retry: false,
  });

  const crearRubro = useMutation({
    mutationFn: (entrada: RubroEntrada) =>
      apiFetch<Rubro>(`/gobierno/tesoreria/rubros`, {
        method: "POST",
        body: entrada,
      }),
    onSuccess: () => {
      setCodigo("");
      setNombre("");
      setTipo("");
      setErrorCodigo(null);
      setErrorNombre(null);
      setErrorTipo(null);
      void queryClient.invalidateQueries({ queryKey: CONSULTA_CAJA });
      notify({ type: "success", title: "Rubro registrado" });
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError) {
        if (error.status === 409 && error.code === "GOV_CASH_ITEM_DUPLICATE") {
          setErrorCodigo("Ya existe un rubro con este código.");
          return;
        }
        if (error.status === 422 && error.fieldErrors) {
          if (error.fieldErrors.codigo) {
            setErrorCodigo(error.fieldErrors.codigo[0]);
          }
          if (error.fieldErrors.nombre) {
            setErrorNombre(error.fieldErrors.nombre[0]);
          }
          if (error.fieldErrors.tipo) {
            setErrorTipo(error.fieldErrors.tipo[0]);
          }
          return;
        }
      }
      notify({ type: "error", title: "No fue posible registrar el rubro" });
    },
  });

  const actualizarRubro = useMutation({
    mutationFn: ({
      id,
      version,
      cambios,
    }: {
      id: string;
      version: number;
      cambios: RubroCambios;
    }) =>
      apiFetch<Rubro>(`/gobierno/tesoreria/rubros/${id}`, {
        method: "PATCH",
        body: cambios,
        ifMatch: String(version),
      }),
    onSuccess: () => {
      setEditandoId(null);
      setEditandoNombre("");
      setErrorEdicion(null);
      setAvisoVersion(null);
      void queryClient.invalidateQueries({ queryKey: CONSULTA_CAJA });
      notify({ type: "success", title: "Rubro actualizado" });
    },
    onError: (error: unknown) => {
      if (
        error instanceof ApiError &&
        error.status === 409 &&
        error.code === "GOV_CASH_PROGRAM_STALE"
      ) {
        setAvisoVersion(
          "El rubro fue modificado por otra persona. Se recargaron los datos; revise los cambios antes de continuar.",
        );
        void queryClient.invalidateQueries({ queryKey: CONSULTA_CAJA });
      } else {
        notify({ type: "error", title: "No fue posible actualizar el rubro" });
      }
    },
  });

  const cabecera = (
    <PageHeader
      crumbs={[
        { label: "Gobierno", to: "/gobierno" },
        { label: "Tesorería", to: "/gobierno/tesoreria/programacion" },
        { label: "Rubros de caja" },
      ]}
      title="Rubros de caja"
      description="Los rubros clasifican ingresos y desembolsos de la programación del ente; no son partidas presupuestarias."
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <Link
            to="/gobierno/tesoreria/programacion"
            className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
          >
            Programación
          </Link>
        </div>
      }
    />
  );

  if (!puedeVer) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para ver el catálogo de rubros."
        />
      </PageContent>
    );
  }

  if (consultaRubros.isLoading) {
    return (
      <PageContent>
        {cabecera}
        <LoadingState label="Cargando rubros…" />
      </PageContent>
    );
  }

  if (consultaRubros.isError) {
    const error = consultaRubros.error;
    if (
      error instanceof ApiError &&
      error.status === 403 &&
      error.code === "MODULE_NOT_ENTITLED"
    ) {
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
            description="No tiene permiso para ver el catálogo de rubros."
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        {cabecera}
        <ErrorState
          message="No fue posible cargar los rubros."
          onRetry={() => void consultaRubros.refetch()}
        />
      </PageContent>
    );
  }

  const rubros = consultaRubros.data?.items ?? [];

  const registrarRubro = () => {
    setErrorCodigo(null);
    setErrorNombre(null);
    setErrorTipo(null);

    const codigoLimpio = codigo.trim();
    const nombreLimpio = nombre.trim();

    if (codigoLimpio.length < 1 || codigoLimpio.length > 20) {
      setErrorCodigo("El código debe tener entre 1 y 20 caracteres");
      return;
    }
    if (nombreLimpio.length < 3 || nombreLimpio.length > 120) {
      setErrorNombre("El nombre debe tener entre 3 y 120 caracteres");
      return;
    }
    if (!tipo) {
      setErrorTipo("Seleccione un tipo");
      return;
    }

    crearRubro.mutate({
      codigo: codigoLimpio,
      nombre: nombreLimpio,
      tipo,
    });
  };

  const iniciarEdicion = (rubro: Rubro) => {
    setAvisoVersion(null);
    setEditandoId(rubro.id);
    setEditandoNombre(rubro.nombre);
    setErrorEdicion(null);
  };

  const cancelarEdicion = () => {
    setEditandoId(null);
    setEditandoNombre("");
    setErrorEdicion(null);
  };

  const guardarEdicion = (rubro: Rubro) => {
    setErrorEdicion(null);
    const nombreLimpio = editandoNombre.trim();
    if (nombreLimpio.length < 3 || nombreLimpio.length > 120) {
      setErrorEdicion("El nombre debe tener entre 3 y 120 caracteres");
      return;
    }
    if (nombreLimpio === rubro.nombre) {
      cancelarEdicion();
      return;
    }
    actualizarRubro.mutate({
      id: rubro.id,
      version: rubro.version,
      cambios: { nombre: nombreLimpio },
    });
  };

  const alternarEstado = (rubro: Rubro) => {
    setAvisoVersion(null);
    const nuevoEstado: EstadoRubro =
      rubro.estado === "ACTIVO" ? "INACTIVO" : "ACTIVO";
    actualizarRubro.mutate({
      id: rubro.id,
      version: rubro.version,
      cambios: { estado: nuevoEstado },
    });
  };

  return (
    <PageContent>
      {cabecera}

      {avisoVersion ? (
        <div
          role="alert"
          className="mb-6 rounded-md bg-error-50 px-4 py-3 text-sm text-error-800"
        >
          {avisoVersion}
        </div>
      ) : null}

      <section aria-labelledby="filtros-rubros-titulo" className="mb-8">
        <h2 id="filtros-rubros-titulo" className="sr-only">
          Filtros de rubros
        </h2>
        <div className="relative grid gap-4 sm:grid-cols-[160px_160px_auto] sm:items-end">
          <FormField label="Filtrar por tipo">
            <select
              id="rubro-filtro-tipo"
              value={filtroTipo}
              onChange={(evento) =>
                setFiltroTipo(evento.target.value as TipoRubro | "")
              }
              className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm"
            >
              <option value="">Todos</option>
              {OPCIONES_TIPO_RUBRO.map((opcion) => (
                <option key={opcion.valor} value={opcion.valor}>
                  {opcion.etiqueta}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Filtrar por estado">
            <select
              id="rubro-filtro-estado"
              value={filtroEstado}
              onChange={(evento) =>
                setFiltroEstado(evento.target.value as EstadoRubro | "")
              }
              className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm"
            >
              <option value="">Todos</option>
              <option value="ACTIVO">Activo</option>
              <option value="INACTIVO">Inactivo</option>
            </select>
          </FormField>
          <div className="flex items-center">
            <Button
              type="button"
              onClick={() => {
                setFiltroTipo("");
                setFiltroEstado("");
              }}
            >
              Limpiar filtros
            </Button>
          </div>
        </div>
      </section>

      {puedeGestionar ? (
        <section aria-labelledby="registrar-rubro-titulo" className="mb-8">
          <h2 id="registrar-rubro-titulo" className="text-lg font-semibold text-text-900 mb-4">
            Registrar rubro
          </h2>
          <form
            onSubmit={(evento) => {
              evento.preventDefault();
              registrarRubro();
            }}
            className="relative grid gap-4 sm:grid-cols-[160px_1fr_160px_auto] sm:items-end"
          >
            <FormField
              label="Código"
              required
              error={errorCodigo ?? undefined}
              help="De 1 a 20 caracteres"
            >
              <TextInput
                id="rubro-codigo"
                value={codigo}
                onChange={(evento) => setCodigo(evento.target.value)}
                maxLength={20}
                required
              />
            </FormField>
            <FormField
              label="Nombre"
              required
              error={errorNombre ?? undefined}
              help="De 3 a 120 caracteres"
            >
              <TextInput
                id="rubro-nombre"
                value={nombre}
                onChange={(evento) => setNombre(evento.target.value)}
                maxLength={120}
                required
              />
            </FormField>
            <FormField
              label="Tipo"
              required
              error={errorTipo ?? undefined}
            >
              <select
                id="rubro-tipo"
                value={tipo}
                onChange={(evento) =>
                  setTipo(evento.target.value as TipoRubro | "")
                }
                required
                className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm"
              >
                <option value="">Seleccione…</option>
                {OPCIONES_TIPO_RUBRO.map((opcion) => (
                  <option key={opcion.valor} value={opcion.valor}>
                    {opcion.etiqueta}
                  </option>
                ))}
              </select>
            </FormField>
            <div className="flex items-center">
              <Button type="submit" disabled={crearRubro.isPending}>
                Registrar rubro
              </Button>
            </div>
          </form>
        </section>
      ) : null}

      {rubros.length === 0 ? (
        <EmptyState
          title="Aún no hay rubros"
          description={
            puedeGestionar
              ? "Registre el primero con el formulario de arriba."
              : "No hay rubros para los filtros seleccionados."
          }
        />
      ) : (
        <div
          className="relative overflow-x-auto"
          tabIndex={0}
          role="region"
          aria-label="Tabla de rubros"
        >
          <table className="w-full min-w-[640px] border-collapse text-sm">
            <caption className="sr-only">Rubros del catálogo</caption>
            <thead>
              <tr className="border-b border-border-default text-left text-text-600">
                <th scope="col" className="px-3 py-2 font-medium">
                  Código
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Nombre
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Tipo
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Estado
                </th>
                {puedeGestionar ? (
                  <th scope="col" className="px-3 py-2 font-medium">
                    Acciones
                  </th>
                ) : null}
              </tr>
            </thead>
            <tbody>
              {rubros.map((rubro) => (
                <tr
                  key={rubro.id}
                  className="border-b border-border-subtle align-top"
                >
                  <td className="px-3 py-2 font-medium text-text-900">
                    {rubro.codigo}
                  </td>
                  <td className="px-3 py-2">
                    {editandoId === rubro.id ? (
                      <div className="flex flex-col gap-1">
                        <TextInput
                          value={editandoNombre}
                          onChange={(evento) =>
                            setEditandoNombre(evento.target.value)
                          }
                          aria-label={`Nombre del rubro ${rubro.nombre}`}
                          aria-invalid={Boolean(errorEdicion)}
                        />
                        {errorEdicion ? (
                          <span className="text-sm text-danger-600">
                            {errorEdicion}
                          </span>
                        ) : null}
                      </div>
                    ) : (
                      <span className="text-text-900">{rubro.nombre}</span>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    <span className="text-text-900">
                      {ETIQUETAS_TIPO_RUBRO[rubro.tipo]}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <span className="inline-flex items-center rounded-full bg-surface-100 px-2 py-0.5 text-xs font-medium text-text-700">
                      {ETIQUETAS_ESTADO_RUBRO[rubro.estado]}
                    </span>
                  </td>
                  {puedeGestionar ? (
                    <td className="px-3 py-2">
                      {editandoId === rubro.id ? (
                        <div className="flex flex-wrap items-center gap-2">
                          <Button
                            type="button"
                            onClick={() => guardarEdicion(rubro)}
                          >
                            Guardar
                          </Button>
                          <button
                            type="button"
                            onClick={cancelarEdicion}
                            className="inline-flex h-8 items-center rounded-md border border-border-default px-2 text-sm font-medium text-text-700 hover:bg-surface-100"
                          >
                            Cancelar
                          </button>
                        </div>
                      ) : (
                        <div className="flex flex-wrap items-center gap-2">
                          <button
                            type="button"
                            onClick={() => iniciarEdicion(rubro)}
                            aria-label={`Editar el rubro ${rubro.nombre}`}
                            className="inline-flex h-8 items-center rounded-md border border-border-default px-2 text-sm font-medium text-text-700 hover:bg-surface-100"
                          >
                            Editar
                          </button>
                          <Button
                            type="button"
                            onClick={() => alternarEstado(rubro)}
                            aria-label={
                              rubro.estado === "ACTIVO"
                                ? `Inactivar el rubro ${rubro.nombre}`
                                : `Activar el rubro ${rubro.nombre}`
                            }
                            className="inline-flex h-8 items-center rounded-md border border-border-default px-2 text-sm font-medium text-text-700 hover:bg-surface-100"
                          >
                            {rubro.estado === "ACTIVO"
                              ? "Inactivar"
                              : "Activar"}
                          </Button>
                        </div>
                      )}
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </PageContent>
  );
}
