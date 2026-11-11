import { useState } from "react";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { DateInput } from "@/components/DateInput";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { ApiError, actualizarExpediente, type FichaRendicion, type ResponsableOpcion } from "./api";

export function EditarCabeceraCuenta({ ficha, responsables, onGuardado }: { ficha: FichaRendicion; responsables: ResponsableOpcion[]; onGuardado: () => Promise<unknown> }) {
  const { tiene } = useAutoridad();
  const puedeEditar = tiene("gobierno_rendicion:form", "empresa");
  const [editando, setEditando] = useState(false);
  const [denominacion, setDenominacion] = useState(ficha.denominacion);
  const [ejercicio, setEjercicio] = useState(ficha.ejercicio?.toString() ?? "");
  const [periodoDesde, setPeriodoDesde] = useState(ficha.periodo_desde);
  const [periodoHasta, setPeriodoHasta] = useState(ficha.periodo_hasta);
  const [fechaCorte, setFechaCorte] = useState(ficha.fecha_corte);
  const [responsable, setResponsable] = useState(responsables.find((r) => r.codigo === ficha.responsable.asignacion_codigo)?.asignacion_id ?? "");
  const [observaciones, setObservaciones] = useState(ficha.observaciones ?? "");
  const [error, setError] = useState<string | null>(null);
  if (!puedeEditar) return null;

  if (!editando) {
    return <Button onClick={() => setEditando(true)}>Editar cabecera</Button>;
  }

  async function guardar() {
    setError(null);
    try {
      await actualizarExpediente(ficha.id, String(ficha.version), {
        denominacion,
        ejercicio: ejercicio ? Number(ejercicio) : undefined,
        periodo_desde: periodoDesde,
        periodo_hasta: periodoHasta,
        fecha_corte: fechaCorte,
        assignment_id: responsable,
        observaciones: observaciones || undefined,
      });
      await onGuardado();
      setEditando(false);
    } catch (e) {
      if (e instanceof ApiError) {
        if (e.code === "VERSION_CONFLICT") {
          setError("La cuenta cambió mientras la editabas; recarga y vuelve a intentarlo.");
        } else {
          setError(e.message || "No se pudo guardar la cabecera.");
        }
      } else {
        setError("No se pudo guardar la cabecera.");
      }
    }
  }

  return (
    <div className="space-y-4 rounded-md border border-border-default bg-surface-0 p-4">
      <h3 className="text-lg font-semibold text-text-900">Editar cabecera</h3>
      {error && <div role="alert" className="text-sm text-error-600">{error}</div>}
      <FormField label="Denominación">
        <TextInput value={denominacion} onChange={(e) => setDenominacion(e.target.value)} />
      </FormField>
      <FormField label="Ejercicio">
        <TextInput value={ejercicio} onChange={(e) => setEjercicio(e.target.value)} />
      </FormField>
      <FormField label="Periodo desde">
        <DateInput value={periodoDesde} onChange={(e) => setPeriodoDesde(e.target.value)} />
      </FormField>
      <FormField label="Periodo hasta">
        <DateInput value={periodoHasta} onChange={(e) => setPeriodoHasta(e.target.value)} />
      </FormField>
      <FormField label="Fecha de corte">
        <DateInput value={fechaCorte} onChange={(e) => setFechaCorte(e.target.value)} />
      </FormField>
      <FormField label="Responsable">
        <select
          className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
          value={responsable}
          onChange={(e) => setResponsable(e.target.value)}
        >
          {responsables.map((opcion) => (
            <option key={opcion.asignacion_id} value={opcion.asignacion_id} selected={opcion.codigo === ficha.responsable.asignacion_codigo}>
              {opcion.funcionario} - {opcion.cargo}
            </option>
          ))}
        </select>
      </FormField>
      <FormField label="Observaciones">
        <TextInput value={observaciones} onChange={(e) => setObservaciones(e.target.value)} />
      </FormField>
      <div className="flex gap-2">
        <AsyncButton onClick={guardar}>Guardar cambios</AsyncButton>
        <Button onClick={() => setEditando(false)}>Cancelar</Button>
      </div>
    </div>
  );
}
