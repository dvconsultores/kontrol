import { useMemo, useState } from "react";
import { Link } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import { descargarArchivo } from "@/api/descargas";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { Button } from "@/components/Button";
import { LoadingState } from "@/components/LoadingState";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { PageHeader } from "@/components/PageHeader";
import { PageContent } from "@/layout/PageContent";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import { CONSULTA_CAUSADOS, RUTA_CAUSADOS } from "./api";
import type { CausadosListado, CausadoResumen } from "./api";

interface Ejercicio {
  id: string;
  anio: string;
  moneda_funcional: string;
  estado: "BORRADOR" | "APROBADO" | "RECONDUCIDO" | "CERRADO";
  version: number;
}

interface EjerciciosRespuesta {
  items: Ejercicio[];
  total: number;
}

const ETIQUETAS_ESTADO: Record<CausadoResumen["estado"], string> = {
  BORRADOR: "Borrador",
  FORMALIZADO: "Formalizado",
  ANULADO: "Anulado",
};

const ESTADOS: Array<{
  valor: "" | CausadoResumen["estado"];
  etiqueta: string;
}> = [
  { valor: "", etiqueta: "Todos" },
  { valor: "BORRADOR", etiqueta: "Borrador" },
  { valor: "FORMALIZADO", etiqueta: "Formalizado" },
  { valor: "ANULADO", etiqueta: "Anulado" },
];

