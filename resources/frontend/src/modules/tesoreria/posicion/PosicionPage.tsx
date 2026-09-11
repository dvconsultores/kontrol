/**
 * Posición de caja — Spec 038.
 *
 * Por cuenta y por moneda, y **sin un total general**. Sumar bolívares con
 * dólares exige una tasa, y aplicar una tasa es convertir: un acto explícito
 * que deja su instantánea y su política. Un número único aquí sería una
 * conversión que nadie autorizó, hecha con una tasa que nadie eligió.
 *
 * Los saldos se calculan desde los movimientos, no se leen de un campo
 * guardado: «los saldos no se editan».
 */
import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/api/client";
import type { CashPosition } from "@/api/types";
import { PageHeader } from "@/components/PageHeader";
import { PageContent } from "@/layout/PageContent";

export function PosicionPage(): React.JSX.Element {
  const posicion = useQuery({
    queryKey: ["tesoreria", "posicion"],
    queryFn: () => apiFetch<CashPosition>("/treasury/cash-position"),
  });

  const datos = posicion.data;

  return (
    <PageContent>
      <PageHeader
        title="Posición de caja"
        description="Por cuenta y por moneda. Sin total general: sumar monedas distintas exige convertirlas."
        crumbs={[{ label: "Tesorería" }, { label: "Posición de caja" }]}
      />

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Por moneda</h2>
        {(datos?.by_currency ?? []).length === 0 ? (
          <p className="text-sm text-text-700">No hay cuentas con saldo.</p>
        ) : (
          <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm sm:grid-cols-3">
            {(datos?.by_currency ?? []).map((m) => (
              <div key={m.currency} className="contents">
                <dt className="text-text-700">{m.currency}</dt>
                <dd className="font-mono">{m.balance}</dd>
              </div>
            ))}
          </dl>
        )}
        <p className="mt-3 text-sm text-text-500">
          Cada moneda va por su lado. Convertir es un acto aparte, con su tasa y su política.
        </p>
      </section>

      <section>
        <h2 className="mb-2 text-base font-semibold text-text-900">Por cuenta</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <caption className="sr-only">Saldo de cada cuenta financiera</caption>
            <thead>
              <tr className="border-b border-border-default text-left text-text-700">
                <th scope="col" className="py-1">Código</th>
                <th scope="col">Cuenta</th>
                <th scope="col">Moneda</th>
                <th scope="col">Saldo</th>
                <th scope="col">Estado</th>
              </tr>
            </thead>
            <tbody>
              {(datos?.accounts ?? []).map((c) => (
                <tr key={c.account_id} className="border-b border-border-subtle">
                  <td className="py-1">{c.code}</td>
                  <td>{c.name}</td>
                  <td>{c.currency}</td>
                  <td className="font-mono">{c.balance}</td>
                  <td>{c.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </PageContent>
  );
}
