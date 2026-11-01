import { useCallback, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Plus } from "lucide-react";

import { apiFetch, ApiError } from "@/api/client";
import { descargarArchivo } from "@/api/descargas";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/Button";
import { AsyncButton } from "@/components/AsyncButton";
import { TextInput } from "@/components/TextInput";
import { FormField } from "@/components/FormField";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { ConflictState } from "@/components/ConflictState";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_CARGOS,
  CONSULTA_ESTRUCTURAS,
  describirLimite,
  ETIQUETA_ACCION,
  ETIQUETA_ESTADO_CARGO,
  ETIQUETA_MATERIA,
  type Cargo,
  type Estructura,
  type ListaCargos,
} from "@/modules/gobierno/api";

import { CargoFormulario, type CambiosCargo } from "./CargoFormulario";

type Panel =
  | { tipo: "ninguno" }
  | {
      tipo: "crear";
    };

const CLASE_SELECT =
  "h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600";

export function CargosPage(): React.JSX.Element {
  const { ejercicio: ejercicioParam } = useParams();
  const ejercicio = Number(ejercicioParam);
  const { activeCompanyId } = useCompany();
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const [panel, setPanel] = useState<Panel>({ tipo: "ninguno" });
  const [erroresServidor, setErroresServidor] = useState<Record<string, string[]>>({});
  const [conflicto, setConflicto] = useState(false);
  const [busqueda, setBusqueda] = useState("");
  const [unidadId, setUnidadId] = useState("");
  const [estado, setEstado] = useState("");

  const puedeVer = tiene("gobierno_cargos:view", "empresa");

  const consultaEstructura = useQuery({
    queryKey: [...CONSULTA_ESTRUCTURAS, activeCompanyId, ejercicio],
    queryFn: () => apiFetch<Estructura>(`/gobierno/estructuras/${ejercicio}`),
    enabled:
      Boolean(activeCompanyId) &&
      Number.isInteger(ejercicio) &&
      tiene("gobierno_cargos:view", "empresa"),
    retry: false,
  });

  const consultaCargos = useQuery({
    queryKey: [...CONSULTA_CARGOS, activeCompanyId, ejercicio],
    queryFn: () =>
      apiFetch<ListaCargos>(
        `/gobierno/estructuras/${ejercicio}/cargos`,
      ),
    enabled:
      Boolean(activeCompanyId) &&
      Number.isInteger(ejercicio) &&
      tiene("gobierno_cargos:view", "empresa"),
    retry: false,
  });

  const recargar = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: [...CONSULTA_CARGOS] });
    void queryClient.invalidateQueries({ queryKey: [...CONSULTA_ESTRUCTURAS] });
  }, [queryClient]);

  const estructura = consultaEstructura.data;
  const puedeEditar =
    tiene("gobierno_cargos:edit", "empresa") &&
    consultaCargos.data?.estructura?.estado !== "CERRADA";

  const manejarError = useCallback(
    (e: unknown) => {
      if (e instanceof ApiError) {
        if (e.status === 409 && e.code === "GOV_POSITION_STALE") {
          setConflicto(true);
          recargar();
          return;
        }
        if (e.status === 422 && e.code === "VALIDATION_ERROR") {
          setErroresServidor(e.fieldErrors);
          return;
        }
        if (e.status === 409 && e.code === "GOV_POSITION_CODE_DUPLICATE") {
          setErroresServidor({ codigo: [e.message] });
          return;
        }
        if (e.status === 422 && e.code === "GOV_POSITION_INVALID_UNIT") {
          setErroresServidor({ unidad_id: [e.message] });
          return;
        }
        if (e.status === 409 && e.code === "GOV_COMPETENCY_DUPLICATE") {
          setErroresServidor({ materia: [e.message] });
          return;
        }
        if (e.status === 422 && e.code === "GOV_POSITION_REASON_REQUIRED") {
          setErroresServidor({ motivo: [e.message] });
          return;
        }
        if (e.status === 403) {
          notify({
            type: "error",
            title: "No tiene permiso para esta acción",
          });
          return;
        }
        notify({
          type: "error",
          title: "No fue posible completar la operación",
          description: e.message,
        });
        return;
      }
      notify({
        type: "error",
        title: "No fue posible completar la operación",
      });
    },
    [notify, recargar],
  );

  const cargosFiltrados = useMemo(() => {
    const items = consultaCargos.data?.items ?? [];
    const texto = busqueda.trim().toLowerCase();
    return items.filter((cargo) => {
      if (
        texto &&
        !cargo.codigo.toLowerCase().includes(texto) &&
        !cargo.denominacion.toLowerCase().includes(texto)
      ) {
        return false;
      }
      if (unidadId && cargo.unidad_id !== unidadId) return false;
      if (estado && cargo.estado !== estado) return false;
      return true;
    });
  }, [consultaCargos.data?.items, busqueda, unidadId, estado]);

  const opcionesUnidades = useMemo(() => {
    return (consultaEstructura.data?.unidades ?? [])
      .map((unidad) => ({
        id: unidad.id,
        etiqueta: `${unidad.codigo} — ${unidad.denominacion}`,
      }))
      .sort((a, b) => a.etiqueta.localeCompare(b.etiqueta));
  }, [consultaEstructura.data?.unidades]);

  const guardarCargo = async (cambios: CambiosCargo, motivo: string | null) => {
    const body = { ...cambios, ...(motivo ? { motivo } : {}) };
    try {
      const creado = await apiFetch<Cargo>(
        `/gobierno/estructuras/${ejercicio}/cargos`,
        {
          method: "POST",
          body,
        },
      );
      notify({ type: "success", title: "Cargo registrado" });
      setPanel({ tipo: "ninguno" });
      setErroresServidor({});
      await queryClient.invalidateQueries({ queryKey: [...CONSULTA_CARGOS] });
      navigate(`/gobierno/cargos/${ejercicio}/${creado.id}`);
    } catch (e) {
      manejarError(e);
    }
  };

  const exportarCsv = async () => {
    try {
      await descargarArchivo(
        `/gobierno/estructuras/${ejercicio}/cargos/exportar`,
        `cargos-${ejercicio}.csv`,
      );
      notify({ type: "success", title: "Cargos exportados" });
    } catch {
      notify({ type: "error", title: "No fue posible exportar" });
    }
  };

  const abrirPanel = (nuevoPanel: Panel) => {
    setErroresServidor({});
    setPanel(nuevoPanel);
  };

  if (!puedeVer) {
    return (
      <PageContent>
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para ver los cargos y competencias."
        />
      </PageContent>
    );
  }

  if (consultaCargos.isLoading || consultaEstructura.isLoading) {
    return (
      <PageContent>
        <LoadingState label="Cargando cargos y competencias…" />
      </PageContent>
    );
  }

  if (consultaCargos.isError) {
    const error = consultaCargos.error;
    if (
      error instanceof ApiError &&
      error.status === 403 &&
      error.code === "MODULE_NOT_ENTITLED"
    ) {
      return (
        <PageContent>
          <EmptyState
            title="Módulo no disponible"
            description="Su empresa no tiene contratado el módulo de Gobierno."
            action={<Link to="/gobierno/cargos">Volver a Cargos y competencias</Link>}
          />
        </PageContent>
      );
    }
    if (error instanceof ApiError && error.status === 403) {
      return (
        <PageContent>
          <EmptyState
            title="Sin acceso"
            description="No tiene permiso para ver los cargos y competencias."
          />
        </PageContent>
      );
    }
    if (
      error instanceof ApiError &&
      error.status === 404 &&
      error.code === "GOV_STRUCTURE_NOT_FOUND"
    ) {
      return (
        <PageContent>
          <EmptyState
            title={`No hay estructura para el ejercicio ${ejercicio}`}
            action={<Link to="/gobierno/estructura">Ir a Estructura organizativa</Link>}
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        <ErrorState
          message="No fue posible cargar los cargos."
          onRetry={() => void consultaCargos.refetch()}
        />
      </PageContent>
    );
  }

  if (consultaEstructura.isError) {
    return (
      <PageContent>
        <ErrorState
          message="No fue posible cargar la estructura."
          onRetry={() => void consultaEstructura.refetch()}
        />
      </PageContent>
    );
  }

  if (!consultaCargos.data || !estructura) {
    return (
      <PageContent>
        <ErrorState
          message="No fue posible cargar los cargos."
          onRetry={() => void consultaCargos.refetch()}
        />
      </PageContent>
    );
  }

  const estadoEstructura = consultaCargos.data.estructura.estado;
  const unidades = estructura.unidades;
  const cargos = consultaCargos.data.items;

  const crumbs = [
    { label: "Gobierno" },
    { label: "Cargos y competencias", to: "/gobierno/cargos" },
    { label: String(ejercicio) },
  ];

  const accionesCabecera = (
    <div className="flex flex-wrap items-center gap-2">
      {puedeVer && (
        <AsyncButton onClick={exportarCsv} variant="secondary">
          <Download className="mr-2 h-4 w-4" aria-hidden="true" />
          Exportar CSV
        </AsyncButton>
      )}
      {puedeEditar && (
        <Button
          variant="primary"
          onClick={() => abrirPanel({ tipo: "crear" })}
        >
          <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
          Agregar cargo
        </Button>
      )}
    </div>
  );

  const vigenciaDeCargo = (cargo: Cargo) => {
    const desde = formatearFechaDeNegocio(cargo.vigente_desde);
    if (!cargo.vigente_hasta) {
      return `desde ${desde}`;
    }
    return `${desde} – ${formatearFechaDeNegocio(cargo.vigente_hasta)}`;
  };



  return (
    <PageContent>
      <PageHeader
        crumbs={crumbs}
        title={`Cargos y competencias ${ejercicio}`}
        description="Qué puede hacer cada cargo y hasta qué monto, con su acto y su historial."
        actions={accionesCabecera}
      />

      {conflicto ? (
        <ConflictState
          message="Otra persona cambió los cargos mientras trabajaba. Se cargó la versión vigente."
          onReload={() => {
            setConflicto(false);
            setPanel({ tipo: "ninguno" });
          }}
        />
      ) : (
        <>
          {estadoEstructura === "BORRADOR" && (
            <p
              role="status"
              className="mb-4 rounded-md bg-surface-100 px-4 py-3 text-sm text-text-700"
            >
              La estructura de este ejercicio está en borrador: puede preparar
              cargos, pero solo se ponen en vigor cuando la estructura esté
              vigente.{" "}
              <Link
                to={`/gobierno/estructura/${ejercicio}`}
                className="font-medium text-brand-700 underline"
              >
                Ir a la estructura
              </Link>
            </p>
          )}
          {estadoEstructura === "CERRADA" && (
            <p
              role="status"
              className="mb-4 rounded-md bg-surface-100 px-4 py-3 text-sm text-text-700"
            >
              Ejercicio cerrado: los cargos son de solo lectura.
            </p>
          )}

          <section aria-labelledby="cargos-titulo" className="mb-8">
            <h2
              id="cargos-titulo"
              className="mb-4 text-lg font-semibold text-text-900"
            >
              Cargos
            </h2>

            <div className="mb-4 flex flex-wrap items-end gap-3">
              <FormField
                label="Buscar"
                htmlFor="busqueda-cargo"
                className="min-w-56 flex-1"
              >
                <TextInput
                  id="busqueda-cargo"
                  value={busqueda}
                  onChange={(e) => setBusqueda(e.target.value)}
                  placeholder="Código o denominación"
                />
              </FormField>
              <FormField
                label="Unidad"
                htmlFor="filtro-unidad"
                className="min-w-56"
              >
                <select
                  id="filtro-unidad"
                  className={CLASE_SELECT}
                  value={unidadId}
                  onChange={(e) => setUnidadId(e.target.value)}
                >
                  <option value="">Todas</option>
                  {opcionesUnidades.map((unidad) => (
                    <option key={unidad.id} value={unidad.id}>
                      {unidad.etiqueta}
                    </option>
                  ))}
                </select>
              </FormField>
              <FormField
                label="Estado"
                htmlFor="filtro-estado-cargo"
                className="min-w-40"
              >
                <select
                  id="filtro-estado-cargo"
                  className={CLASE_SELECT}
                  value={estado}
                  onChange={(e) => setEstado(e.target.value)}
                >
                  <option value="">Todos</option>
                  {Object.entries(ETIQUETA_ESTADO_CARGO).map(
                    ([valor, etiqueta]) => (
                      <option key={valor} value={valor}>
                        {etiqueta}
                      </option>
                    ),
                  )}
                </select>
              </FormField>
            </div>

            <div className="relative overflow-x-auto">
              <table className="w-full min-w-[760px] border-collapse text-sm">
                <caption className="sr-only">
                  Cargos del ejercicio {ejercicio}
                </caption>
                <thead>
                  <tr className="border-b border-border-default text-left text-text-600">
                    <th scope="col" className="px-3 py-2 font-medium">
                      Código
                    </th>
                    <th scope="col" className="px-3 py-2 font-medium">
                      Denominación
                    </th>
                    <th scope="col" className="px-3 py-2 font-medium">
                      Unidad
                    </th>
                    <th scope="col" className="px-3 py-2 font-medium">
                      Competencias
                    </th>
                    <th scope="col" className="px-3 py-2 font-medium">
                      Vigencia
                    </th>
                    <th scope="col" className="px-3 py-2 font-medium">
                      Estado
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {cargosFiltrados.length === 0 ? (
                    <tr>
                      <td
                        colSpan={6}
                        className="px-3 py-6 text-center text-text-600"
                      >
                        {cargos.length === 0
                          ? "Aún no hay cargos en este ejercicio."
                          : "Ningún cargo coincide con el filtro."}
                      </td>
                    </tr>
                  ) : (
                    cargosFiltrados.map((cargo) => (
                      <tr
                        key={cargo.id}
                        className="border-b border-border-subtle align-top"
                      >
                        <td className="px-3 py-2 font-mono text-text-900">
                          <Link
                            to={`/gobierno/cargos/${ejercicio}/${cargo.id}`}
                            className="font-medium text-brand-700 underline"
                            aria-label={`Abrir el cargo ${cargo.codigo}`}
                          >
                            {cargo.codigo}
                          </Link>
                        </td>
                        <td className="px-3 py-2 text-text-900">
                          {cargo.denominacion}
                        </td>
                        <td className="px-3 py-2 text-text-700">
                          {cargo.unidad_codigo} — {cargo.unidad_denominacion}
                        </td>
                        <td className="px-3 py-2 text-text-700">
                          <span>{cargo.competencias.length}</span>
                          {cargo.competencias.length > 0 && (
                            <ul className="mt-1 list-disc pl-4 text-xs text-text-600">
                              {cargo.competencias.map((competencia) => (
                                <li key={competencia.id}>
                                  {ETIQUETA_ACCION[competencia.accion]} ·{" "}
                                  {ETIQUETA_MATERIA[competencia.materia]}:{" "}
                                  {describirLimite(competencia)}
                                </li>
                              ))}
                            </ul>
                          )}
                        </td>
                        <td className="px-3 py-2 text-text-700">
                          {vigenciaDeCargo(cargo)}
                        </td>
                        <td className="px-3 py-2 text-text-700">
                          {ETIQUETA_ESTADO_CARGO[cargo.estado]}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {panel.tipo === "crear" && (
              <div className="mt-6">
                <CargoFormulario
                  key="crear-cargo"
                  modo="crear"
                  ejercicio={ejercicio}
                  unidades={unidades}
                  onGuardar={guardarCargo}
                  onCancelar={() => setPanel({ tipo: "ninguno" })}
                  erroresServidor={erroresServidor}
                />
              </div>
            )}
          </section>
        </>
      )}
    </PageContent>
  );
}
