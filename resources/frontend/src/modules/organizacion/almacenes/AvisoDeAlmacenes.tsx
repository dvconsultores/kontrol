/** Estado del selector de almacén: carga, error y vacío, para que un desplegable vacío nunca parezca completo. */
interface EstadoDeConsulta {
  isLoading: boolean;
  isError: boolean;
  data?: { items: unknown[] };
}

export function AvisoDeAlmacenes({ consulta }: { consulta: EstadoDeConsulta }): React.JSX.Element | null {
  if (consulta.isError) {
    return <p role="alert" className="text-sm text-danger-600">No fue posible cargar todos los almacenes.</p>;
  }
  if (consulta.isLoading) {
    return <p role="status" className="text-sm text-text-500">Cargando almacenes…</p>;
  }
  if (consulta.data && consulta.data.items.length === 0) {
    return <p role="status" className="text-sm text-text-500">Esta empresa no tiene almacenes.</p>;
  }
  return null;
}
