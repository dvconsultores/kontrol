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
import { ConflictoSoD, detalleDeConflictoSod } from "@/modules/gobierno/sod/ConflictoSoD";
import { AutorizadosCuenta } from "@/modules/gobierno/tesoreria/AutorizadosCuenta";
import {
  CONSULTA_CUENTAS,
  ETIQUETAS_ESTADO_CUENTA,
  ETIQUETAS_HISTORIA_CUENTA,
  ETIQUETAS_TIPO_CUENTA,
  MONEDAS_CUENTA,
  textoDeActo,
  type CuentaDetalle,
  type CuentaEntrada,
  type CuentasOpciones,
  ETIQUETA_ESTADO_ACTO,
  ETIQUETA_TIPO_ACTO,
  type EstadoActo,
  type MonedaCuenta,
  type TipoActo,
  type NumeroCuenta,
  type TipoCuenta,
} from "@/modules/gobierno/api";

type PanelActivo = "editar" | "inactivar" | "reactivar" | "cerrar" | null;

const ETIQUETA_FALTANTE_ACTIVACION: Record<string, string> = {
  acto: "un acto habilitante vigente",
  autorizado: "al menos un cargo autorizado en vigor",
  vigencia: "estar dentro de su vigencia",
};


export function CuentaPage(): React.JSX.Element {
  const { cuentaId } = useParams();
  const { activeCompanyId } = useCompany();
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();

  const puedeVer = tiene("gobierno_cuentas:view", "empresa");
  const puedeGestionar = tiene("gobierno_cuentas:manage", "empresa");
  const puedeActivar = tiene("gobierno_cuentas:activate", "empresa");

  const claveDetalle = [...CONSULTA_CUENTAS, "cuenta", cuentaId, activeCompanyId];
  const claveOpciones = [...CONSULTA_CUENTAS, "opciones", activeCompanyId];

  const consultaDetalle = useQuery({
    queryKey: claveDetalle,
    queryFn: () => apiFetch<CuentaDetalle>(`/gobierno/tesoreria/cuentas/${cuentaId}`),
    enabled: Boolean(activeCompanyId && cuentaId && puedeVer),
    retry: false,
  });

  const consultaOpciones = useQuery({
    queryKey: claveOpciones,
    queryFn: () => apiFetch<CuentasOpciones>("/gobierno/tesoreria/opciones"),
    enabled: Boolean(activeCompanyId && cuentaId && puedeGestionar),
    retry: false,
  });

  const [panel, setPanel] = useState<PanelActivo>(null);
  const [enviando, setEnviando] = useState(false);
  const [motivo, setMotivo] = useState("");
  const [fechaCierre, setFechaCierre] = useState(hoyDeNegocio());
  const [conflictoSod, setConflictoSod] = useState<ReturnType<typeof detalleDeConflictoSod>>(null);
  const [alerta, setAlerta] = useState<string | null>(null);
  const [erroresServidor, setErroresServidor] = useState<Record<string, string[]>>({});
  const [numeroCompleto, setNumeroCompleto] = useState<string | null>(null);
  const [actoElegido, setActoElegido] = useState("");

  const [edicion, setEdicion] = useState<{
    denominacion: string;
    banco_id: string;
    tipo: TipoCuenta;
    numero: string;
    moneda: MonedaCuenta;
    vigente_desde: string;
    vigente_hasta: string;
  }>({
    denominacion: "",
    banco_id: "",
    tipo: "CORRIENTE",
    numero: "",
    moneda: "VES",
    vigente_desde: "",
    vigente_hasta: "",
  });


  const recargar = () => {
    void queryClient.invalidateQueries({ queryKey: [...CONSULTA_CUENTAS] });
  };

  const aplicar = (cuenta: CuentaDetalle) => {
    queryClient.setQueryData(claveDetalle, cuenta);
    void queryClient.invalidateQueries({ queryKey: [...CONSULTA_CUENTAS] });
    setAlerta(null);
    setErroresServidor({});
  };

  const alFallar = (e: unknown) => {
    const detalleConflicto = detalleDeConflictoSod(e);
    if (detalleConflicto) {
      setConflictoSod(detalleConflicto);
      return;
    }
    if (e instanceof ApiError && e.status === 409 && e.code === "GOV_BANK_ACCOUNT_STALE") {
      setAlerta("La cuenta cambió desde que la abrió. Se recargaron los datos; revise y vuelva a intentarlo.");
      recargar();
      return;
    }
    if (e instanceof ApiError && e.status === 409 && e.code === "GOV_BANK_ACCOUNT_NOT_READY") {
      const faltan = Array.isArray(e.details?.faltan) ? (e.details.faltan as string[]) : [];
      const textoFaltantes = faltan
        .map((f) => ETIQUETA_FALTANTE_ACTIVACION[f] ?? f)
        .join(", ");
      setAlerta(`Para continuar la cuenta necesita: ${textoFaltantes}.`);
      return;
    }
    if (e instanceof ApiError) {
      setAlerta(e.message);
      return;
    }
    setAlerta("No fue posible completar la operación");
  };

  const escribirCuenta = async (
    ruta: string,
    method: "PATCH" | "POST",
    body: Record<string, unknown>,
  ) => {
    try {
      const nuevaCuenta = await apiFetch<CuentaDetalle>(ruta, {
        method,
        body,
        ifMatch: String(consultaDetalle.data?.version),
      });
      aplicar(nuevaCuenta);
      return nuevaCuenta;
    } catch (e) {
      alFallar(e);
      throw e;
    }
  };

  const cabeceraSinDetalle = (
    <PageHeader
      crumbs={[{ label: "Gobierno" }, { label: "Tesorería" }, { label: "Cuentas bancarias", to: "/gobierno/tesoreria/cuentas" }]}
      title="Cuenta bancaria"
    />
  );

  if (consultaDetalle.isLoading && puedeVer) {
    return (
      <PageContent>
        {cabeceraSinDetalle}
        <LoadingState label="Cargando cuenta…" />
      </PageContent>
    );
  }

  if (!puedeVer) {
    return (
      <PageContent>
        {cabeceraSinDetalle}
        <EmptyState title="Sin acceso" description="No tiene permiso para ver esta cuenta." />
      </PageContent>
    );
  }

  if (consultaDetalle.isError) {
    const error = consultaDetalle.error;
    if (error instanceof ApiError && error.status === 403) {
      return (
        <PageContent>
          {cabeceraSinDetalle}
          <EmptyState title="Sin acceso" description="No tiene permiso para ver esta cuenta." />
        </PageContent>
      );
    }
    if (error instanceof ApiError && error.status === 404) {
      return (
        <PageContent>
          {cabeceraSinDetalle}
          <EmptyState
            title="Cuenta no encontrada"
            description="La cuenta no existe en este ente."
            action={<Link to="/gobierno/tesoreria/cuentas">Volver a Cuentas bancarias</Link>}
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        {cabeceraSinDetalle}
        <ErrorState message="No fue posible cargar la cuenta." onRetry={() => void consultaDetalle.refetch()} />
      </PageContent>
    );
  }

  const cuenta = consultaDetalle.data;
  if (!cuenta) {
    return (
      <PageContent>
        {cabeceraSinDetalle}
        <ErrorState message="No fue posible cargar la cuenta." onRetry={() => void consultaDetalle.refetch()} />
      </PageContent>
    );
  }

  const opciones = consultaOpciones.data;
  const estadoEtiqueta = ETIQUETAS_ESTADO_CUENTA[cuenta.estado] ?? cuenta.estado;

  const abrirPanelEdicion = () => {
    setErroresServidor({});
    setAlerta(null);
    setEdicion({
      denominacion: cuenta.denominacion,
      banco_id: cuenta.banco_id,
      tipo: cuenta.tipo,
      numero: "",
      moneda: cuenta.moneda,
      vigente_desde: cuenta.vigente_desde ?? "",
      vigente_hasta: cuenta.vigente_hasta ?? "",
    });
    setPanel("editar");
  };

  const abrirPanelMotivo = (tipo: Exclude<PanelActivo, "editar" | null>) => {
    setErroresServidor({});
    setAlerta(null);
    setMotivo("");
    setFechaCierre(hoyDeNegocio());
    setPanel(tipo);
  };

  const cerrarPanel = () => {
    setPanel(null);
    setErroresServidor({});
    setAlerta(null);
    setMotivo("");
  };

  const esMotivoValido = motivo.trim().length >= 10 && motivo.length <= 500;

  const camposEditados = (): Partial<CuentaEntrada> | null => {
    const cambios: Partial<CuentaEntrada> = {};
    if (edicion.denominacion !== cuenta.denominacion) cambios.denominacion = edicion.denominacion;
    if (edicion.banco_id !== cuenta.banco_id) cambios.banco_id = edicion.banco_id;
    if (edicion.tipo !== cuenta.tipo) cambios.tipo = edicion.tipo;
    if (edicion.moneda !== cuenta.moneda) cambios.moneda = edicion.moneda;
    if (edicion.vigente_desde !== "" && edicion.vigente_desde !== (cuenta.vigente_desde ?? "")) {
      cambios.vigente_desde = edicion.vigente_desde;
    }
    const hastaNuevo = edicion.vigente_hasta.trim() === "" ? null : edicion.vigente_hasta;
    if (hastaNuevo !== (cuenta.vigente_hasta ?? null)) cambios.vigente_hasta = hastaNuevo;
    if (edicion.numero.trim() !== "") cambios.numero = edicion.numero.trim();
    return Object.keys(cambios).length > 0 ? cambios : null;
  };

  const guardarEdicion = async () => {
    if (enviando) return;
    const numeroEscrito = edicion.numero.trim();
    const bancoElegido = opciones?.bancos.find((b) => b.id === edicion.banco_id);
    const codigoBanco = bancoElegido?.codigo ?? cuenta.banco_codigo;
    if (edicion.denominacion.trim().length < 3) {
      setAlerta("La denominación debe tener al menos 3 caracteres.");
      return;
    }
    if (numeroEscrito !== "" && !/^\d{20}$/.test(numeroEscrito)) {
      setAlerta("El número debe tener 20 dígitos.");
      return;
    }
    if (numeroEscrito !== "" && !numeroEscrito.startsWith(codigoBanco)) {
      setAlerta("El número debe empezar por el código del banco.");
      return;
    }
    if (edicion.vigente_hasta !== "" && edicion.vigente_hasta < edicion.vigente_desde) {
      setAlerta("La vigencia final no puede ser anterior a la inicial.");
      return;
    }
    const cambios = camposEditados();
    if (!cambios) {
      setAlerta("No hay cambios que guardar.");
      return;
    }
    setEnviando(true);
    try {
      await escribirCuenta(`/gobierno/tesoreria/cuentas/${cuenta.id}`, "PATCH", { ...cambios });
      cerrarPanel();
      notify({ type: "success", title: "Cuenta actualizada" });
    } catch {
      // el error ya fue manejado
    } finally {
      setEnviando(false);
    }
  };

  const vincularActo = async () => {
    if (enviando || !actoElegido) return;
    setEnviando(true);
    try {
      await escribirCuenta(`/gobierno/tesoreria/cuentas/${cuenta.id}/acto`, "POST", {
        acto_id: actoElegido,
      });
      notify({ type: "success", title: "Acto vinculado" });
      setActoElegido("");
    } catch {
      // el error ya fue manejado
    } finally {
      setEnviando(false);
    }
  };

  const activarCuenta = async () => {
    if (enviando) return;
    setEnviando(true);
    try {
      await escribirCuenta(`/gobierno/tesoreria/cuentas/${cuenta.id}/activar`, "POST", {});
      notify({ type: "success", title: "Cuenta activada" });
    } catch {
      // el error ya fue manejado
    } finally {
      setEnviando(false);
    }
  };

  const ejecutarConMotivo = async (
    panelActivo: Exclude<PanelActivo, "editar" | null>,
    ruta: string,
    titulo: string,
  ) => {
    if (enviando) return;
    if (!esMotivoValido) return;
    setEnviando(true);
    try {
      const body: Record<string, unknown> = { motivo };
      if (panelActivo === "cerrar") body.fecha_cierre = fechaCierre;
      await escribirCuenta(`/gobierno/tesoreria/cuentas/${cuenta.id}/${ruta}`, "POST", body);
      cerrarPanel();
      notify({ type: "success", title: titulo });
    } catch {
      // el error ya fue manejado
    } finally {
      setEnviando(false);
    }
  };

  const verNumeroCompleto = async () => {
    try {
      const respuesta = await apiFetch<NumeroCuenta>(
        `/gobierno/tesoreria/cuentas/${cuenta.id}/numero`,
      );
      setNumeroCompleto(respuesta.numero);
    } catch (e) {
      alFallar(e);
    }
  };

  const ocultarNumero = () => {
    setNumeroCompleto(null);
  };

  const alertaRender = alerta ? (
    <div role="alert" className="mb-4 rounded-md border border-error-300 bg-error-50 p-3 text-error-800">
      {alerta}
    </div>
  ) : null;

  const avisosFijos: string[] = [];
  if (cuenta.acto_sin_efecto) {
    avisosFijos.push(
      "El acto habilitante fue revocado o anulado. Vincule un acto vigente: hasta entonces no se admiten nuevos autorizados ni la reactivación.",
    );
  }
  if (cuenta.estado === "VIGENTE" && cuenta.autorizados_en_vigor === 0) {
    avisosFijos.push("Esta cuenta vigente no tiene cargos autorizados en vigor.");
  }
  if (cuenta.estado === "VIGENTE" && !cuenta.en_vigor) {
    avisosFijos.push("La cuenta está fuera de su período de vigencia.");
  }

  const panelEdicion = panel === "editar" ? (
    <section aria-labelledby="editar-cuenta-titulo" className="mb-8 rounded-lg border border-border-subtle p-4">
      <h2 id="editar-cuenta-titulo" className="mb-4 text-lg font-semibold text-text-900">
        Editar borrador
      </h2>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void guardarEdicion();
        }}
      >
        <FormField
          label="Denominación"
          htmlFor="cuenta-editar-denominacion"
          error={erroresServidor.denominacion?.[0]}
        >
          <TextInput
            id="cuenta-editar-denominacion"
            value={edicion.denominacion}
            onChange={(e) => setEdicion((prev) => ({ ...prev, denominacion: e.target.value }))}
            required
          />
        </FormField>
        <div className="mt-4">
          <FormField
            label="Banco"
            htmlFor="cuenta-editar-banco"
            required
            error={erroresServidor.banco_id?.[0]}
          >
            <select
              id="cuenta-editar-banco"
              className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              value={edicion.banco_id}
              onChange={(e) => setEdicion((prev) => ({ ...prev, banco_id: e.target.value }))}
              required
            >
              <option value="">Seleccione un banco</option>
              {(opciones?.bancos ?? []).map((banco) => (
                <option key={banco.id} value={banco.id}>
                  {banco.codigo} · {banco.nombre}
                </option>
              ))}
            </select>
          </FormField>
        </div>
        <div className="mt-4">
          <FormField label="Tipo" htmlFor="cuenta-editar-tipo" required error={erroresServidor.tipo?.[0]}>
            <select
              id="cuenta-editar-tipo"
              className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              value={edicion.tipo}
              onChange={(e) => setEdicion((prev) => ({ ...prev, tipo: e.target.value as TipoCuenta }))}
              required
            >
              {Object.entries(ETIQUETAS_TIPO_CUENTA).map(([valor, etiqueta]) => (
                <option key={valor} value={valor}>
                  {etiqueta}
                </option>
              ))}
            </select>
          </FormField>
        </div>
        <div className="mt-4">
          <FormField
            label="Número de cuenta"
            htmlFor="cuenta-editar-numero"
            help="Déjelo vacío para conservar el actual"
            error={erroresServidor.numero?.[0]}
          >
            <TextInput
              id="cuenta-editar-numero"
              value={edicion.numero}
              onChange={(e) => setEdicion((prev) => ({ ...prev, numero: e.target.value }))}
            />
          </FormField>
        </div>
        <div className="mt-4">
          <FormField label="Moneda" htmlFor="cuenta-editar-moneda" required error={erroresServidor.moneda?.[0]}>
            <select
              id="cuenta-editar-moneda"
              className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              value={edicion.moneda}
              onChange={(e) => setEdicion((prev) => ({ ...prev, moneda: e.target.value as MonedaCuenta }))}
              required
            >
              {MONEDAS_CUENTA.map((moneda) => (
                <option key={moneda} value={moneda}>
                  {moneda}
                </option>
              ))}
            </select>
          </FormField>
        </div>
        <div className="mt-4">
          <FormField
            label="Vigente desde"
            htmlFor="cuenta-editar-desde"
            required
            error={erroresServidor.vigente_desde?.[0]}
          >
            <TextInput
              id="cuenta-editar-desde"
              type="date"
              value={edicion.vigente_desde}
              onChange={(e) => setEdicion((prev) => ({ ...prev, vigente_desde: e.target.value }))}
              required
            />
          </FormField>
        </div>
        <div className="mt-4">
          <FormField
            label="Vigente hasta"
            htmlFor="cuenta-editar-hasta"
            error={erroresServidor.vigente_hasta?.[0]}
          >
            <TextInput
              id="cuenta-editar-hasta"
              type="date"
              value={edicion.vigente_hasta}
              onChange={(e) => setEdicion((prev) => ({ ...prev, vigente_hasta: e.target.value }))}
            />
          </FormField>
        </div>
        <div className="mt-4 flex gap-2">
          <AsyncButton
            variant="primary"
            disabled={enviando}
            onClick={guardarEdicion}
          >
            Guardar
          </AsyncButton>
          <Button type="button" variant="secondary" onClick={cerrarPanel}>
            Cancelar
          </Button>
        </div>
      </form>
    </section>
  ) : null;

  const panelMotivo =
    panel === "inactivar" || panel === "reactivar" || panel === "cerrar" ? (
      <section
        aria-labelledby={`${panel}-cuenta-titulo`}
        className="mb-8 rounded-lg border border-border-subtle p-4"
      >
        <h2 id={`${panel}-cuenta-titulo`} className="mb-4 text-lg font-semibold text-text-900">
          {panel === "inactivar"
            ? "Inactivar cuenta"
            : panel === "reactivar"
              ? "Reactivar cuenta"
              : "Cerrar cuenta"}
        </h2>
        {panel === "cerrar" ? (
          <div className="mb-4">
            <FormField label="Fecha de cierre" htmlFor="cuenta-fecha-cierre" required>
              <TextInput
                id="cuenta-fecha-cierre"
                type="date"
                value={fechaCierre}
                onChange={(e) => setFechaCierre(e.target.value)}
                required
              />
            </FormField>
          </div>
        ) : null}
        <FormField
          label="Motivo"
          htmlFor={`cuenta-${panel}-motivo`}
          required
          error={erroresServidor.motivo?.[0]}
        >
          <textarea
            id={`cuenta-${panel}-motivo`}
            className="min-h-24 w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
            minLength={10}
            maxLength={500}
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
          />
          {!esMotivoValido && motivo.length > 0 ? (
            <p className="mt-1 text-sm text-danger-600">El motivo debe tener entre 10 y 500 caracteres.</p>
          ) : null}
        </FormField>
        <div className="mt-4 flex gap-2">
          <AsyncButton
            variant="primary"
            disabled={!esMotivoValido || enviando}
            onClick={() =>
              ejecutarConMotivo(
                panel,
                panel === "inactivar"
                  ? "inactivar"
                  : panel === "reactivar"
                    ? "reactivar"
                    : "cerrar",
                panel === "inactivar"
                  ? "Cuenta inactivada"
                  : panel === "reactivar"
                    ? "Cuenta reactivada"
                    : "Cuenta cerrada",
              )
            }
          >
            Confirmar {panel === "inactivar" ? "inactivación" : panel === "reactivar" ? "reactivación" : "cierre"}
          </AsyncButton>
          <Button type="button" variant="secondary" onClick={cerrarPanel}>
            Cancelar
          </Button>
        </div>
      </section>
    ) : null;

  return (
    <PageContent>
      <PageHeader
        crumbs={[{ label: "Gobierno" }, { label: "Tesorería" }, { label: "Cuentas bancarias", to: "/gobierno/tesoreria/cuentas" }]}
        title={`Cuenta ${cuenta.codigo}`}
        description={cuenta.denominacion}
      />

      <p className="mb-6 text-sm text-text-700">
        {estadoEtiqueta}
        {cuenta.en_vigor ? " · en vigor" : cuenta.estado === "VIGENTE" ? " · aún no en vigor" : ""}
      </p>

      {alertaRender}

      {conflictoSod ? (
        <ConflictoSoD detalle={conflictoSod} onCerrar={() => setConflictoSod(null)} />
      ) : null}

      {avisosFijos.map((aviso) => (
        <div key={aviso} role="alert" className="mb-4 rounded-md bg-error-50 p-3 text-error-800">
          {aviso}
        </div>
      ))}

      <section aria-labelledby="datos-cuenta-titulo" className="mb-8">
        <h2 id="datos-cuenta-titulo" className="mb-4 text-lg font-semibold text-text-900">
          Datos de la cuenta
        </h2>
        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <dt className="text-sm font-medium text-text-700">Estado</dt>
            <dd className="mt-1 text-text-900">{estadoEtiqueta}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Denominación</dt>
            <dd className="mt-1 text-text-900">{cuenta.denominacion}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Banco</dt>
            <dd className="mt-1 text-text-900">
              {cuenta.banco_codigo} · {cuenta.banco_nombre}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Tipo</dt>
            <dd className="mt-1 text-text-900">{ETIQUETAS_TIPO_CUENTA[cuenta.tipo] ?? cuenta.tipo}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Moneda</dt>
            <dd className="mt-1 text-text-900">{cuenta.moneda}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Número</dt>
            <dd className="mt-1 text-text-900">
              {numeroCompleto ?? cuenta.numero_enmascarado}
              {numeroCompleto ? (
                <>
                  {" "}
                  <button
                    type="button"
                    className="font-medium text-brand-700 underline"
                    onClick={ocultarNumero}
                  >
                    Ocultar número
                  </button>
                  <p className="mt-1 text-sm text-text-700">
                    Esta consulta queda registrada en la auditoría.
                  </p>
                </>
              ) : puedeGestionar ? (
                <button
                  type="button"
                  className="ml-2 font-medium text-brand-700 underline"
                  onClick={() => void verNumeroCompleto()}
                >
                  Ver número completo
                </button>
              ) : null}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Vigente desde</dt>
            <dd className="mt-1 text-text-900">
              {cuenta.vigente_desde ? formatearFechaDeNegocio(cuenta.vigente_desde) : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Vigente hasta</dt>
            <dd className="mt-1 text-text-900">
              {cuenta.vigente_hasta ? formatearFechaDeNegocio(cuenta.vigente_hasta) : "Sin fin previsto"}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Registrada por</dt>
            <dd className="mt-1 text-text-900">{cuenta.registrada_por ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Registrada en</dt>
            <dd className="mt-1 text-text-900">{formatearFecha(cuenta.registrada_en)}</dd>
          </div>
          {cuenta.activada_por || cuenta.activada_en ? (
            <>
              <div>
                <dt className="text-sm font-medium text-text-700">Activada por</dt>
                <dd className="mt-1 text-text-900">{cuenta.activada_por ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-text-700">Activada en</dt>
                <dd className="mt-1 text-text-900">
                  {cuenta.activada_en ? formatearFecha(cuenta.activada_en) : "—"}
                </dd>
              </div>
            </>
          ) : null}
          {cuenta.estado === "CERRADA" ? (
            <>
              <div>
                <dt className="text-sm font-medium text-text-700">Fecha de cierre</dt>
                <dd className="mt-1 text-text-900">
                  {cuenta.fecha_cierre ? formatearFechaDeNegocio(cuenta.fecha_cierre) : "—"}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-text-700">Cerrada por</dt>
                <dd className="mt-1 text-text-900">{cuenta.cerrada_por ?? "—"}</dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-sm font-medium text-text-700">Motivo de cierre</dt>
                <dd className="mt-1 text-text-900">{cuenta.motivo_cierre ?? "—"}</dd>
              </div>
            </>
          ) : null}
        </dl>
      </section>

      <section aria-labelledby="acto-cuenta-titulo" className="mb-8">
        <h2 id="acto-cuenta-titulo" className="mb-4 text-lg font-semibold text-text-900">
          Acto habilitante
        </h2>
        {cuenta.acto ? (
          <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-sm font-medium text-text-700">Tipo</dt>
              <dd className="mt-1 text-text-900">
                {ETIQUETA_TIPO_ACTO[cuenta.acto.tipo as TipoActo] ?? cuenta.acto.tipo}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-text-700">Número</dt>
              <dd className="mt-1 text-text-900">{cuenta.acto.numero}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-text-700">Fecha</dt>
              <dd className="mt-1 text-text-900">
                {cuenta.acto.fecha ? formatearFechaDeNegocio(cuenta.acto.fecha) : "—"}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-text-700">Estado</dt>
              <dd className="mt-1 text-text-900">{ETIQUETA_ESTADO_ACTO[cuenta.acto.estado as EstadoActo] ?? cuenta.acto.estado}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-sm font-medium text-text-700">Asunto</dt>
              <dd className="mt-1 text-text-900">{cuenta.acto.asunto}</dd>
            </div>
            <div className="sm:col-span-2">
              <Link
                to={`/gobierno/actos/${cuenta.acto.id}`}
                className="font-medium text-brand-700 underline"
              >
                Abrir el acto
              </Link>
            </div>
          </dl>
        ) : (
          <p className="text-text-700">Aún no se ha vinculado un acto.</p>
        )}
        {puedeGestionar && cuenta.estado !== "CERRADA" && opciones ? (
          <div className="mt-4 flex flex-wrap items-end gap-3">
            <FormField label="Acto vigente" htmlFor="cuenta-vincular-acto" className="min-w-0 flex-1">
              <select
                id="cuenta-vincular-acto"
                className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                value={actoElegido}
                onChange={(e) => setActoElegido(e.target.value)}
              >
                <option value="">Seleccione un acto</option>
                {opciones.actos.map((acto) => (
                  <option key={acto.id} value={acto.id}>
                    {textoDeActo(acto)}
                  </option>
                ))}
              </select>
            </FormField>
            <Button disabled={enviando || !actoElegido} onClick={() => void vincularActo()}>
              Vincular acto
            </Button>
          </div>
        ) : null}
      </section>

      <AutorizadosCuenta
        cuenta={cuenta}
        opciones={opciones}
        alCambiar={aplicar}
        alFallar={alFallar}
      />

      <section aria-labelledby="acciones-cuenta-titulo" className="mb-8">
        <h2 id="acciones-cuenta-titulo" className="mb-4 text-lg font-semibold text-text-900">
          Acciones
        </h2>
        {cuenta.estado === "CERRADA" ? (
          <p className="text-text-700">Una cuenta cerrada no se reabre.</p>
        ) : null}
        <div className="flex flex-wrap gap-2">
          {puedeGestionar && cuenta.estado === "BORRADOR" ? (
            <Button variant="secondary" onClick={abrirPanelEdicion}>
              Editar borrador
            </Button>
          ) : null}
          {puedeActivar && cuenta.estado === "BORRADOR" ? (
            <AsyncButton variant="primary" disabled={enviando} onClick={activarCuenta}>
              Activar cuenta
            </AsyncButton>
          ) : null}
          {puedeActivar && cuenta.estado === "VIGENTE" ? (
            <Button variant="secondary" onClick={() => abrirPanelMotivo("inactivar")}>
              Inactivar cuenta
            </Button>
          ) : null}
          {puedeActivar && cuenta.estado === "INACTIVA" ? (
            <Button variant="secondary" onClick={() => abrirPanelMotivo("reactivar")}>
              Reactivar cuenta
            </Button>
          ) : null}
          {puedeActivar && (cuenta.estado === "VIGENTE" || cuenta.estado === "INACTIVA") ? (
            <Button variant="secondary" onClick={() => abrirPanelMotivo("cerrar")}>
              Cerrar cuenta
            </Button>
          ) : null}
        </div>
      </section>

      {panelEdicion}
      {panelMotivo}

      <section aria-labelledby="historia-cuenta-titulo">
        <h2 id="historia-cuenta-titulo" className="mb-4 text-lg font-semibold text-text-900">
          Historia
        </h2>
        <div
          className="relative overflow-x-auto"
          tabIndex={0}
          role="region"
          aria-label="Tabla de historia de la cuenta"
        >
          <table className="w-full border-collapse text-left">
            <caption className="sr-only">Historia de la cuenta</caption>
            <thead>
              <tr className="border-b border-border-subtle">
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                  Fecha
                </th>
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                  Cambio
                </th>
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                  Usuario
                </th>
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                  Detalle
                </th>
              </tr>
            </thead>
            <tbody>
              {cuenta.historia.map((h, indice) => {
                const campos = Array.isArray(h.detalle?.campos)
                  ? (h.detalle.campos as unknown[]).map(String).join(", ")
                  : null;
                const motivoHistoria =
                  typeof h.detalle?.motivo === "string" ? h.detalle.motivo : null;
                const cargoCodigo =
                  typeof h.detalle?.cargo_codigo === "string" ? h.detalle.cargo_codigo : null;
                const actoNumero =
                  typeof h.detalle?.acto_numero === "string" ? h.detalle.acto_numero : null;
                const detalleTexto = motivoHistoria
                  ? motivoHistoria
                  : campos
                    ? campos
                    : cargoCodigo
                      ? cargoCodigo
                      : actoNumero
                        ? actoNumero
                        : "—";
                return (
                  <tr
                    key={`${h.tipo}-${h.registrado_en}-${indice}`}
                    className="border-b border-border-subtle"
                  >
                    <td className="px-3 py-2 text-sm text-text-900">
                      {formatearFecha(h.registrado_en)}
                    </td>
                    <td className="px-3 py-2 text-sm text-text-900">
                      {ETIQUETAS_HISTORIA_CUENTA[h.tipo] ?? h.tipo}
                    </td>
                    <td className="px-3 py-2 text-sm text-text-900">
                      {h.registrado_por ?? "—"}
                    </td>
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
