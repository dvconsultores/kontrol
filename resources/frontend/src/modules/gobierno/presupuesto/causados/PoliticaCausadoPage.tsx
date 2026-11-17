import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Button } from "@/components/Button";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { formatearFechaDeNegocio, hoyDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_CAUSADOS,
  RUTA_POLITICAS,
  DISPARADORES,
  ESTADOS_POLITICA,
  TIPOS_REGLA,
  ETAPAS,
  ACCIONES_COMPETENCIA,
  MATERIAS_COMPETENCIA,
  type PoliticaCausado,
  type PoliticaCausadoCuerpo,
  type DocumentoExigido,
  type TipoDocumento,
  type Disparador,
  type AccionCompetencia,
  type MateriaCompetencia,
  type EtapaDocumentoCausado,
  type TipoReglaCausado,
} from "./api";

const FECHA_HOY = hoyDeNegocio();

interface DocumentoFila {
  document_type_id: string;
  obligatorio: boolean;
  etapa: EtapaDocumentoCausado;
  condicion: string;
}

function convertirDocumentos(documentos: DocumentoExigido[]): DocumentoFila[] {
  return documentos.map((documento) => ({
    document_type_id: documento.document_type_id,
    obligatorio: documento.obligatorio,
    etapa: documento.etapa,
    condicion: documento.condicion ?? "",
  }));
}

function esCuerpoValido(cuerpo: PoliticaCausadoCuerpo): boolean {
  if (!cuerpo.codigo.trim() || !cuerpo.tipo_gasto.trim() || !cuerpo.nombre.trim()) return false;
  if (!cuerpo.disparador || !cuerpo.competencia_accion || !cuerpo.competencia_materia) return false;
  if (!cuerpo.vigente_desde) return false;
  if (cuerpo.vigente_hasta && cuerpo.vigente_hasta < cuerpo.vigente_desde) return false;
  if (cuerpo.disparador === "DOCUMENTARY" && !cuerpo.documentos.some((documento) => documento.obligatorio)) {
    return false;
  }
  return cuerpo.documentos.every((documento) => documento.document_type_id);
}

