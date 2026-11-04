import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { DateInput } from "@/components/DateInput";

import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { formatearFecha } from "@/i18n";
import { formatearFechaDeNegocio, hoyDeNegocio } from "@/lib/fecha-de-negocio";
import {
  AccionCorrectiva,
  AccionNueva,
  AvanceNuevo,
  CargosResponsables,
  CONSULTA_HALLAZGOS,
  HallazgoDetalle,
  RESOURCE_TYPE_ACCION_CORRECTIVA,
  ETIQUETA_ESTADO_ACCION,
} from "@/modules/gobierno/api";
import { AdjuntosPanel } from "@/modules/documentos/AdjuntosPanel";

export interface PlanDeAccionProps {
  hallazgo: HallazgoDetalle;
  onActualizado: (detalle: HallazgoDetalle) => void;
  onError: (e: unknown) => void;
}

type ErroresRecomendacion = Partial<Record<"texto" | "general", string>>;
type ErroresAccion = Partial<
  Record<"descripcion" | "cargo_id" | "fecha_objetivo" | "general", string>
>;
type ErroresAvance = Partial<
  Record<"nota" | "porcentaje" | "documento_id" | "general", string>
>;

type FormularioAccion = {
  descripcion: string;
  cargo_id: string;
  fecha_objetivo: string;
};

type FormularioAvance = {
  nota: string;
  porcentaje: string;
  documento_id: string;
};

const FORMULARIO_ACCION_INICIAL: FormularioAccion = {
  descripcion: "",
  cargo_id: "",
  fecha_objetivo: "",
};

const FORMULARIO_AVANCE_INICIAL: FormularioAvance = {
  nota: "",
  porcentaje: "",
  documento_id: "",
};