export function CausadosPage() {
  const { tiene } = useAutoridad();
  const puedeVer = tiene("gobierno_presupuesto:view", "empresa");
  const puedeCausar = tiene("gobierno_presupuesto:cause", "empresa");

  const ejerciciosQuery = useQuery({
    queryKey: ["gobierno", "presupuesto", "ejercicios"],
    queryFn: () => apiFetch<EjerciciosRespuesta>("/gobierno/presupuesto/ejercicios"),
    enabled: puedeVer,
  });

  const ejerciciosDisponibles = useMemo(
    () =>
      (ejerciciosQuery.data?.items ?? []).filter(
        (ejercicio) =>
          ejercicio.estado === "APROBADO" || ejercicio.estado === "RECONDUCIDO",
      ),
    [ejerciciosQuery.data],
  );

  const ejercicioPorDefecto = useMemo(() => {
    if (ejerciciosDisponibles.length === 0) return null;
    return ejerciciosDisponibles.reduce((mayor, ejercicio) =>
      Number(ejercicio.anio) > Number(mayor.anio) ? ejercicio : mayor,
    );
  }, [ejerciciosDisponibles]);

  const [ejercicioId, setEjercicioId] = useState<string>("");
  const ejercicioSeleccionado =
    ejerciciosDisponibles.find((ejercicio) => ejercicio.id === ejercicioId) ?? null;

  const [filtroEstado, setFiltroEstado] = useState<"" | CausadoResumen["estado"]>("");
  const [filtroDesde, setFiltroDesde] = useState("");
  const [filtroHasta, setFiltroHasta] = useState("");
  const [filtroBusqueda, setFiltroBusqueda] = useState("");

  const ejercicioActivo = ejercicioSeleccionado ?? ejercicioPorDefecto;

  const causadosQuery = useQuery({
    queryKey: [
      ...CONSULTA_CAUSADOS,
      ejercicioActivo?.id,
      filtroEstado,
      filtroDesde,
      filtroHasta,
      filtroBusqueda,
    ],
    queryFn: () => {
      const id = ejercicioActivo?.id ?? "";
      const parametros = new URLSearchParams();
      if (filtroEstado) parametros.set("estado", filtroEstado);
      if (filtroDesde) parametros.set("desde", filtroDesde);
      if (filtroHasta) parametros.set("hasta", filtroHasta);
      if (filtroBusqueda) parametros.set("q", filtroBusqueda);
      const query = parametros.toString();
      return apiFetch<CausadosListado>(
        `/gobierno/presupuesto/ejercicios/${id}/causados${query ? `?${query}` : ""}`,
      );
    },
    enabled: puedeVer && ejercicioActivo !== null,
  });

  async function descargarCsv() {
    if (!ejercicioActivo) return;
    const parametros = new URLSearchParams();
    if (filtroEstado) parametros.set("estado", filtroEstado);
    if (filtroDesde) parametros.set("desde", filtroDesde);
    if (filtroHasta) parametros.set("hasta", filtroHasta);
    if (filtroBusqueda) parametros.set("q", filtroBusqueda);
    const query = parametros.toString();
    await descargarArchivo(
      `/gobierno/presupuesto/ejercicios/${ejercicioActivo.id}/causados/reporte.csv${query ? `?${query}` : ""}`,
      `causados-${ejercicioActivo.anio}.csv`,
    );
  }

  if (!puedeVer) {
    return (
      <PageContent>
        <EmptyState
          title="Sin acceso"
          description="No tienes permisos para ver los causados."
        />
      </PageContent>
    );
  }

  if (ejerciciosQuery.isLoading) {
    return (
      <PageContent>
        <LoadingState rows={6} label="Cargando ejercicios…" />
      </PageContent>
    );
  }

  if (ejerciciosQuery.isError) {
    return (
      <PageContent>
        <ErrorState
          title="No se pudieron cargar los ejercicios"
          message={ejerciciosQuery.error.message}
          onRetry={() => void ejerciciosQuery.refetch()}
        />
      </PageContent>
    );
  }

  if (ejerciciosDisponibles.length === 0) {
    return (
      <PageContent>
        <PageHeader
          title="Causados"
          description="Obligaciones exigibles registradas contra compromisos vigentes. No son pagos ni asientos contables."
        />
        <EmptyState
          title="No hay ejercicios aprobados"
          description="Para registrar causados debe existir al menos un ejercicio aprobado o reconducido."
        />
      </PageContent>
    );
  }

  const valorEjercicio = ejercicioSeleccionado?.id ?? ejercicioPorDefecto?.id ?? "";

  return (
    <PageContent>
      <PageHeader
        title="Causados"
        description="Obligaciones exigibles registradas contra compromisos vigentes. No son pagos ni asientos contables."
        actions={
          puedeCausar && ejercicioActivo ? (
            <Link
              to={`${RUTA_CAUSADOS}/nuevo?ejercicio=${ejercicioActivo.id}`}
              className="inline-flex items-center rounded-md bg-brand-700 px-3 py-2 text-sm font-medium text-white hover:bg-brand-800"
            >
              Nuevo causado
            </Link>
          ) : undefined
        }
      />

      <div className="flex flex-col gap-4 py-4 md:flex-row md:flex-wrap md:items-end">
        <label className="flex w-full flex-col gap-1 text-sm md:w-auto">
          Ejercicio
          <select
            className="rounded-md border border-slate-300 bg-white px-3 py-2"
            value={valorEjercicio}
            onChange={(evento) => setEjercicioId(evento.target.value)}
          >
            {ejerciciosDisponibles.map((ejercicio) => (
              <option key={ejercicio.id} value={ejercicio.id}>
                {ejercicio.anio}
              </option>
            ))}
          </select>
        </label>

        <label className="flex w-full flex-col gap-1 text-sm md:w-auto">
          Estado
          <select
            className="rounded-md border border-slate-300 bg-white px-3 py-2"
            value={filtroEstado}
            onChange={(evento) =>
              setFiltroEstado(evento.target.value as typeof filtroEstado)
            }
          >
            {ESTADOS.map((estado) => (
              <option key={estado.valor} value={estado.valor}>
                {estado.etiqueta}
              </option>
            ))}
          </select>
        </label>

        <label className="flex w-full flex-col gap-1 text-sm md:w-auto">
          Desde
          <input
            type="date"
            className="w-full rounded-md border border-slate-300 px-3 py-2 md:w-auto"
            value={filtroDesde}
            onChange={(evento) => setFiltroDesde(evento.target.value)}
          />
        </label>

        <label className="flex w-full flex-col gap-1 text-sm md:w-auto">
          Hasta
          <input
            type="date"
            className="w-full rounded-md border border-slate-300 px-3 py-2 md:w-auto"
            value={filtroHasta}
            onChange={(evento) => setFiltroHasta(evento.target.value)}
          />
        </label>

        <label className="flex w-full min-w-48 flex-1 flex-col gap-1 text-sm">
          Búsqueda
          <input
            type="search"
            className="w-full rounded-md border border-slate-300 px-3 py-2"
            placeholder="Código, concepto, beneficiario…"
            value={filtroBusqueda}
            onChange={(evento) => setFiltroBusqueda(evento.target.value)}
          />
        </label>

        <Button
          type="button"
          variant="secondary"
          onClick={() => void descargarCsv()}
        >
          Descargar CSV
        </Button>
      </div>

      {causadosQuery.isLoading ? (
        <LoadingState rows={6} label="Cargando causados…" />
      ) : causadosQuery.isError ? (
        <ErrorState
          title="No se pudieron cargar los causados"
          message={causadosQuery.error.message}
          onRetry={() => void causadosQuery.refetch()}
        />
      ) : (causadosQuery.data?.items.length ?? 0) === 0 ? (
        <EmptyState
          title="Aún no hay causados en este ejercicio"
          description="Usa «Nuevo causado» para registrar el primero."
        />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <caption className="sr-only">Causados del ejercicio</caption>
            <thead>
              <tr className="border-b border-slate-200 text-left">
                <th scope="col" className="px-3 py-2 font-medium">
                  Código
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Fecha efectiva
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Compromiso
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Concepto
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Beneficiario
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Monto
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Pendiente del compromiso
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Estado
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Responsable
                </th>
              </tr>
            </thead>
            <tbody>
              {(causadosQuery.data?.items ?? []).map((causado) => (
                <tr
                  key={causado.id}
                  className="border-b border-slate-100 hover:bg-slate-50"
                >
                  <td className="px-3 py-2">
                    <Link
                      className="text-blue-700 underline"
                      to={`${RUTA_CAUSADOS}/${causado.id}`}
                    >
                      {causado.codigo ?? "Borrador"}
                    </Link>
                  </td>
                  <td className="px-3 py-2">
                    {formatearFechaDeNegocio(causado.fecha_efectiva)}
                  </td>
                  <td className="px-3 py-2">{causado.compromiso_codigo}</td>
                  <td className="px-3 py-2">{causado.concepto}</td>
                  <td className="px-3 py-2">{causado.beneficiario ?? "—"}</td>
                  <td className="px-3 py-2">
                    {causado.monto} {causado.moneda}
                  </td>
                  <td className="px-3 py-2">
                    {causado.pendiente_compromiso} {causado.moneda}
                  </td>
                  <td className="px-3 py-2">
                    {ETIQUETAS_ESTADO[causado.estado]}
                  </td>
                  <td className="px-3 py-2">
                    {causado.unidad} · {causado.responsable}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </PageContent>
  );
}