export function PoliticaCausadoPage() {
  const { politicaId } = useParams<{ politicaId: string }>();
  const navigate = useNavigate();
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();
  const esNueva = politicaId === undefined;
  const puedeGestionar = tiene("gobierno_presupuesto:cause_policy", "empresa");
  const puedeVer = tiene("gobierno_presupuesto:view", "empresa");

  const [editando, setEditando] = useState(esNueva);
  const [guardando, setGuardando] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [campoError, setCampoError] = useState<Record<string, string>>({});
  const [form, setForm] = useState<PoliticaCausadoCuerpo>({
    codigo: "",
    tipo_gasto: "",
    nombre: "",
    descripcion: "",
    disparador: "RECEIPT_ACCEPTED",
    requiere_recepcion: false,
    requiere_valuacion: false,
    requiere_conformidad: false,
    competencia_accion: "CAUSAR",
    competencia_materia: "PRESUPUESTO",
    vigente_desde: FECHA_HOY,
    vigente_hasta: "",
    fundamento: "",
    act_id: "",
    tipo_regla: "INSTITUTIONAL_POLICY",
    documentos: [],
  });
  const [documentos, setDocumentos] = useState<DocumentoFila[]>([]);

  const [dialogoActivarAbierto, setDialogoActivarAbierto] = useState(false);
  const [fundamentoActivacion, setFundamentoActivacion] = useState("");
  const [actoActivacion, setActoActivacion] = useState("");
  const [errorActivacion, setErrorActivacion] = useState<string | null>(null);
  const [activando, setActivando] = useState(false);

  const [dialogoCerrarAbierto, setDialogoCerrarAbierto] = useState(false);
  const [motivoCierre, setMotivoCierre] = useState("");
  const [cerrando, setCerrando] = useState(false);

  const detalle = useQuery({
    queryKey: [...CONSULTA_CAUSADOS, "politica", activeCompanyId, politicaId],
    queryFn: () =>
      apiFetch<PoliticaCausado>(`/gobierno/presupuesto/politicas-causado/${politicaId}`),
    enabled: Boolean(activeCompanyId) && !esNueva && puedeVer,
    retry: false,
  });

  const tiposDocumento = useQuery({
    queryKey: ["documentos", "tipos", activeCompanyId],
    queryFn: () => apiFetch<TipoDocumento[]>("/documentos/tipos"),
    enabled: Boolean(activeCompanyId) && puedeGestionar,
    retry: false,
  });

  useEffect(() => {
    if (detalle.data && !esNueva && !editando) {
      setForm({
        codigo: detalle.data.codigo,
        tipo_gasto: detalle.data.tipo_gasto,
        nombre: detalle.data.nombre,
        descripcion: detalle.data.descripcion ?? "",
        disparador: detalle.data.disparador,
        requiere_recepcion: detalle.data.requiere_recepcion,
        requiere_valuacion: detalle.data.requiere_valuacion,
        requiere_conformidad: detalle.data.requiere_conformidad,
        competencia_accion: detalle.data.competencia_accion,
        competencia_materia: detalle.data.competencia_materia,
        vigente_desde: detalle.data.vigente_desde?.slice(0, 10) ?? FECHA_HOY,
        vigente_hasta: detalle.data.vigente_hasta?.slice(0, 10) ?? "",
        fundamento: detalle.data.fundamento ?? "",
        act_id: detalle.data.act_id ?? "",
        tipo_regla: detalle.data.tipo_regla ?? "INSTITUTIONAL_POLICY",
        documentos: detalle.data.documentos.map((documento) => ({
          document_type_id: documento.document_type_id,
          obligatorio: documento.obligatorio,
          etapa: documento.etapa,
          condicion: documento.condicion ?? "",
        })),
      });
      setDocumentos(convertirDocumentos(detalle.data.documentos));
    }
  }, [detalle.data, esNueva, editando]);

  const cuerpoFormulario: PoliticaCausadoCuerpo = useMemo(
    () => ({
      ...form,
      vigente_hasta: form.vigente_hasta || undefined,
      fundamento: form.fundamento || undefined,
      act_id: form.act_id || undefined,
      documentos: documentos.map((documento) => ({
        document_type_id: documento.document_type_id,
        obligatorio: documento.obligatorio,
        etapa: documento.etapa,
        condicion: documento.condicion || undefined,
      })),
    }),
    [form, documentos],
  );

  const hayDocumentoObligatorioSinTipo = documentos.some(
    (documento) => documento.obligatorio && !documento.document_type_id,
  );
  const disparadorDocumentalInvalido =
    form.disparador === "DOCUMENTARY" &&
    !documentos.some((documento) => documento.obligatorio && documento.document_type_id);

  const formularioValido = esCuerpoValido(cuerpoFormulario) && !disparadorDocumentalInvalido && !hayDocumentoObligatorioSinTipo;

  const cabecera = (
    <PageHeader
      crumbs={[{ label: "Gobierno" }, { label: "Políticas de causado", to: RUTA_POLITICAS }, { label: esNueva ? "Nueva política" : detalle.data?.codigo ?? "Política" }]}
      title={esNueva ? "Nueva política de causado" : detalle.data?.nombre ?? "Política de causado"}
      description={esNueva ? "Registre una política para definir cuándo y cómo se causa un tipo de gasto." : `Código: ${detalle.data?.codigo ?? ""}`}
      status={detalle.data ? (
        <span className="rounded bg-surface-100 px-2 py-0.5 text-xs font-medium text-text-700">
          {ESTADOS_POLITICA[detalle.data.estado]}
        </span>
      ) : undefined}
    />
  );

  const cambiarCampo = <T extends keyof PoliticaCausadoCuerpo>(
    campo: T,
    valor: PoliticaCausadoCuerpo[T],
  ) => {
    setForm((actual) => ({ ...actual, [campo]: valor }));
    setCampoError((actual) => ({ ...actual, [campo]: "" }));
  };

  const anadirDocumento = () => {
    setDocumentos((actual) => [
      ...actual,
      { document_type_id: "", obligatorio: false, etapa: "PREPARACION", condicion: "" },
    ]);
  };

  const quitarDocumento = (indice: number) => {
    setDocumentos((actual) => actual.filter((_, posicion) => posicion !== indice));
  };

  const cambiarDocumento = (indice: number, cambios: Partial<DocumentoFila>) => {
    setDocumentos((actual) =>
      actual.map((documento, posicion) =>
        posicion === indice ? { ...documento, ...cambios } : documento,
      ),
    );
  };

  const mostrarError = (error: unknown) => {
    if (error instanceof ApiError) {
      if (error.fieldErrors) {
        const errores: Record<string, string> = {};
        for (const [campo, mensajes] of Object.entries(error.fieldErrors)) {
          errores[campo] = Array.isArray(mensajes) ? mensajes.join(" ") : String(mensajes);
        }
        setCampoError(errores);
      }
      setFormError(error.message);
    } else {
      setFormError("No fue posible completar la operación.");
    }
  };

  const guardar = async () => {
    if (guardando || !formularioValido) return;
    setGuardando(true);
    setFormError(null);
    setCampoError({});
    try {
      if (esNueva) {
        const creada = await apiFetch<PoliticaCausado>("/gobierno/presupuesto/politicas-causado", {
          method: "POST",
          body: cuerpoFormulario,
        });
        notify({ type: "success", title: "Política registrada en borrador" });
        await queryClient.invalidateQueries({ queryKey: [...CONSULTA_CAUSADOS] });
        navigate(`${RUTA_POLITICAS}/${creada.id}`, { replace: true });
      } else if (detalle.data) {
        await apiFetch<PoliticaCausado>(
          `/gobierno/presupuesto/politicas-causado/${detalle.data.id}`,
          {
            method: "PUT",
            body: cuerpoFormulario,
            ifMatch: String(detalle.data.version),
          },
        );
        notify({ type: "success", title: "Política actualizada" });
        setEditando(false);
        await queryClient.invalidateQueries({ queryKey: [...CONSULTA_CAUSADOS] });
        await detalle.refetch();
      }
    } catch (error) {
      mostrarError(error);
    } finally {
      setGuardando(false);
    }
  };

  const abrirActivacion = () => {
    setFundamentoActivacion("");
    setActoActivacion("");
    setErrorActivacion(null);
    setDialogoActivarAbierto(true);
  };

  const activar = async () => {
    if (activando || !detalle.data) return;
    const fundamento = fundamentoActivacion.trim();
    if (fundamento.length < 20 || fundamento.length > 2000) {
      setErrorActivacion("El fundamento debe tener entre 20 y 2000 caracteres.");
      return;
    }
    setActivando(true);
    setErrorActivacion(null);
    try {
      await apiFetch<PoliticaCausado>(
        `/gobierno/presupuesto/politicas-causado/${detalle.data.id}/activar`,
        {
          method: "POST",
          body: { fundamento, act_id: actoActivacion.trim() || undefined },
          ifMatch: String(detalle.data.version),
        },
      );
      notify({ type: "success", title: "Política activada" });
      setDialogoActivarAbierto(false);
      await queryClient.invalidateQueries({ queryKey: [...CONSULTA_CAUSADOS] });
      await detalle.refetch();
    } catch (error) {
      mostrarError(error);
      setErrorActivacion(error instanceof ApiError ? error.message : "No fue posible activar la política.");
    } finally {
      setActivando(false);
    }
  };

  const abrirCierre = () => {
    setMotivoCierre("");
    setDialogoCerrarAbierto(true);
  };

  const cerrar = async () => {
    if (cerrando || !detalle.data) return;
    const motivo = motivoCierre.trim();
    if (motivo.length < 10 || motivo.length > 500) return;
    setCerrando(true);
    try {
      await apiFetch<PoliticaCausado>(
        `/gobierno/presupuesto/politicas-causado/${detalle.data.id}/cerrar`,
        {
          method: "POST",
          body: { motivo },
          ifMatch: String(detalle.data.version),
        },
      );
      notify({ type: "success", title: "Política cerrada" });
      setDialogoCerrarAbierto(false);
      await queryClient.invalidateQueries({ queryKey: [...CONSULTA_CAUSADOS] });
      await detalle.refetch();
    } catch (error) {
      mostrarError(error);
    } finally {
      setCerrando(false);
    }
  };

  if (!puedeVer && !esNueva) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState title="Sin acceso" description="No tiene permiso para ver esta política." />
      </PageContent>
    );
  }

  if (esNueva && !puedeGestionar) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState title="Sin acceso" description="No tiene permiso para crear políticas de causado." />
      </PageContent>
    );
  }

  if (!esNueva && detalle.isLoading) {
    return (
      <PageContent>
        {cabecera}
        <LoadingState label="Cargando política…" />
      </PageContent>
    );
  }

  if (!esNueva && detalle.isError) {
    const error = detalle.error;
    if (error instanceof ApiError && error.status === 404) {
      return (
        <PageContent>
          {cabecera}
          <EmptyState title="Política no encontrada" description="La política solicitada no existe." />
        </PageContent>
      );
    }
    if (error instanceof ApiError && error.status === 403) {
      return (
        <PageContent>
          {cabecera}
          <EmptyState title="Sin acceso" description="No tiene permiso para ver esta política." />
        </PageContent>
      );
    }
    return (
      <PageContent>
        {cabecera}
        <ErrorState
          message="No fue posible cargar la política."
          onRetry={() => void detalle.refetch()}
        />
      </PageContent>
    );
  }

  if (!esNueva && !detalle.data) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState title="Política no encontrada" description="La política solicitada no existe." />
      </PageContent>
    );
  }

  if (esNueva && tiposDocumento.isLoading) {
    return (
      <PageContent>
        {cabecera}
        <LoadingState label="Cargando documentos…" />
      </PageContent>
    );
  }

  if (esNueva && tiposDocumento.isError) {
    return (
      <PageContent>
        {cabecera}
        <ErrorState
          message="No fue posible cargar los tipos de documento."
          onRetry={() => void tiposDocumento.refetch()}
        />
      </PageContent>
    );
  }

  if (editando || esNueva) {
    return (
      <PageContent>
        {cabecera}
        {formError ? (
          <div
            role="alert"
            className="mb-4 rounded-md border border-danger-300 bg-danger-50 px-3 py-2 text-sm text-danger-700"
          >
            {formError}
          </div>
        ) : null}
        <form
          className="grid gap-5"
          onSubmit={(evento) => {
            evento.preventDefault();
            void guardar();
          }}
        >
          <FormField
            label="Código"
            htmlFor="codigo"
            required
            error={campoError.codigo}
          >
            <TextInput
              id="codigo"
              value={form.codigo}
              onChange={(evento) => cambiarCampo("codigo", evento.target.value)}
              placeholder="POL-OBRAS-01"
            />
          </FormField>

          <FormField
            label="Tipo de gasto"
            htmlFor="tipo-gasto"
            required
            error={campoError.tipo_gasto}
            help="Código que el ente usa para agrupar gastos, p. ej. OBRAS"
          >
            <TextInput
              id="tipo-gasto"
              value={form.tipo_gasto}
              onChange={(evento) => cambiarCampo("tipo_gasto", evento.target.value)}
              placeholder="OBRAS"
            />
          </FormField>

          <FormField label="Nombre" htmlFor="nombre" required error={campoError.nombre}>
            <TextInput
              id="nombre"
              value={form.nombre}
              onChange={(evento) => cambiarCampo("nombre", evento.target.value)}
              placeholder="Política para obras"
            />
          </FormField>

          <FormField label="Descripción" htmlFor="descripcion" error={campoError.descripcion}>
            <TextInput
              id="descripcion"
              value={form.descripcion ?? ""}
              onChange={(evento) => cambiarCampo("descripcion", evento.target.value)}
              placeholder="Opcional"
            />
          </FormField>

          <FormField label="Disparador" htmlFor="disparador" required error={campoError.disparador}>
            <select
              id="disparador"
              className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              value={form.disparador}
              onChange={(evento) => cambiarCampo("disparador", evento.target.value as Disparador)}
            >
              {Object.entries(DISPARADORES).map(([valor, etiqueta]) => (
                <option key={valor} value={valor}>
                  {etiqueta}
                </option>
              ))}
            </select>
          </FormField>

          <fieldset className="grid gap-3">
            <legend className="text-sm font-medium text-text-700">Exigencias previas</legend>
            <label className="flex items-center gap-2 text-sm text-text-700">
              <input
                type="checkbox"
                checked={form.requiere_recepcion}
                onChange={(e) => cambiarCampo("requiere_recepcion", e.target.checked)}
              />
              Requiere recepción conforme
            </label>
            <label className="flex items-center gap-2 text-sm text-text-700">
              <input
                type="checkbox"
                checked={form.requiere_valuacion}
                onChange={(e) => cambiarCampo("requiere_valuacion", e.target.checked)}
              />
              Requiere valuación conformada
            </label>
            <label className="flex items-center gap-2 text-sm text-text-700">
              <input
                type="checkbox"
                checked={form.requiere_conformidad}
                onChange={(e) => cambiarCampo("requiere_conformidad", e.target.checked)}
              />
              Requiere conformidad
            </label>
          </fieldset>

          <div className="grid gap-4 sm:grid-cols-2">
            <FormField label="Competencia · Acción" htmlFor="competencia-accion" required error={campoError.competencia_accion}>
              <select
                id="competencia-accion"
                className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                value={form.competencia_accion}
                onChange={(evento) => cambiarCampo("competencia_accion", evento.target.value as AccionCompetencia)}
              >
                {Object.entries(ACCIONES_COMPETENCIA).map(([valor, etiqueta]) => (
                  <option key={valor} value={valor}>
                    {etiqueta}
                  </option>
                ))}
              </select>
            </FormField>
            <FormField label="Competencia · Materia" htmlFor="competencia-materia" required error={campoError.competencia_materia}>
              <select
                id="competencia-materia"
                className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                value={form.competencia_materia}
                onChange={(evento) => cambiarCampo("competencia_materia", evento.target.value as MateriaCompetencia)}
              >
                {Object.entries(MATERIAS_COMPETENCIA).map(([valor, etiqueta]) => (
                  <option key={valor} value={valor}>
                    {etiqueta}
                  </option>
                ))}
              </select>
            </FormField>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <FormField label="Vigente desde" htmlFor="vigente-desde" required error={campoError.vigente_desde}>
              <TextInput
                id="vigente-desde"
                type="date"
                value={form.vigente_desde}
                onChange={(evento) => cambiarCampo("vigente_desde", evento.target.value)}
              />
            </FormField>
            <FormField label="Vigente hasta" htmlFor="vigente-hasta" error={campoError.vigente_hasta}>
              <TextInput
                id="vigente-hasta"
                type="date"
                value={form.vigente_hasta ?? ""}
                onChange={(evento) => cambiarCampo("vigente_hasta", evento.target.value)}
              />
            </FormField>
          </div>

          <FormField label="Tipo de regla" htmlFor="tipo-regla" required error={campoError.tipo_regla}>
            <select
              id="tipo-regla"
              className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              value={form.tipo_regla ?? "INSTITUTIONAL_POLICY"}
              onChange={(evento) => cambiarCampo("tipo_regla", evento.target.value as TipoReglaCausado)}
            >
              {Object.entries(TIPOS_REGLA).map(([valor, etiqueta]) => (
                <option key={valor} value={valor}>
                  {etiqueta}
                </option>
              ))}
            </select>
          </FormField>

          <FormField label="Fundamento" htmlFor="fundamento" error={campoError.fundamento}>
            <textarea
              id="fundamento"
              className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              rows={3}
              value={form.fundamento ?? ""}
              onChange={(evento) => cambiarCampo("fundamento", evento.target.value)}
            />
          </FormField>

          <FormField label="Acto administrativo (id)" htmlFor="acto-admin" error={campoError.act_id}>
            <TextInput
              id="acto-admin"
              value={form.act_id ?? ""}
              onChange={(evento) => cambiarCampo("act_id", evento.target.value)}
              placeholder="Opcional"
            />
          </FormField>

          <section aria-labelledby="documentos-titulo" className="grid gap-3">
            <div className="flex items-center justify-between">
              <h2 id="documentos-titulo" className="text-sm font-medium text-text-700">
                Documentos exigidos
              </h2>
              <Button type="button" variant="secondary" size="sm" onClick={anadirDocumento}>
                Añadir documento
              </Button>
            </div>
            {documentos.length === 0 ? (
              <p className="text-sm text-text-600">Sin documentos exigidos.</p>
            ) : (
              <ul className="grid gap-3">
                {documentos.map((documento, indice) => (
                  <li
                    key={indice}
                    className="grid gap-3 rounded-md border border-border-subtle bg-surface-0 p-3 sm:grid-cols-[1fr_auto_auto_1fr_auto] sm:items-end"
                  >
                    <FormField
                      label="Tipo documental"
                      htmlFor={`documento-tipo-${indice}`}
                      required
                    >
                      <select
                        id={`documento-tipo-${indice}`}
                        className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                        value={documento.document_type_id}
                        onChange={(evento) =>
                          cambiarDocumento(indice, { document_type_id: evento.target.value })
                        }
                      >
                        <option value="">Seleccione…</option>
                        {(tiposDocumento.data ?? []).map((tipo) => (
                          <option key={tipo.id} value={tipo.id}>
                            {tipo.name}
                          </option>
                        ))}
                      </select>
                    </FormField>
                    <label className="flex items-center gap-2 text-sm text-text-700">
                      <input
                        type="checkbox"
                        checked={documento.obligatorio}
                        onChange={(e) => cambiarDocumento(indice, { obligatorio: e.target.checked })}
                      />
                      Obligatorio
                    </label>
                    <FormField label="Etapa" htmlFor={`documento-etapa-${indice}`}>
                      <select
                        id={`documento-etapa-${indice}`}
                        className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                        value={documento.etapa}
                        onChange={(evento) =>
                          cambiarDocumento(indice, {
                            etapa: evento.target.value as EtapaDocumentoCausado,
                          })
                        }
                      >
                        {Object.entries(ETAPAS).map(([valor, etiqueta]) => (
                          <option key={valor} value={valor}>
                            {etiqueta}
                          </option>
                        ))}
                      </select>
                    </FormField>
                    <FormField label="Condición" htmlFor={`documento-condicion-${indice}`}>
                      <TextInput
                        id={`documento-condicion-${indice}`}
                        value={documento.condicion}
                        onChange={(evento) =>
                          cambiarDocumento(indice, { condicion: evento.target.value })
                        }
                        placeholder="Opcional"
                      />
                    </FormField>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => quitarDocumento(indice)}
                      aria-label={`Quitar documento ${indice + 1}`}
                    >
                      Quitar
                    </Button>
                  </li>
                ))}
              </ul>
            )}
            {disparadorDocumentalInvalido ? (
              <p role="alert" className="text-sm text-danger-700">
                Si el disparador es «Solo documentos exigidos», al menos un documento debe ser obligatorio.
              </p>
            ) : null}
          </section>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="submit"
              variant="primary"
              disabled={guardando || !formularioValido}
            >
              {guardando ? "Guardando…" : "Guardar"}
            </Button>
            {!esNueva ? (
              <Button type="button" variant="secondary" onClick={() => setEditando(false)}>
                Cancelar
              </Button>
            ) : (
              <Link
                to={RUTA_POLITICAS}
                className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
              >
                Cancelar
              </Link>
            )}
          </div>
        </form>
      </PageContent>
    );
  }

  const politica = detalle.data!;
  const puedeEditar = politica.estado === "BORRADOR" && puedeGestionar;
  const puedeActivar = politica.estado === "BORRADOR" && puedeGestionar;
  const puedeCerrar = politica.estado === "VIGENTE" && puedeGestionar;

  return (
    <PageContent>
      {cabecera}

      {formError ? (
        <div
          role="alert"
          className="mb-4 rounded-md border border-danger-300 bg-danger-50 px-3 py-2 text-sm text-danger-700"
        >
          {formError}
        </div>
      ) : null}

      <dl className="mt-6 grid gap-4 border-t border-border-subtle pt-4">
        <div className="grid gap-1 sm:grid-cols-[220px_1fr]">
          <dt className="text-sm font-medium text-text-700">Código</dt>
          <dd className="text-sm text-text-900">{politica.codigo}</dd>
        </div>
        <div className="grid gap-1 sm:grid-cols-[220px_1fr]">
          <dt className="text-sm font-medium text-text-700">Tipo de gasto</dt>
          <dd className="text-sm text-text-900">{politica.tipo_gasto}</dd>
        </div>
        <div className="grid gap-1 sm:grid-cols-[220px_1fr]">
          <dt className="text-sm font-medium text-text-700">Nombre</dt>
          <dd className="text-sm text-text-900">{politica.nombre}</dd>
        </div>
        {politica.descripcion ? (
          <div className="grid gap-1 sm:grid-cols-[220px_1fr]">
            <dt className="text-sm font-medium text-text-700">Descripción</dt>
            <dd className="text-sm text-text-900">{politica.descripcion}</dd>
          </div>
        ) : null}
        <div className="grid gap-1 sm:grid-cols-[220px_1fr]">
          <dt className="text-sm font-medium text-text-700">Disparador</dt>
          <dd className="text-sm text-text-900">{DISPARADORES[politica.disparador]}</dd>
        </div>
        <div className="grid gap-1 sm:grid-cols-[220px_1fr]">
          <dt className="text-sm font-medium text-text-700">Exigencias previas</dt>
          <dd className="text-sm text-text-900">
            {[
              politica.requiere_recepcion ? "Recepción conforme" : null,
              politica.requiere_valuacion ? "Valuación conformada" : null,
              politica.requiere_conformidad ? "Conformidad" : null,
            ]
              .filter(Boolean)
              .join(" · ") || "Ninguna"}
          </dd>
        </div>
        <div className="grid gap-1 sm:grid-cols-[220px_1fr]">
          <dt className="text-sm font-medium text-text-700">Competencia</dt>
          <dd className="text-sm text-text-900">
            {ACCIONES_COMPETENCIA[politica.competencia_accion]} · {MATERIAS_COMPETENCIA[politica.competencia_materia]}
          </dd>
        </div>
        <div className="grid gap-1 sm:grid-cols-[220px_1fr]">
          <dt className="text-sm font-medium text-text-700">Vigencia</dt>
          <dd className="text-sm text-text-900">
            {formatearFechaDeNegocio(politica.vigente_desde)}
            {politica.vigente_hasta ? ` – ${formatearFechaDeNegocio(politica.vigente_hasta)}` : " – Sin fecha de fin"}
          </dd>
        </div>
        <div className="grid gap-1 sm:grid-cols-[220px_1fr]">
          <dt className="text-sm font-medium text-text-700">Tipo de regla</dt>
          <dd className="text-sm text-text-900">{TIPOS_REGLA[politica.tipo_regla]}</dd>
        </div>
        {politica.fundamento ? (
          <div className="grid gap-1 sm:grid-cols-[220px_1fr]">
            <dt className="text-sm font-medium text-text-700">Fundamento</dt>
            <dd className="text-sm text-text-900">{politica.fundamento}</dd>
          </div>
        ) : null}
        {politica.act_id ? (
          <div className="grid gap-1 sm:grid-cols-[220px_1fr]">
            <dt className="text-sm font-medium text-text-700">Acto administrativo</dt>
            <dd className="text-sm text-text-900">
              {politica.acto ? `${politica.acto} (${politica.act_id})` : politica.act_id}
            </dd>
          </div>
        ) : null}
        <div className="grid gap-1 sm:grid-cols-[220px_1fr]">
          <dt className="text-sm font-medium text-text-700">Estado</dt>
          <dd className="text-sm text-text-900">{ESTADOS_POLITICA[politica.estado]}</dd>
        </div>
      </dl>

      <section aria-labelledby="documentos-politica" className="mt-6">
        <h2 id="documentos-politica" className="text-lg font-semibold text-text-900">
          Documentos exigidos
        </h2>
        {politica.documentos.length === 0 ? (
          <p className="mt-1 text-sm text-text-600">Sin documentos exigidos.</p>
        ) : (
          <ul className="mt-2 grid gap-2">
            {politica.documentos.map((documento) => (
              <li key={documento.id} className="rounded-md border border-border-subtle bg-surface-0 p-3 text-sm text-text-900">
                <span className="font-medium">{documento.tipo_documental}</span>
                <span className="text-text-600"> · {ETAPAS[documento.etapa]}</span>
                {documento.obligatorio ? <span className="text-text-600"> · Obligatorio</span> : null}
                {documento.condicion ? <span className="text-text-600"> · {documento.condicion}</span> : null}
              </li>
            ))}
          </ul>
        )}
      </section>

      {politica.historia && politica.historia.length > 0 ? (
        <section aria-labelledby="historia-politica" className="mt-6">
          <h2 id="historia-politica" className="text-lg font-semibold text-text-900">
            Historia
          </h2>
          <ul className="mt-2 grid gap-2">
            {politica.historia.map((evento) => (
              <li key={`${evento.evento}-${evento.version}`} className="rounded-md border border-border-subtle bg-surface-0 p-3 text-sm text-text-900">
                <span className="font-medium">{evento.evento}</span>
                <span className="text-text-600"> · versión {evento.version}</span>
                <span className="text-text-600"> · {formatearFechaDeNegocio(evento.fecha)}</span>
                <span className="text-text-600"> · {evento.actor}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <div className="mt-6 flex flex-wrap items-center gap-2">
        {puedeEditar ? (
          <Button type="button" variant="primary" onClick={() => setEditando(true)}>
            Editar
          </Button>
        ) : null}
        {puedeActivar ? (
          <Button type="button" variant="primary" onClick={abrirActivacion}>
            Activar
          </Button>
        ) : null}
        {puedeCerrar ? (
          <Button type="button" variant="danger" onClick={abrirCierre}>
            Cerrar
          </Button>
        ) : null}
        <Link
          to={RUTA_POLITICAS}
          className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
        >
          Volver
        </Link>
      </div>

      <ConfirmationDialog
        open={dialogoActivarAbierto}
        title="Activar la política"
        description="Confirme que desea activar esta política."
        confirmLabel="Activar"
        cancelLabel="Cancelar"
        onConfirm={activar}
        onCancel={() => setDialogoActivarAbierto(false)}
      >
        <div className="grid gap-3">
          <FormField
            label="Fundamento"
            htmlFor="fundamento-activacion"
            required
            error={errorActivacion ?? undefined}
          >
            <textarea
              id="fundamento-activacion"
              className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              rows={3}
              value={fundamentoActivacion}
              onChange={(evento) => {
                setFundamentoActivacion(evento.target.value);
                setErrorActivacion(null);
              }}
              minLength={20}
              maxLength={2000}
            />
          </FormField>
          <FormField label="Acto administrativo (id)" htmlFor="acto-activacion">
            <TextInput
              id="acto-activacion"
              value={actoActivacion}
              onChange={(evento) => setActoActivacion(evento.target.value)}
              placeholder="Opcional"
            />
          </FormField>
        </div>
      </ConfirmationDialog>

      <ConfirmationDialog
        open={dialogoCerrarAbierto}
        title="Cerrar la política"
        description="Confirme que desea cerrar esta política."
        confirmLabel="Cerrar"
        cancelLabel="Cancelar"
        danger
        onConfirm={cerrar}
        onCancel={() => setDialogoCerrarAbierto(false)}
      >
        <FormField label="Motivo" htmlFor="motivo-cierre" required>
          <textarea
            id="motivo-cierre"
            className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
            rows={3}
            value={motivoCierre}
            onChange={(evento) => setMotivoCierre(evento.target.value)}
            minLength={10}
            maxLength={500}
          />
        </FormField>
      </ConfirmationDialog>
    </PageContent>
  );
}