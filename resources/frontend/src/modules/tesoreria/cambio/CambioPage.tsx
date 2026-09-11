/**
 * Política cambiaria y conversión de moneda — Spec 038.
 *
 * `OWNER-DECISION-038-02`: la política es **parametrizable** y la conversión
 * **explícita**. Por eso esta pantalla no tiene una sola regla venezolana
 * escrita: la política se configura, se versiona y guarda de qué autoridad
 * viene. `D0-07` sigue abierto y nada de aquí homologa nada.
 *
 * Dos cosas que la pantalla hace visibles a propósito. La tasa **no se
 * inventa**: si nadie registró una, el backend se niega y aquí se lee el
 * motivo, en lugar del uno a uno silencioso que había antes. Y una política
 * nace en borrador: activarla es otro acto, de otra persona con permiso de
 * aprobación, que **sustituye** la versión anterior sin borrarla.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { ApiError, apiFetch } from "@/api/client";
import type { FinancialAccountSummary, FxConversion, FxPolicy } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { FormField } from "@/components/FormField";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";

const SELECT =
  "h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900";

const ORIGEN: Record<string, string> = {
  REGISTERED: "Tasa registrada",
  MANUAL: "Tasa manual",
};

export function CambioPage(): React.JSX.Element {
  const qc = useQueryClient();
  const { notify } = useNotifications();

  const [codigo, setCodigo] = useState("");
  const [funcional, setFuncional] = useState("VED");
  const [desde, setDesde] = useState("");
  const [fuente, setFuente] = useState("BCV");
  const [cruzada, setCruzada] = useState(true);
  const [manual, setManual] = useState(false);
  const [reembolso, setReembolso] = useState(true);
  const [autoridad, setAutoridad] = useState("");

  const [origen, setOrigen] = useState("");
  const [destino, setDestino] = useState("");
  const [importe, setImporte] = useState("");
  const [tasaManual, setTasaManual] = useState("");
  const [motivoTasa, setMotivoTasa] = useState("");

  // `/treasury/accounts` devuelve la lista entera de la empresa, sin paginar:
  // no hay tope que agotar aquí. Donde sí lo hay —los selectores paginados— se
  // recorre hasta `total`, nunca con un `limit` inventado.
  const cuentas = useQuery({
    queryKey: ["fx", "cuentas"],
    queryFn: () => apiFetch<{ items: FinancialAccountSummary[] }>("/treasury/accounts"),
  });

  const politicas = useQuery({
    queryKey: ["fx", "politicas"],
    queryFn: () => apiFetch<{ items: FxPolicy[] }>("/treasury/fx-policies"),
  });

  const conversiones = useQuery({
    queryKey: ["fx", "conversiones"],
    queryFn: () => apiFetch<{ items: FxConversion[] }>("/treasury/fx-conversions"),
  });

  function fallo(titulo: string) {
    return (e: unknown) =>
      notify({
        type: "error",
        title: titulo,
        description: e instanceof ApiError ? e.message : undefined,
      });
  }

  async function refrescar(): Promise<void> {
    await qc.invalidateQueries({ queryKey: ["fx"] });
  }

  const activa = (politicas.data?.items ?? []).find((p) => p.status === "ACTIVE");
  const cuentaOrigen = (cuentas.data?.items ?? []).find((c) => c.id === origen);
  const cuentaDestino = (cuentas.data?.items ?? []).find((c) => c.id === destino);
  const mismaMoneda =
    Boolean(cuentaOrigen && cuentaDestino) &&
    cuentaOrigen?.currency === cuentaDestino?.currency;

  async function crearPolitica(): Promise<void> {
    if (!codigo.trim() || !funcional.trim() || !desde) {
      notify({ type: "error", title: "Indique código, moneda funcional y vigencia" });
      return;
    }
    try {
      await apiFetch("/treasury/fx-policies", {
        method: "POST",
        body: {
          policy_code: codigo,
          functional_currency: funcional,
          effective_from: desde,
          rate_source: fuente || null,
          allow_cross_currency: cruzada,
          allow_manual_rate: manual,
          allow_refund: reembolso,
          authority_reference: autoridad || null,
        },
      });
      notify({
        type: "success",
        title: "Política creada en borrador",
        description: "Todavía no rige: hay que activarla.",
      });
      setCodigo("");
      setAutoridad("");
      await refrescar();
    } catch (e) {
      fallo("No se pudo crear la política")(e);
    }
  }

  async function activar(p: FxPolicy): Promise<void> {
    try {
      await apiFetch(`/treasury/fx-policies/${p.id}/activate`, { method: "POST", body: {} });
      notify({
        type: "success",
        title: `Rige ${p.policy_code} v${p.version}`,
        description: "La versión anterior queda sustituida; no se borra.",
      });
      await refrescar();
    } catch (e) {
      fallo("No se pudo activar la política")(e);
    }
  }

  async function convertir(): Promise<void> {
    if (!origen || !destino || Number(importe) <= 0) {
      notify({ type: "error", title: "Indique las dos cuentas y el importe" });
      return;
    }
    try {
      const c = await apiFetch<FxConversion>("/treasury/fx-conversions", {
        method: "POST",
        body: {
          source_account_id: origen,
          target_account_id: destino,
          source_amount: importe,
          manual_rate: tasaManual || null,
          manual_reason: motivoTasa || null,
        },
      });
      notify({
        type: "success",
        title: "Conversión registrada",
        description: `${c.source_amount} ${c.source_currency} → ${c.target_amount} ${c.target_currency} a ${c.rate}.`,
      });
      setImporte("");
      setTasaManual("");
      setMotivoTasa("");
      await refrescar();
    } catch (e) {
      fallo("No se pudo convertir")(e);
    }
  }

  return (
    <PageContent>
      <PageHeader
        title="Cambio de moneda"
        description={
          "La política se configura y se versiona; la tasa nunca se inventa. " +
          "Ninguna regla legal está escrita en el código."
        }
        crumbs={[{ label: "Tesorería" }, { label: "Cambio de moneda" }]}
      />

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Política vigente</h2>
        {activa ? (
          <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm sm:grid-cols-3">
            <dt className="text-text-700">Política</dt>
            <dd>
              {activa.policy_code} · v{activa.version}
            </dd>
            <dt className="text-text-700">Moneda funcional</dt>
            <dd>{activa.functional_currency}</dd>
            <dt className="text-text-700">Fuente de tasa</dt>
            <dd>{activa.rate_source ?? "—"}</dd>
            <dt className="text-text-700">Conversión entre monedas</dt>
            <dd>{activa.allow_cross_currency ? "Permitida" : "No permitida"}</dd>
            <dt className="text-text-700">Tasa manual</dt>
            <dd>{activa.allow_manual_rate ? "Permitida con motivo" : "No permitida"}</dd>
            <dt className="text-text-700">Reembolso en efectivo</dt>
            <dd>{activa.allow_refund ? "Permitido" : "No permitido"}</dd>
            <dt className="text-text-700">Autoridad</dt>
            <dd>{activa.authority_reference ?? "Sin referencia declarada"}</dd>
          </dl>
        ) : (
          <p className="text-sm text-text-700" role="status">
            No hay política activa. Sin política no se convierte ni se reembolsa: el sistema
            prefiere negarse a suponer una regla.
          </p>
        )}
      </section>

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Nueva versión de política</h2>
        <div className="mb-3 flex flex-wrap items-end gap-3">
          <FormField label="Código" required>
            <TextInput value={codigo} onChange={(e) => setCodigo(e.target.value)} placeholder="FX-GENERAL" />
          </FormField>
          <FormField label="Moneda funcional" required>
            <TextInput value={funcional} onChange={(e) => setFuncional(e.target.value)} />
          </FormField>
          <FormField label="Vigente desde" required>
            <TextInput type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
          </FormField>
          <FormField label="Fuente de tasa">
            <TextInput value={fuente} onChange={(e) => setFuente(e.target.value)} placeholder="BCV" />
          </FormField>
          <FormField label="Autoridad que la respalda">
            <TextInput
              value={autoridad}
              onChange={(e) => setAutoridad(e.target.value)}
              placeholder="De dónde sale esta regla"
            />
          </FormField>
        </div>
        <div className="mb-3 flex flex-wrap gap-4 text-sm">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={cruzada} onChange={(e) => setCruzada(e.target.checked)} />
            Permitir conversión entre monedas
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={manual} onChange={(e) => setManual(e.target.checked)} />
            Permitir tasa manual (exige motivo)
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={reembolso} onChange={(e) => setReembolso(e.target.checked)} />
            Permitir reembolso en efectivo
          </label>
        </div>
        <AsyncButton onClick={crearPolitica}>Crear en borrador</AsyncButton>
        <p className="mt-2 text-sm text-text-500">
          Nace en borrador. Activarla es un acto aparte, con permiso de aprobación.
        </p>
      </section>

      <section className="mb-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Versiones</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <caption className="sr-only">Versiones de política cambiaria</caption>
            <thead>
              <tr className="border-b border-border-default text-left text-text-700">
                <th scope="col" className="py-1">Código</th>
                <th scope="col">Versión</th>
                <th scope="col">Funcional</th>
                <th scope="col">Desde</th>
                <th scope="col">Hasta</th>
                <th scope="col">Estado</th>
                <th scope="col">Acción</th>
              </tr>
            </thead>
            <tbody>
              {(politicas.data?.items ?? []).map((p) => (
                <tr key={p.id} className="border-b border-border-subtle">
                  <td className="py-1">{p.policy_code}</td>
                  <td>v{p.version}</td>
                  <td>{p.functional_currency}</td>
                  <td>{p.effective_from}</td>
                  <td>{p.effective_to ?? "—"}</td>
                  <td>{p.status}</td>
                  <td>
                    {p.status === "DRAFT" ? (
                      <AsyncButton size="sm" variant="secondary" onClick={() => activar(p)}>
                        Activar
                      </AsyncButton>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Convertir</h2>
        <div className="mb-3 flex flex-wrap items-end gap-3">
          <FormField label="Cuenta de origen" required>
            <select
              value={origen}
              onChange={(e) => setOrigen(e.target.value)}
              className={SELECT}
              aria-label="Cuenta de origen"
            >
              <option value="">Seleccionar…</option>
              {(cuentas.data?.items ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.code} · {c.name} ({c.currency})
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Cuenta de destino" required>
            <select
              value={destino}
              onChange={(e) => setDestino(e.target.value)}
              className={SELECT}
              aria-label="Cuenta de destino"
            >
              <option value="">Seleccionar…</option>
              {(cuentas.data?.items ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.code} · {c.name} ({c.currency})
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Importe de origen" required>
            <TextInput value={importe} onChange={(e) => setImporte(e.target.value)} placeholder="0.00" />
          </FormField>
          {activa?.allow_manual_rate ? (
            <>
              <FormField label="Tasa manual">
                <TextInput value={tasaManual} onChange={(e) => setTasaManual(e.target.value)} placeholder="Opcional" />
              </FormField>
              <FormField label="Motivo de la tasa manual">
                <TextInput
                  value={motivoTasa}
                  onChange={(e) => setMotivoTasa(e.target.value)}
                  placeholder="Por qué no se usa la registrada"
                />
              </FormField>
            </>
          ) : null}
          <AsyncButton onClick={convertir} disabled={mismaMoneda}>
            Convertir
          </AsyncButton>
        </div>
        {mismaMoneda ? (
          <p className="text-sm text-text-700" role="status">
            Las dos cuentas están en la misma moneda. Eso es una transferencia, no un cambio.
          </p>
        ) : (
          <p className="text-sm text-text-500">
            Si no hay tasa registrada para el día, la operación se rechaza. No se supone uno a uno.
          </p>
        )}
      </section>

      <section>
        <h2 className="mb-2 text-base font-semibold text-text-900">Conversiones</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <caption className="sr-only">Conversiones ejecutadas</caption>
            <thead>
              <tr className="border-b border-border-default text-left text-text-700">
                <th scope="col" className="py-1">Fecha de tasa</th>
                <th scope="col">Entregado</th>
                <th scope="col">Recibido</th>
                <th scope="col">Tasa</th>
                <th scope="col">Procedencia</th>
                <th scope="col">Política</th>
              </tr>
            </thead>
            <tbody>
              {(conversiones.data?.items ?? []).map((c) => (
                <tr key={c.id} className="border-b border-border-subtle">
                  <td className="py-1">{c.rate_date ?? "—"}</td>
                  <td className="font-mono">
                    {c.source_amount} {c.source_currency}
                  </td>
                  <td className="font-mono">
                    {c.target_amount} {c.target_currency}
                  </td>
                  <td className="font-mono">{c.rate ?? "—"}</td>
                  <td>
                    {c.rate_origin ? (ORIGEN[c.rate_origin] ?? c.rate_origin) : "—"}
                    {c.rate_source ? ` · ${c.rate_source}` : ""}
                  </td>
                  <td>{c.policy_version ? `v${c.policy_version}` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </PageContent>
  );
}
