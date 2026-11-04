import { useState } from "react";
import { Link, useParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { formatearFecha } from "@/i18n";
import { formatearFechaDeNegocio, hoyDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_SOD,
  ETIQUETAS_ESTADO_REGLA_SOD,
  ETIQUETAS_HISTORIA_SOD,
  ETIQUETAS_PROCESO_SOD,
  flechaSod,
  type ReglaSodCambios,
  type ReglaSodDetalle,
} from "@/modules/gobierno/api";

type PanelActivo = "editar" | "cerrar" | null;

export function ReglaSodPage() {
  const { reglaId } = useParams();
  const { activeCompanyId } = useCompany();
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();

  const claveDetalle = [...CONSULTA_SOD, activeCompanyId, "regla", reglaId];

  const consultaDetalle = useQuery({
    queryKey: claveDetalle,
    queryFn: () => apiFetch<ReglaSodDetalle>(`/gobierno/sod/reglas/${reglaId}`),
    enabled: Boolean(activeCompanyId && reglaId),
    retry: false,
  });

  const puedeGestionar = tiene("gobierno_sod:manage", "empresa");
  const puedeActivar = tiene("gobierno_sod:activate", "empresa");

  const [panel, setPanel] = useState<PanelActivo>(null);
  const [enviando, setEnviando] = useState(false);

  const [nombre, setNombre] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [vigenteDesde, setVigenteDesde] = useState("");
  const [vigenteHasta, setVigenteHasta] = useState("");

  const [motivoCierre, setMotivoCierre] = useState("");
  const [erroresServidor, setErroresServidor] = useState<Record<string, string[]>>({});
  const [alertaCambio, setAlertaCambio] = useState<string | null>(null);

  const recargar = () => {
    void queryClient.invalidateQueries({ queryKey: [...CONSULTA_SOD] });
  };

  const manejarError = (e: unknown) => {
    if (e instanceof ApiError) {
      if (e.status === 409 && e.code === "GOV_SOD_RULE_STALE") {
        setAlertaCambio(
          "La regla cambió desde que la abrió. Se recargaron los datos; revise y vuelva a intentarlo.",
        );
        recargar();
        return;
      }
      if (e.status === 409 && e.code === "GOV_SOD_RULE_DUPLICATE") {
        setAlertaCambio(
          "Ya hay una regla vigente con esas dos acciones en este proceso. Cierre la otra antes de activar esta.",
        );
        return;
      }
      if (e.status === 409 && e.code === "GOV_SOD_RULE_INVALID_STATE") {
        notify({ type: "warning", title: e.message });
        recargar();
        return;
      }
      if (e.status === 422 && e.code === "VALIDATION_ERROR") {
        setErroresServidor(e.fieldErrors);
        const errorGeneral = e.fieldErrors["_"]?.[0];
        if (errorGeneral) {
          setAlertaCambio(errorGeneral);
        }
        return;
      }
      if (e.status === 422) {
        setAlertaCambio(e.message);
        return;
      }
      if (e.status === 403) {
        notify({ type: "error", title: "No tiene permiso para esta acción" });
        return;
      }
      notify({ type: "error", title: "No fue posible completar la operación" });
      return;
    }
    notify({ type: "error", title: "No fue posible completar la operación" });
  };

  const escribirDetalle = async (
    ruta: string,
    method: "PATCH" | "POST",
    body: Record<string, unknown>,
  ) => {
    try {
      const nuevoDetalle = await apiFetch<ReglaSodDetalle>(ruta, {
        method,
        body,
        ifMatch: String(consultaDetalle.data?.version),
      });
      queryClient.setQueryData(claveDetalle, nuevoDetalle);
      void queryClient.invalidateQueries({ queryKey: [...CONSULTA_SOD] });
      setErroresServidor({});
      setAlertaCambio(null);
      return nuevoDetalle;
    } catch (e) {
      manejarError(e);
      throw e;
    }
  };

  const cabeceraSinDetalle = (
    <PageHeader
      crumbs={[{ label: "Gobierno" }, { label: "Segregación de funciones", to: "/gobierno/sod" }]}
      title="Regla de segregación de funciones"
    />
  );

  if (consultaDetalle.isLoading) {
    return (
      <PageContent>
        {cabeceraSinDetalle}
        <LoadingState label="Cargando regla…" />
      </PageContent>
    );
  }

  if (consultaDetalle.isError) {
    const error = consultaDetalle.error;
    if (error instanceof ApiError && error.status === 403 && error.code === "MODULE_NOT_ENTITLED") {
      return (
        <PageContent>
          {cabeceraSinDetalle}
          <EmptyState
            title="Módulo no habilitado"
            description="Su empresa no tiene contratado el módulo de Gobierno."
            action={<Link to="/gobierno/sod">Volver a Segregación de funciones</Link>}
          />
        </PageContent>
      );
    }
    if (error instanceof ApiError && error.status === 403) {
      return (
        <PageContent>
          {cabeceraSinDetalle}
          <EmptyState title="Sin acceso" description="No tiene permiso para ver esta regla." />
        </PageContent>
      );
    }
    if (error instanceof ApiError && error.status === 404 && error.code === "GOV_SOD_RULE_NOT_FOUND") {
      return (
        <PageContent>
          {cabeceraSinDetalle}
          <EmptyState
            title="Regla no encontrada"
            description="La regla no existe en este ente."
            action={<Link to="/gobierno/sod">Volver a Segregación de funciones</Link>}
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        {cabeceraSinDetalle}
        <ErrorState message="No fue posible cargar la regla." onRetry={() => void consultaDetalle.refetch()} />
      </PageContent>
    );
  }

  const detalle = consultaDetalle.data;
  if (!detalle) {
    return (
      <PageContent>
        {cabeceraSinDetalle}
        <ErrorState message="No fue posible cargar la regla." onRetry={() => void consultaDetalle.refetch()} />
      </PageContent>
    );
  }

  const estadoEtiqueta = ETIQUETAS_ESTADO_REGLA_SOD[detalle.estado] ?? detalle.estado;
  const etiquetaVigor =
    detalle.en_vigor
      ? " · en vigor"
      : detalle.estado === "VIGENTE"
        ? " · aún no en vigor"
        : "";

  const abrirPanelEdicion = () => {
    setErroresServidor({});
    setAlertaCambio(null);
    setNombre(detalle.nombre);
    setDescripcion(detalle.descripcion);
    setVigenteDesde(detalle.vigente_desde ?? "");
    setVigenteHasta(detalle.vigente_hasta ?? "");
    setPanel("editar");
  };

  const cerrarPanel = () => {
    setPanel(null);
    setErroresServidor({});
    setAlertaCambio(null);
    setMotivoCierre("");
  };

  const camposCambiados = (): ReglaSodCambios | null => {
    const cambios: ReglaSodCambios = {};
    if (nombre !== detalle.nombre) cambios.nombre = nombre;
    if (descripcion !== detalle.descripcion) cambios.descripcion = descripcion;

    if (vigenteDesde !== "" && vigenteDesde !== (detalle.vigente_desde ?? "")) {
      cambios.vigente_desde = vigenteDesde;
    }

    const hastaNuevo = vigenteHasta.trim() === "" ? null : vigenteHasta;
    if (hastaNuevo !== (detalle.vigente_hasta ?? null)) cambios.vigente_hasta = hastaNuevo;

    return Object.keys(cambios).length > 0 ? cambios : null;
  };

  const guardarEdicion = async () => {
    if (enviando) return;
    const cambios = camposCambiados();
    if (!cambios) {
      setAlertaCambio("No hay cambios que guardar.");
      return;
    }
    setEnviando(true);
    try {
      const nuevoDetalle = await escribirDetalle(`/gobierno/sod/reglas/${detalle.id}`, "PATCH", {
        ...cambios,
      });
      setNombre(nuevoDetalle.nombre);
      setDescripcion(nuevoDetalle.descripcion);
      setVigenteDesde(nuevoDetalle.vigente_desde ?? "");
      setVigenteHasta(nuevoDetalle.vigente_hasta ?? "");
      cerrarPanel();
      notify({ type: "success", title: "Regla actualizada" });
    } catch {
      // el error ya fue manejado
    } finally {
      setEnviando(false);
    }
  };

  const activarRegla = async () => {
    if (enviando) return;
    setEnviando(true);
    try {
      await escribirDetalle(`/gobierno/sod/reglas/${detalle.id}/activar`, "POST", {});
      cerrarPanel();
      notify({ type: "success", title: "Regla activada" });
    } catch {
      // el error ya fue manejado
    } finally {
      setEnviando(false);
    }
  };

  const cerrarRegla = async () => {
    if (enviando) return;
    setEnviando(true);
    try {
      await escribirDetalle(`/gobierno/sod/reglas/${detalle.id}/cerrar`, "POST", { motivo: motivoCierre });
      cerrarPanel();
      notify({ type: "success", title: "Regla cerrada" });
    } catch {
      // el error ya fue manejado
    } finally {
      setEnviando(false);
    }
  };

  const esMotivoValido = motivoCierre.trim().length >= 10 && motivoCierre.length <= 500;

  const panelRender = panel === "editar" ? (
    <section aria-labelledby="editar-sod-titulo" className="mb-8 rounded-lg border border-border-subtle p-4">
      <h2 id="editar-sod-titulo" className="mb-4 text-lg font-semibold text-text-900">
        Editar borrador
      </h2>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void guardarEdicion();
        }}
      >
        <FormField label="Nombre" htmlFor="sod-editar-nombre" error={erroresServidor.nombre?.[0]}>
          <TextInput
            id="sod-editar-nombre"
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            required
          />
        </FormField>
        <div className="mt-4">
          <FormField label="Razón" htmlFor="sod-editar-descripcion" error={erroresServidor.descripcion?.[0]}>
            <textarea
              id="sod-editar-descripcion"
              className="min-h-24 w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              value={descripcion}
              onChange={(e) => setDescripcion(e.target.value)}
            />
          </FormField>
        </div>
        <div className="mt-4">
          <FormField
            label="Vigente desde"
            htmlFor="sod-editar-desde"
            error={erroresServidor.vigente_desde?.[0]}
          >
            <TextInput
              id="sod-editar-desde"
              type="date"
              min={hoyDeNegocio()}
              value={vigenteDesde}
              onChange={(e) => setVigenteDesde(e.target.value)}
              required
            />
          </FormField>
        </div>
        <div className="mt-4">
          <FormField label="Vigente hasta" htmlFor="sod-editar-hasta" error={erroresServidor.vigente_hasta?.[0]}>
            <TextInput
              id="sod-editar-hasta"
              type="date"
              value={vigenteHasta}
              onChange={(e) => setVigenteHasta(e.target.value)}
            />
          </FormField>
        </div>
        <div className="mt-4 flex gap-2">
          <Button type="button" variant="primary" disabled={enviando} onClick={() => void guardarEdicion()}>
            Guardar
          </Button>
          <Button type="button" variant="secondary" onClick={cerrarPanel}>
            Cancelar
          </Button>
        </div>
      </form>
    </section>
  ) : panel === "cerrar" ? (
    <section aria-labelledby="cerrar-sod-titulo" className="mb-8 rounded-lg border border-border-subtle p-4">
      <h2 id="cerrar-sod-titulo" className="mb-4 text-lg font-semibold text-text-900">
        Cerrar regla
      </h2>
      <p className="mb-4 text-text-700">
        Una regla cerrada deja de aplicarse y no se puede reabrir; para cambiarla, registre otra.
      </p>
      <FormField
        label="Motivo"
        htmlFor="sod-cerrar-motivo"
        required
        error={erroresServidor.motivo?.[0]}
      >
        <textarea
          id="sod-cerrar-motivo"
          className="min-h-24 w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
          minLength={10}
          maxLength={500}
          value={motivoCierre}
          onChange={(e) => setMotivoCierre(e.target.value)}
        />
        {!esMotivoValido && motivoCierre.length > 0 ? (
          <p className="mt-1 text-sm text-danger-600">El motivo debe tener entre 10 y 500 caracteres.</p>
        ) : null}
      </FormField>
      <div className="mt-4 flex gap-2">
        <AsyncButton
          variant="primary"
          disabled={!esMotivoValido || enviando}
          onClick={cerrarRegla}
        >
          Confirmar cierre
        </AsyncButton>
        <Button type="button" variant="secondary" onClick={cerrarPanel}>
          Cancelar
        </Button>
      </div>
    </section>
  ) : null;

  const alertaRender = alertaCambio ? (
    <div role="alert" className="mb-4 rounded-md border border-error-300 bg-error-50 p-3 text-error-800">
      {alertaCambio}
    </div>
  ) : null;

  return (
    <PageContent>
      <PageHeader
        crumbs={[{ label: "Gobierno" }, { label: "Segregación de funciones", to: "/gobierno/sod" }]}
        title={`Regla ${detalle.codigo}`}
        description={detalle.nombre}
      />

      <p className="mb-6 text-sm text-text-700">
        {estadoEtiqueta}
        {etiquetaVigor}
      </p>

      {alertaRender}

      <section aria-labelledby="datos-regla-titulo" className="mb-8">
        <h2 id="datos-regla-titulo" className="mb-4 text-lg font-semibold text-text-900">
          Datos de la regla
        </h2>
        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <dt className="text-sm font-medium text-text-700">Proceso</dt>
            <dd className="mt-1 text-text-900">{ETIQUETAS_PROCESO_SOD[detalle.proceso] ?? detalle.proceso}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Incompatibilidad</dt>
            <dd className="mt-1 text-text-900">
              {detalle.accion_a_etiqueta} {flechaSod(detalle.bidireccional)} {detalle.accion_b_etiqueta}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">En ambos sentidos</dt>
            <dd className="mt-1 text-text-900">{detalle.bidireccional ? "Sí" : "No"}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Alcance</dt>
            <dd className="mt-1 text-text-900">Sobre el mismo acto o hallazgo</dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-sm font-medium text-text-700">Razón</dt>
            <dd className="mt-1 text-text-900">{detalle.descripcion}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Vigencia</dt>
            <dd className="mt-1 text-text-900">
              {detalle.vigente_desde ? formatearFechaDeNegocio(detalle.vigente_desde) : "—"}
              {" hasta "}
              {detalle.vigente_hasta ? formatearFechaDeNegocio(detalle.vigente_hasta) : "sin fecha de fin"}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Registrada</dt>
            <dd className="mt-1 text-text-900">
              {detalle.creada_por} · {formatearFecha(detalle.creada_en)}
            </dd>
          </div>
          {detalle.activada_en ? (
            <div>
              <dt className="text-sm font-medium text-text-700">Activada</dt>
              <dd className="mt-1 text-text-900">{formatearFecha(detalle.activada_en)}</dd>
            </div>
          ) : null}
          {detalle.cerrada_en ? (
            <div>
              <dt className="text-sm font-medium text-text-700">Cerrada</dt>
              <dd className="mt-1 text-text-900">
                {formatearFecha(detalle.cerrada_en)}
                {detalle.motivo_cierre ? ` · ${detalle.motivo_cierre}` : ""}
              </dd>
            </div>
          ) : null}
        </dl>
      </section>

      <div className="mb-8 flex flex-wrap items-center gap-2">
        {detalle.estado === "BORRADOR" && puedeGestionar ? (
          <Button variant="secondary" onClick={abrirPanelEdicion}>
            Editar borrador
          </Button>
        ) : null}
        {detalle.estado === "BORRADOR" && puedeActivar ? (
          <AsyncButton variant="primary" disabled={enviando} onClick={activarRegla}>
            Activar regla
          </AsyncButton>
        ) : null}
        {detalle.estado === "VIGENTE" && puedeActivar ? (
          <Button variant="secondary" onClick={() => setPanel("cerrar")}>
            Cerrar regla
          </Button>
        ) : null}
        <Link
          to={`/gobierno/sod/conflictos?regla_id=${detalle.id}`}
          className="font-medium text-brand-700 underline"
        >
          Ver conflictos de esta regla ({detalle.conflictos})
        </Link>
      </div>

      {panelRender}

      <section aria-labelledby="historia-regla-titulo">
        <h2 id="historia-regla-titulo" className="mb-4 text-lg font-semibold text-text-900">
          Historia
        </h2>
        <div className="relative overflow-x-auto" tabIndex={0} role="region" aria-label="Tabla de historia de la regla">
          <table className="w-full border-collapse text-left">
            <caption className="sr-only">Historia de la regla</caption>
            <thead>
              <tr className="border-b border-border-subtle">
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">Fecha</th>
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">Cambio</th>
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">Usuario</th>
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">Detalle</th>
              </tr>
            </thead>
            <tbody>
              {detalle.historia.map((h, indice) => {
                const campos = Array.isArray(h.detalle?.campos)
                  ? (h.detalle?.campos as unknown[]).map(String)
                  : null;
                const motivoHistoria =
                  typeof h.detalle?.motivo === "string" ? h.detalle?.motivo : null;
                const detalleTexto = campos
                  ? `Campos: ${campos.join(", ")}`
                  : motivoHistoria
                    ? motivoHistoria
                    : "—";
                return (
                  <tr key={`${h.tipo}-${h.registrado_en}-${indice}`} className="border-b border-border-subtle">
                    <td className="px-3 py-2 text-sm text-text-900">{formatearFecha(h.registrado_en)}</td>
                    <td className="px-3 py-2 text-sm text-text-900">
                      {ETIQUETAS_HISTORIA_SOD[h.tipo] ?? h.tipo}
                    </td>
                    <td className="px-3 py-2 text-sm text-text-900">{h.registrado_por ?? "—"}</td>
                    <td className="px-3 py-2 text-sm text-text-900">{detalleTexto}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </PageContent>
  );
}