export function PlanDeAccion({
  hallazgo,
  onActualizado,
  onError,
}: PlanDeAccionProps): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { tiene } = useAutoridad();
  const puedeManage = tiene("gobierno_hallazgos:manage", "empresa");

  const [textoRecomendacion, setTextoRecomendacion] = useState("");
  const [erroresRecomendacion, setErroresRecomendacion] =
    useState<ErroresRecomendacion>({});

  const [formulariosAccion, setFormulariosAccion] = useState<
    Record<string, FormularioAccion>
  >({});
  const [erroresAccion, setErroresAccion] = useState<
    Record<string, ErroresAccion>
  >({});

  const [formulariosAvance, setFormulariosAvance] = useState<
    Record<string, FormularioAvance>
  >({});
  const [erroresAvance, setErroresAvance] = useState<
    Record<string, ErroresAvance>
  >({});

  const consultaCargos = useQuery({
    queryKey: ["gobierno", "hallazgos", "cargos-responsables"],
    queryFn: () =>
      apiFetch<CargosResponsables>("/gobierno/hallazgos/cargos-responsables"),
    retry: false,
  });

  const accionesPorRecomendacion = useMemo(() => {
    const mapa = new Map<string, AccionCorrectiva[]>();
    for (const accion of hallazgo.acciones) {
      const actuales = mapa.get(accion.recomendacion_id) ?? [];
      actuales.push(accion);
      mapa.set(accion.recomendacion_id, actuales);
    }
    return mapa;
  }, [hallazgo.acciones]);

  const cargos = consultaCargos.data?.items ?? [];
  const hoy = hoyDeNegocio();

  const limpiarErroresRecomendacion = () => {
    setErroresRecomendacion({});
  };

  const actualizarFormularioAccion = (
    recomendacionId: string,
    cambios: Partial<FormularioAccion>,
  ) => {
    setFormulariosAccion((previos) => ({
      ...previos,
      [recomendacionId]: {
        ...FORMULARIO_ACCION_INICIAL,
        ...(previos[recomendacionId] ?? {}),
        ...cambios,
      },
    }));
  };

  const actualizarFormularioAvance = (
    accionId: string,
    cambios: Partial<FormularioAvance>,
  ) => {
    setFormulariosAvance((previos) => ({
      ...previos,
      [accionId]: {
        ...FORMULARIO_AVANCE_INICIAL,
        ...(previos[accionId] ?? {}),
        ...cambios,
      },
    }));
  };

  const manejarErrorEscritura = (
    error: unknown,
    campos: string[],
    setErrores: (errores: Record<string, string>) => void,
  ) => {
    if (error instanceof ApiError) {
      if (error.status === 409 && error.code === "GOV_FINDING_STALE") {
        onError(error);
        return;
      }
      if (error.status === 422 && error.code === "VALIDATION_ERROR") {
        const erroresCampo: Record<string, string> = {};
        for (const campo of campos) {
          const primerError = error.fieldErrors[campo]?.[0];
          if (primerError) {
            erroresCampo[campo] = primerError;
          }
        }
        setErrores(erroresCampo);
        return;
      }
      if (error.status === 422) {
        setErrores({ general: error.message });
        return;
      }
      if (error.status === 403) {
        notify({
          type: "error",
          title: "No tiene permiso para realizar esta acción",
        });
        return;
      }
    }
    onError(error);
  };

  const enviarRecomendacion = async (): Promise<void> => {
    if (!puedeManage) return;
    const texto = textoRecomendacion.trim();
    const errores: ErroresRecomendacion = {};
    if (texto.length < 10 || texto.length > 2000) {
      errores.texto = "La recomendación debe tener entre 10 y 2000 caracteres.";
    }
    setErroresRecomendacion(errores);
    if (Object.keys(errores).length > 0) return;

    try {
      const detalle = await apiFetch<HallazgoDetalle>(
        `/gobierno/hallazgos/${hallazgo.id}/recomendaciones`,
        {
          method: "POST",
          body: { texto },
          ifMatch: String(hallazgo.version),
        },
      );
      setTextoRecomendacion("");
      setErroresRecomendacion({});
      onActualizado(detalle);
      notify({ type: "success", title: "Recomendación añadida" });
    } catch (error) {
      manejarErrorEscritura(error, ["texto"], (erroresNuevos: Record<string, string>) =>
        setErroresRecomendacion(erroresNuevos),
      );
    }
  };

  const enviarAccion = async (recomendacionId: string): Promise<void> => {
    if (!puedeManage) return;
    const formulario = formulariosAccion[recomendacionId] ?? FORMULARIO_ACCION_INICIAL;
    const descripcion = formulario.descripcion.trim();
    const errores: ErroresAccion = {};
    if (descripcion.length < 10 || descripcion.length > 2000) {
      errores.descripcion = "La acción debe tener entre 10 y 2000 caracteres.";
    }
    if (!formulario.cargo_id) {
      errores.cargo_id = "Seleccione un cargo responsable.";
    }
    if (!formulario.fecha_objetivo) {
      errores.fecha_objetivo = "Indique la fecha objetivo.";
    } else if (formulario.fecha_objetivo < hoy) {
      errores.fecha_objetivo = "La fecha objetivo no puede ser anterior a hoy.";
    }
    setErroresAccion((previos) => ({
      ...previos,
      [recomendacionId]: errores,
    }));
    if (Object.keys(errores).length > 0) return;

    const cuerpo: AccionNueva = {
      recomendacion_id: recomendacionId,
      descripcion,
      cargo_id: formulario.cargo_id,
      fecha_objetivo: formulario.fecha_objetivo,
    };

    try {
      const detalle = await apiFetch<HallazgoDetalle>(
        `/gobierno/hallazgos/${hallazgo.id}/acciones`,
        {
          method: "POST",
          body: cuerpo,
          ifMatch: String(hallazgo.version),
        },
      );
      setFormulariosAccion((previos) => {
        const copia = { ...previos };
        delete copia[recomendacionId];
        return copia;
      });
      setErroresAccion((previos) => {
        const copia = { ...previos };
        delete copia[recomendacionId];
        return copia;
      });
      onActualizado(detalle);
      notify({ type: "success", title: "Acción añadida" });
    } catch (error) {
      manejarErrorEscritura(error, ["descripcion", "cargo_id", "fecha_objetivo"], (erroresNuevos: Record<string, string>) =>
        setErroresAccion((previos) => ({
          ...previos,
          [recomendacionId]: erroresNuevos,
        })),
      );
    }
  };

  const enviarAvance = async (accion: AccionCorrectiva): Promise<void> => {
    if (!puedeManage) return;
    const formulario = formulariosAvance[accion.id] ?? FORMULARIO_AVANCE_INICIAL;
    const nota = formulario.nota.trim();
    const porcentajeNumero = Number(formulario.porcentaje);
    const errores: ErroresAvance = {};
    if (nota.length < 10 || nota.length > 2000) {
      errores.nota = "La nota debe tener entre 10 y 2000 caracteres.";
    }
    if (
      formulario.porcentaje === "" ||
      !Number.isInteger(porcentajeNumero) ||
      porcentajeNumero < accion.porcentaje ||
      porcentajeNumero > 100
    ) {
      errores.porcentaje = `Indique un porcentaje entero entre ${accion.porcentaje} y 100.`;
    }
    setErroresAvance((previos) => ({
      ...previos,
      [accion.id]: errores,
    }));
    if (Object.keys(errores).length > 0) return;

    const cuerpo: AvanceNuevo = {
      nota,
      porcentaje: porcentajeNumero,
    };
    if (formulario.documento_id) {
      cuerpo.documento_id = formulario.documento_id;
    }

    try {
      const detalle = await apiFetch<HallazgoDetalle>(
        `/gobierno/hallazgos/${hallazgo.id}/acciones/${accion.id}/avances`,
        {
          method: "POST",
          body: cuerpo,
          ifMatch: String(hallazgo.version),
        },
      );
      setFormulariosAvance((previos) => {
        const copia = { ...previos };
        delete copia[accion.id];
        return copia;
      });
      setErroresAvance((previos) => {
        const copia = { ...previos };
        delete copia[accion.id];
        return copia;
      });
      onActualizado(detalle);
      notify({ type: "success", title: "Avance registrado" });
    } catch (error) {
      manejarErrorEscritura(error, ["nota", "porcentaje", "documento_id"], (erroresNuevos: Record<string, string>) =>
        setErroresAvance((previos) => ({
          ...previos,
          [accion.id]: erroresNuevos,
        })),
      );
    }
  };

  const seccionRecomendaciones = (
    <section aria-labelledby="recomendaciones-titulo">
      <h2 id="recomendaciones-titulo">Recomendaciones</h2>
      {hallazgo.recomendaciones.length === 0 ? (
        <p>No hay recomendaciones registradas.</p>
      ) : (
        <ol>
          {hallazgo.recomendaciones.map((recomendacion) => (
            <li key={recomendacion.id}>
              <article>
                <h3>Recomendación {recomendacion.orden}</h3>
                <p>{recomendacion.texto}</p>
                <p>
                  {formatearFecha(recomendacion.created_at)} ·{" "}
                  {recomendacion.created_by}
                </p>
              </article>
            </li>
          ))}
        </ol>
      )}
      {hallazgo.estado === "ABIERTO" && puedeManage && (
        <>
          <FormField
            label="Recomendación"
            htmlFor="nueva-recomendacion"
            required
            error={erroresRecomendacion.texto}
            help="Entre 10 y 2000 caracteres."
          >
            <textarea
              id="nueva-recomendacion"
              value={textoRecomendacion}
              onChange={(evento) => {
                setTextoRecomendacion(evento.target.value);
                limpiarErroresRecomendacion();
              }}
              className="min-h-24 w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              required
            />
          </FormField>
          {erroresRecomendacion.general && (
            <p role="alert">{erroresRecomendacion.general}</p>
          )}
          <AsyncButton
            onClick={enviarRecomendacion}
            loadingText="Guardando…"
            idleText="Añadir recomendación"
            variant="primary"
          >
            Añadir recomendación
          </AsyncButton>
        </>
      )}
    </section>
  );

  return (
    <>
      {seccionRecomendaciones}
    <section aria-labelledby="plan-accion-titulo">
      <h2 id="plan-accion-titulo">Plan de acción</h2>
      {hallazgo.recomendaciones.length === 0 ? (
        <p>No hay recomendaciones registradas.</p>
      ) : (
        hallazgo.recomendaciones.map((recomendacion) => {
          const acciones = accionesPorRecomendacion.get(recomendacion.id) ?? [];
          return (
            <section key={recomendacion.id} aria-labelledby={`recomendacion-${recomendacion.id}`}>
              <h3 id={`recomendacion-${recomendacion.id}`}>
                Recomendación {recomendacion.orden}
              </h3>
              <p>{recomendacion.texto}</p>
              {acciones.length === 0 ? (
                <p>No hay acciones registradas para esta recomendación.</p>
              ) : (
                acciones.map((accion) => (
                  <article key={accion.id} aria-labelledby={`accion-${accion.id}`}>
                    <h4 id={`accion-${accion.id}`}>Acción {accion.orden}</h4>
                    <p>{accion.descripcion}</p>
                    <p>
                      Responsable: {accion.cargo_codigo} · {accion.cargo_denominacion} (
                      {accion.unidad_nombre}, ejercicio {accion.ejercicio})
                    </p>
                    <p>
                      Fecha objetivo: {formatearFechaDeNegocio(accion.fecha_objetivo)}
                      {accion.vencida && (
                        <span role="alert">
                          {" "}
                          — Vencida
                        </span>
                      )}
                    </p>
                    <p>
                      Avance: {accion.porcentaje} % ·{" "}
                      {ETIQUETA_ESTADO_ACCION[accion.estado] ?? accion.estado}
                    </p>
                    {accion.avances.length === 0 ? (
                      <p>No hay avances registrados.</p>
                    ) : (
                      <ul>
                        {accion.avances.map((avance) => (
                          <li key={avance.id}>
                            {avance.nota} — {avance.porcentaje} % ·{" "}
                            {formatearFecha(avance.created_at)} · {avance.created_by}
                            {avance.documento_id ? " · con evidencia" : ""}
                          </li>
                        ))}
                      </ul>
                    )}

                    {hallazgo.estado === "EN_REMEDIACION" &&
                    puedeManage &&
                    accion.estado !== "COMPLETADA" ? (
                      <>
                        <AdjuntosPanel
                          resourceType={RESOURCE_TYPE_ACCION_CORRECTIVA}
                          resourceId={accion.id}
                          title={`Evidencia de la acción ${accion.orden}`}
                          onChange={() => {
                            void queryClient.invalidateQueries({
                              queryKey: [...CONSULTA_HALLAZGOS],
                            });
                          }}
                        />
                        <form onSubmit={(e) => e.preventDefault()}>
                          <FormField
                            label={`Nota del avance de la acción ${accion.orden}`}
                            htmlFor={`avance-nota-${accion.id}`}
                            required
                            error={erroresAvance[accion.id]?.nota}
                            help="Entre 10 y 2000 caracteres."
                          >
                            <textarea
                              id={`avance-nota-${accion.id}`}
                              value={formulariosAvance[accion.id]?.nota ?? ""}
                              onChange={(evento) =>
                                actualizarFormularioAvance(accion.id, {
                                  nota: evento.target.value,
                                })
                              }
                              className="min-h-24 w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                              required
                            />
                          </FormField>
                          <FormField
                            label={`Porcentaje de avance de la acción ${accion.orden}`}
                            htmlFor={`avance-porcentaje-${accion.id}`}
                            required
                            error={erroresAvance[accion.id]?.porcentaje}
                            help={`Mínimo ${accion.porcentaje} %. Para llegar al 100 % adjunte antes la evidencia.`}
                          >
                            <TextInput
                              id={`avance-porcentaje-${accion.id}`}
                              type="number"
                              min={accion.porcentaje}
                              max={100}
                              value={formulariosAvance[accion.id]?.porcentaje ?? ""}
                              onChange={(evento) =>
                                actualizarFormularioAvance(accion.id, {
                                  porcentaje: evento.target.value,
                                })
                              }
                              required
                            />
                          </FormField>
                          <FormField
                            label={`Documento de evidencia de la acción ${accion.orden}`}
                            htmlFor={`avance-documento-${accion.id}`}
                            error={erroresAvance[accion.id]?.documento_id}
                          >
                            <select
                              id={`avance-documento-${accion.id}`}
                              value={formulariosAvance[accion.id]?.documento_id ?? ""}
                              onChange={(evento) =>
                                actualizarFormularioAvance(accion.id, {
                                  documento_id: evento.target.value,
                                })
                              }
                              className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
                            >
                              <option value="">Sin documento</option>
                              {accion.documentos.map((documentoId, indice) => (
                                <option key={documentoId} value={documentoId}>
                                  Documento {indice + 1}
                                </option>
                              ))}
                            </select>
                          </FormField>
                          {erroresAvance[accion.id]?.general && (
                            <p role="alert">{erroresAvance[accion.id]?.general}</p>
                          )}
                          <AsyncButton
                            onClick={() => enviarAvance(accion)}
                            loadingText="Guardando…"
                            idleText="Registrar avance"
                            variant="primary"
                            disabled={false}
                          >
                            Registrar avance
                          </AsyncButton>
                        </form>
                      </>
                    ) : (
                      <p>{accion.documentos.length} documentos de evidencia.</p>
                    )}
                  </article>
                ))
              )}

              {hallazgo.estado === "ABIERTO" && puedeManage && (
                <form onSubmit={(e) => e.preventDefault()}>
                  <h4>Añadir acción correctiva</h4>
                  <FormField
                    label={`Acción para la recomendación ${recomendacion.orden}`}
                    htmlFor={`accion-descripcion-${recomendacion.id}`}
                    required
                    error={erroresAccion[recomendacion.id]?.descripcion}
                    help="Entre 10 y 2000 caracteres."
                  >
                    <textarea
                      id={`accion-descripcion-${recomendacion.id}`}
                      value={formulariosAccion[recomendacion.id]?.descripcion ?? ""}
                      onChange={(evento) =>
                        actualizarFormularioAccion(recomendacion.id, {
                          descripcion: evento.target.value,
                        })
                      }
                      className="min-h-24 w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                      required
                    />
                  </FormField>
                  <FormField
                    label={`Cargo responsable de la recomendación ${recomendacion.orden}`}
                    htmlFor={`accion-cargo-${recomendacion.id}`}
                    required
                    error={erroresAccion[recomendacion.id]?.cargo_id}
                  >
                    {cargos.length === 0 ? (
                      <p>No hay cargos vigentes en el ejercicio en curso.</p>
                    ) : (
                      <select
                        id={`accion-cargo-${recomendacion.id}`}
                        value={formulariosAccion[recomendacion.id]?.cargo_id ?? ""}
                        onChange={(evento) =>
                          actualizarFormularioAccion(recomendacion.id, {
                            cargo_id: evento.target.value,
                          })
                        }
                        className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
                        required
                      >
                        <option value="">Seleccione un cargo</option>
                        {cargos.map((cargo) => (
                          <option key={cargo.id} value={cargo.id}>
                            {cargo.codigo} — {cargo.denominacion} ({cargo.unidad_nombre},{" "}
                            {cargo.ejercicio})
                          </option>
                        ))}
                      </select>
                    )}
                  </FormField>
                  <FormField
                    label={`Fecha objetivo de la recomendación ${recomendacion.orden}`}
                    htmlFor={`accion-fecha-${recomendacion.id}`}
                    required
                    error={erroresAccion[recomendacion.id]?.fecha_objetivo}
                  >
                    <DateInput
                      id={`accion-fecha-${recomendacion.id}`}
                      min={hoy}
                      value={formulariosAccion[recomendacion.id]?.fecha_objetivo ?? ""}
                      onChange={(evento) =>
                        actualizarFormularioAccion(recomendacion.id, {
                          fecha_objetivo: evento.target.value,
                        })
                      }
                      invalid={Boolean(erroresAccion[recomendacion.id]?.fecha_objetivo)}
                      required
                    />
                  </FormField>
                  {erroresAccion[recomendacion.id]?.general && (
                    <p role="alert">{erroresAccion[recomendacion.id]?.general}</p>
                  )}
                  <Button
                    type="submit"
                    variant="primary"
                    disabled={cargos.length === 0}
                    onClick={() => void enviarAccion(recomendacion.id)}
                  >
                    Añadir acción correctiva
                  </Button>
                </form>
              )}
            </section>
          );
        })
      )}
      </section>
    </>
  );
}
