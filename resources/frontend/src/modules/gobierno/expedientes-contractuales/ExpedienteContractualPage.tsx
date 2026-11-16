import { useState } from "react";
import { Link, useParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { descargarArchivo, mensajeDeDescarga } from "@/api/descargas";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { PageHeader } from "@/components/PageHeader";
import { PageContent } from "@/layout/PageContent";
import { ErrorDeCarga } from "@/modules/gobierno/ocupacion/ErrorDeCarga";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_EXPEDIENTES,
  ETIQUETAS_ESTADO_DOCUMENTO,
  ETIQUETAS_INTEGRIDAD,
  ETIQUETAS_MOTIVO,
  ETIQUETAS_VERIFICACION,
  abreviarHuella,
  rutaExpediente,
  type AuditoriaExpediente,
  type Cronologia,
  type Expediente,
  type Integridad,
  type PaquetesExpediente,
  type ResultadoIntegridad,
  type VerificacionPaqueteExpediente,
} from "./api";

const SECCIONES = [
  { id: "resumen", titulo: "Resumen" },
  { id: "origen", titulo: "Origen de contratación" },
  { id: "adjudicacion", titulo: "Adjudicación" },
  { id: "presupuesto", titulo: "Presupuesto" },
  { id: "instrumento", titulo: "Instrumento contractual" },
  { id: "garantias", titulo: "Garantías" },
  { id: "modificaciones", titulo: "Modificaciones" },
  { id: "supervision", titulo: "Supervisión" },
  { id: "ejecucion", titulo: "Ejecución" },
  { id: "actos", titulo: "Actos y documentos" },
  { id: "cronologia", titulo: "Cronología" },
  { id: "auditoria", titulo: "Auditoría" },
  { id: "integridad", titulo: "Integridad" },
  { id: "exportaciones", titulo: "Exportaciones" },
] as const;

export function ExpedienteContractualPage() {
  const { contratoId } = useParams<{ contratoId: string }>();
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();

  const consulta = useQuery({
    queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId, "expediente", contratoId],
    queryFn: () => apiFetch<Expediente>(rutaExpediente(contratoId ?? "")),
    enabled: Boolean(contratoId) && tiene("gobierno_contratos:view", "empresa"),
  });

  if (!contratoId || !tiene("gobierno_contratos:view", "empresa")) {
    return (
      <PageContent>
        <PageHeader crumbs={[{ label: "Gobierno" }, { label: "Expedientes contractuales", to: "/gobierno/expedientes-contractuales" }]} title="Expediente contractual" />
        <EmptyState title="Sin acceso" description="No tiene permiso para consultar este expediente contractual." />
      </PageContent>
    );
  }

  if (consulta.isLoading) {
    return (
      <PageContent>
        <PageHeader
          crumbs={[{ label: "Gobierno" }, { label: "Expedientes contractuales", to: "/gobierno/expedientes-contractuales" }]}
          title="Expediente contractual"
        />
        <LoadingState />
      </PageContent>
    );
  }

  if (consulta.isError) {
    if (consulta.error instanceof ApiError && consulta.error.status === 409) {
      return (
        <PageContent>
          <PageHeader
            crumbs={[{ label: "Gobierno" }, { label: "Expedientes contractuales", to: "/gobierno/expedientes-contractuales" }]}
            title="Expediente contractual"
          />
          <EmptyState
            title="Expediente no disponible"
            description="El expediente contractual existe solo para contratos formalizados."
          />
        </PageContent>
      );
    }
    if (consulta.error instanceof ApiError && consulta.error.status === 404) {
      return (
        <PageContent>
          <PageHeader
            crumbs={[{ label: "Gobierno" }, { label: "Expedientes contractuales", to: "/gobierno/expedientes-contractuales" }]}
            title="Expediente contractual"
          />
          <EmptyState title="Contrato no encontrado" description="El contrato solicitado no existe o no está disponible." />
        </PageContent>
      );
    }
    return (
      <PageContent>
        <PageHeader
          crumbs={[{ label: "Gobierno" }, { label: "Expedientes contractuales", to: "/gobierno/expedientes-contractuales" }]}
          title="Expediente contractual"
        />
        <ErrorDeCarga
          message={consulta.error instanceof Error ? consulta.error.message : "No se pudo cargar el expediente contractual."}
          onRetry={() => void consulta.refetch()}
        />
      </PageContent>
    );
  }

  if (!consulta.data) return null;
  const expediente = consulta.data;

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno" },
          { label: "Expedientes contractuales", to: "/gobierno/expedientes-contractuales" },
          { label: expediente.resumen.codigo },
        ]}
        title={`Expediente contractual · ${expediente.resumen.codigo}`}
      />
      <p className="mb-4 text-sm text-text-600">Solo lectura: cada acción se hace en su pantalla dueña.</p>

      <nav aria-label="Secciones del expediente" className="mb-6 flex flex-wrap gap-2 rounded-md border border-border-subtle bg-white p-3">
        {SECCIONES.map((seccion) => (
          <a key={seccion.id} href={`#${seccion.id}`} className="text-sm text-brand-700 underline">
            {seccion.titulo}
          </a>
        ))}
      </nav>

      <Resumen expediente={expediente} />
      <Origen expediente={expediente} />
      <Adjudicacion expediente={expediente} />
      <Presupuesto expediente={expediente} />
      <Instrumento expediente={expediente} />
      <Garantias expediente={expediente} />
      <Modificaciones expediente={expediente} />
      <Supervision contratoId={contratoId} expediente={expediente} />
      <Ejecucion expediente={expediente} />
      <ActosYDocumentos expediente={expediente} />
      <Cronologia contratoId={contratoId} />
      <Auditoria contratoId={contratoId} expediente={expediente} />
      <Integridad contratoId={contratoId} />
      <Exportaciones contratoId={contratoId} expediente={expediente} queryClient={queryClient} notify={notify} />
    </PageContent>
  );
}

function Resumen({ expediente }: { expediente: Expediente }) {
  const r = expediente.resumen;
  return (
    <section aria-labelledby="resumen-titulo" id="resumen" className="mb-6">
      <h2 id="resumen-titulo" className="text-lg font-semibold text-text-900">Resumen</h2>
      <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-3">
        <div>
          <dt className="font-medium text-text-600">Contratista</dt>
          <dd className="text-text-900">{r.contratista.nombre}</dd>
        </div>
        <div>
          <dt className="font-medium text-text-600">Objeto</dt>
          <dd className="text-text-900">{r.objeto}</dd>
        </div>
        <div>
          <dt className="font-medium text-text-600">Monto original</dt>
          <dd className="text-text-900">{r.monto_original} {r.moneda}</dd>
        </div>
        <div>
          <dt className="font-medium text-text-600">Monto vigente</dt>
          <dd className="text-text-900">{r.monto_vigente} {r.moneda}</dd>
        </div>
        <div>
          <dt className="font-medium text-text-600">Plazo original</dt>
          <dd className="text-text-900">{formatearFechaDeNegocio(r.fecha_inicio)} al {formatearFechaDeNegocio(r.fecha_fin_original)}</dd>
        </div>
        <div>
          <dt className="font-medium text-text-600">Plazo vigente</dt>
          <dd className="text-text-900">{formatearFechaDeNegocio(r.fecha_inicio)} al {formatearFechaDeNegocio(r.fecha_fin_vigente)}</dd>
        </div>
        <div>
          <dt className="font-medium text-text-600">Vigencia</dt>
          <dd className="text-text-900">{r.vigencia_etiqueta}</dd>
        </div>
        <div>
          <dt className="font-medium text-text-600">Adjudicación</dt>
          <dd className="text-text-900">{r.adjudicacion_referencia}</dd>
        </div>
        <div>
          <dt className="font-medium text-text-600">Expediente</dt>
          <dd className="text-text-900">{r.expediente_numero}</dd>
        </div>
        <div>
          <dt className="font-medium text-text-600">Supervisor actual</dt>
          <dd className="text-text-900">
            {r.supervisor_actual ? `${r.supervisor_actual.nombre} · ${r.supervisor_actual.cargo}` : "—"}
          </dd>
        </div>
        <div>
          <dt className="font-medium text-text-600">Cobertura</dt>
          <dd className="text-text-900">
            {r.cobertura.total_asignado} {r.cobertura.moneda} · {r.cobertura.completa ? "Completa" : "Incompleta"}
          </dd>
        </div>
        <div>
          <dt className="font-medium text-text-600">Ejecución</dt>
          <dd className="text-text-900">{r.ejecucion.mensaje}</dd>
        </div>
      </dl>
    </section>
  );
}

