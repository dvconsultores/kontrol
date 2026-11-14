import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Button } from "@/components/Button";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { formatearInstante } from "@/lib/fecha-de-negocio";
import { CONSULTA_EXPEDIENTES } from "../api";

export type MontoOferta = {
  version: number;
  moneda: string;
  monto_sin_iva: string;
  tributos: string;
  total_con_tributos: string;
  suma_coincide: boolean;
  diferencia: string;
  soporte_tipo: string;
  soporte_etiqueta: string;
  soporte_titulo: string | null;
  soporte_version: number;
  soporte_huella: string;
  motivo: string | null;
  registrada_por: string | null;
  registrada_en: string;
};

export type SoporteMonto = {
  tipo: string;
  etiqueta: string;
  documento_id: string;
  titulo: string | null;
  version: number;
};

export type OfertaConMonto = {
  id: string;
  referencia: string;
  monto_estado: string;
  monto_estado_etiqueta: string;
  monto: MontoOferta | null;
  monto_bloqueo: string | null;
  montos_historial: MontoOferta[];
  soportes_monto: SoporteMonto[];
};

const selectClass =
  "block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600";

type FormularioMonto = {
  moneda: string;
  monto_sin_iva: string;
  tributos: string;
  total_con_tributos: string;
  soporte: string;
  motivo: string;
};

