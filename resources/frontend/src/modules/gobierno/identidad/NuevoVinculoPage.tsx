import { useRef, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { ErrorDeCarga } from "@/modules/gobierno/ocupacion/ErrorDeCarga";
import { LoadingState } from "@/components/LoadingState";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import {
  CONSULTA_IDENTIDAD,
  type OpcionesIdentidad,
  type VinculoDetalle,
  type VinculoEntrada,
} from "@/modules/gobierno/api";

type ErroresFormulario = {
  user_id?: string;
  official_id?: string;
  desde?: string;
  hasta?: string;
  motivo?: string;
  soporte?: string;
  general?: string;
};

export function NuevoVinculoPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const { vinculoId } = useParams();

  const esEdicion = Boolean(vinculoId);
  const puedeGestionar = tiene("gobierno_identidad:manage", "empresa");

  const [cuenta, setCuenta] = useState("");
  const [funcionario, setFuncionario] = useState("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [motivo, setMotivo] = useState("");
  const [soporte, setSoporte] = useState("");
  const [errores, setErrores] = useState<ErroresFormulario>({});
  const enviandoRef = useRef(false);
  const [detalleCargado, setDetalleCargado] = useState(false);


  const opciones = useQuery({
    queryKey: [...CONSULTA_IDENTIDAD, "opciones", activeCompanyId],
    queryFn: () => apiFetch<OpcionesIdentidad>("/gobierno/identidad/opciones"),
    enabled: puedeGestionar && Boolean(activeCompanyId),
    retry: false,
  });

  const detalle = useQuery({
    queryKey: [...CONSULTA_IDENTIDAD, "vinculo-detalle", activeCompanyId, vinculoId],
    queryFn: () =>
      apiFetch<VinculoDetalle>(`/gobierno/identidad/vinculos/${vinculoId}`),
    enabled: puedeGestionar && esEdicion && Boolean(activeCompanyId),
    retry: false,
  });

  if (!puedeGestionar || !activeCompanyId) {
    return (
      <PageContent>
        <EmptyState
          title="Sin acceso"
          description="No tiene permisos para gestionar vínculos."
        />
      </PageContent>
    );
  }

  if (opciones.isLoading || (esEdicion && detalle.isLoading)) {
    return (
      <PageContent>
        <LoadingState />
      </PageContent>
    );
  }

  if (opciones.isError || (esEdicion && detalle.isError)) {
    const error = opciones.isError
      ? opciones.error
      : detalle.error;
    return (
      <PageContent>
        <ErrorDeCarga
          message={error instanceof Error ? error.message : "No fue posible cargar el vínculo."}
          onRetry={() => {
            if (opciones.isError) opciones.refetch();
            if (esEdicion && detalle.isError) detalle.refetch();
          }}
        />
      </PageContent>
    );
  }

  if (esEdicion && detalle.data) {
    if (detalle.data.status !== "BORRADOR") {
      return (
        <PageContent>
          <EmptyState
            title="No editable"
            description="Solo se modifica un vínculo en borrador."
          />
        </PageContent>
      );
    }
    if (!detalleCargado) {
      setCuenta(detalle.data.cuenta.id);
      setFuncionario(detalle.data.funcionario.id);
      setDesde(detalle.data.desde);
      setHasta(detalle.data.hasta ?? "");
      setMotivo(detalle.data.motivo);
      setSoporte(detalle.data.soporte ?? "");
      setDetalleCargado(true);
    }
  }

  const limpiarError = (campo: keyof ErroresFormulario) => {
    setErrores((previos) => ({ ...previos, [campo]: undefined }));
  };

  const selectClase = (error?: string) =>
    `w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600 ${
      error ? "border-danger-600" : "border-border-default"
    }`;

  const inputClase = (error?: string) =>
    `w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600 ${
      error ? "border-danger-600" : "border-border-default"
    }`;

  const textareaClase = (error?: string) =>
    `min-h-24 w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600 ${
      error ? "border-danger-600" : "border-border-default"
    }`;

  const enviar = async () => {
    if (enviandoRef.current) return;

    const cuerpo: VinculoEntrada = {
      user_id: cuenta,
      official_id: funcionario,
      desde,
      hasta: hasta || null,
      motivo: motivo.trim(),
      soporte: soporte.trim() || null,
    };

    enviandoRef.current = true;
    try {
      if (esEdicion && detalle.data) {
        const actualizado = await apiFetch<VinculoDetalle>(
          `/gobierno/identidad/vinculos/${detalle.data.id}`,
          {
            method: "PATCH",
            body: cuerpo,
            ifMatch: String(detalle.data.version),
          },
        );
        notify({ type: "success", title: "Vínculo guardado en borrador" });
        await queryClient.invalidateQueries({ queryKey: [...CONSULTA_IDENTIDAD] });
        navigate(`/gobierno/identidad/vinculos/${actualizado.id}`);
      } else {
        const creado = await apiFetch<VinculoDetalle>(
          "/gobierno/identidad/vinculos",
          {
            method: "POST",
            body: cuerpo,
          },
        );
        notify({ type: "success", title: "Vínculo guardado en borrador" });
        await queryClient.invalidateQueries({ queryKey: [...CONSULTA_IDENTIDAD] });
        navigate(`/gobierno/identidad/vinculos/${creado.id}`);
      }
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 422 && Object.keys(error.fieldErrors).length > 0) {
          setErrores({
            user_id: error.fieldErrors.user_id?.[0],
            official_id: error.fieldErrors.official_id?.[0],
            desde: error.fieldErrors.desde?.[0],
            hasta: error.fieldErrors.hasta?.[0],
            motivo: error.fieldErrors.motivo?.[0],
            soporte: error.fieldErrors.soporte?.[0],
            general: error.fieldErrors["_"]?.[0],
          });
          return;
        }
        if (error.status === 422) {
          setErrores({ general: error.message });
          return;
        }
        if (error.status === 409 && error.code === "GOV_IDENTITY_STALE") {
          setErrores({
            general: "El vínculo cambió; recárguelo.",
          });
          return;
        }
        if (error.code?.startsWith("GOV_IDENTITY_")) {
          setErrores({ general: error.message });
          return;
        }
      }
      setErrores({ general: "No se pudo guardar el vínculo." });
    } finally {
      enviandoRef.current = false;
    }
  };

  const cuentas = opciones.data?.cuentas ?? [];
  const funcionarios = opciones.data?.funcionarios ?? [];

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno" },
          { label: "Identidad institucional", to: "/gobierno/identidad" },
        ]}
        title={esEdicion ? "Editar vínculo" : "Nuevo vínculo"}
        description="Registre la cuenta de una persona funcionaria. Queda en borrador hasta que otra persona la active."
      />

      <form
        noValidate
        className="mt-4 space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          void enviar();
        }}
      >
        <p className="text-sm text-text-700">
          El vínculo identifica a la persona detrás de la cuenta. No concede autoridad:
          la autoridad se deriva de la ocupación vigente del cargo (ORG-04).
        </p>

        <FormField
          label="Cuenta"
          htmlFor="vinculo-cuenta"
          required
          error={errores.user_id}
        >
          <select
            id="vinculo-cuenta"
            value={cuenta}
            onChange={(evento) => {
              setCuenta(evento.target.value);
              limpiarError("user_id");
            }}
            aria-invalid={Boolean(errores.user_id)}
            className={selectClase(errores.user_id)}
          >
            <option value="">Elija la cuenta</option>
            {cuentas.map((c) => (
              <option key={c.id} value={c.id}>
                {c.usuario}
                {c.vinculada ? " · ya vinculada" : ""}
              </option>
            ))}
          </select>
        </FormField>

        <FormField
          label="Funcionario"
          htmlFor="vinculo-funcionario"
          required
          error={errores.official_id}
        >
          <select
            id="vinculo-funcionario"
            value={funcionario}
            onChange={(evento) => {
              setFuncionario(evento.target.value);
              limpiarError("official_id");
            }}
            aria-invalid={Boolean(errores.official_id)}
            className={selectClase(errores.official_id)}
          >
            <option value="">Elija el funcionario</option>
            {funcionarios.map((f) => (
              <option key={f.id} value={f.id}>
                {`${f.nombre} · ${f.documento}`}
                {f.vinculado ? " · ya vinculado" : ""}
              </option>
            ))}
          </select>
        </FormField>

        <FormField label="Desde" htmlFor="vinculo-desde" required error={errores.desde}>
          <input
            id="vinculo-desde"
            type="date"
            value={desde}
            onChange={(evento) => {
              setDesde(evento.target.value);
              limpiarError("desde");
              limpiarError("hasta");
            }}
            aria-invalid={Boolean(errores.desde)}
            className={inputClase(errores.desde)}
          />
        </FormField>

        <FormField
          label="Hasta"
          htmlFor="vinculo-hasta"
          error={errores.hasta}
          help="Déjelo vacío si no tiene fecha final."
        >
          <input
            id="vinculo-hasta"
            type="date"
            value={hasta}
            min={desde}
            onChange={(evento) => {
              setHasta(evento.target.value);
              limpiarError("hasta");
            }}
            aria-invalid={Boolean(errores.hasta)}
            className={inputClase(errores.hasta)}
          />
        </FormField>

        <FormField
          label="Motivo"
          htmlFor="vinculo-motivo"
          required
          error={errores.motivo}
        >
          <textarea
            id="vinculo-motivo"
            value={motivo}
            minLength={10}
            maxLength={500}
            onChange={(evento) => {
              setMotivo(evento.target.value);
              limpiarError("motivo");
            }}
            aria-invalid={Boolean(errores.motivo)}
            className={textareaClase(errores.motivo)}
          />
        </FormField>

        <FormField
          label="Soporte"
          htmlFor="vinculo-soporte"
          error={errores.soporte}
          help="Referencia del documento que respalda la vinculación, si existe."
        >
          <input
            id="vinculo-soporte"
            type="text"
            value={soporte}
            minLength={3}
            maxLength={200}
            onChange={(evento) => {
              setSoporte(evento.target.value);
              limpiarError("soporte");
            }}
            aria-invalid={Boolean(errores.soporte)}
            className={inputClase(errores.soporte)}
          />
        </FormField>

        {errores.general && (
          <p role="alert" className="text-sm text-danger-600">
            {errores.general}
          </p>
        )}

        <div className="flex flex-wrap items-center gap-2">
          <AsyncButton variant="primary" onClick={enviar}>
            Guardar borrador
          </AsyncButton>
          <Button
            variant="secondary"
            onClick={() => navigate("/gobierno/identidad")}
          >
            Cancelar
          </Button>
        </div>
      </form>
    </PageContent>
  );
}
