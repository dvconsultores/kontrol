import { useState } from "react";
import { Button } from "@/components/Button";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import type { ComisionDetalle, ComisionCatalogo, ComisionOpciones } from "@/modules/gobierno/api";

export interface PanelComun {
  detalle: ComisionDetalle;
  comisionId: string;
  catalogo: ComisionCatalogo | undefined;
  opciones: ComisionOpciones | undefined;
  enviando: boolean;
  erroresServidor: Record<string, string[]>;
  alertaCambio: string | null;
  escribir: (ruta: string, metodo: "POST" | "DELETE", cuerpo: Record<string, unknown>, version: number) => Promise<void>;
  cerrarPanel: () => void;
}

export function PanelMiembro({ comun }: { comun: PanelComun }) {
  const { detalle, comisionId, catalogo, opciones, enviando, erroresServidor, alertaCambio, escribir, cerrarPanel } = comun;
  const [funcionarioId, setFuncionarioId] = useState("");
  const [funcion, setFuncion] = useState("MIEMBRO");
  const [condicion, setCondicion] = useState("PRINCIPAL");
  const [area, setArea] = useState("");
  const [suplenteDeId, setSuplenteDeId] = useState("");
  const [certificacion, setCertificacion] = useState("");
  const [desde, setDesde] = useState("");
  const [actoId, setActoId] = useState("");
  const estado = detalle.status;

  const guardar = async () => {
    const cuerpo: Record<string, unknown> = {
      funcionario_id: funcionarioId,
      funcion,
      area: area || null,
      condicion,
      suplente_de_id: suplenteDeId || null,
      certificacion_snc: certificacion || null,
      desde: estado === "VIGENTE" ? desde : null,
      acto_id: estado === "VIGENTE" ? actoId : null,
    };
    await escribir(`/gobierno/contrataciones/comisiones/${comisionId}/miembros`, "POST", cuerpo, detalle.version);
  };

  const miembrosActivos = detalle.composicion.filter((m) => !m.fin_efectivo);
  const principalesDisponibles = miembrosActivos.filter(
    (m) => m.condicion === "PRINCIPAL" && m.fin_efectivo === null,
  );

  return (
    <section aria-labelledby="miembro-titulo" className="mb-8 rounded-lg border border-border-subtle p-4">
      <h2 id="miembro-titulo" className="mb-4 text-lg font-semibold text-text-900">
        {estado === "BORRADOR" ? "Añadir miembro" : "Designar miembro"}
      </h2>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (funcionarioId) void guardar();
        }}
        className="space-y-4"
      >
        <FormField label="Funcionario" htmlFor="miembro-funcionario">
          <select
            id="miembro-funcionario"
            className="block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
            value={funcionarioId}
            onChange={(e) => setFuncionarioId(e.target.value)}
          >
            <option value="">Seleccione…</option>
            {opciones?.funcionarios.map((f) => (
              <option key={f.id} value={f.id}>
                {`${f.nombre} · ${f.cargos.join(", ") || "Sin cargo vigente"} · ${f.unidades.join(", ") || "Sin unidad"}`}
              </option>
            ))}
          </select>
          {erroresServidor["funcionario_id"] ? (
            <p className="mt-1 text-sm text-danger-600" role="alert">
              {erroresServidor["funcionario_id"].join(", ")}
            </p>
          ) : null}
        </FormField>
        <FormField label="Función" htmlFor="miembro-funcion">
          <select
            id="miembro-funcion"
            className="block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
            value={funcion}
            onChange={(e) => setFuncion(e.target.value)}
          >
            <option value="MIEMBRO">Miembro</option>
            <option value="SECRETARIO">Secretario</option>
          </select>
          {erroresServidor["funcion"] ? (
            <p className="mt-1 text-sm text-danger-600" role="alert">
              {erroresServidor["funcion"].join(", ")}
            </p>
          ) : null}
        </FormField>
        <FormField label="Condición" htmlFor="miembro-condicion">
          <select
            id="miembro-condicion"
            className="block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
            value={condicion}
            onChange={(e) => setCondicion(e.target.value)}
          >
            <option value="PRINCIPAL">Principal</option>
            <option value="SUPLENTE">Suplente</option>
          </select>
          {erroresServidor["condicion"] ? (
            <p className="mt-1 text-sm text-danger-600" role="alert">
              {erroresServidor["condicion"].join(", ")}
            </p>
          ) : null}
        </FormField>
        {funcion === "MIEMBRO" && condicion === "PRINCIPAL" ? (
          <FormField label="Área" htmlFor="miembro-area">
            <select
              id="miembro-area"
              className="block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
              value={area}
              onChange={(e) => setArea(e.target.value)}
            >
              <option value="">Seleccione…</option>
              {catalogo?.areas.map((a) => (
                <option key={a.codigo} value={a.codigo}>
                  {a.etiqueta}
                </option>
              ))}
            </select>
            {erroresServidor["area"] ? (
              <p className="mt-1 text-sm text-danger-600" role="alert">
                {erroresServidor["area"].join(", ")}
              </p>
            ) : null}
          </FormField>
        ) : null}
        {funcion === "MIEMBRO" && condicion === "SUPLENTE" ? (
          <FormField label="Suple a" htmlFor="miembro-suplente-de">
            <select
              id="miembro-suplente-de"
              className="block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
              value={suplenteDeId}
              onChange={(e) => setSuplenteDeId(e.target.value)}
            >
              <option value="">Seleccione…</option>
              {principalesDisponibles.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.funcionario.nombre}
                </option>
              ))}
            </select>
            {erroresServidor["suplente_de_id"] ? (
              <p className="mt-1 text-sm text-danger-600" role="alert">
                {erroresServidor["suplente_de_id"].join(", ")}
              </p>
            ) : null}
          </FormField>
        ) : null}
        <FormField label="Certificación ante el SNC" htmlFor="miembro-certificacion">
          <TextInput
            id="miembro-certificacion"
            value={certificacion}
            onChange={(e) => setCertificacion(e.target.value)}
            placeholder="Opcional"
            className="w-full"
          />
          {erroresServidor["certificacion_snc"] ? (
            <p className="mt-1 text-sm text-danger-600" role="alert">
              {erroresServidor["certificacion_snc"].join(", ")}
            </p>
          ) : null}
        </FormField>
        {estado === "VIGENTE" ? (
          <>
            <FormField label="Desde" htmlFor="miembro-desde">
              <TextInput
                id="miembro-desde"
                type="date"
                value={desde}
                onChange={(e) => setDesde(e.target.value)}
                className="w-full"
              />
              {erroresServidor["desde"] ? (
                <p className="mt-1 text-sm text-danger-600" role="alert">
                  {erroresServidor["desde"].join(", ")}
                </p>
              ) : null}
            </FormField>
            <FormField label="Acto" htmlFor="miembro-acto">
              <select
                id="miembro-acto"
                className="block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
                value={actoId}
                onChange={(e) => setActoId(e.target.value)}
              >
                <option value="">Seleccione…</option>
                {opciones?.actos.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.etiqueta}
                  </option>
                ))}
              </select>
              {erroresServidor["acto_id"] ? (
                <p className="mt-1 text-sm text-danger-600" role="alert">
                  {erroresServidor["acto_id"].join(", ")}
                </p>
              ) : null}
            </FormField>
          </>
        ) : null}
        {alertaCambio ? (
          <p className="text-sm text-danger-600" role="alert">
            {alertaCambio}
          </p>
        ) : null}
        <div className="flex gap-2">
          <Button type="submit" variant="primary" disabled={!funcionarioId || enviando}>
            Guardar miembro
          </Button>
          <Button type="button" variant="ghost" onClick={cerrarPanel}>
            Cancelar
          </Button>
        </div>
      </form>
    </section>
  );
}

