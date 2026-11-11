import { useState } from "react";
import { Link, useParams } from "react-router";
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
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import {
  ApiError,
  getExpediente,
  getHistorial,
  getIntegridad,
  getOpcionesRendicion,
  getReporte,
  incorporarPieza,
  listarCandidatas,
  nuevaVersion,
  registrarCalificacion,
  registrarFenecimiento,
  registrarParticipacion,
  retirarPieza,
  formarCuenta,
  FichaRendicion,
  Integridad,
} from "./api";
import { EditarCabeceraCuenta } from "./EditarCabeceraCuenta";

const ESTADOS: Record<string, string> = {
  EN_FORMACION: "En formación",
  FORMADA: "Formada",
  PARTICIPADA: "Participada",
  CALIFICADA: "Calificada",
  FENECIDA: "Fenecida",
  SUSTITUIDA: "Sustituida",
};

export function ExpedienteCuentaPage() {
  const { expedienteId } = useParams();
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();

  const puedeVer = tiene("gobierno_rendicion:view", "empresa");
  const puedeFormar = tiene("gobierno_rendicion:form", "empresa");
  const puedeCalificar = tiene("gobierno_rendicion:qualify", "empresa");

  const [procesoCandidata, setProcesoCandidata] = useState("");
  const [textoCandidata, setTextoCandidata] = useState("");
  const [paginaCandidata, setPaginaCandidata] = useState(1);
  const [integResult, setIntegResult] = useState<Integridad | null>(null);
  const [errorAccion, setErrorAccion] = useState<string | null>(null);

  const [participacionFecha, setParticipacionFecha] = useState("");
  const [participacionOficio, setParticipacionOficio] = useState("");
  const [motivoVersion, setMotivoVersion] = useState("");
  const [calResultado, setCalResultado] = useState<"CONFORME" | "OBJETADA">("CONFORME");
  const [calOrgano, setCalOrgano] = useState("");
  const [calNumero, setCalNumero] = useState("");
  const [calFecha, setCalFecha] = useState("");
  const [calFundamento, setCalFundamento] = useState("");
  const [fenNumero, setFenNumero] = useState("");
  const [fenFecha, setFenFecha] = useState("");
  const [fenFundamento, setFenFundamento] = useState("");

  const ficha = useQuery({
    queryKey: ["gobierno-rendicion-ficha", activeCompanyId, expedienteId],
    queryFn: () => getExpediente(expedienteId!),
    enabled: puedeVer && !!expedienteId,
  });

  const opciones = useQuery({ queryKey: ["gobierno-rendicion-opciones", activeCompanyId], queryFn: getOpcionesRendicion, enabled: puedeVer });

  const candidatas = useQuery({
    queryKey: ["gobierno-rendicion-candidatas", activeCompanyId, expedienteId, procesoCandidata, textoCandidata, paginaCandidata],
    queryFn: () => listarCandidatas(expedienteId!, { proceso: procesoCandidata || undefined, texto: textoCandidata || undefined, pagina: paginaCandidata, por_pagina: 10 }),
    enabled: puedeVer && !!expedienteId && ficha.data?.estado === "EN_FORMACION",
  });

  const reporte = useQuery({
    queryKey: ["gobierno-rendicion-reporte", activeCompanyId, expedienteId],
    queryFn: () => getReporte(expedienteId!),
    enabled: puedeVer && !!expedienteId,
  });

  const historial = useQuery({
    queryKey: ["gobierno-rendicion-historial", activeCompanyId, expedienteId],
    queryFn: () => getHistorial(expedienteId!),
    enabled: puedeVer && !!expedienteId,
  });

  const integridad = useQuery({
    queryKey: ["gobierno-rendicion-integridad", activeCompanyId, expedienteId],
    queryFn: () => getIntegridad(expedienteId!),
    enabled: false,
  });

  const invalidar = () => Promise.all([
    queryClient.invalidateQueries({ queryKey: ["gobierno-rendicion-ficha", activeCompanyId, expedienteId] }),
    queryClient.invalidateQueries({ queryKey: ["gobierno-rendicion-candidatas", activeCompanyId, expedienteId] }),
    queryClient.invalidateQueries({ queryKey: ["gobierno-rendicion-reporte", activeCompanyId, expedienteId] }),
    queryClient.invalidateQueries({ queryKey: ["gobierno-rendicion-historial", activeCompanyId, expedienteId] }),
  ]);

  const mutFormar = useMutation({
    mutationFn: () => formarCuenta(expedienteId!),
    onSuccess: () => { notify({ type: "success", title: "Cuenta formada" }); invalidar(); },
    onError: (err: ApiError) => setErrorAccion(err.message),
  });

  const mutParticipacion = useMutation({
    mutationFn: () => registrarParticipacion(expedienteId!, { fecha: participacionFecha, oficio: participacionOficio }),
    onSuccess: () => { notify({ type: "success", title: "Participación registrada" }); setParticipacionFecha(""); setParticipacionOficio(""); invalidar(); },
    onError: (err: ApiError) => setErrorAccion(err.message),
  });

  const mutVersion = useMutation({
    mutationFn: () => nuevaVersion(expedienteId!, { motivo: motivoVersion }),
    onSuccess: () => { notify({ type: "success", title: "Nueva versión creada" }); setMotivoVersion(""); invalidar(); },
    onError: (err: ApiError) => setErrorAccion(err.message),
  });

  const mutCalificacion = useMutation({
    mutationFn: () => registrarCalificacion(expedienteId!, { resultado: calResultado, organo: calOrgano, informe_numero: calNumero, informe_fecha: calFecha, fundamento: calFundamento }),
    onSuccess: () => { notify({ type: "success", title: "Calificación registrada" }); invalidar(); },
    onError: (err: ApiError) => setErrorAccion(err.message),
  });

  const mutFenecimiento = useMutation({
    mutationFn: () => registrarFenecimiento(expedienteId!, { auto_numero: fenNumero, auto_fecha: fenFecha, fundamento: fenFundamento || undefined }),
    onSuccess: () => { notify({ type: "success", title: "Fenecimiento registrado" }); invalidar(); },
    onError: (err: ApiError) => setErrorAccion(err.message),
  });

  const mutIncorporar = useMutation({
    mutationFn: (eventoId: string) => incorporarPieza(expedienteId!, eventoId),
    onSuccess: () => invalidar(),
    onError: (err: ApiError) => setErrorAccion(err.message),
  });

  const mutRetirar = useMutation({
    mutationFn: (piezaId: string) => retirarPieza(expedienteId!, piezaId),
    onSuccess: () => invalidar(),
    onError: (err: ApiError) => setErrorAccion(err.message),
  });

  if (!puedeVer) {
    return <ErrorState message="No tiene permiso para ver este expediente." />;
  }

  if (ficha.isLoading) return <PageContent><LoadingState /></PageContent>;
  if (ficha.isError) return <PageContent><ErrorState message={(ficha.error as Error).message} onRetry={() => ficha.refetch()} /></PageContent>;
  if (!ficha.data) return <PageContent><EmptyState title="Sin expediente" /></PageContent>;

  const f = ficha.data as FichaRendicion;
  const estado = f.estado;
  const esFormacion = estado === "EN_FORMACION";
  const piezasOrdenadas = [...f.piezas].sort((a, b) => (a.ordinal ?? 0) - (b.ordinal ?? 0));

  return (
    <PageContent>
      <PageHeader title={`${f.codigo} · v${f.numero_version}`} description={f.denominacion} />

      <div role="alert" className={errorAccion ? "rounded-md border border-danger bg-danger/10 p-3 text-danger" : "hidden"}>{errorAccion}</div>

      <section aria-labelledby="sec-cuenta" className="flex flex-col gap-3">
        <h2 id="sec-cuenta" className="text-lg font-semibold">Cuenta</h2>
        <dl className="flex flex-wrap gap-3">
          <div><dt className="text-sm text-text-600">Estado</dt><dd>{ESTADOS[estado] ?? estado}</dd></div>
          <div><dt className="text-sm text-text-600">Ente</dt><dd>{f.ente}</dd></div>
          <div><dt className="text-sm text-text-600">Periodo</dt><dd>{formatearFechaDeNegocio(f.periodo_desde)} – {formatearFechaDeNegocio(f.periodo_hasta)}</dd></div>
          <div><dt className="text-sm text-text-600">Corte</dt><dd>{formatearFechaDeNegocio(f.fecha_corte)}</dd></div>
          <div><dt className="text-sm text-text-600">Responsable</dt><dd>{f.responsable.funcionario} · {f.responsable.cargo} · {f.responsable.unidad} ({f.responsable.figura})</dd></div>
        </dl>
        {f.observaciones && <p className="break-words min-w-0 text-text-700">{f.observaciones}</p>}
        {estado === "EN_FORMACION" && puedeFormar && <EditarCabeceraCuenta ficha={f} responsables={opciones.data?.responsables ?? []} onGuardado={invalidar} />}
        {f.sustituido_por_id && (
          <div className="rounded-md border border-warning bg-warning/10 p-3">
            Esta versión fue sustituida por <Link to={`/gobierno/rendicion/${f.sustituido_por_id}`} className="underline">la versión nueva</Link>.
          </div>
        )}
        {f.anterior_id && (
          <p className="text-sm text-text-600">
            Versión anterior: <Link to={`/gobierno/rendicion/${f.anterior_id}`} className="underline">v{f.numero_version - 1}</Link>
            {f.sustitucion_motivo && <> · Motivo: {f.sustitucion_motivo}</>}
          </p>
        )}
      </section>

      <section aria-labelledby="sec-piezas" className="flex flex-col gap-3">
        <h2 id="sec-piezas" className="text-lg font-semibold">Índice de piezas</h2>
        {piezasOrdenadas.length === 0 && <EmptyState title="Sin piezas" description="Incorpore hechos del período." />}
        {piezasOrdenadas.map((p) => (
          <div key={p.id} className="rounded-md border border-border-default bg-surface-0 p-3">
            <div className="flex flex-wrap items-baseline gap-2">
              <span className="font-semibold">{p.ordinal ?? piezasOrdenadas.indexOf(p) + 1}.</span>
              <span>{formatearFecha(p.fecha)}</span>
              <span>{p.proceso_nombre}</span>
              <span>{p.accion_etiqueta}</span>
            </div>
            <div className="break-words min-w-0 text-text-700">{p.referencia}</div>
            <div className="text-sm text-text-600">{p.usuario}</div>
            <div className="flex flex-wrap gap-2 text-sm">
              <Link to={p.ruta_evento} className="underline">Ver en la bitácora</Link>
              {p.objeto && <Link to={p.objeto.ruta} className="underline">Abrir fuente</Link>}
            </div>
            <div className="text-sm text-text-600">{p.documentos.length} soportes · <span title={p.huella}>{p.huella.slice(0, 12)}…</span></div>
            {esFormacion && puedeFormar && (
              <Button variant="danger" size="sm" onClick={() => mutRetirar.mutate(p.id)} disabled={mutRetirar.isPending}>Retirar</Button>
            )}
          </div>
        ))}
      </section>

      {esFormacion && puedeFormar && (
        <section aria-labelledby="sec-candidatas" className="flex flex-col gap-3">
          <h2 id="sec-candidatas" className="text-lg font-semibold">Hechos disponibles del período</h2>
          <div className="flex flex-wrap gap-2">
            <FormField label="Proceso" htmlFor="c-proceso">
              <select id="c-proceso" className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600" value={procesoCandidata} onChange={(e) => { setProcesoCandidata(e.target.value); setPaginaCandidata(1); }}>
                <option value="">Todos</option>
                {(opciones.data?.procesos ?? []).map((p) => <option key={p.codigo} value={p.codigo}>{p.nombre}</option>)}
              </select>
            </FormField>
            <FormField label="Texto" htmlFor="c-texto">
              <TextInput id="c-texto" value={textoCandidata} onChange={(e) => { setTextoCandidata(e.target.value); setPaginaCandidata(1); }} />
            </FormField>
          </div>
          {candidatas.isLoading && <LoadingState />}
          {candidatas.data && candidatas.data.items.length === 0 && <EmptyState title="Sin candidatas" />}
          {candidatas.data?.items.map((c) => (
            <div key={c.evento_id} className="rounded-md border border-border-default bg-surface-0 p-3">
              <div className="break-words min-w-0">{c.referencia}</div>
              <div className="text-sm text-text-600">{formatearFecha(c.fecha)} · {c.proceso_nombre} · {c.usuario}</div>
              <Button variant="secondary" size="sm" disabled={c.incluida || mutIncorporar.isPending} onClick={() => mutIncorporar.mutate(c.evento_id)}>
                {c.incluida ? "Incorporada" : "Incorporar"}
              </Button>
            </div>
          ))}
          {candidatas.data && (
            <div className="flex items-center gap-2">
              <Button variant="secondary" size="sm" disabled={paginaCandidata <= 1} onClick={() => setPaginaCandidata((p) => p - 1)}>Anterior</Button>
              <span className="text-sm">Página {paginaCandidata}</span>
              <Button variant="secondary" size="sm" disabled={candidatas.data.items.length < 10} onClick={() => setPaginaCandidata((p) => p + 1)}>Siguiente</Button>
            </div>
          )}
        </section>
      )}

      <section aria-labelledby="sec-reporte" className="flex flex-col gap-3">
        <h2 id="sec-reporte" className="text-lg font-semibold">Reporte de rendición</h2>
        {reporte.isLoading && <LoadingState />}
        {reporte.data && (
          <>
            {reporte.data.provisional ? (
              <p className="text-sm text-warning">Reporte provisional: cambia mientras la cuenta esté en formación</p>
            ) : (
              <p className="text-sm">Corte congelado el {formatearFecha(f.formado_en ?? "")} · huella {reporte.data.snapshot_sha256}</p>
            )}
            {reporte.data.resumen.map((r, i) => (
              <dl key={i} className="rounded-md border border-border-default bg-surface-0 p-3">
                <div><dt className="text-sm text-text-600">Concepto</dt><dd>{r.concepto}</dd></div>
                <div><dt className="text-sm text-text-600">Fuente</dt><dd>{r.fuente}</dd></div>
                <div><dt className="text-sm text-text-600">Filtro</dt><dd>{r.filtro}</dd></div>
                <div><dt className="text-sm text-text-600">Período</dt><dd>{r.periodo}</dd></div>
                <div><dt className="text-sm text-text-600">Conjunto</dt><dd>{r.conjunto}</dd></div>
                <div><dt className="text-sm text-text-600">Regla</dt><dd>{r.regla}</dd></div>
                <div><dt className="text-sm text-text-600">Resultado</dt><dd>{String(r.resultado)}</dd></div>
              </dl>
            ))}
            {reporte.data.hallazgos.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold">Hallazgos</h3>
                {reporte.data.hallazgos.map((h, i) => <p key={i}>{h.ordinal}. {h.referencia}</p>)}
              </div>
            )}
            {estado !== "EN_FORMACION" && (
              <div className="flex flex-wrap gap-2">
                <Button variant="secondary" size="sm" onClick={() => descargarArchivo(`/gobierno/rendicion/expedientes/${f.id}/reporte.pdf`, "reporte")}>Descargar PDF</Button>
                <Button variant="secondary" size="sm" onClick={() => descargarArchivo(`/gobierno/rendicion/expedientes/${f.id}/indice.csv`, "indice")}>Descargar índice (CSV)</Button>
              </div>
            )}
          </>
        )}
      </section>

      <section aria-labelledby="sec-acciones" className="flex flex-col gap-3">
        <h2 id="sec-acciones" className="text-lg font-semibold">Acciones</h2>
        {esFormacion && puedeFormar && (
          <div className="rounded-md border border-border-default bg-surface-0 p-3">
            <p className="text-sm">Al formar se congelan el índice y el reporte.</p>
            <AsyncButton variant="primary" loadingText="Formando..." idleText="Formar la cuenta" onClick={async () => { await mutFormar.mutateAsync(); }} disabled={mutFormar.isPending} />
          </div>
        )}
        {estado === "FORMADA" && puedeFormar && (
          <form className="rounded-md border border-border-default bg-surface-0 p-3 flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); mutParticipacion.mutate(); }}>
            <h3 className="text-sm font-semibold">Registrar participación</h3>
            {f.plazo_participacion && <p className="text-sm">Plazo: {formatearFechaDeNegocio(f.plazo_participacion)}</p>}
            <FormField label="Fecha" htmlFor="p-fecha" required><DateInput id="p-fecha" value={participacionFecha} onChange={(e) => setParticipacionFecha(e.target.value)} /></FormField>
            <FormField label="Oficio" htmlFor="p-oficio" required><TextInput id="p-oficio" value={participacionOficio} onChange={(e) => setParticipacionOficio(e.target.value)} /></FormField>
            <AsyncButton type="submit" variant="primary" loadingText="Registrando..." idleText="Registrar participación" onClick={async () => { await mutParticipacion.mutateAsync(); }} disabled={mutParticipacion.isPending} />
          </form>
        )}
        {(estado === "FORMADA" || estado === "PARTICIPADA") && puedeFormar && (
          <form className="rounded-md border border-border-default bg-surface-0 p-3 flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); mutVersion.mutate(); }}>
            <h3 className="text-sm font-semibold">Crear nueva versión (subsanación)</h3>
            <FormField label="Motivo" htmlFor="v-motivo" required><TextInput id="v-motivo" value={motivoVersion} onChange={(e) => setMotivoVersion(e.target.value)} /></FormField>
            <AsyncButton type="submit" variant="primary" loadingText="Creando..." idleText="Crear nueva versión" onClick={async () => { await mutVersion.mutateAsync(); }} disabled={mutVersion.isPending} />
          </form>
        )}
        {estado === "PARTICIPADA" && puedeCalificar && (
          <form className="rounded-md border border-border-default bg-surface-0 p-3 flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); mutCalificacion.mutate(); }}>
            <h3 className="text-sm font-semibold">Registrar calificación del órgano de control</h3>
            <p className="text-sm text-text-600">KONTROL registra la calificación emitida por el órgano de control; no la calcula.</p>
            <div className="flex flex-wrap gap-2">
              <label className="flex items-center gap-2"><input type="radio" checked={calResultado === "CONFORME"} onChange={() => setCalResultado("CONFORME")} /> Conforme</label>
              <label className="flex items-center gap-2"><input type="radio" checked={calResultado === "OBJETADA"} onChange={() => setCalResultado("OBJETADA")} /> Objetada</label>
            </div>
            <FormField label="Órgano" htmlFor="c-organo" required><TextInput id="c-organo" value={calOrgano} onChange={(e) => setCalOrgano(e.target.value)} /></FormField>
            <FormField label="Número de informe definitivo" htmlFor="c-numero" required><TextInput id="c-numero" value={calNumero} onChange={(e) => setCalNumero(e.target.value)} /></FormField>
            <FormField label="Fecha del informe" htmlFor="c-fecha" required><DateInput id="c-fecha" value={calFecha} onChange={(e) => setCalFecha(e.target.value)} /></FormField>
            <FormField label="Fundamento" htmlFor="c-fundamento" required><TextInput id="c-fundamento" value={calFundamento} onChange={(e) => setCalFundamento(e.target.value)} /></FormField>
            <AsyncButton type="submit" variant="primary" loadingText="Registrando..." idleText="Registrar calificación" onClick={async () => { await mutCalificacion.mutateAsync(); }} disabled={mutCalificacion.isPending} />
          </form>
        )}
        {estado === "CALIFICADA" && puedeCalificar && (
          <form className="rounded-md border border-border-default bg-surface-0 p-3 flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); mutFenecimiento.mutate(); }}>
            <h3 className="text-sm font-semibold">Registrar fenecimiento</h3>
            <FormField label="Número de auto" htmlFor="f-auto" required><TextInput id="f-auto" value={fenNumero} onChange={(e) => setFenNumero(e.target.value)} /></FormField>
            <FormField label="Fecha del auto" htmlFor="f-fecha" required><DateInput id="f-fecha" value={fenFecha} onChange={(e) => setFenFecha(e.target.value)} /></FormField>
            <FormField label="Fundamento" htmlFor="f-fundamento" required={f.calificacion?.resultado === "OBJETADA"} error={f.calificacion?.resultado === "OBJETADA" && !fenFundamento ? "Obligatorio si la calificación fue Objetada" : undefined}>
              <TextInput id="f-fundamento" value={fenFundamento} onChange={(e) => setFenFundamento(e.target.value)} />
            </FormField>
            <AsyncButton type="submit" variant="primary" loadingText="Registrando..." idleText="Registrar fenecimiento" onClick={async () => { await mutFenecimiento.mutateAsync(); }} disabled={mutFenecimiento.isPending} />
          </form>
        )}
      </section>

      <section aria-labelledby="sec-rendicion" className="flex flex-col gap-3">
        <h2 id="sec-rendicion" className="text-lg font-semibold">Rendición</h2>
        {f.participacion && (
          <dl className="rounded-md border border-border-default p-3">
            <div><dt className="text-sm text-text-600">Fecha</dt><dd>{formatearFechaDeNegocio(f.participacion.fecha)}</dd></div>
            <div><dt className="text-sm text-text-600">Oficio</dt><dd>{f.participacion.oficio}</dd></div>
            <div><dt className="text-sm text-text-600">Vence</dt><dd>{formatearFechaDeNegocio(f.participacion.vence)} · {f.participacion.en_plazo ? "En plazo" : "Fuera de plazo"}</dd></div>
          </dl>
        )}
        {f.calificacion && (
          <dl className="rounded-md border border-border-default p-3">
            <div><dt className="text-sm text-text-600">Resultado</dt><dd>{f.calificacion.resultado}</dd></div>
            <div><dt className="text-sm text-text-600">Órgano</dt><dd>{f.calificacion.organo}</dd></div>
            <div><dt className="text-sm text-text-600">Informe</dt><dd>{f.calificacion.informe_numero} · {formatearFechaDeNegocio(f.calificacion.informe_fecha)}</dd></div>
            <div><dt className="text-sm text-text-600">Fundamento</dt><dd>{f.calificacion.fundamento}</dd></div>
          </dl>
        )}
        {f.fenecimiento && (
          <dl className="rounded-md border border-border-default p-3">
            <div><dt className="text-sm text-text-600">Auto</dt><dd>{f.fenecimiento.auto_numero} · {formatearFechaDeNegocio(f.fenecimiento.auto_fecha)}</dd></div>
            {f.fenecimiento.fundamento && <div><dt className="text-sm text-text-600">Fundamento</dt><dd>{f.fenecimiento.fundamento}</dd></div>}
          </dl>
        )}
        {!f.participacion && !f.calificacion && !f.fenecimiento && <p className="text-sm text-text-600">Sin registros de rendición.</p>}
      </section>

      {estado !== "EN_FORMACION" && (
        <section aria-labelledby="sec-integridad" className="flex flex-col gap-3">
          <h2 id="sec-integridad" className="text-lg font-semibold">Integridad</h2>
          <Button variant="secondary" onClick={() => integridad.refetch().then((r) => { if (r.data) setIntegResult(r.data); })}>Verificar integridad</Button>
          <div aria-live="polite">
            {integResult && (
              <div className="rounded-md border border-border-default p-3">
                <p className="font-semibold">{integResult.estado === "VALIDO" ? "Válido" : "Incompleto"} · snapshot: {integResult.snapshot_ok ? "OK" : "No"} · informe: {integResult.informe_ok ? "OK" : "No"}</p>
                {integResult.piezas.map((p, i) => (
                  <p key={i}>{p.ordinal}. {p.estado} · {p.detalle}</p>
                ))}
              </div>
            )}
          </div>
        </section>
      )}

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
