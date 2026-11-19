import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
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
  CONSULTA_POLITICAS_PAGO,
  CONSULTA_MEDIOS_PAGO,
  RUTA_POLITICAS_PAGO,
  RUTA_MEDIOS_PAGO,
  ACCIONES_COMPETENCIA,
  MATERIAS_COMPETENCIA,
  ESTADOS_POLITICA_PAGO,
  ETAPAS_DOCUMENTO_PAGO,
} from "./api";
import type {
  PoliticaPago,

  MedioPago,
  BandaPago,
  DocumentoPoliticaPago,
  ControlDuplicado,
  EtapaDocumentoPago,
} from "./api";

const FECHA_HOY = hoyDeNegocio();

const MONEDAS = [
  { valor: "VES", etiqueta: "VES" },
  { valor: "USD", etiqueta: "USD" },
  { valor: "EUR", etiqueta: "EUR" },
];

const TIPOS_REGLA = [
  { valor: "INSTITUTIONAL_POLICY", etiqueta: "Política institucional" },
  { valor: "OPERATIONAL_CONFIGURATION", etiqueta: "Configuración operativa" },
  { valor: "LEGAL_MANDATORY", etiqueta: "Mandato legal" },
];

interface FormPoliticaPago {
  codigo: string;
  nombre: string;
  descripcion: string;
  moneda: string;
  permite_pago_parcial: boolean;
  preparador_competencia_accion: string;
  preparador_competencia_materia: string;
  exige_cargo_autorizado_cuenta: boolean;
  control_duplicado: ControlDuplicado;
  vigente_desde: string;
  vigente_hasta: string;
  fundamento: string;
  tipo_regla: string;
}

interface BandaForm {
  monto_desde: string;
  monto_hasta: string;
  requisitos: { accion: string; materia: string; cantidad: number }[];
}

interface DocumentoForm {
  document_type_id: string;
  etapa: EtapaDocumentoPago;
  obligatorio: boolean;
}

function esCuerpoValido(
  form: FormPoliticaPago,
  bandas: BandaForm[],
  documentos: DocumentoForm[],
): boolean {
  if (!/^[A-Z0-9][A-Z0-9_-]{1,19}$/.test(form.codigo)) return false;
  if (form.nombre.trim().length < 3 || form.nombre.trim().length > 200) return false;
  if (!form.moneda) return false;
  if (!form.vigente_desde) return false;
  if (form.vigente_hasta && form.vigente_hasta < form.vigente_desde) return false;
  if (!form.tipo_regla) return false;

  if (
    bandas.some(
      (banda) =>
        banda.monto_desde === "" ||
        (banda.monto_hasta !== "" && Number(banda.monto_hasta) <= Number(banda.monto_desde)) ||
        banda.requisitos.length === 0 ||
        banda.requisitos.some(
          (r) => !r.accion || !r.materia || r.cantidad < 1 || r.cantidad > 5,
        ),
    )
  ) {
    return false;
  }
  if (documentos.some((doc) => !doc.document_type_id || !doc.etapa)) return false;
  return true;
}

function convertirBandas(bandas: BandaPago[]): BandaForm[] {
  if (!Array.isArray(bandas) || bandas.length === 0) {
    return [
      {
        monto_desde: "0",
        monto_hasta: "",
        requisitos: [{ accion: "PAGAR", materia: "TESORERIA", cantidad: 1 }],
      },
    ];
  }
  return bandas.map((banda) => ({
    monto_desde: banda.monto_desde,
    monto_hasta: banda.monto_hasta ?? "",
    requisitos: banda.requisitos.map((req) => ({
      accion: req.accion,
      materia: req.materia,
      cantidad: req.cantidad,
    })),
  }));
}

function convertirDocumentos(documentos: DocumentoPoliticaPago[]): DocumentoForm[] {
  if (!Array.isArray(documentos)) return [];
  return documentos.map((doc) => ({
    document_type_id: doc.document_type_id,
    etapa: doc.etapa,
    obligatorio: doc.obligatorio,
  }));
}

