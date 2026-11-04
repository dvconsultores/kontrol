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
  CONSULTA_SOD,
  ETIQUETAS_PROCESO_SOD,
  type CatalogoSod,
  type ProcesoSod,
  type ReglaSodDetalle,
  type ReglaSodEntrada,
} from "@/modules/gobierno/api";

type ErroresFormulario = {
  proceso?: string;
  accion_a?: string;
  accion_b?: string;
  nombre?: string;
  descripcion?: string;
  vigente_desde?: string;
  vigente_hasta?: string;
  general?: string;
};

export function NuevaReglaSodPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();

  const puedeGestionar = tiene("gobierno_sod:manage", "empresa");

  const [proceso, setProceso] = useState<ProcesoSod | "">("");
  const [accionA, setAccionA] = useState("");
  const [accionB, setAccionB] = useState("");
  const [bidireccional, setBidireccional] = useState(false);
  const [nombre, setNombre] = useState("");
  const [razon, setRazon] = useState("");
  const [desde, setDesde] = useState(hoyDeNegocio());
  const [hasta, setHasta] = useState("");
  const [errores, setErrores] = useState<ErroresFormulario>({});
  const enviandoRef = useRef(false);

  const catalogo = useQuery({
    queryKey: [...CONSULTA_SOD, "acciones", activeCompanyId],
    queryFn: () => apiFetch<CatalogoSod>("/gobierno/sod/acciones"),
    enabled: puedeGestionar && Boolean(activeCompanyId),
    retry: false,
  });

  const procesos = useMemo(() => catalogo.data?.procesos ?? [], [catalogo.data]);
  const procesoElegido = useMemo(
    () => procesos.find((p) => p.proceso === proceso),
    [procesos, proceso],
  );
  const accionesProceso = useMemo(() => procesoElegido?.acciones ?? [], [procesoElegido]);

  const accionesParaA = accionesProceso;

  const accionesParaB = useMemo(() => {
    return accionesProceso.filter((accion) => {
      if (accion.codigo === accionA) return false;
      if (!bidireccional && accion.crea_objeto) return false;
      return true;
    });
  }, [accionesProceso, accionA, bidireccional]);

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

    if (!proceso) {
      siguientes.proceso = "Elija el proceso.";
    }

    if (!accionA) {
      siguientes.accion_a = "Elija la acción A.";
    }

    if (!accionB) {
      siguientes.accion_b = "Elija la acción B.";
    }

    const nombreRecortado = nombre.trim();
    if (nombreRecortado.length < 3 || nombreRecortado.length > 200) {
      siguientes.nombre = "El nombre debe tener entre 3 y 200 caracteres.";
    }

    const razonRecortada = razon.trim();
    if (razonRecortada.length < 10 || razonRecortada.length > 2000) {
      siguientes.descripcion = "La razón debe tener entre 10 y 2000 caracteres.";
    }

    const hoy = hoyDeNegocio();
    if (!desde || desde < hoy) {
      siguientes.vigente_desde = "La vigencia no puede empezar antes de hoy.";
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
    if (proceso === "") return;

    const cuerpo: ReglaSodEntrada = {
      proceso,
      accion_a: accionA,
      accion_b: accionB,
      bidireccional,
      nombre: nombre.trim(),
      descripcion: razon.trim(),
      vigente_desde: desde,
      vigente_hasta: hasta || null,
    };

    enviandoRef.current = true;
    try {
      const creada = await apiFetch<ReglaSodDetalle>("/gobierno/sod/reglas", {
        method: "POST",
        body: cuerpo,
      });
      notify({ type: "success", title: "Regla registrada en borrador" });
      await queryClient.invalidateQueries({ queryKey: [...CONSULTA_SOD] });
      navigate(`/gobierno/sod/${creada.id}`);
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 422 && error.code === "VALIDATION_ERROR") {
          setErrores({
            nombre: error.fieldErrors.nombre?.[0],
            descripcion: error.fieldErrors.descripcion?.[0],
            accion_a: error.fieldErrors.accion_a?.[0],
            accion_b: error.fieldErrors.accion_b?.[0],
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
            title: "No tiene permiso para registrar reglas",
          });
          return;
        }
      }
      notify({ type: "error", title: "No fue posible registrar la regla" });
    } finally {
      enviandoRef.current = false;
    }
  };

  if (!puedeGestionar) {
    return (
      <PageContent>
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para registrar reglas de segregación de funciones."
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
            { label: "Segregación de funciones", to: "/gobierno/sod" },
          ]}
          title="Nueva regla de segregación de funciones"
        />
        <LoadingState label="Cargando el catálogo de acciones…" />
      </PageContent>
    );
  }

  if (catalogo.isError) {
    return (
      <PageContent>
        <PageHeader
          crumbs={[
            { label: "Gobierno" },
            { label: "Segregación de funciones", to: "/gobierno/sod" },
          ]}
          title="Nueva regla de segregación de funciones"
        />
        <ErrorState
          message="No fue posible cargar el catálogo de acciones."
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

  const cambiarProceso = (valor: ProcesoSod | ""): void => {
    setProceso(valor);
    setAccionA("");
    setAccionB("");
    limpiarError("proceso");
    limpiarError("accion_a");
    limpiarError("accion_b");
  };

  const cambiarAccionA = (valor: string): void => {
    setAccionA(valor);
    if (accionB) {
      const sigueValida = accionesProceso.some(
        (accion) =>
          accion.codigo === accionB &&
          accion.codigo !== valor &&
          (bidireccional || !accion.crea_objeto),
      );
      if (!sigueValida) {
        setAccionB("");
      }
    }
    limpiarError("accion_a");
    limpiarError("accion_b");
  };

  const cambiarBidireccional = (marcado: boolean): void => {
    setBidireccional(marcado);
    if (accionB && !marcado) {
      const accionElegida = accionesProceso.find(
        (accion) => accion.codigo === accionB,
      );
      if (accionElegida?.crea_objeto) {
        setAccionB("");
      }
    }
    limpiarError("accion_b");
  };

  const cambiarAccionB = (valor: string): void => {
    setAccionB(valor);
    limpiarError("accion_b");
  };

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno" },
          { label: "Segregación de funciones", to: "/gobierno/sod" },
        ]}
        title="Nueva regla de segregación de funciones"
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
          label="Proceso"
          htmlFor="sod-proceso"
          required
          error={errores.proceso}
        >
          <select
            id="sod-proceso"
            value={proceso}
            onChange={(evento) =>
              cambiarProceso(evento.target.value as ProcesoSod | "")
            }
            aria-invalid={Boolean(errores.proceso)}
            className={selectClase(errores.proceso)}
          >
            <option value="">Elija el proceso</option>
            {procesos.map((p) => (
              <option key={p.proceso} value={p.proceso}>
                {ETIQUETAS_PROCESO_SOD[p.proceso] ?? p.proceso}
              </option>
            ))}
          </select>
        </FormField>

        <FormField
          label="Acción A"
          htmlFor="sod-accion-a"
          required
          error={errores.accion_a}
          help="Lo que hizo primero"
        >
          <select
            id="sod-accion-a"
            value={accionA}
            disabled={!proceso}
            onChange={(evento) => cambiarAccionA(evento.target.value)}
            aria-invalid={Boolean(errores.accion_a)}
            className={selectClase(errores.accion_a)}
          >
            <option value="">Elija la acción A</option>
            {accionesParaA.map((accion) => (
              <option key={accion.codigo} value={accion.codigo}>
                {accion.etiqueta}
              </option>
            ))}
          </select>
        </FormField>

        <FormField
          label="Acción B"
          htmlFor="sod-accion-b"
          required
          error={errores.accion_b}
          help="Lo que ya no podrá hacer la misma persona"
        >
          <select
            id="sod-accion-b"
            value={accionB}
            disabled={!proceso || !accionA}
            onChange={(evento) => cambiarAccionB(evento.target.value)}
            aria-invalid={Boolean(errores.accion_b)}
            className={selectClase(errores.accion_b)}
          >
            <option value="">Elija la acción B</option>
            {accionesParaB.map((accion) => (
              <option key={accion.codigo} value={accion.codigo}>
                {accion.etiqueta}
              </option>
            ))}
          </select>
        </FormField>

        <FormField
          label="En ambos sentidos"
          htmlFor="sod-bidireccional"
          help="Si se marca, quien hizo B tampoco podrá hacer A"
        >
          <label className="flex items-center gap-2 text-sm text-text-900">
            <input
              id="sod-bidireccional"
              type="checkbox"
              checked={bidireccional}
              onChange={(evento) => cambiarBidireccional(evento.target.checked)}
            />
            En ambos sentidos
          </label>
        </FormField>

        <FormField label="Alcance" htmlFor="sod-alcance">
          <input
            id="sod-alcance"
            type="text"
            value="Sobre el mismo acto o hallazgo"
            readOnly
            disabled
            className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
          />
        </FormField>

        <FormField
          label="Nombre"
          htmlFor="sod-nombre"
          required
          error={errores.nombre}
          help="Nombre corto de la incompatibilidad"
        >
          <TextInput
            id="sod-nombre"
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
          label="Razón"
          htmlFor="sod-descripcion"
          required
          error={errores.descripcion}
          help="Por qué no puede hacer ambas la misma persona"
        >
          <textarea
            id="sod-descripcion"
            value={razon}
            maxLength={2000}
            onChange={(evento) => {
              setRazon(evento.target.value);
              limpiarError("descripcion");
            }}
            aria-invalid={Boolean(errores.descripcion)}
            className={textareaClase(errores.descripcion)}
          />
        </FormField>

        <FormField
          label="Vigente desde"
          htmlFor="sod-desde"
          required
          error={errores.vigente_desde}
        >
          <input
            id="sod-desde"
            type="date"
            value={desde}
            min={hoyDeNegocio()}
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
          htmlFor="sod-hasta"
          error={errores.vigente_hasta}
        >
          <input
            id="sod-hasta"
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
            Registrar regla
          </AsyncButton>
          <Button
            variant="secondary"
            onClick={() => navigate("/gobierno/sod")}
          >
            Cancelar
          </Button>
        </div>
      </form>
    </PageContent>
  );
}
