/**
 * Reembolso de un crédito a favor — Spec 038.
 *
 * `OWNER-DECISION-038-01`: se soporta, **no es automático**, reserva el
 * crédito, exige aprobación y no permite gastar dos veces el mismo dinero.
 * Por eso son tres actos separados —solicitar, decidir, ejecutar— y no un
 * botón de «devolver».
 *
 * La reserva es lo que impide el doble gasto: desde que se solicita, ese
 * importe deja de ofrecerse para imputar a facturas. Denegar la libera;
 * ejecutar la convierte en dinero que salió del banco. El saldo del cliente
 * **no se mueve al reservar**: lo que se debe se sigue debiendo hasta que el
 * pago ocurre.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { ApiError, apiFetch } from "@/api/client";
import type {
  CustomerCredit,
  FinancialAccountSummary,
  FxPolicy,
  PagedResult,
  Party,
  TreasuryRefund,
} from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Autorizado } from "@/components/Autorizado";
import { FormField } from "@/components/FormField";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";
import { fechaDeNegocioDeInstante } from "@/lib/fecha-de-negocio";

const SELECT =
  "h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900";

const ESTADO: Record<string, string> = {
  REQUESTED: "Solicitado",
  APPROVED: "Aprobado",
  REJECTED: "Denegado",
  SETTLED: "Ejecutado",
  CANCELLED: "Anulado",
};

function corto(id: string): string {
  return `${id.slice(0, 8)}…`;
}

export function ReembolsosPage(): React.JSX.Element {
  const qc = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();
  const [clienteId, setClienteId] = useState("");
  const [creditoId, setCreditoId] = useState("");
  const [importe, setImporte] = useState("");
  const [motivo, setMotivo] = useState("");
  const [cuentaId, setCuentaId] = useState("");
  const [motivoDecision, setMotivoDecision] = useState("");

  // El endpoint pagina con `page`/`page_size` y su máximo es 100: se recorre
  // hasta agotar `total`. Un `limit` inventado se ignora en silencio y el
  // desplegable se queda corto sin que nada lo diga.
  const clientes = useQuery({
    queryKey: ["reembolsos", "clientes"],
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

  const cuentas = useQuery({
    queryKey: ["reembolsos", "cuentas"],
    queryFn: () => apiFetch<{ items: FinancialAccountSummary[] }>("/treasury/accounts"),
  });

  const politicas = useQuery({
    queryKey: ["reembolsos", "politicas"],
    queryFn: () => apiFetch<{ items: FxPolicy[] }>("/treasury/fx-policies"),
  });

  // Lo que el backend considera disponible ya descuenta lo reservado y lo
  // devuelto: la pantalla no vuelve a calcularlo.
  const creditos = useQuery({
    queryKey: ["reembolsos", "creditos", clienteId],
    queryFn: () =>
      apiFetch<{ items: CustomerCredit[] }>(`/sales/cxc/clientes/${clienteId}/creditos`),
    enabled: Boolean(clienteId),
  });

  const reembolsos = useQuery({
    queryKey: ["reembolsos", "lista"],
    queryFn: () => apiFetch<{ items: TreasuryRefund[] }>("/treasury/refunds"),
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
    await qc.invalidateQueries({ queryKey: ["reembolsos"] });
  }

  const activa = (politicas.data?.items ?? []).find((p) => p.status === "ACTIVE");
  const credito = (creditos.data?.items ?? []).find((c) => c.id === creditoId);
  const cuenta = (cuentas.data?.items ?? []).find((c) => c.id === cuentaId);
  // Devolver en otra moneda exigiría convertir, y convertir es otro acto con su
  // propia tasa. Aquí se avisa antes; el backend lo vuelve a comprobar.
  const monedaDistinta = Boolean(credito && cuenta && credito.currency !== cuenta.currency);

  async function solicitar(): Promise<void> {
    if (!creditoId || Number(importe) <= 0 || motivo.trim().length < 3) {
      notify({ type: "error", title: "Indique el crédito, el importe y el motivo" });
      return;
    }
    try {
      const r = await apiFetch<TreasuryRefund>("/treasury/refunds", {
        method: "POST",
        body: {
          credit_note_id: creditoId,
          amount: importe,
          reason: motivo,
          account_id: cuentaId || null,
        },
      });
      notify({
        type: "success",
        title: "Reembolso solicitado",
        description: `Quedan reservados ${r.amount} ${r.currency}: ese crédito ya no se imputa a facturas.`,
      });
      setImporte("");
      setMotivo("");
      await refrescar();
    } catch (e) {
      fallo("No se pudo solicitar el reembolso")(e);
    }
  }

  async function decidir(r: TreasuryRefund, aprobado: boolean): Promise<void> {
    if (!aprobado && !motivoDecision.trim()) {
      notify({ type: "error", title: "Denegar exige motivo" });
      return;
    }
    try {
      await apiFetch(`/treasury/refunds/${r.id}/decide`, {
        method: "POST",
        body: { approved: aprobado, reason: motivoDecision || null },
      });
      notify({
        type: "success",
        title: aprobado ? "Reembolso aprobado" : "Reembolso denegado",
        description: aprobado
          ? "Aprobar no paga: el dinero sale al ejecutarlo."
          : "La reserva queda liberada: el crédito vuelve a poder imputarse.",
      });
      setMotivoDecision("");
      await refrescar();
    } catch (e) {
      fallo("No se pudo registrar la decisión")(e);
    }
  }

  async function ejecutar(r: TreasuryRefund): Promise<void> {
    try {
      const hecho = await apiFetch<TreasuryRefund>(`/treasury/refunds/${r.id}/settle`, {
        method: "POST",
        body: { account_id: r.account_id ?? cuentaId ?? null },
      });
      notify({
        type: "success",
        title: "Reembolso ejecutado",
        description: `Salió el dinero de la cuenta; movimiento ${hecho.movement_id ? corto(hecho.movement_id) : "—"}.`,
      });
      await refrescar();
    } catch (e) {
      fallo("No se pudo ejecutar el reembolso")(e);
    }
  }

  return (
    <PageContent>
      <PageHeader
        title="Reembolsos"
        description={
          "Devolver dinero de un crédito a favor: se solicita, se aprueba y se ejecuta. " +
          "La reserva impide gastarlo dos veces."
        }
        crumbs={[{ label: "Tesorería" }, { label: "Reembolsos" }]}
      />

      {activa && !activa.allow_refund ? (
        <p className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4 text-sm text-text-700" role="status">
          La política vigente no permite reembolso en efectivo. Cambiarla es una decisión de
          política, no de esta pantalla.
        </p>
      ) : null}
      {!activa ? (
        <p className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4 text-sm text-text-700" role="status">
          No hay política cambiaria activa. Sin política no se reembolsa.
        </p>
      ) : null}

      <Autorizado operacion={["POST", "/treasury/refunds"]}>
      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Solicitar</h2>
        <div className="mb-3 flex flex-wrap items-end gap-3">
          <FormField label="Cliente" required>
            <select
              value={clienteId}
              onChange={(e) => {
                setClienteId(e.target.value);
                setCreditoId("");
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
          <FormField label="Crédito" required>
            <select
              value={creditoId}
              onChange={(e) => setCreditoId(e.target.value)}
              className={SELECT}
              aria-label="Crédito"
            >
              <option value="">Seleccionar…</option>
              {(creditos.data?.items ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.number} · disponible {c.available} {c.currency}
                  {Number(c.refund_reserved) > 0 ? ` · reservado ${c.refund_reserved}` : ""}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Importe" required>
            <TextInput value={importe} onChange={(e) => setImporte(e.target.value)} placeholder="0.00" />
          </FormField>
          <FormField label="Cuenta pagadora">
            <select
              value={cuentaId}
              onChange={(e) => setCuentaId(e.target.value)}
              className={SELECT}
              aria-label="Cuenta pagadora"
            >
              <option value="">Decidir al ejecutar…</option>
              {(cuentas.data?.items ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.code} · {c.name} ({c.currency})
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Motivo" required>
            <TextInput
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              placeholder="Por qué se devuelve"
            />
          </FormField>
          <AsyncButton onClick={solicitar} disabled={monedaDistinta}>
            Solicitar reembolso
          </AsyncButton>
        </div>
        {monedaDistinta ? (
          <p className="text-sm text-text-700" role="status">
            El crédito está en {credito?.currency} y la cuenta en {cuenta?.currency}. Convertir es
            otro acto, con su propia tasa.
          </p>
        ) : (
          <p className="text-sm text-text-500">
            Solicitar reserva el importe: deja de estar disponible para imputar a facturas, y el
            saldo del cliente no cambia hasta que el dinero salga.
          </p>
        )}
      </section>
      </Autorizado>

      {puede("POST", "/treasury/refunds/_/decide") ? (
      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <FormField label="Motivo de la decisión">
          <TextInput
            value={motivoDecision}
            onChange={(e) => setMotivoDecision(e.target.value)}
            placeholder="Obligatorio para denegar"
          />
        </FormField>
      </section>
      ) : null}

      <section>
        <h2 className="mb-2 text-base font-semibold text-text-900">Reembolsos</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <caption className="sr-only">Reembolsos solicitados</caption>
            <thead>
              <tr className="border-b border-border-default text-left text-text-700">
                <th scope="col" className="py-1">Solicitado</th>
                <th scope="col">Nota</th>
                <th scope="col">Importe</th>
                <th scope="col">Estado</th>
                <th scope="col">Movimiento</th>
                <th scope="col">Acción</th>
              </tr>
            </thead>
            <tbody>
              {(reembolsos.data?.items ?? []).map((r) => (
                <tr key={r.id} className="border-b border-border-subtle">
                  <td className="py-1">{fechaDeNegocioDeInstante(r.requested_at)}</td>
                  <td className="font-mono text-xs">{corto(r.credit_note_id)}</td>
                  <td className="font-mono">
                    {r.amount} {r.currency}
                  </td>
                  <td>
                    {ESTADO[r.status] ?? r.status}
                    {r.status_reason ? ` · ${r.status_reason}` : ""}
                  </td>
                  <td className="font-mono text-xs">
                    {r.movement_id ? corto(r.movement_id) : "—"}
                  </td>
                  <td className="flex flex-wrap gap-2 py-1">
                    {r.status === "REQUESTED" && puede("POST", `/treasury/refunds/${r.id}/decide`) ? (
                      <>
                        <AsyncButton size="sm" onClick={() => decidir(r, true)}>
                          Aprobar
                        </AsyncButton>
                        <AsyncButton size="sm" variant="secondary" onClick={() => decidir(r, false)}>
                          Denegar
                        </AsyncButton>
                      </>
                    ) : null}
                    {r.status === "APPROVED" && puede("POST", `/treasury/refunds/${r.id}/settle`) ? (
                      <AsyncButton size="sm" onClick={() => ejecutar(r)}>
                        Ejecutar pago
                      </AsyncButton>
                    ) : null}
                    {r.status !== "REQUESTED" && r.status !== "APPROVED" ? "—" : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </PageContent>
  );
}
