import { useState } from "react";
import { Link } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/Button";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { apiFetch } from "@/api/client";
import { hoyDeNegocio } from "@/lib/fecha-de-negocio";
import type {
  ExpedienteDetalle,
  ExpedienteCatalogo,
  ExpedienteOpciones,
  ExpedienteEvento,
  ExpedienteHito,
  ExpedienteFolio,
  ExpedienteResponsable,
} from "../api";

export interface PanelExpediente {
  detalle: ExpedienteDetalle;
  catalogo: ExpedienteCatalogo | undefined;
  opciones: ExpedienteOpciones | undefined;
  enviando: boolean;
  errores: Record<string, string[]>;
  alerta: string | null;
  escribir: (ruta: string, cuerpo: Record<string, unknown>) => Promise<void>;
  cerrarPanel: () => void;
}

const CONTROL =
  "block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600";

function errorDe(comun: PanelExpediente, campo: string): string | undefined {
  return comun.errores[campo]?.join(", ");
}

function Alerta({ texto }: { texto: string | null }) {
  if (!texto) {
    return null;
  }
  return (
    <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
      {texto}
    </p>
  );
}

function ETiquetaFuncionario(f: { nombre: string; cargos?: string[] }): string {
  if (f.cargos && f.cargos.length > 0) {
    return `${f.nombre} · ${f.cargos.join(", ")}`;
  }
  return f.nombre;
}

