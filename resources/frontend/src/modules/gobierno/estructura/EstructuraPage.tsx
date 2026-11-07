import { useMemo, useState } from "react";
import { Link, useParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus, Trash2, History, UserRoundX, Download } from "lucide-react";

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
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { ConflictState } from "@/components/ConflictState";
import { AdjuntosPanel } from "@/modules/documentos/AdjuntosPanel";
import { BloqueoDeCierre, detalleDeBloqueoDeCierre } from "@/modules/gobierno/cierres/BloqueoDeCierre";
import type { DetalleBloqueoCierre } from "@/modules/gobierno/api";
import { formatearFecha } from "@/i18n";
import { formatearFechaDeNegocio, hoyDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_ESTRUCTURAS,
  Estructura,
  Unidad,
  ETIQUETA_ESTADO_ESTRUCTURA,
  ETIQUETA_ESTADO_UNIDAD,
  ETIQUETA_TIPO_UNIDAD,
  ETIQUETA_FALTANTE_ESTRUCTURA,
} from "@/modules/gobierno/api";

import { UnidadFormulario, CambiosUnidad } from "./UnidadFormulario";
import { DesactivarUnidad } from "./DesactivarUnidad";
import { HistorialUnidad } from "./HistorialUnidad";

type Panel =
  | { tipo: "ninguno" }
  | { tipo: "crear"; superior: string | null }
  | { tipo: "editar"; unidad: Unidad }
  | { tipo: "desactivar"; unidad: Unidad }
  | { tipo: "historial"; unidad: Unidad };

type Confirmacion = null | "publicar" | "cerrar" | { eliminar: Unidad };

const CLASE_SELECT =
  "h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600";

function ordenarUnidades(unidades: Unidad[]): Unidad[] {
  const porSuperior = new Map<string | null, Unidad[]>();
  for (const unidad of unidades) {
    const clave = unidad.unidad_superior_id;
    const lista = porSuperior.get(clave) ?? [];
    lista.push(unidad);
    porSuperior.set(clave, lista);
  }
  for (const lista of porSuperior.values()) {
    lista.sort((a, b) => a.codigo.localeCompare(b.codigo));
  }
  const resultado: Unidad[] = [];
  const visitar = (superior: string | null, nivel: number) => {
    for (const unidad of porSuperior.get(superior) ?? []) {
      resultado.push({ ...unidad, nivel });
      visitar(unidad.id, nivel + 1);
    }
  };
  visitar(null, 0);
  return resultado;
}

