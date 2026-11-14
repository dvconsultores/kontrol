export type LimiteAutoridad = {
  cargo: string | null;
  tipo_limite: "SIN_LIMITE" | "MONTO" | null;
  monto: string | null;
  moneda: string | null;
  etiqueta: string;
};

export type ControlMonto = {
  offer_id: string;
  oferta: string;
  estado: string;
  estado_etiqueta: string;
  permite: boolean;
  mensaje: string;
  cargo: string | null;
  limite: LimiteAutoridad;
  monto_oferta: { total_con_tributos: string; moneda: string } | null;
};

export function ControlLimiteAutoridad({ control }: { control: ControlMonto }) {
  return (
    <section
      aria-labelledby="control-limite-titulo"
      className="mt-4 min-w-0 rounded-md border border-border-subtle bg-white p-3"
    >
      <h3 id="control-limite-titulo" className="text-sm font-semibold text-text-900">
        Control del límite de autoridad
      </h3>
      <dl className="mt-2 grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="min-w-0">
          <dt className="text-xs font-medium text-text-600">Monto declarado de la oferta</dt>
          <dd className="break-words text-sm text-text-900">
            {control.monto_oferta?.total_con_tributos ?? "No declarado"}
          </dd>
        </div>
        <div className="min-w-0">
          <dt className="text-xs font-medium text-text-600">Moneda</dt>
          <dd className="break-words text-sm text-text-900">
            {control.monto_oferta?.moneda ?? "—"}
          </dd>
        </div>
        <div className="min-w-0">
          <dt className="text-xs font-medium text-text-600">Autoridad efectiva</dt>
          <dd className="break-words text-sm text-text-900">
            {control.cargo ?? "Cargo del acto"}
          </dd>
        </div>
        <div className="min-w-0">
          <dt className="text-xs font-medium text-text-600">Límite de aprobación</dt>
          <dd className="break-words text-sm text-text-900">{control.limite.etiqueta}</dd>
        </div>
        <div className="min-w-0">
          <dt className="text-xs font-medium text-text-600">Resultado de validación</dt>
          <dd className="break-words text-sm text-text-900">{control.estado_etiqueta}</dd>
        </div>
      </dl>
      <p
        className={
          control.permite
            ? "mt-2 break-words text-sm text-text-900"
            : "mt-2 break-words text-sm font-medium text-red-700"
        }
      >
        {control.mensaje}
      </p>
    </section>
  );
}