export function PanelResponsable({ comun }: { comun: PanelExpediente }) {
  const [funcionarioId, setFuncionarioId] = useState("");
  const [rol, setRol] = useState("");
  const [desde, setDesde] = useState(hoyDeNegocio());
  const opciones = comun.opciones;

  async function alEnviar(evento: React.FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    await comun.escribir("/responsables", {
      funcionario_id: funcionarioId,
      rol,
      desde,
    });
  }

  return (
    <section aria-labelledby="panel-responsable-titulo">
      <h2 id="panel-responsable-titulo" className="text-lg font-semibold text-text-900">
        Asignar responsable
      </h2>
      <form onSubmit={alEnviar} className="mt-3 space-y-3">
        <Alerta texto={comun.alerta} />
        <FormField label="Funcionario" htmlFor="resp-funcionario" required error={errorDe(comun, "funcionario_id")}>
          <select
            id="resp-funcionario"
            className={CONTROL}
            value={funcionarioId}
            onChange={(e) => setFuncionarioId(e.target.value)}
            required
          >
            <option value="">Seleccionar…</option>
            {(opciones?.funcionarios ?? []).map((f) => (
              <option key={f.id} value={f.id}>
                {ETiquetaFuncionario(f)}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Rol" htmlFor="resp-rol" required error={errorDe(comun, "rol")}>
          <select
            id="resp-rol"
            className={CONTROL}
            value={rol}
            onChange={(e) => setRol(e.target.value)}
            required
          >
            <option value="">Seleccionar…</option>
            {(comun.catalogo?.roles ?? []).map((r) => (
              <option key={r.codigo} value={r.codigo}>
                {r.etiqueta}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Desde" htmlFor="resp-desde" required error={errorDe(comun, "desde")}>
          <TextInput
            id="resp-desde"
            type="date"
            value={desde}
            onChange={(e) => setDesde(e.target.value)}
            required
          />
        </FormField>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={comun.cerrarPanel}>
            Cancelar
          </Button>
          <Button type="submit" variant="primary" disabled={comun.enviando || !funcionarioId || !rol || !desde}>
            Guardar
          </Button>
        </div>
      </form>
    </section>
  );
}

export function PanelTerminarResponsable({
  comun,
  responsable,
}: {
  comun: PanelExpediente;
  responsable: ExpedienteResponsable;
}) {
  const [fecha, setFecha] = useState(hoyDeNegocio());
  const [motivo, setMotivo] = useState("");

  async function alEnviar(evento: React.FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    await comun.escribir(`/responsables/${responsable.id}/terminar`, { fecha, motivo });
  }

  return (
    <section aria-labelledby="panel-terminar-titulo">
      <h2 id="panel-terminar-titulo" className="text-lg font-semibold text-text-900">
        Terminar responsabilidad
      </h2>
      <p className="mt-1 text-sm text-text-700">
        {responsable.nombre} · {responsable.rol_etiqueta}
      </p>
      <form onSubmit={alEnviar} className="mt-3 space-y-3">
        <Alerta texto={comun.alerta} />
        <FormField label="Fecha" htmlFor="fin-fecha" required error={errorDe(comun, "fecha")}>
          <TextInput
            id="fin-fecha"
            type="date"
            value={fecha}
            onChange={(e) => setFecha(e.target.value)}
            required
          />
        </FormField>
        <FormField label="Motivo" htmlFor="fin-motivo" required error={errorDe(comun, "motivo")}>
          <textarea
            id="fin-motivo"
            className={CONTROL}
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
            required
          />
        </FormField>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={comun.cerrarPanel}>
            Cancelar
          </Button>
          <Button type="submit" variant="primary" disabled={comun.enviando || !fecha || !motivo}>
            Guardar
          </Button>
        </div>
      </form>
    </section>
  );
}

export function PanelComision({ comun }: { comun: PanelExpediente }) {
  const tieneVinculo = Boolean(comun.detalle.comision_detalle || comun.detalle.comision_no_aplica_motivo);
  const [modo, setModo] = useState<"vincular" | "no-aplica">("vincular");
  const [comisionId, setComisionId] = useState("");
  const [noAplicaMotivo, setNoAplicaMotivo] = useState("");
  const [motivo, setMotivo] = useState("");
  const comisionesEnVigor = comun.opciones?.comisiones ?? [];

  async function alEnviar(evento: React.FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    await comun.escribir("/comision", {
      comision_id: modo === "vincular" ? comisionId : null,
      no_aplica_motivo: modo === "no-aplica" ? noAplicaMotivo : null,
      motivo: tieneVinculo ? motivo : null,
    });
  }

  const faltante =
    modo === "vincular"
      ? !comisionId
      : !noAplicaMotivo;

  return (
    <section aria-labelledby="panel-comision-titulo">
      <h2 id="panel-comision-titulo" className="text-lg font-semibold text-text-900">
        {tieneVinculo ? "Cambiar comisión" : "Vincular comisión"}
      </h2>
      <form onSubmit={alEnviar} className="mt-3 space-y-3">
        <Alerta texto={comun.alerta} />
        <fieldset className="space-y-2">
          <legend className="text-sm font-medium text-text-900">Intervención</legend>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="radio"
              name="com-modo"
              value="vincular"
              checked={modo === "vincular"}
              onChange={() => setModo("vincular")}
            />
            Vincular una comisión
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="radio"
              name="com-modo"
              value="no-aplica"
              checked={modo === "no-aplica"}
              onChange={() => setModo("no-aplica")}
            />
            No interviene comisión (RLCP art. 33)
          </label>
        </fieldset>
        {modo === "vincular" ? (
          comisionesEnVigor.length === 0 ? (
            <p className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
              No hay comisiones en vigor.{" "}
              <Link to="/gobierno/contrataciones/comisiones" className="underline">
                Gestionar comisiones
              </Link>
            </p>
          ) : (
            <FormField label="Comisión" htmlFor="com-comision" required error={errorDe(comun, "comision_id")}>
              <select
                id="com-comision"
                className={CONTROL}
                value={comisionId}
                onChange={(e) => setComisionId(e.target.value)}
                required
              >
                <option value="">Seleccionar…</option>
                {comisionesEnVigor.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.codigo} · {c.nombre}
                  </option>
                ))}
              </select>
            </FormField>
          )
        ) : (
          <FormField label="Motivo de no intervención" htmlFor="com-no-aplica" required error={errorDe(comun, "no_aplica_motivo")}>
            <textarea
              id="com-no-aplica"
              className={CONTROL}
              value={noAplicaMotivo}
              onChange={(e) => setNoAplicaMotivo(e.target.value)}
              required
            />
          </FormField>
        )}
        {tieneVinculo && (
          <FormField label="Motivo del cambio" htmlFor="com-motivo" required error={errorDe(comun, "motivo")}>
            <textarea
              id="com-motivo"
              className={CONTROL}
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              required
            />
          </FormField>
        )}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={comun.cerrarPanel}>
            Cancelar
          </Button>
          <Button type="submit" variant="primary" disabled={comun.enviando || faltante || (tieneVinculo && !motivo)}>
            Guardar
          </Button>
        </div>
      </form>
    </section>
  );
}

export function PanelActuacion({
  comun,
  rectifica,
  clase,
}: {
  comun: PanelExpediente;
  rectifica: ExpedienteEvento | null;
  clase: "ACTUACION" | "DECISION";
}) {
  const esDecision = (rectifica ? rectifica.clase : clase) === "DECISION";
  const [fecha, setFecha] = useState(hoyDeNegocio());
  const [titulo, setTitulo] = useState(rectifica?.titulo ?? "");
  const [detalle, setDetalle] = useState("");
  const [resultado, setResultado] = useState("");
  const [funcionarioId, setFuncionarioId] = useState("");
  const [actoId, setActoId] = useState("");
  const [folioId, setFolioId] = useState("");
  const [hitoId, setHitoId] = useState("");
  const [motivo, setMotivo] = useState("");

  async function alEnviar(evento: React.FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    await comun.escribir("/actuaciones", {
      clase: rectifica ? rectifica.clase : clase,
      fecha,
      titulo,
      detalle: detalle || null,
      resultado: resultado || null,
      funcionario_id: funcionarioId || null,
      acto_id: actoId || null,
      folio_id: folioId || null,
      hito_id: hitoId || null,
      rectifica_id: rectifica ? rectifica.id : null,
      motivo: rectifica ? motivo || null : null,
    });
  }

  const faltaObligatorio = !fecha || !titulo || !funcionarioId || (rectifica ? !motivo : false) || (esDecision && !resultado);

  const tituloPanel = rectifica
    ? `Rectificar registro ${rectifica.secuencia}`
    : esDecision
      ? "Registrar decisión"
      : "Registrar actuación";

  return (
    <section aria-labelledby="panel-actuacion-titulo">
      <h2 id="panel-actuacion-titulo" className="text-lg font-semibold text-text-900">
        {tituloPanel}
      </h2>
      {rectifica && (
        <p className="mt-1 text-sm text-text-700">El registro original se conserva.</p>
      )}
      <form onSubmit={alEnviar} className="mt-3 space-y-3">
        <Alerta texto={comun.alerta} />
        <FormField label="Fecha" htmlFor="act-fecha" required error={errorDe(comun, "fecha")}>
          <TextInput
            id="act-fecha"
            type="date"
            value={fecha}
            onChange={(e) => setFecha(e.target.value)}
            required
          />
        </FormField>
        <FormField label="Título" htmlFor="act-titulo" required error={errorDe(comun, "titulo")}>
          <TextInput
            id="act-titulo"
            value={titulo}
            onChange={(e) => setTitulo(e.target.value)}
            required
          />
        </FormField>
        <FormField label="Detalle" htmlFor="act-detalle" error={errorDe(comun, "detalle")}>
          <textarea
            id="act-detalle"
            className={CONTROL}
            value={detalle}
            onChange={(e) => setDetalle(e.target.value)}
          />
        </FormField>
        <FormField
          label="Resultado"
          htmlFor="act-resultado"
          required={esDecision}
          help={esDecision ? "Una decisión no adjudica: la adjudicación llegará con su propio proceso" : undefined}
          error={errorDe(comun, "resultado")}
        >
          <TextInput
            id="act-resultado"
            value={resultado}
            onChange={(e) => setResultado(e.target.value)}
            required={esDecision}
          />
        </FormField>
        <FormField label="Responsable" htmlFor="act-funcionario" error={errorDe(comun, "funcionario_id")}>
          <select
            id="act-funcionario"
            className={CONTROL}
            value={funcionarioId}
            onChange={(e) => setFuncionarioId(e.target.value)}
          >
            <option value="">Sin responsable</option>
            {(comun.opciones?.funcionarios ?? []).map((f) => (
              <option key={f.id} value={f.id}>
                {ETiquetaFuncionario(f)}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Acto formal" htmlFor="act-acto" error={errorDe(comun, "acto_id")}>
          <select
            id="act-acto"
            className={CONTROL}
            value={actoId}
            onChange={(e) => setActoId(e.target.value)}
          >
            <option value="">Sin acto</option>
            {(comun.opciones?.actos ?? []).map((a) => (
              <option key={a.id} value={a.id}>
                {a.etiqueta}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Folio" htmlFor="act-folio" error={errorDe(comun, "folio_id")}>
          <select
            id="act-folio"
            className={CONTROL}
            value={folioId}
            onChange={(e) => setFolioId(e.target.value)}
          >
            <option value="">Sin folio</option>
            {comun.detalle.folios.map((f) => (
              <option key={f.id} value={f.id}>
                Folio {f.numero} · {f.etiqueta}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Hito" htmlFor="act-hito" error={errorDe(comun, "hito_id")}>
          <select
            id="act-hito"
            className={CONTROL}
            value={hitoId}
            onChange={(e) => setHitoId(e.target.value)}
          >
            <option value="">Sin hito</option>
            {comun.detalle.hitos.map((h) => (
              <option key={h.id} value={h.id}>
                {h.nombre}
              </option>
            ))}
          </select>
        </FormField>
        {rectifica && (
          <FormField label="Motivo de la rectificación" htmlFor="act-motivo" required error={errorDe(comun, "motivo")}>
            <textarea
              id="act-motivo"
              className={CONTROL}
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              required
            />
          </FormField>
        )}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={comun.cerrarPanel}>
            Cancelar
          </Button>
          <Button type="submit" variant="primary" disabled={comun.enviando || faltaObligatorio}>
            Guardar
          </Button>
        </div>
      </form>
    </section>
  );
}

export function PanelFolio({ comun }: { comun: PanelExpediente }) {
  const [clase, setClase] = useState("");
  const [tipo, setTipo] = useState<"documento" | "acto">("documento");
  const [documentoId, setDocumentoId] = useState("");
  const [actoId, setActoId] = useState("");
  const [hitoId, setHitoId] = useState("");
  const [reservado, setReservado] = useState(false);
  const [motivoReserva, setMotivoReserva] = useState("");
  const [busqueda, setBusqueda] = useState("");

  const vinculados = useQuery({
    queryKey: ["gobierno", "expedientes", comun.detalle.id, "documentos-vinculados"],
    queryFn: () =>
      apiFetch<{ id: string; title: string; current_version: { version_number: number } | null }[]>(
        `/documentos/por-recurso/GovernmentProcurementFile/${comun.detalle.id}`,
      ),
  });

  const buscados = useQuery({
    queryKey: ["documentos", "buscar", busqueda],
    queryFn: () =>
      apiFetch<{ items: { id: string; title: string; current_version: { version_number: number } | null }[] }>(
        `/documentos?q=${encodeURIComponent(busqueda)}&limit=25`,
      ),
    enabled: tipo === "documento",
  });

  const folioIds = new Set(comun.detalle.folios.map((f: ExpedienteFolio) => f.documento_id).filter(Boolean));
  const vistos = new Set<string>();
  const candidatos: { id: string; title: string; version: number }[] = [];
  for (const doc of [...(vinculados.data ?? []), ...(buscados.data?.items ?? [])]) {
    if (!doc.current_version) {
      continue;
    }
    if (folioIds.has(doc.id) || vistos.has(doc.id)) {
      continue;
    }
    vistos.add(doc.id);
    candidatos.push({ id: doc.id, title: doc.title, version: doc.current_version.version_number });
  }

  const clasesAgrupadas = (comun.catalogo?.clases_folio ?? []).reduce<
    Record<string, { codigo: string; etiqueta: string }[]>
  >((acc, c) => {
    const grupo = c.grupo ?? "OTROS";
    acc[grupo] = acc[grupo] ?? [];
    acc[grupo].push(c);
    return acc;
  }, {});

  async function alEnviar(evento: React.FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    await comun.escribir("/folios", {
      clase,
      documento_id: tipo === "documento" ? documentoId : null,
      acto_id: tipo === "acto" ? actoId : null,
      hito_id: hitoId || null,
      reservado,
      motivo_reserva: reservado ? motivoReserva || null : null,
    });
  }

  const falta =
    !clase ||
    (tipo === "documento" ? !documentoId : !actoId) ||
    (reservado && !motivoReserva);

  return (
    <section aria-labelledby="panel-folio-titulo">
      <h2 id="panel-folio-titulo" className="text-lg font-semibold text-text-900">
        Incorporar al expediente
      </h2>
      <form onSubmit={alEnviar} className="mt-3 space-y-3">
        <Alerta texto={comun.alerta} />
        <FormField label="Clase" htmlFor="fol-clase" required error={errorDe(comun, "clase")}>
          <select
            id="fol-clase"
            className={CONTROL}
            value={clase}
            onChange={(e) => setClase(e.target.value)}
            required
          >
            <option value="">Seleccionar…</option>
            {Object.entries(clasesAgrupadas).map(([grupo, lista]) => (
              <optgroup
                key={grupo}
                label={
                  grupo === "SELECCION"
                    ? "Selección del contratista (RLCP art. 32)"
                    : grupo === "ADMINISTRACION"
                      ? "Administración del contrato (RLCP art. 32)"
                      : grupo
                }
              >
                {lista.map((c) => (
                  <option key={c.codigo} value={c.codigo}>
                    {c.etiqueta}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </FormField>
        <fieldset className="space-y-2">
          <legend className="text-sm font-medium text-text-900">Tipo</legend>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="radio"
              name="fol-tipo"
              value="documento"
              checked={tipo === "documento"}
              onChange={() => setTipo("documento")}
            />
            Documento
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="radio"
              name="fol-tipo"
              value="acto"
              checked={tipo === "acto"}
              onChange={() => setTipo("acto")}
            />
            Acto
          </label>
        </fieldset>
        {tipo === "documento" ? (
          <>
            <FormField label="Buscar documento del ente" htmlFor="fol-buscar">
              <TextInput
                id="fol-buscar"
                value={busqueda}
                onChange={(e) => setBusqueda(e.target.value)}
              />
            </FormField>
            <FormField label="Documento" htmlFor="fol-documento" required error={errorDe(comun, "documento_id")}>
              <select
                id="fol-documento"
                className={CONTROL}
                value={documentoId}
                onChange={(e) => setDocumentoId(e.target.value)}
                required
              >
                <option value="">Seleccionar…</option>
                {candidatos.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.title} · versión {d.version}
                  </option>
                ))}
              </select>
            </FormField>
          </>
        ) : (
          <FormField label="Acto" htmlFor="fol-acto" required error={errorDe(comun, "acto_id")}>
            <select
              id="fol-acto"
              className={CONTROL}
              value={actoId}
              onChange={(e) => setActoId(e.target.value)}
              required
            >
              <option value="">Seleccionar…</option>
              {(comun.opciones?.actos ?? []).map((a) => (
                <option key={a.id} value={a.id}>
                  {a.etiqueta}
                </option>
              ))}
            </select>
          </FormField>
        )}
        <FormField label="Hito" htmlFor="fol-hito" error={errorDe(comun, "hito_id")}>
          <select
            id="fol-hito"
            className={CONTROL}
            value={hitoId}
            onChange={(e) => setHitoId(e.target.value)}
          >
            <option value="">Sin hito</option>
            {comun.detalle.hitos.map((h) => (
              <option key={h.id} value={h.id}>
                {h.nombre}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Reservado" htmlFor="fol-reservado" help="LCP art. 20">
          <input
            id="fol-reservado"
            type="checkbox"
            checked={reservado}
            onChange={(e) => setReservado(e.target.checked)}
          />
        </FormField>
        {reservado && (
          <FormField label="Motivo de reserva" htmlFor="fol-motivo-reserva" required error={errorDe(comun, "motivo_reserva")}>
            <textarea
              id="fol-motivo-reserva"
              className={CONTROL}
              value={motivoReserva}
              onChange={(e) => setMotivoReserva(e.target.value)}
              required
            />
          </FormField>
        )}
        <p className="text-sm text-text-700">El folio se asigna al incorporar y no se puede borrar ni cambiar.</p>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={comun.cerrarPanel}>
            Cancelar
          </Button>
          <Button type="submit" variant="primary" disabled={comun.enviando || falta}>
            Guardar
          </Button>
        </div>
      </form>
    </section>
  );
}

export function PanelHito({ comun }: { comun: PanelExpediente }) {
  const [nombre, setNombre] = useState("");
  const [fuente, setFuente] = useState("");
  const [fechaPrevista, setFechaPrevista] = useState(hoyDeNegocio());
  const [funcionarioId, setFuncionarioId] = useState("");

  async function alEnviar(evento: React.FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    await comun.escribir("/hitos", {
      nombre,
      fuente,
      fecha_prevista: fechaPrevista,
      funcionario_id: funcionarioId || null,
    });
  }

  return (
    <section aria-labelledby="panel-hito-titulo">
      <h2 id="panel-hito-titulo" className="text-lg font-semibold text-text-900">
        Registrar hito
      </h2>
      <p className="mt-1 text-sm text-text-700">{comun.catalogo?.aviso_lapsos}</p>
      <form onSubmit={alEnviar} className="mt-3 space-y-3">
        <Alerta texto={comun.alerta} />
        <FormField label="Nombre" htmlFor="hito-nombre" required error={errorDe(comun, "nombre")}>
          <TextInput
            id="hito-nombre"
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            required
          />
        </FormField>
        <FormField label="Fuente o fundamento" htmlFor="hito-fuente" required error={errorDe(comun, "fuente")}>
          <TextInput
            id="hito-fuente"
            value={fuente}
            onChange={(e) => setFuente(e.target.value)}
            required
          />
        </FormField>
        <FormField label="Fecha prevista" htmlFor="hito-prevista" required error={errorDe(comun, "fecha_prevista")}>
          <TextInput
            id="hito-prevista"
            type="date"
            value={fechaPrevista}
            onChange={(e) => setFechaPrevista(e.target.value)}
            required
          />
        </FormField>
        <FormField label="Responsable" htmlFor="hito-funcionario" error={errorDe(comun, "funcionario_id")}>
          <select
            id="hito-funcionario"
            className={CONTROL}
            value={funcionarioId}
            onChange={(e) => setFuncionarioId(e.target.value)}
          >
            <option value="">Sin responsable</option>
            {(comun.opciones?.funcionarios ?? []).map((f) => (
              <option key={f.id} value={f.id}>
                {ETiquetaFuncionario(f)}
              </option>
            ))}
          </select>
        </FormField>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={comun.cerrarPanel}>
            Cancelar
          </Button>
          <Button type="submit" variant="primary" disabled={comun.enviando || !nombre || !fuente || !fechaPrevista}>
            Guardar
          </Button>
        </div>
      </form>
    </section>
  );
}

export function PanelActualizarHito({
  comun,
  hito,
}: {
  comun: PanelExpediente;
  hito: ExpedienteHito;
}) {
  const [fechaPrevista, setFechaPrevista] = useState(hito.fecha_prevista ?? "");
  const [fechaReal, setFechaReal] = useState(hito.fecha_real ?? "");
  const [noAplica, setNoAplica] = useState(hito.estado === "NO_APLICA");
  const [fuente, setFuente] = useState(hito.fuente ?? "");
  const [funcionarioId, setFuncionarioId] = useState(hito.funcionario_id ?? "");
  const [motivo, setMotivo] = useState("");

  async function alEnviar(evento: React.FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    await comun.escribir(`/hitos/${hito.id}/actualizar`, {
      fecha_prevista: fechaPrevista || null,
      fecha_real: fechaReal || null,
      no_aplica: noAplica,
      fuente: fuente || null,
      funcionario_id: funcionarioId || null,
      motivo: motivo || null,
    });
  }

  return (
    <section aria-labelledby="panel-upd-hito-titulo">
      <h2 id="panel-upd-hito-titulo" className="text-lg font-semibold text-text-900">
        Actualizar hito
      </h2>
      <form onSubmit={alEnviar} className="mt-3 space-y-3">
        <Alerta texto={comun.alerta} />
        <FormField label="Fecha prevista" htmlFor="upd-prevista" error={errorDe(comun, "fecha_prevista")}>
          <TextInput
            id="upd-prevista"
            type="date"
            value={fechaPrevista}
            onChange={(e) => setFechaPrevista(e.target.value)}
          />
        </FormField>
        <FormField label="Fecha real" htmlFor="upd-real" error={errorDe(comun, "fecha_real")}>
          <TextInput
            id="upd-real"
            type="date"
            value={fechaReal}
            onChange={(e) => setFechaReal(e.target.value)}
          />
        </FormField>
        <FormField label="No aplica" htmlFor="upd-no-aplica">
          <input
            id="upd-no-aplica"
            type="checkbox"
            checked={noAplica}
            onChange={(e) => setNoAplica(e.target.checked)}
          />
        </FormField>
        <FormField label="Fuente" htmlFor="upd-fuente" error={errorDe(comun, "fuente")}>
          <TextInput
            id="upd-fuente"
            value={fuente}
            onChange={(e) => setFuente(e.target.value)}
          />
        </FormField>
        <FormField label="Responsable" htmlFor="upd-funcionario" error={errorDe(comun, "funcionario_id")}>
          <select
            id="upd-funcionario"
            className={CONTROL}
            value={funcionarioId}
            onChange={(e) => setFuncionarioId(e.target.value)}
          >
            <option value="">Sin responsable</option>
            {(comun.opciones?.funcionarios ?? []).map((f) => (
              <option key={f.id} value={f.id}>
                {ETiquetaFuncionario(f)}
              </option>
            ))}
          </select>
        </FormField>
        <FormField
          label="Motivo"
          htmlFor="upd-motivo"
          help="Obligatorio si reprograma, corrige la fecha real o marca que no aplica"
          error={errorDe(comun, "motivo")}
        >
          <textarea
            id="upd-motivo"
            className={CONTROL}
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
          />
        </FormField>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={comun.cerrarPanel}>
            Cancelar
          </Button>
          <Button type="submit" variant="primary" disabled={comun.enviando}>
            Guardar
          </Button>
        </div>
      </form>
    </section>
  );
}

export function PanelCerrar({ comun }: { comun: PanelExpediente }) {
  const [fecha, setFecha] = useState(hoyDeNegocio());
  const [motivo, setMotivo] = useState("");

  async function alEnviar(evento: React.FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    await comun.escribir("/cerrar", { fecha, motivo });
  }

  return (
    <section aria-labelledby="panel-cerrar-titulo">
      <h2 id="panel-cerrar-titulo" className="text-lg font-semibold text-text-900">
        Cerrar expediente
      </h2>
      <p className="mt-1 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
        Cerrar impide más incorporaciones. No adjudica ni termina la contratación. No se puede reabrir.
      </p>
      <form onSubmit={alEnviar} className="mt-3 space-y-3">
        <Alerta texto={comun.alerta} />
        <FormField label="Fecha" htmlFor="cie-fecha" required error={errorDe(comun, "fecha")}>
          <TextInput
            id="cie-fecha"
            type="date"
            value={fecha}
            onChange={(e) => setFecha(e.target.value)}
            required
          />
        </FormField>
        <FormField label="Motivo" htmlFor="cie-motivo" required error={errorDe(comun, "motivo")}>
          <textarea
            id="cie-motivo"
            className={CONTROL}
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
            required
          />
        </FormField>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={comun.cerrarPanel}>
            Cancelar
          </Button>
          <Button type="submit" variant="danger" disabled={comun.enviando || !fecha || !motivo}>
            Cerrar expediente
          </Button>
        </div>
      </form>
    </section>
  );
}

export function PanelDescartar({ comun }: { comun: PanelExpediente }) {
  const [motivo, setMotivo] = useState("");

  async function alEnviar(evento: React.FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    await comun.escribir("/descartar", { motivo });
  }

  return (
    <section aria-labelledby="panel-descartar-titulo">
      <h2 id="panel-descartar-titulo" className="text-lg font-semibold text-text-900">
        Descartar expediente
      </h2>
      <p className="mt-1 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
        Solo para un expediente creado por error y sin contenido.
      </p>
      <form onSubmit={alEnviar} className="mt-3 space-y-3">
        <Alerta texto={comun.alerta} />
        <FormField label="Motivo" htmlFor="des-motivo" required error={errorDe(comun, "motivo")}>
          <textarea
            id="des-motivo"
            className={CONTROL}
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
            required
          />
        </FormField>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={comun.cerrarPanel}>
            Cancelar
          </Button>
          <Button type="submit" variant="danger" disabled={comun.enviando || !motivo}>
            Descartar expediente
          </Button>
        </div>
      </form>
    </section>
  );
}