export function PoliticaPagoPage() {
  const { politicaId } = useParams<{ politicaId: string }>();
  const navigate = useNavigate();
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();
  const esNueva = politicaId === undefined;
  const puedeGestionar = tiene("gobierno_pagos:policy", "empresa");

  const detalle = useQuery({
    queryKey: [CONSULTA_POLITICAS_PAGO, "politica", politicaId],
    queryFn: () => apiFetch<PoliticaPago>(`${RUTA_POLITICAS_PAGO}/${politicaId}`),
    enabled: !esNueva && politicaId !== undefined,
    retry: false,
  });

  const medios = useQuery({
    queryKey: [CONSULTA_MEDIOS_PAGO],
    queryFn: () => apiFetch<MedioPago[]>(RUTA_MEDIOS_PAGO),
    enabled: puedeGestionar,
    retry: false,
  });

  const [editando, setEditando] = useState(esNueva);
  const [guardando, setGuardando] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [campoError, setCampoError] = useState<Record<string, string>>({});
  const [form, setForm] = useState<FormPoliticaPago>({
    codigo: "",
    nombre: "",
    descripcion: "",
    moneda: "VES",
    permite_pago_parcial: false,
    preparador_competencia_accion: "",
    preparador_competencia_materia: "",
    exige_cargo_autorizado_cuenta: false,
    control_duplicado: "ADVERTIR",
    vigente_desde: FECHA_HOY,
    vigente_hasta: "",
    fundamento: "",
    tipo_regla: "INSTITUTIONAL_POLICY",
  });
  const [mediosSeleccionados, setMediosSeleccionados] = useState<string[]>([]);
  const [bandas, setBandas] = useState<BandaForm[]>(convertirBandas([]));
  const [documentos, setDocumentos] = useState<DocumentoForm[]>([]);

  const [dialogoActivarAbierto, setDialogoActivarAbierto] = useState(false);
  const [fundamentoActivacion, setFundamentoActivacion] = useState("");
  const [errorActivacion, setErrorActivacion] = useState<string | null>(null);
  const [activando, setActivando] = useState(false);

  const [dialogoCerrarAbierto, setDialogoCerrarAbierto] = useState(false);
  const [motivoCierre, setMotivoCierre] = useState("");
  const [errorCierre, setErrorCierre] = useState<string | null>(null);
  const [cerrando, setCerrando] = useState(false);

  useEffect(() => {
    if (detalle.data && !esNueva && !editando) {
      setForm({
        codigo: detalle.data.codigo,
        nombre: detalle.data.nombre,
        descripcion: detalle.data.descripcion ?? "",
        moneda: detalle.data.moneda,
        permite_pago_parcial: detalle.data.permite_pago_parcial,
        preparador_competencia_accion: detalle.data.preparador_competencia_accion ?? "",
        preparador_competencia_materia: detalle.data.preparador_competencia_materia ?? "",
        exige_cargo_autorizado_cuenta: detalle.data.exige_cargo_autorizado_cuenta,
        control_duplicado: detalle.data.control_duplicado,
        vigente_desde: detalle.data.vigente_desde?.slice(0, 10) ?? FECHA_HOY,
        vigente_hasta: detalle.data.vigente_hasta?.slice(0, 10) ?? "",
        fundamento: detalle.data.fundamento ?? "",
        tipo_regla: detalle.data.tipo_regla,
      });
      setMediosSeleccionados(detalle.data.medios.map((m) => m.id));
      setBandas(convertirBandas(detalle.data.bandas));
      setDocumentos(convertirDocumentos(detalle.data.documentos));
    }
  }, [detalle.data, esNueva, editando]);

  const formularioValido = esCuerpoValido(form, bandas, documentos);

  const cambiarCampo = <T extends keyof FormPoliticaPago>(campo: T, valor: FormPoliticaPago[T]) => {
    setForm((actual) => ({ ...actual, [campo]: valor }));
    setCampoError((actual) => ({ ...actual, [campo]: "" }));
  };

  const alternarMedio = (medioId: string) => {
    setMediosSeleccionados((actual) =>
      actual.includes(medioId) ? actual.filter((id) => id !== medioId) : [...actual, medioId],
    );
  };

  const anadirBanda = () => {
    const desde = bandas.length > 0 ? bandas[bandas.length - 1].monto_hasta || "0" : "0";
    setBandas((actual) => [
      ...actual,
      {
        monto_desde: desde,
        monto_hasta: "",
        requisitos: [{ accion: "PAGAR", materia: "TESORERIA", cantidad: 1 }],
      },
    ]);
  };

  const quitarBanda = (indice: number) => {
    setBandas((actual) => actual.filter((_, posicion) => posicion !== indice));
  };

  const cambiarBanda = (indice: number, cambios: Partial<BandaForm>) => {
    setBandas((actual) =>
      actual.map((banda, posicion) => (posicion === indice ? { ...banda, ...cambios } : banda)),
    );
  };

  const anadirRequisito = (indiceBanda: number) => {
    setBandas((actual) =>
      actual.map((banda, posicion) =>
        posicion === indiceBanda
          ? {
              ...banda,
              requisitos: [
                ...banda.requisitos,
                { accion: "PAGAR", materia: "TESORERIA", cantidad: 1 },
              ],
            }
          : banda,
      ),
    );
  };

  const quitarRequisito = (indiceBanda: number, indiceRequisito: number) => {
    setBandas((actual) =>
      actual.map((banda, posicion) =>
        posicion === indiceBanda
          ? {
              ...banda,
              requisitos: banda.requisitos.filter((_, pos) => pos !== indiceRequisito),
            }
          : banda,
      ),
    );
  };

  const cambiarRequisito = (
    indiceBanda: number,
    indiceRequisito: number,
    cambios: Partial<{ accion: string; materia: string; cantidad: number }>,
  ) => {
    setBandas((actual) =>
      actual.map((banda, posicionBanda) =>
        posicionBanda === indiceBanda
          ? {
              ...banda,
              requisitos: banda.requisitos.map((requisito, posicionRequisito) =>
                posicionRequisito === indiceRequisito
                  ? { ...requisito, ...cambios }
                  : requisito,
              ),
            }
          : banda,
      ),
    );
  };

  const anadirDocumento = () => {
    setDocumentos((actual) => [
      ...actual,
      { document_type_id: "", etapa: "PREPARAR", obligatorio: false },
    ]);
  };

  const quitarDocumento = (indice: number) => {
    setDocumentos((actual) => actual.filter((_, posicion) => posicion !== indice));
  };

  const cambiarDocumento = (indice: number, cambios: Partial<DocumentoForm>) => {
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
    const cuerpo = {
      codigo: form.codigo,
      nombre: form.nombre,
      descripcion: form.descripcion || null,
      moneda: form.moneda,
      permite_pago_parcial: form.permite_pago_parcial,
      preparador_competencia_accion: form.preparador_competencia_accion || null,
      preparador_competencia_materia: form.preparador_competencia_materia || null,
      exige_cargo_autorizado_cuenta: form.exige_cargo_autorizado_cuenta,
      control_duplicado: form.control_duplicado,
      vigente_desde: form.vigente_desde,
      vigente_hasta: form.vigente_hasta || null,
      fundamento: form.fundamento || null,
      tipo_regla: form.tipo_regla,
      medios: mediosSeleccionados,
      bandas: bandas.map((banda) => ({
        monto_desde: banda.monto_desde,
        monto_hasta: banda.monto_hasta || null,
        requisitos: banda.requisitos.map((req) => ({
          accion: req.accion,
          materia: req.materia,
          cantidad: req.cantidad,
        })),
      })),
      documentos: documentos.map((doc) => ({
        document_type_id: doc.document_type_id,
        etapa: doc.etapa,
        obligatorio: doc.obligatorio,
      })),
    };
    try {
      if (esNueva) {
        const creada = await apiFetch<PoliticaPago>(RUTA_POLITICAS_PAGO, {
          method: "POST",
          body: cuerpo,
        });
        notify({ type: "success", title: "Política registrada en borrador" });
        await queryClient.invalidateQueries({ queryKey: [CONSULTA_POLITICAS_PAGO] });
        navigate(`${RUTA_POLITICAS_PAGO}/${creada.id}`, { replace: true });
      } else if (detalle.data) {
        await apiFetch<PoliticaPago>(`${RUTA_POLITICAS_PAGO}/${detalle.data.id}`, {
          method: "PUT",
          body: cuerpo,
          ifMatch: String(detalle.data.version),
        });
        notify({ type: "success", title: "Política actualizada" });
        setEditando(false);
        await queryClient.invalidateQueries({ queryKey: [CONSULTA_POLITICAS_PAGO] });
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
    if (fundamento.length < 20) {
      setErrorActivacion("El fundamento debe tener al menos 20 caracteres.");
      return;
    }
    setActivando(true);
    setErrorActivacion(null);
    try {
      await apiFetch<PoliticaPago>(`${RUTA_POLITICAS_PAGO}/${detalle.data.id}/activar`, {
        method: "POST",
        body: { fundamento },
        ifMatch: String(detalle.data.version),
      });
      notify({ type: "success", title: "Política activada" });
      setDialogoActivarAbierto(false);
      await queryClient.invalidateQueries({ queryKey: [CONSULTA_POLITICAS_PAGO] });
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
    if (motivo.length < 10) {
      setErrorCierre("El motivo debe tener al menos 10 caracteres.");
      return;
    }
    setCerrando(true);
    setErrorCierre(null);
    try {
      await apiFetch<PoliticaPago>(`${RUTA_POLITICAS_PAGO}/${detalle.data.id}/cerrar`, {
        method: "POST",
        body: { motivo },
        ifMatch: String(detalle.data.version),
      });
      notify({ type: "success", title: "Política cerrada" });
      setDialogoCerrarAbierto(false);
      await queryClient.invalidateQueries({ queryKey: [CONSULTA_POLITICAS_PAGO] });
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

  const nuevaVersion = async () => {
    if (!detalle.data) return;
    try {
      const nueva = await apiFetch<PoliticaPago>(
        `${RUTA_POLITICAS_PAGO}/${detalle.data.id}/nueva-version`,
        { method: "POST" },
      );
      notify({ type: "success", title: "Nueva versión creada" });
      await queryClient.invalidateQueries({ queryKey: [CONSULTA_POLITICAS_PAGO] });
      navigate(`${RUTA_POLITICAS_PAGO}/${nueva.id}`, { replace: true });
    } catch (error) {
      mostrarError(error);
    }
  };

  if (detalle.isLoading && !esNueva) {
    return (
      <PageContent>
        <LoadingState />
      </PageContent>
    );
  }

  if (detalle.isError && !esNueva) {
    return (
      <PageContent>
        <ErrorState
          title="No fue posible cargar la política"
          message={
            detalle.error instanceof ApiError
              ? detalle.error.message
              : "Ocurrió un error al cargar la política."
          }
        />
      </PageContent>
    );
  }

  const estado = detalle.data?.estado;
  const esBorrador = esNueva || estado === "BORRADOR";
  const puedeEditar = puedeGestionar && esBorrador;
  const puedeActivar = puedeGestionar && estado === "BORRADOR";
  const puedeCerrar = puedeGestionar && estado === "VIGENTE";
  const puedeNuevaVersion = puedeGestionar && (estado === "VIGENTE" || estado === "CERRADA");

  const cabecera = (
    <PageHeader
      crumbs={[
        { label: "Gobierno" },
        { label: "Tesorería" },
        { label: "Políticas de pago", to: RUTA_POLITICAS_PAGO },
        {
          label: esNueva
            ? "Nueva política"
            : `${detalle.data?.codigo ?? "Política"} v${detalle.data?.numero_version ?? ""}`,
        },
      ]}
      title={
        esNueva
          ? "Nueva política de pago"
          : `Política de pago ${detalle.data?.codigo ?? ""} v${detalle.data?.numero_version ?? ""}`
      }
      description={
        esNueva
          ? "Registre una política para definir qué se exige al pagar una orden."
          : detalle.data?.nombre ?? ""
      }
      status={
        detalle.data ? (
          <span className="rounded bg-surface-100 px-2 py-0.5 text-xs font-medium text-text-700">
            {ESTADOS_POLITICA_PAGO[detalle.data.estado]}
          </span>
        ) : undefined
      }
    />
  );

  const renderCampo = (campo: keyof FormPoliticaPago, etiqueta: string, required: boolean) => {
    if (!puedeEditar) return null;
    return (
      <FormField label={etiqueta} htmlFor={`campo-${campo}`} required={required} error={campoError[campo]}>
        <TextInput
          id={`campo-${campo}`}
          value={String(form[campo])}
          onChange={(evento) => cambiarCampo(campo, evento.target.value as FormPoliticaPago[typeof campo])}
        />
      </FormField>
    );
  };

  return (
    <PageContent>
      {cabecera}
      {!esNueva && detalle.data && !puedeGestionar ? (
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para gestionar las políticas de pago."
        />
      ) : (
        <>
          {formError && (
            <div role="alert" className="mb-4 rounded-md border border-danger-300 bg-danger-50 px-4 py-3 text-sm text-danger-800">
              {formError}
            </div>
          )}

          {puedeEditar && (
            <>
              <h2 className="mb-3 text-lg font-semibold">Datos</h2>
              {esNueva && renderCampo("codigo", "Código", true)}
              {renderCampo("nombre", "Nombre", true)}
              {renderCampo("descripcion", "Descripción", false)}
              <FormField label="Moneda" htmlFor="campo-moneda" required error={campoError.moneda}>
                <select
                  id="campo-moneda"
                  className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                  value={form.moneda}
                  onChange={(evento) => cambiarCampo("moneda", evento.target.value)}
                >
                  {MONEDAS.map((moneda) => (
                    <option key={moneda.valor} value={moneda.valor}>
                      {moneda.etiqueta}
                    </option>
                  ))}
                </select>
              </FormField>
              <FormField label="Vigente desde" htmlFor="campo-vigente_desde" required error={campoError.vigente_desde}>
                <input
                  id="campo-vigente_desde"
                  type="date"
                  className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                  value={form.vigente_desde}
                  onChange={(evento) => cambiarCampo("vigente_desde", evento.target.value)}
                />
              </FormField>
              <FormField label="Vigente hasta" htmlFor="campo-vigente_hasta" required={false} error={campoError.vigente_hasta}>
                <input
                  id="campo-vigente_hasta"
                  type="date"
                  className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                  value={form.vigente_hasta}
                  onChange={(evento) => cambiarCampo("vigente_hasta", evento.target.value)}
                />
              </FormField>
              <FormField label="Tipo de regla" htmlFor="campo-tipo_regla" required error={campoError.tipo_regla}>
                <select
                  id="campo-tipo_regla"
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
              <FormField
                label="Fundamento"
                htmlFor="campo-fundamento"
                required={false}
                help="Norma, acto u ordenanza del ente que sustenta la regla"
              >
                <textarea
                  id="campo-fundamento"
                  className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                  rows={3}
                  value={form.fundamento}
                  onChange={(evento) => cambiarCampo("fundamento", evento.target.value)}
                />
              </FormField>

              <h2 className="mb-3 mt-6 text-lg font-semibold">Reglas</h2>
              <div className="space-y-2">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={form.permite_pago_parcial}
                    onChange={(evento) => cambiarCampo("permite_pago_parcial", evento.target.checked)}
                  />
                  Permite pagos parciales
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={form.exige_cargo_autorizado_cuenta}
                    onChange={(evento) =>
                      cambiarCampo("exige_cargo_autorizado_cuenta", evento.target.checked)
                    }
                  />
                  El autorizador debe ser firmante de la cuenta
                </label>
              </div>
              <FormField label="Control de duplicado" htmlFor="campo-control_duplicado" required>
                <select
                  id="campo-control_duplicado"
                  className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                  value={form.control_duplicado}
                  onChange={(evento) =>
                    cambiarCampo("control_duplicado", evento.target.value as ControlDuplicado)
                  }
                >
                  <option value="BLOQUEAR">Bloquear</option>
                  <option value="ADVERTIR">Advertir y pedir confirmación</option>
                </select>
              </FormField>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <FormField label="Acción del preparador" htmlFor="campo-preparador_accion">
                  <select
                    id="campo-preparador_accion"
                    className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                    value={form.preparador_competencia_accion}
                    onChange={(evento) =>
                      cambiarCampo("preparador_competencia_accion", evento.target.value)
                    }
                  >
                    <option value="">Sin exigencia</option>
                    {ACCIONES_COMPETENCIA.map((accion) => (
                      <option key={accion} value={accion}>
                        {accion}
                      </option>
                    ))}
                  </select>
                </FormField>
                <FormField label="Materia del preparador" htmlFor="campo-preparador_materia">
                  <select
                    id="campo-preparador_materia"
                    className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                    value={form.preparador_competencia_materia}
                    onChange={(evento) =>
                      cambiarCampo("preparador_competencia_materia", evento.target.value)
                    }
                  >
                    <option value="">Sin exigencia</option>
                    {MATERIAS_COMPETENCIA.map((materia) => (
                      <option key={materia} value={materia}>
                        {materia}
                      </option>
                    ))}
                  </select>
                </FormField>
              </div>

              <h2 className="mb-3 mt-6 text-lg font-semibold">Medios permitidos</h2>
              {medios.isLoading && <LoadingState />}
              {medios.data && medios.data.length === 0 && (
                <p className="text-sm">
                  Registre primero los medios de pago del ente en{" "}
                  <Link to={RUTA_MEDIOS_PAGO} className="text-brand-700 underline">
                    {RUTA_MEDIOS_PAGO}
                  </Link>
                  .
                </p>
              )}
              {medios.data && medios.data.length > 0 && (
                <div className="space-y-2">
                  {medios.data.map((medio) => (
                    <label key={medio.id} className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={mediosSeleccionados.includes(medio.id)}
                        onChange={() => alternarMedio(medio.id)}
                      />
                      {medio.codigo} - {medio.nombre}
                    </label>
                  ))}
                </div>
              )}

              <h2 className="mb-2 mt-6 text-lg font-semibold">Bandas de aprobación por monto</h2>
              <p className="mb-3 text-sm text-text-700">
                Cada banda aplica a pagos con monto mayor que «desde» y hasta «hasta» inclusive, en
                la moneda de la política. La primera empieza en 0 y cada una empieza donde termina
                la anterior. Las cifras las define el ente.
              </p>
              {bandas.map((banda, indiceBanda) => (
                <div key={indiceBanda} className="mb-4 rounded-md border border-border-default p-4">
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <FormField label="Desde" htmlFor={`banda-${indiceBanda}-desde`} required>
                      <input
                        id={`banda-${indiceBanda}-desde`}
                        type="text"
                        inputMode="decimal"
                        className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                        value={banda.monto_desde}
                        onChange={(evento) =>
                          cambiarBanda(indiceBanda, { monto_desde: evento.target.value })
                        }
                      />
                    </FormField>
                    <FormField label="Hasta (vacío = sin tope)" htmlFor={`banda-${indiceBanda}-hasta`}>
                      <input
                        id={`banda-${indiceBanda}-hasta`}
                        type="text"
                        inputMode="decimal"
                        className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                        value={banda.monto_hasta}
                        onChange={(evento) =>
                          cambiarBanda(indiceBanda, { monto_hasta: evento.target.value })
                        }
                      />
                    </FormField>
                  </div>
                  <h3 className="mb-2 mt-4 text-sm font-semibold">Requisitos</h3>
                  {banda.requisitos.map((requisito, indiceRequisito) => (
                    <div
                      key={indiceRequisito}
                      className="mb-2 grid grid-cols-1 gap-2 sm:grid-cols-4"
                    >
                      <select
                        className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                        aria-label={`Acción del requisito ${indiceRequisito + 1}`}
                        value={requisito.accion}
                        onChange={(evento) =>
                          cambiarRequisito(indiceBanda, indiceRequisito, {
                            accion: evento.target.value,
                          })
                        }
                      >
                        {ACCIONES_COMPETENCIA.map((accion) => (
                          <option key={accion} value={accion}>
                            {accion}
                          </option>
                        ))}
                      </select>
                      <select
                        className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                        aria-label={`Materia del requisito ${indiceRequisito + 1}`}
                        value={requisito.materia}
                        onChange={(evento) =>
                          cambiarRequisito(indiceBanda, indiceRequisito, {
                            materia: evento.target.value,
                          })
                        }
                      >
                        {MATERIAS_COMPETENCIA.map((materia) => (
                          <option key={materia} value={materia}>
                            {materia}
                          </option>
                        ))}
                      </select>
                      <input
                        type="number"
                        min={1}
                        aria-label={`Cantidad del requisito ${indiceRequisito + 1}`}
                        max={5}
                        className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                        value={requisito.cantidad}
                        onChange={(evento) =>
                          cambiarRequisito(indiceBanda, indiceRequisito, {
                            cantidad: Number(evento.target.value),
                          })
                        }
                      />
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() => quitarRequisito(indiceBanda, indiceRequisito)}
                      >
                        Quitar
                      </Button>
                    </div>
                  ))}
                  <Button type="button" variant="secondary" onClick={() => anadirRequisito(indiceBanda)}>
                    Añadir requisito
                  </Button>
                  <div className="mt-3">
                    <Button
                      type="button"
                      variant="danger"
                      onClick={() => quitarBanda(indiceBanda)}
                    >
                      Quitar banda
                    </Button>
                  </div>
                </div>
              ))}
              <Button type="button" variant="secondary" onClick={anadirBanda}>
                Añadir banda
              </Button>

              <h2 className="mb-3 mt-6 text-lg font-semibold">Documentos por etapa</h2>
              {documentos.map((documento, indice) => (
                <div key={indice} className="mb-2 grid grid-cols-1 gap-2 sm:grid-cols-4">
                  <FormField label="Tipo documental (id)" htmlFor={`documento-${indice}-tipo`}>
                    <input
                      id={`documento-${indice}-tipo`}
                      className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                      value={documento.document_type_id}
                      onChange={(evento) =>
                        cambiarDocumento(indice, { document_type_id: evento.target.value })
                      }
                    />
                  </FormField>
                  <select
                    className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                    value={documento.etapa}
                    onChange={(evento) =>
                      cambiarDocumento(indice, {
                        etapa: evento.target.value as EtapaDocumentoPago,
                      })
                    }
                  >
                    {Object.entries(ETAPAS_DOCUMENTO_PAGO).map(([valor, etiqueta]) => (
                      <option key={valor} value={valor}>
                        {etiqueta}
                      </option>
                    ))}
                  </select>
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={documento.obligatorio}
                      onChange={(evento) =>
                        cambiarDocumento(indice, { obligatorio: evento.target.checked })
                      }
                    />
                    Obligatorio
                  </label>
                  <Button type="button" variant="secondary" onClick={() => quitarDocumento(indice)}>
                    Quitar
                  </Button>
                </div>
              ))}
              <Button type="button" variant="secondary" onClick={anadirDocumento}>
                Añadir documento
              </Button>

              <div className="mt-6 flex gap-3">
                <Button type="button" onClick={guardar} disabled={guardando || !formularioValido}>
                  {guardando ? "Guardando..." : "Guardar"}
                </Button>
                <Link
                  to={RUTA_POLITICAS_PAGO}
                  className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
                >
                  Volver
                </Link>
              </div>
            </>
          )}

          {!esNueva && detalle.data && !puedeEditar && (
            <div className="space-y-6">
              <section>
                <h2 className="mb-3 text-lg font-semibold">Datos</h2>
                <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <dt className="text-sm font-medium text-text-700">Código</dt>
                    <dd>{detalle.data.codigo}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-text-700">Nombre</dt>
                    <dd>{detalle.data.nombre}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-text-700">Descripción</dt>
                    <dd>{detalle.data.descripcion ?? "-"}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-text-700">Moneda</dt>
                    <dd>{detalle.data.moneda}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-text-700">Vigente desde</dt>
                    <dd>{formatearFechaDeNegocio(detalle.data.vigente_desde)}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-text-700">Vigente hasta</dt>
                    <dd>
                      {detalle.data.vigente_hasta
                        ? formatearFechaDeNegocio(detalle.data.vigente_hasta)
                        : "-"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-text-700">Tipo de regla</dt>
                    <dd>{detalle.data.tipo_regla}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-text-700">Fundamento</dt>
                    <dd>{detalle.data.fundamento ?? "-"}</dd>
                  </div>
                </dl>
              </section>
              <section>
                <h2 className="mb-3 text-lg font-semibold">Reglas</h2>
                <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <dt className="text-sm font-medium text-text-700">Permite pagos parciales</dt>
                    <dd>{detalle.data.permite_pago_parcial ? "Sí" : "No"}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-text-700">Control de duplicado</dt>
                    <dd>
                      {detalle.data.control_duplicado === "BLOQUEAR"
                        ? "Bloquear"
                        : "Advertir y pedir confirmación"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-text-700">
                      El autorizador debe ser firmante
                    </dt>
                    <dd>{detalle.data.exige_cargo_autorizado_cuenta ? "Sí" : "No"}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-text-700">Preparador</dt>
                    <dd>
                      {detalle.data.preparador_competencia_accion
                        ? `${detalle.data.preparador_competencia_accion} · ${detalle.data.preparador_competencia_materia ?? "-"}`
                        : "Sin exigencia"}
                    </dd>
                  </div>
                </dl>
              </section>
              <section>
                <h2 className="mb-3 text-lg font-semibold">Medios permitidos</h2>
                {detalle.data.medios.length === 0 ? (
                  <p>Sin medios permitidos</p>
                ) : (
                  <ul className="list-inside list-disc">
                    {detalle.data.medios.map((medio) => (
                      <li key={medio.id}>
                        {medio.codigo} - {medio.nombre}
                      </li>
                    ))}
                  </ul>
                )}
              </section>
              <section>
                <h2 className="mb-3 text-lg font-semibold">Bandas de aprobación por monto</h2>
                <div
                  className="overflow-x-auto"
                  tabIndex={0}
                  role="region"
                  aria-label="Bandas de aprobación"
                >
                  <table className="min-w-full divide-y divide-border-default">
                    <thead>
                      <tr>
                        <th className="px-4 py-2 text-left text-sm font-semibold">Desde</th>
                        <th className="px-4 py-2 text-left text-sm font-semibold">Hasta</th>
                        <th className="px-4 py-2 text-left text-sm font-semibold">Requisitos</th>
                      </tr>
                    </thead>
                    <tbody>
                      {detalle.data.bandas.map((banda, indice) => (
                        <tr key={indice}>
                          <td className="px-4 py-2 text-sm">{banda.monto_desde}</td>
                          <td className="px-4 py-2 text-sm">{banda.monto_hasta ?? "Sin tope"}</td>
                          <td className="px-4 py-2 text-sm">
                            {banda.requisitos
                              .map(
                                (requisito) =>
                                  `${requisito.accion} × ${requisito.materia} × ${requisito.cantidad}`,
                              )
                              .join("; ")}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
              <section>
                <h2 className="mb-3 text-lg font-semibold">Documentos por etapa</h2>
                <div
                  className="overflow-x-auto"
                  tabIndex={0}
                  role="region"
                  aria-label="Documentos por etapa"
                >
                  <table className="min-w-full divide-y divide-border-default">
                    <thead>
                      <tr>
                        <th className="px-4 py-2 text-left text-sm font-semibold">Tipo documental</th>
                        <th className="px-4 py-2 text-left text-sm font-semibold">Etapa</th>
                        <th className="px-4 py-2 text-left text-sm font-semibold">Obligatorio</th>
                      </tr>
                    </thead>
                    <tbody>
                      {detalle.data.documentos.length === 0 ? (
                        <tr>
                          <td colSpan={3} className="px-4 py-2 text-sm">
                            Sin documentos
                          </td>
                        </tr>
                      ) : (
                        detalle.data.documentos.map((documento, indice) => (
                          <tr key={indice}>
                            <td className="px-4 py-2 text-sm">{documento.document_type_id}</td>
                            <td className="px-4 py-2 text-sm">
                              {ETAPAS_DOCUMENTO_PAGO[documento.etapa]}
                            </td>
                            <td className="px-4 py-2 text-sm">
                              {documento.obligatorio ? "Sí" : "No"}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </section>
              <section>
                <h2 className="mb-3 text-lg font-semibold">Historia</h2>
                <div
                  className="overflow-x-auto"
                  tabIndex={0}
                  role="region"
                  aria-label="Historia de versiones"
                >
                  <table className="min-w-full divide-y divide-border-default">
                    <thead>
                      <tr>
                        <th className="px-4 py-2 text-left text-sm font-semibold">Evento</th>
                        <th className="px-4 py-2 text-left text-sm font-semibold">Versión</th>
                        <th className="px-4 py-2 text-left text-sm font-semibold">Fecha</th>
                      </tr>
                    </thead>
                    <tbody>
                      {detalle.data.historia.length === 0 ? (
                        <tr>
                          <td colSpan={3} className="px-4 py-2 text-sm">
                            Sin historia
                          </td>
                        </tr>
                      ) : (
                        detalle.data.historia.map((evento, indice) => (
                          <tr key={indice}>
                            <td className="px-4 py-2 text-sm">{evento.evento}</td>
                            <td className="px-4 py-2 text-sm">{evento.numero_version}</td>
                            <td className="px-4 py-2 text-sm">
                              {evento.created_at
                                ? formatearInstante(evento.created_at)
                                : evento.created_at}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </section>
            </div>
          )}

          {!esNueva && detalle.data && (
            <div className="mt-6 flex flex-wrap gap-3">
              {puedeActivar && (
                <Button type="button" onClick={abrirActivacion}>
                  Activar
                </Button>
              )}
              {puedeCerrar && (
                <Button type="button" variant="danger" onClick={abrirCierre}>
                  Cerrar
                </Button>
              )}
              {puedeNuevaVersion && (
                <Button type="button" onClick={nuevaVersion}>
                  Nueva versión
                </Button>
              )}
              <Link
                to={RUTA_POLITICAS_PAGO}
                className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
              >
                Volver
              </Link>
            </div>
          )}

          <ConfirmationDialog
            open={dialogoActivarAbierto}
            title="Activar la política"
            description="Confirme que desea activar esta política. Exige MFA y activar una versión nueva cierra la anterior."
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
              />
            </FormField>
          </ConfirmationDialog>
        </>
      )}
    </PageContent>
  );
}