function Origen({ expediente }: { expediente: Expediente }) {
  const o = expediente.origen;
  return (
    <section aria-labelledby="origen-titulo" id="origen" className="mb-6">
      <h2 id="origen-titulo" className="text-lg font-semibold text-text-900">Origen de contratación</h2>
      <div className="mt-3 grid gap-4 sm:grid-cols-2">
        <div className="rounded-md border border-border-subtle p-3">
          <h3 className="text-sm font-semibold text-text-900">Expediente de contratación</h3>
          <dl className="mt-2 grid gap-1 text-sm">
            <div><dt className="inline font-medium text-text-600">Número: </dt><dd className="inline text-text-900">{o.expediente.numero}</dd></div>
            <div><dt className="inline font-medium text-text-600">Objeto: </dt><dd className="inline text-text-900">{o.expediente.objeto}</dd></div>
            <div><dt className="inline font-medium text-text-600">Tipo: </dt><dd className="inline text-text-900">{o.expediente.tipo_contratacion}</dd></div>
            <div><dt className="inline font-medium text-text-600">Modalidad: </dt><dd className="inline text-text-900">{o.expediente.modalidad}</dd></div>
            <div><dt className="inline font-medium text-text-600">Unidad: </dt><dd className="inline text-text-900">{o.expediente.unidad}</dd></div>
            <div><dt className="inline font-medium text-text-600">Estado: </dt><dd className="inline text-text-900">{o.expediente.estado}</dd></div>
          </dl>
          <Link className="mt-2 inline-block text-sm text-brand-700 underline" to={o.expediente.enlace}>
            Abrir expediente de contratación
          </Link>
        </div>
        <div className="rounded-md border border-border-subtle p-3">
          <h3 className="text-sm font-semibold text-text-900">Oferta adjudicada</h3>
          <dl className="mt-2 grid gap-1 text-sm">
            <div><dt className="inline font-medium text-text-600">Referencia: </dt><dd className="inline text-text-900">{o.oferta.referencia}</dd></div>
            <div><dt className="inline font-medium text-text-600">Oferente: </dt><dd className="inline text-text-900">{o.oferta.oferente}</dd></div>
            <div><dt className="inline font-medium text-text-600">Documento: </dt><dd className="inline text-text-900">{o.oferta.documento}</dd></div>
            <div><dt className="inline font-medium text-text-600">Recibida: </dt><dd className="inline text-text-900">{formatearFechaDeNegocio(o.oferta.recibida_en)}</dd></div>
          </dl>
        </div>
      </div>
    </section>
  );
}

function Adjudicacion({ expediente }: { expediente: Expediente }) {
  const a = expediente.adjudicacion;
  return (
    <section aria-labelledby="adjudicacion-titulo" id="adjudicacion" className="mb-6">
      <h2 id="adjudicacion-titulo" className="text-lg font-semibold text-text-900">Adjudicación</h2>
      <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
        <div><dt className="font-medium text-text-600">Referencia</dt><dd className="text-text-900">{a.referencia}</dd></div>
        <div><dt className="font-medium text-text-600">Fecha</dt><dd className="text-text-900">{formatearFechaDeNegocio(a.fecha)}</dd></div>
        <div><dt className="font-medium text-text-600">Resultado</dt><dd className="text-text-900">{a.resultado}</dd></div>
        <div><dt className="font-medium text-text-600">Vigente</dt><dd className="text-text-900">{a.vigente ? "Sí" : "No"}</dd></div>
        <div className="sm:col-span-2"><dt className="font-medium text-text-600">Motivación</dt><dd className="text-text-900">{a.motivacion}</dd></div>
        <div><dt className="font-medium text-text-600">Acto</dt><dd className="text-text-900"><Link className="text-brand-700 underline" to={a.acto.enlace}>{a.acto.etiqueta}</Link></dd></div>
        <div><dt className="font-medium text-text-600">Cargo</dt><dd className="text-text-900">{a.cargo ?? "—"}</dd></div>
      </dl>
    </section>
  );
}

