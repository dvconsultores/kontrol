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
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { formatearFecha } from "@/i18n";
import { ConflictoSoD, detalleDeConflictoSod } from "@/modules/gobierno/sod/ConflictoSoD";
import { formatMoney } from "@/lib/format";
import {
  CONSULTA_CAJA,
  ETIQUETAS_ESTADO_PROGRAMA,
  ETIQUETAS_ESTADO_VERSION,
  ETIQUETAS_HISTORIA_PROGRAMA,
  NOMBRES_DE_MES,
  type ProgramaDetalle,
} from "@/modules/gobierno/api";
import { DeclaracionesPrograma } from "./DeclaracionesPrograma";
import { LineasPrograma } from "./LineasPrograma";

type PanelActivo = "reprogramar" | "cerrar" | null;

const ETIQUETA_FALTANTE_ACTIVACION: Record<string, string> = {
  declaracion: "al menos una declaración de disponibilidad",
  linea: "al menos una línea de programación",
};

export function ProgramaPage(): React.JSX.Element {
  const { programaId } = useParams();
  const { activeCompanyId } = useCompany();
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();

  const puedeVer = tiene("gobierno_caja:view", "empresa");
  const puedeGestionar = tiene("gobierno_caja:manage", "empresa");
  const puedeActivar = tiene("gobierno_caja:activate", "empresa");

  const [numeroVista, setNumeroVista] = useState<number | null>(null);

  const claveDetalle = [
    ...CONSULTA_CAJA,
    "programa",
    programaId,
    numeroVista,
    activeCompanyId,
  ];

  const consultaDetalle = useQuery({
    queryKey: claveDetalle,
    queryFn: () =>
      apiFetch<ProgramaDetalle>(
        `/gobierno/tesoreria/programas/${programaId}${
          numeroVista !== null ? `?version=${numeroVista}` : ""
        }`,
      ),
    enabled: Boolean(activeCompanyId && programaId && puedeVer),
    retry: false,
  });

  const [panel, setPanel] = useState<PanelActivo>(null);
  const [enviando, setEnviando] = useState(false);
  const [motivo, setMotivo] = useState("");
  const [conflictoSod, setConflictoSod] = useState<ReturnType<typeof detalleDeConflictoSod>>(null);
  const [alerta, setAlerta] = useState<string | null>(null);

  const recargar = () => {
    void queryClient.invalidateQueries({ queryKey: [...CONSULTA_CAJA] });
  };

  const aplicar = (programa: ProgramaDetalle) => {
    queryClient.setQueryData(claveDetalle, programa);
    void queryClient.invalidateQueries({ queryKey: [...CONSULTA_CAJA] });
    setAlerta(null);
  };

  const alFallar = (e: unknown) => {
    const detalleConflicto = detalleDeConflictoSod(e);
    if (detalleConflicto) {
      setConflictoSod(detalleConflicto);
      return;
    }
    if (e instanceof ApiError && e.status === 409 && e.code === "GOV_CASH_PROGRAM_STALE") {
      setAlerta("El programa cambió desde que lo abrió. Se recargaron los datos; revise y vuelva a intentarlo.");
      recargar();
      return;
    }
    if (e instanceof ApiError && e.status === 409 && e.code === "GOV_CASH_PROGRAM_NOT_READY") {
      const faltan = Array.isArray(e.details?.faltan) ? (e.details.faltan as string[]) : [];
      const textoFaltantes = faltan
        .map((f) => ETIQUETA_FALTANTE_ACTIVACION[f] ?? f)
        .join(", ");
      setAlerta(`Para continuar el programa necesita: ${textoFaltantes}.`);
      return;
    }
    if (e instanceof ApiError) {
      setAlerta(e.message);
      return;
    }
    setAlerta("No fue posible completar la operación");
  };

  const escribirPrograma = async (
    ruta: string,
    method: "POST",
    body: Record<string, unknown>,
  ) => {
    try {
      const nuevoPrograma = await apiFetch<ProgramaDetalle>(ruta, {
        method,
        body,
        ifMatch: String(consultaDetalle.data?.version),
      });
      aplicar(nuevoPrograma);
      return nuevoPrograma;
    } catch (e) {
      alFallar(e);
      throw e;
    }
  };

  const cabeceraSinDetalle = (
    <PageHeader
      crumbs={[
        { label: "Gobierno" },
        { label: "Tesorería" },
        { label: "Programación financiera", to: "/gobierno/tesoreria/programacion" },
      ]}
      title="Programa financiero"
    />
  );

  if (consultaDetalle.isLoading && puedeVer) {
    return (
      <PageContent>
        {cabeceraSinDetalle}
        <LoadingState label="Cargando programa…" />
      </PageContent>
    );
  }

  if (!puedeVer) {
    return (
      <PageContent>
        {cabeceraSinDetalle}
        <EmptyState title="Sin acceso" description="No tiene permiso para ver este programa." />
      </PageContent>
    );
  }

  if (consultaDetalle.isError) {
    const error = consultaDetalle.error;
    if (error instanceof ApiError && error.status === 403) {
      return (
        <PageContent>
          {cabeceraSinDetalle}
          <EmptyState title="Sin acceso" description="No tiene permiso para ver este programa." />
        </PageContent>
      );
    }
    if (error instanceof ApiError && error.status === 404) {
      return (
        <PageContent>
          {cabeceraSinDetalle}
          <EmptyState
            title="Programa no encontrado"
            description="El programa no existe en este ente."
            action={<Link to="/gobierno/tesoreria/programacion">Volver a Programación financiera</Link>}
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        {cabeceraSinDetalle}
        <ErrorState
          message="No fue posible cargar el programa."
          onRetry={() => void consultaDetalle.refetch()}
        />
      </PageContent>
    );
  }

  const programa = consultaDetalle.data;
  if (!programa) {
    return (
      <PageContent>
        {cabeceraSinDetalle}
        <ErrorState
          message="No fue posible cargar el programa."
          onRetry={() => void consultaDetalle.refetch()}
        />
      </PageContent>
    );
  }

  const editable =
    programa.version_vista === programa.borrador_numero && puedeGestionar;

  const estadoEtiqueta = ETIQUETAS_ESTADO_PROGRAMA[programa.estado] ?? programa.estado;
  const esCerrado = programa.estado === "CERRADO";
  const esVigenteSinBorrador =
    programa.estado === "VIGENTE" && programa.borrador_numero === null;
  const hayBorrador = programa.borrador_numero !== null;
  const versionMostradaEsBorrador = programa.version_vista === programa.borrador_numero;
  const versionMostradaEsVigente = programa.version_vista === programa.version_vigente;
  const soloLectura = !versionMostradaEsVigente && !versionMostradaEsBorrador;

  const abrirPanelMotivo = (tipo: Exclude<PanelActivo, null>) => {
    setAlerta(null);
    setMotivo("");
    setPanel(tipo);
  };

  const cerrarPanel = () => {
    setPanel(null);
    setAlerta(null);
    setMotivo("");
  };

  const esMotivoValido = motivo.trim().length >= 10 && motivo.length <= 500;

  const activarVersion = async () => {
    if (enviando) return;
    setEnviando(true);
    try {
      await escribirPrograma(
        `/gobierno/tesoreria/programas/${programa.id}/activar`,
        "POST",
        {},
      );
      notify({ type: "success", title: "Versión activada" });
    } catch {
      // el error ya fue manejado
    } finally {
      setEnviando(false);
    }
  };

  const reprogramar = async () => {
    if (enviando || !esMotivoValido) return;
    setEnviando(true);
    try {
      const nuevoPrograma = await escribirPrograma(
        `/gobierno/tesoreria/programas/${programa.id}/reprogramar`,
        "POST",
        { motivo },
      );
      if (nuevoPrograma.borrador_numero !== null) {
        setNumeroVista(nuevoPrograma.borrador_numero);
      }
      cerrarPanel();
      notify({ type: "success", title: "Reprogramación iniciada" });
    } catch {
      // el error ya fue manejado
    } finally {
      setEnviando(false);
    }
  };

  const descartarBorrador = async () => {
    if (enviando) return;
    setEnviando(true);
    try {
      await escribirPrograma(
        `/gobierno/tesoreria/programas/${programa.id}/descartar`,
        "POST",
        {},
      );
      setNumeroVista(null);
      notify({ type: "success", title: "Borrador descartado" });
    } catch {
      // el error ya fue manejado
    } finally {
      setEnviando(false);
    }
  };

  const cerrarPrograma = async () => {
    if (enviando || !esMotivoValido) return;
    setEnviando(true);
    try {
      await escribirPrograma(
        `/gobierno/tesoreria/programas/${programa.id}/cerrar`,
        "POST",
        { motivo },
      );
      cerrarPanel();
      notify({ type: "success", title: "Programa cerrado" });
    } catch {
      // el error ya fue manejado
    } finally {
      setEnviando(false);
    }
  };

  const alertaRender = alerta ? (
    <div role="alert" className="mb-4 rounded-md border border-error-300 bg-error-50 p-3 text-error-800">
      {alerta}
    </div>
  ) : null;

  const panelMotivo =
    panel === "reprogramar" || panel === "cerrar" ? (
      <section
        aria-labelledby={`${panel}-programa-titulo`}
        className="mb-8 rounded-lg border border-border-subtle p-4"
      >
        <h2 id={`${panel}-programa-titulo`} className="mb-4 text-lg font-semibold text-text-900">
          {panel === "reprogramar" ? "Reprogramar" : "Cerrar programa"}
        </h2>
        <FormField
          label="Motivo"
          htmlFor={`programa-${panel}-motivo`}
          required
        >
          <textarea
            id={`programa-${panel}-motivo`}
            className="min-h-24 w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
            minLength={10}
            maxLength={500}
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
          />
          {!esMotivoValido && motivo.length > 0 ? (
            <p className="mt-1 text-sm text-danger-600">
              El motivo debe tener entre 10 y 500 caracteres.
            </p>
          ) : null}
        </FormField>
        <div className="mt-4 flex gap-2">
          <AsyncButton
            variant="primary"
            disabled={!esMotivoValido || enviando}
            onClick={panel === "reprogramar" ? reprogramar : cerrarPrograma}
          >
            Confirmar {panel === "reprogramar" ? "reprogramación" : "cierre"}
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
        crumbs={[
          { label: "Gobierno" },
          { label: "Tesorería" },
          { label: "Programación financiera", to: "/gobierno/tesoreria/programacion" },
        ]}
        title={`Programa ${programa.codigo}`}
      />

      <p className="mb-6 text-sm text-text-700">
        {estadoEtiqueta}
        {soloLectura ? " · solo lectura" : ""}
      </p>

      <p role="note" className="mb-4 rounded-md border border-border-subtle bg-surface-50 p-3 text-sm text-text-700">
        Disponibilidad de caja proyectada. No es disponibilidad presupuestaria ni saldo bancario.
      </p>

      {alertaRender}

      {conflictoSod ? (
        <ConflictoSoD detalle={conflictoSod} onCerrar={() => setConflictoSod(null)} />
      ) : null}

      <section aria-labelledby="datos-programa-titulo" className="mb-8">
        <h2 id="datos-programa-titulo" className="mb-4 text-lg font-semibold text-text-900">
          Datos del programa
        </h2>
        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <dt className="text-sm font-medium text-text-700">Ejercicio</dt>
            <dd className="mt-1 text-text-900">{programa.ejercicio}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Moneda</dt>
            <dd className="mt-1 text-text-900">{programa.moneda}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Mes inicial</dt>
            <dd className="mt-1 text-text-900">
              {NOMBRES_DE_MES[programa.mes_inicial - 1] ?? programa.mes_inicial}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Versión vigente</dt>
            <dd className="mt-1 text-text-900">{programa.version_vigente ?? '—'}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Versión mostrada</dt>
            <dd className="mt-1 text-text-900">{programa.version_vista}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Disponibilidad inicial</dt>
            <dd className="mt-1 text-text-900">{formatMoney(programa.disponibilidad_inicial)}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Registrado por</dt>
            <dd className="mt-1 text-text-900">{programa.registrado_por ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Registrado en</dt>
            <dd className="mt-1 text-text-900">{formatearFecha(programa.registrado_en)}</dd>
          </div>
        </dl>
      </section>

      {hayBorrador && !versionMostradaEsBorrador ? (
        <div className="mb-6 flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => setNumeroVista(programa.borrador_numero)}>
            Trabajar en el borrador {programa.borrador_numero}
          </Button>
        </div>
      ) : null}

      {soloLectura ? (
        <div role="note" className="mb-4 rounded-md border border-border-subtle bg-surface-50 p-3 text-sm text-text-700">
          Esta versión es de solo lectura.
        </div>
      ) : null}

      <DeclaracionesPrograma
        programa={programa}
        editable={editable}
        onCambio={() => {
          void queryClient.invalidateQueries({ queryKey: [...CONSULTA_CAJA] });
        }}
      />

      <LineasPrograma
        programa={programa}
        editable={editable}
        onCambio={() => {
          void queryClient.invalidateQueries({ queryKey: [...CONSULTA_CAJA] });
        }}
      />

      <section aria-labelledby="disponibilidad-mensual-titulo" className="mb-8">
        <h2 id="disponibilidad-mensual-titulo" className="mb-4 text-lg font-semibold text-text-900">
          Disponibilidad mensual
        </h2>
        <div
          className="relative overflow-x-auto"
          tabIndex={0}
          role="region"
          aria-label="Tabla de disponibilidad mensual del programa"
        >
          <table className="w-full border-collapse text-left">
            <caption className="sr-only">
              Disponibilidad mensual del programa en {programa.moneda}
            </caption>
            <thead>
              <tr className="border-b border-border-subtle">
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                  Mes
                </th>
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                  Inicial
                </th>
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                  Ingresos
                </th>
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                  Desembolsos
                </th>
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                  Final
                </th>
              </tr>
            </thead>
            <tbody>
              {programa.meses.map((mes) => (
                <tr key={mes.mes} className="border-b border-border-subtle">
                  <td className="px-3 py-2 text-sm text-text-900">
                    {NOMBRES_DE_MES[mes.mes - 1] ?? mes.mes}
                    {mes.deficit ? (
                      <>
                        {" "}
                        <span className="font-medium text-danger-600">Déficit proyectado</span>
                      </>
                    ) : null}
                  </td>
                  <td className="px-3 py-2 text-sm text-text-900">{formatMoney(mes.inicial)}</td>
                  <td className="px-3 py-2 text-sm text-text-900">{formatMoney(mes.ingresos)}</td>
                  <td className="px-3 py-2 text-sm text-text-900">{formatMoney(mes.desembolsos)}</td>
                  <td className="px-3 py-2 text-sm text-text-900">{formatMoney(mes.final)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {programa.hay_deficit ? (
          <p role="note" className="mt-4 rounded-md border border-border-subtle bg-surface-50 p-3 text-sm text-text-700">
            El programa puede activarse igualmente.
          </p>
        ) : null}
      </section>

      <section aria-labelledby="acciones-programa-titulo" className="mb-8">
        <h2 id="acciones-programa-titulo" className="mb-4 text-lg font-semibold text-text-900">
          Acciones
        </h2>
        {esCerrado ? <p className="text-text-700">Un programa cerrado no se reabre.</p> : null}
        <div className="flex flex-wrap gap-2">
          {puedeActivar && hayBorrador && !esCerrado ? (
            <AsyncButton variant="primary" disabled={enviando} onClick={activarVersion}>
              Activar versión
            </AsyncButton>
          ) : null}
          {puedeGestionar && esVigenteSinBorrador && !esCerrado ? (
            <Button variant="secondary" onClick={() => abrirPanelMotivo("reprogramar")}>
              Reprogramar
            </Button>
          ) : null}
          {puedeGestionar && hayBorrador && !esCerrado ? (
            <AsyncButton variant="secondary" disabled={enviando} onClick={() => descartarBorrador()}>
              Descartar borrador
            </AsyncButton>
          ) : null}
          {puedeActivar && esVigenteSinBorrador && !esCerrado ? (
            <Button variant="secondary" onClick={() => abrirPanelMotivo("cerrar")}>
              Cerrar programa
            </Button>
          ) : null}
        </div>
      </section>

      {panelMotivo}

      <section aria-labelledby="versiones-programa-titulo" className="mb-8">
        <h2 id="versiones-programa-titulo" className="mb-4 text-lg font-semibold text-text-900">
          Versiones
        </h2>
        <div
          className="relative overflow-x-auto"
          tabIndex={0}
          role="region"
          aria-label="Tabla de versiones del programa"
        >
          <table className="w-full border-collapse text-left">
            <caption className="sr-only">Versiones del programa</caption>
            <thead>
              <tr className="border-b border-border-subtle">
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                  Número
                </th>
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                  Estado
                </th>
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                  Motivo
                </th>
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                  Activada por
                </th>
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                  Activada en
                </th>
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                  <span className="sr-only">Acciones</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {programa.versiones.map((version) => (
                <tr key={version.numero} className="border-b border-border-subtle">
                  <td className="px-3 py-2 text-sm text-text-900">{version.numero}</td>
                  <td className="px-3 py-2 text-sm text-text-900">
                    {ETIQUETAS_ESTADO_VERSION[version.estado] ?? version.estado}
                  </td>
                  <td className="px-3 py-2 text-sm text-text-900">{version.motivo ?? "—"}</td>
                  <td className="px-3 py-2 text-sm text-text-900">
                    {version.activada_por ?? "—"}
                  </td>
                  <td className="px-3 py-2 text-sm text-text-900">
                    {version.activada_en ? formatearFecha(version.activada_en) : "—"}
                  </td>
                  <td className="px-3 py-2 text-sm text-text-900">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setNumeroVista(version.numero)}
                    >
                      Ver versión {version.numero}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="historia-programa-titulo">
        <h2 id="historia-programa-titulo" className="mb-4 text-lg font-semibold text-text-900">
          Historia
        </h2>
        <div
          className="relative overflow-x-auto"
          tabIndex={0}
          role="region"
          aria-label="Tabla de historia del programa"
        >
          <table className="w-full border-collapse text-left">
            <caption className="sr-only">Historia del programa</caption>
            <thead>
              <tr className="border-b border-border-subtle">
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                  Fecha
                </th>
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                  Autor
                </th>
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                  Acción
                </th>
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                  Versión
                </th>
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                  Motivo
                </th>
              </tr>
            </thead>
            <tbody>
              {programa.historia.map((h, indice) => {
                const motivoHistoria =
                  typeof h.detalle?.motivo === "string" ? h.detalle.motivo : null;
                return (
                  <tr
                    key={`${h.tipo}-${h.registrado_en}-${indice}`}
                    className="border-b border-border-subtle"
                  >
                    <td className="px-3 py-2 text-sm text-text-900">
                      {formatearFecha(h.registrado_en)}
                    </td>
                    <td className="px-3 py-2 text-sm text-text-900">
                      {h.registrado_por ?? "—"}
                    </td>
                    <td className="px-3 py-2 text-sm text-text-900">
                      {ETIQUETAS_HISTORIA_PROGRAMA[h.tipo] ?? h.tipo}
                    </td>
                    <td className="px-3 py-2 text-sm text-text-900">{h.version_numero}</td>
                    <td className="px-3 py-2 text-sm text-text-900">
                      {motivoHistoria ?? "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {esCerrado ? (
        <section aria-labelledby="cierre-programa-titulo" className="mb-8">
          <h2 id="cierre-programa-titulo" className="mb-4 text-lg font-semibold text-text-900">
            Datos del cierre
          </h2>
          <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-sm font-medium text-text-700">Cerrado por</dt>
              <dd className="mt-1 text-text-900">{programa.cerrado_por ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-text-700">Cerrado en</dt>
              <dd className="mt-1 text-text-900">
                {programa.cerrado_en ? formatearFecha(programa.cerrado_en) : "—"}
              </dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-sm font-medium text-text-700">Motivo de cierre</dt>
              <dd className="mt-1 text-text-900">{programa.motivo_cierre ?? "—"}</dd>
            </div>
          </dl>
        </section>
      ) : null}
    </PageContent>
  );
}
