import type { ReglaActa } from "./api";
import { ETIQUETAS_HITO, ETIQUETAS_EVIDENCIA, describirPlazo } from "./reglaActa";

export function ReglaActaResumen({ regla, congelada }: { regla: ReglaActa; congelada?: boolean }) {
  return (
    <section aria-labelledby="sec-regla" className="flex flex-col gap-3">
      <h2 id="sec-regla" className="text-lg font-semibold">Regla aplicada</h2>
      <p className="text-sm">{regla.origen_etiqueta} · {regla.regla_version}</p>
      {congelada === true && <p className="text-sm text-text-600">Congelada al suscribir: no cambia aunque cambie la política.</p>}
      {congelada === false && <p className="text-sm text-text-600">Se recalcula al editar el borrador.</p>}
      <p className="text-sm">Norma: {regla.norma.titulo} ({regla.norma.gaceta})</p>
      <ul aria-label="Supuestos que aplican" className="flex flex-col gap-1">
        {regla.supuestos.map((s) => (
          <li key={s.codigo} className="text-sm">
            N34 art. {s.articulo} · {s.titulo}: {s.motivo}
            {s.nota ? ` (${s.nota})` : ""}
          </li>
        ))}
      </ul>
      <ul aria-label="Anexos exigidos" className="flex flex-col gap-1">
        {regla.anexos.map((a) => (
          <li key={a.codigo} className="text-sm">
            {a.codigo} · {a.titulo}
            {a.obligatorio ? " (obligatorio)" : " (opcional)"}
            {a.origen === "POLITICA" ? " · Política del ente" : ""}
            {a.fuente ? ` · ${a.fuente}` : ""}
            {a.document_type_nombre ? ` · Tipo: ${a.document_type_nombre}` : ""}
            {a.evidencia !== "DOCUMENTO" ? ` · Evidencia: ${ETIQUETAS_EVIDENCIA[a.evidencia]}` : ""}
          </li>
        ))}
      </ul>
      <p className="text-sm">
        Acta levantada por el receptor: {regla.testigos.levantada_por_receptor.testigos} testigos y auditor interno ({regla.testigos.levantada_por_receptor.fuente})
      </p>
      {regla.testigos.entrega.minimo > 0 && (
        <p className="text-sm">Entrega por el saliente: al menos {regla.testigos.entrega.minimo} testigos ({regla.testigos.entrega.fuente})</p>
      )}
      <ul aria-label="Plazos" className="flex flex-col gap-1">
        {regla.plazos.map((p, i) => (
          <li key={`${p.hito}-${i}`} className="text-sm">
            {ETIQUETAS_HITO[p.hito]}: {describirPlazo(p)} ({p.fuente ?? "—"})
          </li>
        ))}
      </ul>
      <p className="text-sm">Numeración: {regla.numeracion.patron}</p>
      {regla.avisos.map((aviso, i) => (
        <div key={i} role="status" className="rounded-md border border-warning bg-warning/10 p-3 text-warning">
          {aviso}
        </div>
      ))}
    </section>
  );
}
