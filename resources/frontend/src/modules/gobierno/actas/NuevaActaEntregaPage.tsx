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
import { hoyDeNegocio } from "@/lib/fecha-de-negocio";
import { ApiError, crearActa, getOpcionesActas, getReglaActa, testigosExigidos, ReglaActa } from "./api";
import { ReglaActaResumen } from "./ReglaActaResumen";

export function NuevaActaEntregaPage() {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const { notify } = useNotifications();
  const navigate = useNavigate();
  const puedeGestionar = tiene("gobierno_actas:manage", "empresa");

  const [assignmentId, setAssignmentId] = useState("");
  const [receptorOfficialId, setReceptorOfficialId] = useState("");
  const [modalidad, setModalidad] = useState<"ENTREGA" | "LEVANTADA_POR_RECEPTOR">("ENTREGA");
  const [testigos, setTestigos] = useState<{ nombre: string; documento: string }[]>([]);
  const [auditorOfficialId, setAuditorOfficialId] = useState("");
  const [motivo, setMotivo] = useState("");
  const [fundamento, setFundamento] = useState("");
  const [lugar, setLugar] = useState("");
  const [fechaCorte, setFechaCorte] = useState(hoyDeNegocio());
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});
  const actualizarTestigo = (i: number, campo: "nombre" | "documento", valor: string) => {
    const nuevos = Array.from({ length: Math.max(cantidadTestigos, testigos.length) }, (_, idx) => testigos[idx] ?? { nombre: "", documento: "" });
    nuevos[i] = { ...nuevos[i], [campo]: valor };
    setTestigos(nuevos.slice(0, cantidadTestigos));
  };

  const opciones = useQuery({
    queryKey: ["gobierno-actas-opciones", activeCompanyId],
    queryFn: getOpcionesActas,
    enabled: puedeGestionar,
  });

  const regla = useQuery({
    queryKey: ["gobierno-actas-regla", activeCompanyId, assignmentId, fechaCorte],
    queryFn: () => getReglaActa(assignmentId, fechaCorte),
    enabled: puedeGestionar && !!assignmentId && !!fechaCorte,
  });

  const cantidadTestigos = regla.data ? testigosExigidos(regla.data, modalidad) : (modalidad === "LEVANTADA_POR_RECEPTOR" ? 2 : 0);
  const testigosNormalizados = (regla.data ? Array.from({ length: cantidadTestigos }, (_, i) => testigos[i] ?? { nombre: "", documento: "" }) : testigos);

  const crear = useMutation({
    mutationFn: () =>
      crearActa({
        assignment_id: assignmentId,
        receptor_official_id: receptorOfficialId,
        receptor_assignment_id: null,
        modalidad,
        testigos: regla.data ? testigosNormalizados.slice(0, cantidadTestigos) : testigosNormalizados,
        auditor_official_id: modalidad === "LEVANTADA_POR_RECEPTOR" ? auditorOfficialId : null,
        motivo,
        fundamento,
        lugar,
        fecha_corte: fechaCorte,
      }),
    onSuccess: (ficha) => {
      notify({ type: "success", title: "Acta creada en borrador", description: ficha.codigo });
      navigate(`/gobierno/actas-entrega/${ficha.id}`);
    },
    onError: (err: ApiError) => {
      setErrorGeneral(err.message);
      setFieldErrors(err.fieldErrors ?? {});
    },
  });

  if (!puedeGestionar) {
    return <ErrorState message="No tiene permiso para crear actas de entrega." />;
  }

  return (
    <PageContent>
      <PageHeader title="Nueva acta de entrega" description="Cree un acta de entrega en borrador." />

      <form
        onSubmit={(e) => {
          e.preventDefault();
          setErrorGeneral(null);
          setFieldErrors({});
          crear.mutate();
        }}
        className="flex flex-col gap-4"
      >
        {errorGeneral && (
          <div role="alert" className="rounded-md border border-danger bg-danger/10 p-3 text-danger">
            {errorGeneral}
          </div>
        )}

        <FormField label="Ocupación saliente" htmlFor="n-ocupacion" required error={fieldErrors.assignment_id?.[0]}>
          <select
            id="n-ocupacion"
            className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
            value={assignmentId}
            onChange={(e) => setAssignmentId(e.target.value)}
          >
            <option value="">Seleccione...</option>
            {(opciones.data?.ocupaciones ?? []).map((r) => (
              <option key={r.asignacion_id} value={r.asignacion_id}>
                {r.funcionario} — {r.cargo} ({r.unidad})
              </option>
            ))}
          </select>
        </FormField>

        {!assignmentId || !fechaCorte ? (
          <p className="text-sm text-text-600">Elija la ocupación saliente y la fecha de corte para ver la regla aplicada.</p>
        ) : regla.isLoading ? (
          <p className="text-sm text-text-600">Cargando regla aplicada...</p>
        ) : regla.data ? (
          <ReglaActaResumen regla={regla.data as ReglaActa} />
        ) : null}

        <FormField label="Receptor" htmlFor="n-receptor" required error={fieldErrors.receptor_official_id?.[0]}>
          <select
            id="n-receptor"
            className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
            value={receptorOfficialId}
            onChange={(e) => setReceptorOfficialId(e.target.value)}
          >
            <option value="">Seleccione...</option>
            {(opciones.data?.funcionarios ?? []).map((r) => (
              <option key={r.official_id} value={r.official_id}>
                {r.nombre} ({r.codigo})
              </option>
            ))}
          </select>
        </FormField>

        <fieldset className="flex flex-col gap-2">
          <legend className="text-sm font-medium text-text-900">Modalidad</legend>
          <label className="flex items-center gap-2 text-sm text-text-900">
            <input
              type="radio"
              name="modalidad"
              value="ENTREGA"
              checked={modalidad === "ENTREGA"}
              onChange={() => setModalidad("ENTREGA")}
            />
            Entrega por el saliente
          </label>
          <label className="flex items-center gap-2 text-sm text-text-900">
            <input
              type="radio"
              name="modalidad"
              value="LEVANTADA_POR_RECEPTOR"
              checked={modalidad === "LEVANTADA_POR_RECEPTOR"}
              onChange={() => setModalidad("LEVANTADA_POR_RECEPTOR")}
            />
            Levantada por el receptor
          </label>
        </fieldset>

        {cantidadTestigos > 0 && (
          <div className="flex flex-col gap-3">
            {Array.from({ length: cantidadTestigos }).map((_, i) => {
              const idx = i + 1;
              const testigo = testigosNormalizados[i] ?? { nombre: "", documento: "" };
              return (
                <div key={idx} className="flex flex-wrap gap-2">
                  <FormField label={`Testigo ${idx} - Nombre`} htmlFor={`n-testigo${idx}-nombre`} required error={fieldErrors.testigos?.[0]}>
                    <TextInput
                      id={`n-testigo${idx}-nombre`}
                      value={testigo.nombre}
                      onChange={(e) => actualizarTestigo(i, "nombre", e.target.value)}
                      invalid={!!fieldErrors.testigos}
                    />
                  </FormField>
                  <FormField label={`Testigo ${idx} - Documento`} htmlFor={`n-testigo${idx}-documento`} required error={fieldErrors.testigos?.[0]}>
                    <TextInput
                      id={`n-testigo${idx}-documento`}
                      value={testigo.documento}
                      onChange={(e) => actualizarTestigo(i, "documento", e.target.value)}
                      invalid={!!fieldErrors.testigos}
                    />
                  </FormField>
                </div>
              );
            })}
          </div>
        )}
        {modalidad === "LEVANTADA_POR_RECEPTOR" && (
          <FormField label="Auditor" htmlFor="n-auditor" required error={fieldErrors.auditor_official_id?.[0]}>
            <select
              id="n-auditor"
              className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              value={auditorOfficialId}
              onChange={(e) => setAuditorOfficialId(e.target.value)}
            >
              <option value="">Seleccione...</option>
              {(opciones.data?.funcionarios ?? []).map((r) => (
                <option key={r.official_id} value={r.official_id}>
                  {r.nombre} ({r.codigo})
                </option>
              ))}
            </select>
          </FormField>
        )}

        <FormField label="Motivo" htmlFor="n-motivo" required error={fieldErrors.motivo?.[0]}>
          <TextInput id="n-motivo" value={motivo} onChange={(e) => setMotivo(e.target.value)} invalid={!!fieldErrors.motivo} />
        </FormField>

        <FormField label="Fundamento" htmlFor="n-fundamento" required error={fieldErrors.fundamento?.[0]}>
          <TextInput id="n-fundamento" value={fundamento} onChange={(e) => setFundamento(e.target.value)} invalid={!!fieldErrors.fundamento} />
        </FormField>

        <FormField label="Lugar" htmlFor="n-lugar" required error={fieldErrors.lugar?.[0]}>
          <TextInput id="n-lugar" value={lugar} onChange={(e) => setLugar(e.target.value)} invalid={!!fieldErrors.lugar} />
        </FormField>

        <FormField label="Fecha de corte" htmlFor="n-corte" required error={fieldErrors.fecha_corte?.[0]}>
          <DateInput id="n-corte" value={fechaCorte} onChange={(e) => setFechaCorte(e.target.value)} invalid={!!fieldErrors.fecha_corte} />
        </FormField>

        <div>
          <AsyncButton
            type="submit"
            variant="primary"
            loadingText="Creando..."
            idleText="Crear acta de entrega"
            onClick={async () => {
              await crear.mutateAsync();
            }}
            disabled={crear.isPending}
          />
        </div>
      </form>
    </PageContent>
  );
}
