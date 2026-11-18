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
import { formatearFechaDeNegocio, formatearInstante, hoyDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_POLITICAS_OP,
  RUTA_POLITICAS_OP,
  type PoliticaOrdenPago,
  type PoliticaCreateBody,
  type PoliticaDocumentoBody,
} from "./api";

const FECHA_HOY = hoyDeNegocio();

const ETAPA_FIJA = "EMISION";
const COMPETENCIA_ACCION = "ORDENAR_PAGO";
const COMPETENCIA_MATERIA = "TESORERIA";

const ESTADOS_POLITICA: Record<PoliticaOrdenPago["estado"], string> = {
  BORRADOR: "Borrador",
  VIGENTE: "Vigente",
  CERRADA: "Cerrada",
};

const TIPOS_REGLA: Array<{ valor: string; etiqueta: string }> = [
  { valor: "INSTITUTIONAL_POLICY", etiqueta: "Política institucional" },
  { valor: "OPERATIONAL_CONFIGURATION", etiqueta: "Configuración operativa" },
  { valor: "LEGAL_MANDATORY", etiqueta: "Mandato legal" },
];

interface DocumentoFila {
  document_type_id: string;
  obligatorio: boolean;
  etapa: string;
  condicion: string;
}

interface DocumentoReal {
  document_type_id: string;
  obligatorio: boolean;
  etapa: string;
  condicion: string | null;
  tipo?: string | null;
}

function esDocumentoReal(valor: unknown): valor is DocumentoReal {
  if (typeof valor !== "object" || valor === null) return false;
  const objeto = valor as Record<string, unknown>;
  return (
    typeof objeto.document_type_id === "string" &&
    typeof objeto.obligatorio === "boolean" &&
    typeof objeto.etapa === "string" &&
    (objeto.condicion === null || typeof objeto.condicion === "string")
  );
}

function convertirDocumentos(documentos: unknown[]): DocumentoFila[] {
  return documentos
    .filter(esDocumentoReal)
    .map((documento) => ({
      document_type_id: documento.document_type_id,
      obligatorio: documento.obligatorio,
      etapa: documento.etapa,
      condicion: documento.condicion ?? "",
    }));
}

interface TipoDocumento {
  id: string;
  nombre: string;
  codigo?: string | null;
}

interface CuerpoPolitica {
  codigo: string;
  nombre: string;
  descripcion: string;
  tipo_gasto: string;
  requiere_expediente_completo: boolean;
  vigente_desde: string;
  vigente_hasta: string;
  fundamento: string;
  tipo_regla: string;
}

function esCuerpoValido(cuerpo: CuerpoPolitica, documentos: DocumentoFila[]): boolean {
  if (!/^[A-Z0-9][A-Z0-9_-]{1,19}$/.test(cuerpo.codigo)) return false;
  if (cuerpo.nombre.trim().length < 3 || cuerpo.nombre.trim().length > 200) return false;
  if (cuerpo.tipo_gasto && !/^[A-Z0-9_]{2,40}$/.test(cuerpo.tipo_gasto)) return false;
  if (!cuerpo.vigente_desde) return false;
  if (cuerpo.vigente_hasta && cuerpo.vigente_hasta < cuerpo.vigente_desde) return false;
  if (!cuerpo.tipo_regla) return false;
  return documentos.every((documento) => documento.document_type_id);
}

