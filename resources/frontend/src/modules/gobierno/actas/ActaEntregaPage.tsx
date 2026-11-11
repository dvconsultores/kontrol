import { useState } from "react";
import { useParams } from "react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { descargarArchivo } from "@/api/descargas";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/Button";
import { AsyncButton } from "@/components/AsyncButton";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { DateInput } from "@/components/DateInput";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { formatearFecha } from "@/i18n";
import { formatearFechaDeNegocio, hoyDeNegocio } from "@/lib/fecha-de-negocio";
import { AdjuntosPanel } from "@/modules/documentos/AdjuntosPanel";
import {
  ApiError,
  getActa,
  getHistorialActa,
  getIntegridadActa,
  actualizarAnexo,
  suscribirActa,
  remitirActa,
  observarActa,
  verificarActa,
  verAnexoGenerado,
  ActaFicha,
} from "./api";

const ESTADOS: Record<string, string> = {
  BORRADOR: "Borrador",
  SUSCRITA: "Suscrita",
  VERIFICADA: "Verificada",
};

const MODALIDADES: Record<string, string> = {
  ENTREGA: "Entrega por el saliente",
  LEVANTADA_POR_RECEPTOR: "Levantada por el receptor",
};

export function ActaEntregaPage() {
  const { actaId } = useParams();
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();

  const puedeVer = tiene("gobierno_actas:view", "empresa");
  const puedeGestionar = tiene("gobierno_actas:manage", "empresa");
  const puedeVerificar = tiene("gobierno_actas:verify", "empresa");

  const [errorAccion, setErrorAccion] = useState<string | null>(null);

  const [suscripcionFecha, setSuscripcionFecha] = useState(hoyDeNegocio());
  const [suscripcionErrores, setSuscripcionErrores] = useState("");
  const [remisionFecha, setRemisionFecha] = useState(hoyDeNegocio());
  const [observacionFecha, setObservacionFecha] = useState(hoyDeNegocio());
  const [observacionTexto, setObservacionTexto] = useState("");
  const [verificacionNumero, setVerificacionNumero] = useState("");
  const [verificacionFecha, setVerificacionFecha] = useState(hoyDeNegocio());
  const [verificacionResultado, setVerificacionResultado] = useState<"CONFORME" | "CON_OBSERVACIONES">("CONFORME");
  const [verificacionFundamento, setVerificacionFundamento] = useState("");

  const [anexoGenerado, setAnexoGenerado] = useState<Record<string, unknown> | null>(null);
  const [anexoGeneradoCodigo, setAnexoGeneradoCodigo] = useState("");
  const [documentosPorAnexo, setDocumentosPorAnexo] = useState<Record<string, string[]>>({});
  const [constanciasPorAnexo, setConstanciasPorAnexo] = useState<Record<string, string>>({});
  const [incluirGenerado, setIncluirGenerado] = useState<Record<string, boolean>>({});

  const ficha = useQuery({
    queryKey: ["gobierno-actas-ficha", activeCompanyId, actaId],
    queryFn: () => getActa(actaId!),
    enabled: puedeVer && !!actaId,
  });

  const historial = useQuery({
    queryKey: ["gobierno-actas-historial", activeCompanyId, actaId],
    queryFn: () => getHistorialActa(actaId!),
    enabled: puedeVer && !!actaId,
  });

  const integridad = useQuery({
    queryKey: ["gobierno-actas-integridad", activeCompanyId, actaId],
    queryFn: () => getIntegridadActa(actaId!),
    enabled: false,
  });

  const invalidar = () => Promise.all([
    queryClient.invalidateQueries({ queryKey: ["gobierno-actas-ficha", activeCompanyId, actaId] }),
    queryClient.invalidateQueries({ queryKey: ["gobierno-actas", activeCompanyId] }),
    queryClient.invalidateQueries({ queryKey: ["gobierno-actas-historial", activeCompanyId, actaId] }),
  ]);

  const mutAnexo = useMutation({
    mutationFn: ({ codigo, body }: { codigo: string; body: { incluir_generado?: boolean; documento_ids?: string[]; constancia?: string } }) =>
      actualizarAnexo(actaId!, codigo, body),
    onSuccess: () => { notify({ type: "success", title: "Anexo actualizado" }); invalidar(); },
    onError: (err: ApiError) => setErrorAccion(err.message),
  });

  const mutSuscribir = useMutation({
    mutationFn: () => suscribirActa(actaId!, {
      fecha_suscripcion: suscripcionFecha,
      errores_deficiencias: suscripcionErrores || null,
    }),
    onSuccess: () => { notify({ type: "success", title: "Acta suscrita" }); invalidar(); },
    onError: (err: ApiError) => setErrorAccion(err.message),
  });

  const mutRemitir = useMutation({
    mutationFn: () => remitirActa(actaId!, { fecha: remisionFecha }),
    onSuccess: () => { notify({ type: "success", title: "Remisión registrada" }); setRemisionFecha(""); invalidar(); },
    onError: (err: ApiError) => setErrorAccion(err.message),
  });

  const mutObservar = useMutation({
    mutationFn: () => observarActa(actaId!, { fecha: observacionFecha, texto: observacionTexto }),
    onSuccess: () => { notify({ type: "success", title: "Observación registrada" }); setObservacionFecha(hoyDeNegocio()); setObservacionTexto(""); invalidar(); },
    onError: (err: ApiError) => setErrorAccion(err.message),
  });

  const mutVerificar = useMutation({
    mutationFn: () => verificarActa(actaId!, {
      numero: verificacionNumero,
      fecha: verificacionFecha,
      resultado: verificacionResultado,
      fundamento: verificacionFundamento,
    }),
    onSuccess: () => { notify({ type: "success", title: "Verificación registrada" }); invalidar(); },
    onError: (err: ApiError) => setErrorAccion(err.message),
  });

  if (!puedeVer) {
    return <ErrorState message="No tiene permiso para ver este acta." />;
  }

  if (ficha.isLoading) return <PageContent><LoadingState /></PageContent>;
  if (ficha.isError) return <PageContent><ErrorState message={(ficha.error as Error).message} onRetry={() => ficha.refetch()} /></PageContent>;
  if (!ficha.data) return <PageContent><EmptyState title="Sin acta" /></PageContent>;

  const f = ficha.data as ActaFicha;
  const esBorrador = f.estado === "BORRADOR";


  const cargarGenerado = async (codigo: string) => {
    setAnexoGeneradoCodigo(codigo);
    setAnexoGenerado(null);
    try {
      const data = await verAnexoGenerado(actaId!, codigo);
      setAnexoGenerado(data);
    } catch (err) {
      setErrorAccion((err as Error).message);
    }
  };

  return (
    <PageContent>
      <PageHeader title={`Acta ${f.codigo}`} description={ESTADOS[f.estado] ?? f.estado} />

      <div role="alert" className={errorAccion ? "rounded-md border border-danger bg-danger/10 p-3 text-danger" : "hidden"}>{errorAccion}</div>

      <section aria-labelledby="sec-datos" className="flex flex-col gap-3">
        <h2 id="sec-datos" className="text-lg font-semibold">Datos del acta</h2>
        <dl className="rounded-md border border-border-default p-3 grid gap-3">
          <div><dt className="text-sm text-text-600">Saliente</dt><dd>{f.saliente.funcionario} · {f.saliente.cargo} · {f.saliente.unidad}</dd></div>
          <div><dt className="text-sm text-text-600">Receptor</dt><dd>{f.receptor.funcionario}</dd></div>
          <div><dt className="text-sm text-text-600">Modalidad</dt><dd>{MODALIDADES[f.modalidad] ?? f.modalidad}</dd></div>
          <div><dt className="text-sm text-text-600">Testigos</dt><dd>{f.testigos.length ? f.testigos.map((t) => t.nombre).join(", ") : "—"}</dd></div>
          <div><dt className="text-sm text-text-600">Auditor</dt><dd>{f.auditor?.funcionario ?? "—"}</dd></div>
          <div><dt className="text-sm text-text-600">Motivo</dt><dd>{f.motivo}</dd></div>
          <div><dt className="text-sm text-text-600">Fundamento</dt><dd>{f.fundamento}</dd></div>
          <div><dt className="text-sm text-text-600">Lugar</dt><dd>{f.lugar}</dd></div>
          <div><dt className="text-sm text-text-600">Fecha de corte</dt><dd>{formatearFechaDeNegocio(f.fecha_corte)}</dd></div>
          <div><dt className="text-sm text-text-600">Ámbito</dt><dd>{f.ambito}</dd></div>
        </dl>
      </section>

      {f.anexos_pendientes.length > 0 && (
        <div role="status" className="rounded-md border border-warning bg-warning/10 p-3 text-warning">
          Anexos obligatorios pendientes: {f.anexos_pendientes.join(", ")}
        </div>
      )}

      <section aria-labelledby="sec-anexos" className="flex flex-col gap-3">
        <h2 id="sec-anexos" className="text-lg font-semibold">Anexos</h2>
        <table className="w-full text-sm border-collapse">
          <caption className="sr-only">Anexos del acta</caption>
          <thead>
            <tr>
              <th className="text-left p-2 border-b">Código</th>
              <th className="text-left p-2 border-b">Anexo</th>
              <th className="text-left p-2 border-b">Obligatorio</th>
              <th className="text-left p-2 border-b">Situación</th>
            </tr>
          </thead>
          <tbody>
            {f.anexos.map((anexo) => (
              <>
                <tr key={anexo.codigo}>
                  <td className="p-2 border-b">{anexo.codigo}</td>
                  <td className="p-2 border-b">{anexo.titulo}</td>
                  <td className="p-2 border-b">{anexo.obligatorio ? "Sí" : "No"}</td>
                  <td className="p-2 border-b">{anexo.resuelto ? "Resuelto" : "Pendiente"}</td>
                </tr>
                {esBorrador && puedeGestionar && (
                  <tr key={`${anexo.codigo}-acciones`}>
                    <td colSpan={4} className="p-2 border-b bg-surface-0">
                      <div className="flex flex-col gap-3">
                        {anexo.generable && (
                          <div className="flex items-center gap-3">
                            <label className="flex items-center gap-2">
                              <input
                                type="checkbox"
                                checked={incluirGenerado[anexo.codigo] ?? anexo.incluir_generado}
                                onChange={(e) => setIncluirGenerado((prev) => ({ ...prev, [anexo.codigo]: e.target.checked }))}
                              />
                              Incluir contenido generado al corte
                            </label>
                            <Button variant="secondary" onClick={() => cargarGenerado(anexo.codigo)}>Ver contenido generado</Button>
                            <Button variant="secondary" onClick={() => mutAnexo.mutate({ codigo: anexo.codigo, body: { incluir_generado: incluirGenerado[anexo.codigo] ?? anexo.incluir_generado } })} disabled={mutAnexo.isPending}>Guardar</Button>
                          </div>
                        )}
                        {anexoGenerado && anexoGeneradoCodigo === anexo.codigo && (
                          <pre aria-label={`Contenido generado de ${anexo.codigo}`} className="rounded-md border border-border-default p-3 text-xs overflow-auto">
                            {JSON.stringify(anexoGenerado, null, 2)}
                          </pre>
                        )}
                        <div className="flex flex-col gap-2">
                          <span className="text-sm font-semibold">Documentos del acta</span>
                          {f.documentos_del_acta.map((doc) => (
                            <label key={doc.id} className="flex items-center gap-2">
                              <input
                                type="checkbox"
                                checked={(documentosPorAnexo[anexo.codigo] ?? anexo.documento_ids).includes(doc.id)}
                                onChange={(e) => {
                                  const actuales = documentosPorAnexo[anexo.codigo] ?? anexo.documento_ids;
                                  const nuevos = e.target.checked ? [...actuales, doc.id] : actuales.filter((id) => id !== doc.id);
                                  setDocumentosPorAnexo((prev) => ({ ...prev, [anexo.codigo]: nuevos }));
                                }}
                              />
                              {doc.title}
                            </label>
                          ))}
                          <Button variant="secondary" onClick={() => mutAnexo.mutate({ codigo: anexo.codigo, body: { documento_ids: documentosPorAnexo[anexo.codigo] ?? anexo.documento_ids } })} disabled={mutAnexo.isPending}>Guardar documentos</Button>
                        </div>
                        <FormField label="Constancia (art. 19)" htmlFor={`constancia-${anexo.codigo}`}>
                          <textarea
                            id={`constancia-${anexo.codigo}`}
                            className="w-full rounded-md border border-border-default p-2 text-sm"
                            value={constanciasPorAnexo[anexo.codigo] ?? anexo.constancia ?? ""}
                            onChange={(e) => setConstanciasPorAnexo((prev) => ({ ...prev, [anexo.codigo]: e.target.value }))}
                          />
                        </FormField>
                        <Button variant="secondary" onClick={() => mutAnexo.mutate({ codigo: anexo.codigo, body: { constancia: constanciasPorAnexo[anexo.codigo] ?? anexo.constancia ?? "" } })} disabled={mutAnexo.isPending}>Guardar constancia</Button>
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </section>

      {esBorrador && <AdjuntosPanel resourceType="GovernmentHandoverAct" resourceId={actaId!} title="Documentos del acta" onChange={() => invalidar()} />}

      {esBorrador && (
        <section aria-labelledby="sec-suscripcion" className="flex flex-col gap-3">
          <h2 id="sec-suscripcion" className="text-lg font-semibold">Suscripción</h2>
          {puedeGestionar ? (
            <form className="rounded-md border border-border-default bg-surface-0 p-3 flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); mutSuscribir.mutate(); }}>
              <FormField label="Fecha de suscripción" htmlFor="s-fecha" required><DateInput id="s-fecha" value={suscripcionFecha} onChange={(e) => setSuscripcionFecha(e.target.value)} /></FormField>
              <FormField label="Errores o deficiencias (art. 18)" htmlFor="s-errores">
                <textarea id="s-errores" className="w-full rounded-md border border-border-default p-2 text-sm" value={suscripcionErrores} onChange={(e) => setSuscripcionErrores(e.target.value)} />
              </FormField>
              <AsyncButton type="submit" variant="primary" loadingText="Suscribiendo..." idleText="Suscribir acta" onClick={async () => { await mutSuscribir.mutateAsync(); }} disabled={mutSuscribir.isPending || f.anexos_pendientes.length > 0} />
            </form>
          ) : (
            <p className="text-sm text-text-600">Sin permisos para suscribir.</p>
          )}
        </section>
      )}

      {f.estado === "SUSCRITA" && (
        <section aria-labelledby="sec-huella" className="flex flex-col gap-3">
          <h2 id="sec-huella" className="text-lg font-semibold">Huella del acta</h2>
          <p className="text-sm">{f.snapshot_sha256}</p>
          <Button variant="secondary" onClick={() => descargarArchivo(`/gobierno/actas-entrega/actas/${actaId}/acta.pdf`, `acta-${f.codigo}`)}>Descargar acta (PDF)</Button>
        </section>
      )}

      {(f.estado === "SUSCRITA" || f.estado === "VERIFICADA") && (
        <section aria-labelledby="sec-remision" className="flex flex-col gap-3">
          <h2 id="sec-remision" className="text-lg font-semibold">Remisión a la UAI (art. 21)</h2>
          {f.remision_uai_fecha ? (
            <p className="text-sm">{formatearFechaDeNegocio(f.remision_uai_fecha)}</p>
          ) : puedeGestionar ? (
            <form className="rounded-md border border-border-default bg-surface-0 p-3 flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); mutRemitir.mutate(); }}>
              <FormField label="Fecha de remisión" htmlFor="r-fecha" required><DateInput id="r-fecha" value={remisionFecha} onChange={(e) => setRemisionFecha(e.target.value)} /></FormField>
              <AsyncButton type="submit" variant="primary" loadingText="Registrando..." idleText="Registrar remisión" onClick={async () => { await mutRemitir.mutateAsync(); }} disabled={mutRemitir.isPending} />
            </form>
          ) : null}
        </section>
      )}

      <section aria-labelledby="sec-observaciones" className="flex flex-col gap-3">
        <h2 id="sec-observaciones" className="text-lg font-semibold">Observaciones (art. 22)</h2>
        {f.observaciones.length === 0 && <p className="text-sm text-text-600">Sin observaciones.</p>}
        {f.observaciones.map((o, i) => (
          <p key={i} className="text-sm">{formatearFechaDeNegocio(o.fecha)} · {o.texto} · {o.registrada_por}</p>
        ))}
        {(f.estado === "SUSCRITA" || f.estado === "VERIFICADA") && puedeGestionar && (
          <form className="rounded-md border border-border-default bg-surface-0 p-3 flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); mutObservar.mutate(); }}>
            <FormField label="Fecha de la observación" htmlFor="o-fecha" required><DateInput id="o-fecha" value={observacionFecha} onChange={(e) => setObservacionFecha(e.target.value)} /></FormField>
            <FormField label="Observación" htmlFor="o-texto" required>
              <textarea id="o-texto" className="w-full rounded-md border border-border-default p-2 text-sm" value={observacionTexto} onChange={(e) => setObservacionTexto(e.target.value)} />
            </FormField>
            <AsyncButton type="submit" variant="primary" loadingText="Registrando..." idleText="Registrar observación" onClick={async () => { await mutObservar.mutateAsync(); }} disabled={mutObservar.isPending} />
          </form>
        )}
      </section>

      <section aria-labelledby="sec-verificacion" className="flex flex-col gap-3">
        <h2 id="sec-verificacion" className="text-lg font-semibold">Verificación de la UAI</h2>
        {f.verificacion ? (
          <dl className="rounded-md border border-border-default p-3">
            <div><dt className="text-sm text-text-600">Número</dt><dd>{f.verificacion.numero}</dd></div>
            <div><dt className="text-sm text-text-600">Fecha</dt><dd>{formatearFechaDeNegocio(f.verificacion.fecha)}</dd></div>
            <div><dt className="text-sm text-text-600">Resultado</dt><dd>{f.verificacion.resultado === "CONFORME" ? "Conforme" : "Con observaciones"}</dd></div>
            <div><dt className="text-sm text-text-600">Fundamento</dt><dd>{f.verificacion.fundamento}</dd></div>
            <div><dt className="text-sm text-text-600">Verificada por</dt><dd>{f.verificacion.verificada_por}</dd></div>
          </dl>
        ) : f.estado === "SUSCRITA" && puedeVerificar ? (
          <form className="rounded-md border border-border-default bg-surface-0 p-3 flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); mutVerificar.mutate(); }}>
            <FormField label="Número del informe" htmlFor="v-numero" required><TextInput id="v-numero" value={verificacionNumero} onChange={(e) => setVerificacionNumero(e.target.value)} /></FormField>
            <FormField label="Fecha del informe" htmlFor="v-fecha" required><DateInput id="v-fecha" value={verificacionFecha} onChange={(e) => setVerificacionFecha(e.target.value)} /></FormField>
            <div className="flex flex-wrap gap-2">
              <label className="flex items-center gap-2"><input type="radio" checked={verificacionResultado === "CONFORME"} onChange={() => setVerificacionResultado("CONFORME")} /> Conforme</label>
              <label className="flex items-center gap-2"><input type="radio" checked={verificacionResultado === "CON_OBSERVACIONES"} onChange={() => setVerificacionResultado("CON_OBSERVACIONES")} /> Con observaciones</label>
            </div>
            <FormField label="Fundamento de la verificación" htmlFor="v-fundamento" required>
              <textarea id="v-fundamento" className="w-full rounded-md border border-border-default p-2 text-sm" value={verificacionFundamento} onChange={(e) => setVerificacionFundamento(e.target.value)} />
            </FormField>
            <AsyncButton type="submit" variant="primary" loadingText="Registrando..." idleText="Registrar verificación" onClick={async () => { await mutVerificar.mutateAsync(); }} disabled={mutVerificar.isPending} />
          </form>
        ) : null}
      </section>

      <section aria-labelledby="sec-integridad" className="flex flex-col gap-3">
        <h2 id="sec-integridad" className="text-lg font-semibold">Integridad</h2>
        <Button variant="secondary" onClick={() => integridad.refetch()}>Verificar integridad</Button>
        <div aria-live="polite">
          {integridad.data && (
            <>
              <p>{integridad.data.estado === "VALIDO" ? "Resultado: Íntegra" : "Resultado: Incompleta"}</p>
              <p>Huella del acta: {integridad.data.snapshot_ok ? "correcta" : "alterada"}</p>
              <p>Acta en PDF: {integridad.data.informe_ok ? "correcta" : "alterada"}</p>
            </>
          )}
        </div>
      </section>

      <section aria-labelledby="sec-historial" className="flex flex-col gap-3">
        <h2 id="sec-historial" className="text-lg font-semibold">Historial</h2>
        {historial.isLoading && <LoadingState />}
        {historial.data && historial.data.items.length === 0 && <p className="text-sm">Sin historial.</p>}
        {historial.data?.items.map((h, i) => (
          <p key={i} className="text-sm">{formatearFecha(h.fecha)} · {h.accion_etiqueta} · {h.usuario}{h.motivo ? ` · ${h.motivo}` : ""}</p>
        ))}
      </section>
    </PageContent>
  );
}
