/**
 * Estado de cuenta del cliente — Spec 037.
 *
 * «Saldo = documentos + débitos − cobros − retenciones − créditos»
 * (arquitectura funcional §9). Ninguna cifra de esta pantalla se calcula aquí:
 * todas vienen del backend, que usa el motor de saldos compartido en `Decimal`.
 *
 * Dos cosas que la pantalla hace explícitas porque el dominio las exige. El
 * crédito de un cliente solo se ofrece contra documentos **suyos** —y el
 * backend lo vuelve a comprobar, porque filtrar en el navegador no es
 * seguridad—. Y revertir una aplicación **no la borra**: crea su evento
 * inverso, así que el botón no dice «eliminar» y nunca lo dirá.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { ApiError, apiFetch } from "@/api/client";
import type {
  CreditApplicationResult,
  CreditApplicationRow,
  CustomerCredit,
  CustomerStatement,
  OpenItem,
  PagedResult,
  Party,
} from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { Autorizado } from "@/components/Autorizado";
import { AsyncButton } from "@/components/AsyncButton";
import { FormField } from "@/components/FormField";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";

const SELECT =
  "h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900";

const TIPO: Record<string, string> = {
  DOCUMENT: "Documento",
  CREDIT_NOTE: "Nota de crédito",
  APPLICATION: "Aplicación",
  APPLICATION_REVERSAL: "Reverso de aplicación",
};

function corto(id: string): string {
  return `${id.slice(0, 8)}…`;
}

export function EstadoDeCuentaPage(): React.JSX.Element {
  const qc = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();
  const [clienteId, setClienteId] = useState("");
  const [creditoId, setCreditoId] = useState("");
  const [documentoId, setDocumentoId] = useState("");
  const [importe, setImporte] = useState("");
  const [motivo, setMotivo] = useState("");

  const clientes = useQuery({
    queryKey: ["cxc", "clientes"],
    // Se pide hasta agotar `total` en vez de confiar en un tope. El endpoint
    // pagina con `page`/`page_size` y su máximo es 100: un `limit` inventado se
    // ignora en silencio y el desplegable se queda con los veinte por defecto,
    // sin que nada lo diga. Es la misma clase de defecto que el selector de
    // almacén de la Spec 031.
    queryFn: async () => {
      const items: Party[] = [];
      for (let page = 1; ; page += 1) {
        const p = await apiFetch<PagedResult<Party>>(
          `/maestros/terceros?page=${page}&page_size=100`,
        );
        items.push(...p.items);
        if (items.length >= p.total || p.items.length === 0) break;
      }
      return { items, total: items.length, page: 1, page_size: items.length };
    },
    retry: false,
  });

  const estado = useQuery({
    queryKey: ["cxc", "estado", clienteId],
    queryFn: () =>
      apiFetch<CustomerStatement>(`/sales/cxc/clientes/${clienteId}/estado-de-cuenta`),
    enabled: Boolean(clienteId),
  });

  const creditos = useQuery({
    queryKey: ["cxc", "creditos", clienteId],
    queryFn: () => apiFetch<{ items: CustomerCredit[] }>(`/sales/cxc/clientes/${clienteId}/creditos`),
    enabled: Boolean(clienteId),
  });

  // Solo los documentos **de este cliente**: un crédito no se aplica al de otro.
  const documentos = useQuery({
    queryKey: ["cxc", "documentos", clienteId],
    queryFn: () =>
      apiFetch<{ items: OpenItem[] }>(`/sales/open-items?party_id=${clienteId}&status=OPEN`),
    enabled: Boolean(clienteId),
  });

  const aplicaciones = useQuery({
    queryKey: ["cxc", "aplicaciones", documentoId],
    queryFn: () =>
      apiFetch<{ items: CreditApplicationRow[] }>(
        `/sales/cxc/documentos/${documentoId}/aplicaciones`,
      ),
    enabled: Boolean(documentoId),
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
    await qc.invalidateQueries({ queryKey: ["cxc"] });
  }

  const credito = (creditos.data?.items ?? []).find((c) => c.id === creditoId);
  const documento = (documentos.data?.items ?? []).find((d) => d.id === documentoId);
  // La moneda tiene que coincidir: sin política de diferencia cambiaria, aplicar
  // entre monedas sería inventar un tipo de cambio.
  const monedasCoinciden = !credito || !documento || credito.currency === documento.currency;

  async function aplicar(): Promise<void> {
    if (!creditoId || !documentoId || Number(importe) <= 0) {
      notify({ type: "error", title: "Indique el crédito, el documento y el importe" });
      return;
    }
    try {
      const r = await apiFetch<CreditApplicationResult>(
        `/sales/cxc/creditos/${creditoId}/aplicar`,
        { method: "POST", body: { target_open_item_id: documentoId, amount: importe } },
      );
      notify({
        type: "success",
        title: "Crédito aplicado",
        description: `Al documento le quedan ${r.target_outstanding} ${r.currency}; al crédito, ${r.credit_remaining}.`,
      });
      setImporte("");
      await refrescar();
    } catch (e) {
      fallo("No se pudo aplicar el crédito")(e);
    }
  }

  async function revertir(app: CreditApplicationRow): Promise<void> {
    if (!motivo.trim()) {
      notify({ type: "error", title: "Revertir una aplicación exige motivo" });
      return;
    }
    try {
      await apiFetch(`/sales/cxc/aplicaciones/${app.id}/revertir`, {
        method: "POST",
        body: { reason: motivo },
      });
      notify({
        type: "success",
        title: "Aplicación revertida",
        description: "La original se conserva: lo que se creó es su evento inverso.",
      });
      setMotivo("");
      await refrescar();
    } catch (e) {
      fallo("No se pudo revertir la aplicación")(e);
    }
  }

  const e = estado.data;

  return (
    <PageContent>
      <PageHeader
        title="Estado de cuenta"
        description={
          "Saldo = documentos + débitos − cobros − retenciones − créditos. " +
          "Todas las cifras las calcula el backend."
        }
        crumbs={[{ label: "Ventas" }, { label: "Estado de cuenta" }]}
      />

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <FormField label="Cliente" required>
          <select
            value={clienteId}
            onChange={(ev) => {
              setClienteId(ev.target.value);
              setCreditoId("");
              setDocumentoId("");
            }}
            className={SELECT}
            aria-label="Cliente"
          >
            <option value="">Seleccionar…</option>
            {(clientes.data?.items ?? []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.code} · {c.name}
              </option>
            ))}
          </select>
        </FormField>
      </section>

      {e ? (
        <>
          <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
            <h2 className="mb-2 text-base font-semibold text-text-900">Saldo</h2>
            <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm sm:grid-cols-3">
              <dt className="text-text-700">Documentos</dt>
              <dd className="font-mono">{e.documents}</dd>
              <dt className="text-text-700">Aplicado</dt>
              <dd className="font-mono">{e.applied}</dd>
              <dt className="text-text-700">Pendiente de documentos</dt>
              <dd className="font-mono">{e.outstanding}</dd>
              <dt className="text-text-700">Créditos emitidos</dt>
              <dd className="font-mono">{e.credits}</dd>
              <dt className="text-text-700">Crédito imputable</dt>
              <dd className="font-mono">{e.credit_available}</dd>
              <dt className="text-text-700">Reservado para devolver</dt>
              <dd className="font-mono">{e.credit_refund_reserved}</dd>
              <dt className="text-text-700">Ya devuelto en efectivo</dt>
              <dd className="font-mono">{e.credit_refunded}</dd>
              <dt className="font-semibold text-text-900">Saldo</dt>
              <dd className="font-mono font-semibold">{e.balance}</dd>
            </dl>
            {Number(e.balance) < 0 ? (
              <p className="mt-3 text-sm text-text-700" role="status">
                El cliente tiene saldo a favor. Puede imputarse a otros documentos suyos; para
                devolverlo en dinero, el reembolso se solicita y se aprueba en tesorería.
              </p>
            ) : null}
          </section>

          <Autorizado operacion={["POST", "/sales/cxc/creditos/_/aplicar"]}>
            <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
              <h2 className="mb-2 text-base font-semibold text-text-900">Aplicar un crédito</h2>
              {(creditos.data?.items ?? []).length === 0 ? (
                <p className="text-sm text-text-700">Este cliente no tiene créditos sin aplicar.</p>
              ) : (
                <>
                  <div className="mb-3 flex flex-wrap items-end gap-3">
                    <FormField label="Crédito" required>
                      <select
                        value={creditoId}
                        onChange={(ev) => setCreditoId(ev.target.value)}
                        className={SELECT}
                        aria-label="Crédito"
                      >
                        <option value="">Seleccionar…</option>
                        {(creditos.data?.items ?? []).map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.number} · quedan {c.available} {c.currency}
                            {Number(c.refund_reserved) > 0
                              ? ` · ${c.refund_reserved} reservado para devolver`
                              : ""}
                          </option>
                        ))}
                      </select>
                    </FormField>
                    <FormField label="Documento del mismo cliente" required>
                      <select
                        value={documentoId}
                        onChange={(ev) => setDocumentoId(ev.target.value)}
                        className={SELECT}
                        aria-label="Documento del mismo cliente"
                      >
                        <option value="">Seleccionar…</option>
                        {(documentos.data?.items ?? []).map((d) => (
                          <option
                            key={d.id}
                            value={d.id}
                            disabled={Boolean(credito) && d.currency !== credito?.currency}
                          >
                            {corto(d.id)} · pendiente {d.balance} {d.currency}
                            {credito && d.currency !== credito.currency ? " · otra moneda" : ""}
                          </option>
                        ))}
                      </select>
                    </FormField>
                    <FormField label="Importe" required>
                      <TextInput
                        value={importe}
                        onChange={(ev) => setImporte(ev.target.value)}
                        placeholder="0.00"
                      />
                    </FormField>
                    <AsyncButton onClick={aplicar} disabled={!monedasCoinciden}>
                      Aplicar crédito
                    </AsyncButton>
                  </div>
                  {!monedasCoinciden ? (
                    <p className="text-sm text-text-700" role="status">
                      El crédito y el documento están en monedas distintas. No se aplica: falta la
                      política de diferencia cambiaria.
                    </p>
                  ) : (
                    <p className="text-sm text-text-500">
                      Aplicar un crédito no es cobrar: no entra dinero ni se mueve tesorería.
                    </p>
                  )}
                </>
              )}
            </section>
          </Autorizado>

          <section className="mb-4">
            <h2 className="mb-2 text-base font-semibold text-text-900">Cronología</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <caption className="sr-only">Estado de cuenta del cliente</caption>
                <thead>
                  <tr className="border-b border-border-default text-left text-text-700">
                    <th scope="col" className="py-1">Fecha</th>
                    <th scope="col">Concepto</th>
                    <th scope="col">Referencia</th>
                    <th scope="col">Debe</th>
                    <th scope="col">Haber</th>
                    <th scope="col">Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {e.entries.map((x) => (
                    <tr key={`${x.type}-${x.id}`} className="border-b border-border-subtle">
                      <td className="py-1">{x.date ?? "—"}</td>
                      <td>{TIPO[x.type] ?? x.type}</td>
                      <td className="font-mono text-xs">{x.reference ? corto(x.reference) : "—"}</td>
                      <td className="font-mono">{x.debit}</td>
                      <td className="font-mono">{x.credit}</td>
                      <td>{x.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {documentoId ? (
            <section className="rounded-lg border border-border-default bg-surface-0 p-4">
              <h2 className="mb-2 text-base font-semibold text-text-900">
                Aplicaciones del documento {corto(documentoId)}
              </h2>
              {(aplicaciones.data?.items ?? []).length === 0 ? (
                <p className="text-sm text-text-700">Este documento no tiene aplicaciones.</p>
              ) : (
                <>
                  <table className="mb-3 w-full text-sm">
                    <caption className="sr-only">Aplicaciones y reversos</caption>
                    <thead>
                      <tr className="border-b border-border-default text-left text-text-700">
                        <th scope="col" className="py-1">Fecha</th>
                        <th scope="col">Origen</th>
                        <th scope="col">Importe</th>
                        <th scope="col">Estado</th>
                        <th scope="col">Acción</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(aplicaciones.data?.items ?? []).map((a) => (
                        <tr key={a.id} className="border-b border-border-subtle">
                          <td className="py-1">{a.date ?? "—"}</td>
                          <td>{a.source_type}</td>
                          <td className="font-mono">
                            {a.amount} {a.currency}
                          </td>
                          <td>{a.status}</td>
                          <td>
                            {a.status === "APPLIED" &&
                            puede("POST", `/sales/cxc/aplicaciones/${a.id}/revertir`) ? (
                              <AsyncButton size="sm" variant="secondary" onClick={() => revertir(a)}>
                                Revertir aplicación
                              </AsyncButton>
                            ) : (
                              "—"
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <FormField label="Motivo del reverso">
                    <TextInput
                      value={motivo}
                      onChange={(ev) => setMotivo(ev.target.value)}
                      placeholder="Por qué se deshace"
                    />
                  </FormField>
                  <p className="mt-2 text-sm text-text-500">
                    Revertir no borra nada: la aplicación original se conserva y se crea su evento
                    inverso.
                  </p>
                </>
              )}
            </section>
          ) : null}
        </>
      ) : null}
    </PageContent>
  );
}