export function PanelInhibicion({ comun }: { comun: PanelComun }) {
  const { detalle, comisionId, catalogo, enviando, erroresServidor, alertaCambio, escribir, cerrarPanel } = comun;
  const [miembroId, setMiembroId] = useState("");
  const [asunto, setAsunto] = useState("");
  const [causal, setCausal] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [fechaInhibicion, setFechaInhibicion] = useState("");
  const [soporte, setSoporte] = useState("");

  const declarar = async () => {
    const cuerpo = {
      miembro_id: miembroId,
      asunto,
      causal,
      descripcion,
      fecha: fechaInhibicion,
      soporte: soporte || null,
    };
    await escribir(`/gobierno/contrataciones/comisiones/${comisionId}/inhibiciones`, "POST", cuerpo, detalle.version);
  };

  const miembrosActivos = detalle.composicion.filter((m) => !m.fin_efectivo);

  return (
    <section aria-labelledby="inhibicion-titulo" className="mb-8 rounded-lg border border-border-subtle p-4">
      <h2 id="inhibicion-titulo" className="mb-4 text-lg font-semibold text-text-900">
        Declarar inhibición
      </h2>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (miembroId && asunto && causal && fechaInhibicion) void declarar();
        }}
        className="space-y-4"
      >
        <FormField label="Miembro" htmlFor="inhibicion-miembro">
          <select
            id="inhibicion-miembro"
            className="block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
            value={miembroId}
            onChange={(e) => setMiembroId(e.target.value)}
          >
            <option value="">Seleccione…</option>
            {miembrosActivos.map((m) => (
              <option key={m.id} value={m.id}>
                {m.funcionario.nombre}
              </option>
            ))}
          </select>
          {erroresServidor["miembro_id"] ? (
            <p className="mt-1 text-sm text-danger-600" role="alert">
              {erroresServidor["miembro_id"].join(", ")}
            </p>
          ) : null}
        </FormField>
        <FormField label="Asunto" htmlFor="inhibicion-asunto">
          <TextInput
            id="inhibicion-asunto"
            value={asunto}
            onChange={(e) => setAsunto(e.target.value)}
            className="w-full"
          />
          {erroresServidor["asunto"] ? (
            <p className="mt-1 text-sm text-danger-600" role="alert">
              {erroresServidor["asunto"].join(", ")}
            </p>
          ) : null}
        </FormField>
        <FormField label="Causal" htmlFor="inhibicion-causal">
          <select
            id="inhibicion-causal"
            className="block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
            value={causal}
            onChange={(e) => setCausal(e.target.value)}
          >
            <option value="">Seleccione…</option>
            {catalogo?.causales.map((c) => (
              <option key={c.codigo} value={c.codigo}>
                {`${c.etiqueta} (${c.fuente})`}
              </option>
            ))}
          </select>
          {erroresServidor["causal"] ? (
            <p className="mt-1 text-sm text-danger-600" role="alert">
              {erroresServidor["causal"].join(", ")}
            </p>
          ) : null}
        </FormField>
        <FormField label="Descripción" htmlFor="inhibicion-descripcion">
          <textarea
            id="inhibicion-descripcion"
            className="block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
            value={descripcion}
            onChange={(e) => setDescripcion(e.target.value)}
            rows={3}
          />
          {erroresServidor["descripcion"] ? (
            <p className="mt-1 text-sm text-danger-600" role="alert">
              {erroresServidor["descripcion"].join(", ")}
            </p>
          ) : null}
        </FormField>
        <FormField label="Fecha" htmlFor="inhibicion-fecha">
          <TextInput
            id="inhibicion-fecha"
            type="date"
            value={fechaInhibicion}
            onChange={(e) => setFechaInhibicion(e.target.value)}
            className="w-full"
          />
          {erroresServidor["fecha"] ? (
            <p className="mt-1 text-sm text-danger-600" role="alert">
              {erroresServidor["fecha"].join(", ")}
            </p>
          ) : null}
        </FormField>
        <FormField label="Soporte" htmlFor="inhibicion-soporte">
          <TextInput
            id="inhibicion-soporte"
            value={soporte}
            onChange={(e) => setSoporte(e.target.value)}
            placeholder="Opcional"
            className="w-full"
          />
          {erroresServidor["soporte"] ? (
            <p className="mt-1 text-sm text-danger-600" role="alert">
              {erroresServidor["soporte"].join(", ")}
            </p>
          ) : null}
        </FormField>
        {alertaCambio ? (
          <p className="text-sm text-danger-600" role="alert">
            {alertaCambio}
          </p>
        ) : null}
        <div className="flex gap-2">
          <Button type="submit" variant="primary" disabled={!miembroId || !asunto || !causal || !fechaInhibicion || enviando}>
            Declarar
          </Button>
          <Button type="button" variant="ghost" onClick={cerrarPanel}>
            Cancelar
          </Button>
        </div>
      </form>
    </section>
  );
}