export function OfertaMonto({
  oferta,
  expedienteId,
  version,
  activeCompanyId,
}: {
  oferta: OfertaConMonto;
  expedienteId: string;
  version: number;
  activeCompanyId: string | null;
}) {
  const queryClient = useQueryClient();
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const [formularioAbierto, setFormularioAbierto] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null);
  const [erroresCampos, setErroresCampos] = useState<Record<string, string[]>>({});

  const puedeDeclarar =
    tiene("gobierno_ofertas:amount", "empresa") && oferta.monto_bloqueo === null;

  const [form, setForm] = useState<FormularioMonto>({
    moneda: oferta.monto?.moneda ?? "VES",
    monto_sin_iva: oferta.monto?.monto_sin_iva ?? "",
    tributos: oferta.monto?.tributos ?? "",
    total_con_tributos: oferta.monto?.total_con_tributos ?? "",
    soporte: "",
    motivo: "",
  });

  const abrirFormulario = () => {
    setForm({
      moneda: oferta.monto?.moneda ?? "VES",
      monto_sin_iva: oferta.monto?.monto_sin_iva ?? "",
      tributos: oferta.monto?.tributos ?? "",
      total_con_tributos: oferta.monto?.total_con_tributos ?? "",
      soporte: "",
      motivo: "",
    });
    setErrorGeneral(null);
    setErroresCampos({});
    setFormularioAbierto(true);
  };

  const cerrarFormulario = () => {
    setFormularioAbierto(false);
    setErrorGeneral(null);
    setErroresCampos({});
  };

  const enviar = async (evento: React.FormEvent<HTMLFormElement>) => {
    evento.preventDefault();
    setEnviando(true);
    setErrorGeneral(null);
    setErroresCampos({});

    const [soporteTipo, soporteDocumentoId] = form.soporte.split("|");

    try {
      await apiFetch<OfertaConMonto>(
        `/gobierno/contrataciones/expedientes/${expedienteId}/ofertas/${oferta.id}/montos`,
        {
          method: "POST",
          body: {
            moneda: form.moneda,
            monto_sin_iva: form.monto_sin_iva,
            tributos: form.tributos,
            total_con_tributos: form.total_con_tributos,
            soporte_tipo: soporteTipo,
            soporte_documento_id: soporteDocumentoId,
            motivo: oferta.monto ? form.motivo : null,
            version_anterior: oferta.monto?.version ?? null,
          },
          ifMatch: String(version),
        },
      );
      notify({ type: "success", title: "Monto registrado" });
      cerrarFormulario();
      queryClient.invalidateQueries({
        queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId],
      });
    } catch (err) {
      if (err instanceof ApiError) {
        if (
          err.code === "GOV_PROCUREMENT_FILE_STALE" ||
          err.code === "GOV_OFFER_AMOUNT_STALE"
        ) {
          setErrorGeneral("El expediente o el monto cambió; recargue la oferta");
          queryClient.invalidateQueries({
            queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId],
          });
        } else if (err.fieldErrors && Object.keys(err.fieldErrors).length > 0) {
          setErroresCampos(err.fieldErrors);
        } else {
          setErrorGeneral(err.message || "No fue posible registrar el monto");
        }
      } else {
        setErrorGeneral("No fue posible registrar el monto");
      }
    } finally {
      setEnviando(false);
    }
  };

  const motivoInvalido =
    oferta.monto !== null && form.motivo.trim().length < 10;

  return (
    <section aria-labelledby={`monto-${oferta.id}`} className="mt-4">
      <h3 id={`monto-${oferta.id}`} className="text-sm font-semibold text-text-900">
        Monto declarado
      </h3>

      {oferta.monto ? (
        <>
          <dl className="grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="min-w-0 break-words">
              <dt className="text-xs font-medium text-text-600">Moneda</dt>
              <dd className="text-sm text-text-900">{oferta.monto.moneda}</dd>
            </div>
            <div className="min-w-0 break-words">
              <dt className="text-xs font-medium text-text-600">
                Monto del objeto sin IVA
              </dt>
              <dd className="text-sm text-text-900">
                {oferta.monto.monto_sin_iva} {oferta.monto.moneda}
              </dd>
            </div>
            <div className="min-w-0 break-words">
              <dt className="text-xs font-medium text-text-600">Tributos</dt>
              <dd className="text-sm text-text-900">
                {oferta.monto.tributos} {oferta.monto.moneda}
              </dd>
            </div>
            <div className="min-w-0 break-words">
              <dt className="text-xs font-medium text-text-600">
                Total con tributos
              </dt>
              <dd className="text-sm text-text-900">
                {oferta.monto.total_con_tributos} {oferta.monto.moneda}
              </dd>
            </div>
            <div className="min-w-0 break-words">
              <dt className="text-xs font-medium text-text-600">
                Documento soporte
              </dt>
              <dd className="text-sm text-text-900">
                {oferta.monto.soporte_etiqueta} ·{" "}
                {oferta.monto.soporte_titulo ?? "Sin título"} · Versión{" "}
                {oferta.monto.soporte_version}
              </dd>
            </div>
            <div className="min-w-0 break-words">
              <dt className="text-xs font-medium text-text-600">Registrado</dt>
              <dd className="text-sm text-text-900">
                Versión {oferta.monto.version} ·{" "}
                {oferta.monto.registrada_por ?? "—"} ·{" "}
                {formatearInstante(oferta.monto.registrada_en)}
              </dd>
            </div>
          </dl>
          {!oferta.monto.suma_coincide && (
            <p
              role="note"
              className="mt-2 text-sm font-medium text-amber-800"
            >
              La suma declarada no coincide con el total (diferencia{" "}
              {oferta.monto.diferencia} {oferta.monto.moneda}).
            </p>
          )}
        </>
      ) : (
        <p className="text-sm text-text-800">{oferta.monto_estado_etiqueta}</p>
      )}

      {oferta.monto_bloqueo && (
        <p className="mt-2 text-sm text-text-600">{oferta.monto_bloqueo}</p>
      )}

      {puedeDeclarar && !formularioAbierto && (
        <div className="mt-3">
          <Button
            variant="secondary"
            type="button"
            onClick={abrirFormulario}
            aria-label={`${oferta.monto ? "Corregir monto" : "Declarar monto"} de ${oferta.referencia}`}
          >
            {oferta.monto ? "Corregir monto" : "Declarar monto"}
          </Button>
        </div>
      )}

      {puedeDeclarar && formularioAbierto && (
        <form onSubmit={enviar} className="mt-4 space-y-4 border-t border-border-subtle pt-4">
          <FormField
            label="Moneda"
            htmlFor={`moneda-${oferta.id}`}
            error={erroresCampos.moneda?.[0]}
          >
            <select
              id={`moneda-${oferta.id}`}
              className={selectClass}
              value={form.moneda}
              onChange={(evento) =>
                setForm({ ...form, moneda: evento.target.value })
              }
            >
              <option value="VES">VES</option>
              <option value="USD">USD</option>
              <option value="EUR">EUR</option>
            </select>
          </FormField>
          <FormField
            label="Monto del objeto sin IVA"
            htmlFor={`monto-sin-iva-${oferta.id}`}
            error={erroresCampos.monto_sin_iva?.[0]}
          >
            <TextInput
              id={`monto-sin-iva-${oferta.id}`}
              inputMode="decimal"
              placeholder="0.00"
              value={form.monto_sin_iva}
              onChange={(evento) =>
                setForm({ ...form, monto_sin_iva: evento.target.value })
              }
            />
          </FormField>
          <FormField
            label="Tributos"
            htmlFor={`tributos-${oferta.id}`}
            error={erroresCampos.tributos?.[0]}
          >
            <TextInput
              id={`tributos-${oferta.id}`}
              inputMode="decimal"
              placeholder="0.00"
              value={form.tributos}
              onChange={(evento) =>
                setForm({ ...form, tributos: evento.target.value })
              }
            />
          </FormField>
          <FormField
            label="Total con tributos"
            htmlFor={`total-con-tributos-${oferta.id}`}
            error={erroresCampos.total_con_tributos?.[0]}
          >
            <TextInput
              id={`total-con-tributos-${oferta.id}`}
              inputMode="decimal"
              placeholder="0.00"
              value={form.total_con_tributos}
              onChange={(evento) =>
                setForm({ ...form, total_con_tributos: evento.target.value })
              }
            />
          </FormField>
          <FormField
            label="Documento soporte"
            htmlFor={`soporte-${oferta.id}`}
            error={erroresCampos.soporte_documento_id?.[0]}
          >
            <select
              id={`soporte-${oferta.id}`}
              className={selectClass}
              value={form.soporte}
              onChange={(evento) =>
                setForm({ ...form, soporte: evento.target.value })
              }
            >
              <option value="">Seleccione</option>
              {oferta.soportes_monto.map((soporte) => (
                <option
                  key={`${soporte.tipo}-${soporte.documento_id}`}
                  value={`${soporte.tipo}|${soporte.documento_id}`}
                >
                  {soporte.etiqueta} · {soporte.titulo ?? "Sin título"} · Versión{" "}
                  {soporte.version}
                </option>
              ))}
            </select>
          </FormField>
          {oferta.monto && (
            <FormField
              label="Motivo de la corrección"
              htmlFor={`motivo-${oferta.id}`}
              error={erroresCampos.motivo?.[0]}
              help="Mínimo 10 caracteres"
            >
              <textarea
                id={`motivo-${oferta.id}`}
                className={selectClass}
                value={form.motivo}
                onChange={(evento) =>
                  setForm({ ...form, motivo: evento.target.value })
                }
              />
            </FormField>
          )}
          {errorGeneral && (
            <p role="alert" className="text-sm text-red-700">
              {errorGeneral}
            </p>
          )}
          <div className="flex flex-wrap gap-2">
            <Button
              variant="primary"
              type="submit"
              disabled={enviando || motivoInvalido}
            >
              Registrar monto
            </Button>
            <Button
              variant="secondary"
              type="button"
              onClick={cerrarFormulario}
            >
              Cancelar
            </Button>
          </div>
        </form>
      )}

      {oferta.montos_historial.length > 1 && (
        <div className="mt-4">
          <h4 className="text-sm font-semibold text-text-900">
            Historial del monto
          </h4>
          <ul className="mt-2 space-y-2">
            {oferta.montos_historial.map((historial) => (
              <li key={historial.version} className="text-sm text-text-900">
                Versión {historial.version} · {historial.total_con_tributos}{" "}
                {historial.moneda} · {historial.registrada_por ?? "—"} ·{" "}
                {formatearInstante(historial.registrada_en)}
                {historial.motivo && ` · Motivo: ${historial.motivo}`}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
