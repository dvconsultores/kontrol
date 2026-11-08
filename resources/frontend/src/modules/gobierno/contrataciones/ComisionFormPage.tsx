import { useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
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
  CONSULTA_COMISIONES,

  type ComisionCatalogo,
  type ComisionDetalle,
  type ComisionIn,
  type ComisionOpciones,
} from "@/modules/gobierno/api";

type ErroresFormulario = {
  nombre?: string;
  tipo?: string;
  objeto?: string;
  desde?: string;
  hasta?: string;
  acto_id?: string;
  general?: string;
};

export function ComisionFormPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const { comisionId } = useParams();

  const esEdicion = Boolean(comisionId);
  const puedeGestionar = tiene("gobierno_comisiones:manage", "empresa");

  const [nombre, setNombre] = useState("");
  const [tipo, setTipo] = useState("");
  const [objeto, setObjeto] = useState("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [actoId, setActoId] = useState("");
  const [errores, setErrores] = useState<ErroresFormulario>({});
  const enviandoRef = useRef(false);
  const [detalleCargado, setDetalleCargado] = useState(false);

  const catalogo = useQuery({
    queryKey: [...CONSULTA_COMISIONES, "catalogo", activeCompanyId],
    queryFn: () =>
      apiFetch<ComisionCatalogo>("/gobierno/contrataciones/comisiones/catalogo"),
    enabled: puedeGestionar && Boolean(activeCompanyId),
    retry: false,
  });

  const opciones = useQuery({
    queryKey: [...CONSULTA_COMISIONES, "opciones", activeCompanyId],
    queryFn: () =>
      apiFetch<ComisionOpciones>("/gobierno/contrataciones/comisiones/opciones"),
    enabled: puedeGestionar && Boolean(activeCompanyId),
    retry: false,
  });

  const detalle = useQuery({
    queryKey: [
      ...CONSULTA_COMISIONES,
      "comision-detalle",
      activeCompanyId,
      comisionId,
    ],
    queryFn: () =>
      apiFetch<ComisionDetalle>(
        `/gobierno/contrataciones/comisiones/${comisionId}`,
      ),
    enabled: puedeGestionar && esEdicion && Boolean(activeCompanyId),
    retry: false,
  });

  if (!puedeGestionar || !activeCompanyId) {
    return (
      <PageContent>
        <EmptyState
          title="Sin acceso"
          description="No tiene permisos para gestionar comisiones."
        />
      </PageContent>
    );
  }

  if (
    catalogo.isLoading ||
    opciones.isLoading ||
    (esEdicion && detalle.isLoading)
  ) {
    return (
      <PageContent>
        <LoadingState />
      </PageContent>
    );
  }

  if (
    catalogo.isError ||
    opciones.isError ||
    (esEdicion && detalle.isError)
  ) {
    const error = catalogo.isError
      ? catalogo.error
      : opciones.isError
        ? opciones.error
        : detalle.error;
    return (
      <PageContent>
        <ErrorDeCarga
          message={
            error instanceof Error
              ? error.message
              : "No fue posible cargar la comisión."
          }
          onRetry={() => {
            if (catalogo.isError) catalogo.refetch();
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
            description="Solo se modifica una comisión en borrador."
            action={
              <Link
                to={`/gobierno/contrataciones/comisiones/${detalle.data.id}`}
                className="text-brand-700 underline"
              >
                Volver a la comisión
              </Link>
            }
          />
        </PageContent>
      );
    }
    if (!detalleCargado) {
      setNombre(detalle.data.nombre);
      setTipo(detalle.data.tipo);
      setObjeto(detalle.data.objeto ?? "");
      setDesde(detalle.data.desde);
      setHasta(detalle.data.hasta ?? "");
      setActoId(detalle.data.acto?.id ?? "");
      setDetalleCargado(true);
    }
  }

  const limpiarError = (campo: keyof ErroresFormulario) => {
    setErrores((previos) => ({ ...previos, [campo]: undefined }));
  };

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

    const cuerpo: ComisionIn = {
      nombre: nombre.trim(),
      tipo,
      objeto: objeto.trim() || null,
      desde,
      hasta: hasta || null,
      acto_id: actoId || null,
    };

    enviandoRef.current = true;
    try {
      if (esEdicion && detalle.data) {
        const actualizado = await apiFetch<ComisionDetalle>(
          `/gobierno/contrataciones/comisiones/${detalle.data.id}`,
          {
            method: "PATCH",
            body: cuerpo,
            ifMatch: String(detalle.data.version),
          },
        );
        notify({ type: "success", title: "Comisión guardada en borrador" });
        await queryClient.invalidateQueries({ queryKey: [...CONSULTA_COMISIONES] });
        navigate(`/gobierno/contrataciones/comisiones/${actualizado.id}`);
      } else {
        const creado = await apiFetch<ComisionDetalle>(
          "/gobierno/contrataciones/comisiones",
          {
            method: "POST",
            body: cuerpo,
          },
        );
        notify({ type: "success", title: "Comisión guardada en borrador" });
        await queryClient.invalidateQueries({ queryKey: [...CONSULTA_COMISIONES] });
        navigate(`/gobierno/contrataciones/comisiones/${creado.id}`);
      }
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 422 && Object.keys(error.fieldErrors).length > 0) {
          setErrores({
            nombre: error.fieldErrors.nombre?.[0],
            tipo: error.fieldErrors.tipo?.[0],
            objeto: error.fieldErrors.objeto?.[0],
            desde: error.fieldErrors.desde?.[0],
            hasta: error.fieldErrors.hasta?.[0],
            acto_id: error.fieldErrors.acto_id?.[0],
            general: error.fieldErrors["_"]?.[0],
          });
          return;
        }
        if (error.status === 409 && error.code === "GOV_COMMITTEE_STALE") {
          setErrores({
            general: "La comisión cambió; recargue.",
          });
          return;
        }
        if (error.code?.startsWith("GOV_COMMITTEE_")) {
          setErrores({ general: error.message });
          return;
        }
      }
      setErrores({ general: "No se pudo guardar la comisión." });
    } finally {
      enviandoRef.current = false;
    }
  };

  const tipos = catalogo.data?.tipos ?? [];
  const actos = opciones.data?.actos ?? [];

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno" },
          { label: "Contrataciones" },
          {
            label: "Comisiones",
            to: "/gobierno/contrataciones/comisiones",
          },
        ]}
        title={esEdicion ? "Editar comisión" : "Nueva comisión"}
        description="Registre la comisión. Queda en borrador hasta que otra persona la active."
      />

      <form
        noValidate
        className="mt-4 space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          void enviar();
        }}
      >
        <FormField
          label="Nombre"
          htmlFor="comision-nombre"
          required
          error={errores.nombre}
        >
          <input
            id="comision-nombre"
            type="text"
            value={nombre}
            onChange={(evento) => {
              setNombre(evento.target.value);
              limpiarError("nombre");
            }}
            aria-invalid={Boolean(errores.nombre)}
            className={inputClase(errores.nombre)}
          />
        </FormField>

        <FormField
          label="Tipo"
          htmlFor="comision-tipo-form"
          required
          error={errores.tipo}
        >
          <select
            id="comision-tipo-form"
            value={tipo}
            onChange={(evento) => {
              setTipo(evento.target.value);
              limpiarError("tipo");
            }}
            aria-invalid={Boolean(errores.tipo)}
            className={inputClase(errores.tipo)}
          >
            <option value="">Elija el tipo</option>
            {tipos.map((t) => (
              <option key={t.codigo} value={t.codigo}>
                {t.etiqueta}
              </option>
            ))}
          </select>
        </FormField>

        <FormField
          label="Objeto o especialidad"
          htmlFor="comision-objeto"
          error={errores.objeto}
          help="Especialidad, obras, bienes o servicios que atenderá."
        >
          <textarea
            id="comision-objeto"
            value={objeto}
            onChange={(evento) => {
              setObjeto(evento.target.value);
              limpiarError("objeto");
            }}
            aria-invalid={Boolean(errores.objeto)}
            className={textareaClase(errores.objeto)}
          />
        </FormField>

        <FormField label="Desde" htmlFor="comision-desde" required error={errores.desde}>
          <input
            id="comision-desde"
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
          htmlFor="comision-hasta"
          error={errores.hasta}
          help={
            tipo === "TEMPORAL"
              ? "Obligatorio si la comisión es temporal."
              : "Déjelo vacío si no tiene fecha final."
          }
        >
          <input
            id="comision-hasta"
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
          label="Acto que la crea"
          htmlFor="comision-acto"
          error={errores.acto_id}
          help="Debe estar eficaz y publicado en gaceta para poder activarla."
        >
          <select
            id="comision-acto"
            value={actoId}
            onChange={(evento) => {
              setActoId(evento.target.value);
              limpiarError("acto_id");
            }}
            aria-invalid={Boolean(errores.acto_id)}
            className={inputClase(errores.acto_id)}
          >
            <option value="">Sin acto todavía</option>
            {actos.map((a) => (
              <option key={a.id} value={a.id}>
                {a.etiqueta}
              </option>
            ))}
          </select>
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
            onClick={() => navigate(-1)}
          >
            Cancelar
          </Button>
        </div>
      </form>
    </PageContent>
  );
}