export function PanelResolverInhibicion({ comun, inhibicion }: { comun: PanelComun; inhibicion: { id: string; miembro: string; asunto: string; version: number } }) {
  const { comisionId, enviando, erroresServidor, alertaCambio, escribir, cerrarPanel } = comun;
  const [decision, setDecision] = useState("ACEPTADA");
  const [motivo, setMotivo] = useState("");

  const resolver = async () => {
    const cuerpo = {
      decision,
      motivo: motivo || null,
    };
    await escribir(
      `/gobierno/contrataciones/comisiones/${comisionId}/inhibiciones/${inhibicion.id}/resolver`,
      "POST",
      cuerpo,
      inhibicion.version,
    );
  };

  return (
    <section aria-labelledby="resolver-inhibicion-titulo" className="mb-8 rounded-lg border border-border-subtle p-4">
      <h2 id="resolver-inhibicion-titulo" className="mb-4 text-lg font-semibold text-text-900">
        Resolver inhibición
      </h2>
      <p className="mb-4 text-sm text-text-700">
        {inhibicion.asunto} — {inhibicion.miembro}
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (motivo) void resolver();
        }}
        className="space-y-4"
      >
        <FormField label="Decisión" htmlFor="resolver-decision">
          <select
            id="resolver-decision"
            className="block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
            value={decision}
            onChange={(e) => setDecision(e.target.value)}
          >
            <option value="ACEPTADA">Aceptar</option>
            <option value="RECHAZADA">Rechazar</option>
          </select>
          {erroresServidor["decision"] ? (
            <p className="mt-1 text-sm text-danger-600" role="alert">
              {erroresServidor["decision"].join(", ")}
            </p>
          ) : null}
        </FormField>
        <FormField label="Motivo" htmlFor="resolver-motivo">
          <TextInput
            id="resolver-motivo"
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
            className="w-full"
          />
          {erroresServidor["motivo"] ? (
            <p className="mt-1 text-sm text-danger-600" role="alert">
              {erroresServidor["motivo"].join(", ")}
            </p>
          ) : null}
        </FormField>
        {alertaCambio ? (
          <p className="text-sm text-danger-600" role="alert">
            {alertaCambio}
          </p>
        ) : null}
        <div className="flex gap-2">
          <Button type="submit" variant="primary" disabled={!motivo || enviando}>
            Resolver
          </Button>
          <Button type="button" variant="ghost" onClick={cerrarPanel}>
            Cancelar
          </Button>
        </div>
      </form>
    </section>
  );
}

