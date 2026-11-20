import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { descargarArchivo, mensajeDeDescarga } from "@/api/descargas";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Button } from "@/components/Button";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { ErrorState } from "@/components/ErrorState";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { TextInput } from "@/components/TextInput";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import {
  API_RETENCIONES,
  CONSULTA_LIQUIDACIONES,
  ESTADOS_COMPROBANTE,
  ESTADOS_LIQUIDACION,
  Liquidacion,
  MontosPago,
  MOTIVOS_NO_APLICA,
  OpcionesRetencion,
  TIPOS_PERSONA,
} from "./api";

interface OpcionesPago {
  cargos: {
    id: string;
    codigo: string;
    nombre: string;
    competencias: string[];
  }[];
}

interface PoliticaAprobador {
  aprobador_competencia_accion: string | null;
  aprobador_competencia_materia: string | null;
}

export function RetencionesPago({
  pagoId,
  pagoEstado,
}: {
  pagoId: string;
  pagoEstado: string;
}) {
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();

  const puedeVer = tiene("gobierno_retenciones:view", "empresa");
  const puedeCalcular = tiene("gobierno_retenciones:calculate", "empresa");
  const puedeAprobar = tiene("gobierno_retenciones:approve", "empresa");
  const puedeAnular = tiene("gobierno_retenciones:cancel", "empresa");

  const [mostrarFormulario, setMostrarFormulario] = useState(false);
  const [opciones, setOpciones] = useState<OpcionesRetencion | null>(null);
  const [opcionesCargando, setOpcionesCargando] = useState(false);
  const [politicaId, setPoliticaId] = useState("");
  const [conceptosSeleccionados, setConceptosSeleccionados] = useState<
    string[]
  >([]);
  const [nombreBeneficiario, setNombreBeneficiario] = useState("");
  const [identificacionFiscal, setIdentificacionFiscal] = useState("");
  const [tipoPersona, setTipoPersona] = useState("NATURAL");
  const [condicionesSeleccionadas, setCondicionesSeleccionadas] = useState<
    string[]
  >([]);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [calculando, setCalculando] = useState(false);

  const [dialogoAjusteLinea, setDialogoAjusteLinea] = useState<string | null>(
    null,
  );
  const [montoAprobado, setMontoAprobado] = useState("");
  const [motivoAjuste, setMotivoAjuste] = useState("");
  const [ajustando, setAjustando] = useState(false);
  const [errorAjuste, setErrorAjuste] = useState<string | null>(null);

  const [dialogoAprobar, setDialogoAprobar] = useState(false);
  const [cargoId, setCargoId] = useState("");
  const [aprobando, setAprobando] = useState(false);
  const [errorAprobar, setErrorAprobar] = useState<string | null>(null);

  const [dialogoDescartar, setDialogoDescartar] = useState(false);
  const [motivoDescartar, setMotivoDescartar] = useState("");
  const [descartando, setDescartando] = useState(false);
  const [errorDescartar, setErrorDescartar] = useState<string | null>(null);

  const [dialogoAnular, setDialogoAnular] = useState(false);
  const [motivoAnular, setMotivoAnular] = useState("");
  const [anulando, setAnulando] = useState(false);
  const [errorAnular, setErrorAnular] = useState<string | null>(null);

  const liquidacionQuery = useQuery({
    queryKey: [...CONSULTA_LIQUIDACIONES, pagoId],
    queryFn: async () => {
      const respuesta = await apiFetch<{
        montos: MontosPago;
        liquidacion: Liquidacion | null;
      }>(`${API_RETENCIONES}/pagos/${pagoId}/liquidacion`);
      return respuesta;
    },
    enabled: puedeVer,
  });

  const opcionesPagoQuery = useQuery({
    queryKey: ["gobierno", "tesoreria", "pagos", "opciones"],
    queryFn: async () => {
      return apiFetch<OpcionesPago>("/gobierno/tesoreria/pagos/opciones");
    },
    enabled: dialogoAprobar,
  });

  const politicaAprobadorQuery = useQuery({
    queryKey: ["retenciones", "politica", liquidacionQuery.data?.liquidacion?.policy_id],
    queryFn: async () => {
      const policyId = liquidacionQuery.data?.liquidacion?.policy_id;
      if (!policyId) return null;
      return apiFetch<PoliticaAprobador>(
        `${API_RETENCIONES}/politicas/${policyId}`,
      );
    },
    enabled: dialogoAprobar && !!liquidacionQuery.data?.liquidacion?.policy_id,
  });

  useEffect(() => {
    if (!mostrarFormulario) {
      setOpciones(null);
      setPoliticaId("");
      setConceptosSeleccionados([]);
      setNombreBeneficiario("");
      setIdentificacionFiscal("");
      setTipoPersona("NATURAL");
      setCondicionesSeleccionadas([]);
      setFieldErrors({});
      setGeneralError(null);
    }
  }, [mostrarFormulario]);

  const cargarOpciones = async () => {
    setOpcionesCargando(true);
    setFieldErrors({});
    setGeneralError(null);
    try {
      const datos = await apiFetch<OpcionesRetencion>(
        `${API_RETENCIONES}/opciones?payment_id=${pagoId}`,
      );
      setOpciones(datos);
      setMostrarFormulario(true);
    } catch (error) {
      notify({
        type: "error",
        title: "Error",
        description:
          error instanceof ApiError
            ? error.message
            : "No fue posible cargar las opciones de retención.",
      });
    } finally {
      setOpcionesCargando(false);
    }
  };

  const politicaElegida = opciones?.politicas.find(
    (politica) => politica.id === politicaId,
  );

  const conceptosDisponibles = politicaElegida
    ? opciones?.conceptos.filter((concepto) =>
        politicaElegida.conceptos.includes(concepto.codigo),
      )
    : [];

  const alternarConcepto = (id: string) => {
    setConceptosSeleccionados((previos) =>
      previos.includes(id)
        ? previos.filter((c) => c !== id)
        : [...previos, id],
    );
    setFieldErrors((previos) => {
      const nuevos = { ...previos };
      delete nuevos.conceptos;
      return nuevos;
    });
  };

  const alternarCondicion = (id: string) => {
    setCondicionesSeleccionadas((previas) =>
      previas.includes(id)
        ? previas.filter((c) => c !== id)
        : [...previas, id],
    );
  };

  const calcular = async () => {
    setCalculando(true);
    setFieldErrors({});
    setGeneralError(null);
    try {
      await apiFetch(`${API_RETENCIONES}/pagos/${pagoId}/liquidacion`, {
        method: "POST",
        body: {
          policy_id: politicaId,
          conceptos: conceptosSeleccionados,
          beneficiario: {
            nombre: nombreBeneficiario,
            identificacion_fiscal: identificacionFiscal,
            tipo_persona: tipoPersona,
            condiciones: condicionesSeleccionadas,
          },
        },
      });
      setMostrarFormulario(false);
      notify({
        type: "success",
        title: "Retenciones calculadas",
      });
      await queryClient.invalidateQueries({
        queryKey: [...CONSULTA_LIQUIDACIONES, pagoId],
      });
      await queryClient.invalidateQueries({
        queryKey: ["gobierno", "tesoreria", "pagos"],
      });
    } catch (error) {
      if (error instanceof ApiError && error.status === 422) {
        const errores = error.fieldErrors;
        if (errores) {
          const planos: Record<string, string> = {};
          for (const [campo, mensajes] of Object.entries(errores)) {
            planos[campo] = mensajes[0] ?? "Valor inválido.";
          }
          setFieldErrors(planos);
        }
        setGeneralError(
          error.message || "Revise los datos del formulario de cálculo.",
        );
      } else {
        setGeneralError(
          error instanceof ApiError
            ? error.message
            : "No fue posible calcular las retenciones.",
        );
      }
    } finally {
      setCalculando(false);
    }
  };

  const abrirAjuste = (lineaId: string) => {
    setDialogoAjusteLinea(lineaId);
    setMontoAprobado("");
    setMotivoAjuste("");
    setErrorAjuste(null);
  };

  const ajustarLinea = async () => {
    const liquidacion = liquidacionQuery.data?.liquidacion;
    if (!liquidacion) return;
    if (motivoAjuste.trim().length < 10) {
      setErrorAjuste("El motivo del ajuste debe tener al menos 10 caracteres.");
      return;
    }
    if (ajustando) return;
    setAjustando(true);
    setErrorAjuste(null);
    try {
      await apiFetch(
        `${API_RETENCIONES}/liquidaciones/${liquidacion.id}/lineas/${dialogoAjusteLinea}`,
        {
          method: "PUT",
          ifMatch: String(liquidacion.version),
          body: {
            monto_aprobado: montoAprobado,
            motivo: motivoAjuste,
          },
        },
      );
      setDialogoAjusteLinea(null);
      notify({ type: "success", title: "Línea ajustada" });
      await queryClient.invalidateQueries({
        queryKey: [...CONSULTA_LIQUIDACIONES, pagoId],
      });
      await queryClient.invalidateQueries({
        queryKey: ["gobierno", "tesoreria", "pagos"],
      });
    } catch (error) {
      setErrorAjuste(
        error instanceof ApiError
          ? error.message
          : "No fue posible ajustar la línea.",
      );
    } finally {
      setAjustando(false);
    }
  };

  const abrirAprobar = () => {
    setDialogoAprobar(true);
    setCargoId("");
    setErrorAprobar(null);
  };

  const aprobar = async () => {
    const liquidacion = liquidacionQuery.data?.liquidacion;
    if (!liquidacion) return;
    if (!cargoId) {
      setErrorAprobar("Seleccione el cargo que aprueba.");
      return;
    }
    if (aprobando) return;
    setAprobando(true);
    setErrorAprobar(null);
    try {
      await apiFetch(
        `${API_RETENCIONES}/liquidaciones/${liquidacion.id}/aprobar`,
        {
          method: "POST",
          ifMatch: String(liquidacion.version),
          body: { cargo_id: cargoId },
        },
      );
      setDialogoAprobar(false);
      notify({ type: "success", title: "Retenciones aprobadas" });
      await queryClient.invalidateQueries({
        queryKey: [...CONSULTA_LIQUIDACIONES, pagoId],
      });
      await queryClient.invalidateQueries({
        queryKey: ["gobierno", "tesoreria", "pagos"],
      });
    } catch (error) {
      setErrorAprobar(
        error instanceof ApiError
          ? error.message
          : "No fue posible aprobar las retenciones.",
      );
    } finally {
      setAprobando(false);
    }
  };

  const abrirDescartar = () => {
    setDialogoDescartar(true);
    setMotivoDescartar("");
    setErrorDescartar(null);
  };

  const descartar = async () => {
    const liquidacion = liquidacionQuery.data?.liquidacion;
    if (!liquidacion) return;
    if (motivoDescartar.trim().length < 10) {
      setErrorDescartar("El motivo debe tener al menos 10 caracteres.");
      return;
    }
    if (descartando) return;
    setDescartando(true);
    setErrorDescartar(null);
    try {
      await apiFetch(
        `${API_RETENCIONES}/liquidaciones/${liquidacion.id}/descartar`,
        {
          method: "POST",
          ifMatch: String(liquidacion.version),
          body: { motivo: motivoDescartar },
        },
      );
      setDialogoDescartar(false);
      notify({ type: "success", title: "Cálculo descartado" });
      await queryClient.invalidateQueries({
        queryKey: [...CONSULTA_LIQUIDACIONES, pagoId],
      });
      await queryClient.invalidateQueries({
        queryKey: ["gobierno", "tesoreria", "pagos"],
      });
    } catch (error) {
      setErrorDescartar(
        error instanceof ApiError
          ? error.message
          : "No fue posible descartar el cálculo.",
      );
    } finally {
      setDescartando(false);
    }
  };

  const abrirAnular = () => {
    setDialogoAnular(true);
    setMotivoAnular("");
    setErrorAnular(null);
  };

  const anular = async () => {
    const liquidacion = liquidacionQuery.data?.liquidacion;
    if (!liquidacion) return;
    if (motivoAnular.trim().length < 10) {
      setErrorAnular("El motivo debe tener al menos 10 caracteres.");
      return;
    }
    if (anulando) return;
    setAnulando(true);
    setErrorAnular(null);
    try {
      await apiFetch(
        `${API_RETENCIONES}/liquidaciones/${liquidacion.id}/anular`,
        {
          method: "POST",
          ifMatch: String(liquidacion.version),
          body: { motivo: motivoAnular },
        },
      );
      setDialogoAnular(false);
      notify({ type: "success", title: "Retenciones anuladas" });
      await queryClient.invalidateQueries({
        queryKey: [...CONSULTA_LIQUIDACIONES, pagoId],
      });
      await queryClient.invalidateQueries({
        queryKey: ["gobierno", "tesoreria", "pagos"],
      });
    } catch (error) {
      setErrorAnular(
        error instanceof ApiError
          ? error.message
          : "No fue posible anular las retenciones.",
      );
    } finally {
      setAnulando(false);
    }
  };

  const descargarComprobante = async (comprobanteId: string, codigo: string) => {
    try {
      await descargarArchivo(
        `${API_RETENCIONES}/comprobantes/${comprobanteId}/pdf`,
        `comprobante-${codigo}.pdf`,
      );
    } catch (error) {
      notify({
        type: "error",
        title: "Error",
        description: mensajeDeDescarga(error),
      });
    }
  };

  if (!puedeVer) {
    return null;
  }

  const montos = liquidacionQuery.data?.montos;
  const liquidacion = liquidacionQuery.data?.liquidacion;

  const puedeCalcularSegunEstado = ["BORRADOR", "PENDIENTE_AUTORIZACION", "AUTORIZADO"].includes(
    pagoEstado,
  );

  return (
    <section aria-labelledby="retenciones-heading" className="mt-8">
      <h2 id="retenciones-heading" className="text-lg font-semibold">
        Retenciones
      </h2>

      {liquidacionQuery.isLoading ? (
        <LoadingState />
      ) : liquidacionQuery.isError ? (
        <ErrorState
          title="No se pudieron cargar las retenciones"
          message={
            liquidacionQuery.error instanceof ApiError
              ? liquidacionQuery.error.message
              : "Error inesperado"
          }
        />
      ) : (
        <>
          {montos && (
            <dl className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">
              <div>
                <dt className="text-sm text-muted-foreground">Bruto</dt>
                <dd className="font-medium">
                  {montos.bruto} {montos.moneda}
                </dd>
              </div>
              <div>
                <dt className="text-sm text-muted-foreground">Retenciones</dt>
                <dd className="font-medium">
                  {montos.total_retenido} {montos.moneda}
                </dd>
              </div>
              <div>
                <dt className="text-sm text-muted-foreground">Neto</dt>
                <dd className="font-medium">
                  {montos.neto} {montos.moneda}
                </dd>
              </div>
              <div>
                <dt className="text-sm text-muted-foreground">Estado</dt>
                <dd className="font-medium">
                  {montos.definitivo ? "Definitivo" : "Preliminar"}
                </dd>
              </div>
            </dl>
          )}

          {!liquidacion && puedeCalcularSegunEstado && puedeCalcular && (
            <div className="mt-4">
              {!mostrarFormulario ? (
                <Button onClick={cargarOpciones} disabled={opcionesCargando}>
                  {opcionesCargando ? "Cargando opciones…" : "Calcular retenciones"}
                </Button>
              ) : (
                <div className="mt-4 rounded-md border border-border-default p-4">
                  <h3 className="font-medium">Calcular retenciones</h3>
                  {opciones && (
                    <div className="mt-4 space-y-4">
                      <FormField label="Política de retención" htmlFor="politica-retencion">
                        <select
                          id="politica-retencion"
                          className="w-full rounded-md border border-border-default px-3 py-2"
                          value={politicaId}
                          onChange={(event) => {
                            setPoliticaId(event.target.value);
                            setConceptosSeleccionados([]);
                            setFieldErrors((previos) => {
                              const nuevos = { ...previos };
                              delete nuevos.policy_id;
                              delete nuevos.conceptos;
                              return nuevos;
                            });
                          }}
                        >
                          <option value="">Seleccione…</option>
                          {opciones.politicas.map((politica) => (
                            <option key={politica.id} value={politica.id}>
                              {politica.codigo} · v{politica.numero_version} ·{" "}
                              {politica.nombre}
                            </option>
                          ))}
                        </select>
                        {fieldErrors["policy_id"] && (
                          <p className="mt-1 text-sm text-red-600" role="alert">
                            {fieldErrors["policy_id"]}
                          </p>
                        )}
                      </FormField>

                      {politicaElegida && (
                        <fieldset>
                          <legend className="text-sm font-medium">Conceptos</legend>
                          {conceptosDisponibles?.map((concepto) => (
                            <label
                              key={concepto.id}
                              className="mt-2 flex items-center gap-2"
                            >
                              <input
                                type="checkbox"
                                checked={conceptosSeleccionados.includes(concepto.codigo)}
                                onChange={() => alternarConcepto(concepto.codigo)}
                              />
                              <span>
                                {concepto.codigo} · {concepto.nombre}
                              </span>
                            </label>
                          ))}
                          {fieldErrors["conceptos"] && (
                            <p className="mt-1 text-sm text-red-600" role="alert">
                              {fieldErrors["conceptos"]}
                            </p>
                          )}
                        </fieldset>
                      )}

                      <fieldset>
                        <legend className="text-sm font-medium">
                          Beneficiario (datos declarados)
                        </legend>
                        <p className="text-sm text-muted-foreground">
                          Datos declarados por el ente pagador: el sistema no los
                          verifica.
                        </p>
                        <div className="mt-2 space-y-3">
                          <FormField label="Nombre" htmlFor="beneficiario-nombre">
                            <TextInput
                              id="beneficiario-nombre"
                              value={nombreBeneficiario}
                              onChange={(event) => {
                                setNombreBeneficiario(event.target.value);
                                setFieldErrors((previos) => {
                                  const nuevos = { ...previos };
                                  delete nuevos["beneficiario.nombre"];
                                  return nuevos;
                                });
                              }}
                            />
                            {fieldErrors["beneficiario.nombre"] && (
                              <p className="mt-1 text-sm text-red-600" role="alert">
                                {fieldErrors["beneficiario.nombre"]}
                              </p>
                            )}
                          </FormField>
                          <FormField
                            label="Identificación fiscal"
                            htmlFor="beneficiario-identificacion"
                          >
                            <TextInput
                              id="beneficiario-identificacion"
                              value={identificacionFiscal}
                              onChange={(event) => {
                                setIdentificacionFiscal(event.target.value);
                                setFieldErrors((previos) => {
                                  const nuevos = { ...previos };
                                  delete nuevos["beneficiario.identificacion_fiscal"];
                                  return nuevos;
                                });
                              }}
                            />
                            {fieldErrors["beneficiario.identificacion_fiscal"] && (
                              <p className="mt-1 text-sm text-red-600" role="alert">
                                {fieldErrors["beneficiario.identificacion_fiscal"]}
                              </p>
                            )}
                          </FormField>
                          <FormField
                            label="Tipo de persona"
                            htmlFor="beneficiario-tipo-persona"
                          >
                            <select
                              id="beneficiario-tipo-persona"
                              className="w-full rounded-md border border-border-default px-3 py-2"
                              value={tipoPersona}
                              onChange={(event) => setTipoPersona(event.target.value)}
                            >
                              <option value="NATURAL">Natural</option>
                              <option value="JURIDICA">Jurídica</option>
                            </select>
                            {fieldErrors["beneficiario.tipo_persona"] && (
                              <p className="mt-1 text-sm text-red-600" role="alert">
                                {fieldErrors["beneficiario.tipo_persona"]}
                              </p>
                            )}
                          </FormField>
                        </div>
                      </fieldset>

                      {opciones.condiciones.length > 0 && (
                        <fieldset>
                          <legend className="text-sm font-medium">Condiciones</legend>
                          {opciones.condiciones.map((condicion) => (
                            <label
                              key={condicion.id}
                              className="mt-2 flex items-center gap-2"
                            >
                              <input
                                type="checkbox"
                                checked={condicionesSeleccionadas.includes(condicion.codigo)}
                                onChange={() => alternarCondicion(condicion.codigo)}
                              />
                              <span>
                                {condicion.codigo} · {condicion.nombre}
                              </span>
                            </label>
                          ))}
                          {fieldErrors["beneficiario.condiciones"] && (
                            <p className="mt-1 text-sm text-red-600" role="alert">
                              {fieldErrors["beneficiario.condiciones"]}
                            </p>
                          )}
                        </fieldset>
                      )}

                      {generalError && (
                        <p className="text-sm text-red-600" role="alert">
                          {generalError}
                        </p>
                      )}

                      <div className="flex gap-3">
                        <Button onClick={calcular} disabled={calculando}>
                          {calculando ? "Calculando…" : "Calcular"}
                        </Button>
                        <Button
                          variant="secondary"
                          onClick={() => setMostrarFormulario(false)}
                          disabled={calculando}
                        >
                          Cancelar
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {liquidacion && (
            <div className="mt-6 space-y-4">
              <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
                <span>
                  Estado:{" "}
                  <strong>{ESTADOS_LIQUIDACION[liquidacion.estado]}</strong>
                </span>
                <span>
                  Política:{" "}
                  <strong>
                    {liquidacion.policy_codigo} · v
                    {liquidacion.policy_numero_version}
                  </strong>
                </span>
                <span>
                  Fuente:{" "}
                  {liquidacion.politica_fuente.fuente_descripcion}{" "}
                  {liquidacion.politica_fuente.fuente_referencia}
                  {liquidacion.politica_fuente.estado_verificacion ===
                    "PENDING_PIN" &&
                    " · Adoptada por el ente; verificación normativa pendiente"}
                </span>
                <span>
                  Beneficiario declarado:{" "}
                  <strong>
                    {liquidacion.beneficiario.nombre} ·{" "}
                    {liquidacion.beneficiario.identificacion_fiscal} ·{" "}
                    {TIPOS_PERSONA[liquidacion.beneficiario.tipo_persona] ??
                      liquidacion.beneficiario.tipo_persona}
                  </strong>
                </span>
              </div>

              <div role="region" aria-label="Retenciones calculadas (desplazable)" tabIndex={0} className="overflow-x-auto">
                <table className="w-full text-sm" aria-label="Retenciones calculadas">
                  <thead>
                    <tr className="border-b border-border-default text-left">
                      <th className="px-3 py-2">Concepto</th>
                      <th className="px-3 py-2">Base</th>
                      <th className="px-3 py-2">Alícuota %</th>
                      <th className="px-3 py-2">Umbral</th>
                      <th className="px-3 py-2">Calculado</th>
                      <th className="px-3 py-2">Aprobado</th>
                      <th className="px-3 py-2">Fundamento</th>
                    </tr>
                  </thead>
                  <tbody>
                    {liquidacion.lineas.map((linea) => (
                      <tr key={linea.id} className="border-b border-border-default">
                        <td className="px-3 py-2">
                          {linea.concepto_codigo} · {linea.concepto_nombre}
                        </td>
                        <td className="px-3 py-2">{linea.base}</td>
                        <td className="px-3 py-2">{linea.tasa}</td>
                        <td className="px-3 py-2">{linea.umbral}</td>
                        <td className="px-3 py-2">{linea.monto_calculado}</td>
                        <td className="px-3 py-2">
                          {linea.monto_aprobado}
                          {linea.motivo_ajuste && (
                            <div className="text-xs text-muted-foreground">
                              Ajuste: {linea.motivo_ajuste}
                            </div>
                          )}
                        </td>
                        <td className="px-3 py-2">
                          {!linea.aplica
                            ? MOTIVOS_NO_APLICA[linea.motivo_no_aplica ?? ""] ??
                              linea.motivo_no_aplica
                            : linea.tasa_referencia
                              ? `Umbral con tasa ${linea.tasa_referencia.valor} ${linea.tasa_referencia.moneda} del ${formatearFechaDeNegocio(linea.tasa_referencia.fecha_efectiva)}`
                              : ""}
                        </td>
                        {liquidacion.estado === "CALCULADA" &&
                          puedeCalcular &&
                          liquidacion.permite_ajuste &&
                          linea.aplica && (
                            <td className="px-3 py-2">
                              <Button
                                variant="secondary"
                                onClick={() => abrirAjuste(linea.id)}
                              >
                                Ajustar
                              </Button>
                            </td>
                          )}
                      </tr>
                    ))}
                    <tr className="border-b border-border-default font-medium">
                      <td className="px-3 py-2" colSpan={5}>
                        Total
                      </td>
                      <td className="px-3 py-2">{liquidacion.total_retenido}</td>
                      <td className="px-3 py-2" />
                    </tr>
                  </tbody>
                </table>
              </div>

              <div className="flex flex-wrap gap-3">
                {liquidacion.estado === "CALCULADA" && puedeAprobar && (
                  <Button onClick={abrirAprobar}>Aprobar retenciones</Button>
                )}
                {liquidacion.estado === "CALCULADA" && puedeCalcular && (
                  <Button variant="secondary" onClick={abrirDescartar}>
                    Descartar cálculo
                  </Button>
                )}
                {liquidacion.estado === "APROBADA" && puedeAnular && (
                  <Button variant="secondary" onClick={abrirAnular}>
                    Anular retenciones
                  </Button>
                )}
              </div>

              {liquidacion.comprobantes.length > 0 && (
                <div className="mt-4">
                  <h3 className="font-medium">Comprobantes</h3>
                  <ul className="mt-2 space-y-2">
                    {liquidacion.comprobantes.map((comprobante) => (
                      <li
                        key={comprobante.id}
                        className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-border-default px-3 py-2"
                      >
                        <span>
                          {comprobante.codigo} · {comprobante.concepto_codigo} ·{" "}
                          {comprobante.monto} ·{" "}
                          {ESTADOS_COMPROBANTE[comprobante.estado] ??
                            comprobante.estado}
                        </span>
                        <Button
                          variant="secondary"
                          onClick={() =>
                            descargarComprobante(comprobante.id, comprobante.codigo)
                          }
                        >
                          Descargar PDF
                        </Button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </>
      )}

      <ConfirmationDialog
        open={dialogoAjusteLinea !== null}
        onCancel={() => setDialogoAjusteLinea(null)}
        onConfirm={ajustarLinea}
        title="Ajustar línea de retención"
        confirmLabel="Ajustar"
      >
        <div className="space-y-3">
          <FormField label="Monto aprobado" htmlFor="monto-aprobado">
            <TextInput
              id="monto-aprobado"
              value={montoAprobado}
              onChange={(event) => setMontoAprobado(event.target.value)}
            />
          </FormField>
          <FormField label="Motivo del ajuste" htmlFor="motivo-ajuste">
            <textarea
              id="motivo-ajuste"
              className="w-full rounded-md border border-border-default px-3 py-2"
              value={motivoAjuste}
              onChange={(event) => setMotivoAjuste(event.target.value)}
              rows={3}
            />
          </FormField>
          {errorAjuste && (
            <p className="text-sm text-red-600" role="alert">
              {errorAjuste}
            </p>
          )}
        </div>
      </ConfirmationDialog>

      <ConfirmationDialog
        open={dialogoAprobar}
        onCancel={() => setDialogoAprobar(false)}
        onConfirm={aprobar}
        title="Aprobar retenciones"
        confirmLabel="Aprobar"
      >
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Quien calculó o ajustó no puede aprobar.
          </p>
          <FormField label="Cargo que aprueba" htmlFor="cargo-aprobador">
            <select
              id="cargo-aprobador"
              className="w-full rounded-md border border-border-default px-3 py-2"
              value={cargoId}
              onChange={(event) => setCargoId(event.target.value)}
            >
              <option value="">Seleccione…</option>
              {opcionesPagoQuery.data?.cargos.map((cargo) => {
                const politica = politicaAprobadorQuery.data;
                const accion = politica?.aprobador_competencia_accion;
                const materia = politica?.aprobador_competencia_materia;
                const competente =
                  accion && materia
                    ? cargo.competencias.includes(`${accion}·${materia}`)
                    : false;
                return (
                  <option key={cargo.id} value={cargo.id}>
                    {cargo.codigo} · {cargo.nombre}
                    {competente ? " (competente)" : ""}
                  </option>
                );
              })}
            </select>
          </FormField>
          {errorAprobar && (
            <p className="text-sm text-red-600" role="alert">
              {errorAprobar}
            </p>
          )}
        </div>
      </ConfirmationDialog>

      <ConfirmationDialog
        open={dialogoDescartar}
        onCancel={() => setDialogoDescartar(false)}
        onConfirm={descartar}
        title="Descartar cálculo"
        confirmLabel="Descartar"
      >
        <div className="space-y-3">
          <FormField label="Motivo" htmlFor="motivo-descartar">
            <textarea
              id="motivo-descartar"
              className="w-full rounded-md border border-border-default px-3 py-2"
              value={motivoDescartar}
              onChange={(event) => setMotivoDescartar(event.target.value)}
              rows={3}
            />
          </FormField>
          {errorDescartar && (
            <p className="text-sm text-red-600" role="alert">
              {errorDescartar}
            </p>
          )}
        </div>
      </ConfirmationDialog>

      <ConfirmationDialog
        open={dialogoAnular}
        onCancel={() => setDialogoAnular(false)}
        onConfirm={anular}
        title="Anular retenciones"
        confirmLabel="Anular"
      >
        <div className="space-y-3">
          <FormField label="Motivo" htmlFor="motivo-anular">
            <textarea
              id="motivo-anular"
              className="w-full rounded-md border border-border-default px-3 py-2"
              value={motivoAnular}
              onChange={(event) => setMotivoAnular(event.target.value)}
              rows={3}
            />
          </FormField>
          {errorAnular && (
            <p className="text-sm text-red-600" role="alert">
              {errorAnular}
            </p>
          )}
        </div>
      </ConfirmationDialog>
    </section>
  );
}
