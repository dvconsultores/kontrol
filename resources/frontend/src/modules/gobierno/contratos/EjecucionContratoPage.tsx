import { useState } from "react";
import { useParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { descargarArchivo } from "@/api/descargas";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { Button } from "@/components/Button";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { EmptyState } from "@/components/EmptyState";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { PageHeader } from "@/components/PageHeader";
import { PageContent } from "@/layout/PageContent";
import { formatearFechaDeNegocio, hoyDeNegocio } from "@/lib/fecha-de-negocio";
import { CONSULTA_CONTRATOS } from "./api";
import type {
  EjecucionContrato,
  OpcionesEjecucion,
  DocumentoRef,
} from "./api";

type Pendiente = {
  titulo: string;
  descripcion: string;
  ejecutar: () => Promise<void>;
};

type Anulando = {
  ruta: string;
  titulo: string;
};

const inputClase =
  "w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900";

function SelectorDocumento({
  id,
  etiqueta,
  valor,
  onChange,
  documentos,
}: {
  id: string;
  etiqueta: string;
  valor: string;
  onChange: (valor: string) => void;
  documentos: DocumentoRef[];
}) {
  return (
    <FormField label={etiqueta} htmlFor={id} required>
      {documentos.length === 0 ? (
        <p className="text-sm text-text-600">
          No hay documentos libres en el expediente: adjúntelos en la ficha del expediente.
        </p>
      ) : (
        <select
          id={id}
          className={inputClase}
          value={valor}
          onChange={(e) => onChange(e.target.value)}
        >
          <option value="">Elija un documento del expediente</option>
          {documentos.map((documento) => (
            <option key={documento.id} value={documento.id}>
              {documento.titulo}
            </option>
          ))}
        </select>
      )}
    </FormField>
  );
}

function Dato({
  etiqueta,
  children,
}: {
  etiqueta: string;
  children: React.ReactNode;
}) {
  return (
    <div className="break-words">
      <dt className="text-sm font-medium text-text-600">{etiqueta}</dt>
      <dd className="mt-1 text-sm text-text-900">{children}</dd>
    </div>
  );
}

function SeccionResumen({ ejecucion }: { ejecucion: EjecucionContrato }) {
  const { contrato, terminos, resumen } = ejecucion;
  const moneda = terminos.moneda || contrato.moneda || "";
  const formatoMoneda = (valor: string | null | undefined) =>
    valor ? `${valor} ${moneda}` : "—";

  return (
    <section aria-labelledby="resumen" className="mb-10">
      <h2 id="resumen" className="mb-4 text-xl font-semibold text-text-900">
        Resumen de la ejecución
      </h2>
      <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Dato etiqueta="Monto original">{formatoMoneda(terminos.monto_original)}</Dato>
        <Dato etiqueta="Monto efectivo">{formatoMoneda(terminos.monto_efectivo)}</Dato>
        <Dato etiqueta="Valuado conformado">{formatoMoneda(resumen.valuado_conformado)}</Dato>
        <Dato etiqueta="Valuado presentado">{formatoMoneda(resumen.valuado_presentado)}</Dato>
        <Dato etiqueta="Saldo contractual">{formatoMoneda(resumen.saldo)}</Dato>
        <Dato etiqueta="Facturado">{formatoMoneda(resumen.facturado)}</Dato>
        <Dato etiqueta="Inicio">
          {terminos.fecha_inicio ? formatearFechaDeNegocio(terminos.fecha_inicio) : "—"}
        </Dato>
        <Dato etiqueta="Fin efectivo">
          {terminos.fecha_fin ? formatearFechaDeNegocio(terminos.fecha_fin) : "—"}
        </Dato>
        <Dato etiqueta="Supervisor">
          {resumen.supervisor
            ? `${resumen.supervisor.nombre} · ${resumen.supervisor.cargo} · ${resumen.supervisor.referencia}`
            : "Sin supervisor"}
        </Dato>
        <Dato etiqueta="Hitos cumplidos">
          {resumen.hitos_cumplidos} de {resumen.hitos_total}
        </Dato>
        <Dato etiqueta="Entregables pendientes">{resumen.entregables_pendientes}</Dato>
        <Dato etiqueta="Estado de la ejecución">{resumen.estado_etiqueta}</Dato>
        <Dato etiqueta="Tipo de contratación">
          {contrato.flujo === "OBRAS" ? "Obras" : "Bienes y servicios"}
        </Dato>
      </dl>
    </section>
  );
}

function SeccionInicio({
  ejecucion,
  opciones,
  puedeEjecutar,
  confirmar,
  enviar,
}: {
  ejecucion: EjecucionContrato;
  opciones: OpcionesEjecucion | undefined;
  puedeEjecutar: boolean;
  confirmar: (pendiente: Pendiente) => void;
  enviar: (ruta: string, cuerpo: Record<string, unknown>, mensaje: string) => Promise<void>;
}) {
  const [fecha, setFecha] = useState(opciones?.hoy ?? hoyDeNegocio());
  const [documentoId, setDocumentoId] = useState("");
  const [observacion, setObservacion] = useState("");


  return (
    <section aria-labelledby="inicio" className="mb-10">
      <h2 id="inicio" className="mb-4 text-xl font-semibold text-text-900">
        Inicio de la ejecución
      </h2>
      {ejecucion.inicio ? (
        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Dato etiqueta="Fecha">
            {formatearFechaDeNegocio(ejecucion.inicio.fecha)}
          </Dato>
          <Dato etiqueta="Supervisor">{ejecucion.inicio.supervisor}</Dato>
          <Dato etiqueta="Acta">{ejecucion.inicio.documento.titulo}</Dato>
          <Dato etiqueta="Observación">{ejecucion.inicio.observacion ?? "—"}</Dato>
        </dl>
      ) : ejecucion.acciones.iniciar && puedeEjecutar ? (
        <>
          {!ejecucion.soy_supervisor && (
            <p className="mb-4 text-sm text-text-600">
              Solo el supervisor del contrato puede registrar el inicio.
            </p>
          )}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <FormField label="Fecha de inicio" htmlFor="inicio-fecha" required>
              <input
                id="inicio-fecha"
                type="date"
                className={inputClase}
                value={fecha}
                onChange={(e) => setFecha(e.target.value)}
              />
            </FormField>
            <SelectorDocumento
              id="inicio-documento"
              etiqueta="Acta de inicio"
              valor={documentoId}
              onChange={setDocumentoId}
              documentos={opciones?.documentos ?? []}
            />
            <div className="sm:col-span-2">
              <FormField label="Observación" htmlFor="inicio-observacion">
                <textarea
                  id="inicio-observacion"
                  className={inputClase}
                  maxLength={1000}
                  value={observacion}
                  onChange={(e) => setObservacion(e.target.value)}
                />
              </FormField>
            </div>
          </div>
          <Button
            type="button"
            onClick={() => {
              confirmar({
                titulo: "Registrar el inicio de la ejecución",
                descripcion: "Se registrará el inicio de la ejecución del contrato.",
                ejecutar: () =>
                  enviar(
                    "/inicio",
                    {
                      fecha,
                      documento_id: documentoId,
                      observacion: observacion || null,
                    },
                    "Inicio de la ejecución registrado.",
                  ),
              });
            }}
            disabled={!ejecucion.soy_supervisor || !documentoId || !fecha}
          >
            Registrar inicio
          </Button>
        </>
      ) : null}
    </section>
  );
}

function SeccionHitos({
  ejecucion,
  puedeEjecutar,
  confirmar,
  enviar,
}: {
  ejecucion: EjecucionContrato;
  puedeEjecutar: boolean;
  confirmar: (pendiente: Pendiente) => void;
  enviar: (ruta: string, cuerpo: Record<string, unknown>, mensaje: string) => Promise<void>;
}) {
  const [descripcion, setDescripcion] = useState("");
  const [fechaPrevista, setFechaPrevista] = useState("");
  const [montoPrevisto, setMontoPrevisto] = useState("");
  const [porcentajePrevisto, setPorcentajePrevisto] = useState("");
  const [obligatorio, setObligatorio] = useState(true);
  const [anulando, setAnulando] = useState<Anulando | null>(null);
  const [motivo, setMotivo] = useState("");

  const hitos = ejecucion.hitos;

  return (
    <section aria-labelledby="hitos" className="mb-10">
      <h2 id="hitos" className="mb-4 text-xl font-semibold text-text-900">
        Hitos
      </h2>
      {hitos.length === 0 ? (
        <EmptyState title="Sin hitos" description="Este contrato no tiene hitos registrados." />
      ) : (
        <div role="region" aria-label="Tabla de hitos" tabIndex={0} className="relative overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <caption className="sr-only">Hitos del contrato</caption>
            <thead>
              <tr className="border-b border-border-subtle">
                <th scope="col" className="px-3 py-2">Hito</th>
                <th scope="col" className="px-3 py-2">Descripción</th>
                <th scope="col" className="px-3 py-2">Fecha prevista</th>
                <th scope="col" className="px-3 py-2">Monto previsto</th>
                <th scope="col" className="px-3 py-2">%</th>
                <th scope="col" className="px-3 py-2">Obligatorio</th>
                <th scope="col" className="px-3 py-2">Estado</th>
                <th scope="col" className="px-3 py-2">Valuado</th>
                <th scope="col" className="px-3 py-2">Facturado</th>
                <th scope="col" className="px-3 py-2">
                  <span className="sr-only">Acciones</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {hitos.map((hito) => (
                <tr key={hito.id} className="border-b border-border-subtle">
                  <td className="px-3 py-2">{hito.referencia}</td>
                  <td className="px-3 py-2 break-words">{hito.descripcion}</td>
                  <td className="px-3 py-2">{formatearFechaDeNegocio(hito.fecha_prevista)}</td>
                  <td className="px-3 py-2">{hito.monto_previsto ?? "—"}</td>
                  <td className="px-3 py-2">{hito.porcentaje_previsto ?? "—"}</td>
                  <td className="px-3 py-2">{hito.obligatorio ? "Sí" : "No"}</td>
                  <td className="px-3 py-2">
                    {hito.estado === "ANULADO"
                      ? "Anulado"
                      : hito.cumplido
                        ? `Cumplido · ${hito.recepcion ?? ""}`
                        : "Pendiente"}
                  </td>
                  <td className="px-3 py-2">{hito.valuado_conformado || "—"}</td>
                  <td className="px-3 py-2">{hito.facturado || "—"}</td>
                  <td className="px-3 py-2">
                    {hito.estado === "VIGENTE" && !hito.cumplido && puedeEjecutar ? (
                      <Button type="button" onClick={() => setAnulando({ ruta: `/hitos/${hito.id}/anular`, titulo: "Anular el hito" })}>
                        Anular
                      </Button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {anulando ? (
        <div className="mt-4 grid grid-cols-1 gap-4 rounded-md border border-border-subtle p-4 sm:grid-cols-2">
          <FormField label="Motivo de la anulación" htmlFor="hito-motivo" required>
            <input
              id="hito-motivo"
              className={inputClase}
              maxLength={500}
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
            />
          </FormField>
          <div className="flex items-end">
            <Button
              type="button"
              disabled={!motivo}
              onClick={() =>
                confirmar({
                  titulo: anulando.titulo,
                  descripcion: "Se anulará el registro seleccionado.",
                  ejecutar: () => enviar(anulando.ruta, { motivo }, "Anulación registrada."),
                })
              }
            >
              Confirmar anulación
            </Button>
          </div>
        </div>
      ) : null}

      {ejecucion.acciones.registrar && puedeEjecutar ? (
        <div className="mt-6 grid grid-cols-1 gap-4 rounded-md border border-border-subtle p-4 sm:grid-cols-2">
          <h3 className="text-base font-semibold text-text-900 sm:col-span-2">Nuevo hito</h3>
          <div className="sm:col-span-2">
            <FormField label="Descripción" htmlFor="hito-descripcion" required>
              <input
                id="hito-descripcion"
                className={inputClase}
                maxLength={500}
                value={descripcion}
                onChange={(e) => setDescripcion(e.target.value)}
              />
            </FormField>
          </div>
          <FormField label="Fecha prevista" htmlFor="hito-fecha" required>
            <input
              id="hito-fecha"
              type="date"
              className={inputClase}
              value={fechaPrevista}
              onChange={(e) => setFechaPrevista(e.target.value)}
            />
          </FormField>
          <FormField label="Monto previsto" htmlFor="hito-monto">
            <input
              id="hito-monto"
              className={inputClase}
              inputMode="decimal"
              value={montoPrevisto}
              onChange={(e) => setMontoPrevisto(e.target.value)}
            />
          </FormField>
          <FormField label="Porcentaje previsto" htmlFor="hito-porcentaje">
            <input
              id="hito-porcentaje"
              className={inputClase}
              value={porcentajePrevisto}
              onChange={(e) => setPorcentajePrevisto(e.target.value)}
            />
          </FormField>
          <div className="flex items-end gap-2 pb-2">
            <input
              id="hito-obligatorio"
              type="checkbox"
              checked={obligatorio}
              onChange={(e) => setObligatorio(e.target.checked)}
            />
            <label htmlFor="hito-obligatorio" className="text-sm text-text-900">
              Obligatorio
            </label>
          </div>
          <div className="flex items-end sm:col-span-2">
            <Button
              type="button"
              disabled={!descripcion || !fechaPrevista}
              onClick={() =>
                confirmar({
                  titulo: "Registrar hito",
                  descripcion: "Se registrará el nuevo hito.",
                  ejecutar: () =>
                    enviar(
                      "/hitos",
                      {
                        descripcion,
                        fecha_prevista: fechaPrevista,
                        monto_previsto: montoPrevisto || null,
                        porcentaje_previsto: porcentajePrevisto || null,
                        obligatorio,
                      },
                      "Hito registrado.",
                    ),
                })
              }
            >
              Registrar hito
            </Button>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function SeccionEntregables({
  ejecucion,
  opciones,
  puedeEjecutar,
  confirmar,
  enviar,
}: {
  ejecucion: EjecucionContrato;
  opciones: OpcionesEjecucion | undefined;
  puedeEjecutar: boolean;
  confirmar: (pendiente: Pendiente) => void;
  enviar: (ruta: string, cuerpo: Record<string, unknown>, mensaje: string) => Promise<void>;
}) {
  const [descripcion, setDescripcion] = useState("");
  const [vencimiento, setVencimiento] = useState("");
  const [hitoId, setHitoId] = useState("");
  const [obligatorio, setObligatorio] = useState(true);
  const [entrega, setEntrega] = useState<{ id: string; abierto: boolean } | null>(null);
  const [fechaEntrega, setFechaEntrega] = useState("");
  const [evidenciaId, setEvidenciaId] = useState("");
  const [observacionEntrega, setObservacionEntrega] = useState("");
  const [revision, setRevision] = useState<{ id: string; resultado: "CONFORME" | "RECHAZADA" } | null>(null);
  const [fechaRevision, setFechaRevision] = useState(hoyDeNegocio());
  const [observacionRevision, setObservacionRevision] = useState("");

  const hitosVigentes = ejecucion.hitos.filter((hito) => hito.estado === "VIGENTE");

  return (
    <section aria-labelledby="entregables" className="mb-10">
      <h2 id="entregables" className="mb-4 text-xl font-semibold text-text-900">
        Entregables
      </h2>
      {ejecucion.entregables.length === 0 ? (
        <EmptyState title="Sin entregables" description="Este contrato no tiene entregables registrados." />
      ) : (
        <div role="region" aria-label="Tabla de entregables" tabIndex={0} className="relative overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <caption className="sr-only">Entregables del contrato</caption>
            <thead>
              <tr className="border-b border-border-subtle">
                <th scope="col" className="px-3 py-2">Entregable</th>
                <th scope="col" className="px-3 py-2">Descripción</th>
                <th scope="col" className="px-3 py-2">Hito</th>
                <th scope="col" className="px-3 py-2">Vencimiento</th>
                <th scope="col" className="px-3 py-2">Obligatorio</th>
                <th scope="col" className="px-3 py-2">Situación</th>
                <th scope="col" className="px-3 py-2">Entregas</th>
                <th scope="col" className="px-3 py-2">
                  <span className="sr-only">Acciones</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {ejecucion.entregables.map((entregable) => (
                <tr key={entregable.id} className="border-b border-border-subtle">
                  <td className="px-3 py-2">{entregable.referencia}</td>
                  <td className="px-3 py-2 break-words">{entregable.descripcion}</td>
                  <td className="px-3 py-2">{entregable.hito ?? "—"}</td>
                  <td className="px-3 py-2">{formatearFechaDeNegocio(entregable.fecha_vencimiento)}</td>
                  <td className="px-3 py-2">{entregable.obligatorio ? "Sí" : "No"}</td>
                  <td className="px-3 py-2">{entregable.situacion}</td>
                  <td className="px-3 py-2">
                    {entregable.entregas.map((entrega) => (
                      <div key={entrega.id} className="break-words">
                        {entrega.referencia} · {formatearFechaDeNegocio(entrega.fecha_entrega)} ·{" "}
                        {entrega.estado}
                      </div>
                    ))}
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex flex-col gap-2">
                      {entregable.estado === "VIGENTE" &&
                      (entregable.situacion === "PENDIENTE" || entregable.situacion === "RECHAZADO") &&
                      ejecucion.acciones.registrar_hechos && puedeEjecutar ? (
                        <Button type="button" onClick={() => setEntrega({ id: entregable.id, abierto: true })}>
                          Registrar entrega
                        </Button>
                      ) : null}
                      {entregable.entregas
                        .filter((entrega) => entrega.estado === "ENTREGADA")
                        .map((entrega) =>
                          ejecucion.soy_supervisor ? (
                            <div key={entrega.id} className="flex gap-2">
                              <Button
                                type="button"
                                onClick={() =>
                                  setRevision({ id: entrega.id, resultado: "CONFORME" })
                                }
                              >
                                Conformar
                              </Button>
                              <Button
                                type="button"
                                onClick={() =>
                                  setRevision({ id: entrega.id, resultado: "RECHAZADA" })
                                }
                              >
                                Rechazar
                              </Button>
                            </div>
                          ) : null,
                        )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {entrega?.abierto ? (
        <div className="mt-6 grid grid-cols-1 gap-4 rounded-md border border-border-subtle p-4 sm:grid-cols-2">
          <h3 className="text-base font-semibold text-text-900 sm:col-span-2">Registrar entrega</h3>
          <FormField label="Fecha de entrega" htmlFor="entrega-fecha" required>
            <input
              id="entrega-fecha"
              type="date"
              className={inputClase}
              value={fechaEntrega}
              onChange={(e) => setFechaEntrega(e.target.value)}
            />
          </FormField>
          <SelectorDocumento
            id="entrega-evidencia"
            etiqueta="Evidencia"
            valor={evidenciaId}
            onChange={setEvidenciaId}
            documentos={opciones?.documentos ?? []}
          />
          <div className="sm:col-span-2">
            <FormField label="Observación" htmlFor="entrega-observacion">
              <textarea
                id="entrega-observacion"
                className={inputClase}
                value={observacionEntrega}
                onChange={(e) => setObservacionEntrega(e.target.value)}
              />
            </FormField>
          </div>
          <div className="flex items-end sm:col-span-2">
            <Button
              type="button"
              disabled={!fechaEntrega || !evidenciaId}
              onClick={() =>
                confirmar({
                  titulo: "Registrar entrega",
                  descripcion: "Se registrará la entrega del entregable.",
                  ejecutar: () =>
                    enviar(
                      `/entregables/${entrega.id}/entregas`,
                      {
                        fecha_entrega: fechaEntrega,
                        documento_id: evidenciaId,
                        observacion: observacionEntrega || null,
                      },
                      "Entrega registrada.",
                    ),
                })
              }
            >
              Registrar entrega
            </Button>
          </div>
        </div>
      ) : null}

      {revision ? (
        <div className="mt-6 grid grid-cols-1 gap-4 rounded-md border border-border-subtle p-4 sm:grid-cols-2">
          <h3 className="text-base font-semibold text-text-900 sm:col-span-2">
            {revision.resultado === "CONFORME" ? "Conformar entrega" : "Rechazar entrega"}
          </h3>
          <FormField label="Fecha de revisión" htmlFor="revision-fecha" required>
            <input
              id="revision-fecha"
              type="date"
              className={inputClase}
              value={fechaRevision}
              onChange={(e) => setFechaRevision(e.target.value)}
            />
          </FormField>
          {revision.resultado === "RECHAZADA" ? (
            <FormField label="Observación" htmlFor="revision-observacion" required>
              <textarea
                id="revision-observacion"
                className={inputClase}
                value={observacionRevision}
                onChange={(e) => setObservacionRevision(e.target.value)}
              />
            </FormField>
          ) : null}
          <div className="flex items-end gap-2 sm:col-span-2">
            <Button
              type="button"
              disabled={!fechaRevision || (revision.resultado === "RECHAZADA" && !observacionRevision)}
              onClick={() =>
                confirmar({
                  titulo: revision.resultado === "CONFORME" ? "Conformar entrega" : "Rechazar entrega",
                  descripcion: "Se registrará la revisión de la entrega.",
                  ejecutar: () =>
                    enviar(
                      `/entregas/${revision.id}/revision`,
                      {
                        resultado: revision.resultado,
                        fecha_revision: fechaRevision,
                        observacion: observacionRevision || null,
                      },
                      revision.resultado === "CONFORME" ? "Entrega conformada." : "Entrega rechazada.",
                    ),
                })
              }
            >
              Confirmar revisión
            </Button>
          </div>
        </div>
      ) : null}

      {ejecucion.acciones.registrar_hechos && puedeEjecutar ? (
        <div className="mt-6 grid grid-cols-1 gap-4 rounded-md border border-border-subtle p-4 sm:grid-cols-2">
          <h3 className="text-base font-semibold text-text-900 sm:col-span-2">Nuevo entregable</h3>
          <div className="sm:col-span-2">
            <FormField label="Descripción" htmlFor="entregable-descripcion" required>
              <input
                id="entregable-descripcion"
                className={inputClase}
                value={descripcion}
                onChange={(e) => setDescripcion(e.target.value)}
              />
            </FormField>
          </div>
          <FormField label="Fecha de vencimiento" htmlFor="entregable-vencimiento" required>
            <input
              id="entregable-vencimiento"
              type="date"
              className={inputClase}
              value={vencimiento}
              onChange={(e) => setVencimiento(e.target.value)}
            />
          </FormField>
          <FormField label="Hito" htmlFor="entregable-hito">
            <select
              id="entregable-hito"
              className={inputClase}
              value={hitoId}
              onChange={(e) => setHitoId(e.target.value)}
            >
              <option value="">Sin hito</option>
              {hitosVigentes.map((hito) => (
                <option key={hito.id} value={hito.id}>
                  {hito.referencia} · {hito.descripcion}
                </option>
              ))}
            </select>
          </FormField>
          <div className="flex items-end gap-2 pb-2">
            <input
              id="entregable-obligatorio"
              type="checkbox"
              checked={obligatorio}
              onChange={(e) => setObligatorio(e.target.checked)}
            />
            <label htmlFor="entregable-obligatorio" className="text-sm text-text-900">
              Obligatorio
            </label>
          </div>
          <div className="flex items-end sm:col-span-2">
            <Button
              type="button"
              disabled={!descripcion || !vencimiento}
              onClick={() =>
                confirmar({
                  titulo: "Registrar entregable",
                  descripcion: "Se registrará el nuevo entregable.",
                  ejecutar: () =>
                    enviar(
                      "/entregables",
                      {
                        descripcion,
                        fecha_vencimiento: vencimiento,
                        obligatorio,
                        hito_id: hitoId || null,
                      },
                      "Entregable registrado.",
                    ),
                })
              }
            >
              Registrar entregable
            </Button>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function SeccionValuaciones({
  ejecucion,
  opciones,
  puedeEjecutar,
  confirmar,
  enviar,
}: {
  ejecucion: EjecucionContrato;
  opciones: OpcionesEjecucion | undefined;
  puedeEjecutar: boolean;
  confirmar: (pendiente: Pendiente) => void;
  enviar: (ruta: string, cuerpo: Record<string, unknown>, mensaje: string) => Promise<void>;
}) {
  const [hitoId, setHitoId] = useState("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [fecha, setFecha] = useState("");
  const [monto, setMonto] = useState("");
  const [documentoId, setDocumentoId] = useState("");
  const [resolucion, setResolucion] = useState<{ id: string; resultado: "CONFORMADA" | "REPARADA" } | null>(null);
  const [fechaConformidad, setFechaConformidad] = useState(hoyDeNegocio());
  const [reparos, setReparos] = useState("");
  const [anulando, setAnulando] = useState<Anulando | null>(null);
  const [motivo, setMotivo] = useState("");

  const hitosVigentes = ejecucion.hitos.filter((hito) => hito.estado === "VIGENTE");

  return (
    <section aria-labelledby="valuaciones" className="mb-10">
      <h2 id="valuaciones" className="mb-4 text-xl font-semibold text-text-900">
        Valuaciones
      </h2>
      {ejecucion.valuaciones.length === 0 ? (
        <EmptyState title="Sin valuaciones" description="Este contrato no tiene valuaciones presentadas." />
      ) : (
        <div role="region" aria-label="Tabla de valuaciones" tabIndex={0} className="relative overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <caption className="sr-only">Valuaciones del contrato</caption>
            <thead>
              <tr className="border-b border-border-subtle">
                <th scope="col" className="px-3 py-2">Valuación</th>
                <th scope="col" className="px-3 py-2">Hito</th>
                <th scope="col" className="px-3 py-2">Período</th>
                <th scope="col" className="px-3 py-2">Fecha</th>
                <th scope="col" className="px-3 py-2">Monto</th>
                <th scope="col" className="px-3 py-2">Estado</th>
                <th scope="col" className="px-3 py-2">Acumulado</th>
                <th scope="col" className="px-3 py-2">Supervisor</th>
                <th scope="col" className="px-3 py-2">Reparos/Motivo</th>
                <th scope="col" className="px-3 py-2">
                  <span className="sr-only">Acciones</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {ejecucion.valuaciones.map((valuacion) => (
                <tr key={valuacion.id} className="border-b border-border-subtle">
                  <td className="px-3 py-2">{valuacion.referencia}</td>
                  <td className="px-3 py-2">{valuacion.hito}</td>
                  <td className="px-3 py-2">
                    {formatearFechaDeNegocio(valuacion.periodo_desde)} –{" "}
                    {formatearFechaDeNegocio(valuacion.periodo_hasta)}
                  </td>
                  <td className="px-3 py-2">{formatearFechaDeNegocio(valuacion.fecha)}</td>
                  <td className="px-3 py-2">{valuacion.monto} {valuacion.moneda}</td>
                  <td className="px-3 py-2">{valuacion.estado_etiqueta}</td>
                  <td className="px-3 py-2">{valuacion.acumulado ?? "—"}</td>
                  <td className="px-3 py-2">{valuacion.supervisor ?? "—"}</td>
                  <td className="px-3 py-2 break-words">
                    {valuacion.reparos || valuacion.motivo_anulacion || "—"}
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex flex-col gap-2">
                      {valuacion.estado === "PRESENTADA" ? (
                        <>
                          {ejecucion.soy_supervisor ? (
                            <div className="flex gap-2">
                              <Button
                                type="button"
                                onClick={() => setResolucion({ id: valuacion.id, resultado: "CONFORMADA" })}
                              >
                                Conformar
                              </Button>
                              <Button
                                type="button"
                                onClick={() => setResolucion({ id: valuacion.id, resultado: "REPARADA" })}
                              >
                                Reparar
                              </Button>
                            </div>
                          ) : null}
                          {puedeEjecutar ? (
                            <Button
                              type="button"
                              onClick={() =>
                                setAnulando({
                                  ruta: `/valuaciones/${valuacion.id}/anular`,
                                  titulo: "Anular valuación",
                                })
                              }
                            >
                              Anular
                            </Button>
                          ) : null}
                        </>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {anulando ? (
        <div className="mt-4 grid grid-cols-1 gap-4 rounded-md border border-border-subtle p-4 sm:grid-cols-2">
          <FormField label="Motivo de la anulación" htmlFor="valuacion-motivo" required>
            <input
              id="valuacion-motivo"
              className={inputClase}
              maxLength={500}
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
            />
          </FormField>
          <div className="flex items-end">
            <Button
              type="button"
              disabled={!motivo}
              onClick={() =>
                confirmar({
                  titulo: anulando.titulo,
                  descripcion: "Se anulará la valuación seleccionada.",
                  ejecutar: () => enviar(anulando.ruta, { motivo }, "Anulación registrada."),
                })
              }
            >
              Confirmar anulación
            </Button>
          </div>
        </div>
      ) : null}

      {resolucion ? (
        <div className="mt-6 grid grid-cols-1 gap-4 rounded-md border border-border-subtle p-4 sm:grid-cols-2">
          <h3 className="text-base font-semibold text-text-900 sm:col-span-2">
            {resolucion.resultado === "CONFORMADA" ? "Conformar valuación" : "Reparar valuación"}
          </h3>
          <FormField label="Fecha de conformidad" htmlFor="conformidad-fecha" required>
            <input
              id="conformidad-fecha"
              type="date"
              className={inputClase}
              value={fechaConformidad}
              onChange={(e) => setFechaConformidad(e.target.value)}
            />
          </FormField>
          {resolucion.resultado === "REPARADA" ? (
            <FormField label="Reparos" htmlFor="valuacion-reparos" required>
              <textarea
                id="valuacion-reparos"
                className={inputClase}
                value={reparos}
                onChange={(e) => setReparos(e.target.value)}
              />
            </FormField>
          ) : null}
          <div className="flex items-end gap-2 sm:col-span-2">
            <Button
              type="button"
              disabled={!fechaConformidad || (resolucion.resultado === "REPARADA" && !reparos)}
              onClick={() =>
                confirmar({
                  titulo: resolucion.resultado === "CONFORMADA" ? "Conformar valuación" : "Reparar valuación",
                  descripcion: "Se registrará la resolución de la valuación.",
                  ejecutar: () =>
                    enviar(
                      `/valuaciones/${resolucion.id}/resolucion`,
                      {
                        resultado: resolucion.resultado,
                        fecha_conformidad: fechaConformidad,
                        reparos: reparos || null,
                      },
                      resolucion.resultado === "CONFORMADA" ? "Valuación conformada." : "Valuación reparada.",
                    ),
                })
              }
            >
              Confirmar resolución
            </Button>
          </div>
        </div>
      ) : null}

      {ejecucion.acciones.registrar_hechos && puedeEjecutar ? (
        <div className="mt-6 grid grid-cols-1 gap-4 rounded-md border border-border-subtle p-4 sm:grid-cols-2">
          <h3 className="text-base font-semibold text-text-900 sm:col-span-2">Presentar valuación</h3>
          <FormField label="Hito" htmlFor="valuacion-hito" required>
            <select
              id="valuacion-hito"
              className={inputClase}
              value={hitoId}
              onChange={(e) => setHitoId(e.target.value)}
            >
              <option value="">Elija un hito</option>
              {hitosVigentes.map((hito) => (
                <option key={hito.id} value={hito.id}>
                  {hito.referencia} · {hito.descripcion}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Período desde" htmlFor="valuacion-desde" required>
            <input
              id="valuacion-desde"
              type="date"
              className={inputClase}
              value={desde}
              onChange={(e) => setDesde(e.target.value)}
            />
          </FormField>
          <FormField label="Período hasta" htmlFor="valuacion-hasta" required>
            <input
              id="valuacion-hasta"
              type="date"
              className={inputClase}
              value={hasta}
              onChange={(e) => setHasta(e.target.value)}
            />
          </FormField>
          <FormField label="Fecha" htmlFor="valuacion-fecha" required>
            <input
              id="valuacion-fecha"
              type="date"
              className={inputClase}
              value={fecha}
              onChange={(e) => setFecha(e.target.value)}
            />
          </FormField>
          <FormField label="Monto" htmlFor="valuacion-monto" required>
            <input
              id="valuacion-monto"
              className={inputClase}
              inputMode="decimal"
              value={monto}
              onChange={(e) => setMonto(e.target.value)}
            />
          </FormField>
          <SelectorDocumento
            id="valuacion-soporte"
            etiqueta="Soporte"
            valor={documentoId}
            onChange={setDocumentoId}
            documentos={opciones?.documentos ?? []}
          />
          <div className="flex items-end sm:col-span-2">
            <Button
              type="button"
              disabled={!hitoId || !desde || !hasta || !fecha || !monto}
              onClick={() =>
                confirmar({
                  titulo: "Presentar valuación",
                  descripcion: "Se presentará la valuación.",
                  ejecutar: () =>
                    enviar(
                      "/valuaciones",
                      {
                        hito_id: hitoId,
                        periodo_desde: desde,
                        periodo_hasta: hasta,
                        fecha,
                        monto,
                        documento_id: documentoId,
                      },
                      "Valuación presentada.",
                    ),
                })
              }
            >
              Presentar valuación
            </Button>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function SeccionRecepciones({
  ejecucion,
  opciones,
  puedeEjecutar,
  confirmar,
  enviar,
}: {
  ejecucion: EjecucionContrato;
  opciones: OpcionesEjecucion | undefined;
  puedeEjecutar: boolean;
  confirmar: (pendiente: Pendiente) => void;
  enviar: (ruta: string, cuerpo: Record<string, unknown>, mensaje: string) => Promise<void>;
}) {
  const [fechaTerminacion, setFechaTerminacion] = useState("");
  const [documentoTerminacionId, setDocumentoTerminacionId] = useState("");
  const [observacionTerminacion, setObservacionTerminacion] = useState("");
  const [tipo, setTipo] = useState<"PARCIAL" | "PROVISIONAL" | "DEFINITIVA">("PARCIAL");
  const [fecha, setFecha] = useState("");
  const [documentoId, setDocumentoId] = useState("");
  const [observacion, setObservacion] = useState("");
  const [hitoIds, setHitoIds] = useState<string[]>([]);
  const [representanteId, setRepresentanteId] = useState("");
  const [finGarantia, setFinGarantia] = useState("");
  const [anulando, setAnulando] = useState<Anulando | null>(null);
  const [motivo, setMotivo] = useState("");

  const tiposPermitidos: { valor: "PARCIAL" | "PROVISIONAL" | "DEFINITIVA"; etiqueta: string }[] = [];
  if (ejecucion.acciones.recepcion_parcial) tiposPermitidos.push({ valor: "PARCIAL", etiqueta: "Recepción parcial" });
  if (ejecucion.acciones.recepcion_provisional) tiposPermitidos.push({ valor: "PROVISIONAL", etiqueta: "Aceptación provisional" });
  if (ejecucion.acciones.recepcion_definitiva) tiposPermitidos.push({ valor: "DEFINITIVA", etiqueta: "Recepción definitiva" });

  const hitosVigentesNoCumplidos = ejecucion.hitos.filter(
    (hito) => hito.estado === "VIGENTE" && !hito.cumplido,
  );

  return (
    <section aria-labelledby="recepciones" className="mb-10">
      <h2 id="recepciones" className="mb-4 text-xl font-semibold text-text-900">
        Recepciones
      </h2>

      {ejecucion.contrato.flujo === "OBRAS" && ejecucion.acciones.terminar && ejecucion.soy_supervisor ? (
        <div className="mb-6 grid grid-cols-1 gap-4 rounded-md border border-border-subtle p-4 sm:grid-cols-2">
          <h3 className="text-base font-semibold text-text-900 sm:col-span-2">Acta de terminación</h3>
          <FormField label="Fecha" htmlFor="terminacion-fecha" required>
            <input
              id="terminacion-fecha"
              type="date"
              className={inputClase}
              value={fechaTerminacion}
              onChange={(e) => setFechaTerminacion(e.target.value)}
            />
          </FormField>
          <SelectorDocumento
            id="terminacion-documento"
            etiqueta="Acta"
            valor={documentoTerminacionId}
            onChange={setDocumentoTerminacionId}
            documentos={opciones?.documentos ?? []}
          />
          <div className="sm:col-span-2">
            <FormField label="Observación" htmlFor="terminacion-observacion">
              <textarea
                id="terminacion-observacion"
                className={inputClase}
                value={observacionTerminacion}
                onChange={(e) => setObservacionTerminacion(e.target.value)}
              />
            </FormField>
          </div>
          <div className="flex items-end sm:col-span-2">
            <Button
              type="button"
              disabled={!fechaTerminacion || !documentoTerminacionId}
              onClick={() =>
                confirmar({
                  titulo: "Registrar terminación",
                  descripcion: "Se registrará la terminación de la obra.",
                  ejecutar: () =>
                    enviar(
                      "/terminacion",
                      {
                        fecha: fechaTerminacion,
                        documento_id: documentoTerminacionId,
                        observacion: observacionTerminacion || null,
                      },
                      "Terminación registrada.",
                    ),
                })
              }
            >
              Registrar terminación
            </Button>
          </div>
        </div>
      ) : ejecucion.terminacion ? (
        <p className="mb-6 text-sm text-text-900">
          Obra terminada el {formatearFechaDeNegocio(ejecucion.terminacion.fecha)}
        </p>
      ) : null}

      {ejecucion.recepciones.length === 0 ? (
        <EmptyState title="Sin recepciones" description="Este contrato no tiene recepciones registradas." />
      ) : (
        <div role="region" aria-label="Tabla de recepciones" tabIndex={0} className="relative overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <caption className="sr-only">Recepciones del contrato</caption>
            <thead>
              <tr className="border-b border-border-subtle">
                <th scope="col" className="px-3 py-2">Recepción</th>
                <th scope="col" className="px-3 py-2">Tipo</th>
                <th scope="col" className="px-3 py-2">Fecha</th>
                <th scope="col" className="px-3 py-2">Hitos</th>
                <th scope="col" className="px-3 py-2">Supervisor</th>
                <th scope="col" className="px-3 py-2">Representante</th>
                <th scope="col" className="px-3 py-2">Fin de garantía</th>
                <th scope="col" className="px-3 py-2">Estado</th>
                <th scope="col" className="px-3 py-2">
                  <span className="sr-only">Acciones</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {ejecucion.recepciones.map((recepcion) => (
                <tr key={recepcion.id} className="border-b border-border-subtle">
                  <td className="px-3 py-2">{recepcion.referencia}</td>
                  <td className="px-3 py-2">{recepcion.tipo_etiqueta}</td>
                  <td className="px-3 py-2">{formatearFechaDeNegocio(recepcion.fecha)}</td>
                  <td className="px-3 py-2 break-words">{recepcion.hitos.join(", ")}</td>
                  <td className="px-3 py-2">{recepcion.supervisor}</td>
                  <td className="px-3 py-2">{recepcion.representante ?? "—"}</td>
                  <td className="px-3 py-2">
                    {recepcion.fin_garantia ? formatearFechaDeNegocio(recepcion.fin_garantia) : "—"}
                  </td>
                  <td className="px-3 py-2">{recepcion.estado}</td>
                  <td className="px-3 py-2">
                    {recepcion.tipo === "PARCIAL" && recepcion.estado === "CONFORME" && puedeEjecutar ? (
                      <Button
                        type="button"
                        onClick={() =>
                          setAnulando({
                            ruta: `/recepciones/${recepcion.id}/anular`,
                            titulo: "Anular recepción",
                          })
                        }
                      >
                        Anular
                      </Button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {anulando ? (
        <div className="mt-4 grid grid-cols-1 gap-4 rounded-md border border-border-subtle p-4 sm:grid-cols-2">
          <FormField label="Motivo de la anulación" htmlFor="recepcion-motivo" required>
            <input
              id="recepcion-motivo"
              className={inputClase}
              maxLength={500}
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
            />
          </FormField>
          <div className="flex items-end">
            <Button
              type="button"
              disabled={!motivo}
              onClick={() =>
                confirmar({
                  titulo: anulando.titulo,
                  descripcion: "Se anulará la recepción seleccionada.",
                  ejecutar: () => enviar(anulando.ruta, { motivo }, "Anulación registrada."),
                })
              }
            >
              Confirmar anulación
            </Button>
          </div>
        </div>
      ) : null}

      {ejecucion.soy_supervisor && tiposPermitidos.length > 0 ? (
        <div className="mt-6 grid grid-cols-1 gap-4 rounded-md border border-border-subtle p-4 sm:grid-cols-2">
          <h3 className="text-base font-semibold text-text-900 sm:col-span-2">Registrar recepción</h3>
          <FormField label="Tipo" htmlFor="recepcion-tipo" required>
            <select
              id="recepcion-tipo"
              className={inputClase}
              value={tipo}
              onChange={(e) => setTipo(e.target.value as "PARCIAL" | "PROVISIONAL" | "DEFINITIVA")}
            >
              {tiposPermitidos.map((tipo) => (
                <option key={tipo.valor} value={tipo.valor}>
                  {tipo.etiqueta}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Fecha" htmlFor="recepcion-fecha" required>
            <input
              id="recepcion-fecha"
              type="date"
              className={inputClase}
              value={fecha}
              onChange={(e) => setFecha(e.target.value)}
            />
          </FormField>
          <SelectorDocumento
            id="recepcion-documento"
            etiqueta="Acta"
            valor={documentoId}
            onChange={setDocumentoId}
            documentos={opciones?.documentos ?? []}
          />
          <div className="sm:col-span-2">
            <FormField label="Observación" htmlFor="recepcion-observacion">
              <textarea
                id="recepcion-observacion"
                className={inputClase}
                value={observacion}
                onChange={(e) => setObservacion(e.target.value)}
              />
            </FormField>
          </div>
          {tipo === "PARCIAL" ? (
            <fieldset className="sm:col-span-2">
              <legend className="mb-2 text-sm font-medium text-text-900">Hitos recibidos</legend>
              <div className="grid grid-cols-1 gap-2">
                {hitosVigentesNoCumplidos.map((hito) => (
                  <label key={hito.id} className="flex items-center gap-2 text-sm text-text-900">
                    <input
                      type="checkbox"
                      checked={hitoIds.includes(hito.id)}
                      onChange={(e) =>
                        setHitoIds((prev) =>
                          e.target.checked ? [...prev, hito.id] : prev.filter((id) => id !== hito.id),
                        )
                      }
                    />
                    {hito.referencia} · {hito.descripcion}
                  </label>
                ))}
              </div>
            </fieldset>
          ) : null}
          {ejecucion.contrato.flujo === "OBRAS" && (tipo === "PROVISIONAL" || tipo === "DEFINITIVA") ? (
            <FormField label="Representante del contratante" htmlFor="recepcion-representante" required>
              <select
                id="recepcion-representante"
                className={inputClase}
                value={representanteId}
                onChange={(e) => setRepresentanteId(e.target.value)}
              >
                <option value="">Elija un representante</option>
                {(opciones?.representantes ?? []).map((representante) => (
                  <option key={representante.id} value={representante.id}>
                    {representante.codigo} · {representante.nombre}
                  </option>
                ))}
              </select>
            </FormField>
          ) : null}
          {tipo === "PROVISIONAL" ? (
            <FormField label="Fin de la garantía" htmlFor="recepcion-garantia" required>
              <input
                id="recepcion-garantia"
                type="date"
                className={inputClase}
                value={finGarantia}
                onChange={(e) => setFinGarantia(e.target.value)}
              />
            </FormField>
          ) : null}
          <div className="flex items-end sm:col-span-2">
            <Button
              type="button"
              disabled={
                !fecha ||
                !documentoId ||
                (tipo === "PARCIAL" && hitoIds.length === 0) ||
                (ejecucion.contrato.flujo === "OBRAS" &&
                  (tipo === "PROVISIONAL" || tipo === "DEFINITIVA") &&
                  !representanteId) ||
                (tipo === "PROVISIONAL" && !finGarantia)
              }
              onClick={() =>
                confirmar({
                  titulo: "Registrar recepción",
                  descripcion: "Se registrará la recepción seleccionada.",
                  ejecutar: () =>
                    enviar(
                      "/recepciones",
                      {
                        tipo,
                        fecha,
                        documento_id: documentoId,
                        observacion: observacion || null,
                        hito_ids: tipo === "PARCIAL" ? hitoIds : [],
                        representante_cargo_id:
                          ejecucion.contrato.flujo === "OBRAS" &&
                          (tipo === "PROVISIONAL" || tipo === "DEFINITIVA")
                            ? representanteId
                            : null,
                        fin_garantia: tipo === "PROVISIONAL" ? finGarantia : null,
                      },
                      "Recepción registrada.",
                    ),
                })
              }
            >
              Registrar recepción
            </Button>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function SeccionFacturas({
  ejecucion,
  opciones,
  puedeEjecutar,
  confirmar,
  enviar,
}: {
  ejecucion: EjecucionContrato;
  opciones: OpcionesEjecucion | undefined;
  puedeEjecutar: boolean;
  confirmar: (pendiente: Pendiente) => void;
  enviar: (ruta: string, cuerpo: Record<string, unknown>, mensaje: string) => Promise<void>;
}) {
  const [numero, setNumero] = useState("");
  const [fecha, setFecha] = useState("");
  const [monto, setMonto] = useState("");
  const [hitoId, setHitoId] = useState("");
  const [recepcionId, setRecepcionId] = useState("");
  const [fechaConformidad, setFechaConformidad] = useState(hoyDeNegocio());
  const [documentoId, setDocumentoId] = useState("");
  const [anulando, setAnulando] = useState<Anulando | null>(null);
  const [motivo, setMotivo] = useState("");

  const hitosVigentes = ejecucion.hitos.filter((hito) => hito.estado === "VIGENTE");
  const recepcionesConformes = ejecucion.recepciones.filter(
    (recepcion) => recepcion.estado === "CONFORME" && recepcion.hito_ids.includes(hitoId),
  );

  return (
    <section aria-labelledby="facturas" className="mb-10">
      <h2 id="facturas" className="mb-4 text-xl font-semibold text-text-900">
        Facturas / cuentas vinculadas
      </h2>
      <p className="mb-4 text-sm text-text-600">
        La factura se vincula a un hito y a una recepción conforme. No genera causado, cuentas por
        pagar, asientos ni pagos.
      </p>

      {ejecucion.facturas.length === 0 ? (
        <EmptyState title="Sin facturas" description="Este contrato no tiene facturas vinculadas." />
      ) : (
        <div role="region" aria-label="Tabla de facturas" tabIndex={0} className="relative overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <caption className="sr-only">Facturas vinculadas al contrato</caption>
            <thead>
              <tr className="border-b border-border-subtle">
                <th scope="col" className="px-3 py-2">Factura</th>
                <th scope="col" className="px-3 py-2">N.º de documento</th>
                <th scope="col" className="px-3 py-2">Fecha</th>
                <th scope="col" className="px-3 py-2">Monto</th>
                <th scope="col" className="px-3 py-2">Hito</th>
                <th scope="col" className="px-3 py-2">Recepción</th>
                <th scope="col" className="px-3 py-2">Supervisor</th>
                <th scope="col" className="px-3 py-2">Estado</th>
                <th scope="col" className="px-3 py-2">
                  <span className="sr-only">Acciones</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {ejecucion.facturas.map((factura) => (
                <tr key={factura.id} className="border-b border-border-subtle">
                  <td className="px-3 py-2">{factura.referencia}</td>
                  <td className="px-3 py-2">{factura.numero_documento}</td>
                  <td className="px-3 py-2">{formatearFechaDeNegocio(factura.fecha)}</td>
                  <td className="px-3 py-2">{factura.monto} {factura.moneda}</td>
                  <td className="px-3 py-2">{factura.hito}</td>
                  <td className="px-3 py-2">{factura.recepcion}</td>
                  <td className="px-3 py-2">{factura.supervisor}</td>
                  <td className="px-3 py-2">{factura.estado}</td>
                  <td className="px-3 py-2">
                    {factura.estado === "CONFORME" && puedeEjecutar ? (
                      <Button
                        type="button"
                        onClick={() =>
                          setAnulando({
                            ruta: `/facturas/${factura.id}/anular`,
                            titulo: "Anular factura",
                          })
                        }
                      >
                        Anular
                      </Button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {anulando ? (
        <div className="mt-4 grid grid-cols-1 gap-4 rounded-md border border-border-subtle p-4 sm:grid-cols-2">
          <FormField label="Motivo de la anulación" htmlFor="factura-motivo" required>
            <input
              id="factura-motivo"
              className={inputClase}
              maxLength={500}
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
            />
          </FormField>
          <div className="flex items-end">
            <Button
              type="button"
              disabled={!motivo}
              onClick={() =>
                confirmar({
                  titulo: anulando.titulo,
                  descripcion: "Se anulará la factura seleccionada.",
                  ejecutar: () => enviar(anulando.ruta, { motivo }, "Anulación registrada."),
                })
              }
            >
              Confirmar anulación
            </Button>
          </div>
        </div>
      ) : null}

      {ejecucion.acciones.registrar_hechos && ejecucion.soy_supervisor ? (
        <div className="mt-6 grid grid-cols-1 gap-4 rounded-md border border-border-subtle p-4 sm:grid-cols-2">
          <h3 className="text-base font-semibold text-text-900 sm:col-span-2">Vincular factura</h3>
          <FormField label="N.º de factura o cuenta" htmlFor="factura-numero" required>
            <input
              id="factura-numero"
              className={inputClase}
              maxLength={40}
              value={numero}
              onChange={(e) => setNumero(e.target.value)}
            />
          </FormField>
          <FormField label="Fecha" htmlFor="factura-fecha" required>
            <input
              id="factura-fecha"
              type="date"
              className={inputClase}
              value={fecha}
              onChange={(e) => setFecha(e.target.value)}
            />
          </FormField>
          <FormField label="Monto" htmlFor="factura-monto" required>
            <input
              id="factura-monto"
              className={inputClase}
              inputMode="decimal"
              value={monto}
              onChange={(e) => setMonto(e.target.value)}
            />
          </FormField>
          <FormField label="Hito" htmlFor="factura-hito" required>
            <select
              id="factura-hito"
              className={inputClase}
              value={hitoId}
              onChange={(e) => {
                setHitoId(e.target.value);
                setRecepcionId("");
              }}
            >
              <option value="">Elija un hito</option>
              {hitosVigentes.map((hito) => (
                <option key={hito.id} value={hito.id}>
                  {hito.referencia} · {hito.descripcion}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Recepción conforme" htmlFor="factura-recepcion" required>
            <select
              id="factura-recepcion"
              className={inputClase}
              value={recepcionId}
              onChange={(e) => setRecepcionId(e.target.value)}
            >
              <option value="">Elija una recepción</option>
              {recepcionesConformes.map((recepcion) => (
                <option key={recepcion.id} value={recepcion.id}>
                  {recepcion.referencia} · {recepcion.tipo_etiqueta}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Fecha de conformidad" htmlFor="factura-conformidad" required>
            <input
              id="factura-conformidad"
              type="date"
              className={inputClase}
              value={fechaConformidad}
              onChange={(e) => setFechaConformidad(e.target.value)}
            />
          </FormField>
          <SelectorDocumento
            id="factura-soporte"
            etiqueta="Soporte"
            valor={documentoId}
            onChange={setDocumentoId}
            documentos={opciones?.documentos ?? []}
          />
          <div className="flex items-end sm:col-span-2">
            <Button
              type="button"
              disabled={!numero || !fecha || !monto || !hitoId || !recepcionId || !documentoId || !fechaConformidad}
              onClick={() =>
                confirmar({
                  titulo: "Vincular factura",
                  descripcion: "Se vinculará la factura al contrato.",
                  ejecutar: () =>
                    enviar(
                      "/facturas",
                      {
                        numero_documento: numero,
                        fecha,
                        monto,
                        hito_id: hitoId,
                        recepcion_id: recepcionId,
                        documento_id: documentoId,
                        fecha_conformidad: fechaConformidad,
                      },
                      "Factura vinculada.",
                    ),
                })
              }
            >
              Vincular factura
            </Button>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function SeccionCronologia({ ejecucion }: { ejecucion: EjecucionContrato }) {
  return (
    <section aria-labelledby="cronologia" className="mb-10">
      <h2 id="cronologia" className="mb-4 text-xl font-semibold text-text-900">
        Cronología
      </h2>
      {ejecucion.cronologia.length === 0 ? (
        <EmptyState title="Sin hechos registrados" description="Aún no hay hechos en la ejecución." />
      ) : (
        <div role="region" aria-label="Tabla de cronología" tabIndex={0} className="relative overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <caption className="sr-only">Cronología de la ejecución</caption>
            <thead>
              <tr className="border-b border-border-subtle">
                <th scope="col" className="px-3 py-2">Fecha</th>
                <th scope="col" className="px-3 py-2">Hecho</th>
                <th scope="col" className="px-3 py-2">Referencia</th>
                <th scope="col" className="px-3 py-2">Monto</th>
                <th scope="col" className="px-3 py-2">Estado</th>
              </tr>
            </thead>
            <tbody>
              {ejecucion.cronologia.map((evento, index) => (
                <tr key={`${evento.fecha}-${evento.referencia}-${index}`} className="border-b border-border-subtle">
                  <td className="px-3 py-2">{formatearFechaDeNegocio(evento.fecha)}</td>
                  <td className="px-3 py-2 break-words">{evento.titulo}</td>
                  <td className="px-3 py-2">{evento.referencia}</td>
                  <td className="px-3 py-2">
                    {evento.monto ? `${evento.monto} ${evento.moneda ?? ""}` : "—"}
                  </td>
                  <td className="px-3 py-2">{evento.estado}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function SeccionCierre({
  ejecucion,
  opciones,
  puedeEjecutar,
  confirmar,
  enviar,
}: {
  ejecucion: EjecucionContrato;
  opciones: OpcionesEjecucion | undefined;
  puedeEjecutar: boolean;
  confirmar: (pendiente: Pendiente) => void;
  enviar: (ruta: string, cuerpo: Record<string, unknown>, mensaje: string) => Promise<void>;
}) {
  const [fecha, setFecha] = useState("");
  const [documentoId, setDocumentoId] = useState("");
  const [evaluacionDocumentoId, setEvaluacionDocumentoId] = useState("");
  const [observacion, setObservacion] = useState("");

  const tieneRecepcionDefinitiva = ejecucion.recepciones.some(
    (recepcion) => recepcion.tipo === "DEFINITIVA" && recepcion.estado === "CONFORME",
  );

  return (
    <section aria-labelledby="cierre" className="mb-10">
      <h2 id="cierre" className="mb-4 text-xl font-semibold text-text-900">
        Cierre operativo
      </h2>
      {ejecucion.cierre ? (
        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Dato etiqueta="Fecha">{formatearFechaDeNegocio(ejecucion.cierre.fecha)}</Dato>
          <Dato etiqueta="Aprobado por">
            {ejecucion.cierre.aprobador_tipo === "COMISION"
              ? "Comisión de Contrataciones"
              : "Unidad Contratante"}{" "}
            · {ejecucion.cierre.aprobador_nombre}
          </Dato>
          <Dato etiqueta="Acta de aprobación">{ejecucion.cierre.documento.titulo}</Dato>
          <Dato etiqueta="Evaluación de desempeño">{ejecucion.cierre.evaluacion.titulo}</Dato>
          <Dato etiqueta="Supervisor">{ejecucion.cierre.supervisor}</Dato>
          <Dato etiqueta="Observación">{ejecucion.cierre.observacion ?? "—"}</Dato>
        </dl>
      ) : ejecucion.acciones.cerrar && puedeEjecutar ? (
        <>
          {!tieneRecepcionDefinitiva ? (
            <p className="mb-4 text-sm text-text-600">
              El cierre requiere la recepción definitiva.
            </p>
          ) : (
            <div className="grid grid-cols-1 gap-4 rounded-md border border-border-subtle p-4 sm:grid-cols-2">
              <h3 className="text-base font-semibold text-text-900 sm:col-span-2">
                Cerrar la ejecución
              </h3>
              <FormField label="Fecha" htmlFor="cierre-fecha" required>
                <input
                  id="cierre-fecha"
                  type="date"
                  className={inputClase}
                  value={fecha}
                  onChange={(e) => setFecha(e.target.value)}
                />
              </FormField>
              <SelectorDocumento
                id="cierre-documento"
                etiqueta="Acta de aprobación del cierre"
                valor={documentoId}
                onChange={setDocumentoId}
                documentos={opciones?.documentos ?? []}
              />
              <SelectorDocumento
                id="cierre-evaluacion"
                etiqueta="Evaluación de desempeño"
                valor={evaluacionDocumentoId}
                onChange={setEvaluacionDocumentoId}
                documentos={opciones?.documentos ?? []}
              />
              <div className="sm:col-span-2">
                <FormField label="Observación" htmlFor="cierre-observacion">
                  <textarea
                    id="cierre-observacion"
                    className={inputClase}
                    value={observacion}
                    onChange={(e) => setObservacion(e.target.value)}
                  />
                </FormField>
              </div>
              <div className="flex items-end sm:col-span-2">
                <Button
                  type="button"
                  disabled={!fecha || !documentoId || !evaluacionDocumentoId}
                  onClick={() =>
                    confirmar({
                      titulo: "Cerrar la ejecución del contrato",
                      descripcion: "Se cerrará la ejecución del contrato.",
                      ejecutar: () =>
                        enviar(
                          "/cierre",
                          {
                            fecha,
                            documento_id: documentoId,
                            evaluacion_documento_id: evaluacionDocumentoId,
                            observacion: observacion || null,
                          },
                          "Ejecución cerrada.",
                        ),
                    })
                  }
                >
                  Cerrar ejecución
                </Button>
              </div>
            </div>
          )}
        </>
      ) : null}
    </section>
  );
}

export function EjecucionContratoPage() {
  const { contratoId } = useParams<{ contratoId: string }>();
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const queryClient = useQueryClient();

  const puedeVer = tiene("gobierno_contratos:view", "empresa");
  const puedeEjecutar = tiene("gobierno_contratos:execute", "empresa");

  const clave = [...CONSULTA_CONTRATOS, activeCompanyId, "ejecucion", contratoId] as const;

  const ejecucionQuery = useQuery({
    queryKey: clave,
    queryFn: () => apiFetch<EjecucionContrato>(`/gobierno/contratos/${contratoId}/ejecucion`),
    enabled: Boolean(puedeVer && contratoId),
  });

  const opcionesQuery = useQuery({
    queryKey: [...clave, "opciones"],
    queryFn: () => apiFetch<OpcionesEjecucion>(`/gobierno/contratos/${contratoId}/ejecucion/opciones`),
    enabled: Boolean(puedeVer && puedeEjecutar && contratoId),
  });

  const [pendiente, setPendiente] = useState<Pendiente | null>(null);
  const [exito, setExito] = useState("");
  const [error, setError] = useState("");

  if (!puedeVer) {
    return (
      <PageContent>
        <EmptyState title="Sin acceso" description="No tiene permisos para ver la ejecución del contrato." />
      </PageContent>
    );
  }

  if (ejecucionQuery.isLoading) {
    return (
      <PageContent>
        <PageHeader
          crumbs={[
            { label: "Gobierno" },
            { label: "Contratos y órdenes", to: "/gobierno/contratos" },
            { label: "Contrato" },
          ]}
          title="Ejecución del contrato"
        />
        <LoadingState />
      </PageContent>
    );
  }

  if (ejecucionQuery.isError || !ejecucionQuery.data) {
    return (
      <PageContent>
        <PageHeader
          crumbs={[
            { label: "Gobierno" },
            { label: "Contratos y órdenes", to: "/gobierno/contratos" },
            { label: "Contrato" },
          ]}
          title="Ejecución del contrato"
        />
        <EmptyState title="Ejecución no disponible" description="No se pudo cargar la ejecución del contrato." />
      </PageContent>
    );
  }

  const ejecucion = ejecucionQuery.data;
  const opciones = opcionesQuery.data;
  const codigo = ejecucion.contrato.codigo ?? "Contrato";

  const confirmar = (nuevoPendiente: Pendiente) => {
    setPendiente(nuevoPendiente);
  };

  const enviar = async (ruta: string, cuerpo: Record<string, unknown>, mensaje: string) => {
    try {
      const respuesta = await apiFetch<EjecucionContrato>(
        `/gobierno/contratos/${contratoId}/ejecucion${ruta}`,
        { method: "POST", body: cuerpo },
      );
      queryClient.setQueryData(clave, respuesta);
      await queryClient.invalidateQueries({ queryKey: [...clave, "opciones"] });
      setExito(mensaje);
      setError("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo registrar.");
      setExito("");
      throw err;
    }
  };

  const handleConfirm = async () => {
    if (!pendiente) return;
    setPendiente(null);
    try {
      await pendiente.ejecutar();
    } catch {
      // el error ya se mostró en el estado global
    }
  };

  const handleCancel = () => {
    setPendiente(null);
  };

  const handleDescargar = async () => {
    try {
      await descargarArchivo(
        `/gobierno/contratos/${contratoId}/ejecucion/reporte.csv`,
        `ejecucion-${codigo}.csv`,
      );
      setExito("Descarga iniciada.");
      setError("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo descargar el reporte.");
      setExito("");
    }
  };

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno" },
          { label: "Contratos y órdenes", to: "/gobierno/contratos" },
          {
            label: codigo,
            to: `/gobierno/contratos/${ejecucion.contrato.id}`,
          },
        ]}
        title="Ejecución del contrato"
      />

      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <Button type="button" onClick={handleDescargar}>
          Descargar CSV
        </Button>
      </div>

      {exito ? (
        <p role="status" className="mb-4 rounded-md bg-green-50 p-3 text-sm text-green-800">
          {exito}
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-800">
          {error}
        </p>
      ) : null}

      {ejecucion.contrato.estado !== "FORMALIZADO" ? (
        <EmptyState
          title="Contrato no formalizado"
          description="La ejecución se registra sobre un contrato formalizado."
        />
      ) : (
        <>
          <SeccionResumen ejecucion={ejecucion} />
          <SeccionInicio
            ejecucion={ejecucion}
            opciones={opciones}
            puedeEjecutar={puedeEjecutar}
            confirmar={confirmar}
            enviar={enviar}
          />
          <SeccionHitos
            ejecucion={ejecucion}
            puedeEjecutar={puedeEjecutar}
            confirmar={confirmar}
            enviar={enviar}
          />
          <SeccionEntregables
            ejecucion={ejecucion}
            opciones={opciones}
            puedeEjecutar={puedeEjecutar}
            confirmar={confirmar}
            enviar={enviar}
          />
          <SeccionValuaciones
            ejecucion={ejecucion}
            opciones={opciones}
            puedeEjecutar={puedeEjecutar}
            confirmar={confirmar}
            enviar={enviar}
          />
          <SeccionRecepciones
            ejecucion={ejecucion}
            opciones={opciones}
            puedeEjecutar={puedeEjecutar}
            confirmar={confirmar}
            enviar={enviar}
          />
          <SeccionFacturas
            ejecucion={ejecucion}
            opciones={opciones}
            puedeEjecutar={puedeEjecutar}
            confirmar={confirmar}
            enviar={enviar}
          />
          <SeccionCronologia ejecucion={ejecucion} />
          <SeccionCierre
            ejecucion={ejecucion}
            opciones={opciones}
            puedeEjecutar={puedeEjecutar}
            confirmar={confirmar}
            enviar={enviar}
          />
        </>
      )}

      <ConfirmationDialog
        open={pendiente !== null}
        title={pendiente?.titulo ?? ""}
        description={pendiente?.descripcion ?? ""}
        confirmLabel="Confirmar"
        cancelLabel="Cancelar"
        onConfirm={handleConfirm}
        onCancel={handleCancel}
      />
    </PageContent>
  );
}