export function PanelTerminarMiembro({ comun, miembro }: { comun: PanelComun; miembro: { id: string; nombre: string } }) {
  const { comisionId, detalle, catalogo, enviando, erroresServidor, alertaCambio, escribir, cerrarPanel } = comun;
  const [fechaFin, setFechaFin] = useState("");
  const [causa, setCausa] = useState("");
  const [motivo, setMotivo] = useState("");

  const terminar = async () => {
    const cuerpo = {
      fecha: fechaFin,
      causa,
      motivo: motivo || null,
    };
    await escribir(
      `/gobierno/contrataciones/comisiones/${comisionId}/miembros/${miembro.id}/terminar`,
      "POST",
      cuerpo,
      detalle.version,
    );
  };

  return (
    <section aria-labelledby="terminar-miembro-titulo" className="mb-8 rounded-lg border border-border-subtle p-4">
      <h2 id="terminar-miembro-titulo" className="mb-4 text-lg font-semibold text-text-900">
        Terminar miembro: {miembro.nombre}
      </h2>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (fechaFin && causa) void terminar();
        }}
        className="space-y-4"
      >
        <FormField label="Fecha de fin" htmlFor="fin-fecha">
          <TextInput
            id="fin-fecha"
            type="date"
            value={fechaFin}
            onChange={(e) => setFechaFin(e.target.value)}
            className="w-full"
          />
          {erroresServidor["fecha"] ? (
            <p className="mt-1 text-sm text-danger-600" role="alert">
              {erroresServidor["fecha"].join(", ")}
            </p>
          ) : null}
        </FormField>
        <FormField label="Causa" htmlFor="fin-causa">
          <select
            id="fin-causa"
            className="block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
            value={causa}
            onChange={(e) => setCausa(e.target.value)}
          >
            <option value="">Seleccione…</option>
            {catalogo?.causas_fin.map((c) => (
              <option key={c.codigo} value={c.codigo}>
                {c.etiqueta}
              </option>
            ))}
          </select>
          {erroresServidor["causa"] ? (
            <p className="mt-1 text-sm text-danger-600" role="alert">
              {erroresServidor["causa"].join(", ")}
            </p>
          ) : null}
        </FormField>
        <FormField label="Motivo" htmlFor="fin-motivo">
          <TextInput
            id="fin-motivo"
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
            placeholder="Opcional"
            className="w-full"
          />
          {erroresServidor["motivo"] ? (
            <p className="mt-1 text-sm text-danger-600" role="alert">
              {erroresServidor["motivo"].join(", ")}
            </p>
          ) : null}
        </FormField>
        {alertaCambio ? (
          <p className="text-sm text-danger-600" role="alert">
            {alertaCambio}
          </p>
        ) : null}
        <div className="flex gap-2">
          <Button type="submit" variant="primary" disabled={!fechaFin || !causa || enviando}>
            Terminar miembro
          </Button>
          <Button type="button" variant="ghost" onClick={cerrarPanel}>
            Cancelar
          </Button>
        </div>
      </form>
    </section>
  );
}

