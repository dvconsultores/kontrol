import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { hoyDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_CIERRES,
  ETIQUETAS_ACCION_CIERRE,
  type AccionCierre,
  type CatalogoCierres,
  type PoliticaCierreDetalle,
  type PoliticaCierreEntrada,
} from "@/modules/gobierno/api";

type ErroresFormulario = {
  nombre?: string;
  accion_cierre?: string;
  fundamento?: string;
  vigente_desde?: string;
  vigente_hasta?: string;
  general?: string;
};

export function NuevaPoliticaPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();

  const puedeGestionar = tiene("gobierno_cierre:manage", "empresa");

  const [nombre, setNombre] = useState("");
  const [accionCierre, setAccionCierre] = useState<AccionCierre | "">("");
  const [fundamento, setFundamento] = useState("");
  const [desde, setDesde] = useState(hoyDeNegocio());
  const [hasta, setHasta] = useState("");
  const [errores, setErrores] = useState<ErroresFormulario>({});
  const enviandoRef = useRef(false);

  const catalogo = useQuery({
    queryKey: [...CONSULTA_CIERRES, "catalogo", activeCompanyId],
    queryFn: () => apiFetch<CatalogoCierres>("/gobierno/cierres/catalogo"),
    enabled: puedeGestionar && Boolean(activeCompanyId),
    retry: false,
  });

  const acciones = useMemo(() => catalogo.data?.acciones ?? [], [catalogo.data]);

  const limpiarError = (campo: keyof ErroresFormulario): void => {
    setErrores((previos) => {
      if (!(campo in previos)) return previos;
      const siguientes = { ...previos };
      delete siguientes[campo];
      return siguientes;
    });
  };

  const validar = (): ErroresFormulario => {
    const siguientes: ErroresFormulario = {};

    if (!accionCierre) {
      siguientes.accion_cierre = "Elija la acción de cierre.";
    }

    const nombreRecortado = nombre.trim();
    if (nombreRecortado.length < 3 || nombreRecortado.length > 200) {
      siguientes.nombre = "El nombre debe tener entre 3 y 200 caracteres.";
    }

    const fundamentoRecortado = fundamento.trim();
    if (fundamentoRecortado.length < 10 || fundamentoRecortado.length > 1000) {
      siguientes.fundamento =
        "El fundamento debe tener entre 10 y 1000 caracteres.";
    }

    if (!desde) {
      siguientes.vigente_desde = "Indique la fecha de inicio de la vigencia.";
    }

    if (hasta && desde && hasta < desde) {
      siguientes.vigente_hasta =
        "La vigencia final no puede ser anterior a la inicial.";
    }

    return siguientes;
  };

  const enviar = async (): Promise<void> => {
    if (!puedeGestionar || enviandoRef.current) return;

    const erroresLocales = validar();
    setErrores(erroresLocales);
    if (Object.keys(erroresLocales).length > 0) return;
    if (accionCierre === "") return;

    const cuerpo: PoliticaCierreEntrada = {
      nombre: nombre.trim(),
      accion_cierre: accionCierre,
      fundamento: fundamento.trim(),
      vigente_desde: desde,
      vigente_hasta: hasta || null,
    };

    enviandoRef.current = true;
    try {
      const creada = await apiFetch<PoliticaCierreDetalle>(
        "/gobierno/cierres/politicas",
        {
          method: "POST",
          body: cuerpo,
        },
      );
      notify({ type: "success", title: "Política registrada en borrador" });
      await queryClient.invalidateQueries({ queryKey: [...CONSULTA_CIERRES] });
      navigate(`/gobierno/cierres/${creada.id}`);
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 422 && error.code === "VALIDATION_ERROR") {
          setErrores({
            nombre: error.fieldErrors.nombre?.[0],
            fundamento: error.fieldErrors.fundamento?.[0],
            accion_cierre: error.fieldErrors.accion_cierre?.[0],
            vigente_desde: error.fieldErrors.vigente_desde?.[0],
            vigente_hasta: error.fieldErrors.vigente_hasta?.[0],
            general: error.fieldErrors["_"]?.[0],
          });
          return;
        }
        if (error.status === 422) {
          setErrores({ general: error.message });
          return;
        }
        if (error.status === 403) {
          notify({
            type: "error",
            title: "No tiene permiso para registrar políticas",
          });
          return;
        }
      }
      notify({ type: "error", title: "No fue posible registrar la política" });
    } finally {
      enviandoRef.current = false;
    }
  };

  if (!puedeGestionar) {
    return (
      <PageContent>
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para registrar políticas de cierre."
        />
      </PageContent>
    );
  }

  if (catalogo.isLoading) {
    return (
      <PageContent>
        <PageHeader
          crumbs={[
            { label: "Gobierno" },
            { label: "Controles de cierre", to: "/gobierno/cierres" },
          ]}
          title="Nueva política de cierre"
        />
        <LoadingState label="Cargando el catálogo de cierres…" />
      </PageContent>
    );
  }

  if (catalogo.isError) {
    return (
      <PageContent>
        <PageHeader
          crumbs={[
            { label: "Gobierno" },
            { label: "Controles de cierre", to: "/gobierno/cierres" },
          ]}
          title="Nueva política de cierre"
        />
        <ErrorState
          message="No fue posible cargar el catálogo de cierres."
          onRetry={() => void catalogo.refetch()}
        />
      </PageContent>
    );
  }

  const selectClase = (error?: string) =>
    `w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600 ${
      error ? "border-danger-600" : "border-border-default"
    }`;

  const textareaClase = (error?: string) =>
    `min-h-24 w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600 ${
      error ? "border-danger-600" : "border-border-default"
    }`;

  const cambiarAccionCierre = (valor: AccionCierre | ""): void => {
    setAccionCierre(valor);
    limpiarError("accion_cierre");
  };

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno" },
          { label: "Controles de cierre", to: "/gobierno/cierres" },
        ]}
        title="Nueva política de cierre"
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
          label="Nombre de la política"
          htmlFor="politica-nombre"
          required
          error={errores.nombre}
          help="Nombre corto de la política"
        >
          <TextInput
            id="politica-nombre"
            value={nombre}
            maxLength={200}
            onChange={(evento) => {
              setNombre(evento.target.value);
              limpiarError("nombre");
            }}
            aria-invalid={Boolean(errores.nombre)}
          />
        </FormField>

        <FormField
          label="Acción de cierre"
          htmlFor="politica-accion-cierre"
          required
          error={errores.accion_cierre}
        >
          <select
            id="politica-accion-cierre"
            value={accionCierre}
            onChange={(evento) =>
              cambiarAccionCierre(evento.target.value as AccionCierre | "")
            }
            aria-invalid={Boolean(errores.accion_cierre)}
            className={selectClase(errores.accion_cierre)}
          >
            <option value="">Elija la acción de cierre</option>
            {acciones.map((accion) => (
              <option key={accion.codigo} value={accion.codigo}>
                {ETIQUETAS_ACCION_CIERRE[accion.codigo as AccionCierre] ??
                  accion.etiqueta}
              </option>
            ))}
          </select>
        </FormField>

        <FormField
          label="Fundamento"
          htmlFor="politica-fundamento"
          required
          error={errores.fundamento}
          help="Por qué se aplica esta política"
        >
          <textarea
            id="politica-fundamento"
            value={fundamento}
            maxLength={1000}
            onChange={(evento) => {
              setFundamento(evento.target.value);
              limpiarError("fundamento");
            }}
            aria-invalid={Boolean(errores.fundamento)}
            className={textareaClase(errores.fundamento)}
          />
        </FormField>

        <FormField
          label="Vigente desde"
          htmlFor="politica-desde"
          required
          error={errores.vigente_desde}
        >
          <input
            id="politica-desde"
            type="date"
            value={desde}
            onChange={(evento) => {
              setDesde(evento.target.value);
              limpiarError("vigente_desde");
              limpiarError("vigente_hasta");
            }}
            aria-invalid={Boolean(errores.vigente_desde)}
            className={selectClase(errores.vigente_desde)}
          />
        </FormField>

        <FormField
          label="Vigente hasta"
          htmlFor="politica-hasta"
          error={errores.vigente_hasta}
        >
          <input
            id="politica-hasta"
            type="date"
            value={hasta}
            min={desde}
            onChange={(evento) => {
              setHasta(evento.target.value);
              limpiarError("vigente_hasta");
            }}
            aria-invalid={Boolean(errores.vigente_hasta)}
            className={selectClase(errores.vigente_hasta)}
          />
        </FormField>

        {errores.general && (
          <p role="alert" className="text-sm text-danger-600">
            {errores.general}
          </p>
        )}

        <div className="flex items-center gap-2">
          <AsyncButton variant="primary" onClick={enviar}>
            Crear política
          </AsyncButton>
          <Button
            variant="secondary"
            onClick={() => navigate("/gobierno/cierres")}
          >
            Cancelar
          </Button>
        </div>
      </form>
    </PageContent>
  );
}
