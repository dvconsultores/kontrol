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
import { ConflictoSoD, detalleDeConflictoSod } from "@/modules/gobierno/sod/ConflictoSoD";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_CIERRES,
  ETIQUETAS_ACCION_CIERRE,
  ETIQUETAS_ESTADO_POLITICA_CIERRE,
  ETIQUETAS_HISTORIA_CIERRE,
  ETIQUETAS_RIESGO_CIERRE,
  ETIQUETAS_TIPO_CONTROL_CIERRE,
  type CatalogoCierres,
  type PoliticaCierreCambios,
  type PoliticaCierreDetalle,
  type ControlCierreEntrada,
  type TipoControlCierre,
  type RiesgoMinimoCierre,
} from "@/modules/gobierno/api";

type PanelActivo = "editar" | "anadir-control" | "retirar" | null;

export function PoliticaPage() {
  const { politicaId } = useParams();
  const { activeCompanyId } = useCompany();
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();

  const claveDetalle = [...CONSULTA_CIERRES, activeCompanyId, "politica", politicaId];

  const consultaDetalle = useQuery({
    queryKey: claveDetalle,
    queryFn: () => apiFetch<PoliticaCierreDetalle>(`/gobierno/cierres/politicas/${politicaId}`),
    enabled: Boolean(activeCompanyId && politicaId),
    retry: false,
  });

  const consultaCatalogo = useQuery({
    queryKey: [...CONSULTA_CIERRES, activeCompanyId, "catalogo"],
    queryFn: () => apiFetch<CatalogoCierres>(`/gobierno/cierres/catalogo`),
    enabled: Boolean(activeCompanyId),
    retry: false,
  });

  const puedeGestionar = tiene("gobierno_cierre:manage", "empresa");
  const puedeActivar = tiene("gobierno_cierre:activate", "empresa");

  const [panel, setPanel] = useState<PanelActivo>(null);
  const [enviando, setEnviando] = useState(false);

  const [nombre, setNombre] = useState("");
  const [fundamento, setFundamento] = useState("");
  const [vigenteDesde, setVigenteDesde] = useState("");
  const [vigenteHasta, setVigenteHasta] = useState("");

  const [tipoControl, setTipoControl] = useState<TipoControlCierre | "">("");
  const [riesgoMinimo, setRiesgoMinimo] = useState<RiesgoMinimoCierre | "">("");
  const [materialidad, setMaterialidad] = useState("");

  const [motivoRetiro, setMotivoRetiro] = useState("");
  const [erroresServidor, setErroresServidor] = useState<Record<string, string[]>>({});
  const [alertaCambio, setAlertaCambio] = useState<string | null>(null);
  const [conflictoSod, setConflictoSod] = useState<ReturnType<typeof detalleDeConflictoSod>>(null);

  const recargar = () => {
    void queryClient.invalidateQueries({ queryKey: [...CONSULTA_CIERRES] });
  };

  const manejarError = (e: unknown) => {
    const detalleConflicto = detalleDeConflictoSod(e);
    if (detalleConflicto) {
      setConflictoSod(detalleConflicto);
      return;
    }
    if (e instanceof ApiError) {
      if (e.status === 409 && e.code === "GOV_CLOSURE_POLICY_STALE") {
        setAlertaCambio(
          "Otra persona modificó esta política. Recargue para ver los cambios.",
        );
        recargar();
        return;
      }
      if (e.status === 409 && e.code === "GOV_CLOSURE_POLICY_ACTIVE_EXISTS") {
        setAlertaCambio(
          "Ya hay una política vigente para esa acción de cierre.",
        );
        return;
      }
      if (e.status === 409 && e.code === "GOV_CLOSURE_POLICY_INVALID_STATE") {
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
    method: "PATCH" | "POST" | "DELETE",
    body: Record<string, unknown> | undefined,
  ) => {
    try {
      const nuevoDetalle = await apiFetch<PoliticaCierreDetalle>(ruta, {
        method,
        body,
        ifMatch: String(consultaDetalle.data?.version),
      });
      queryClient.setQueryData(claveDetalle, nuevoDetalle);
      void queryClient.invalidateQueries({ queryKey: [...CONSULTA_CIERRES] });
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
      crumbs={[{ label: "Gobierno" }, { label: "Cierres", to: "/gobierno/cierres" }]}
      title="Política de cierre"
    />
  );

  if (consultaDetalle.isLoading) {
    return (
      <PageContent>
        {cabeceraSinDetalle}
        <LoadingState label="Cargando política…" />
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
            action={<Link to="/gobierno/cierres">Volver a Cierres</Link>}
          />
        </PageContent>
      );
    }
    if (error instanceof ApiError && error.status === 403) {
      return (
        <PageContent>
          {cabeceraSinDetalle}
          <EmptyState title="Sin acceso" description="No tiene permiso para ver esta política." />
        </PageContent>
      );
    }
    if (error instanceof ApiError && error.status === 404) {
      return (
        <PageContent>
          {cabeceraSinDetalle}
          <EmptyState
            title="Política no encontrada"
            description="La política no existe en este ente."
            action={<Link to="/gobierno/cierres">Volver a Cierres</Link>}
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        {cabeceraSinDetalle}
        <ErrorState message="No fue posible cargar la política." onRetry={() => void consultaDetalle.refetch()} />
      </PageContent>
    );
  }

  const detalle = consultaDetalle.data;
  if (!detalle) {
    return (
      <PageContent>
        {cabeceraSinDetalle}
        <ErrorState message="No fue posible cargar la política." onRetry={() => void consultaDetalle.refetch()} />
      </PageContent>
    );
  }

  const catalogo = consultaCatalogo.data;

  const estadoEtiqueta = ETIQUETAS_ESTADO_POLITICA_CIERRE[detalle.estado] ?? detalle.estado;
  const accionEtiqueta = ETIQUETAS_ACCION_CIERRE[detalle.accion_cierre] ?? detalle.accion_cierre;

  const abrirPanelEdicion = () => {
    setErroresServidor({});
    setAlertaCambio(null);
    setNombre(detalle.nombre);
    setFundamento(detalle.fundamento);
    setVigenteDesde(detalle.vigente_desde ?? "");
    setVigenteHasta(detalle.vigente_hasta ?? "");
    setPanel("editar");
  };

  const abrirPanelAnadirControl = () => {
    setErroresServidor({});
    setAlertaCambio(null);
    setTipoControl("");
    setRiesgoMinimo("");
    setMaterialidad("");
    setPanel("anadir-control");
  };

  const abrirPanelRetirar = () => {
    setErroresServidor({});
    setAlertaCambio(null);
    setMotivoRetiro("");
    setPanel("retirar");
  };

  const cerrarPanel = () => {
    setPanel(null);
    setErroresServidor({});
    setAlertaCambio(null);
    setMotivoRetiro("");
  };

  const camposCambiados = (): PoliticaCierreCambios | null => {
    const cambios: PoliticaCierreCambios = {};
    if (nombre !== detalle.nombre) cambios.nombre = nombre;
    if (fundamento !== detalle.fundamento) cambios.fundamento = fundamento;

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
      const nuevoDetalle = await escribirDetalle(`/gobierno/cierres/politicas/${detalle.id}`, "PATCH", {
        ...cambios,
      });
      setNombre(nuevoDetalle.nombre);
      setFundamento(nuevoDetalle.fundamento);
      setVigenteDesde(nuevoDetalle.vigente_desde ?? "");
      setVigenteHasta(nuevoDetalle.vigente_hasta ?? "");
      cerrarPanel();
      notify({ type: "success", title: "Política actualizada" });
    } catch {
      // el error ya fue manejado
    } finally {
      setEnviando(false);
    }
  };

  const activarPolitica = async () => {
    if (enviando) return;
    setEnviando(true);
    try {
      await escribirDetalle(`/gobierno/cierres/politicas/${detalle.id}/activar`, "POST", {});
      cerrarPanel();
      notify({ type: "success", title: "Política activada" });
    } catch {
      // el error ya fue manejado
    } finally {
      setEnviando(false);
    }
  };

  const retirarPolitica = async () => {
    if (enviando) return;
    if (motivoRetiro.trim().length < 10 || motivoRetiro.length > 500) return;
    setEnviando(true);
    try {
      await escribirDetalle(`/gobierno/cierres/politicas/${detalle.id}/retirar`, "POST", {
        motivo: motivoRetiro,
      });
      cerrarPanel();
      notify({ type: "success", title: "Política retirada" });
    } catch {
      // el error ya fue manejado
    } finally {
      setEnviando(false);
    }
  };

  const tipoSeleccionado = catalogo?.tipos.find((t) => t.codigo === tipoControl);
  const requiereRiesgo = tipoSeleccionado?.requiere_riesgo ?? false;

  const anadirControl = async () => {
    if (enviando) return;
    if (!tipoControl) return;
    setEnviando(true);
    const entrada: ControlCierreEntrada = {
      tipo: tipoControl,
      riesgo_minimo: requiereRiesgo ? (riesgoMinimo as RiesgoMinimoCierre) : null,
      materialidad,
    };
    try {
      await escribirDetalle(`/gobierno/cierres/politicas/${detalle.id}/controles`, "POST", {
        ...entrada,
      });
      cerrarPanel();
      notify({ type: "success", title: "Control añadido" });
    } catch {
      // el error ya fue manejado
    } finally {
      setEnviando(false);
    }
  };

  const quitarControl = async (controlId: string) => {
    if (enviando) return;
    setEnviando(true);
    try {
      await escribirDetalle(`/gobierno/cierres/politicas/${detalle.id}/controles/${controlId}`, "DELETE", undefined);
      notify({ type: "success", title: "Control quitado" });
    } catch {
      // el error ya fue manejado
    } finally {
      setEnviando(false);
    }
  };

  const esMotivoRetiroValido = motivoRetiro.trim().length >= 10 && motivoRetiro.length <= 500;
  const esMaterialidadValida = materialidad.trim().length >= 10 && materialidad.length <= 500;

  const panelRender = panel === "editar" ? (
    <section aria-labelledby="editar-politica-titulo" className="mb-8 rounded-lg border border-border-subtle p-4">
      <h2 id="editar-politica-titulo" className="mb-4 text-lg font-semibold text-text-900">
        Editar borrador
      </h2>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void guardarEdicion();
        }}
      >
        <FormField label="Nombre" htmlFor="politica-editar-nombre" error={erroresServidor.nombre?.[0]}>
          <TextInput
            id="politica-editar-nombre"
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            required
          />
        </FormField>
        <div className="mt-4">
          <FormField label="Fundamento" htmlFor="politica-editar-fundamento" error={erroresServidor.fundamento?.[0]}>
            <textarea
              id="politica-editar-fundamento"
              className="min-h-24 w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              value={fundamento}
              onChange={(e) => setFundamento(e.target.value)}
            />
          </FormField>
        </div>
        <div className="mt-4">
          <FormField
            label="Vigente desde"
            htmlFor="politica-editar-desde"
            error={erroresServidor.vigente_desde?.[0]}
          >
            <TextInput
              id="politica-editar-desde"
              type="date"
              value={vigenteDesde}
              onChange={(e) => setVigenteDesde(e.target.value)}
              required
            />
          </FormField>
        </div>
        <div className="mt-4">
          <FormField label="Vigente hasta" htmlFor="politica-editar-hasta" error={erroresServidor.vigente_hasta?.[0]}>
            <TextInput
              id="politica-editar-hasta"
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
  ) : panel === "anadir-control" ? (
    <section aria-labelledby="anadir-control-titulo" className="mb-8 rounded-lg border border-border-subtle p-4">
      <h2 id="anadir-control-titulo" className="mb-4 text-lg font-semibold text-text-900">
        Añadir control
      </h2>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void anadirControl();
        }}
      >
        <FormField label="Tipo" htmlFor="politica-control-tipo" error={erroresServidor.tipo?.[0]}>
          <select
            id="politica-control-tipo"
            className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
            value={tipoControl}
            onChange={(e) => {
              setTipoControl(e.target.value as TipoControlCierre);
              setRiesgoMinimo("");
            }}
            required
          >
            <option value="">Seleccione…</option>
            {(catalogo?.tipos ?? []).map((tipo) => (
              <option key={tipo.codigo} value={tipo.codigo}>
                {tipo.etiqueta}
              </option>
            ))}
          </select>
        </FormField>
        {requiereRiesgo ? (
          <div className="mt-4">
            <FormField
              label="Riesgo mínimo"
              htmlFor="politica-control-riesgo"
              error={erroresServidor.riesgo_minimo?.[0]}
            >
              <select
                id="politica-control-riesgo"
                className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                value={riesgoMinimo}
                onChange={(e) => setRiesgoMinimo(e.target.value as RiesgoMinimoCierre)}
                required
              >
                <option value="">Seleccione…</option>
                <option value="ALTO">{ETIQUETAS_RIESGO_CIERRE.ALTO}</option>
                <option value="MEDIO">{ETIQUETAS_RIESGO_CIERRE.MEDIO}</option>
                <option value="BAJO">{ETIQUETAS_RIESGO_CIERRE.BAJO}</option>
              </select>
            </FormField>
          </div>
        ) : null}
        <div className="mt-4">
          <FormField
            label="Materialidad"
            htmlFor="politica-control-materialidad"
            required
            error={erroresServidor.materialidad?.[0]}
          >
            <textarea
              id="politica-control-materialidad"
              className="min-h-24 w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              minLength={10}
              maxLength={500}
              value={materialidad}
              onChange={(e) => setMaterialidad(e.target.value)}
            />
            {!esMaterialidadValida && materialidad.length > 0 ? (
              <p className="mt-1 text-sm text-danger-600">La materialidad debe tener entre 10 y 500 caracteres.</p>
            ) : null}
          </FormField>
        </div>
        <div className="mt-4 flex gap-2">
          <Button
            type="button"
            variant="primary"
            disabled={!tipoControl || !esMaterialidadValida || enviando}
            onClick={() => void anadirControl()}
          >
            Guardar
          </Button>
          <Button type="button" variant="secondary" onClick={cerrarPanel}>
            Cancelar
          </Button>
        </div>
      </form>
    </section>
  ) : panel === "retirar" ? (
    <section aria-labelledby="retirar-politica-titulo" className="mb-8 rounded-lg border border-border-subtle p-4">
      <h2 id="retirar-politica-titulo" className="mb-4 text-lg font-semibold text-text-900">
        Retirar política
      </h2>
      <p className="mb-4 text-text-700">
        Una política retirada deja de aplicarse y no se puede reactivar; para cambiarla, registre otra.
      </p>
      <FormField
        label="Motivo"
        htmlFor="politica-retirar-motivo"
        required
        error={erroresServidor.motivo?.[0]}
      >
        <textarea
          id="politica-retirar-motivo"
          className="min-h-24 w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
          minLength={10}
          maxLength={500}
          value={motivoRetiro}
          onChange={(e) => setMotivoRetiro(e.target.value)}
        />
        {!esMotivoRetiroValido && motivoRetiro.length > 0 ? (
          <p className="mt-1 text-sm text-danger-600">El motivo debe tener entre 10 y 500 caracteres.</p>
        ) : null}
      </FormField>
      <div className="mt-4 flex gap-2">
        <AsyncButton
          variant="primary"
          disabled={!esMotivoRetiroValido || enviando}
          onClick={retirarPolitica}
        >
          Confirmar retiro
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
        crumbs={[{ label: "Gobierno" }, { label: "Cierres", to: "/gobierno/cierres" }]}
        title={`Política ${detalle.codigo}`}
        description={detalle.nombre}
      />

      <p className="mb-6 text-sm text-text-700">
        {estadoEtiqueta}
        {detalle.efectiva_hoy ? " · efectiva hoy" : ""}
      </p>

      {alertaRender}
      {conflictoSod ? (
        <ConflictoSoD detalle={conflictoSod} onCerrar={() => setConflictoSod(null)} />
      ) : null}

      <section aria-labelledby="datos-politica-titulo" className="mb-8">
        <h2 id="datos-politica-titulo" className="mb-4 text-lg font-semibold text-text-900">
          Datos de la política
        </h2>
        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <dt className="text-sm font-medium text-text-700">Acción controlada</dt>
            <dd className="mt-1 text-text-900">{accionEtiqueta}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Nombre</dt>
            <dd className="mt-1 text-text-900">{detalle.nombre}</dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-sm font-medium text-text-700">Fundamento</dt>
            <dd className="mt-1 text-text-900">{detalle.fundamento}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Vigencia</dt>
            <dd className="mt-1 text-text-900">
              {detalle.vigente_desde ? formatearFechaDeNegocio(detalle.vigente_desde) : "—"}
              {" hasta "}
              {detalle.vigente_hasta ? formatearFechaDeNegocio(detalle.vigente_hasta) : "sin fecha de fin"}
            </dd>
          </div>
          {detalle.activada_por ? (
            <div>
              <dt className="text-sm font-medium text-text-700">Activada</dt>
              <dd className="mt-1 text-text-900">
                {detalle.activada_por} · {detalle.activada_en ? formatearFecha(detalle.activada_en) : "—"}
              </dd>
            </div>
          ) : null}
          {detalle.retirada_por ? (
            <div>
              <dt className="text-sm font-medium text-text-700">Retirada</dt>
              <dd className="mt-1 text-text-900">
                {detalle.retirada_por} · {detalle.retirada_en ? formatearFecha(detalle.retirada_en) : "—"}
                {detalle.motivo_retiro ? ` · ${detalle.motivo_retiro}` : ""}
              </dd>
            </div>
          ) : null}
        </dl>
      </section>

      <div className="mb-8 flex flex-wrap items-center gap-2">
        {detalle.estado === "BORRADOR" && puedeGestionar ? (
          <Button variant="secondary" onClick={abrirPanelEdicion}>
            Editar
          </Button>
        ) : null}
        {detalle.estado === "BORRADOR" && puedeGestionar ? (
          <Button variant="secondary" onClick={abrirPanelAnadirControl}>
            Añadir control
          </Button>
        ) : null}
        {detalle.estado === "BORRADOR" && puedeActivar ? (
          <AsyncButton
            variant="primary"
            disabled={detalle.controles.length === 0 || enviando}
            onClick={activarPolitica}
            title={detalle.controles.length === 0 ? "Añada al menos un control para activar" : undefined}
          >
            Activar
          </AsyncButton>
        ) : null}
        {detalle.estado === "BORRADOR" && puedeActivar && detalle.controles.length === 0 ? (
          <p className="text-sm text-text-700">Añada al menos un control para activar</p>
        ) : null}
        {(detalle.estado === "BORRADOR" || detalle.estado === "VIGENTE") && puedeActivar ? (
          <Button variant="secondary" onClick={abrirPanelRetirar}>
            Retirar
          </Button>
        ) : null}
      </div>

      {panelRender}

      <section aria-labelledby="controles-politica-titulo" className="mb-8">
        <h2 id="controles-politica-titulo" className="mb-4 text-lg font-semibold text-text-900">
          Controles
        </h2>
        <div className="relative overflow-x-auto" tabIndex={0} role="region" aria-label="Tabla de controles de la política">
          <table className="w-full border-collapse text-left">
            <caption className="sr-only">Controles de la política</caption>
            <thead>
              <tr className="border-b border-border-subtle">
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">Tipo</th>
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">Riesgo mínimo</th>
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">Materialidad</th>
                {detalle.estado === "BORRADOR" && puedeGestionar ? (
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                    <span className="sr-only">Acciones</span>
                  </th>
                ) : null}
              </tr>
            </thead>
            <tbody>
              {detalle.controles.length === 0 ? (
                <tr className="border-b border-border-subtle">
                  <td colSpan={detalle.estado === "BORRADOR" && puedeGestionar ? 4 : 3} className="px-3 py-4 text-sm text-text-700">
                    No hay controles definidos.
                  </td>
                </tr>
              ) : (
                detalle.controles.map((control) => (
                  <tr key={control.id} className="border-b border-border-subtle">
                    <td className="px-3 py-2 text-sm text-text-900">
                      {ETIQUETAS_TIPO_CONTROL_CIERRE[control.tipo] ?? control.tipo}
                    </td>
                    <td className="px-3 py-2 text-sm text-text-900">
                      {control.riesgo_minimo ? ETIQUETAS_RIESGO_CIERRE[control.riesgo_minimo] : "—"}
                    </td>
                    <td className="px-3 py-2 text-sm text-text-900">{control.materialidad}</td>
                    {detalle.estado === "BORRADOR" && puedeGestionar ? (
                      <td className="px-3 py-2 text-sm text-text-900">
                        <Button
                          variant="secondary"
                          disabled={enviando}
                          onClick={() => void quitarControl(control.id)}
                        >
                          Quitar control
                        </Button>
                      </td>
                    ) : null}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="historia-politica-titulo">
        <h2 id="historia-politica-titulo" className="mb-4 text-lg font-semibold text-text-900">
          Historia
        </h2>
        <div className="relative overflow-x-auto" tabIndex={0} role="region" aria-label="Tabla de historia de la política">
          <table className="w-full border-collapse text-left">
            <caption className="sr-only">Historia de la política</caption>
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
                const detalleTexto =
                  h.detalle && typeof h.detalle === "object"
                    ? Object.entries(h.detalle)
                        .map(([clave, valor]) => `${clave}: ${String(valor)}`)
                        .join(", ")
                    : "—";
                return (
                  <tr key={`${h.evento}-${h.instante}-${indice}`} className="border-b border-border-subtle">
                    <td className="px-3 py-2 text-sm text-text-900">{formatearFecha(h.instante)}</td>
                    <td className="px-3 py-2 text-sm text-text-900">
                      {ETIQUETAS_HISTORIA_CIERRE[h.evento] ?? h.evento}
                    </td>
                    <td className="px-3 py-2 text-sm text-text-900">{h.usuario ?? "—"}</td>
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