export function PanelRetirarMiembro({ comun, miembro }: { comun: PanelComun; miembro: { id: string; nombre: string } }) {
  const { comisionId, detalle, enviando, alertaCambio, escribir, cerrarPanel } = comun;

  const retirar = async () => {
    await escribir(
      `/gobierno/contrataciones/comisiones/${comisionId}/miembros/${miembro.id}`,
      "DELETE",
      {},
      detalle.version,
    );
  };

  return (
    <section aria-labelledby="retirar-miembro-titulo" className="mb-8 rounded-lg border border-border-subtle p-4">
      <h2 id="retirar-miembro-titulo" className="mb-4 text-lg font-semibold text-text-900">
        ¿Retirar a {miembro.nombre}?
      </h2>
      {alertaCambio ? (
        <p className="text-sm text-danger-600" role="alert">
          {alertaCambio}
        </p>
      ) : null}
      <div className="flex gap-2">
        <Button type="button" variant="primary" disabled={enviando} onClick={() => void retirar()}>
          Retirar
        </Button>
        <Button type="button" variant="ghost" onClick={cerrarPanel}>
          Cancelar
        </Button>
      </div>
    </section>
  );
}

export function PanelDescartar({ comun }: { comun: PanelComun }) {
  const { comisionId, detalle, enviando, erroresServidor, alertaCambio, escribir, cerrarPanel } = comun;
  const [motivo, setMotivo] = useState("");

  const descartar = async () => {
    await escribir(`/gobierno/contrataciones/comisiones/${comisionId}/descartar`, "POST", { motivo }, detalle.version);
  };

  return (
    <section aria-labelledby="descartar-comision-titulo" className="mb-8 rounded-lg border border-border-subtle p-4">
      <h2 id="descartar-comision-titulo" className="mb-4 text-lg font-semibold text-text-900">
        Descartar comisión
      </h2>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (motivo) void descartar();
        }}
        className="space-y-4"
      >
        <FormField label="Motivo" htmlFor="descarte-motivo">
          <TextInput
            id="descarte-motivo"
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
            className="w-full"
          />
          {erroresServidor["motivo"] ? (
            <p className="mt-1 text-sm text-danger-600" role="alert">
              {erroresServidor["motivo"].join(", ")}
            </p>
          ) : null}
        </FormField>
        {alertaCambio ? (
          <p className="text-sm text-danger-600" role="alert">
            {alertaCambio}
          </p>
        ) : null}
        <div className="flex gap-2">
          <Button type="submit" variant="primary" disabled={!motivo || enviando}>
            Descartar comisión
          </Button>
          <Button type="button" variant="ghost" onClick={cerrarPanel}>
            Cancelar
          </Button>
        </div>
      </form>
    </section>
  );
}

