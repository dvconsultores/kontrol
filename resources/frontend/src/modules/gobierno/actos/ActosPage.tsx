import { useCallback, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Plus } from "lucide-react";

import { apiFetch, ApiError } from "@/api/client";
import { descargarArchivo } from "@/api/descargas";
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
import { hoyDeNegocio, formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_ACTOS,
  ETIQUETA_CARACTER,
  ETIQUETA_ESTADO_ACTO,
  ETIQUETA_TIPO_ACTO,
  contextoDeActos,
  nombreDeActo,
  type Acto,
  type EstadoActo,
  type ListaActos,
} from "@/modules/gobierno/api";

import { ActoFormulario, type DatosActo } from "./ActoFormulario";

type Panel =
  | { tipo: "ninguno" }
  | {
      tipo: "crear";
    };

const CLASE_SELECT =
  "h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600";

export function ActosPage(): React.JSX.Element {
  const [params] = useSearchParams();
  const contexto = contextoDeActos(params);
  return <ListaDeActos key={params.toString()} anioInicial={contexto.anio} estadoInicial={contexto.estado} />;
}

function ListaDeActos({ anioInicial, estadoInicial }: { anioInicial?: number; estadoInicial?: EstadoActo }): React.JSX.Element {
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const anioActual = Number(hoyDeNegocio().slice(0, 4));
  const anios = useMemo(
    () => {
      const anios = Array.from({ length: 6 }, (_, i) => anioActual - i);
      if (anioInicial !== undefined && !anios.includes(anioInicial)) {
        anios.push(anioInicial);
      }
      return anios.sort((a, b) => b - a);
    },
    [anioActual, anioInicial],
  );

  const [anio, setAnio] = useState(anioInicial ?? anioActual);
  const [panel, setPanel] = useState<Panel>({ tipo: "ninguno" });
  const [erroresServidor, setErroresServidor] = useState<Record<string, string[]>>({});
  const [busqueda, setBusqueda] = useState("");
  const [tipo, setTipo] = useState("");
  const [caracter, setCaracter] = useState("");
  const [estado, setEstado] = useState<string>(estadoInicial ?? "");
  const [cargoCodigo, setCargoCodigo] = useState("");

  const puedeVer = tiene("gobierno_actos:view", "empresa");
  const puedeEditar = tiene("gobierno_actos:edit", "empresa");

  const consultaActos = useQuery({
    queryKey: [...CONSULTA_ACTOS, "lista", anio],
    queryFn: () => apiFetch<ListaActos>(`/gobierno/actos?anio=${anio}`),
    enabled: puedeVer,
    retry: false,
  });

  const recargar = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: [...CONSULTA_ACTOS] });
  }, [queryClient]);

  const manejarError = useCallback(
    (e: unknown) => {
      if (e instanceof ApiError) {
        if (e.status === 403) {
          notify({
            type: "error",
            title: "No tiene permiso para esta acción",
          });
          return;
        }
        if (e.status === 409 && e.code === "GOV_ACT_NUMBER_DUPLICATE") {
          setErroresServidor({ numero: [e.message] });
          return;
        }
        if (e.status === 422) {
          setErroresServidor(e.fieldErrors);
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
    [notify],
  );

  const actosFiltrados = useMemo(() => {
    const items = consultaActos.data?.items ?? [];
    const texto = busqueda.trim().toLowerCase();
    return items.filter((acto) => {
      if (
        texto &&
        !nombreDeActo(acto).toLowerCase().includes(texto) &&
        !acto.asunto.toLowerCase().includes(texto)
      ) {
        return false;
      }
      if (tipo && acto.tipo !== tipo) return false;
      if (caracter && acto.caracter !== caracter) return false;
      if (estado && acto.estado !== estado) return false;
      if (cargoCodigo && acto.cargo_codigo !== cargoCodigo) return false;
      return true;
    });
  }, [consultaActos.data?.items, busqueda, tipo, caracter, estado, cargoCodigo]);

  const opcionesCargos = useMemo(() => {
    const codigos = new Map<string, string>();
    for (const acto of consultaActos.data?.items ?? []) {
      if (!codigos.has(acto.cargo_codigo)) {
        codigos.set(
          acto.cargo_codigo,
          `${acto.cargo_codigo} — ${acto.cargo_denominacion}`,
        );
      }
    }
    return Array.from(codigos.entries())
      .map(([codigo, etiqueta]) => ({ codigo, etiqueta }))
      .sort((a, b) => a.etiqueta.localeCompare(b.etiqueta));
  }, [consultaActos.data?.items]);

  const guardarActo = async (datos: DatosActo) => {
    try {
      const creado = await apiFetch<Acto>("/gobierno/actos", {
        method: "POST",
        body: datos,
      });
      notify({ type: "success", title: "Acto registrado" });
      setPanel({ tipo: "ninguno" });
      setErroresServidor({});
      await queryClient.invalidateQueries({ queryKey: [...CONSULTA_ACTOS] });
      navigate(`/gobierno/actos/${creado.id}`);
    } catch (e) {
      manejarError(e);
    }
  };

  const exportarCsv = async () => {
    try {
      await descargarArchivo(
        `/gobierno/actos/exportar?anio=${anio}`,
        `actos-${anio}.csv`,
      );
      notify({ type: "success", title: "Actos exportados" });
    } catch {
      notify({ type: "error", title: "No fue posible exportar" });
    }
  };

  const abrirPanel = (nuevoPanel: Panel) => {
    setErroresServidor({});
    setPanel(nuevoPanel);
  };

  const crumbs = [
    { label: "Gobierno" },
    { label: "Actos administrativos", to: "/gobierno/actos" },
  ];
  const cabecera = (
    <PageHeader crumbs={crumbs} title="Actos administrativos" description="Registro de actos administrativos del año." />
  );

  if (!puedeVer) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para ver los actos administrativos."
        />
      </PageContent>
    );
  }

  if (consultaActos.isLoading) {
    return (
      <PageContent>
        {cabecera}
        <LoadingState label="Cargando actos administrativos…" />
      </PageContent>
    );
  }

  if (consultaActos.isError) {
    const error = consultaActos.error;
    if (
      error instanceof ApiError &&
      error.status === 403 &&
      error.code === "MODULE_NOT_ENTITLED"
    ) {
      return (
        <PageContent>
          {cabecera}
          <EmptyState
            title="Módulo no disponible"
            description="El módulo de Gobierno no está habilitado."
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
            description="No tiene permiso para ver los actos administrativos."
          />
        </PageContent>
      );
    }
    if (
      error instanceof ApiError &&
      error.status === 404 &&
      error.code === "GOV_ENTITY_NOT_FOUND"
    ) {
      return (
        <PageContent>
          {cabecera}
          <EmptyState
            title="Primero configure el ente"
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
    return (
      <PageContent>
        {cabecera}
        <ErrorState
          message="No fue posible cargar los actos."
          onRetry={() => void consultaActos.refetch()}
        />
      </PageContent>
    );
  }

  if (!consultaActos.data) {
    return (
      <PageContent>
        {cabecera}
        <ErrorState
          message="No fue posible cargar los actos."
          onRetry={recargar}
        />
      </PageContent>
    );
  }

  const actos = consultaActos.data.items;

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
          Registrar acto
        </Button>
      )}
    </div>
  );

  return (
    <PageContent>
      <PageHeader
        crumbs={crumbs}
        title="Actos administrativos"
        description="Registro de actos administrativos del año."
        actions={accionesCabecera}
      />

      <section aria-labelledby="actos-titulo" className="mb-8">
        <h2
          id="actos-titulo"
          className="mb-4 text-lg font-semibold text-text-900"
        >
          Actos
        </h2>

        <div className="mb-4 flex flex-wrap items-end gap-3">
          <FormField label="Año" htmlFor="filtro-anio" className="min-w-28">
            <select
              id="filtro-anio"
              className={CLASE_SELECT}
              value={anio}
              onChange={(e) => setAnio(Number(e.target.value))}
            >
              {anios.map((valor) => (
                <option key={valor} value={valor}>
                  {valor}
                </option>
              ))}
            </select>
          </FormField>
          <FormField
            label="Buscar"
            htmlFor="busqueda-acto"
            className="min-w-56 flex-1"
          >
            <TextInput
              id="busqueda-acto"
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              placeholder="Número o asunto"
            />
          </FormField>
          <FormField label="Tipo" htmlFor="filtro-tipo" className="min-w-40">
            <select
              id="filtro-tipo"
              className={CLASE_SELECT}
              value={tipo}
              onChange={(e) => setTipo(e.target.value)}
            >
              <option value="">Todos</option>
              {Object.entries(ETIQUETA_TIPO_ACTO).map(([valor, etiqueta]) => (
                <option key={valor} value={valor}>
                  {etiqueta}
                </option>
              ))}
            </select>
          </FormField>
          <FormField
            label="Carácter"
            htmlFor="filtro-caracter"
            className="min-w-40"
          >
            <select
              id="filtro-caracter"
              className={CLASE_SELECT}
              value={caracter}
              onChange={(e) => setCaracter(e.target.value)}
            >
              <option value="">Todos</option>
              {Object.entries(ETIQUETA_CARACTER).map(([valor, etiqueta]) => (
                <option key={valor} value={valor}>
                  {etiqueta}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Estado" htmlFor="filtro-estado" className="min-w-40">
            <select
              id="filtro-estado"
              className={CLASE_SELECT}
              value={estado}
              onChange={(e) => setEstado(e.target.value)}
            >
              <option value="">Todos</option>
              {Object.entries(ETIQUETA_ESTADO_ACTO).map(([valor, etiqueta]) => (
                <option key={valor} value={valor}>
                  {etiqueta}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Cargo" htmlFor="filtro-cargo" className="min-w-56">
            <select
              id="filtro-cargo"
              className={CLASE_SELECT}
              value={cargoCodigo}
              onChange={(e) => setCargoCodigo(e.target.value)}
            >
              <option value="">Todos</option>
              {opcionesCargos.map((cargo) => (
                <option key={cargo.codigo} value={cargo.codigo}>
                  {cargo.etiqueta}
                </option>
              ))}
            </select>
          </FormField>
        </div>

        <div className="relative overflow-x-auto">
          <table className="w-full min-w-[760px] border-collapse text-sm">
            <caption className="sr-only">
              Actos administrativos de {anio}
            </caption>
            <thead>
              <tr className="border-b border-border-default text-left text-text-600">
                <th scope="col" className="px-3 py-2 font-medium">
                  Acto
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Fecha
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Cargo
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Asunto
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Carácter
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Estado
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Eficacia
                </th>
              </tr>
            </thead>
            <tbody>
              {actosFiltrados.length === 0 ? (
                <tr>
                  <td
                    colSpan={7}
                    className="px-3 py-6 text-center text-text-600"
                  >
                    {actos.length === 0
                      ? `No hay actos registrados en ${anio}`
                      : "Ningún acto coincide con el filtro."}
                  </td>
                </tr>
              ) : (
                actosFiltrados.map((acto) => (
                  <tr
                    key={acto.id}
                    className="border-b border-border-subtle align-top"
                  >
                    <td className="px-3 py-2 text-text-900">
                      <Link
                        to={`/gobierno/actos/${acto.id}`}
                        className="font-medium text-brand-700 underline"
                        aria-label={`Abrir el acto ${nombreDeActo(acto)}`}
                      >
                        {nombreDeActo(acto)}
                      </Link>
                    </td>
                    <td className="px-3 py-2 text-text-700">
                      {formatearFechaDeNegocio(acto.fecha)}
                    </td>
                    <td className="px-3 py-2 text-text-700">
                      {acto.cargo_codigo} — {acto.cargo_denominacion}
                    </td>
                    <td className="px-3 py-2 text-text-700">{acto.asunto}</td>
                    <td className="px-3 py-2 text-text-700">
                      {ETIQUETA_CARACTER[acto.caracter]}
                    </td>
                    <td className="px-3 py-2 text-text-700">
                      {ETIQUETA_ESTADO_ACTO[acto.estado]}
                    </td>
                    <td className="px-3 py-2 text-text-700">
                      {acto.fecha_eficacia
                        ? formatearFechaDeNegocio(acto.fecha_eficacia)
                        : "—"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {panel.tipo === "crear" && (
          <div className="mt-6">
            <ActoFormulario
              key="crear-acto"
              modo="crear"
              onGuardar={guardarActo}
              onCancelar={() => setPanel({ tipo: "ninguno" })}
              erroresServidor={erroresServidor}
            />
          </div>
        )}
      </section>
    </PageContent>
  );
}
