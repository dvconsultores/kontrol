import { useState } from "react";
import { useNavigate } from "react-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { AsyncButton } from "@/components/AsyncButton";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { DateInput } from "@/components/DateInput";
import { ErrorState } from "@/components/ErrorState";
import { ApiError, crearExpediente, getOpcionesRendicion } from "./api";

export function NuevoExpedienteCuentaPage() {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const { notify } = useNotifications();
  const navigate = useNavigate();
  const puedeFormar = tiene("gobierno_rendicion:form", "empresa");

  const [denominacion, setDenominacion] = useState("");
  const [ejercicio, setEjercicio] = useState("");
  const [periodoDesde, setPeriodoDesde] = useState("");
  const [periodoHasta, setPeriodoHasta] = useState("");
  const [fechaCorte, setFechaCorte] = useState("");
  const [assignmentId, setAssignmentId] = useState("");
  const [observaciones, setObservaciones] = useState("");
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});

  const opciones = useQuery({ queryKey: ["gobierno-rendicion-opciones", activeCompanyId], queryFn: getOpcionesRendicion, enabled: puedeFormar });

  const crear = useMutation({
    mutationFn: () =>
      crearExpediente({
        denominacion,
        ejercicio: ejercicio ? Number(ejercicio) : undefined,
        periodo_desde: periodoDesde,
        periodo_hasta: periodoHasta,
        fecha_corte: fechaCorte || periodoHasta,
        assignment_id: assignmentId,
        observaciones: observaciones || undefined,
      }),
    onSuccess: (ficha) => {
      notify({ type: "success", title: "Expediente creado", description: ficha.codigo });
      navigate(`/gobierno/rendicion/${ficha.id}`);
    },
    onError: (err: ApiError) => {
      setErrorGeneral(err.message);
      setFieldErrors(err.fieldErrors ?? {});
    },
  });

  if (!puedeFormar) {
    return <ErrorState message="No tiene permiso para crear expedientes de cuenta." />;
  }

  const handleHasta = (v: string) => {
    setPeriodoHasta(v);
    if (!fechaCorte) setFechaCorte(v);
  };

  return (
    <PageContent>
      <PageHeader title="Nuevo expediente de cuenta" description="Cree un expediente para la formación de cuenta." />

      <form
        onSubmit={(e) => {
          e.preventDefault();
          setErrorGeneral(null);
          setFieldErrors({});
          crear.mutate();
        }}
        className="flex flex-col gap-4"
      >
        {errorGeneral && <div role="alert" className="rounded-md border border-danger bg-danger/10 p-3 text-danger">{errorGeneral}</div>}

        <FormField label="Denominación" htmlFor="n-denominacion" required error={fieldErrors.denominacion?.[0]}>
          <TextInput id="n-denominacion" value={denominacion} onChange={(e) => setDenominacion(e.target.value)} invalid={!!fieldErrors.denominacion} />
        </FormField>

        <FormField label="Ejercicio" htmlFor="n-ejercicio" error={fieldErrors.ejercicio?.[0]}>
          <TextInput id="n-ejercicio" type="number" value={ejercicio} onChange={(e) => setEjercicio(e.target.value)} invalid={!!fieldErrors.ejercicio} />
        </FormField>

        <div className="flex flex-wrap gap-2">
          <FormField label="Periodo desde" htmlFor="n-desde" required error={fieldErrors.periodo_desde?.[0]}>
            <DateInput id="n-desde" value={periodoDesde} onChange={(e) => setPeriodoDesde(e.target.value)} invalid={!!fieldErrors.periodo_desde} />
          </FormField>
          <FormField label="Periodo hasta" htmlFor="n-hasta" required error={fieldErrors.periodo_hasta?.[0]}>
            <DateInput id="n-hasta" value={periodoHasta} onChange={(e) => handleHasta(e.target.value)} invalid={!!fieldErrors.periodo_hasta} />
          </FormField>
          <FormField label="Fecha de corte" htmlFor="n-corte" required error={fieldErrors.fecha_corte?.[0]}>
            <DateInput id="n-corte" value={fechaCorte} onChange={(e) => setFechaCorte(e.target.value)} invalid={!!fieldErrors.fecha_corte} />
          </FormField>
        </div>

        <FormField label="Responsable" htmlFor="n-responsable" required error={fieldErrors.assignment_id?.[0]}>
          <select id="n-responsable" className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600" value={assignmentId} onChange={(e) => setAssignmentId(e.target.value)}>
            <option value="">Seleccione...</option>
            {(opciones.data?.responsables ?? []).map((r) => (
              <option key={r.asignacion_id} value={r.asignacion_id}>
                {r.funcionario} · {r.cargo} · {r.unidad} ({r.figura})
              </option>
            ))}
          </select>
        </FormField>

        <FormField label="Observaciones" htmlFor="n-observaciones" error={fieldErrors.observaciones?.[0]}>
          <TextInput id="n-observaciones" value={observaciones} onChange={(e) => setObservaciones(e.target.value)} invalid={!!fieldErrors.observaciones} />
        </FormField>

        <div>
          <AsyncButton type="submit" variant="primary" loadingText="Creando..." idleText="Crear expediente" onClick={async () => { await crear.mutateAsync(); }} disabled={crear.isPending} />
        </div>
      </form>
    </PageContent>
  );
}