export function PanelCerrar({ comun }: { comun: PanelComun }) {
  const { comisionId, detalle, enviando, erroresServidor, alertaCambio, escribir, cerrarPanel } = comun;
  const [fechaCierre, setFechaCierre] = useState("");
  const [motivo, setMotivo] = useState("");

  const cerrar = async () => {
    const cuerpo = {
      fecha: fechaCierre,
      motivo: motivo || null,
    };
    await escribir(`/gobierno/contrataciones/comisiones/${comisionId}/cerrar`, "POST", cuerpo, detalle.version);
  };

  return (
    <section aria-labelledby="cerrar-comision-titulo" className="mb-8 rounded-lg border border-border-subtle p-4">
      <h2 id="cerrar-comision-titulo" className="mb-4 text-lg font-semibold text-text-900">
        Cerrar comisión
      </h2>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (fechaCierre) void cerrar();
        }}
        className="space-y-4"
      >
        <FormField label="Fecha de fin" htmlFor="cierre-fecha">
          <TextInput
            id="cierre-fecha"
            type="date"
            value={fechaCierre}
            onChange={(e) => setFechaCierre(e.target.value)}
            className="w-full"
          />
          {erroresServidor["fecha"] ? (
            <p className="mt-1 text-sm text-danger-600" role="alert">
              {erroresServidor["fecha"].join(", ")}
            </p>
          ) : null}
        </FormField>
        <FormField label="Motivo" htmlFor="cierre-motivo">
          <TextInput
            id="cierre-motivo"
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
            placeholder="Opcional"
            className="w-full"
          />
          {erroresServidor["motivo"] ? (
            <p className="mt-1 text-sm text-danger-600" role="alert">
              {erroresServidor["motivo"].join(", ")}
            </p>
          ) : null}
        </FormField>
        {alertaCambio ? (
          <p className="text-sm text-danger-600" role="alert">
            {alertaCambio}
          </p>
        ) : null}
        <div className="flex gap-2">
          <Button type="submit" variant="primary" disabled={!fechaCierre || enviando}>
            Cerrar comisión
          </Button>
          <Button type="button" variant="ghost" onClick={cerrarPanel}>
            Cancelar
          </Button>
        </div>
      </form>
    </section>
  );
}

export function PanelSnc({ comun }: { comun: PanelComun }) {
  const { comisionId, detalle, enviando, erroresServidor, alertaCambio, escribir, cerrarPanel } = comun;
  const [fechaNotificacion, setFechaNotificacion] = useState("");
  const [referencia, setReferencia] = useState("");

  const registrar = async () => {
    const cuerpo = {
      fecha: fechaNotificacion,
      referencia: referencia || null,
    };
    await escribir(`/gobierno/contrataciones/comisiones/${comisionId}/notificacion-snc`, "POST", cuerpo, detalle.version);
  };

  return (
    <section aria-labelledby="snc-comision-titulo" className="mb-8 rounded-lg border border-border-subtle p-4">
      <h2 id="snc-comision-titulo" className="mb-4 text-lg font-semibold text-text-900">
        Registrar notificación al SNC
      </h2>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (fechaNotificacion) void registrar();
        }}
        className="space-y-4"
      >
        <FormField label="Fecha" htmlFor="snc-fecha">
          <TextInput
            id="snc-fecha"
            type="date"
            value={fechaNotificacion}
            onChange={(e) => setFechaNotificacion(e.target.value)}
            className="w-full"
          />
          {erroresServidor["fecha"] ? (
            <p className="mt-1 text-sm text-danger-600" role="alert">
              {erroresServidor["fecha"].join(", ")}
            </p>
          ) : null}
        </FormField>
        <FormField label="Referencia" htmlFor="snc-referencia">
          <TextInput
            id="snc-referencia"
            value={referencia}
            onChange={(e) => setReferencia(e.target.value)}
            placeholder="Opcional"
            className="w-full"
          />
          {erroresServidor["referencia"] ? (
            <p className="mt-1 text-sm text-danger-600" role="alert">
              {erroresServidor["referencia"].join(", ")}
            </p>
          ) : null}
        </FormField>
        {alertaCambio ? (
          <p className="text-sm text-danger-600" role="alert">
            {alertaCambio}
          </p>
        ) : null}
        <div className="flex gap-2">
          <Button type="submit" variant="primary" disabled={!fechaNotificacion || enviando}>
            Registrar
          </Button>
          <Button type="button" variant="ghost" onClick={cerrarPanel}>
            Cancelar
          </Button>
        </div>
      </form>
    </section>
  );
}
