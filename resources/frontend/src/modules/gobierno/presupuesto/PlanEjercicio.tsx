import { useId, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import { Button } from "@/components/Button";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import type { DocumentSummary } from "@/modules/documentos/types";
import { AsyncButton } from "@/components/AsyncButton";
import {
  CONSULTA_PRESUPUESTO,
  type EjercicioDetalle,
  type EscribirBloque,
  type PlanVista,
} from "./api";

interface PlanEjercicioProps {
  detalle: EjercicioDetalle;
  puedeGestionar: boolean;
  escribirBloque: EscribirBloque;
  erroresServidor: Record<string, string[]>;
}

const errorDe = (
  erroresServidor: Record<string, string[]>,
  campo: string,
): string | undefined => erroresServidor[campo]?.[0];

export function PlanEjercicio({
  detalle,
  puedeGestionar,
  escribirBloque,
  erroresServidor,
}: PlanEjercicioProps) {
  const editable = puedeGestionar && detalle.estado === "BORRADOR";

  const planQuery = useQuery({
    queryKey: [...CONSULTA_PRESUPUESTO, "plan", detalle.id, detalle.version],
    queryFn: () =>
      apiFetch<PlanVista>(
        `/gobierno/presupuesto/ejercicios/${detalle.id}/plan`,
      ),
    retry: false,
  });

  const documentosQuery = useQuery({
    queryKey: ["documentos", "por-recurso", "GovernmentBudgetYear", detalle.id],
    queryFn: () =>
      apiFetch<DocumentSummary[]>(
        `/documentos/por-recurso/GovernmentBudgetYear/${encodeURIComponent(detalle.id)}`,
      ),
    retry: false,
  });

  const documentosValidos =
    documentosQuery.data?.filter((documento) => documento.status === "ACTIVE") ??
    [];

  const [denominacionPlan, setDenominacionPlan] = useState("");
  const [documentoPlan, setDocumentoPlan] = useState("");
  const [nuevoObjetivoCodigo, setNuevoObjetivoCodigo] = useState("");
  const [nuevoObjetivoDescripcion, setNuevoObjetivoDescripcion] = useState("");
  const [metaCategoria, setMetaCategoria] = useState("");
  const [metaDescripcion, setMetaDescripcion] = useState("");
  const [metaUnidadMedida, setMetaUnidadMedida] = useState("");
  const [metaCantidad, setMetaCantidad] = useState("");
  const [metaIndicador, setMetaIndicador] = useState("");
  const [metaFormula, setMetaFormula] = useState("");

  const idSeccion = useId();

  if (planQuery.isLoading || documentosQuery.isLoading) {
    return <p>Cargando plan…</p>;
  }

  if (planQuery.isError || !planQuery.data) {
    return <p>No fue posible cargar el plan.</p>;
  }

  const plan = planQuery.data;

  if (
    plan.estructura_organizativa == null ||
    plan.estructura_organizativa.estado !== "VIGENTE"
  ) {
    return (
      <section aria-labelledby={idSeccion}>
        <h2 id={idSeccion}>Plan operativo y metas</h2>
        <p role="note">
          No hay una estructura organizativa vigente para {detalle.anio}:
          publíquela en Gobierno › Estructura para asignar unidades
          responsables.
        </p>
      </section>
    );
  }

  return (
    <section aria-labelledby={idSeccion}>
      <h2 id={idSeccion}>Plan operativo y metas</h2>

      <h3>Plan operativo anual</h3>
      {editable ? (
        <form
          onSubmit={(evento) => {
            evento.preventDefault();
            void (async () => {
              try {
                const nuevoPlan = await escribirBloque<PlanVista>("/plan", "PUT", {
                  denominacion: denominacionPlan,
                  documento_id: documentoPlan || null,
                });
                setDenominacionPlan(nuevoPlan.plan?.denominacion ?? "");
                setDocumentoPlan(nuevoPlan.plan?.documento_id ?? "");
              } catch {
                // ya informado
              }
            })();
          }}
        >
          <FormField
            label="Denominación del plan"
            htmlFor={`${idSeccion}-denominacion-plan`}
            required
            error={errorDe(erroresServidor, "denominacion")}
          >
            <TextInput
              id={`${idSeccion}-denominacion-plan`}
              value={denominacionPlan}
              onChange={(evento) => setDenominacionPlan(evento.target.value)}
            />
          </FormField>
          <FormField
            label="Documento del plan"
            htmlFor={`${idSeccion}-documento-plan`}
            error={errorDe(erroresServidor, "documento_id")}
          >
            <select
              id={`${idSeccion}-documento-plan`}
              value={documentoPlan}
              onChange={(evento) => setDocumentoPlan(evento.target.value)}
            >
              <option value="">Sin documento</option>
              {documentosValidos.map((documento) => (
                <option key={documento.id} value={documento.id}>
                  {documento.document_number ?? documento.title}
                </option>
              ))}
            </select>
          </FormField>
          <Button type="submit">Guardar plan</Button>
        </form>
      ) : (
        <p>{plan.plan?.denominacion ?? "Sin plan operativo"}</p>
      )}

      <h3>Objetivos</h3>
      <div role="region" aria-label="Objetivos del plan">
        <table>
          <caption className="sr-only">Objetivos del plan</caption>
          <thead>
            <tr>
              <th>Código</th>
              <th>Descripción</th>
              {editable ? <th>Eliminar</th> : null}
            </tr>
          </thead>
          <tbody>
            {plan.objetivos.map((objetivo) => (
              <tr key={objetivo.id}>
                <td>{objetivo.codigo}</td>
                <td>{objetivo.descripcion}</td>
                {editable ? (
                  <td>
                    <AsyncButton
                      onClick={async () => {
                        try {
                          await escribirBloque<PlanVista>(
                            `/plan/objetivos/${objetivo.id}`,
                            "DELETE",
                          );
                        } catch {
                          // ya informado
                        }
                      }}
                      idleText={`Eliminar ${objetivo.codigo}`}
                      loadingText="Eliminando…"
                      disabled={false}
                    />
                  </td>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editable ? (
        <form
          onSubmit={(evento) => {
            evento.preventDefault();
            void (async () => {
              try {
                await escribirBloque<PlanVista>("/plan/objetivos", "POST", {
                  codigo: nuevoObjetivoCodigo,
                  descripcion: nuevoObjetivoDescripcion,
                });
                setNuevoObjetivoCodigo("");
                setNuevoObjetivoDescripcion("");
              } catch {
                // ya informado
              }
            })();
          }}
        >
          <h4>Nuevo objetivo</h4>
          <FormField
            label="Código"
            htmlFor={`${idSeccion}-nuevo-objetivo-codigo`}
            required
            error={errorDe(erroresServidor, "codigo")}
          >
            <TextInput
              id={`${idSeccion}-nuevo-objetivo-codigo`}
              value={nuevoObjetivoCodigo}
              onChange={(evento) => setNuevoObjetivoCodigo(evento.target.value)}
            />
          </FormField>
          <FormField
            label="Descripción"
            htmlFor={`${idSeccion}-nuevo-objetivo-descripcion`}
            required
            error={errorDe(erroresServidor, "descripcion")}
          >
            <TextInput
              id={`${idSeccion}-nuevo-objetivo-descripcion`}
              value={nuevoObjetivoDescripcion}
              onChange={(evento) =>
                setNuevoObjetivoDescripcion(evento.target.value)
              }
            />
          </FormField>
          <Button type="submit">Crear objetivo</Button>
        </form>
      ) : null}

      <h3>Unidades responsables y objetivos</h3>
      <div role="region" aria-label="Unidades responsables por categoría">
        <table>
          <thead>
            <tr>
              <th>Categoría</th>
              <th>Unidad responsable</th>
              <th>Objetivo</th>
              {editable ? <th>Acciones</th> : null}
            </tr>
          </thead>
          <tbody>
            {plan.vinculos.map((vinculo) => (
              <tr key={vinculo.categoria_id}>
                <td>
                  {vinculo.codigo_completo} · {vinculo.denominacion}
                </td>
                <td>
                  {editable ? (
                    <select
                      aria-label={`Unidad responsable de ${vinculo.codigo_completo}`}
                      defaultValue={vinculo.unidad?.id ?? ""}
                      data-vinculo-categoria={vinculo.categoria_id}
                      data-vinculo-campo="unidad"
                    >
                      <option value="">Sin asignar</option>
                      {plan.unidades_disponibles.map((unidad) => (
                        <option key={unidad.id} value={unidad.id}>
                          {unidad.codigo} · {unidad.nombre}
                        </option>
                      ))}
                    </select>
                  ) : (
                    vinculo.unidad
                      ? `${vinculo.unidad.codigo} · ${vinculo.unidad.nombre}`
                      : "Sin asignar"
                  )}
                </td>
                <td>
                  {editable ? (
                    <select
                      aria-label={`Objetivo de ${vinculo.codigo_completo}`}
                      defaultValue={vinculo.objetivo?.id ?? ""}
                      data-vinculo-categoria={vinculo.categoria_id}
                      data-vinculo-campo="objetivo"
                    >
                      <option value="">Sin objetivo</option>
                      {plan.objetivos.map((objetivo) => (
                        <option key={objetivo.id} value={objetivo.id}>
                          {objetivo.codigo} · {objetivo.descripcion}
                        </option>
                      ))}
                    </select>
                  ) : (
                    vinculo.objetivo
                      ? `${vinculo.objetivo.codigo} · Vinculado`
                      : "Sin objetivo"
                  )}
                </td>
                {editable ? (
                  <td>
                    <AsyncButton
                      onClick={async () => {
                        const fila = document.querySelector(
                          `[data-vinculo-categoria="${vinculo.categoria_id}"]`,
                        );
                        if (!fila) return;
                        const unidadSelect = document.querySelector<HTMLSelectElement>(
                          `[data-vinculo-categoria="${vinculo.categoria_id}"][data-vinculo-campo="unidad"]`,
                        );
                        const objetivoSelect = document.querySelector<HTMLSelectElement>(
                          `[data-vinculo-categoria="${vinculo.categoria_id}"][data-vinculo-campo="objetivo"]`,
                        );
                        const unidadId = unidadSelect?.value || null;
                        const objetivoId = objetivoSelect?.value || null;
                        try {
                          await escribirBloque<PlanVista>(
                            `/categorias/${vinculo.categoria_id}/vinculo`,
                            "PUT",
                            {
                              unidad_id: unidadId,
                              objetivo_id: objetivoId,
                            },
                          );
                        } catch {
                          // ya informado
                        }
                      }}
                      idleText={`Guardar vínculo de ${vinculo.codigo_completo}`}
                      loadingText="Guardando…"
                      disabled={false}
                    />
                  </td>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3>Metas físicas</h3>
      <div role="region" aria-label="Metas físicas">
        <table>
          <thead>
            <tr>
              <th>Categoría</th>
              <th>Descripción</th>
              <th>Unidad de medida</th>
              <th>Cantidad</th>
              <th>Indicador</th>
              <th>Fórmula</th>
              {editable ? <th>Eliminar</th> : null}
            </tr>
          </thead>
          <tbody>
            {plan.metas.map((meta) => (
              <tr key={meta.id}>
                <td>{meta.codigo_completo}</td>
                <td>{meta.descripcion}</td>
                <td>{meta.unidad_medida}</td>
                <td>{meta.cantidad}</td>
                <td>{meta.indicador}</td>
                <td>{meta.formula ?? "—"}</td>
                {editable ? (
                  <td>
                    <AsyncButton
                      onClick={async () => {
                        try {
                          await escribirBloque<PlanVista>(
                            `/plan/metas/${meta.id}`,
                            "DELETE",
                          );
                        } catch {
                          // ya informado
                        }
                      }}
                      idleText="Eliminar"
                      loadingText="Eliminando…"
                      disabled={false}
                    />
                  </td>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editable ? (
        <form
          onSubmit={(evento) => {
            evento.preventDefault();
            void (async () => {
              try {
                await escribirBloque<PlanVista>("/plan/metas", "POST", {
                  categoria_id: metaCategoria,
                  descripcion: metaDescripcion,
                  unidad_medida: metaUnidadMedida,
                  cantidad: metaCantidad,
                  indicador: metaIndicador,
                  formula: metaFormula || null,
                });
                setMetaCategoria("");
                setMetaDescripcion("");
                setMetaUnidadMedida("");
                setMetaCantidad("");
                setMetaIndicador("");
                setMetaFormula("");
              } catch {
                // ya informado
              }
            })();
          }}
        >
          <h4>Nueva meta física</h4>
          <FormField
            label="Categoría"
            htmlFor={`${idSeccion}-meta-categoria`}
            required
            error={errorDe(erroresServidor, "categoria_id")}
          >
            <select
              id={`${idSeccion}-meta-categoria`}
              value={metaCategoria}
              onChange={(evento) => setMetaCategoria(evento.target.value)}
            >
              <option value="">Seleccione categoría</option>
              {plan.vinculos.map((vinculo) => (
                <option key={vinculo.categoria_id} value={vinculo.categoria_id}>
                  {vinculo.codigo_completo} · {vinculo.denominacion}
                </option>
              ))}
            </select>
          </FormField>
          <FormField
            label="Descripción"
            htmlFor={`${idSeccion}-meta-descripcion`}
            required
            error={errorDe(erroresServidor, "descripcion")}
          >
            <TextInput
              id={`${idSeccion}-meta-descripcion`}
              value={metaDescripcion}
              onChange={(evento) => setMetaDescripcion(evento.target.value)}
            />
          </FormField>
          <FormField
            label="Unidad de medida"
            htmlFor={`${idSeccion}-meta-unidad-medida`}
            required
            error={errorDe(erroresServidor, "unidad_medida")}
          >
            <TextInput
              id={`${idSeccion}-meta-unidad-medida`}
              value={metaUnidadMedida}
              onChange={(evento) => setMetaUnidadMedida(evento.target.value)}
            />
          </FormField>
          <FormField
            label="Cantidad"
            htmlFor={`${idSeccion}-meta-cantidad`}
            required
            error={errorDe(erroresServidor, "cantidad")}
          >
            <TextInput
              id={`${idSeccion}-meta-cantidad`}
              inputMode="decimal"
              value={metaCantidad}
              onChange={(evento) => setMetaCantidad(evento.target.value)}
            />
          </FormField>
          <FormField
            label="Indicador"
            htmlFor={`${idSeccion}-meta-indicador`}
            required
            error={errorDe(erroresServidor, "indicador")}
          >
            <TextInput
              id={`${idSeccion}-meta-indicador`}
              value={metaIndicador}
              onChange={(evento) => setMetaIndicador(evento.target.value)}
            />
          </FormField>
          <FormField
            label="Fórmula (opcional)"
            htmlFor={`${idSeccion}-meta-formula`}
            error={errorDe(erroresServidor, "formula")}
          >
            <TextInput
              id={`${idSeccion}-meta-formula`}
              value={metaFormula}
              onChange={(evento) => setMetaFormula(evento.target.value)}
            />
          </FormField>
          <Button type="submit">Crear meta</Button>
        </form>
      ) : null}
    </section>
  );
}
