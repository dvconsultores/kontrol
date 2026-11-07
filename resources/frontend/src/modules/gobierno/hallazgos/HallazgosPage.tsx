import { useState } from "react";
import { Link, useSearchParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";

import { apiFetch, ApiError } from "@/api/client";
import { descargarArchivo } from "@/api/descargas";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { AsyncButton } from "@/components/AsyncButton";
import { TextInput } from "@/components/TextInput";
import { FormField } from "@/components/FormField";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { hoyDeNegocio } from "@/lib/fecha-de-negocio";
import { formatearFecha } from "@/i18n";
import {
  CONSULTA_HALLAZGOS,
  POR_PAGINA_HALLAZGOS,
  consultaDeHallazgos,
  contextoDeHallazgos,
  ETIQUETA_ESTADO_HALLAZGO,
  ETIQUETAS_RIESGO_CIERRE,
  ETIQUETA_RIESGO_HALLAZGO,
  ETIQUETA_ORIGEN_HALLAZGO,
  type EstadoHallazgo,
  type RiesgoHallazgo,
  type OrigenHallazgo,
  type FiltrosHallazgos,
  type HallazgosListado,
} from "@/modules/gobierno/api";

const CLASE_SELECT =
  "h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600";

const OPCIONES_ESTADO = Object.entries(ETIQUETA_ESTADO_HALLAZGO) as [
  EstadoHallazgo,
  string,
][];
const OPCIONES_RIESGO = Object.entries(ETIQUETA_RIESGO_HALLAZGO) as [
  RiesgoHallazgo,
  string,
][];
const OPCIONES_ORIGEN = Object.entries(ETIQUETA_ORIGEN_HALLAZGO) as [
  OrigenHallazgo,
  string,
][];

export function HallazgosPage(): React.JSX.Element {
  const [params, setParams] = useSearchParams();
  return (
    <ListaDeHallazgos
      key={params.toString()}
      contexto={contextoDeHallazgos(params)}
      alQuitarContexto={() => setParams({})}
    />
  );
}

function ListaDeHallazgos({
  contexto,
  alQuitarContexto,
}: {
  contexto: Pick<FiltrosHallazgos, "abiertos" | "riesgo_minimo">;
  alQuitarContexto: () => void;
}): React.JSX.Element {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const { notify } = useNotifications();

  const [estado, setEstado] = useState<EstadoHallazgo | "">("");
  const [riesgo, setRiesgo] = useState<RiesgoHallazgo | "">("");
  const [origen, setOrigen] = useState<OrigenHallazgo | "">("");
  const [texto, setTexto] = useState("");
  const [soloVencidas, setSoloVencidas] = useState(false);

  const [filtrosAplicados, setFiltrosAplicados] = useState<FiltrosHallazgos>(
    {},
  );
  const [pagina, setPagina] = useState(1);
  const filtrosEfectivos: FiltrosHallazgos = { ...filtrosAplicados, ...contexto };
  const hayContexto = contexto.abiertos === true || contexto.riesgo_minimo !== undefined;

  const puedeVer = tiene("gobierno_hallazgos:view", "empresa");
  const puedeGestionar = tiene("gobierno_hallazgos:manage", "empresa");

  const consultaHallazgos = useQuery({
    queryKey: [
      ...CONSULTA_HALLAZGOS,
      activeCompanyId,
      filtrosEfectivos,
      pagina,
    ],
    queryFn: () =>
      apiFetch<HallazgosListado>(
        `/gobierno/hallazgos${consultaDeHallazgos(filtrosEfectivos, {
          pagina,
          por_pagina: POR_PAGINA_HALLAZGOS,
        })}`,
      ),
    enabled: puedeVer && Boolean(activeCompanyId),
    retry: false,
  });

  const exportarCsv = async () => {
    try {
      await descargarArchivo(
        `/gobierno/hallazgos/exportar${consultaDeHallazgos(filtrosEfectivos)}`,
        `plan-acciones-${hoyDeNegocio()}.csv`,
      );
      notify({ type: "success", title: "Plan de acción exportado" });
    } catch {
      notify({ type: "error", title: "No fue posible exportar" });
    }
  };

  const aplicarFiltros = (evento: React.FormEvent) => {
    evento.preventDefault();
    setFiltrosAplicados({
      estado: estado || undefined,
      riesgo: riesgo || undefined,
      origen: origen || undefined,
      texto: texto.trim() || undefined,
      vencidas: soloVencidas || undefined,
    });
    setPagina(1);
  };

  const limpiarFiltros = () => {
    setEstado("");
    setRiesgo("");
    setOrigen("");
    setTexto("");
    setSoloVencidas(false);
    setFiltrosAplicados({});
    setPagina(1);
    if (hayContexto) alQuitarContexto();
  };

  const aplicarIndicador = (nuevosFiltros: FiltrosHallazgos) => {
    const siguientesFiltros = { ...filtrosAplicados, ...nuevosFiltros };
    setFiltrosAplicados(siguientesFiltros);
    setPagina(1);
  };

  const crumbs = [{ label: "Gobierno" }, { label: "Hallazgos" }];

  const cabecera = (
    <PageHeader
      crumbs={crumbs}
      title="Hallazgos y acciones correctivas"
      description="Hallazgos de Control Interno, sus recomendaciones y el plan de acción correctiva con responsable y fecha objetivo."
    />
  );

  if (!puedeVer) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para ver los hallazgos y acciones correctivas."
        />
      </PageContent>
    );
  }

  if (consultaHallazgos.isLoading) {
    return (
      <PageContent>
        {cabecera}
        <LoadingState label="Cargando hallazgos…" />
      </PageContent>
    );
  }

  if (consultaHallazgos.isError) {
    const error = consultaHallazgos.error;
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
            description="No tiene permiso para ver los hallazgos y acciones correctivas."
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        {cabecera}
        <ErrorState
          message="No fue posible cargar los hallazgos."
          onRetry={() => void consultaHallazgos.refetch()}
        />
      </PageContent>
    );
  }

  if (!consultaHallazgos.data) {
    return (
      <PageContent>
        {cabecera}
        <ErrorState
          message="No fue posible cargar los hallazgos."
          onRetry={() => void consultaHallazgos.refetch()}
        />
      </PageContent>
    );
  }

  const accionesCabecera = (
    <div className="flex flex-wrap items-center gap-2">
      {puedeGestionar && (
        <Link
          to="/gobierno/hallazgos/nuevo"
          className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
        >
          Registrar hallazgo
        </Link>
      )}
      <AsyncButton onClick={exportarCsv} variant="secondary">
        <Download className="mr-2 h-4 w-4" aria-hidden="true" />
        Exportar plan (CSV)
      </AsyncButton>
    </div>
  );

  const tieneFiltrosActivos =
    hayContexto ||
    filtrosAplicados.estado !== undefined ||
    filtrosAplicados.riesgo !== undefined ||
    filtrosAplicados.origen !== undefined ||
    filtrosAplicados.texto !== undefined ||
    filtrosAplicados.vencidas === true;

  const resumen = consultaHallazgos.data.resumen;

  return (
    <PageContent>
      <PageHeader
        crumbs={crumbs}
        title="Hallazgos y acciones correctivas"
        description="Hallazgos de Control Interno, sus recomendaciones y el plan de acción correctiva con responsable y fecha objetivo."
        actions={accionesCabecera}
      />

      <section aria-labelledby="resumen-hallazgos-titulo" className="mb-8">
        <h2 id="resumen-hallazgos-titulo" className="sr-only">
          Resumen
        </h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <button
            type="button"
            aria-pressed={
              !filtrosAplicados.estado && !filtrosAplicados.vencidas
            }
            className="rounded-md border border-border-subtle bg-surface-0 p-4 text-left"
            onClick={() => aplicarIndicador({ estado: undefined, vencidas: undefined })}
          >
            <span className="block text-2xl font-semibold">
              {resumen.abiertos}
            </span>
            <span className="text-sm text-text-600">Abiertos</span>
          </button>
          <button
            type="button"
            aria-pressed={filtrosAplicados.vencidas === true}
            className="rounded-md border border-border-subtle bg-surface-0 p-4 text-left"
            onClick={() => aplicarIndicador({ vencidas: true })}
          >
            <span className="block text-2xl font-semibold">
              {resumen.acciones_vencidas}
            </span>
            <span className="text-sm text-text-600">Acciones vencidas</span>
          </button>
          <button
            type="button"
            aria-pressed={filtrosAplicados.estado === "EVIDENCIA_PRESENTADA"}
            className="rounded-md border border-border-subtle bg-surface-0 p-4 text-left"
            onClick={() =>
              aplicarIndicador({ estado: "EVIDENCIA_PRESENTADA" })
            }
          >
            <span className="block text-2xl font-semibold">
              {resumen.pendientes_verificacion}
            </span>
            <span className="text-sm text-text-600">
              Pendientes de verificación
            </span>
          </button>
          <button
            type="button"
            aria-pressed={filtrosAplicados.estado === "CERRADO"}
            className="rounded-md border border-border-subtle bg-surface-0 p-4 text-left"
            onClick={() => aplicarIndicador({ estado: "CERRADO" })}
          >
            <span className="block text-2xl font-semibold">
              {resumen.cerrados}
            </span>
            <span className="text-sm text-text-600">Cerrados</span>
          </button>
        </div>
      </section>

      <section aria-labelledby="filtros-hallazgos-titulo" className="mb-8">
        <h2 id="filtros-hallazgos-titulo" className="sr-only">
          Filtros
        </h2>
        {hayContexto && (
          <div role="status" className="mb-3 flex flex-wrap items-center gap-2 rounded-md border border-border-subtle p-3 text-sm text-text-700">
            <span>
              Filtro de cierre: hallazgos pendientes
              {contexto.riesgo_minimo !== undefined &&
                ` · riesgo ${ETIQUETAS_RIESGO_CIERRE[contexto.riesgo_minimo]}`}
            </span>
            <button
              type="button"
              onClick={alQuitarContexto}
              className="font-medium text-brand-700 underline"
            >
              Quitar filtro
            </button>
          </div>
        )}
        <form onSubmit={aplicarFiltros} className="mb-4">
          <div className="flex flex-wrap items-end gap-3">
            <FormField
              label="Estado"
              htmlFor="filtro-estado"
              className="min-w-40"
            >
              <select
                id="filtro-estado"
                className={CLASE_SELECT}
                value={estado}
                onChange={(e) => {
                  const valor = e.target.value;
                  setEstado(
                    valor === ""
                      ? ""
                      : (OPCIONES_ESTADO.find(([v]) => v === valor)?.[0] ?? ""),
                  );
                  setPagina(1);
                }}
              >
                <option value="">Todos</option>
                {OPCIONES_ESTADO.map(([valor, etiqueta]) => (
                  <option key={valor} value={valor}>
                    {etiqueta}
                  </option>
                ))}
              </select>
            </FormField>
            <FormField
              label="Riesgo"
              htmlFor="filtro-riesgo"
              className="min-w-40"
            >
              <select
                id="filtro-riesgo"
                className={CLASE_SELECT}
                value={riesgo}
                onChange={(e) => {
                  const valor = e.target.value;
                  setRiesgo(
                    valor === ""
                      ? ""
                      : (OPCIONES_RIESGO.find(([v]) => v === valor)?.[0] ?? ""),
                  );
                  setPagina(1);
                }}
              >
                <option value="">Todos</option>
                {OPCIONES_RIESGO.map(([valor, etiqueta]) => (
                  <option key={valor} value={valor}>
                    {etiqueta}
                  </option>
                ))}
              </select>
            </FormField>
            <FormField
              label="Origen"
              htmlFor="filtro-origen"
              className="min-w-40"
            >
              <select
                id="filtro-origen"
                className={CLASE_SELECT}
                value={origen}
                onChange={(e) => {
                  const valor = e.target.value;
                  setOrigen(
                    valor === ""
                      ? ""
                      : (OPCIONES_ORIGEN.find(([v]) => v === valor)?.[0] ?? ""),
                  );
                  setPagina(1);
                }}
              >
                <option value="">Todos</option>
                {OPCIONES_ORIGEN.map(([valor, etiqueta]) => (
                  <option key={valor} value={valor}>
                    {etiqueta}
                  </option>
                ))}
              </select>
            </FormField>
            <FormField
              label="Buscar"
              htmlFor="filtro-texto"
              className="min-w-56 flex-1"
            >
              <TextInput
                id="filtro-texto"
                value={texto}
                onChange={(e) => {
                  setTexto(e.target.value);
                  setPagina(1);
                }}
                placeholder="Código o título"
              />
            </FormField>
            <label className="flex items-center gap-2 text-sm text-text-700">
              <input
                type="checkbox"
                checked={soloVencidas}
                onChange={(e) => {
                  setSoloVencidas(e.target.checked);
                  setPagina(1);
                }}
              />
              Solo con acciones vencidas
            </label>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="submit"
              className="inline-flex h-10 items-center rounded-md bg-brand-600 px-4 text-sm font-medium text-white hover:bg-brand-700"
            >
              Buscar
            </button>
            <button
              type="button"
              onClick={limpiarFiltros}
              className="inline-flex h-10 items-center rounded-md border border-border-default px-4 text-sm font-medium text-text-700 hover:bg-surface-100"
            >
              Limpiar filtros
            </button>
          </div>
        </form>
      </section>

      {consultaHallazgos.data.total === 0 && !tieneFiltrosActivos ? (
        <EmptyState
          title="Aún no hay hallazgos registrados"
          description="Los hallazgos se registran desde el módulo de Gobierno."
        />
      ) : consultaHallazgos.data.total === 0 ? (
        <EmptyState title="Ningún hallazgo coincide con los filtros" />
      ) : (
        <>
          <div
            className="relative overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Tabla de hallazgos"
          >
            <table className="w-full min-w-[820px] border-collapse text-sm">
              <caption className="sr-only">
                Hallazgos de Control Interno
              </caption>
              <thead>
                <tr className="border-b border-border-default text-left text-text-600">
                  <th scope="col" className="px-3 py-2 font-medium">
                    Código
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Título
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Riesgo
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Estado
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Acciones
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Vencidas
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Origen
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Registrado
                  </th>
                </tr>
              </thead>
              <tbody>
                {consultaHallazgos.data.items.map((hallazgo) => (
                  <tr
                    key={hallazgo.id}
                    className="border-b border-border-subtle align-top"
                  >
                    <td className="px-3 py-2 text-text-900">
                      <Link
                        to={`/gobierno/hallazgos/${hallazgo.id}`}
                        className="font-medium text-brand-700 underline"
                        aria-label={`Abrir el hallazgo ${hallazgo.codigo}`}
                      >
                        {hallazgo.codigo}
                      </Link>
                    </td>
                    <td className="px-3 py-2 text-text-900">
                      {hallazgo.titulo}
                    </td>
                    <td className="px-3 py-2 text-text-700">
                      {ETIQUETA_RIESGO_HALLAZGO[hallazgo.riesgo]}
                    </td>
                    <td className="px-3 py-2 text-text-700">
                      {ETIQUETA_ESTADO_HALLAZGO[hallazgo.estado]}
                    </td>
                    <td className="px-3 py-2 text-text-700">
                      {hallazgo.acciones_total}
                    </td>
                    <td className="px-3 py-2 text-text-700">
                      {hallazgo.acciones_vencidas > 0
                        ? `${hallazgo.acciones_vencidas} vencidas`
                        : "—"}
                    </td>
                    <td className="px-3 py-2 text-text-700">
                      {ETIQUETA_ORIGEN_HALLAZGO[hallazgo.origen]}
                    </td>
                    <td className="px-3 py-2 text-text-700">
                      {formatearFecha(hallazgo.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {consultaHallazgos.data.total > POR_PAGINA_HALLAZGOS && (
            <div className="mt-4 flex items-center justify-between gap-3">
              <button
                type="button"
                disabled={pagina <= 1}
                onClick={() => setPagina((actual) => Math.max(1, actual - 1))}
                className="inline-flex h-10 items-center rounded-md border border-border-default px-4 text-sm font-medium text-text-700 hover:bg-surface-100 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Anterior
              </button>
              <p className="text-sm text-text-600">
                Página {pagina} de{" "}
                {Math.ceil(
                  consultaHallazgos.data.total / POR_PAGINA_HALLAZGOS,
                )}
              </p>
              <button
                type="button"
                disabled={
                  pagina >=
                  Math.ceil(
                    consultaHallazgos.data.total / POR_PAGINA_HALLAZGOS,
                  )
                }
                onClick={() => setPagina((actual) => actual + 1)}
                className="inline-flex h-10 items-center rounded-md border border-border-default px-4 text-sm font-medium text-text-700 hover:bg-surface-100 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Siguiente
              </button>
            </div>
          )}
        </>
      )}
    </PageContent>
  );
}
