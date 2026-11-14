import { useId, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { DateInput } from "@/components/DateInput";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import type { DocumentSummary } from "@/modules/documentos/types";
import {
  CONSULTA_PRESUPUESTO,
  type EjercicioDetalle,
  type EscribirBloque,
  type FuentesVista,
} from "./api";

interface FuentesEjercicioProps {
  detalle: EjercicioDetalle;
  puedeGestionar: boolean;
  escribirBloque: EscribirBloque;
  erroresServidor: Record<string, string[]>;
}

const errorDe = (
  erroresServidor: Record<string, string[]>,
  campo: string,
): string | undefined => erroresServidor[campo]?.[0];

export function FuentesEjercicio({
  detalle,
  puedeGestionar,
  escribirBloque,
  erroresServidor,
}: FuentesEjercicioProps) {
  const editable = puedeGestionar && detalle.estado === "BORRADOR";
  const idSeccion = useId();

  const fuentesQuery = useQuery({
    queryKey: [...CONSULTA_PRESUPUESTO, "fuentes", detalle.id, detalle.version],
    queryFn: () =>
      apiFetch<FuentesVista>(
        `/gobierno/presupuesto/ejercicios/${detalle.id}/fuentes`,
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

  const [nuevaFuenteCodigo, setNuevaFuenteCodigo] = useState("");
  const [nuevaFuenteDenominacion, setNuevaFuenteDenominacion] = useState("");
  const [nuevaFuenteProcedencia, setNuevaFuenteProcedencia] = useState("");
  const [nuevaFuenteDocumento, setNuevaFuenteDocumento] = useState("");
  const [nuevaFuenteVigenteDesde, setNuevaFuenteVigenteDesde] = useState("");
  const [nuevaFuenteVigenteHasta, setNuevaFuenteVigenteHasta] = useState("");

  const [restriccionDescripcion, setRestriccionDescripcion] = useState<
    Record<string, string>
  >({});
  const [restriccionFundamento, setRestriccionFundamento] = useState<
    Record<string, string>
  >({});
  const [restriccionPartidas, setRestriccionPartidas] = useState<
    Record<string, string>
  >({});

  if (fuentesQuery.isLoading || documentosQuery.isLoading) {
    return <p>Cargando fuentes…</p>;
  }

  if (fuentesQuery.isError || !fuentesQuery.data) {
    return <p>No fue posible cargar las fuentes.</p>;
  }

  const fuentes = fuentesQuery.data;

  return (
    <section aria-labelledby={idSeccion}>
      <h2 id={idSeccion}>Fuentes de financiamiento</h2>
      <p>
        Fuentes registradas por el ente con su procedencia. KONTROL no precarga
        códigos oficiales.
      </p>

      <div role="region" aria-label="Fuentes de financiamiento">
        <table>
          <thead>
            <tr>
              <th>Código</th>
              <th>Denominación</th>
              <th>Vigencia</th>
              <th>Procedencia</th>
              <th>Restricciones</th>
              {editable ? <th>Eliminar</th> : null}
            </tr>
          </thead>
          <tbody>
            {fuentes.items.map((fuente) => (
              <tr key={fuente.id}>
                <td>{fuente.codigo}</td>
                <td>{fuente.denominacion}</td>
                <td>
                  {fuente.vigente_desde
                    ? `${formatearFechaDeNegocio(fuente.vigente_desde)} – ${fuente.vigente_hasta ? formatearFechaDeNegocio(fuente.vigente_hasta) : "—"}`
                    : "—"}
                </td>
                <td>{fuente.procedencia}</td>
                <td>{fuente.restricciones.length}</td>
                {editable ? (
                  <td>
                    <AsyncButton
                      onClick={async () => {
                        try {
                          await escribirBloque<FuentesVista>(
                            `/fuentes/${fuente.id}`,
                            "DELETE",
                          );
                        } catch {
                          // ya informado
                        }
                      }}
                      idleText={`Eliminar ${fuente.codigo}`}
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

      {fuentes.items.map((fuente) => (
        <div key={fuente.id}>
          <h3>Restricciones de {fuente.codigo}</h3>
          {fuente.restricciones.length === 0 ? (
            <p>Sin restricciones.</p>
          ) : (
            <ul>
              {fuente.restricciones.map((restriccion) => (
                <li key={restriccion.id}>
                  {restriccion.descripcion} · {restriccion.fundamento} ·{" "}
                  {restriccion.partidas.length > 0
                    ? restriccion.partidas.join(", ")
                    : "Sin partidas"}{" "}
                  {editable ? (
                    <AsyncButton
                      onClick={async () => {
                        try {
                          await escribirBloque<FuentesVista>(
                            `/fuentes/${fuente.id}/restricciones/${restriccion.id}`,
                            "DELETE",
                          );
                        } catch {
                          // ya informado
                        }
                      }}
                      idleText="Retirar restricción"
                      loadingText="Retirando…"
                      disabled={false}
                    />
                  ) : null}
                </li>
              ))}
            </ul>
          )}
          {editable ? (
            <form
              onSubmit={(evento) => {
                evento.preventDefault();
                const partidas = (restriccionPartidas[fuente.id] ?? "")
                  .split(",")
                  .map((partida) => partida.trim())
                  .filter((partida) => partida.length > 0);
                void (async () => {
                  try {
                    await escribirBloque<FuentesVista>(
                      `/fuentes/${fuente.id}/restricciones`,
                      "POST",
                      {
                        descripcion: restriccionDescripcion[fuente.id],
                        fundamento: restriccionFundamento[fuente.id],
                        partidas,
                      },
                    );
                    setRestriccionDescripcion((anterior) => ({
                      ...anterior,
                      [fuente.id]: "",
                    }));
                    setRestriccionFundamento((anterior) => ({
                      ...anterior,
                      [fuente.id]: "",
                    }));
                    setRestriccionPartidas((anterior) => ({
                      ...anterior,
                      [fuente.id]: "",
                    }));
                  } catch {
                    // ya informado
                  }
                })();
              }}
            >
              <FormField
                label={`Descripción de la restricción de ${fuente.codigo}`}
                htmlFor={`${idSeccion}-restriccion-descripcion-${fuente.id}`}
                required
                error={errorDe(erroresServidor, "descripcion")}
              >
                <TextInput
                  id={`${idSeccion}-restriccion-descripcion-${fuente.id}`}
                  value={restriccionDescripcion[fuente.id] ?? ""}
                  onChange={(evento) =>
                    setRestriccionDescripcion((anterior) => ({
                      ...anterior,
                      [fuente.id]: evento.target.value,
                    }))
                  }
                />
              </FormField>
              <FormField
                label={`Fundamento de la restricción de ${fuente.codigo}`}
                htmlFor={`${idSeccion}-restriccion-fundamento-${fuente.id}`}
                required
                error={errorDe(erroresServidor, "fundamento")}
              >
                <TextInput
                  id={`${idSeccion}-restriccion-fundamento-${fuente.id}`}
                  value={restriccionFundamento[fuente.id] ?? ""}
                  onChange={(evento) =>
                    setRestriccionFundamento((anterior) => ({
                      ...anterior,
                      [fuente.id]: evento.target.value,
                    }))
                  }
                />
              </FormField>
              <FormField
                label={`Partidas de egreso de ${fuente.codigo}`}
                htmlFor={`${idSeccion}-restriccion-partidas-${fuente.id}`}
                help="Opcional. Códigos de partidas de egresos del clasificador, separados por comas."
              >
                <TextInput
                  id={`${idSeccion}-restriccion-partidas-${fuente.id}`}
                  value={restriccionPartidas[fuente.id] ?? ""}
                  onChange={(evento) =>
                    setRestriccionPartidas((anterior) => ({
                      ...anterior,
                      [fuente.id]: evento.target.value,
                    }))
                  }
                />
              </FormField>
              <Button type="submit">
                Añadir restricción a {fuente.codigo}
              </Button>
            </form>
          ) : null}
        </div>
      ))}

      {editable ? (
        <form
          onSubmit={(evento) => {
            evento.preventDefault();
            void (async () => {
              try {
                await escribirBloque<FuentesVista>("/fuentes", "POST", {
                  codigo: nuevaFuenteCodigo,
                  denominacion: nuevaFuenteDenominacion,
                  procedencia: nuevaFuenteProcedencia,
                  documento_id: nuevaFuenteDocumento || null,
                  vigente_desde: nuevaFuenteVigenteDesde || null,
                  vigente_hasta: nuevaFuenteVigenteHasta || null,
                });
                setNuevaFuenteCodigo("");
                setNuevaFuenteDenominacion("");
                setNuevaFuenteProcedencia("");
                setNuevaFuenteDocumento("");
                setNuevaFuenteVigenteDesde("");
                setNuevaFuenteVigenteHasta("");
              } catch {
                // ya informado
              }
            })();
          }}
        >
          <h3>Nueva fuente</h3>
          <FormField
            label="Código"
            htmlFor={`${idSeccion}-nueva-fuente-codigo`}
            required
            error={errorDe(erroresServidor, "codigo")}
          >
            <TextInput
              id={`${idSeccion}-nueva-fuente-codigo`}
              value={nuevaFuenteCodigo}
              onChange={(evento) => setNuevaFuenteCodigo(evento.target.value)}
            />
          </FormField>
          <FormField
            label="Denominación"
            htmlFor={`${idSeccion}-nueva-fuente-denominacion`}
            required
            error={errorDe(erroresServidor, "denominacion")}
          >
            <TextInput
              id={`${idSeccion}-nueva-fuente-denominacion`}
              value={nuevaFuenteDenominacion}
              onChange={(evento) =>
                setNuevaFuenteDenominacion(evento.target.value)
              }
            />
          </FormField>
          <FormField
            label="Procedencia"
            htmlFor={`${idSeccion}-nueva-fuente-procedencia`}
            required
            error={errorDe(erroresServidor, "procedencia")}
          >
            <textarea
              id={`${idSeccion}-nueva-fuente-procedencia`}
              value={nuevaFuenteProcedencia}
              onChange={(evento) =>
                setNuevaFuenteProcedencia(evento.target.value)
              }
            />
          </FormField>
          <FormField
            label="Documento de procedencia (opcional)"
            htmlFor={`${idSeccion}-nueva-fuente-documento`}
            error={errorDe(erroresServidor, "documento_id")}
          >
            <select
              id={`${idSeccion}-nueva-fuente-documento`}
              value={nuevaFuenteDocumento}
              onChange={(evento) => setNuevaFuenteDocumento(evento.target.value)}
            >
              <option value="">Sin documento</option>
              {documentosValidos.map((documento) => (
                <option key={documento.id} value={documento.id}>
                  {documento.document_number ?? documento.title}
                </option>
              ))}
            </select>
          </FormField>
          <FormField
            label="Vigente desde"
            htmlFor={`${idSeccion}-nueva-fuente-vigente-desde`}
          >
            <DateInput
              id={`${idSeccion}-nueva-fuente-vigente-desde`}
              value={nuevaFuenteVigenteDesde}
              onChange={(evento) =>
                setNuevaFuenteVigenteDesde(evento.target.value)
              }
            />
          </FormField>
          <FormField
            label="Vigente hasta"
            htmlFor={`${idSeccion}-nueva-fuente-vigente-hasta`}
          >
            <DateInput
              id={`${idSeccion}-nueva-fuente-vigente-hasta`}
              value={nuevaFuenteVigenteHasta}
              onChange={(evento) =>
                setNuevaFuenteVigenteHasta(evento.target.value)
              }
            />
          </FormField>
          <Button type="submit">Crear fuente</Button>
        </form>
      ) : null}
    </section>
  );
}
