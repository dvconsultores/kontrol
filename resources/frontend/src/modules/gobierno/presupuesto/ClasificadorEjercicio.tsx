import { useId, useState } from "react";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";

import type { DocumentSummary } from "@/modules/documentos/types";
import {
  CONSULTA_PRESUPUESTO,
  ETIQUETAS_TIPO_PARTIDA,
  type EjercicioDetalle,
  type EscribirEjercicio,
  type ImportarPartidas,
  type PartidaClasificador,
} from "./api";

interface ClasificadorEjercicioProps {
  detalle: EjercicioDetalle;
  puedeGestionar: boolean;
  escribir: EscribirEjercicio;
  importar: ImportarPartidas;
  erroresServidor: Record<string, string[]>;
}

interface PartidasListado {
  items: PartidaClasificador[];
  total: number;
}

function huellaCorta(sha256: string | null): string {
  if (!sha256) return "Sin documento";
  return `${sha256.slice(0, 12)}…`;
}

export function ClasificadorEjercicio({
  detalle,
  puedeGestionar,
  escribir,
  importar,
  erroresServidor,
}: ClasificadorEjercicioProps) {
  const idTitulo = useId();
  const editable = puedeGestionar && detalle.estado === "BORRADOR";

  const clasificador = detalle.clasificador;

  const [edicion, setEdicion] = useState(clasificador?.edicion ?? "");
  const [fechaEdicion, setFechaEdicion] = useState(
    clasificador?.fecha_edicion ?? "",
  );
  const [procedencia, setProcedencia] = useState(
    clasificador?.procedencia ?? "",
  );
  const [documentoId, setDocumentoId] = useState(
    clasificador?.documento_id ?? "",
  );
  const [enviandoClasificador, setEnviandoClasificador] = useState(false);

  const [tipoPartida, setTipoPartida] = useState("");
  const [enviandoEliminacion, setEnviandoEliminacion] = useState(false);

  const [nuevaTipo, setNuevaTipo] = useState<"RECURSO" | "EGRESO">("RECURSO");
  const [nuevoCodigo, setNuevoCodigo] = useState("");
  const [nuevaDenominacion, setNuevaDenominacion] = useState("");
  const [nuevoNivel, setNuevoNivel] = useState(1);
  const [nuevoSuperior, setNuevoSuperior] = useState("");
  const [nuevoDesde, setNuevoDesde] = useState("");
  const [nuevoHasta, setNuevoHasta] = useState("");
  const [enviandoPartida, setEnviandoPartida] = useState(false);

  const [archivoImportacion, setArchivoImportacion] = useState<File | null>(
    null,
  );
  const [enviandoImportacion, setEnviandoImportacion] = useState(false);

  const documentosQuery = useQuery({
    queryKey: [
      "documentos",
      "por-recurso",
      "GovernmentBudgetYear",
      detalle.id,
    ],
    queryFn: () =>
      apiFetch<DocumentSummary[]>(
        `/documentos/por-recurso/GovernmentBudgetYear/${encodeURIComponent(detalle.id)}`,
      ),
    retry: false,
  });

  const documentosValidos =
    documentosQuery.data?.filter(
      (documento) => documento.status === "ACTIVE",
    ) ?? [];

  const partidasQuery = useQuery({
    queryKey: [
      ...CONSULTA_PRESUPUESTO,
      "partidas",
      detalle.id,
      detalle.version,
      tipoPartida,
    ],
    queryFn: () => {
      const parametros = new URLSearchParams();
      if (tipoPartida) {
        parametros.set("tipo", tipoPartida);
      }
      return apiFetch<PartidasListado>(
        `/gobierno/presupuesto/ejercicios/${detalle.id}/clasificador/partidas?${parametros.toString()}`,
      );
    },
    retry: false,
  });

  const partidas = partidasQuery.data?.items ?? [];

  async function guardarClasificador() {
    if (!editable) return;
    setEnviandoClasificador(true);
    try {
      await escribir("/clasificador", "PUT", {
        edicion: edicion.trim(),
        fecha_edicion: fechaEdicion || null,
        procedencia: procedencia.trim(),
        documento_id: documentoId || null,
      });
    } catch {
      // La página ya informó del error.
    } finally {
      setEnviandoClasificador(false);
    }
  }

  async function eliminarPartida(id: string) {
    setEnviandoEliminacion(true);
    try {
      await escribir(`/clasificador/partidas/${id}`, "DELETE");
    } catch {
      // La página ya informó del error.
    } finally {
      setEnviandoEliminacion(false);
    }
  }

  async function agregarPartida() {
    if (!editable || !clasificador) return;
    setEnviandoPartida(true);
    try {
      await escribir("/clasificador/partidas", "POST", {
        tipo: nuevaTipo,
        codigo: nuevoCodigo.trim(),
        denominacion: nuevaDenominacion.trim(),
        nivel: nuevoNivel,
        codigo_padre: nuevoSuperior.trim() || null,
        vigente_desde: nuevoDesde || null,
        vigente_hasta: nuevoHasta || null,
      });
      setNuevoCodigo("");
      setNuevaDenominacion("");
      setNuevoSuperior("");
      setNuevoDesde("");
      setNuevoHasta("");
      setNuevoNivel(1);
      setNuevaTipo("RECURSO");
    } catch {
      // La página ya informó del error.
    } finally {
      setEnviandoPartida(false);
    }
  }

  async function importarPartidas() {
    if (!archivoImportacion) return;
    setEnviandoImportacion(true);
    try {
      await importar(archivoImportacion);
      setArchivoImportacion(null);
    } catch {
      // La página ya informó del error.
    } finally {
      setEnviandoImportacion(false);
    }
  }

  return (
    <section aria-labelledby={idTitulo}>
      <h2
        id={idTitulo}
        className="mb-2 text-lg font-semibold text-text-900"
      >
        Clasificador registrado por el ente
      </h2>
      <p className="mb-4 text-sm text-text-700">
        El ente registra el clasificador que aplica en el ejercicio, con su
        procedencia. KONTROL no precarga códigos.
      </p>

      {clasificador ? (
        <dl className="mb-6 grid grid-cols-1 gap-x-4 gap-y-2 rounded-md border border-border-default p-4 sm:grid-cols-2">
          <div>
            <dt className="text-sm font-medium text-text-700">Edición</dt>
            <dd className="text-sm text-text-900">{clasificador.edicion}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">
              Fecha de edición
            </dt>
            <dd className="text-sm text-text-900">
              {formatearFechaDeNegocio(clasificador.fecha_edicion)}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Procedencia</dt>
            <dd className="text-sm text-text-900">
              {clasificador.procedencia}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">
              Documento de procedencia
            </dt>
            <dd className="text-sm text-text-900">
              {huellaCorta(clasificador.documento_sha256)}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">
              Partidas de recursos
            </dt>
            <dd className="text-sm text-text-900">
              {clasificador.partidas_recurso}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">
              Partidas de egresos
            </dt>
            <dd className="text-sm text-text-900">
              {clasificador.partidas_egreso}
            </dd>
          </div>
        </dl>
      ) : null}

      {editable ? (
        <form
          onSubmit={(evento) => {
            evento.preventDefault();
            void guardarClasificador();
          }}
          className="mb-6 rounded-md border border-border-default p-4"
        >
          <h3 className="mb-2 text-base font-medium text-text-800">
            Procedencia del clasificador
          </h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <FormField
              label="Edición"
              htmlFor="clasificador-edicion"
              error={erroresServidor.edicion?.[0]}
            >
              <TextInput
                id="clasificador-edicion"
                value={edicion}
                onChange={(evento) => setEdicion(evento.target.value)}
                aria-invalid={Boolean(erroresServidor.edicion)}
              />
            </FormField>

            <FormField
              label="Fecha de edición"
              htmlFor="clasificador-fecha"
              error={erroresServidor.fecha_edicion?.[0]}
            >
              <input
                id="clasificador-fecha"
                type="date"
                value={fechaEdicion}
                onChange={(evento) => setFechaEdicion(evento.target.value)}
                aria-invalid={Boolean(erroresServidor.fecha_edicion)}
                className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
              />
            </FormField>

            <FormField
              label="Procedencia"
              htmlFor="clasificador-procedencia"
              error={erroresServidor.procedencia?.[0]}
              className="sm:col-span-2"
            >
              <textarea
                id="clasificador-procedencia"
                value={procedencia}
                onChange={(evento) => setProcedencia(evento.target.value)}
                aria-invalid={Boolean(erroresServidor.procedencia)}
                rows={3}
                className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
              />
            </FormField>

            <FormField
              label="Documento de procedencia"
              htmlFor="clasificador-documento"
              error={erroresServidor.documento_id?.[0]}
              help='Adjunte primero el PDF en "Documentos del ejercicio".'
            >
              <select
                id="clasificador-documento"
                value={documentoId}
                onChange={(evento) => setDocumentoId(evento.target.value)}
                aria-invalid={Boolean(erroresServidor.documento_id)}
                className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
              >
                <option value="">Sin documento</option>
                {documentosValidos.map((documento) => (
                  <option key={documento.id} value={documento.id}>
                    {documento.document_number ?? documento.title}
                  </option>
                ))}
              </select>
            </FormField>
          </div>
          <div className="mt-4">
            <button
              type="submit"
              disabled={enviandoClasificador}
              className="inline-flex h-10 items-center rounded-md bg-brand-600 px-3 text-sm font-medium text-white hover:bg-brand-700 focus-visible:outline-brand-600 disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-brand-300"
            >
              Guardar clasificador
            </button>
          </div>
        </form>
      ) : null}

      <div className="mb-6">
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <h3 className="text-base font-medium text-text-800">Partidas</h3>
          <select
            id="filtro-tipo-partida"
            aria-label="Tipo"
            value={tipoPartida}
            onChange={(evento) => setTipoPartida(evento.target.value)}
            className="rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
          >
            <option value="">Todos</option>
            <option value="RECURSO">Recurso</option>
            <option value="EGRESO">Egreso</option>
          </select>
        </div>
        <div
          className="relative overflow-x-auto"
          tabIndex={0}
          role="region"
          aria-label="Partidas del clasificador"
        >
          <table className="w-full border-collapse text-left">
            <caption className="sr-only">Partidas del clasificador</caption>
            <thead>
              <tr className="border-b border-border-subtle">
                <th
                  scope="col"
                  className="px-3 py-2 text-sm font-medium text-text-700"
                >
                  Tipo
                </th>
                <th
                  scope="col"
                  className="px-3 py-2 text-sm font-medium text-text-700"
                >
                  Código
                </th>
                <th
                  scope="col"
                  className="px-3 py-2 text-sm font-medium text-text-700"
                >
                  Denominación
                </th>
                <th
                  scope="col"
                  className="px-3 py-2 text-sm font-medium text-text-700"
                >
                  Nivel
                </th>
                <th
                  scope="col"
                  className="px-3 py-2 text-sm font-medium text-text-700"
                >
                  Superior
                </th>
                <th
                  scope="col"
                  className="px-3 py-2 text-sm font-medium text-text-700"
                >
                  Vigencia
                </th>
                {editable ? (
                  <th
                    scope="col"
                    className="px-3 py-2 text-sm font-medium text-text-700"
                  >
                    <span className="sr-only">Acciones</span>
                  </th>
                ) : null}
              </tr>
            </thead>
            <tbody>
              {partidas.length === 0 ? (
                <tr className="border-b border-border-subtle">
                  <td
                    colSpan={editable ? 7 : 6}
                    className="px-3 py-2 text-sm text-text-700"
                  >
                    Aún no hay partidas.
                  </td>
                </tr>
              ) : (
                partidas.map((partida) => (
                  <tr
                    key={partida.id}
                    className="border-b border-border-subtle"
                  >
                    <td className="px-3 py-2 text-sm text-text-900">
                      {ETIQUETAS_TIPO_PARTIDA[partida.tipo]}
                    </td>
                    <td className="px-3 py-2 text-sm text-text-900">
                      {partida.codigo}
                    </td>
                    <td className="px-3 py-2 text-sm text-text-900">
                      {partida.denominacion}
                    </td>
                    <td className="px-3 py-2 text-sm text-text-900">
                      {partida.nivel}
                    </td>
                    <td className="px-3 py-2 text-sm text-text-900">
                      {partida.codigo_padre ?? "—"}
                    </td>
                    <td className="px-3 py-2 text-sm text-text-900">
                      {`${formatearFechaDeNegocio(partida.vigente_desde)} – ${partida.vigente_hasta ? formatearFechaDeNegocio(partida.vigente_hasta) : "—"}`}
                    </td>
                    {editable ? (
                      <td className="px-3 py-2 text-sm text-text-900">
                        <button
                          type="button"
                          onClick={() => void eliminarPartida(partida.id)}
                          disabled={enviandoEliminacion}
                          className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-red-700 hover:bg-surface-100 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          Eliminar
                        </button>
                      </td>
                    ) : null}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {editable && clasificador ? (
        <form
          onSubmit={(evento) => {
            evento.preventDefault();
            void agregarPartida();
          }}
          className="mb-6 rounded-md border border-border-default p-4"
        >
          <h3 className="mb-2 text-base font-medium text-text-800">
            Nueva partida
          </h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <FormField
              label="Tipo"
              htmlFor="nueva-partida-tipo"
              error={erroresServidor.tipo?.[0]}
            >
              <select
                id="nueva-partida-tipo"
                value={nuevaTipo}
                onChange={(evento) =>
                  setNuevaTipo(evento.target.value as "RECURSO" | "EGRESO")
                }
                aria-invalid={Boolean(erroresServidor.tipo)}
                className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
              >
                <option value="RECURSO">Recurso</option>
                <option value="EGRESO">Egreso</option>
              </select>
            </FormField>

            <FormField
              label="Código"
              htmlFor="nueva-partida-codigo"
              error={erroresServidor.codigo?.[0]}
            >
              <TextInput
                id="nueva-partida-codigo"
                value={nuevoCodigo}
                onChange={(evento) => setNuevoCodigo(evento.target.value)}
                aria-invalid={Boolean(erroresServidor.codigo)}
              />
            </FormField>

            <FormField
              label="Denominación"
              htmlFor="nueva-partida-denominacion"
              error={erroresServidor.denominacion?.[0]}
            >
              <TextInput
                id="nueva-partida-denominacion"
                value={nuevaDenominacion}
                onChange={(evento) =>
                  setNuevaDenominacion(evento.target.value)
                }
                aria-invalid={Boolean(erroresServidor.denominacion)}
              />
            </FormField>

            <FormField
              label="Nivel"
              htmlFor="nueva-partida-nivel"
              error={erroresServidor.nivel?.[0]}
            >
              <input
                id="nueva-partida-nivel"
                type="number"
                min={1}
                max={12}
                value={nuevoNivel}
                onChange={(evento) =>
                  setNuevoNivel(Number(evento.target.value))
                }
                aria-invalid={Boolean(erroresServidor.nivel)}
                className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
              />
            </FormField>

            <FormField
              label="Código superior"
              htmlFor="nueva-partida-superior"
              error={erroresServidor.codigo_padre?.[0]}
            >
              <TextInput
                id="nueva-partida-superior"
                value={nuevoSuperior}
                onChange={(evento) => setNuevoSuperior(evento.target.value)}
                aria-invalid={Boolean(erroresServidor.codigo_padre)}
              />
            </FormField>

            <FormField
              label="Vigente desde"
              htmlFor="nueva-partida-desde"
              error={erroresServidor.vigente_desde?.[0]}
            >
              <input
                id="nueva-partida-desde"
                type="date"
                value={nuevoDesde}
                onChange={(evento) => setNuevoDesde(evento.target.value)}
                aria-invalid={Boolean(erroresServidor.vigente_desde)}
                className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
              />
            </FormField>

            <FormField
              label="Vigente hasta"
              htmlFor="nueva-partida-hasta"
              error={erroresServidor.vigente_hasta?.[0]}
            >
              <input
                id="nueva-partida-hasta"
                type="date"
                value={nuevoHasta}
                onChange={(evento) => setNuevoHasta(evento.target.value)}
                aria-invalid={Boolean(erroresServidor.vigente_hasta)}
                className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
              />
            </FormField>
          </div>
          <div className="mt-4">
            <button
              type="submit"
              disabled={enviandoPartida}
              className="inline-flex h-10 items-center rounded-md bg-brand-600 px-3 text-sm font-medium text-white hover:bg-brand-700 focus-visible:outline-brand-600 disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-brand-300"
            >
              Agregar partida
            </button>
          </div>
        </form>
      ) : null}

      {editable && clasificador ? (
        <form
          onSubmit={(evento) => {
            evento.preventDefault();
            void importarPartidas();
          }}
          className="rounded-md border border-border-default p-4"
        >
          <h3 className="mb-2 text-base font-medium text-text-800">
            Importar partidas (CSV)
          </h3>
          <FormField
            label="Archivo CSV de partidas"
            htmlFor="archivo-partidas"
            help="Cabecera: tipo,codigo,denominacion,nivel,codigo_padre,vigente_desde,vigente_hasta. Si una fila tiene un error no se importa ninguna."
          >
            <input
              id="archivo-partidas"
              type="file"
              accept=".csv,text/csv"
              onChange={(evento) =>
                setArchivoImportacion(evento.target.files?.[0] ?? null)
              }
              className="w-full text-sm text-text-900"
            />
          </FormField>
          {erroresServidor.archivo?.length ? (
            <ul
              role="alert"
              className="mb-3 list-inside list-disc text-sm text-red-700"
            >
              {erroresServidor.archivo.map((mensaje, indice) => (
                <li key={`${mensaje}-${indice}`}>{mensaje}</li>
              ))}
            </ul>
          ) : null}
          <button
            type="submit"
            disabled={enviandoImportacion || !archivoImportacion}
            className="inline-flex h-10 items-center rounded-md bg-brand-600 px-3 text-sm font-medium text-white hover:bg-brand-700 focus-visible:outline-brand-600 disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-brand-300"
          >
            Importar partidas
          </button>
        </form>
      ) : null}
    </section>
  );
}
