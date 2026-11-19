import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { PageHeader } from "@/components/PageHeader";
import { PageContent } from "@/layout/PageContent";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { hoyDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_PAGOS,
  RUTA_PAGOS,
  type OpcionesPago,
  type Pago,
} from "./api";

export function NuevoPagoPage() {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const { notify } = useNotifications();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { pagoId } = useParams<{ pagoId: string }>();

  const esEdicion = Boolean(pagoId);

  const [orderId, setOrderId] = useState<string>("");
  const [policyId, setPolicyId] = useState<string>("");
  const [accountId, setAccountId] = useState<string>("");
  const [methodId, setMethodId] = useState<string>("");
  const [monto, setMonto] = useState<string>("");
  const [fechaPago, setFechaPago] = useState<string>(hoyDeNegocio());
  const [concepto, setConcepto] = useState<string>("");
  const [documentosSeleccionados, setDocumentosSeleccionados] = useState<Set<string>>(new Set());
  const [idempotencyKey] = useState<string>(() => crypto.randomUUID());
  const [inicializado, setInicializado] = useState<boolean>(false);
  const [errorFormulario, setErrorFormulario] = useState<string>("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});

  const tienePermiso = tiene("gobierno_pagos:manage", "empresa");

  const pagoQuery = useQuery({
    queryKey: [...CONSULTA_PAGOS, "edicion", activeCompanyId, pagoId],
    queryFn: async () => {
      if (!pagoId) return null;
      try {
        return await apiFetch<Pago>(`${RUTA_PAGOS}/${pagoId}`);
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) {
          return null;
        }
        throw error;
      }
    },
    enabled: Boolean(pagoId) && tienePermiso,
  });

  const pago = pagoQuery.data;

  useEffect(() => {
    if (!esEdicion || !pago || inicializado) return;
    setOrderId(pago.orden.id);
    setPolicyId(pago.politica.id);
    setAccountId(pago.cuenta.id);
    setMethodId(pago.medio.id);
    setMonto(pago.monto);
    setFechaPago(pago.fecha_pago);
    setConcepto(pago.concepto);
    const documentos = new Set<string>();
    for (const documento of pago.documentos) {
      if (documento.etapa === "PREPARAR") {
        documentos.add(documento.document_id);
      }
    }
    setDocumentosSeleccionados(documentos);
    setInicializado(true);
  }, [esEdicion, pago, inicializado]);

  const opcionesQuery = useQuery({
    queryKey: [...CONSULTA_PAGOS, "opciones", activeCompanyId, orderId],
    queryFn: async () => {
      const parametros = new URLSearchParams();
      if (orderId) parametros.set("order_id", orderId);
      const query = parametros.toString();
      return await apiFetch<OpcionesPago>(
        `/gobierno/tesoreria/pagos/opciones${query ? `?${query}` : ""}`,
      );
    },
    enabled: tienePermiso,
  });

  const opciones = opcionesQuery.data;

  const mutacion = useMutation({
    mutationFn: async () => {
      const documentos = Array.from(documentosSeleccionados);
      if (esEdicion) {
        if (!pago) throw new Error("No se pudo cargar el pago para editar.");
        return await apiFetch<Pago>(`${RUTA_PAGOS}/${pago.id}`, {
          method: "PUT",
          ifMatch: String(pago.version),
          body: {
            policy_id: policyId,
            account_id: accountId,
            method_id: methodId,
            monto,
            fecha_pago: fechaPago,
            concepto,
            documentos,
          },
        });
      }
      return await apiFetch<Pago>(RUTA_PAGOS, {
        method: "POST",
        body: {
          order_id: orderId,
          policy_id: policyId,
          account_id: accountId,
          method_id: methodId,
          monto,
          fecha_pago: fechaPago,
          concepto,
          documentos,
          idempotency_key: idempotencyKey,
        },
      });
    },
    onSuccess: async (pagoCreado) => {
      await queryClient.invalidateQueries({ queryKey: CONSULTA_PAGOS });
      notify({
        type: "success",
        title: esEdicion ? "Pago actualizado" : "Pago creado",
        description: "El borrador del pago quedó guardado.",
      });
      navigate(`${RUTA_PAGOS}/${pagoCreado.id}`);
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError) {
        setErrorFormulario(error.message);
        if (error.fieldErrors && typeof error.fieldErrors === "object") {
          setFieldErrors(error.fieldErrors as Record<string, string[]>);
        } else {
          setFieldErrors({});
        }
      } else if (error instanceof Error) {
        setErrorFormulario(error.message);
        setFieldErrors({});
      } else {
        setErrorFormulario("No se pudo completar la acción.");
        setFieldErrors({});
      }
    },
  });

  const ordenSeleccionada = useMemo(() => {
    if (!opciones || !orderId) return null;
    return opciones.ordenes.find((orden) => orden.id === orderId) ?? null;
  }, [opciones, orderId]);

  const politicaSeleccionada = useMemo(() => {
    if (!opciones || !policyId) return null;
    return opciones.politicas.find((politica) => politica.id === policyId) ?? null;
  }, [opciones, policyId]);

  useEffect(() => {
    if (!ordenSeleccionada || !opciones) return;
    const politicasDeLaMoneda = opciones.politicas.filter(
      (politica) => politica.moneda === ordenSeleccionada.moneda,
    );
    if (!politicasDeLaMoneda.some((politica) => politica.id === policyId)) {
      setPolicyId(politicasDeLaMoneda[0]?.id ?? "");
    }
    const cuentasDeLaMoneda = opciones.cuentas.filter(
      (cuenta) => cuenta.moneda === ordenSeleccionada.moneda,
    );
    if (!cuentasDeLaMoneda.some((cuenta) => cuenta.id === accountId)) {
      setAccountId(cuentasDeLaMoneda[0]?.id ?? "");
    }
  }, [ordenSeleccionada, opciones, policyId, accountId]);

  useEffect(() => {
    if (!politicaSeleccionada || !opciones) return;
    if (!politicaSeleccionada.medios.includes(methodId)) {
      setMethodId(politicaSeleccionada.medios[0] ?? "");
    }
  }, [politicaSeleccionada, opciones, methodId]);

  if (!tienePermiso) {
    return (
      <PageContent>
        <EmptyState
          title="No tiene permiso para preparar pagos"
          description="Su rol no incluye la capacidad de gestión de pagos de tesorería."
        />
      </PageContent>
    );
  }

  if (esEdicion && pagoQuery.data === null) {
    return (
      <PageContent>
        <EmptyState
          title="Pago no encontrado"
          description="El pago solicitado no existe o no está disponible."
        />
      </PageContent>
    );
  }

  if (esEdicion && pago && pago.estado !== "BORRADOR") {
    return (
      <PageContent>
        <EmptyState
          title="El pago ya no es editable"
          description={`Solo los pagos en estado Borrador pueden editarse. Este pago está en estado ${pago.estado}.`}
        />
        <div className="mt-4 flex justify-center gap-2">
          <Link
            to={`${RUTA_PAGOS}/${pago.id}`}
            className="inline-flex items-center rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Ver detalle del pago
          </Link>
          <Link
            to={RUTA_PAGOS}
            className="inline-flex items-center rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Volver a pagos
          </Link>
        </div>
      </PageContent>
    );
  }

  const politicasDeLaMoneda = ordenSeleccionada
    ? (opciones?.politicas ?? []).filter(
        (politica) => politica.moneda === ordenSeleccionada.moneda,
      )
    : [];

  const cuentasDeLaMoneda = ordenSeleccionada
    ? (opciones?.cuentas ?? []).filter(
        (cuenta) => cuenta.moneda === ordenSeleccionada.moneda,
      )
    : [];

  const mediosDeLaPolitica = politicaSeleccionada
    ? (opciones?.medios ?? []).filter((medio) =>
        politicaSeleccionada.medios.includes(medio.id),
      )
    : [];

  const ayudaMonto =
    politicaSeleccionada && !politicaSeleccionada.permite_pago_parcial
      ? "Esta política exige pagar el disponible completo"
      : undefined;

  const manejarEnvio = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setErrorFormulario("");
    setFieldErrors({});
    mutacion.mutate();
  };

  const tituloPagina = esEdicion
    ? `Editar pago ${pago?.codigo ?? "borrador"}`
    : "Nuevo pago";

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno", to: "/gobierno" },
          { label: "Tesorería", to: RUTA_PAGOS },
          { label: "Pagos" },
          { label: tituloPagina },
        ]}
        title={tituloPagina}
        description="Preparación de un pago de tesorería"
        actions={
          <Link
            to={RUTA_PAGOS}
            className="inline-flex items-center rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Cancelar
          </Link>
        }
      />

      {pagoQuery.isLoading && <LoadingState label="Cargando pago" />}
      {pagoQuery.isError && (
        <ErrorState
          title="No se pudo cargar el pago"
          message={
            pagoQuery.error instanceof Error
              ? pagoQuery.error.message
              : "No se pudo completar la acción."
          }
          requestId={pagoQuery.error instanceof ApiError ? pagoQuery.error.requestId : undefined}
          onRetry={() => void pagoQuery.refetch()}
        />
      )}

      {!esEdicion && opcionesQuery.isLoading && <LoadingState label="Cargando opciones de pago" />}
      {esEdicion && (!pago || !inicializado) && <LoadingState label="Cargando pago" />}

      {opcionesQuery.isError && (
        <ErrorState
          title="No se pudieron cargar las opciones de pago"
          message={
            opcionesQuery.error instanceof Error
              ? opcionesQuery.error.message
              : "No se pudo completar la acción."
          }
          requestId={
            opcionesQuery.error instanceof ApiError ? opcionesQuery.error.requestId : undefined
          }
          onRetry={() => void opcionesQuery.refetch()}
        />
      )}

      {((!esEdicion && opciones) || (esEdicion && pago && inicializado)) && (
        <form className="mt-6 space-y-6" onSubmit={manejarEnvio}>
          {errorFormulario && (
            <div
              role="alert"
              className="rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700"
            >
              {errorFormulario}
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <FormField
              label="Orden de pago"
              htmlFor="pago-orden"
              required
              help={fieldErrors.order_id?.join(", ")}
            >
              <select
                id="pago-orden"
                value={orderId}
                onChange={(event) => setOrderId(event.target.value)}
                disabled={esEdicion}
                className="block w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="">Seleccione una orden</option>
                {(opciones?.ordenes ?? []).map((orden) => (
                  <option key={orden.id} value={orden.id}>
                    {`${orden.codigo ?? "Borrador"} · ${orden.beneficiario ?? "Sin beneficiario"} · ${orden.moneda} · disponible ${orden.disponible_para_pago}`}
                  </option>
                ))}
              </select>
            </FormField>

            {ordenSeleccionada && (
              <div className="rounded-md border border-slate-200 bg-slate-50 p-4 sm:col-span-2 lg:col-span-3">
                <dl className="grid grid-cols-2 gap-4 sm:grid-cols-5">
                  <div>
                    <dt className="text-xs font-semibold text-slate-700">Ordenado</dt>
                    <dd className="text-sm">{ordenSeleccionada.monto_ordenado}</dd>
                  </div>
                  <div>
                    <dt className="text-xs font-semibold text-slate-700">Pagado</dt>
                    <dd className="text-sm">{ordenSeleccionada.monto_pagado}</dd>
                  </div>
                  <div>
                    <dt className="text-xs font-semibold text-slate-700">En trámite</dt>
                    <dd className="text-sm">{ordenSeleccionada.monto_en_tramite}</dd>
                  </div>
                  <div>
                    <dt className="text-xs font-semibold text-slate-700">Pendiente de pagar</dt>
                    <dd className="text-sm">{ordenSeleccionada.pendiente_de_pagar}</dd>
                  </div>
                  <div>
                    <dt className="text-xs font-semibold text-slate-700">
                      Disponible para un nuevo pago
                    </dt>
                    <dd className="text-sm">{ordenSeleccionada.disponible_para_pago}</dd>
                  </div>
                </dl>
              </div>
            )}

            <FormField label="Política" htmlFor="pago-politica" required>
              <select
                id="pago-politica"
                value={policyId}
                onChange={(event) => setPolicyId(event.target.value)}
                className="block w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="">Seleccione una política</option>
                {politicasDeLaMoneda.map((politica) => (
                  <option key={politica.id} value={politica.id}>
                    {`${politica.codigo} v${politica.numero_version} · ${politica.nombre}`}
                  </option>
                ))}
              </select>
            </FormField>

            <FormField label="Cuenta" htmlFor="pago-cuenta" required>
              <select
                id="pago-cuenta"
                value={accountId}
                onChange={(event) => setAccountId(event.target.value)}
                className="block w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="">Seleccione una cuenta</option>
                {cuentasDeLaMoneda.map((cuenta) => (
                  <option key={cuenta.id} value={cuenta.id}>
                    {`${cuenta.codigo} · ${cuenta.denominacion} · ${cuenta.numero_enmascarado}`}
                  </option>
                ))}
              </select>
            </FormField>

            <FormField label="Medio de pago" htmlFor="pago-medio" required>
              <select
                id="pago-medio"
                value={methodId}
                onChange={(event) => setMethodId(event.target.value)}
                className="block w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="">Seleccione un medio</option>
                {mediosDeLaPolitica.map((medio) => (
                  <option key={medio.id} value={medio.id}>
                    {`${medio.codigo} · ${medio.nombre}`}
                  </option>
                ))}
              </select>
            </FormField>

            <FormField label="Monto" htmlFor="pago-monto" required help={ayudaMonto}>
              <TextInput
                id="pago-monto"
                value={monto}
                onChange={(event) => setMonto(event.target.value)}
                placeholder="0.00"
              />
            </FormField>

            <FormField label="Fecha de pago" htmlFor="pago-fecha" required>
              <TextInput
                id="pago-fecha"
                type="date"
                value={fechaPago}
                onChange={(event) => setFechaPago(event.target.value)}
              />
            </FormField>

            <FormField label="Concepto" htmlFor="pago-concepto">
              <TextInput
                id="pago-concepto"
                value={concepto}
                onChange={(event) => setConcepto(event.target.value)}
                placeholder="Concepto del pago"
              />
            </FormField>
          </div>

          <fieldset>
            <legend className="text-sm font-semibold text-slate-700">
              Documentos de preparación
            </legend>
            <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {(opciones?.documentos ?? []).map((documento) => (
                <label
                  key={documento.id}
                  className="flex items-start gap-2 rounded-md border border-slate-200 p-3 text-sm"
                >
                  <input
                    type="checkbox"
                    checked={documentosSeleccionados.has(documento.id)}
                    onChange={(event) => {
                      const nuevos = new Set(documentosSeleccionados);
                      if (event.target.checked) {
                        nuevos.add(documento.id);
                      } else {
                        nuevos.delete(documento.id);
                      }
                      setDocumentosSeleccionados(nuevos);
                    }}
                    className="mt-0.5"
                  />
                  <span>
                    <span className="font-medium">{documento.titulo}</span>
                    {documento.tipo && (
                      <span className="text-slate-600"> · {documento.tipo}</span>
                    )}
                  </span>
                </label>
              ))}
            </div>
          </fieldset>

          <p className="text-sm text-slate-600">
            El borrador no consume saldo. Al enviarlo se reserva el monto y se congela la política.
          </p>

          <div className="flex justify-end gap-2">
            <Button variant="secondary" type="button" onClick={() => navigate(RUTA_PAGOS)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={mutacion.isPending}>
              {mutacion.isPending ? "Guardando…" : "Guardar borrador"}
            </Button>
          </div>
        </form>
      )}
    </PageContent>
  );
}