export function PoliticaOrdenPagoPage() {
  const { politicaId } = useParams<{ politicaId: string }>();
  const navigate = useNavigate();
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();
  const esNueva = politicaId === undefined;
  const puedeGestionar = tiene("gobierno_ordenes_pago:policy", "empresa");
  const puedeVer = tiene("gobierno_ordenes_pago:view", "empresa");

  const [editando, setEditando] = useState(esNueva);
  const [guardando, setGuardando] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [campoError, setCampoError] = useState<Record<string, string>>({});
  const [form, setForm] = useState<CuerpoPolitica>({
    codigo: "",
    nombre: "",
    descripcion: "",
    tipo_gasto: "",
    requiere_expediente_completo: false,
    vigente_desde: FECHA_HOY,
    vigente_hasta: "",
    fundamento: "",
    tipo_regla: "INSTITUTIONAL_POLICY",
  });
  const [documentos, setDocumentos] = useState<DocumentoFila[]>([]);

  const [dialogoActivarAbierto, setDialogoActivarAbierto] = useState(false);
  const [fundamentoActivacion, setFundamentoActivacion] = useState("");
  const [errorActivacion, setErrorActivacion] = useState<string | null>(null);
  const [activando, setActivando] = useState(false);

  const [dialogoCerrarAbierto, setDialogoCerrarAbierto] = useState(false);
  const [motivoCierre, setMotivoCierre] = useState("");
  const [errorCierre, setErrorCierre] = useState<string | null>(null);
  const [cerrando, setCerrando] = useState(false);

  const detalle = useQuery({
    queryKey: [CONSULTA_POLITICAS_OP, "politica", activeCompanyId, politicaId],
    queryFn: () => apiFetch<PoliticaOrdenPago>(`${RUTA_POLITICAS_OP}/${politicaId}`),
    enabled: Boolean(activeCompanyId) && !esNueva && puedeVer && politicaId !== undefined,
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
        nombre: detalle.data.nombre,
        descripcion: detalle.data.descripcion ?? "",
        tipo_gasto: detalle.data.tipo_gasto ?? "",
        requiere_expediente_completo: detalle.data.requiere_expediente_completo,
        vigente_desde: detalle.data.vigente_desde?.slice(0, 10) ?? FECHA_HOY,
        vigente_hasta: detalle.data.vigente_hasta?.slice(0, 10) ?? "",
        fundamento: detalle.data.fundamento ?? "",
        tipo_regla: detalle.data.tipo_regla ?? "INSTITUTIONAL_POLICY",
      });
      setDocumentos(convertirDocumentos(detalle.data.documentos));
    }
  }, [detalle.data, esNueva, editando]);

  const cuerpoFormulario: PoliticaCreateBody = useMemo(
    () => ({
      codigo: form.codigo,
      nombre: form.nombre,
      descripcion: form.descripcion || null,
      tipo_gasto: form.tipo_gasto || null,
      requiere_expediente_completo: form.requiere_expediente_completo,
      competencia_accion: COMPETENCIA_ACCION,
      competencia_materia: COMPETENCIA_MATERIA,
      vigente_desde: form.vigente_desde,
      vigente_hasta: form.vigente_hasta || null,
      fundamento: form.fundamento || null,
      tipo_regla: form.tipo_regla,
      documentos: documentos.map(
        (documento): PoliticaDocumentoBody => ({
          document_type_id: documento.document_type_id,
          obligatorio: documento.obligatorio,
          etapa: ETAPA_FIJA,
          condicion: documento.condicion || null,
        }),
      ),
    }),
    [form, documentos],
  );

  const formularioValido = esCuerpoValido(form, documentos);

  const cabecera = (
    <PageHeader
      crumbs={[
        { label: "Gobierno" },
        { label: "Políticas de orden de pago", to: RUTA_POLITICAS_OP },
        { label: esNueva ? "Nueva política" : detalle.data?.codigo ?? "Política" },
      ]}
      title={esNueva ? "Nueva política de orden de pago" : detalle.data?.nombre ?? "Política de orden de pago"}
      description={
        esNueva
          ? "Registre una política para definir qué se exige al ordenar el pago de un tipo de gasto."
          : `Código: ${detalle.data?.codigo ?? ""}`
      }
      status={
        detalle.data ? (
          <span className="rounded bg-surface-100 px-2 py-0.5 text-xs font-medium text-text-700">
            {ESTADOS_POLITICA[detalle.data.estado]}
          </span>
        ) : undefined
      }
    />
  );

  const cambiarCampo = <T extends keyof CuerpoPolitica>(campo: T, valor: CuerpoPolitica[T]) => {
    setForm((actual) => ({ ...actual, [campo]: valor }));
    setCampoError((actual) => ({ ...actual, [campo]: "" }));
  };

  const anadirDocumento = () => {
    setDocumentos((actual) => [
      ...actual,
      { document_type_id: "", obligatorio: false, etapa: ETAPA_FIJA, condicion: "" },
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
        const creada = await apiFetch<PoliticaOrdenPago>(RUTA_POLITICAS_OP, {
          method: "POST",
          body: cuerpoFormulario,
        });
        notify({ type: "success", title: "Política registrada en borrador" });
        await queryClient.invalidateQueries({ queryKey: [CONSULTA_POLITICAS_OP] });
        setEditando(false);
        navigate(`${RUTA_POLITICAS_OP}/${creada.id}`, { replace: true });
      } else if (detalle.data) {
        await apiFetch<PoliticaOrdenPago>(`${RUTA_POLITICAS_OP}/${detalle.data.id}`, {
          method: "PUT",
          body: cuerpoFormulario,
          ifMatch: String(detalle.data.version),
        });
        notify({ type: "success", title: "Política actualizada" });
        setEditando(false);
        await queryClient.invalidateQueries({ queryKey: [CONSULTA_POLITICAS_OP] });
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
      await apiFetch<PoliticaOrdenPago>(`${RUTA_POLITICAS_OP}/${detalle.data.id}/activar`, {
        method: "POST",
        body: { fundamento },
        ifMatch: String(detalle.data.version),
      });
      notify({ type: "success", title: "Política activada" });
      setDialogoActivarAbierto(false);
      await queryClient.invalidateQueries({ queryKey: [CONSULTA_POLITICAS_OP] });
      await detalle.refetch();
    } catch (error) {
      mostrarError(error);
      setErrorActivacion(
        error instanceof ApiError ? error.message : "No fue posible activar la política.",
      );
    } finally {
      setActivando(false);
    }
  };

  const abrirCierre = () => {
    setMotivoCierre("");
    setErrorCierre(null);
    setDialogoCerrarAbierto(true);
  };

  const cerrar = async () => {
    if (cerrando || !detalle.data) return;
    const motivo = motivoCierre.trim();
    if (motivo.length < 10 || motivo.length > 500) {
      setErrorCierre("El motivo debe tener entre 10 y 500 caracteres.");
      return;
    }
    setCerrando(true);
    setErrorCierre(null);
    try {
      await apiFetch<PoliticaOrdenPago>(`${RUTA_POLITICAS_OP}/${detalle.data.id}/cerrar`, {
        method: "POST",
        body: { motivo },
        ifMatch: String(detalle.data.version),
      });
      notify({ type: "success", title: "Política cerrada" });
      setDialogoCerrarAbierto(false);
      await queryClient.invalidateQueries({ queryKey: [CONSULTA_POLITICAS_OP] });
      await detalle.refetch();
    } catch (error) {
      mostrarError(error);
      setErrorCierre(
        error instanceof ApiError ? error.message : "No fue posible cerrar la política.",
      );
    } finally {
      setCerrando(false);
    }
  };

  if (!puedeVer) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para ver las políticas de orden de pago."
        />
      </PageContent>
    );
  }

  if (detalle.isLoading) {
    return (
      <PageContent>
        {cabecera}
        <LoadingState label="Cargando política…" />
      </PageContent>
    );
  }

  if (detalle.isError) {
    const error = detalle.error;
    if (error instanceof ApiError && error.status === 403) {
      return (
        <PageContent>
          {cabecera}
          <EmptyState
            title="Sin acceso"
            description="No tiene permiso para ver esta política."
          />
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

  const puedeEditar = !esNueva && detalle.data?.estado === "BORRADOR" && !editando && puedeGestionar;
  const puedeActivar = !esNueva && detalle.data?.estado === "BORRADOR" && puedeGestionar;
  const puedeCerrar = !esNueva && detalle.data?.estado === "VIGENTE" && puedeGestionar;

  if (editando) {
    return (
      <PageContent>
        {cabecera}
        <form
          onSubmit={(evento) => {
            evento.preventDefault();
            void guardar();
          }}
          className="grid gap-5"
        >
          {formError ? (
            <div className="rounded-md border border-danger-200 bg-danger-50 px-3 py-2 text-sm text-danger-800">
              {formError}
            </div>
          ) : null}

          <div className="grid gap-4 md:grid-cols-2">
            <FormField
              label="Código"
              htmlFor="codigo-politica"
              required
              error={campoError.codigo}
              help="Letras mayúsculas, números, guiones y guiones bajos. Entre 2 y 20 caracteres."
            >
              <TextInput
                id="codigo-politica"
                value={form.codigo}
                onChange={(evento) => cambiarCampo("codigo", evento.target.value)}
                disabled={!esNueva}
              />
            </FormField>
            <FormField
              label="Nombre"
              htmlFor="nombre-politica"
              required
              error={campoError.nombre}
            >
              <TextInput
                id="nombre-politica"
                value={form.nombre}
                onChange={(evento) => cambiarCampo("nombre", evento.target.value)}
                placeholder="Política de orden de pago"
              />
            </FormField>
          </div>

          <FormField label="Descripción" htmlFor="descripcion-politica" error={campoError.descripcion}>
            <textarea
              id="descripcion-politica"
              className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              rows={4}
              value={form.descripcion}
              onChange={(evento) => cambiarCampo("descripcion", evento.target.value)}
            />
          </FormField>

          <div className="grid gap-4 md:grid-cols-2">
            <FormField
              label="Tipo de gasto"
              htmlFor="tipo-gasto-politica"
              error={campoError.tipo_gasto}
              help="Código opcional. Letras mayúsculas, números y guiones bajos."
            >
              <TextInput
                id="tipo-gasto-politica"
                value={form.tipo_gasto}
                onChange={(evento) => cambiarCampo("tipo_gasto", evento.target.value)}
                placeholder="BIENES"
              />
            </FormField>
            <FormField
              label="Tipo de regla"
              htmlFor="tipo-regla-politica"
              required
              error={campoError.tipo_regla}
            >
              <select
                id="tipo-regla-politica"
                className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                value={form.tipo_regla}
                onChange={(evento) => cambiarCampo("tipo_regla", evento.target.value)}
              >
                {TIPOS_REGLA.map((tipo) => (
                  <option key={tipo.valor} value={tipo.valor}>
                    {tipo.etiqueta}
                  </option>
                ))}
              </select>
            </FormField>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <FormField
              label="Vigente desde"
              htmlFor="vigente-desde-politica"
              required
              error={campoError.vigente_desde}
            >
              <TextInput
                id="vigente-desde-politica"
                type="date"
                value={form.vigente_desde}
                onChange={(evento) => cambiarCampo("vigente_desde", evento.target.value)}
              />
            </FormField>
            <FormField
              label="Vigente hasta"
              htmlFor="vigente-hasta-politica"
              error={campoError.vigente_hasta}
            >
              <TextInput
                id="vigente-hasta-politica"
                type="date"
                value={form.vigente_hasta}
                onChange={(evento) => cambiarCampo("vigente_hasta", evento.target.value)}
              />
            </FormField>
          </div>

          <FormField label="Fundamento" htmlFor="fundamento-politica" error={campoError.fundamento}>
            <textarea
              id="fundamento-politica"
              className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              rows={4}
              value={form.fundamento}
              onChange={(evento) => cambiarCampo("fundamento", evento.target.value)}
            />
          </FormField>

          <FormField label="Competencia" htmlFor="competencia-politica">
            <TextInput
              id="competencia-politica"
              value={`${COMPETENCIA_ACCION} · ${COMPETENCIA_MATERIA}`}
              disabled
            />
          </FormField>

          <div className="flex items-center gap-2">
            <input
              id="requiere-expediente-politica"
              type="checkbox"
              checked={form.requiere_expediente_completo}
              onChange={(evento) =>
                cambiarCampo("requiere_expediente_completo", evento.target.checked)
              }
              className="h-4 w-4 rounded border-border-default text-brand-600 focus:ring-brand-600"
            />
            <label htmlFor="requiere-expediente-politica" className="text-sm text-text-900">
              Exige expediente completo
            </label>
          </div>

          <section aria-labelledby="documentos-politica" className="grid gap-3">
            <div className="flex items-center justify-between">
              <h2 id="documentos-politica" className="text-lg font-semibold text-text-900">
                Documentos exigidos
              </h2>
              {documentos.length < 20 ? (
                <Button type="button" variant="secondary" onClick={anadirDocumento}>
                  Añadir documento
                </Button>
              ) : null}
            </div>
            {documentos.length === 0 ? (
              <p className="text-sm text-text-600">Sin documentos exigidos.</p>
            ) : (
              <ul className="grid gap-2">
                {documentos.map((documento, indice) => (
                  <li
                    key={indice}
                    className="grid gap-3 rounded-md border border-border-subtle bg-surface-0 p-3 sm:grid-cols-[1fr_auto_auto]"
                  >
                    <FormField
                      label={`Documento ${indice + 1}`}
                      htmlFor={`documento-tipo-${indice}`}
                    >
                      <select
                        id={`documento-tipo-${indice}`}
                        className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                        value={documento.document_type_id}
                        onChange={(evento) =>
                          cambiarDocumento(indice, { document_type_id: evento.target.value })
                        }
                      >
                        <option value="">Seleccione un tipo</option>
                        {(tiposDocumento.data ?? []).map((tipo) => (
                          <option key={tipo.id} value={tipo.id}>
                            {tipo.nombre}
                          </option>
                        ))}
                      </select>
                    </FormField>
                    <div className="flex items-end gap-2">
                      <label className="flex items-center gap-2 text-sm text-text-900">
                        <input
                          type="checkbox"
                          checked={documento.obligatorio}
                          onChange={(evento) =>
                            cambiarDocumento(indice, { obligatorio: evento.target.checked })
                          }
                          className="h-4 w-4 rounded border-border-default text-brand-600 focus:ring-brand-600"
                        />
                        Obligatorio
                      </label>
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() => quitarDocumento(indice)}
                      >
                        Quitar
                      </Button>
                    </div>
                    <FormField
                      label="Condición"
                      htmlFor={`documento-condicion-${indice}`}
                    >
                      <TextInput
                        id={`documento-condicion-${indice}`}
                        value={documento.condicion}
                        onChange={(evento) =>
                          cambiarDocumento(indice, { condicion: evento.target.value })
                        }
                        placeholder="Opcional"
                      />
                    </FormField>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            <Button type="submit" variant="primary" disabled={guardando || !formularioValido}>
              {guardando ? "Guardando…" : "Guardar"}
            </Button>
            <Button type="button" variant="secondary" onClick={() => setEditando(false)}>
              Cancelar
            </Button>
          </div>
        </form>
      </PageContent>
    );
  }

  if (!detalle.data) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState
          title="Política no encontrada"
          description="La política solicitada no existe."
        />
      </PageContent>
    );
  }

  const politica = detalle.data;

  return (
    <PageContent>
      {cabecera}

      <div className="grid gap-4 text-sm text-text-900">
        <div>
          <span className="font-medium">Código:</span> {politica.codigo}
        </div>
        <div>
          <span className="font-medium">Tipo de gasto:</span> {politica.tipo_gasto ?? "—"}
        </div>
        <div>
          <span className="font-medium">Tipo de regla:</span>{" "}
          {TIPOS_REGLA.find((tipo) => tipo.valor === politica.tipo_regla)?.etiqueta ??
            politica.tipo_regla}
        </div>
        <div>
          <span className="font-medium">Vigencia:</span>{" "}
          {formatearFechaDeNegocio(politica.vigente_desde)}
          {politica.vigente_hasta
            ? ` – ${formatearFechaDeNegocio(politica.vigente_hasta)}`
            : ""}
        </div>
        <div>
          <span className="font-medium">Exige expediente completo:</span>{" "}
          {politica.requiere_expediente_completo ? "Sí" : "No"}
        </div>
        <div>
          <span className="font-medium">Competencia:</span>{" "}
          {politica.competencia_accion} · {politica.competencia_materia}
        </div>
        {politica.descripcion ? (
          <div>
            <span className="font-medium">Descripción:</span> {politica.descripcion}
          </div>
        ) : null}
        {politica.fundamento ? (
          <div>
            <span className="font-medium">Fundamento:</span> {politica.fundamento}
          </div>
        ) : null}
        {politica.acto ? (
          <div>
            <span className="font-medium">Acto vinculado:</span> {politica.acto}
          </div>
        ) : null}
        {politica.motivo_cierre ? (
          <div>
            <span className="font-medium">Motivo de cierre:</span> {politica.motivo_cierre}
          </div>
        ) : null}
      </div>

      <section aria-labelledby="documentos-politica" className="mt-6">
        <h2 id="documentos-politica" className="text-lg font-semibold text-text-900">
          Documentos exigidos
        </h2>
        {convertirDocumentos(politica.documentos).length === 0 ? (
          <p className="mt-1 text-sm text-text-600">Sin documentos exigidos.</p>
        ) : (
          <ul className="mt-2 grid gap-2">
            {convertirDocumentos(politica.documentos).map((documento, indice) => (
              <li
                key={indice}
                className="rounded-md border border-border-subtle bg-surface-0 p-3 text-sm text-text-900"
              >
                <span className="font-medium">
                  {tiposDocumento.data?.find(
                    (tipo) => tipo.id === documento.document_type_id,
                  )?.nombre ?? documento.document_type_id}
                </span>
                <span className="text-text-600"> · {documento.etapa}</span>
                {documento.obligatorio ? (
                  <span className="text-text-600"> · Obligatorio</span>
                ) : null}
                {documento.condicion ? (
                  <span className="text-text-600"> · {documento.condicion}</span>
                ) : null}
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
              <li
                key={`${evento.evento}-${evento.version}`}
                className="rounded-md border border-border-subtle bg-surface-0 p-3 text-sm text-text-900"
              >
                <span className="font-medium">{evento.evento}</span>
                <span className="text-text-600"> · versión {evento.version}</span>
                <span className="text-text-600"> · {formatearInstante(evento.fecha)}</span>
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
          to={RUTA_POLITICAS_OP}
          className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
        >
          Volver
        </Link>
      </div>

      <ConfirmationDialog
        open={dialogoActivarAbierto}
        title="Activar la política"
        description="Confirme que desea activar esta política. El acto administrativo es opcional."
        confirmLabel="Activar"
        cancelLabel="Cancelar"
        onConfirm={activar}
        onCancel={() => setDialogoActivarAbierto(false)}
      >
        <FormField
          label="Fundamento de la activación"
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
        <FormField
          label="Motivo del cierre"
          htmlFor="motivo-cierre"
          required
          error={errorCierre ?? undefined}
        >
          <textarea
            id="motivo-cierre"
            className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
            rows={3}
            value={motivoCierre}
            onChange={(evento) => {
              setMotivoCierre(evento.target.value);
              setErrorCierre(null);
            }}
            minLength={10}
            maxLength={500}
          />
        </FormField>
      </ConfirmationDialog>
    </PageContent>
  );
}
