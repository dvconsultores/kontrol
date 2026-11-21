import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Button } from "@/components/Button";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { formatearInstante } from "@/lib/fecha-de-negocio";
import {
  ACCIONES_COMPETENCIA,
  API_RETENCIONES,
  BASES,
  CONSULTA_CATALOGO_RETENCION,
  CONSULTA_POLITICAS_RETENCION,
  ESTADOS_POLITICA_RETENCION,
  MATERIAS_COMPETENCIA,
  MODOS_REDONDEO,
  RUTA_POLITICAS_RETENCION,
  TIPOS_PERSONA,
  UMBRALES,
  type ElementoCatalogoRetencion,
  type HistoriaRetencion,
  type PoliticaRetencion,
  type ReglaRetencion,
} from "./api";

interface FormularioPolitica {
  codigo: string;
  nombre: string;
  descripcion: string;
  moneda: "VES" | "USD" | "EUR";
  tipo_regla: "INSTITUTIONAL_POLICY" | "OPERATIONAL_CONFIGURATION";
  fuente_descripcion: string;
  fuente_referencia: string;
  aprobador_competencia_accion: string;
  aprobador_competencia_materia: string;
  permite_ajuste: boolean;
  redondeo_decimales: number;
  redondeo_modo: "HALF_UP" | "HALF_EVEN" | "DOWN";
  vigente_desde: string;
  vigente_hasta: string;
}

const FORMULARIO_POLITICA_INICIAL: FormularioPolitica = {
  codigo: "",
  nombre: "",
  descripcion: "",
  moneda: "VES",
  tipo_regla: "INSTITUTIONAL_POLICY",
  fuente_descripcion: "",
  fuente_referencia: "",
  aprobador_competencia_accion: "",
  aprobador_competencia_materia: "",
  permite_ajuste: false,
  redondeo_decimales: 0,
  redondeo_modo: "HALF_UP",
  vigente_desde: "",
  vigente_hasta: "",
};

function reglaVacia(orden: number): ReglaRetencion {
  return {
    orden,
    concept_id: "",
    base_tipo: "MONTO_BRUTO",
    base_porcentaje: null,
    tasa: "",
    umbral_tipo: "NINGUNO",
    umbral_monto: null,
    umbral_multiplo: null,
    umbral_moneda_tasa: null,
    sustraendo: null,
    tope: null,
    condiciones_exigidas: [],
    exclusiones: [],
    tipos_persona: null,
    exige_comprobante: false,
  };
}

