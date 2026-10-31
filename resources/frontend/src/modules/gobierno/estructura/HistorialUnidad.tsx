import { useId } from "react";
import { useQuery } from "@tanstack/react-query";
import { ColumnDef } from "@tanstack/react-table";
import { apiFetch } from "@/api/client";
import { Button } from "@/components/Button";
import { DataTable } from "@/components/DataTable";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { formatearFecha } from "@/i18n";
import {
  CONSULTA_ESTRUCTURAS,
  ETIQUETA_ESTADO_UNIDAD,
  Unidad,
  VersionUnidad,
  VersionesUnidad,
} from "@/modules/gobierno/api";

export interface HistorialUnidadProps {
  ejercicio: number;
  unidad: Unidad;
  onCerrar: () => void;
}

const columnasHistorial: ColumnDef<VersionUnidad, unknown>[] = [
  {
    accessorKey: "version",
    header: "Versión",
    cell: ({ row }) => row.original.version,
  },
  {
    accessorKey: "estado",
    header: "Estado",
    cell: ({ row }) => ETIQUETA_ESTADO_UNIDAD[row.original.estado],
  },
  {
    id: "denominacion",
    header: "Denominación",
    cell: ({ row }) => String(row.original.datos.denominacion ?? "—"),
  },
  {
    accessorKey: "creado_en",
    header: "Fecha",
    cell: ({ row }) => formatearFecha(row.original.creado_en),
  },
  {
    accessorKey: "motivo",
    header: "Motivo",
    cell: ({ row }) => row.original.motivo ?? "—",
  },
  {
    accessorKey: "actor_id",
    header: "Responsable",
    cell: ({ row }) => row.original.actor_id?.slice(0, 8) ?? "—",
  },
];

export function HistorialUnidad(props: HistorialUnidadProps) {
  const { ejercicio, unidad, onCerrar } = props;

  const idTitulo = useId();

  const consulta = useQuery({
    queryKey: [...CONSULTA_ESTRUCTURAS, "versiones", unidad.id],
    queryFn: () =>
      apiFetch<VersionesUnidad>(
        `/gobierno/estructuras/${ejercicio}/unidades/${unidad.id}/versiones`,
      ),
    retry: false,
  });

  return (
    <section
      aria-labelledby={idTitulo}
      className="grid grid-cols-1 gap-4"
    >
      <h2 id={idTitulo} className="text-lg font-semibold">
        Historial de la unidad {unidad.codigo}
      </h2>

      {consulta.isLoading && <LoadingState label="Cargando historial…" />}

      {consulta.isError && (
        <ErrorState
          message="No se pudo cargar el historial de la unidad."
          onRetry={() => consulta.refetch()}
        />
      )}

      {consulta.isSuccess && (
        <DataTable
          columns={columnasHistorial}
          data={consulta.data.items}
          emptyTitle="Sin versiones"
          getRowId={(fila) => String(fila.version)}
        />
      )}

      <div className="flex flex-wrap gap-3">
        <Button variant="secondary" type="button" onClick={onCerrar}>
          Cerrar historial
        </Button>
      </div>
    </section>
  );
}