function Presupuesto({ expediente }: { expediente: Expediente }) {
  const p = expediente.presupuesto;
  return (
    <section aria-labelledby="presupuesto-titulo" id="presupuesto" className="mb-6">
      <h2 id="presupuesto-titulo" className="text-lg font-semibold text-text-900">Presupuesto</h2>
      <h3 className="mt-3 text-sm font-semibold text-text-900">Certificados</h3>
      <div role="region" aria-label="Certificados" tabIndex={0} className="mt-2 overflow-x-auto">
        <table className="w-full min-w-[700px] border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-border-subtle text-text-600">
              <th scope="col" className="py-2 pr-3 font-medium">Código</th>
              <th scope="col" className="py-2 pr-3 font-medium">Fecha</th>
              <th scope="col" className="py-2 pr-3 font-medium">Monto</th>
              <th scope="col" className="py-2 pr-3 font-medium">Asignado al contrato</th>
              <th scope="col" className="py-2 pr-3 font-medium">Asignado por modificaciones</th>
              <th scope="col" className="py-2 pr-3 font-medium">Estado</th>
              <th scope="col" className="py-2 pr-3 font-medium">Presupuesto</th>
            </tr>
          </thead>
          <tbody>
            {p.certificados.map((c) => (
              <tr key={c.id} className="border-b border-border-subtle">
                <td className="py-2 pr-3 text-text-900">{c.codigo}</td>
                <td className="py-2 pr-3 text-text-900">{formatearFechaDeNegocio(c.fecha)}</td>
                <td className="py-2 pr-3 text-text-900">{c.monto} {c.moneda}</td>
                <td className="py-2 pr-3 text-text-900">{c.asignado_contrato}</td>
                <td className="py-2 pr-3 text-text-900">{c.asignado_modificaciones}</td>
                <td className="py-2 pr-3 text-text-900">{c.estado}</td>
                <td className="py-2 pr-3">
                  <Link className="text-brand-700 underline" to={c.enlace}>Ver en Presupuesto</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h3 className="mt-4 text-sm font-semibold text-text-900">Compromisos</h3>
      <div role="region" aria-label="Compromisos" tabIndex={0} className="mt-2 overflow-x-auto">
        <table className="w-full min-w-[700px] border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-border-subtle text-text-600">
              <th scope="col" className="py-2 pr-3 font-medium">Código</th>
              <th scope="col" className="py-2 pr-3 font-medium">Fecha</th>
              <th scope="col" className="py-2 pr-3 font-medium">Total</th>
              <th scope="col" className="py-2 pr-3 font-medium">Líneas</th>
              <th scope="col" className="py-2 pr-3 font-medium">Estado</th>
              <th scope="col" className="py-2 pr-3 font-medium">Presupuesto</th>
            </tr>
          </thead>
          <tbody>
            {p.compromisos.map((c) => (
              <tr key={c.id} className="border-b border-border-subtle">
                <td className="py-2 pr-3 text-text-900">{c.codigo}</td>
                <td className="py-2 pr-3 text-text-900">{formatearFechaDeNegocio(c.fecha)}</td>
                <td className="py-2 pr-3 text-text-900">{c.total} {c.moneda}</td>
                <td className="py-2 pr-3 text-text-900">
                  {c.lineas.map((linea, i) => (
                    <span key={i} className="block">{linea.certificado_codigo} · {linea.monto}</span>
                  ))}
                </td>
                <td className="py-2 pr-3 text-text-900">{c.estado}</td>
                <td className="py-2 pr-3">
                  <Link className="text-brand-700 underline" to={c.enlace}>Ver en Presupuesto</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-sm text-text-900">{String(p.control.mensaje ?? p.control)}</p>
      <p className="mt-2 text-sm text-text-600">{p.efectos}</p>
    </section>
  );
}

function Instrumento({ expediente }: { expediente: Expediente }) {
  const original = expediente.instrumento.original;
  const vigente = expediente.instrumento.vigente as {
    monto?: string;
    fecha_fin?: string;
    modificacion_codigo?: string;
  };
  return (
    <section aria-labelledby="instrumento-titulo" id="instrumento" className="mb-6">
      <h2 id="instrumento-titulo" className="text-lg font-semibold text-text-900">Instrumento contractual</h2>
      <div className="mt-3 grid gap-4 md:grid-cols-2">
        <div className="rounded-md border border-border-subtle p-3">
          <h3 className="text-sm font-semibold text-text-900">Condiciones originales</h3>
          <dl className="mt-2 grid gap-1 text-sm">
            <div><dt className="font-medium text-text-600">Monto</dt><dd className="text-text-900">{original.monto} {original.moneda}</dd></div>
            <div><dt className="font-medium text-text-600">Plazo</dt><dd className="text-text-900">{formatearFechaDeNegocio(original.fecha_inicio)} al {formatearFechaDeNegocio(original.fecha_fin)}</dd></div>
            <div><dt className="font-medium text-text-600">Referencia</dt><dd className="text-text-900">{original.referencia_instrumento}</dd></div>
            <div><dt className="font-medium text-text-600">Formalización</dt><dd className="text-text-900">{formatearFechaDeNegocio(original.fecha_formalizacion)}</dd></div>
            <div><dt className="font-medium text-text-600">Firmante</dt><dd className="text-text-900">{original.firmante.cargo} · {original.firmante.funcionario}</dd></div>
            <div>
              <dt className="font-medium text-text-600">Documento</dt>
              <dd className="text-text-900">
                {original.documento
                  ? `${original.documento.titulo} · v${original.documento.version} · ${abreviarHuella(original.documento.sha256)}`
                  : "—"}
              </dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Huella del contrato</dt>
              <dd className="break-words text-text-900" title={original.huella}>{abreviarHuella(original.huella)}</dd>
            </div>
          </dl>
        </div>
        <div className="rounded-md border border-border-subtle p-3">
          <h3 className="text-sm font-semibold text-text-900">Condiciones vigentes al {formatearFechaDeNegocio(expediente.instrumento.fecha_consulta)}</h3>
          <dl className="mt-2 grid gap-1 text-sm">
            <div><dt className="font-medium text-text-600">Monto vigente</dt><dd className="text-text-900">{vigente.monto ?? "—"} {original.moneda}</dd></div>
            <div><dt className="font-medium text-text-600">Fin del plazo vigente</dt><dd className="text-text-900">{vigente.fecha_fin ? formatearFechaDeNegocio(vigente.fecha_fin) : "—"}</dd></div>
            <div><dt className="font-medium text-text-600">Según</dt><dd className="text-text-900">{vigente.modificacion_codigo ?? "Contrato original"}</dd></div>
          </dl>
        </div>
      </div>
    </section>
  );
}

function Garantias({ expediente }: { expediente: Expediente }) {
  const garantias = expediente.garantias;
  return (
    <section aria-labelledby="garantias-titulo" id="garantias" className="mb-6">
      <h2 id="garantias-titulo" className="text-lg font-semibold text-text-900">Garantías</h2>
      {garantias.length === 0 ? (
        <p className="mt-3 text-sm text-text-600">Sin garantías vinculadas al contrato.</p>
      ) : (
        <div role="region" aria-label="Garantías" tabIndex={0} className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[800px] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-border-subtle text-text-600">
                <th scope="col" className="py-2 pr-3 font-medium">Referencia</th>
                <th scope="col" className="py-2 pr-3 font-medium">Tipo</th>
                <th scope="col" className="py-2 pr-3 font-medium">Emisor</th>
                <th scope="col" className="py-2 pr-3 font-medium">Monto</th>
                <th scope="col" className="py-2 pr-3 font-medium">Vigencia</th>
                <th scope="col" className="py-2 pr-3 font-medium">Estado</th>
                <th scope="col" className="py-2 pr-3 font-medium">Eventos</th>
              </tr>
            </thead>
            <tbody>
              {garantias.map((g) => (
                <tr key={g.instrumento_id} className="border-b border-border-subtle">
                  <td className="py-2 pr-3 text-text-900">{g.referencia}</td>
                  <td className="py-2 pr-3 text-text-900">{g.tipo_etiqueta}</td>
                  <td className="py-2 pr-3 text-text-900">{g.emisor}</td>
                  <td className="py-2 pr-3 text-text-900">{g.monto} {g.moneda}</td>
                  <td className="py-2 pr-3 text-text-900">{formatearFechaDeNegocio(g.vigente_desde)}–{formatearFechaDeNegocio(g.vigente_hasta)}</td>
                  <td className="py-2 pr-3 text-text-900">{g.estado_etiqueta}</td>
                  <td className="py-2 pr-3 text-text-900">
                    {g.eventos.map((e, i) => (
                      <span key={i} className="block">{e.accion_etiqueta} {formatearFechaDeNegocio(e.fecha)}</span>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function Modificaciones({ expediente }: { expediente: Expediente }) {
  const m = expediente.modificaciones;
  return (
    <section aria-labelledby="modificaciones-titulo" id="modificaciones" className="mb-6">
      <h2 id="modificaciones-titulo" className="text-lg font-semibold text-text-900">Modificaciones</h2>
      {m.cantidad === 0 ? (
        <p className="mt-3 text-sm text-text-600">Sin modificaciones formalizadas.</p>
      ) : (
        <ul className="mt-3 space-y-3">
          {m.historial.map((nodo, indice) => {
            const n = nodo as Record<string, unknown>;
            const enlace = String(n.enlace ?? "");
            return (
              <li key={indice} className="rounded-md border border-border-subtle p-3 text-sm">
                <h3 className="font-semibold text-text-900">
                  <Link className="text-brand-700 underline" to={enlace}>{String(n.tipo_etiqueta ?? "")} {String(n.codigo ?? "")}</Link>
                </h3>
                <dl className="mt-2 grid gap-1 sm:grid-cols-2">
                  <div><dt className="font-medium text-text-600">Fecha</dt><dd className="text-text-900">{formatearFechaDeNegocio(String(n.fecha_instrumento ?? ""))}</dd></div>
                  <div><dt className="font-medium text-text-600">Vigente desde</dt><dd className="text-text-900">{formatearFechaDeNegocio(String(n.vigente_desde ?? ""))}</dd></div>
                  <div className="sm:col-span-2"><dt className="font-medium text-text-600">Motivo</dt><dd className="text-text-900">{String(n.motivo ?? "")}</dd></div>
                  <div><dt className="font-medium text-text-600">Cambio de monto</dt><dd className="text-text-900">{(n.monto as Record<string, string>)?.anterior} → {(n.monto as Record<string, string>)?.nuevo}</dd></div>
                  <div><dt className="font-medium text-text-600">Cambio de plazo</dt><dd className="text-text-900">{String(n.plazo ?? "—")}</dd></div>
                  <div><dt className="font-medium text-text-600">Firmante</dt><dd className="text-text-900">{(n.firmante as Record<string, string>)?.cargo}</dd></div>
                  <div><dt className="font-medium text-text-600">Huella</dt><dd className="break-words text-text-900">{abreviarHuella(String(n.huella ?? ""))}</dd></div>
                </dl>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

function Supervision({ contratoId, expediente }: { contratoId: string; expediente: Expediente }) {
  const [fecha, setFecha] = useState("");
  const [consultaFecha, setConsultaFecha] = useState<{ fecha: string; supervisor: Record<string, string> | null } | null>(null);
  const [errorFecha, setErrorFecha] = useState<string | null>(null);

  const consultarSupervisor = async () => {
    if (!fecha) return;
    setErrorFecha(null);
    setConsultaFecha(null);
    try {
      const respuesta = await apiFetch<{ fecha: string; supervisor: Record<string, string> | null }>(
        `/gobierno/contratos/${contratoId}/supervision/en?fecha=${fecha}`,
      );
      setConsultaFecha(respuesta);
    } catch (err) {
      setErrorFecha(err instanceof ApiError ? err.message : "No se pudo consultar el supervisor.");
    }
  };

  const historia = Array.isArray(expediente.supervision.historia)
    ? (expediente.supervision.historia as Array<Record<string, unknown>>)
    : [];

  return (
    <section aria-labelledby="supervision-titulo" id="supervision" className="mb-6">
      <h2 id="supervision-titulo" className="text-lg font-semibold text-text-900">Supervisión</h2>
      <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
        <div>
          <dt className="font-medium text-text-600">Vigente</dt>
          <dd className="text-text-900">
            {expediente.supervision.vigente
              ? `${String((expediente.supervision.vigente as Record<string, string>).nombre ?? "")} · ${String((expediente.supervision.vigente as Record<string, string>).cargo ?? "")}`
              : "—"}
          </dd>
        </div>
        <div>
          <dt className="font-medium text-text-600">Programada</dt>
          <dd className="text-text-900">{String(expediente.supervision.programada ?? "—")}</dd>
        </div>
      </dl>
      {historia.length > 0 ? (
        <div role="region" aria-label="Historia de supervisión" tabIndex={0} className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[700px] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-border-subtle text-text-600">
                <th scope="col" className="py-2 pr-3 font-medium">Referencia</th>
                <th scope="col" className="py-2 pr-3 font-medium">Nombre</th>
                <th scope="col" className="py-2 pr-3 font-medium">Cargo</th>
                <th scope="col" className="py-2 pr-3 font-medium">Unidad</th>
                <th scope="col" className="py-2 pr-3 font-medium">Acto</th>
                <th scope="col" className="py-2 pr-3 font-medium">Desde–hasta</th>
                <th scope="col" className="py-2 pr-3 font-medium">Situación</th>
              </tr>
            </thead>
            <tbody>
              {historia.map((nodo, indice) => (
                <tr key={indice} className="border-b border-border-subtle">
                  <td className="py-2 pr-3 text-text-900">{String(nodo.referencia ?? "")}</td>
                  <td className="py-2 pr-3 text-text-900">{String(nodo.nombre ?? "")}</td>
                  <td className="py-2 pr-3 text-text-900">{String(nodo.cargo ?? "")}</td>
                  <td className="py-2 pr-3 text-text-900">{String(nodo.unidad ?? "")}</td>
                  <td className="py-2 pr-3 text-text-900">{String(nodo.acto ?? "")}</td>
                  <td className="py-2 pr-3 text-text-900">{String(nodo.desde ?? "")}–{String(nodo.hasta ?? "")}</td>
                  <td className="py-2 pr-3 text-text-900">{String(nodo.situacion ?? "")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="mt-3 text-sm text-text-600">Sin historia de supervisiones.</p>
      )}
      <div className="mt-4 flex flex-wrap items-end gap-2">
        <FormField label="Supervisor en una fecha" htmlFor="supervision-fecha">
          <input
            id="supervision-fecha"
            type="date"
            value={fecha}
            onChange={(e) => setFecha(e.target.value)}
            className="w-full rounded-md border border-border-subtle px-3 py-2 text-sm"
          />
        </FormField>
        <Button variant="primary" onClick={() => void consultarSupervisor()}>
          Consultar
        </Button>
      </div>
      {consultaFecha ? (
        <p className="mt-2 text-sm text-text-900">
          {formatearFechaDeNegocio(consultaFecha.fecha)}: {consultaFecha.supervisor ? `${consultaFecha.supervisor.nombre} · ${consultaFecha.supervisor.cargo}` : "Sin supervisor en esa fecha"}
        </p>
      ) : null}
      {errorFecha ? <p className="mt-2 text-sm text-red-700" role="alert">{errorFecha}</p> : null}
    </section>
  );
}

function Ejecucion({ expediente }: { expediente: Expediente }) {
  const { ejecucion } = expediente;

  return (
    <section aria-labelledby="ejecucion-titulo" id="ejecucion" className="mb-6">
      <h2 id="ejecucion-titulo" className="text-lg font-semibold text-text-900">Ejecución</h2>
      <p className="mt-2 text-sm text-text-900">Estado de la ejecución: {ejecucion.estado_etiqueta}</p>
      <Link
        to={ejecucion.enlace}
        className="mt-1 inline-block text-sm font-medium text-primary-600 hover:underline"
      >
        Abrir la ejecución del contrato
      </Link>

      <dl className="mt-3 grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-text-700">Valuado conformado</dt>
          <dd className="font-medium text-text-900">{ejecucion.resumen.valuado_conformado}</dd>
        </div>
        <div>
          <dt className="text-text-700">Valuado presentado</dt>
          <dd className="font-medium text-text-900">{ejecucion.resumen.valuado_presentado}</dd>
        </div>
        <div>
          <dt className="text-text-700">Saldo</dt>
          <dd className="font-medium text-text-900">{ejecucion.resumen.saldo}</dd>
        </div>
        <div>
          <dt className="text-text-700">Facturado</dt>
          <dd className="font-medium text-text-900">{ejecucion.resumen.facturado}</dd>
        </div>
        <div>
          <dt className="text-text-700">Hitos cumplidos</dt>
          <dd className="font-medium text-text-900">
            {ejecucion.resumen.hitos_cumplidos} de {ejecucion.resumen.hitos_total}
          </dd>
        </div>
        <div>
          <dt className="text-text-700">Entregables pendientes</dt>
          <dd className="font-medium text-text-900">{ejecucion.resumen.entregables_pendientes}</dd>
        </div>
        <div>
          <dt className="text-text-700">Inicio</dt>
          <dd className="font-medium text-text-900">
            {ejecucion.inicio ? formatearFechaDeNegocio(ejecucion.inicio.fecha) : "—"}
          </dd>
        </div>
        <div>
          <dt className="text-text-700">Terminación</dt>
          <dd className="font-medium text-text-900">
            {ejecucion.terminacion ? formatearFechaDeNegocio(ejecucion.terminacion.fecha) : "—"}
          </dd>
        </div>
        <div>
          <dt className="text-text-700">Cierre</dt>
          <dd className="font-medium text-text-900">
            {ejecucion.cierre ? formatearFechaDeNegocio(ejecucion.cierre.fecha) : "—"}
          </dd>
        </div>
      </dl>

      <h3 className="mt-4 font-semibold text-text-900">Hitos de ejecución</h3>
      {ejecucion.hitos.length === 0 ? (
        <p className="mt-1 text-sm text-text-900">Sin registros</p>
      ) : (
        <div role="region" aria-label="Hitos de ejecución" tabIndex={0} className="mt-2 overflow-x-auto">
          <table className="min-w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border-subtle text-left text-text-700">
                <th className="py-2 pr-4 font-medium">Referencia</th>
                <th className="py-2 pr-4 font-medium">Descripción</th>
                <th className="py-2 pr-4 font-medium">Fecha prevista</th>
                <th className="py-2 pr-4 font-medium">Monto previsto</th>
                <th className="py-2 pr-4 font-medium">Estado</th>
              </tr>
            </thead>
            <tbody>
              {ejecucion.hitos.map((hito) => (
                <tr key={hito.id} className="border-b border-border-subtle text-text-900">
                  <td className="py-2 pr-4">{hito.referencia}</td>
                  <td className="py-2 pr-4">{hito.descripcion}</td>
                  <td className="py-2 pr-4">{formatearFechaDeNegocio(hito.fecha_prevista)}</td>
                  <td className="py-2 pr-4">{hito.monto_previsto ?? "—"}</td>
                  <td className="py-2 pr-4">{hito.cumplido ? "Cumplido" : "Pendiente"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h3 className="mt-4 font-semibold text-text-900">Valuaciones</h3>
      {ejecucion.valuaciones.length === 0 ? (
        <p className="mt-1 text-sm text-text-900">Sin registros</p>
      ) : (
        <div role="region" aria-label="Valuaciones" tabIndex={0} className="mt-2 overflow-x-auto">
          <table className="min-w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border-subtle text-left text-text-700">
                <th className="py-2 pr-4 font-medium">Referencia</th>
                <th className="py-2 pr-4 font-medium">Hito</th>
                <th className="py-2 pr-4 font-medium">Período</th>
                <th className="py-2 pr-4 font-medium">Monto</th>
                <th className="py-2 pr-4 font-medium">Estado</th>
              </tr>
            </thead>
            <tbody>
              {ejecucion.valuaciones.map((valuacion) => (
                <tr key={valuacion.id} className="border-b border-border-subtle text-text-900">
                  <td className="py-2 pr-4">{valuacion.referencia}</td>
                  <td className="py-2 pr-4">{valuacion.hito}</td>
                  <td className="py-2 pr-4">
                    {formatearFechaDeNegocio(valuacion.periodo_desde)} – {formatearFechaDeNegocio(valuacion.periodo_hasta)}
                  </td>
                  <td className="py-2 pr-4">{valuacion.monto} {valuacion.moneda}</td>
                  <td className="py-2 pr-4">{valuacion.estado_etiqueta}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h3 className="mt-4 font-semibold text-text-900">Recepciones</h3>
      {ejecucion.recepciones.length === 0 ? (
        <p className="mt-1 text-sm text-text-900">Sin registros</p>
      ) : (
        <div role="region" aria-label="Recepciones" tabIndex={0} className="mt-2 overflow-x-auto">
          <table className="min-w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border-subtle text-left text-text-700">
                <th className="py-2 pr-4 font-medium">Referencia</th>
                <th className="py-2 pr-4 font-medium">Tipo</th>
                <th className="py-2 pr-4 font-medium">Fecha</th>
                <th className="py-2 pr-4 font-medium">Estado</th>
              </tr>
            </thead>
            <tbody>
              {ejecucion.recepciones.map((recepcion) => (
                <tr key={recepcion.id} className="border-b border-border-subtle text-text-900">
                  <td className="py-2 pr-4">{recepcion.referencia}</td>
                  <td className="py-2 pr-4">{recepcion.tipo_etiqueta}</td>
                  <td className="py-2 pr-4">{formatearFechaDeNegocio(recepcion.fecha)}</td>
                  <td className="py-2 pr-4">{recepcion.estado === "CONFORME" ? "Conforme" : "Anulada"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h3 className="mt-4 font-semibold text-text-900">Facturas</h3>
      {ejecucion.facturas.length === 0 ? (
        <p className="mt-1 text-sm text-text-900">Sin registros</p>
      ) : (
        <div role="region" aria-label="Facturas" tabIndex={0} className="mt-2 overflow-x-auto">
          <table className="min-w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border-subtle text-left text-text-700">
                <th className="py-2 pr-4 font-medium">Referencia</th>
                <th className="py-2 pr-4 font-medium">Número de documento</th>
                <th className="py-2 pr-4 font-medium">Fecha</th>
                <th className="py-2 pr-4 font-medium">Monto</th>
                <th className="py-2 pr-4 font-medium">Estado</th>
              </tr>
            </thead>
            <tbody>
              {ejecucion.facturas.map((factura) => (
                <tr key={factura.id} className="border-b border-border-subtle text-text-900">
                  <td className="py-2 pr-4">{factura.referencia}</td>
                  <td className="py-2 pr-4">{factura.numero_documento}</td>
                  <td className="py-2 pr-4">{formatearFechaDeNegocio(factura.fecha)}</td>
                  <td className="py-2 pr-4">{factura.monto} {factura.moneda}</td>
                  <td className="py-2 pr-4">{factura.estado === "CONFORME" ? "Conforme" : "Anulada"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h3 className="mt-4 font-semibold text-text-900">Otras fuentes del expediente</h3>
      <ul className="mt-3 space-y-3">
        {expediente.fuentes_futuras.map((fuente) => (
          <li key={fuente.proceso} className="rounded-md border border-border-subtle p-3 text-sm">
            <h4 className="font-semibold text-text-900">{fuente.proceso} · {fuente.titulo}</h4>
            <p className="mt-1 text-text-900">{fuente.mensaje}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

function ActosYDocumentos({ expediente }: { expediente: Expediente }) {
  const { notify } = useNotifications();

  async function descargarDocumento(ruta: string, titulo: string) {
    try {
      await descargarArchivo(ruta, titulo);
    } catch (error) {
      notify({ type: "error", title: "No fue posible descargar el documento", description: mensajeDeDescarga(error) });
    }
  }
  return (
    <section aria-labelledby="actos-titulo" id="actos" className="mb-6">
      <h2 id="actos-titulo" className="text-lg font-semibold text-text-900">Actos y documentos</h2>
      <h3 className="mt-3 text-sm font-semibold text-text-900">Actos administrativos</h3>
      <div role="region" aria-label="Actos administrativos" tabIndex={0} className="mt-2 overflow-x-auto">
        <table className="w-full min-w-[700px] border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-border-subtle text-text-600">
              <th scope="col" className="py-2 pr-3 font-medium">Acto</th>
              <th scope="col" className="py-2 pr-3 font-medium">Rol</th>
              <th scope="col" className="py-2 pr-3 font-medium">Fecha</th>
              <th scope="col" className="py-2 pr-3 font-medium">Estado</th>
              <th scope="col" className="py-2 pr-3 font-medium">Asunto</th>
            </tr>
          </thead>
          <tbody>
            {expediente.actos.map((acto) => (
              <tr key={acto.id} className="border-b border-border-subtle">
                <td className="py-2 pr-3"><Link className="text-brand-700 underline" to={acto.enlace}>{acto.etiqueta}</Link></td>
                <td className="py-2 pr-3 text-text-900">{acto.rol}</td>
                <td className="py-2 pr-3 text-text-900">{formatearFechaDeNegocio(acto.fecha)}</td>
                <td className="py-2 pr-3 text-text-900">{acto.estado}</td>
                <td className="py-2 pr-3 text-text-900">{acto.asunto}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h3 className="mt-4 text-sm font-semibold text-text-900">Índice documental</h3>
      <div role="region" aria-label="Índice documental" tabIndex={0} className="mt-2 overflow-x-auto">
        <table className="w-full min-w-[800px] border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-border-subtle text-text-600">
              <th scope="col" className="py-2 pr-3 font-medium">Tipo</th>
              <th scope="col" className="py-2 pr-3 font-medium">Título</th>
              <th scope="col" className="py-2 pr-3 font-medium">Proceso</th>
              <th scope="col" className="py-2 pr-3 font-medium">Referencia</th>
              <th scope="col" className="py-2 pr-3 font-medium">Versión</th>
              <th scope="col" className="py-2 pr-3 font-medium">Huella</th>
              <th scope="col" className="py-2 pr-3 font-medium">Fecha</th>
              <th scope="col" className="py-2 pr-3 font-medium">Estado</th>
              <th scope="col" className="py-2 pr-3 font-medium">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {expediente.documentos.map((doc) => (
              <tr key={doc.clave} className="border-b border-border-subtle">
                <td className="py-2 pr-3 text-text-900">{doc.tipo_etiqueta}</td>
                <td className="py-2 pr-3 text-text-900">{doc.titulo}</td>
                <td className="py-2 pr-3 text-text-900">{doc.proceso}</td>
                <td className="py-2 pr-3 text-text-900">{doc.referencia}</td>
                <td className="py-2 pr-3 text-text-900">{doc.version !== null ? `v${doc.version}` : "—"}</td>
                <td className="py-2 pr-3 text-text-900" title={doc.sha256 ?? undefined}>{doc.sha256 !== null ? abreviarHuella(doc.sha256) : "—"}</td>
                <td className="py-2 pr-3 text-text-900">{formatearFechaDeNegocio(doc.fecha)}</td>
                <td className="py-2 pr-3 text-text-900">{ETIQUETAS_ESTADO_DOCUMENTO[doc.estado]}</td>
                <td className="py-2 pr-3">
                  {doc.sellado ? (
                    <span className="text-text-500">Sellado · la autoridad documental no lo entrega (huella registrada)</span>
                  ) : (
                    <>
                      {doc.descarga ? (
                        <Button variant="secondary" onClick={() => void descargarDocumento(doc.descarga ?? "", doc.titulo)}>
                          Descargar
                        </Button>
                      ) : null}
                      {doc.enlace?.startsWith("/documentos/") ? (
                        <Link className="ml-2 text-brand-700 underline" to={doc.enlace}>Ver documento</Link>
                      ) : null}
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Cronologia({ contratoId }: { contratoId: string }) {
  const [proceso, setProceso] = useState("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [offset, setOffset] = useState(0);
  const { activeCompanyId } = useCompany();

  const params = new URLSearchParams();
  if (proceso) params.set("proceso", proceso);
  if (desde) params.set("desde", desde);
  if (hasta) params.set("hasta", hasta);
  params.set("limit", "50");
  params.set("offset", String(offset));

  const consulta = useQuery({
    queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId, "expediente", contratoId, "cronologia", params.toString()],
    queryFn: () => apiFetch<Cronologia>(`/gobierno/contratos/${contratoId}/expediente/cronologia?${params.toString()}`),
  });

  return (
    <section aria-labelledby="cronologia-titulo" id="cronologia" className="mb-6">
      <h2 id="cronologia-titulo" className="text-lg font-semibold text-text-900">Cronología</h2>
      <div className="mt-3 flex flex-wrap items-end gap-2">
        <FormField label="Proceso" htmlFor="cronologia-proceso">
          <select
            id="cronologia-proceso"
            value={proceso}
            onChange={(e) => { setProceso(e.target.value); setOffset(0); }}
            className="w-full rounded-md border border-border-subtle px-3 py-2 text-sm"
          >
            <option value="">Todos</option>
            {(consulta.data?.procesos ?? []).map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </FormField>
        <FormField label="Desde" htmlFor="cronologia-desde">
          <input id="cronologia-desde" type="date" value={desde} onChange={(e) => { setDesde(e.target.value); setOffset(0); }} className="w-full rounded-md border border-border-subtle px-3 py-2 text-sm" />
        </FormField>
        <FormField label="Hasta" htmlFor="cronologia-hasta">
          <input id="cronologia-hasta" type="date" value={hasta} onChange={(e) => { setHasta(e.target.value); setOffset(0); }} className="w-full rounded-md border border-border-subtle px-3 py-2 text-sm" />
        </FormField>
      </div>
      {consulta.isLoading ? <LoadingState /> : null}
      {consulta.data ? (
        <>
          <div role="region" aria-label="Cronología del expediente" tabIndex={0} className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[900px] border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-border-subtle text-text-600">
                  <th scope="col" className="py-2 pr-3 font-medium">Orden</th>
                  <th scope="col" className="py-2 pr-3 font-medium">Fecha</th>
                  <th scope="col" className="py-2 pr-3 font-medium">Tipo</th>
                  <th scope="col" className="py-2 pr-3 font-medium">Proceso</th>
                  <th scope="col" className="py-2 pr-3 font-medium">Título</th>
                  <th scope="col" className="py-2 pr-3 font-medium">Actor</th>
                  <th scope="col" className="py-2 pr-3 font-medium">Autoridad</th>
                  <th scope="col" className="py-2 pr-3 font-medium">Unidad</th>
                  <th scope="col" className="py-2 pr-3 font-medium">Estado</th>
                </tr>
              </thead>
              <tbody>
                {consulta.data.items.map((evento) => (
                  <tr key={`${evento.orden}-${evento.fuente_id}`} className="border-b border-border-subtle">
                    <td className="py-2 pr-3 text-text-900">{evento.orden}</td>
                    <td className="py-2 pr-3 text-text-900">
                      {formatearFechaDeNegocio(evento.fecha)}
                      <span className="block text-xs text-text-600">Registro: {formatearFechaDeNegocio(evento.fecha_registro)}</span>
                    </td>
                    <td className="py-2 pr-3 text-text-900">{evento.tipo_etiqueta}</td>
                    <td className="py-2 pr-3 text-text-900">{evento.proceso}</td>
                    <td className="py-2 pr-3 text-text-900">
                      {evento.enlace ? <Link className="text-brand-700 underline" to={evento.enlace}>{evento.titulo}</Link> : evento.titulo}
                    </td>
                    <td className="py-2 pr-3 text-text-900">{evento.actor}</td>
                    <td className="py-2 pr-3 text-text-900">{evento.autoridad}</td>
                    <td className="py-2 pr-3 text-text-900">{evento.unidad}</td>
                    <td className="py-2 pr-3 text-text-900">{evento.estado}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-2 flex items-center justify-between text-sm text-text-600">
            <span>Mostrando {consulta.data.total === 0 ? 0 : offset + 1}–{Math.min(offset + 50, consulta.data.total)} de {consulta.data.total}</span>
            <div className="flex gap-2">
              <Button variant="secondary" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 50))}>Anterior</Button>
              <Button variant="secondary" disabled={offset + 50 >= consulta.data.total} onClick={() => setOffset(offset + 50)}>Siguiente</Button>
            </div>
          </div>
        </>
      ) : null}
    </section>
  );
}

function Auditoria({ contratoId, expediente }: { contratoId: string; expediente: Expediente }) {
  const [offset, setOffset] = useState(0);
  const { activeCompanyId } = useCompany();

  const consulta = useQuery({
    queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId, "expediente", contratoId, "auditoria", offset],
    queryFn: () => apiFetch<AuditoriaExpediente>(`/gobierno/contratos/${contratoId}/expediente/auditoria?limit=50&offset=${offset}`),
    enabled: expediente.permisos.auditoria,
  });

  if (!expediente.permisos.auditoria) {
    return (
      <section aria-labelledby="auditoria-titulo" id="auditoria" className="mb-6">
        <h2 id="auditoria-titulo" className="text-lg font-semibold text-text-900">Auditoría</h2>
        <p className="mt-3 text-sm text-text-600">Necesita el permiso de auditoría institucional para ver estos eventos.</p>
      </section>
    );
  }

  return (
    <section aria-labelledby="auditoria-titulo" id="auditoria" className="mb-6">
      <h2 id="auditoria-titulo" className="text-lg font-semibold text-text-900">Auditoría</h2>
      {consulta.isLoading ? <LoadingState /> : null}
      {consulta.data ? (
        <>
          <div role="region" aria-label="Auditoría del expediente" tabIndex={0} className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[700px] border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-border-subtle text-text-600">
                  <th scope="col" className="py-2 pr-3 font-medium">Fecha</th>
                  <th scope="col" className="py-2 pr-3 font-medium">Acción</th>
                  <th scope="col" className="py-2 pr-3 font-medium">Proceso</th>
                  <th scope="col" className="py-2 pr-3 font-medium">Usuario</th>
                  <th scope="col" className="py-2 pr-3 font-medium">Evento</th>
                </tr>
              </thead>
              <tbody>
                {consulta.data.items.map((evento) => (
                  <tr key={evento.id} className="border-b border-border-subtle">
                    <td className="py-2 pr-3 text-text-900">{formatearFechaDeNegocio(evento.fecha)}</td>
                    <td className="py-2 pr-3 text-text-900">{evento.accion_etiqueta}</td>
                    <td className="py-2 pr-3 text-text-900">{evento.proceso_nombre}</td>
                    <td className="py-2 pr-3 text-text-900">{evento.usuario}</td>
                    <td className="py-2 pr-3"><Link className="text-brand-700 underline" to={evento.enlace}>Ver evento</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-2 flex items-center justify-between text-sm text-text-600">
            <span>Mostrando {consulta.data.total === 0 ? 0 : offset + 1}–{Math.min(offset + 50, consulta.data.total)} de {consulta.data.total}</span>
            <div className="flex gap-2">
              <Button variant="secondary" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 50))}>Anterior</Button>
              <Button variant="secondary" disabled={offset + 50 >= consulta.data.total} onClick={() => setOffset(offset + 50)}>Siguiente</Button>
            </div>
          </div>
        </>
      ) : null}
    </section>
  );
}

function Integridad({ contratoId }: { contratoId: string }) {
  const [resultado, setResultado] = useState<Integridad | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { activeCompanyId } = useCompany();

  async function comprobar() {
    if (!contratoId) return;
    setCargando(true);
    setError(null);
    try {
      const r = await apiFetch<Integridad>(`/gobierno/contratos/${contratoId}/expediente/integridad`);
      setResultado(r);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo comprobar la integridad.");
    } finally {
      setCargando(false);
    }
  }

  const orden: ResultadoIntegridad[] = ["VERIFIED", "MISSING", "MISMATCH", "NOT_APPLICABLE"];

  return (
    <section aria-labelledby="integridad-titulo" id="integridad" className="mb-6">
      <h2 id="integridad-titulo" className="text-lg font-semibold text-text-900">Integridad</h2>
      <p className="mt-3 text-sm text-text-600">Las huellas se comprueban contra los archivos almacenados al pulsar el botón.</p>
      <Button variant="primary" disabled={cargando || !activeCompanyId} onClick={() => void comprobar()}>
        {cargando ? "Comprobando…" : "Comprobar huellas"}
      </Button>
      {error ? <p className="mt-2 text-sm text-red-700" role="alert">{error}</p> : null}
      {resultado ? (
        <>
          <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-4">
            {orden.map((clave) => (
              <div key={clave} className="rounded-md border border-border-subtle p-3">
                <dt className="font-medium text-text-600">{ETIQUETAS_INTEGRIDAD[clave]}</dt>
                <dd className="text-lg font-semibold text-text-900">{resultado.resumen[clave]}</dd>
              </div>
            ))}
          </dl>
          <div role="region" aria-label="Integridad documental" tabIndex={0} className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[700px] border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-border-subtle text-text-600">
                  <th scope="col" className="py-2 pr-3 font-medium">Título</th>
                  <th scope="col" className="py-2 pr-3 font-medium">Tipo</th>
                  <th scope="col" className="py-2 pr-3 font-medium">Huella registrada</th>
                  <th scope="col" className="py-2 pr-3 font-medium">Resultado</th>
                  <th scope="col" className="py-2 pr-3 font-medium">Detalle</th>
                </tr>
              </thead>
              <tbody>
                {resultado.documentos.map((doc) => (
                  <tr key={doc.clave} className="border-b border-border-subtle">
                    <td className="py-2 pr-3 text-text-900">{doc.titulo}</td>
                    <td className="py-2 pr-3 text-text-900">{doc.tipo}</td>
                    <td className="py-2 pr-3 text-text-900" title={doc.sha256_registrado}>{abreviarHuella(doc.sha256_registrado)}</td>
                    <td className="py-2 pr-3 text-text-900">{ETIQUETAS_INTEGRIDAD[doc.resultado]}</td>
                    <td className="py-2 pr-3 text-text-900">{doc.detalle}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
    </section>
  );
}

function Exportaciones({
  contratoId,
  expediente,
  queryClient,
  notify,
}: {
  contratoId: string;
  expediente: Expediente;
  queryClient: ReturnType<typeof useQueryClient>;
  notify: ReturnType<typeof useNotifications>["notify"];
}) {
  const [proposito, setProposito] = useState("");
  const [generando, setGenerando] = useState(false);
  const [errorGeneracion, setErrorGeneracion] = useState<string | null>(null);
  const [archivo, setArchivo] = useState<File | null>(null);
  const [verificando, setVerificando] = useState(false);
  const [errorVerificacion, setErrorVerificacion] = useState<string | null>(null);
  const [verificacion, setVerificacion] = useState<VerificacionPaqueteExpediente | null>(null);
  const { activeCompanyId } = useCompany();

  const paquetes = useQuery({
    queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId, "expediente", contratoId, "paquetes"],
    queryFn: () => apiFetch<PaquetesExpediente>(`/gobierno/contratos/${contratoId}/expediente/paquetes?limit=20&offset=0`),
    enabled: expediente.permisos.ver_paquetes,
  });

  async function generarPaquete() {
    if (!proposito) return;
    setGenerando(true);
    setErrorGeneracion(null);
    try {
      const paquete = await apiFetch<{ codigo: string }>(`/gobierno/contratos/${contratoId}/expediente/paquetes`, {
        method: "POST",
        body: { proposito },
        idempotencyKey: crypto.randomUUID(),
      });
      notify({ type: "success", title: `Paquete generado: ${paquete.codigo}` });
      setProposito("");
      void queryClient.invalidateQueries({ queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId, "expediente", contratoId, "paquetes"] });
    } catch (err) {
      setErrorGeneracion(err instanceof ApiError ? err.message : "No se pudo generar el paquete.");
    } finally {
      setGenerando(false);
    }
  }

  async function verificarPaquete() {
    if (!archivo) return;
    setVerificando(true);
    setErrorVerificacion(null);
    setVerificacion(null);
    const datos = new FormData();
    datos.append("archivo", archivo);
    try {
      const r = await apiFetch<VerificacionPaqueteExpediente>("/gobierno/expedientes-contractuales/paquetes/verificar", {
        method: "POST",
        body: datos,
      });
      setVerificacion(r);
      void queryClient.invalidateQueries({ queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId, "expediente", contratoId, "paquetes"] });
    } catch (err) {
      setErrorVerificacion(err instanceof ApiError ? err.message : "No se pudo verificar el paquete.");
    } finally {
      setVerificando(false);
    }
  }

  if (!expediente.permisos.generar_paquete && !expediente.permisos.ver_paquetes) {
    return (
      <section aria-labelledby="exportaciones-titulo" id="exportaciones" className="mb-6">
        <h2 id="exportaciones-titulo" className="text-lg font-semibold text-text-900">Exportaciones</h2>
        <p className="mt-3 text-sm text-text-600">No tiene permisos para generar ni consultar paquetes de este expediente.</p>
      </section>
    );
  }

  return (
    <section aria-labelledby="exportaciones-titulo" id="exportaciones" className="mb-6">
      <h2 id="exportaciones-titulo" className="text-lg font-semibold text-text-900">Exportaciones</h2>
      {expediente.permisos.generar_paquete ? (
        <div className="mt-3 rounded-md border border-border-subtle p-3">
          <h3 className="text-sm font-semibold text-text-900">Generar paquete</h3>
          <FormField label="Propósito del paquete" htmlFor="paquete-proposito">
            <textarea
              id="paquete-proposito"
              value={proposito}
              onChange={(e) => setProposito(e.target.value)}
              minLength={10}
              maxLength={1000}
              className="w-full rounded-md border border-border-subtle px-3 py-2 text-sm"
              rows={3}
            />
          </FormField>
          <AsyncButton
            variant="primary"
            disabled={generando || proposito.trim().length < 10 || proposito.length > 1000}
            onClick={generarPaquete}
          >
            {generando ? "Generando…" : "Generar paquete"}
          </AsyncButton>
          {errorGeneracion ? <p className="mt-2 text-sm text-red-700" role="alert">{errorGeneracion}</p> : null}
        </div>
      ) : null}
      {expediente.permisos.ver_paquetes ? (
        <>
          <div className="mt-4 rounded-md border border-border-subtle p-3">
            <h3 className="text-sm font-semibold text-text-900">Paquetes generados</h3>
            {paquetes.isLoading ? <LoadingState /> : null}
            {paquetes.data ? (
              <div role="region" aria-label="Paquetes del expediente" tabIndex={0} className="mt-2 overflow-x-auto">
                <table className="w-full min-w-[900px] border-collapse text-left text-sm">
                  <thead>
                    <tr className="border-b border-border-subtle text-text-600">
                      <th scope="col" className="py-2 pr-3 font-medium">Código</th>
                      <th scope="col" className="py-2 pr-3 font-medium">Generado</th>
                      <th scope="col" className="py-2 pr-3 font-medium">Por</th>
                      <th scope="col" className="py-2 pr-3 font-medium">Docs incl./excl.</th>
                      <th scope="col" className="py-2 pr-3 font-medium">Eventos</th>
                      <th scope="col" className="py-2 pr-3 font-medium">Huella</th>
                      <th scope="col" className="py-2 pr-3 font-medium">Última verificación</th>
                      <th scope="col" className="py-2 pr-3 font-medium">Descargar</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paquetes.data.items.map((paquete) => (
                      <tr key={paquete.id} className="border-b border-border-subtle">
                        <td className="py-2 pr-3 text-text-900">{paquete.codigo}</td>
                        <td className="py-2 pr-3 text-text-900">{formatearFechaDeNegocio(paquete.generado_en)}</td>
                        <td className="py-2 pr-3 text-text-900">{paquete.generado_por}</td>
                        <td className="py-2 pr-3 text-text-900">{paquete.documentos_incluidos}/{paquete.documentos_excluidos}</td>
                        <td className="py-2 pr-3 text-text-900">{paquete.eventos}</td>
                        <td className="py-2 pr-3 text-text-900" title={paquete.huella_paquete}>{abreviarHuella(paquete.huella_paquete)}</td>
                        <td className="py-2 pr-3 text-text-900">
                          {paquete.ultima_verificacion
                            ? `${ETIQUETAS_VERIFICACION[paquete.ultima_verificacion.resultado] ?? paquete.ultima_verificacion.resultado} · ${formatearFechaDeNegocio(paquete.ultima_verificacion.verificado_en)}`
                            : "—"}
                        </td>
                        <td className="py-2 pr-3">
                          <Button
                            variant="secondary"
                            onClick={() => void descargarArchivo(`/gobierno/expedientes-contractuales/paquetes/${paquete.id}/descargar`, paquete.nombre_archivo)}
                          >
                            Descargar
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </div>
          <div className="mt-4 rounded-md border border-border-subtle p-3">
            <h3 className="text-sm font-semibold text-text-900">Verificar un paquete</h3>
            <FormField label="Archivo .zip del paquete" htmlFor="paquete-archivo">
              <input
                id="paquete-archivo"
                type="file"
                accept=".zip"
                onChange={(e) => setArchivo(e.target.files?.[0] ?? null)}
                className="w-full text-sm"
              />
            </FormField>
            <AsyncButton variant="primary" disabled={verificando || !archivo} onClick={verificarPaquete}>
              {verificando ? "Verificando…" : "Verificar"}
            </AsyncButton>
            {errorVerificacion ? <p className="mt-2 text-sm text-red-700" role="alert">{errorVerificacion}</p> : null}
            {verificacion ? (
              <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
                <div>
                  <dt className="font-medium text-text-600">Resultado</dt>
                  <dd className="text-text-900">{ETIQUETAS_VERIFICACION[verificacion.resultado] ?? verificacion.resultado}</dd>
                </div>
                <div>
                  <dt className="font-medium text-text-600">Idéntico</dt>
                  <dd className="text-text-900">{verificacion.identico ? "Sí" : "No"}</dd>
                </div>
                {verificacion.motivos.length > 0 ? (
                  <div className="sm:col-span-2">
                    <dt className="font-medium text-text-600">Motivos</dt>
                    <dd className="text-text-900">
                      <ul className="list-disc pl-5">
                        {verificacion.motivos.map((motivo, indice) => (
                          <li key={indice}>
                            {ETIQUETAS_MOTIVO[motivo.codigo] ?? motivo.codigo}
                            {motivo.ruta ? `: ${motivo.ruta}` : ""}
                          </li>
                        ))}
                      </ul>
                    </dd>
                  </div>
                ) : null}
              </dl>
            ) : null}
          </div>
        </>
      ) : null}
    </section>
  );
}