export function EstructuraPage(): React.JSX.Element {
  const { ejercicio: ejercicioParam } = useParams();
  const ejercicio = Number(ejercicioParam);
  const { activeCompanyId } = useCompany();
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();

  const [panel, setPanel] = useState<Panel>({ tipo: "ninguno" });
  const [erroresServidor, setErroresServidor] = useState<Record<string, string[]>>({});
  const [confirmar, setConfirmar] = useState<Confirmacion>(null);
  const [conflicto, setConflicto] = useState(false);
  const [bloqueoCierre, setBloqueoCierre] = useState<DetalleBloqueoCierre | null>(null);
  const [busqueda, setBusqueda] = useState("");
  const [tipo, setTipo] = useState("");
  const [estado, setEstado] = useState("");

  const consulta = useQuery({
    queryKey: [...CONSULTA_ESTRUCTURAS, activeCompanyId, ejercicio],
    queryFn: () => apiFetch<Estructura>(`/gobierno/estructuras/${ejercicio}`),
    enabled: Boolean(activeCompanyId) && Number.isInteger(ejercicio),
    retry: false,
  });

  const recargar = () => {
    void queryClient.invalidateQueries({ queryKey: [...CONSULTA_ESTRUCTURAS] });
  };

  const estructura = consulta.data;
  const puedeEditar = tiene("gobierno_estructura:edit", "empresa") && estructura?.estado !== "CERRADA";
  const puedePublicar = tiene("gobierno_estructura:publish", "empresa");
  const puedeCerrar = tiene("gobierno_estructura:close", "empresa");
  const puedeVer = tiene("gobierno_estructura:view", "empresa");

  const unidadesOrdenadas = useMemo(() => {
    if (!estructura) return [];
    return ordenarUnidades(estructura.unidades);
  }, [estructura]);

  const unidadesFiltradas = useMemo(() => {
    const texto = busqueda.trim().toLowerCase();
    return unidadesOrdenadas.filter((unidad) => {
      if (texto && !unidad.codigo.toLowerCase().includes(texto) && !unidad.denominacion.toLowerCase().includes(texto)) {
        return false;
      }
      if (tipo && unidad.tipo !== tipo) return false;
      if (estado && unidad.estado !== estado) return false;
      return true;
    });
  }, [unidadesOrdenadas, busqueda, tipo, estado]);

  const manejarError = (e: unknown) => {
    if (e instanceof ApiError) {
      if (e.status === 409 && (e.code === "GOV_UNIT_STALE" || e.code === "GOV_STRUCTURE_STALE")) {
        setConflicto(true);
        recargar();
        return;
      }
      if (e.status === 422 && e.code === "VALIDATION_ERROR") {
        setErroresServidor(e.fieldErrors);
        return;
      }
      if (e.status === 409 && e.code === "GOV_UNIT_CODE_DUPLICATE") {
        setErroresServidor({ codigo: [e.message] });
        return;
      }
      if (e.status === 422 && (e.code === "GOV_UNIT_INVALID_PARENT" || e.code === "GOV_UNIT_HIERARCHY_CYCLE")) {
        setErroresServidor({ unidad_superior_id: [e.message] });
        return;
      }
      if (e.status === 422 && e.code === "GOV_UNIT_REASON_REQUIRED") {
        setErroresServidor({ motivo: [e.message] });
        return;
      }
      if (e.status === 422 && e.code === "GOV_STRUCTURE_INCOMPLETE") {
        const lista: unknown = e.details?.faltantes;
        const faltantes = Array.isArray(lista)
          ? lista.map((c) => ETIQUETA_FALTANTE_ESTRUCTURA[String(c)] ?? String(c)).join(", ")
          : "";
        notify({ type: "error", title: "No se puede poner en vigor", description: faltantes });
        return;
      }
      if (
        (e.status === 422 &&
          (e.code === "GOV_UNIT_FIELD_LOCKED" ||
            e.code === "GOV_UNIT_NO_CHANGES" ||
            e.code === "GOV_STRUCTURE_EXERCISE_NOT_ENDED")) ||
        (e.status === 409 &&
          (e.code === "GOV_UNIT_HAS_CHILDREN" ||
            e.code === "GOV_UNIT_HAS_ACTIVE_CHILDREN" ||
            e.code === "GOV_UNIT_INVALID_STATE" ||
            e.code === "GOV_STRUCTURE_INVALID_STATE" ||
            e.code === "GOV_STRUCTURE_CLOSED"))
      ) {
        notify({ type: "warning", title: e.message });
        recargar();
        return;
      }
      if (e.status === 403) {
        notify({ type: "error", title: "No tiene permiso para esta acción" });
        return;
      }
      notify({ type: "error", title: "No fue posible completar la operación", description: e.message });
      return;
    }
    notify({ type: "error", title: "No fue posible completar la operación" });
  };

  const guardarUnidad = async (cambios: CambiosUnidad, motivo: string | null) => {
    if (!estructura) return;
    const body = { ...cambios, ...(motivo ? { motivo } : {}) };
    try {
      if (panel.tipo === "crear") {
        await apiFetch<Unidad>(`/gobierno/estructuras/${ejercicio}/unidades`, { method: "POST", body });
        notify({ type: "success", title: "Unidad registrada" });
      } else if (panel.tipo === "editar") {
        await apiFetch<Unidad>(`/gobierno/estructuras/${ejercicio}/unidades/${panel.unidad.id}`, {
          method: "PATCH",
          body,
          ifMatch: String(panel.unidad.version),
        });
        notify({ type: "success", title: "Unidad actualizada" });
      }
      setPanel({ tipo: "ninguno" });
      setErroresServidor({});
      recargar();
    } catch (e) {
      manejarError(e);
    }
  };

  const desactivarUnidad = async (fecha: string, motivo: string) => {
    if (panel.tipo !== "desactivar") return;
    try {
      await apiFetch<Unidad>(`/gobierno/estructuras/${ejercicio}/unidades/${panel.unidad.id}/desactivar`, {
        method: "POST",
        body: { fecha, motivo },
        ifMatch: String(panel.unidad.version),
      });
      notify({ type: "success", title: "Unidad desactivada" });
      setPanel({ tipo: "ninguno" });
      setErroresServidor({});
      recargar();
    } catch (e) {
      manejarError(e);
    }
  };

  const eliminarUnidad = async () => {
    if (!confirmar || confirmar === "publicar" || confirmar === "cerrar") return;
    const unidad = confirmar.eliminar;
    try {
      await apiFetch<void>(`/gobierno/estructuras/${ejercicio}/unidades/${unidad.id}`, {
        method: "DELETE",
        ifMatch: String(unidad.version),
      });
      notify({ type: "success", title: "Unidad eliminada" });
      setPanel({ tipo: "ninguno" });
      setErroresServidor({});
      recargar();
    } catch (e) {
      manejarError(e);
    } finally {
      setConfirmar(null);
    }
  };

  const publicar = async () => {
    if (!estructura) return;
    try {
      await apiFetch<Estructura>(`/gobierno/estructuras/${ejercicio}/publicar`, {
        method: "POST",
        ifMatch: String(estructura.version),
      });
      notify({ type: "success", title: "Estructura en vigor" });
      setPanel({ tipo: "ninguno" });
      setErroresServidor({});
      recargar();
    } catch (e) {
      manejarError(e);
    } finally {
      setConfirmar(null);
    }
  };

  const cerrar = async () => {
    if (!estructura) return;
    try {
      await apiFetch<Estructura>(`/gobierno/estructuras/${ejercicio}/cerrar`, {
        method: "POST",
        ifMatch: String(estructura.version),
      });
      notify({ type: "success", title: "Ejercicio cerrado" });
      setBloqueoCierre(null);
      setPanel({ tipo: "ninguno" });
      setErroresServidor({});
      recargar();
    } catch (e) {
      const detalleBloqueo = detalleDeBloqueoDeCierre(e);
      if (detalleBloqueo) {
        setBloqueoCierre(detalleBloqueo);
      } else {
        manejarError(e);
      }
    } finally {
      setConfirmar(null);
    }
  };

  const exportarCsv = async () => {
    try {
      await descargarArchivo(`/gobierno/estructuras/${ejercicio}/exportar`, `estructura-${ejercicio}.csv`);
      notify({ type: "success", title: "Estructura exportada" });
    } catch {
      notify({ type: "error", title: "No fue posible exportar" });
    }
  };

  const abrirPanel = (nuevoPanel: Panel) => {
    setErroresServidor({});
    setPanel(nuevoPanel);
  };

  if (consulta.isLoading) {
    return (
      <PageContent>
        <LoadingState label="Cargando estructura organizativa…" />
      </PageContent>
    );
  }

  if (consulta.isError) {
    const error = consulta.error;
    if (error instanceof ApiError && error.status === 403 && error.code === "MODULE_NOT_ENTITLED") {
      return (
        <PageContent>
          <EmptyState
            title="Módulo no disponible"
            description="Su empresa no tiene contratado el módulo de Gobierno."
            action={<Link to="/gobierno/estructura">Volver a Estructura organizativa</Link>}
          />
        </PageContent>
      );
    }
    if (error instanceof ApiError && error.status === 403) {
      return (
        <PageContent>
          <EmptyState title="Sin acceso" description="No tiene permiso para ver esta estructura." />
        </PageContent>
      );
    }
    if (error instanceof ApiError && error.status === 404 && error.code === "GOV_STRUCTURE_NOT_FOUND") {
      return (
        <PageContent>
          <EmptyState
            title={`No hay estructura para el ejercicio ${ejercicio}`}
            action={<Link to="/gobierno/estructura">Volver a Estructura organizativa</Link>}
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        <ErrorState message="No fue posible cargar la estructura." onRetry={() => void consulta.refetch()} />
      </PageContent>
    );
  }

  if (!estructura) {
    return (
      <PageContent>
        <ErrorState message="No fue posible cargar la estructura." onRetry={() => void consulta.refetch()} />
      </PageContent>
    );
  }

  const crumbs = [
    { label: "Gobierno" },
    { label: "Estructura organizativa", to: "/gobierno/estructura" },
    { label: String(ejercicio) },
  ];

  const descripcionCabecera = `Versión ${estructura.version}${
    estructura.estado === "VIGENTE" && estructura.publicada_en
      ? ` · En vigor desde ${formatearFecha(estructura.publicada_en)}`
      : estructura.estado === "CERRADA" && estructura.cerrada_en
        ? ` · Cerrada el ${formatearFecha(estructura.cerrada_en)}`
        : ""
  }`;

  const faltantes = estructura.faltantes_para_publicar ?? [];
  const hayFaltantes = faltantes.length > 0;
  const cierreDeshabilitado = ejercicio >= Number(hoyDeNegocio().slice(0, 4));

  const accionesCabecera = (
    <div className="flex flex-wrap items-center gap-2">
      {puedeVer && (
        <AsyncButton onClick={exportarCsv} variant="secondary">
          <Download className="mr-2 h-4 w-4" aria-hidden="true" />
          Exportar CSV
        </AsyncButton>
      )}
      {estructura.estado === "BORRADOR" && puedePublicar && (
        <Button
          variant="primary"
          disabled={hayFaltantes}
          aria-describedby="requisitos-publicar"
          onClick={() => setConfirmar("publicar")}
        >
          Poner en vigor
        </Button>
      )}
      {estructura.estado === "VIGENTE" && puedeCerrar && (
        <Button
          variant="secondary"
          disabled={cierreDeshabilitado}
          aria-describedby="nota-cierre"
          onClick={() => setConfirmar("cerrar")}
        >
          Cerrar ejercicio
        </Button>
      )}
    </div>
  );

  return (
    <PageContent>
      <PageHeader
        crumbs={crumbs}
        title={`Estructura organizativa ${ejercicio}`}
        description={descripcionCabecera}
        status={
          <span className="inline-flex items-center rounded-full bg-surface-100 px-3 py-1 text-sm font-medium text-text-700">
            {ETIQUETA_ESTADO_ESTRUCTURA[estructura.estado]}
          </span>
        }
        actions={accionesCabecera}
      />
      {bloqueoCierre ? (
        <BloqueoDeCierre detalle={bloqueoCierre} onCerrar={() => setBloqueoCierre(null)} />
      ) : null}

      {estructura.estado === "VIGENTE" && puedeCerrar && cierreDeshabilitado && (
        <p id="nota-cierre" className="mb-4 text-sm text-text-600">
          El ejercicio {ejercicio} se cierra a partir del 1 de enero de {ejercicio + 1}.
        </p>
      )}

      {conflicto ? (
        <ConflictState
          message="Otra persona cambió la estructura mientras trabajaba. Se cargó la versión vigente."
          onReload={() => {
            setConflicto(false);
            setPanel({ tipo: "ninguno" });
          }}
        />
      ) : (
        <>
          {estructura.estado === "CERRADA" && (
            <p role="status" className="mb-4 rounded-md bg-surface-100 px-4 py-3 text-sm text-text-700">
              Estructura de un ejercicio cerrado: solo lectura.
            </p>
          )}

          {estructura.estado === "BORRADOR" && (
            <section id="requisitos-publicar" aria-labelledby="requisitos-publicar-titulo" className="mb-8">
              <h2 id="requisitos-publicar-titulo" className="mb-2 text-lg font-semibold text-text-900">
                Requisitos para poner en vigor
              </h2>
              {hayFaltantes ? (
                <>
                  <p className="text-sm text-text-700">Para poner en vigor falta:</p>
                  <ul className="mt-2 list-disc pl-6 text-sm text-text-700">
                    {faltantes.map((c) => (
                      <li key={c}>{ETIQUETA_FALTANTE_ESTRUCTURA[c] ?? c}</li>
                    ))}
                  </ul>
                </>
              ) : (
                <p role="status" className="text-sm text-text-700">
                  La estructura está completa y puede ponerse en vigor.
                </p>
              )}
            </section>
          )}

          <section aria-labelledby="unidades-titulo" className="mb-8">
            <h2 id="unidades-titulo" className="mb-4 text-lg font-semibold text-text-900">
              Unidades
            </h2>

            <div className="mb-4 flex flex-wrap items-end gap-3">
              <FormField label="Buscar" htmlFor="busqueda-unidad" className="min-w-56 flex-1">
                <TextInput
                  id="busqueda-unidad"
                  value={busqueda}
                  onChange={(e) => setBusqueda(e.target.value)}
                  placeholder="Código o denominación"
                />
              </FormField>
              <FormField label="Tipo" htmlFor="filtro-tipo" className="min-w-44">
                <select id="filtro-tipo" className={CLASE_SELECT} value={tipo} onChange={(e) => setTipo(e.target.value)}>
                  <option value="">Todos</option>
                  {Object.entries(ETIQUETA_TIPO_UNIDAD).map(([valor, etiqueta]) => (
                    <option key={valor} value={valor}>
                      {etiqueta}
                    </option>
                  ))}
                </select>
              </FormField>
              <FormField label="Estado" htmlFor="filtro-estado" className="min-w-40">
                <select id="filtro-estado" className={CLASE_SELECT} value={estado} onChange={(e) => setEstado(e.target.value)}>
                  <option value="">Todas</option>
                  {Object.entries(ETIQUETA_ESTADO_UNIDAD).map(([valor, etiqueta]) => (
                    <option key={valor} value={valor}>
                      {etiqueta}
                    </option>
                  ))}
                </select>
              </FormField>
              {puedeEditar && (
                <Button variant="primary" onClick={() => abrirPanel({ tipo: "crear", superior: null })}>
                  <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
                  Agregar unidad
                </Button>
              )}
            </div>

            <div className="relative overflow-x-auto">
              <table className="w-full min-w-[720px] border-collapse text-sm">
                <caption className="sr-only">Unidades de la estructura {ejercicio}</caption>
                <thead>
                  <tr className="border-b border-border-default text-left text-text-600">
                    <th scope="col" className="px-3 py-2 font-medium">
                      Código
                    </th>
                    <th scope="col" className="px-3 py-2 font-medium">
                      Denominación
                    </th>
                    <th scope="col" className="px-3 py-2 font-medium">
                      Tipo
                    </th>
                    <th scope="col" className="px-3 py-2 font-medium">
                      Depende de
                    </th>
                    <th scope="col" className="px-3 py-2 font-medium">
                      Vigencia
                    </th>
                    <th scope="col" className="px-3 py-2 font-medium">
                      Estado
                    </th>
                    <th scope="col" className="px-3 py-2 font-medium">
                      Acciones
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {unidadesFiltradas.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-3 py-6 text-center text-text-600">
                        {estructura.unidades.length === 0 ? "Aún no hay unidades" : "Ninguna unidad coincide con el filtro"}
                      </td>
                    </tr>
                  ) : (
                    unidadesFiltradas.map((unidad) => {
                      const superior = estructura.unidades.find((u) => u.id === unidad.unidad_superior_id);
                      const vigencia = `${formatearFechaDeNegocio(unidad.vigente_desde)} – ${
                        unidad.vigente_hasta ? formatearFechaDeNegocio(unidad.vigente_hasta) : "—"
                      }`;
                      return (
                        <tr key={unidad.id} className="border-b border-border-subtle align-top">
                          <td className="px-3 py-2 font-mono text-text-900">{unidad.codigo}</td>
                          <td className="px-3 py-2 text-text-900" style={{ paddingLeft: `${unidad.nivel * 1.25}rem` }}>
                            <span className="sr-only">Nivel {unidad.nivel + 1}. </span>
                            {unidad.denominacion}
                          </td>
                          <td className="px-3 py-2 text-text-700">{ETIQUETA_TIPO_UNIDAD[unidad.tipo]}</td>
                          <td className="px-3 py-2 text-text-700">{superior ? superior.codigo : "Ente"}</td>
                          <td className="px-3 py-2 text-text-700">{vigencia}</td>
                          <td className="px-3 py-2 text-text-700">{ETIQUETA_ESTADO_UNIDAD[unidad.estado]}</td>
                          <td className="px-3 py-2">
                            <div className="flex flex-wrap gap-1">
                              {puedeEditar && unidad.estado === "ACTIVA" && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  aria-label={`Editar ${unidad.codigo}`}
                                  onClick={() => abrirPanel({ tipo: "editar", unidad })}
                                >
                                  <Pencil className="h-4 w-4" aria-hidden="true" />
                                  Editar
                                </Button>
                              )}
                              {puedeEditar && unidad.estado === "ACTIVA" && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  aria-label={`Agregar subordinada a ${unidad.codigo}`}
                                  onClick={() => abrirPanel({ tipo: "crear", superior: unidad.id })}
                                >
                                  <Plus className="h-4 w-4" aria-hidden="true" />
                                  Agregar subordinada
                                </Button>
                              )}
                              {puedeEditar && estructura.estado === "VIGENTE" && unidad.estado === "ACTIVA" && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  aria-label={`Desactivar ${unidad.codigo}`}
                                  onClick={() => abrirPanel({ tipo: "desactivar", unidad })}
                                >
                                  <UserRoundX className="h-4 w-4" aria-hidden="true" />
                                  Desactivar
                                </Button>
                              )}
                              {puedeEditar && estructura.estado === "BORRADOR" && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  aria-label={`Eliminar ${unidad.codigo}`}
                                  onClick={() => setConfirmar({ eliminar: unidad })}
                                >
                                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                                  Eliminar
                                </Button>
                              )}
                              <Button
                                variant="ghost"
                                size="sm"
                                aria-label={`Historial de ${unidad.codigo}`}
                                onClick={() => abrirPanel({ tipo: "historial", unidad })}
                              >
                                <History className="h-4 w-4" aria-hidden="true" />
                                Historial
                              </Button>
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>

            {panel.tipo === "crear" && (
              <div className="mt-6">
                <UnidadFormulario
                  key={`crear-${panel.superior ?? "raiz"}`}
                  modo="crear"
                  estadoEstructura={estructura.estado}
                  ejercicio={ejercicio}
                  unidades={estructura.unidades}
                  superiorInicial={panel.superior}
                  onGuardar={guardarUnidad}
                  onCancelar={() => setPanel({ tipo: "ninguno" })}
                  erroresServidor={erroresServidor}
                />
              </div>
            )}
            {panel.tipo === "editar" && (
              <div className="mt-6">
                <UnidadFormulario
                  key={`editar-${panel.unidad.id}`}
                  modo="editar"
                  estadoEstructura={estructura.estado}
                  ejercicio={ejercicio}
                  unidades={estructura.unidades}
                  unidad={panel.unidad}
                  onGuardar={guardarUnidad}
                  onCancelar={() => setPanel({ tipo: "ninguno" })}
                  erroresServidor={erroresServidor}
                />
              </div>
            )}
            {panel.tipo === "desactivar" && (
              <div className="mt-6">
                <DesactivarUnidad
                  key={`desactivar-${panel.unidad.id}`}
                  unidad={panel.unidad}
                  ejercicio={ejercicio}
                  onConfirmar={desactivarUnidad}
                  onCancelar={() => setPanel({ tipo: "ninguno" })}
                  erroresServidor={erroresServidor}
                />
              </div>
            )}
            {panel.tipo === "historial" && (
              <div className="mt-6">
                <HistorialUnidad
                  key={`historial-${panel.unidad.id}`}
                  ejercicio={ejercicio}
                  unidad={panel.unidad}
                  onCerrar={() => setPanel({ tipo: "ninguno" })}
                />
              </div>
            )}
          </section>

          <section aria-labelledby="acto-titulo">
            <h2 id="acto-titulo" className="mb-4 text-lg font-semibold text-text-900">
              Acto que aprueba la estructura
            </h2>
            <AdjuntosPanel
              resourceType="GovernmentStructure"
              resourceId={estructura.id}
              title="Acto que aprueba la estructura"
              onChange={() => void recargar()}
            />
            {estructura.estado === "BORRADOR" && !estructura.documento_vinculado && (
              <p className="mt-2 text-sm text-text-600">
                Adjunte la resolución o el reglamento interno que aprueba la estructura para ponerla en vigor.
              </p>
            )}
          </section>
        </>
      )}

      <ConfirmationDialog
        open={confirmar === "publicar"}
        title={`¿Poner en vigor la estructura de ${ejercicio}?`}
        description="Desde ese momento cada cambio exigirá un motivo y quedará en el historial; las unidades ya no se eliminan, se desactivan con fecha."
        confirmLabel="Poner en vigor"
        onConfirm={publicar}
        onCancel={() => setConfirmar(null)}
      />
      <ConfirmationDialog
        open={confirmar === "cerrar"}
        title={`¿Cerrar la estructura de ${ejercicio}?`}
        description="Quedará de solo lectura: ningún cambio posterior reescribe el ejercicio cerrado."
        confirmLabel="Cerrar ejercicio"
        onConfirm={cerrar}
        onCancel={() => setConfirmar(null)}
      />
      <ConfirmationDialog
        open={confirmar !== null && confirmar !== "publicar" && confirmar !== "cerrar"}
        title={`¿Eliminar la unidad ${confirmar !== null && confirmar !== "publicar" && confirmar !== "cerrar" ? confirmar.eliminar.codigo : ""}?`}
        description="Solo se eliminan unidades de un borrador."
        confirmLabel="Eliminar"
        danger
        onConfirm={eliminarUnidad}
        onCancel={() => setConfirmar(null)}
      />
    </PageContent>
  );
}