export function PoliticaRetencionPage() {
  const { politicaId } = useParams<{ politicaId: string }>();
  const esNueva = !politicaId || politicaId === "nueva";
  const navigate = useNavigate();
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();

  const puedeVer = tiene("gobierno_retenciones:view", "empresa");
  const puedeGestionar = tiene("gobierno_retenciones:manage", "empresa");
  const puedeActuar = tiene("gobierno_retenciones:policy", "empresa");

  const [formulario, setFormulario] = useState<FormularioPolitica>(
    FORMULARIO_POLITICA_INICIAL,
  );
  const [reglas, setReglas] = useState<ReglaRetencion[]>([]);
  const [erroresReglas, setErroresReglas] = useState<Record<string, string[]>>(
    {},
  );
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null);
  const [errorFundamento, setErrorFundamento] = useState<string | null>(null);
  const [errorMotivoCierre, setErrorMotivoCierre] = useState<string | null>(
    null,
  );
  const [guardando, setGuardando] = useState(false);
  const [dialogoActivar, setDialogoActivar] = useState(false);
  const [fundamento, setFundamento] = useState("");
  const [dialogoCerrar, setDialogoCerrar] = useState(false);
  const [motivoCierre, setMotivoCierre] = useState("");
  const [accionando, setAccionando] = useState(false);

  const politica = useQuery({
    queryKey: [...CONSULTA_POLITICAS_RETENCION, "detalle", politicaId],
    queryFn: () =>
      apiFetch<PoliticaRetencion>(`${API_RETENCIONES}/politicas/${politicaId}`),
    enabled: Boolean(activeCompanyId) && Boolean(politicaId) && !esNueva && puedeVer,
    retry: false,
  });

  const historia = useQuery({
    queryKey: [...CONSULTA_POLITICAS_RETENCION, "historia", politicaId],
    queryFn: () =>
      apiFetch<HistoriaRetencion[]>(
        `${API_RETENCIONES}/politicas/${politicaId}/historia`,
      ),
    enabled:
      Boolean(activeCompanyId) && Boolean(politicaId) && !esNueva && puedeVer,
    retry: false,
  });

  const conceptos = useQuery({
    queryKey: [...CONSULTA_CATALOGO_RETENCION, "CONCEPTO", activeCompanyId],
    queryFn: () =>
      apiFetch<ElementoCatalogoRetencion[]>(
        `/gobierno/tesoreria/retenciones/catalogo?tipo=CONCEPTO`,
      ),
    enabled: Boolean(activeCompanyId) && puedeVer,
    retry: false,
  });

  const condiciones = useQuery({
    queryKey: [...CONSULTA_CATALOGO_RETENCION, "CONDICION", activeCompanyId],
    queryFn: () =>
      apiFetch<ElementoCatalogoRetencion[]>(
        `/gobierno/tesoreria/retenciones/catalogo?tipo=CONDICION`,
      ),
    enabled: Boolean(activeCompanyId) && puedeVer,
    retry: false,
  });

  const conceptosActivos =
    conceptos.data?.filter((elemento) => elemento.estado === "ACTIVO") ?? [];
  const condicionesActivas =
    condiciones.data?.filter((elemento) => elemento.estado === "ACTIVO") ?? [];

  const inicializarDesdePolitica = (datos: PoliticaRetencion) => {
    setFormulario({
      codigo: datos.codigo,
      nombre: datos.nombre,
      descripcion: datos.descripcion ?? "",
      moneda: datos.moneda,
      tipo_regla: datos.tipo_regla,
      fuente_descripcion: datos.fuente_descripcion ?? "",
      fuente_referencia: datos.fuente_referencia ?? "",
      aprobador_competencia_accion: datos.aprobador_competencia_accion ?? "",
      aprobador_competencia_materia:
        datos.aprobador_competencia_materia ?? "",
      permite_ajuste: datos.permite_ajuste,
      redondeo_decimales: datos.redondeo_decimales,
      redondeo_modo: datos.redondeo_modo,
      vigente_desde: datos.vigente_desde ?? "",
      vigente_hasta: datos.vigente_hasta ?? "",
    });
    setReglas(datos.reglas ?? []);
  };

  useEffect(() => {
    if (politica.data) {
      inicializarDesdePolitica(politica.data);
    }
  }, [politica.data]);

  const cabecera = (
    <PageHeader
      crumbs={[
        { label: "Gobierno" },
        { label: "Políticas de retención", to: RUTA_POLITICAS_RETENCION },
        { label: esNueva ? "Nueva" : politica.data?.codigo ?? "Detalle" },
      ]}
      title={esNueva ? "Nueva política de retención" : politica.data?.nombre ?? "Política de retención"}
      description="Regla adoptada por el ente. Verificación normativa pendiente (N38): el producto no afirma cumplimiento fiscal."
      status={
        politica.data
          ? ESTADOS_POLITICA_RETENCION[politica.data.estado] ??
            politica.data.estado
          : undefined
      }
    />
  );

  if (!puedeVer) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para ver esta política."
        />
      </PageContent>
    );
  }

  if (!esNueva && politica.isLoading) {
    return (
      <PageContent>
        {cabecera}
        <LoadingState />
      </PageContent>
    );
  }

  if (!esNueva && politica.isError) {
    return (
      <PageContent>
        {cabecera}
        <ErrorState
          title="No se pudo cargar la política"
          message={
            politica.error instanceof ApiError
              ? politica.error.message
              : "Error inesperado"
          }
        />
      </PageContent>
    );
  }


  const actualizarRegla = (
    indice: number,
    campo: keyof ReglaRetencion,
    valor: unknown,
  ) => {
    setReglas((anteriores) =>
      anteriores.map((regla, i) =>
        i === indice ? { ...regla, [campo]: valor } : regla,
      ),
    );
  };

  const quitarRegla = (indice: number) => {
    setReglas((anteriores) =>
      anteriores
        .filter((_, i) => i !== indice)
        .map((regla, i) => ({ ...regla, orden: i + 1 })),
    );
  };

  const añadirRegla = () => {
    setReglas((anteriores) => [
      ...anteriores,
      reglaVacia(anteriores.length + 1),
    ]);
  };

  const guardar = async () => {
    if (guardando) return;
    setGuardando(true);
    setErrorGeneral(null);
    setErroresReglas({});
    const body = {
      ...(esNueva ? { codigo: formulario.codigo } : {}),
      nombre: formulario.nombre,
      descripcion: formulario.descripcion || null,
      moneda: formulario.moneda,
      tipo_regla: formulario.tipo_regla,
      fuente_descripcion: formulario.fuente_descripcion || null,
      fuente_referencia: formulario.fuente_referencia || null,
      aprobador_competencia_accion:
        formulario.aprobador_competencia_accion || null,
      aprobador_competencia_materia:
        formulario.aprobador_competencia_materia || null,
      permite_ajuste: formulario.permite_ajuste,
      redondeo_decimales: formulario.redondeo_decimales,
      redondeo_modo: formulario.redondeo_modo,
      vigente_desde: formulario.vigente_desde || null,
      vigente_hasta: formulario.vigente_hasta || null,
      reglas: reglas.map(({ id, ...resto }) => ({
        ...resto,
        id: id || undefined,
      })),
    };
    try {
      const respuesta = esNueva
        ? await apiFetch<PoliticaRetencion>(`${API_RETENCIONES}/politicas`, {
            method: "POST",
            body,
          })
        : await apiFetch<PoliticaRetencion>(
            `${API_RETENCIONES}/politicas/${politicaId}`,
            {
              method: "PUT",
              body,
              ifMatch: String(politica.data?.version ?? 0),
            },
          );
      notify({ type: "success", title: "Política guardada" });
      await queryClient.invalidateQueries({
        queryKey: CONSULTA_POLITICAS_RETENCION,
      });
      if (esNueva) {
        navigate(`${RUTA_POLITICAS_RETENCION}/${respuesta.id}`, {
          replace: true,
        });
      } else {
        await politica.refetch();
      }
    } catch (error) {
      if (error instanceof ApiError && error.fieldErrors) {
        const errores: Record<string, string[]> = {};
        Object.entries(error.fieldErrors).forEach(([campo, mensajes]) => {
          if (campo.startsWith("reglas.")) {
            errores[campo] = mensajes;
          } else {
            setErrorGeneral((mensajes ?? []).join(" "));
          }
        });
        setErroresReglas(errores);
      } else {
        setErrorGeneral(
          error instanceof ApiError
            ? error.message
            : "No fue posible guardar la política.",
        );
      }
    } finally {
      setGuardando(false);
    }
  };

  const activar = async () => {
    if (accionando) return;
    setAccionando(true);
    try {
      await apiFetch(`${API_RETENCIONES}/politicas/${politicaId}/activar`, {
        method: "POST",
        body: { fundamento },
        ifMatch: String(politica.data?.version ?? 0),
      });
      notify({ type: "success", title: "Política activada" });
      setDialogoActivar(false);
      setFundamento("");
      await Promise.all([
        politica.refetch(),
        queryClient.invalidateQueries({
          queryKey: CONSULTA_POLITICAS_RETENCION,
        }),
      ]);
    } catch (error) {
      notify({
        type: "error",
        title: "Error",
        description:
          error instanceof ApiError
            ? error.message
            : "No fue posible activar la política.",
      });
    } finally {
      setAccionando(false);
    }
  };

  const cerrar = async () => {
    if (accionando) return;
    setAccionando(true);
    try {
      await apiFetch(`${API_RETENCIONES}/politicas/${politicaId}/cerrar`, {
        method: "POST",
        body: { motivo: motivoCierre },
        ifMatch: String(politica.data?.version ?? 0),
      });
      notify({ type: "success", title: "Política cerrada" });
      setDialogoCerrar(false);
      setMotivoCierre("");
      await Promise.all([
        politica.refetch(),
        queryClient.invalidateQueries({
          queryKey: CONSULTA_POLITICAS_RETENCION,
        }),
      ]);
    } catch (error) {
      notify({
        type: "error",
        title: "Error",
        description:
          error instanceof ApiError
            ? error.message
            : "No fue posible cerrar la política.",
      });
    } finally {
      setAccionando(false);
    }
  };

  const nuevaVersion = async () => {
    if (accionando) return;
    setAccionando(true);
    try {
      const respuesta = await apiFetch<PoliticaRetencion>(
        `${API_RETENCIONES}/politicas/${politicaId}/nueva-version`,
        { method: "POST" },
      );
      notify({ type: "success", title: "Nueva versión creada" });
      await queryClient.invalidateQueries({
        queryKey: CONSULTA_POLITICAS_RETENCION,
      });
      navigate(`${RUTA_POLITICAS_RETENCION}/${respuesta.id}`);
    } catch (error) {
      notify({
        type: "error",
        title: "Error",
        description:
          error instanceof ApiError
            ? error.message
            : "No fue posible crear una nueva versión.",
      });
    } finally {
      setAccionando(false);
    }
  };

  const puedeEditar =
    esNueva ||
    (puedeGestionar && politica.data?.estado === "BORRADOR");

  return (
    <PageContent>
      {cabecera}

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-6">
          <section
            aria-labelledby="datos-generales-titulo"
            className="rounded-lg border border-border-default p-4"
          >
            <h2
              id="datos-generales-titulo"
              className="text-base font-semibold text-text-900"
            >
              Datos generales
            </h2>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {esNueva && (
                <FormField label="Código" htmlFor="politica-codigo">
                  <TextInput
                    id="politica-codigo"
                    value={formulario.codigo}
                    onChange={(event) =>
                      setFormulario({
                        ...formulario,
                        codigo: event.target.value,
                      })
                    }
                    disabled={!puedeEditar}
                  />
                </FormField>
              )}
              <FormField label="Nombre" htmlFor="politica-nombre">
                <TextInput
                  id="politica-nombre"
                  value={formulario.nombre}
                  onChange={(event) =>
                    setFormulario({
                      ...formulario,
                      nombre: event.target.value,
                    })
                  }
                  disabled={!puedeEditar}
                />
              </FormField>
              <FormField
                label="Descripción"
                htmlFor="politica-descripcion"
              >
                <TextInput
                  id="politica-descripcion"
                  value={formulario.descripcion}
                  onChange={(event) =>
                    setFormulario({
                      ...formulario,
                      descripcion: event.target.value,
                    })
                  }
                  disabled={!puedeEditar}
                />
              </FormField>
              <FormField label="Moneda" htmlFor="politica-moneda">
                <select
                  id="politica-moneda"
                  className="w-full rounded-md border border-border-default px-3 py-2"
                  value={formulario.moneda}
                  onChange={(event) =>
                    setFormulario({
                      ...formulario,
                      moneda: event.target.value as "VES" | "USD" | "EUR",
                    })
                  }
                  disabled={!puedeEditar}
                >
                  <option value="VES">VES</option>
                  <option value="USD">USD</option>
                  <option value="EUR">EUR</option>
                </select>
              </FormField>
              <FormField label="Clasificación" htmlFor="politica-tipo-regla">
                <select
                  id="politica-tipo-regla"
                  className="w-full rounded-md border border-border-default px-3 py-2"
                  value={formulario.tipo_regla}
                  onChange={(event) =>
                    setFormulario({
                      ...formulario,
                      tipo_regla: event.target.value as
                        | "INSTITUTIONAL_POLICY"
                        | "OPERATIONAL_CONFIGURATION",
                    })
                  }
                  disabled={!puedeEditar}
                >
                  <option value="INSTITUTIONAL_POLICY">
                    Política institucional
                  </option>
                  <option value="OPERATIONAL_CONFIGURATION">
                    Configuración operativa
                  </option>
                </select>
              </FormField>
              <FormField
                label="Fuente (descripción)"
                htmlFor="politica-fuente-descripcion"
              >
                <TextInput
                  id="politica-fuente-descripcion"
                  value={formulario.fuente_descripcion}
                  onChange={(event) =>
                    setFormulario({
                      ...formulario,
                      fuente_descripcion: event.target.value,
                    })
                  }
                  disabled={!puedeEditar}
                />
              </FormField>
              <FormField
                label="Referencia (artículo)"
                htmlFor="politica-fuente-referencia"
              >
                <TextInput
                  id="politica-fuente-referencia"
                  value={formulario.fuente_referencia}
                  onChange={(event) =>
                    setFormulario({
                      ...formulario,
                      fuente_referencia: event.target.value,
                    })
                  }
                  disabled={!puedeEditar}
                />
              </FormField>
              <FormField
                label="Competencia del aprobador"
                htmlFor="politica-competencia-accion"
              >
                <div className="grid gap-2 sm:grid-cols-2">
                  <select
                    id="politica-competencia-accion"
                    aria-label="Acción de la competencia del aprobador"
                    className="w-full rounded-md border border-border-default px-3 py-2"
                    value={formulario.aprobador_competencia_accion}
                    onChange={(event) =>
                      setFormulario({
                        ...formulario,
                        aprobador_competencia_accion: event.target.value,
                      })
                    }
                    disabled={!puedeEditar}
                  >
                    <option value="">Acción…</option>
                    {ACCIONES_COMPETENCIA.map((accion) => (
                      <option key={accion} value={accion}>
                        {accion}
                      </option>
                    ))}
                  </select>
                  <select
                    id="politica-competencia-materia"
                    aria-label="Materia de la competencia del aprobador"
                    className="w-full rounded-md border border-border-default px-3 py-2"
                    value={formulario.aprobador_competencia_materia}
                    onChange={(event) =>
                      setFormulario({
                        ...formulario,
                        aprobador_competencia_materia: event.target.value,
                      })
                    }
                    disabled={!puedeEditar}
                  >
                    <option value="">Materia…</option>
                    {MATERIAS_COMPETENCIA.map((materia) => (
                      <option key={materia} value={materia}>
                        {materia}
                      </option>
                    ))}
                  </select>
                </div>
              </FormField>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="politica-permite-ajuste"
                  checked={formulario.permite_ajuste}
                  onChange={(event) =>
                    setFormulario({
                      ...formulario,
                      permite_ajuste: event.target.checked,
                    })
                  }
                  disabled={!puedeEditar}
                />
                <label
                  htmlFor="politica-permite-ajuste"
                  className="text-sm text-text-700"
                >
                  Permite ajustar el monto aprobado
                </label>
              </div>
              <FormField
                label="Decimales de redondeo"
                htmlFor="politica-redondeo-decimales"
              >
                <select
                  id="politica-redondeo-decimales"
                  className="w-full rounded-md border border-border-default px-3 py-2"
                  value={formulario.redondeo_decimales}
                  onChange={(event) =>
                    setFormulario({
                      ...formulario,
                      redondeo_decimales: Number(event.target.value),
                    })
                  }
                  disabled={!puedeEditar}
                >
                  {[0, 1, 2, 3, 4].map((valor) => (
                    <option key={valor} value={valor}>
                      {valor}
                    </option>
                  ))}
                </select>
              </FormField>
              <FormField label="Modo de redondeo" htmlFor="politica-redondeo-modo">
                <select
                  id="politica-redondeo-modo"
                  className="w-full rounded-md border border-border-default px-3 py-2"
                  value={formulario.redondeo_modo}
                  onChange={(event) =>
                    setFormulario({
                      ...formulario,
                      redondeo_modo: event.target.value as
                        | "HALF_UP"
                        | "HALF_EVEN"
                        | "DOWN",
                    })
                  }
                  disabled={!puedeEditar}
                >
                  {Object.entries(MODOS_REDONDEO).map(([valor, texto]) => (
                    <option key={valor} value={valor}>
                      {texto}
                    </option>
                  ))}
                </select>
              </FormField>
              <FormField
                label="Vigente desde"
                htmlFor="politica-vigente-desde"
              >
                <TextInput
                  id="politica-vigente-desde"
                  value={formulario.vigente_desde}
                  onChange={(event) =>
                    setFormulario({
                      ...formulario,
                      vigente_desde: event.target.value,
                    })
                  }
                  disabled={!puedeEditar}
                />
              </FormField>
              <FormField
                label="Vigente hasta"
                htmlFor="politica-vigente-hasta"
              >
                <TextInput
                  id="politica-vigente-hasta"
                  value={formulario.vigente_hasta}
                  onChange={(event) =>
                    setFormulario({
                      ...formulario,
                      vigente_hasta: event.target.value,
                    })
                  }
                  disabled={!puedeEditar}
                />
              </FormField>
            </div>
          </section>

          <section
            aria-labelledby="reglas-titulo"
            className="rounded-lg border border-border-default p-4"
          >
            <h2 id="reglas-titulo" className="text-base font-semibold text-text-900">
              Reglas
            </h2>
            <div className="mt-4 space-y-4">
              {reglas.map((regla, indice) => (
                <fieldset
                  key={indice}
                  className="rounded-md border border-border-default p-3"
                >
                  <legend className="px-2 text-sm font-medium text-text-700">
                    Regla {indice + 1}
                  </legend>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <FormField
                      label="Concepto"
                      htmlFor={`regla-${indice}-concepto`}
                    >
                      <select
                        id={`regla-${indice}-concepto`}
                        className="w-full rounded-md border border-border-default px-3 py-2"
                        value={regla.concept_id}
                        onChange={(event) =>
                          actualizarRegla(
                            indice,
                            "concept_id",
                            event.target.value,
                          )
                        }
                        disabled={!puedeEditar}
                      >
                        <option value="">Seleccione…</option>
                        {conceptosActivos.map((concepto) => (
                          <option key={concepto.id} value={concepto.id}>
                            {concepto.codigo} — {concepto.nombre}
                          </option>
                        ))}
                      </select>
                      {erroresReglas[`reglas.${indice}.concept_id`] && (
                        <p role="alert" className="mt-1 text-sm text-error-600">
                          {erroresReglas[`reglas.${indice}.concept_id`].join(
                            " ",
                          )}
                        </p>
                      )}
                    </FormField>
                    <FormField label="Base" htmlFor={`regla-${indice}-base`}>
                      <select
                        id={`regla-${indice}-base`}
                        className="w-full rounded-md border border-border-default px-3 py-2"
                        value={regla.base_tipo}
                        onChange={(event) =>
                          actualizarRegla(
                            indice,
                            "base_tipo",
                            event.target.value,
                          )
                        }
                        disabled={!puedeEditar}
                      >
                        {Object.entries(BASES).map(([valor, texto]) => (
                          <option key={valor} value={valor}>
                            {texto}
                          </option>
                        ))}
                      </select>
                    </FormField>
                    {regla.base_tipo === "PORCENTAJE_DEL_BRUTO" && (
                      <FormField
                        label="Porcentaje de la base"
                        htmlFor={`regla-${indice}-base-porcentaje`}
                      >
                        <TextInput
                          id={`regla-${indice}-base-porcentaje`}
                          value={regla.base_porcentaje ?? ""}
                          onChange={(event) =>
                            actualizarRegla(
                              indice,
                              "base_porcentaje",
                              event.target.value || null,
                            )
                          }
                          disabled={!puedeEditar}
                        />
                      </FormField>
                    )}
                    <FormField label="Alícuota %" htmlFor={`regla-${indice}-tasa`}>
                      <TextInput
                        id={`regla-${indice}-tasa`}
                        value={regla.tasa}
                        onChange={(event) =>
                          actualizarRegla(indice, "tasa", event.target.value)
                        }
                        disabled={!puedeEditar}
                      />
                      {erroresReglas[`reglas.${indice}.tasa`] && (
                        <p role="alert" className="mt-1 text-sm text-error-600">
                          {erroresReglas[`reglas.${indice}.tasa`].join(" ")}
                        </p>
                      )}
                    </FormField>
                    <FormField
                      label="Umbral"
                      htmlFor={`regla-${indice}-umbral-tipo`}
                    >
                      <select
                        id={`regla-${indice}-umbral-tipo`}
                        className="w-full rounded-md border border-border-default px-3 py-2"
                        value={regla.umbral_tipo}
                        onChange={(event) =>
                          actualizarRegla(
                            indice,
                            "umbral_tipo",
                            event.target.value,
                          )
                        }
                        disabled={!puedeEditar}
                      >
                        {Object.entries(UMBRALES).map(([valor, texto]) => {
                          const deshabilitado =
                            valor === "MULTIPLO_TASA" &&
                            formulario.moneda !== "VES";
                          return (
                            <option
                              key={valor}
                              value={valor}
                              disabled={deshabilitado}
                            >
                              {texto}
                            </option>
                          );
                        })}
                      </select>
                    </FormField>
                    {regla.umbral_tipo === "MONTO" && (
                      <FormField
                        label="Monto del umbral"
                        htmlFor={`regla-${indice}-umbral-monto`}
                      >
                        <TextInput
                          id={`regla-${indice}-umbral-monto`}
                          value={regla.umbral_monto ?? ""}
                          onChange={(event) =>
                            actualizarRegla(
                              indice,
                              "umbral_monto",
                              event.target.value || null,
                            )
                          }
                          disabled={!puedeEditar}
                        />
                      </FormField>
                    )}
                    {regla.umbral_tipo === "MULTIPLO_TASA" && (
                      <>
                        <FormField
                          label="Múltiplo"
                          htmlFor={`regla-${indice}-umbral-multiplo`}
                        >
                          <TextInput
                            id={`regla-${indice}-umbral-multiplo`}
                            value={regla.umbral_multiplo ?? ""}
                            onChange={(event) =>
                              actualizarRegla(
                                indice,
                                "umbral_multiplo",
                                event.target.value || null,
                              )
                            }
                            disabled={!puedeEditar}
                          />
                        </FormField>
                        <FormField
                          label="Moneda de la tasa"
                          htmlFor={`regla-${indice}-umbral-moneda`}
                        >
                          <select
                            id={`regla-${indice}-umbral-moneda`}
                            className="w-full rounded-md border border-border-default px-3 py-2"
                            value={regla.umbral_moneda_tasa ?? ""}
                            onChange={(event) =>
                              actualizarRegla(
                                indice,
                                "umbral_moneda_tasa",
                                event.target.value || null,
                              )
                            }
                            disabled={!puedeEditar}
                          >
                            <option value="">Seleccione…</option>
                            <option value="USD">USD</option>
                            <option value="EUR">EUR</option>
                          </select>
                        </FormField>
                      </>
                    )}
                    <FormField
                      label="Sustraendo"
                      htmlFor={`regla-${indice}-sustraendo`}
                    >
                      <TextInput
                        id={`regla-${indice}-sustraendo`}
                        value={regla.sustraendo ?? ""}
                        onChange={(event) =>
                          actualizarRegla(
                            indice,
                            "sustraendo",
                            event.target.value || null,
                          )
                        }
                        disabled={!puedeEditar}
                      />
                    </FormField>
                    <FormField label="Tope" htmlFor={`regla-${indice}-tope`}>
                      <TextInput
                        id={`regla-${indice}-tope`}
                        value={regla.tope ?? ""}
                        onChange={(event) =>
                          actualizarRegla(
                            indice,
                            "tope",
                            event.target.value || null,
                          )
                        }
                        disabled={!puedeEditar}
                      />
                    </FormField>
                  </div>

                  <div className="mt-3 grid gap-3 sm:grid-cols-2">
                    <fieldset>
                      <legend className="text-sm font-medium text-text-700">
                        Condiciones exigidas
                      </legend>
                      <div className="mt-1 space-y-1">
                        {condicionesActivas.map((condicion) => (
                          <label
                            key={condicion.id}
                            className="flex items-center gap-2 text-sm"
                          >
                            <input
                              type="checkbox"
                              checked={regla.condiciones_exigidas.includes(
                                condicion.codigo,
                              )}
                              onChange={(event) => {
                                const seleccionados = event.target.checked
                                  ? [
                                      ...regla.condiciones_exigidas,
                                      condicion.codigo,
                                    ]
                                  : regla.condiciones_exigidas.filter(
                                      (codigo) => codigo !== condicion.codigo,
                                    );
                                actualizarRegla(
                                  indice,
                                  "condiciones_exigidas",
                                  seleccionados,
                                );
                              }}
                              disabled={!puedeEditar}
                            />
                            {condicion.codigo} — {condicion.nombre}
                          </label>
                        ))}
                      </div>
                    </fieldset>
                    <fieldset>
                      <legend className="text-sm font-medium text-text-700">
                        Exclusiones
                      </legend>
                      <div className="mt-1 space-y-1">
                        {condicionesActivas.map((condicion) => (
                          <label
                            key={condicion.id}
                            className="flex items-center gap-2 text-sm"
                          >
                            <input
                              type="checkbox"
                              checked={regla.exclusiones.includes(
                                condicion.codigo,
                              )}
                              onChange={(event) => {
                                const seleccionados = event.target.checked
                                  ? [...regla.exclusiones, condicion.codigo]
                                  : regla.exclusiones.filter(
                                      (codigo) => codigo !== condicion.codigo,
                                    );
                                actualizarRegla(
                                  indice,
                                  "exclusiones",
                                  seleccionados,
                                );
                              }}
                              disabled={!puedeEditar}
                            />
                            {condicion.codigo} — {condicion.nombre}
                          </label>
                        ))}
                      </div>
                    </fieldset>
                    <fieldset>
                      <legend className="text-sm font-medium text-text-700">
                        Tipos de persona
                      </legend>
                      <div className="mt-1 space-y-1">
                        {Object.entries(TIPOS_PERSONA).map(([valor, texto]) => (
                          <label
                            key={valor}
                            className="flex items-center gap-2 text-sm"
                          >
                            <input
                              type="checkbox"
                              checked={
                                regla.tipos_persona?.includes(
                                  valor as "NATURAL" | "JURIDICA",
                                ) ?? false
                              }
                              onChange={(event) => {
                                const actuales = regla.tipos_persona ?? [];
                                const siguientes = event.target.checked
                                  ? [
                                      ...actuales,
                                      valor as "NATURAL" | "JURIDICA",
                                    ]
                                  : actuales.filter(
                                      (tipo) => tipo !== valor,
                                    );
                                actualizarRegla(
                                  indice,
                                  "tipos_persona",
                                  siguientes.length > 0 ? siguientes : null,
                                );
                              }}
                              disabled={!puedeEditar}
                            />
                            {texto}
                          </label>
                        ))}
                      </div>
                    </fieldset>
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        id={`regla-${indice}-exige-comprobante`}
                        checked={regla.exige_comprobante}
                        onChange={(event) =>
                          actualizarRegla(
                            indice,
                            "exige_comprobante",
                            event.target.checked,
                          )
                        }
                        disabled={!puedeEditar}
                      />
                      <label
                        htmlFor={`regla-${indice}-exige-comprobante`}
                        className="text-sm text-text-700"
                      >
                        Exige comprobante
                      </label>
                    </div>
                  </div>

                  <div className="mt-3">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => quitarRegla(indice)}
                      disabled={!puedeEditar}
                    >
                      Quitar regla
                    </Button>
                  </div>
                </fieldset>
              ))}
              {puedeEditar && (
                <div className="mt-4">
                  <Button variant="secondary" onClick={añadirRegla}>
                    Añadir regla
                  </Button>
                </div>
              )}
            </div>
          </section>

          {errorGeneral && (
            <p role="alert" className="text-sm text-error-600">
              {errorGeneral}
            </p>
          )}

          {puedeEditar && (
            <div className="flex justify-end">
              <Button variant="primary" onClick={guardar} disabled={guardando}>
                Guardar política
              </Button>
            </div>
          )}
        </div>

        <aside className="space-y-6">
          <div className="rounded-lg border border-border-default p-4">
            <h2 className="text-base font-semibold text-text-900">Acciones</h2>
            <div className="mt-3 space-y-2">
              {puedeActuar && politica.data?.estado === "BORRADOR" && (
                <Button
                  variant="primary"
                  className="w-full"
                  onClick={() => setDialogoActivar(true)}
                >
                  Activar
                </Button>
              )}
              {puedeActuar && politica.data?.estado === "VIGENTE" && (
                <Button
                  variant="secondary"
                  className="w-full"
                  onClick={() => setDialogoCerrar(true)}
                >
                  Cerrar
                </Button>
              )}
              {puedeGestionar &&
                (politica.data?.estado === "VIGENTE" ||
                  politica.data?.estado === "CERRADA") && (
                  <Button
                    variant="secondary"
                    className="w-full"
                    onClick={nuevaVersion}
                    disabled={accionando}
                  >
                    Nueva versión
                  </Button>
                )}
            </div>
          </div>

          <section
            aria-labelledby="historia-titulo"
            className="rounded-lg border border-border-default p-4"
          >
            <h2
              id="historia-titulo"
              className="text-base font-semibold text-text-900"
            >
              Historia
            </h2>
            {historia.isLoading ? (
              <LoadingState />
            ) : historia.isError ? (
              <p className="text-sm text-error-600">
                No se pudo cargar la historia.
              </p>
            ) : historia.data && historia.data.length === 0 ? (
              <p className="mt-2 text-sm text-text-500">
                Sin eventos registrados.
              </p>
            ) : (
              <div
                role="region"
                aria-label="Historia de la política (desplazable)"
                tabIndex={0}
                className="overflow-x-auto"
              >
                <table
                  className="w-full text-sm"
                  aria-label="Historia de la política"
                >
                  <thead>
                    <tr>
                      <th className="px-3 py-2 text-left">Evento</th>
                      <th className="px-3 py-2 text-left">Versión</th>
                      <th className="px-3 py-2 text-left">Fecha</th>
                    </tr>
                  </thead>
                  <tbody>
                    {historia.data?.map((evento) => (
                      <tr key={evento.id}>
                        <td className="px-3 py-2">{evento.evento}</td>
                        <td className="px-3 py-2">{evento.numero_version}</td>
                        <td className="px-3 py-2">
                          {formatearInstante(evento.created_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </aside>
      </div>

      <ConfirmationDialog
        open={dialogoActivar}
        onCancel={() => setDialogoActivar(false)}
        onConfirm={async () => {
          if (fundamento.trim().length < 20) {
            setErrorFundamento(
              "El fundamento debe tener al menos 20 caracteres.",
            );
            return;
          }
          await activar();
        }}
        title="Activar política"
        confirmLabel="Activar"
      >
        <FormField label="Fundamento" htmlFor="fundamento-activar">
          <textarea
            id="fundamento-activar"
            className="w-full rounded-md border border-border-default px-3 py-2"
            value={fundamento}
            onChange={(event) => setFundamento(event.target.value)}
            rows={3}
          />
        </FormField>
        {errorFundamento && (
          <p role="alert" className="text-sm text-error">
            {errorFundamento}
          </p>
        )}
      </ConfirmationDialog>

      <ConfirmationDialog
        open={dialogoCerrar}
        onCancel={() => setDialogoCerrar(false)}
        onConfirm={async () => {
          if (motivoCierre.trim().length < 10) {
            setErrorMotivoCierre(
              "El motivo debe tener al menos 10 caracteres.",
            );
            return;
          }
          await cerrar();
        }}
        title="Cerrar política"
        confirmLabel="Cerrar"
      >
        <FormField label="Motivo" htmlFor="motivo-cierre">
          <textarea
            id="motivo-cierre"
            className="w-full rounded-md border border-border-default px-3 py-2"
            value={motivoCierre}
            onChange={(event) => setMotivoCierre(event.target.value)}
            rows={3}
          />
        </FormField>
        {errorMotivoCierre && (
          <p role="alert" className="text-sm text-error">{errorMotivoCierre}</p>
        )}
      </ConfirmationDialog>
    </PageContent>
  );
}
