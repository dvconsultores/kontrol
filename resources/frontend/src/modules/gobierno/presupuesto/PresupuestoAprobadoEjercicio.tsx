import { useId, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { DateInput } from "@/components/DateInput";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { formatMoney } from "@/lib/format";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import type { DocumentSummary } from "@/modules/documentos/types";
import {
  CONSULTA_PRESUPUESTO,
  type EjercicioDetalle,
  type EscribirBloque,
  type PresupuestoAprobadoVista,
} from "./api";

interface PresupuestoAprobadoEjercicioProps {
  detalle: EjercicioDetalle;
  puedeGestionar: boolean;
  escribirBloque: EscribirBloque;
  erroresServidor: Record<string, string[]>;
}

const errorDe = (
  erroresServidor: Record<string, string[]>,
  campo: string,
): string | undefined => erroresServidor[campo]?.[0];

const normalizarMonto = (texto: string): string => {
  const sinEspacios = texto.replace(/\s+/g, "");
  const sinPuntosMiles = sinEspacios.replace(/\.(?=\d{3}(\D|$))/g, "");
  return sinPuntosMiles.replace(",", ".");
};

export function PresupuestoAprobadoEjercicio({
  detalle,
  puedeGestionar,
  escribirBloque,
  erroresServidor,
}: PresupuestoAprobadoEjercicioProps) {
  const editable = puedeGestionar && detalle.estado === "BORRADOR";
  const idSeccion = useId();

  const vistaQuery = useQuery({
    queryKey: [
      ...CONSULTA_PRESUPUESTO,
      "presupuesto-aprobado",
      detalle.id,
      detalle.version,
    ],
    queryFn: () =>
      apiFetch<PresupuestoAprobadoVista>(
        `/gobierno/presupuesto/ejercicios/${detalle.id}/presupuesto-aprobado`,
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

  const [nuevoIngresoPartidaId, setNuevoIngresoPartidaId] = useState("");
  const [nuevoIngresoMonto, setNuevoIngresoMonto] = useState("");

  const [nuevoCreditoCategoriaId, setNuevoCreditoCategoriaId] = useState("");
  const [nuevoCreditoFuenteId, setNuevoCreditoFuenteId] = useState("");
  const [nuevoCreditoPartidaId, setNuevoCreditoPartidaId] = useState("");
  const [nuevoCreditoMonto, setNuevoCreditoMonto] = useState("");

  const [nuevasExistenciasMonto, setNuevasExistenciasMonto] = useState("");
  const [nuevasExistenciasFechaCorte, setNuevasExistenciasFechaCorte] =
    useState("");
  const [nuevasExistenciasDocumentoId, setNuevasExistenciasDocumentoId] =
    useState("");
  const [montosIngreso, setMontosIngreso] = useState<Record<string, string>>({});
  const [montosCredito, setMontosCredito] = useState<Record<string, string>>({});

  if (vistaQuery.isLoading || documentosQuery.isLoading) {
    return <p>Cargando presupuesto aprobado…</p>;
  }

  if (vistaQuery.isError || !vistaQuery.data) {
    return <p>No fue posible cargar el presupuesto aprobado.</p>;
  }

  const vista = vistaQuery.data;
  const fuenteElegida = vista.opciones.fuentes.find(
    (fuente) => fuente.id === nuevoCreditoFuenteId,
  );
  const partidasFiltradas = (() => {
    if (!fuenteElegida || fuenteElegida.partidas_permitidas === null) {
      return vista.opciones.partidas_egreso;
    }
    const permitidas = fuenteElegida.partidas_permitidas;
    return vista.opciones.partidas_egreso.filter((partida) =>
      permitidas.some(
        (permitida) =>
          partida.codigo === permitida ||
          partida.codigo.startsWith(`${permitida}.`),
      ),
    );
  })();

  return (
    <section aria-labelledby={idSeccion}>
      <h2 id={idSeccion}>Presupuesto aprobado</h2>
      <p>
        Transcriba la ordenanza de presupuesto: la estimación de ingresos y los
        créditos por categoría programática, partida y fuente.
      </p>
      {vista.congelado ? (
        <p>El presupuesto aprobado está fijado y ya no se modifica.</p>
      ) : null}

      <h3>Presupuesto de ingresos</h3>
      <div role="region" aria-label="Tabla de ingresos estimados">
        <table>
          <thead>
            <tr>
              <th>Partida</th>
              <th>Monto</th>
              {editable ? <th>Acciones</th> : null}
            </tr>
          </thead>
          <tbody>
            {vista.ingresos.length === 0 ? (
              <tr>
                <td colSpan={editable ? 3 : 2}>
                  <p>Sin ingresos estimados.</p>
                </td>
              </tr>
            ) : (
              vista.ingresos.map((ingreso) => (
                <tr key={ingreso.id}>
                  <td>
                    {ingreso.partida.codigo} · {ingreso.partida.denominacion}
                  </td>
                  <td>
                    {formatMoney(ingreso.monto)} {vista.moneda}
                  </td>
                  {editable ? (
                    <td>
                      <TextInput
                        aria-label={`Nuevo monto del ingreso ${ingreso.partida.codigo}`}
                        id={`${idSeccion}-ingreso-${ingreso.id}-monto`}
                        value={montosIngreso[ingreso.id] ?? ""}
                        onChange={(e) => {
                          setMontosIngreso((prev) => ({
                            ...prev,
                            [ingreso.id]: e.target.value,
                          }));
                        }}
                      />
                      <Button
                        type="button"
                        onClick={async () => {
                          try {
                            await escribirBloque<PresupuestoAprobadoVista>(
                              `/presupuesto-aprobado/ingresos/${ingreso.id}`,
                              "PATCH",
                              { monto: normalizarMonto(montosIngreso[ingreso.id] ?? "") },
                            );
                            setMontosIngreso((prev) => {
                              const copia = { ...prev };
                              delete copia[ingreso.id];
                              return copia;
                            });
                          } catch {
                            // ya informado
                          }
                        }}
                      >
                        Guardar ingreso {ingreso.partida.codigo}
                      </Button>
                      <AsyncButton
                        onClick={async () => {
                          try {
                            await escribirBloque<PresupuestoAprobadoVista>(
                              `/presupuesto-aprobado/ingresos/${ingreso.id}`,
                              "DELETE",
                            );
                          } catch {
                            // ya informado
                          }
                        }}
                        idleText={`Eliminar ingreso ${ingreso.partida.codigo}`}
                        loadingText="Eliminando…"
                        disabled={false}
                      />
                    </td>
                  ) : null}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {editable ? (
        <form
          onSubmit={async (evento) => {
            evento.preventDefault();
            try {
              await escribirBloque<PresupuestoAprobadoVista>(
                "/presupuesto-aprobado/ingresos",
                "POST",
                {
                  partida_id: nuevoIngresoPartidaId,
                  monto: normalizarMonto(nuevoIngresoMonto),
                },
              );
              setNuevoIngresoPartidaId("");
              setNuevoIngresoMonto("");
            } catch {
              // ya informado
            }
          }}
        >
          <FormField
            label="Partida de recursos"
            required
            htmlFor={`${idSeccion}-nuevo-ingreso-partida`}
            error={errorDe(erroresServidor, "partida_id")}
          >
            <select
              id={`${idSeccion}-nuevo-ingreso-partida`}
              value={nuevoIngresoPartidaId}
              onChange={(evento) => setNuevoIngresoPartidaId(evento.target.value)}
              required
            >
              <option value="">Seleccione…</option>
              {vista.opciones.partidas_recurso.map((partida) => (
                <option key={partida.id} value={partida.id}>
                  {partida.codigo} · {partida.denominacion}
                </option>
              ))}
            </select>
          </FormField>
          <FormField
            label="Monto del ingreso"
            required
            htmlFor={`${idSeccion}-nuevo-ingreso-monto`}
            error={errorDe(erroresServidor, "monto")}
          >
            <TextInput
              id={`${idSeccion}-nuevo-ingreso-monto`}
              value={nuevoIngresoMonto}
              onChange={(evento) => setNuevoIngresoMonto(evento.target.value)}
              inputMode="decimal"
              required
            />
          </FormField>
          <Button type="submit">Registrar ingreso</Button>
        </form>
      ) : null}

      <h3>Créditos presupuestarios</h3>
      <div role="region" aria-label="Tabla de créditos presupuestarios">
        <table>
          <thead>
            <tr>
              <th>Categoría</th>
              <th>Unidad ejecutora</th>
              <th>Partida</th>
              <th>Fuente</th>
              <th>Monto</th>
              {editable ? <th>Acciones</th> : null}
            </tr>
          </thead>
          <tbody>
            {vista.creditos.length === 0 ? (
              <tr>
                <td colSpan={editable ? 6 : 5}>
                  <p>Sin créditos registrados.</p>
                </td>
              </tr>
            ) : (
              vista.creditos.map((credito) => {
                const etiqueta = `${credito.categoria.codigo_completo} · ${credito.partida.codigo} · ${credito.fuente.codigo}`;
                return (
                  <tr key={credito.id}>
                    <td>
                      {credito.categoria.codigo_completo} ·{" "}
                      {credito.categoria.denominacion}
                    </td>
                    <td>
                      {credito.unidad
                        ? `${credito.unidad.codigo} · ${credito.unidad.nombre}`
                        : "Sin asignar"}
                    </td>
                    <td>
                      {credito.partida.codigo} · {credito.partida.denominacion}
                    </td>
                    <td>
                      {credito.fuente.codigo} · {credito.fuente.denominacion}
                    </td>
                    <td>
                      {formatMoney(credito.monto)} {vista.moneda}
                    </td>
                    {editable ? (
                      <td>
                        <TextInput
                          aria-label={`Nuevo monto del crédito ${etiqueta}`}
                          id={`${idSeccion}-credito-${credito.id}-monto`}
                          value={montosCredito[credito.id] ?? ""}
                          onChange={(e) => {
                            setMontosCredito((prev) => ({
                              ...prev,
                              [credito.id]: e.target.value,
                            }));
                          }}
                        />
                        <Button
                          type="button"
                          onClick={async () => {
                            try {
                              await escribirBloque<PresupuestoAprobadoVista>(
                                `/presupuesto-aprobado/creditos/${credito.id}`,
                                "PATCH",
                                { monto: normalizarMonto(montosCredito[credito.id] ?? "") },
                              );
                              setMontosCredito((prev) => {
                                const copia = { ...prev };
                                delete copia[credito.id];
                                return copia;
                              });
                            } catch {
                              // ya informado
                            }
                          }}
                        >
                          Guardar crédito {etiqueta}
                        </Button>
                        <AsyncButton
                          onClick={async () => {
                            try {
                              await escribirBloque<PresupuestoAprobadoVista>(
                                `/presupuesto-aprobado/creditos/${credito.id}`,
                                "DELETE",
                              );
                            } catch {
                              // ya informado
                            }
                          }}
                          idleText={`Eliminar crédito ${etiqueta}`}
                          loadingText="Eliminando…"
                          disabled={false}
                        />
                      </td>
                    ) : null}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {editable ? (
        <form
          onSubmit={async (evento) => {
            evento.preventDefault();
            try {
              await escribirBloque<PresupuestoAprobadoVista>(
                "/presupuesto-aprobado/creditos",
                "POST",
                {
                  categoria_id: nuevoCreditoCategoriaId,
                  partida_id: nuevoCreditoPartidaId,
                  fuente_id: nuevoCreditoFuenteId,
                  monto: normalizarMonto(nuevoCreditoMonto),
                },
              );
              setNuevoCreditoCategoriaId("");
              setNuevoCreditoFuenteId("");
              setNuevoCreditoPartidaId("");
              setNuevoCreditoMonto("");
            } catch {
              // ya informado
            }
          }}
        >
          <FormField
            label="Categoría programática"
            required
            htmlFor={`${idSeccion}-nuevo-credito-categoria`}
            error={errorDe(erroresServidor, "categoria_id")}
          >
            <select
              id={`${idSeccion}-nuevo-credito-categoria`}
              value={nuevoCreditoCategoriaId}
              onChange={(evento) =>
                setNuevoCreditoCategoriaId(evento.target.value)
              }
              required
            >
              <option value="">Seleccione…</option>
              {vista.opciones.categorias.map((categoria) => (
                <option key={categoria.id} value={categoria.id}>
                  {categoria.codigo_completo} · {categoria.denominacion}
                </option>
              ))}
            </select>
          </FormField>
          <FormField
            label="Fuente de financiamiento"
            required
            htmlFor={`${idSeccion}-nuevo-credito-fuente`}
            error={errorDe(erroresServidor, "fuente_id")}
          >
            <select
              id={`${idSeccion}-nuevo-credito-fuente`}
              value={nuevoCreditoFuenteId}
              onChange={(evento) => {
                const nuevaFuenteId = evento.target.value;
                setNuevoCreditoFuenteId(nuevaFuenteId);
                const nuevaFuente = vista.opciones.fuentes.find(
                  (fuente) => fuente.id === nuevaFuenteId,
                );
                if (
                  nuevaFuente &&
                  nuevaFuente.partidas_permitidas !== null &&
                  nuevoCreditoPartidaId
                ) {
                  const partidaActual = vista.opciones.partidas_egreso.find(
                    (partida) => partida.id === nuevoCreditoPartidaId,
                  );
                  if (
                    partidaActual &&
                    !nuevaFuente.partidas_permitidas.some(
                      (permitida) =>
                        partidaActual.codigo === permitida ||
                        partidaActual.codigo.startsWith(`${permitida}.`),
                    )
                  ) {
                    setNuevoCreditoPartidaId("");
                  }
                }
              }}
              required
            >
              <option value="">Seleccione…</option>
              {vista.opciones.fuentes.map((fuente) => (
                <option key={fuente.id} value={fuente.id}>
                  {fuente.codigo} · {fuente.denominacion}
                </option>
              ))}
            </select>
          </FormField>
          {fuenteElegida && fuenteElegida.partidas_permitidas !== null ? (
            <p>
              La fuente {fuenteElegida.codigo} solo financia las partidas{" "}
              {fuenteElegida.partidas_permitidas.join(", ")} (restricción de
              uso).
            </p>
          ) : null}
          <FormField
            label="Partida de egresos"
            required
            htmlFor={`${idSeccion}-nuevo-credito-partida`}
            error={errorDe(erroresServidor, "partida_id")}
          >
            <select
              id={`${idSeccion}-nuevo-credito-partida`}
              value={nuevoCreditoPartidaId}
              onChange={(evento) =>
                setNuevoCreditoPartidaId(evento.target.value)
              }
              required
            >
              <option value="">Seleccione…</option>
              {partidasFiltradas.map((partida) => (
                <option key={partida.id} value={partida.id}>
                  {partida.codigo} · {partida.denominacion}
                </option>
              ))}
            </select>
          </FormField>
          <FormField
            label="Monto del crédito"
            required
            htmlFor={`${idSeccion}-nuevo-credito-monto`}
            error={errorDe(erroresServidor, "monto")}
          >
            <TextInput
              id={`${idSeccion}-nuevo-credito-monto`}
              value={nuevoCreditoMonto}
              onChange={(evento) => setNuevoCreditoMonto(evento.target.value)}
              inputMode="decimal"
              required
            />
          </FormField>
          <Button type="submit">Registrar crédito</Button>
        </form>
      ) : null}

      <h3>Existencias del Tesoro no comprometidas</h3>
      <p>
        LOPPM art. 240: los gastos pueden exceder los ingresos estimados hasta
        la mitad de estas existencias. Declárelas solo con la certificación del
        Tesorero.
      </p>
      {vista.existencias_tesoro ? (
        <p>
          {formatMoney(vista.existencias_tesoro.monto)} {vista.moneda} al{" "}
          {formatearFechaDeNegocio(vista.existencias_tesoro.fecha_corte)}
        </p>
      ) : null}
      {editable && vista.existencias_tesoro ? (
        <AsyncButton
          onClick={async () => {
            try {
              await escribirBloque<PresupuestoAprobadoVista>(
                "/presupuesto-aprobado/existencias-tesoro",
                "DELETE",
              );
            } catch {
              // ya informado
            }
          }}
          idleText="Retirar existencias"
          loadingText="Retirando…"
          disabled={false}
        />
      ) : null}
      {editable ? (
        <form
          onSubmit={async (evento) => {
            evento.preventDefault();
            try {
              await escribirBloque<PresupuestoAprobadoVista>(
                "/presupuesto-aprobado/existencias-tesoro",
                "PUT",
                {
                  monto: normalizarMonto(nuevasExistenciasMonto),
                  fecha_corte: nuevasExistenciasFechaCorte,
                  documento_id: nuevasExistenciasDocumentoId,
                },
              );
              setNuevasExistenciasMonto("");
              setNuevasExistenciasFechaCorte("");
              setNuevasExistenciasDocumentoId("");
            } catch {
              // ya informado
            }
          }}
        >
          <FormField
            label="Monto de las existencias"
            required
            htmlFor={`${idSeccion}-nuevas-existencias-monto`}
            error={errorDe(erroresServidor, "monto")}
          >
            <TextInput
              id={`${idSeccion}-nuevas-existencias-monto`}
              value={nuevasExistenciasMonto}
              onChange={(evento) =>
                setNuevasExistenciasMonto(evento.target.value)
              }
              inputMode="decimal"
              required
            />
          </FormField>
          <FormField
            label="Fecha de corte"
            required
            htmlFor={`${idSeccion}-nuevas-existencias-fecha-corte`}
            error={errorDe(erroresServidor, "fecha_corte")}
          >
            <DateInput
              id={`${idSeccion}-nuevas-existencias-fecha-corte`}
              value={nuevasExistenciasFechaCorte}
              onChange={(evento) =>
                setNuevasExistenciasFechaCorte(evento.target.value)
              }
              required
            />
          </FormField>
          <FormField
            label="Certificación del Tesorero"
            required
            htmlFor={`${idSeccion}-nuevas-existencias-documento`}
            error={errorDe(erroresServidor, "documento_id")}
          >
            <select
              id={`${idSeccion}-nuevas-existencias-documento`}
              value={nuevasExistenciasDocumentoId}
              onChange={(evento) =>
                setNuevasExistenciasDocumentoId(evento.target.value)
              }
              required
            >
              <option value="">Seleccione…</option>
              {documentosValidos.map((documento) => (
                <option key={documento.id} value={documento.id}>
                  {documento.document_number ?? documento.title}
                </option>
              ))}
            </select>
          </FormField>
          <Button type="submit">Declarar existencias</Button>
        </form>
      ) : null}

      <h3>Cuadre (LOPPM art. 240)</h3>
      <dl>
        <dt>Ingresos estimados</dt>
        <dd>
          {formatMoney(vista.totales.ingresos)} {vista.moneda}
        </dd>
        <dt>Mitad de las existencias del Tesoro</dt>
        <dd>
          {formatMoney(vista.totales.holgura_tesoro)} {vista.moneda}
        </dd>
        <dt>Disponible</dt>
        <dd>
          {formatMoney(vista.totales.disponible)} {vista.moneda}
        </dd>
        <dt>Créditos</dt>
        <dd>
          {formatMoney(vista.totales.creditos)} {vista.moneda}
        </dd>
        <dt>Diferencia</dt>
        <dd>
          {formatMoney(vista.totales.diferencia)} {vista.moneda}
        </dd>
      </dl>
      {vista.totales.cuadra ? (
        <p>
          El presupuesto cuadra: los créditos no superan los ingresos estimados
          más la mitad de las existencias del Tesoro.
        </p>
      ) : (
        <p>
          No cuadra: los créditos superan el disponible. El ejercicio no podrá
          aprobarse hasta corregirlo.
        </p>
      )}
    </section>
  );
}
