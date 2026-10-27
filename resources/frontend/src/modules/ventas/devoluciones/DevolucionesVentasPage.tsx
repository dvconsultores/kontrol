/**
 * Devoluciones de venta — Spec 036.
 *
 * La norma escribe el proceso entero y en este orden: «Solicitud → Verificación
 * física → Aprobación → **Entrada de inventario**». Cuatro actos, y la pantalla
 * los mantiene separados porque no son lo mismo: una solicitud no aumenta
 * existencia y recibir la mercancía no la hace vendible.
 *
 * Lo que no se teclea aquí: cuánto se puede devolver —lo dice el backend, que
 * es quien ve todas las devoluciones— ni el estado al que vuelve la mercancía,
 * que sale de los dos destinos que `D0-10` concede a esta Spec.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { ApiError, apiFetch } from "@/api/client";
import type { PutAwayLocation, ReturnEligibility, SalesReturnDetail } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Autorizado } from "@/components/Autorizado";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";

const cols = createColumnHelper<SalesReturnDetail>();

const SELECT =
  "h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900";

/** Los dos que `D0-10` declara para `DEVUELTO`. No hay más y no se inventan. */
const DESTINOS = [
  { value: "DISPONIBLE", label: "Vuelve a existencia" },
  { value: "RECHAZADO", label: "No apta" },
];

const ACTO: Record<string, string> = {
  REQUESTED: "Solicitada",
  RECEIVED: "Recibida",
  INSPECTED: "Verificada",
  APPROVED: "Aprobada",
  CLOSED: "Reingresada",
  REJECTED: "Denegada",
  CANCELLED: "Anulada",
  DRAFT: "Anterior a la 036",
};

function corto(id: string): string {
  return `${id.slice(0, 8)}…`;
}

export function DevolucionesVentasPage(): React.JSX.Element {
  const qc = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();
  const [facturaId, setFacturaId] = useState("");
  const [codigo, setCodigo] = useState("");
  const [motivo, setMotivo] = useState("");
  const [cantidades, setCantidades] = useState<Record<string, string>>({});
  const [seleccion, setSeleccion] = useState<string | null>(null);
  const [ubicacion, setUbicacion] = useState("");
  const [dictamen, setDictamen] = useState<Record<string, string>>({});
  const [aceptadas, setAceptadas] = useState<Record<string, string>>({});
  const [motivoDenegar, setMotivoDenegar] = useState("");

  const devoluciones = useQuery({
    queryKey: ["devoluciones", "lista"],
    queryFn: () => apiFetch<{ items: SalesReturnDetail[] }>("/sales/devoluciones"),
  });

  const elegible = useQuery({
    queryKey: ["devoluciones", "elegible", facturaId],
    queryFn: () => apiFetch<ReturnEligibility>(`/sales/devoluciones/elegibles/${facturaId}`),
    enabled: facturaId.length > 20,
    retry: false,
  });

  const detalle = useQuery({
    queryKey: ["devoluciones", "detalle", seleccion],
    queryFn: () => apiFetch<SalesReturnDetail>(`/sales/devoluciones/${seleccion}`),
    enabled: Boolean(seleccion),
  });

  const ubicaciones = useQuery({
    queryKey: ["devoluciones", "ubicaciones", detalle.data?.warehouse_id],
    queryFn: () =>
      apiFetch<{ items: PutAwayLocation[] }>(
        `/organization/locations?warehouse_id=${detalle.data?.warehouse_id}&status=ACTIVE&limit=200`,
      ),
    enabled: Boolean(detalle.data?.warehouse_id),
    retry: false,
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
    await qc.invalidateQueries({ queryKey: ["devoluciones"] });
  }

  async function solicitar(): Promise<void> {
    const lineas = (elegible.data?.lines ?? [])
      .map((l) => ({ l, pedida: Number(cantidades[l.invoice_line_id] ?? 0) }))
      .filter(({ pedida }) => pedida > 0)
      .map(({ l, pedida }) => ({
        invoice_line_id: l.invoice_line_id,
        base_quantity: pedida,
        quantity: l.conversion_factor_snapshot
          ? pedida / Number(l.conversion_factor_snapshot)
          : pedida,
      }));
    if (!codigo || !motivo || lineas.length === 0) {
      notify({
        type: "error",
        title: "Faltan datos de la solicitud",
        description: "Indique el código, el motivo y al menos una cantidad.",
      });
      return;
    }
    try {
      const dev = await apiFetch<SalesReturnDetail>("/sales/devoluciones", {
        method: "POST",
        body: { code: codigo, invoice_id: facturaId, reason: motivo, lines: lineas },
      });
      notify({
        type: "success",
        title: "Devolución solicitada",
        description: "La mercancía sigue con el cliente: esto no mueve inventario.",
      });
      setSeleccion(dev.id);
      setCodigo("");
      setMotivo("");
      setCantidades({});
      await refrescar();
    } catch (e) {
      fallo("No se pudo solicitar la devolución")(e);
    }
  }

  async function recibir(dev: SalesReturnDetail): Promise<void> {
    if (!ubicacion) {
      notify({ type: "error", title: "Indique a qué ubicación entra la mercancía" });
      return;
    }
    try {
      await apiFetch(`/sales/devoluciones/${dev.id}/recibir`, {
        method: "POST",
        body: { location_id: ubicacion },
      });
      notify({
        type: "success",
        title: "Mercancía recibida",
        description: "Vuelve a custodia de la empresa; todavía no es vendible.",
      });
      await refrescar();
    } catch (e) {
      fallo("No se pudo registrar la recepción")(e);
    }
  }

  async function verificar(dev: SalesReturnDetail): Promise<void> {
    const lineas = dev.lines.map((l) => ({
      return_line_id: l.id,
      disposition: dictamen[l.id] ?? "DISPONIBLE",
      accepted_base_quantity: Number(aceptadas[l.id] ?? l.base_quantity),
    }));
    try {
      await apiFetch(`/sales/devoluciones/${dev.id}/verificar`, {
        method: "POST",
        body: { lines: lineas },
      });
      notify({ type: "success", title: "Verificación registrada" });
      await refrescar();
    } catch (e) {
      fallo("No se pudo registrar la verificación")(e);
    }
  }

  async function decidir(dev: SalesReturnDetail, approved: boolean): Promise<void> {
    try {
      await apiFetch(`/sales/devoluciones/${dev.id}/decidir`, {
        method: "POST",
        body: { approved, reason: approved ? null : motivoDenegar },
      });
      notify({ type: "success", title: approved ? "Devolución aprobada" : "Devolución denegada" });
      setMotivoDenegar("");
      await refrescar();
    } catch (e) {
      fallo("No se pudo decidir la devolución")(e);
    }
  }

  async function reingresar(dev: SalesReturnDetail): Promise<void> {
    try {
      await apiFetch(`/sales/devoluciones/${dev.id}/reingresar`, { method: "POST", body: {} });
      notify({
        type: "success",
        title: "Entrada de inventario registrada",
        description: "Cada línea fue al destino que la verificación le dictaminó.",
      });
      await refrescar();
    } catch (e) {
      fallo("No se pudo reingresar la mercancía")(e);
    }
  }

  const columnas = [
    cols.accessor("code", { header: "Devolución" }),
    cols.accessor("status", {
      header: "Acto",
      cell: (c) => ACTO[c.getValue()] ?? c.getValue(),
    }),
    cols.accessor("reason", { header: "Motivo" }),
    cols.display({
      id: "accion",
      header: "Acción",
      cell: (c) => (
        <button
          type="button"
          onClick={() => setSeleccion(c.row.original.id)}
          className="text-sm font-medium text-primary-700 underline"
        >
          Abrir
        </button>
      ),
    }),
  ];

  const d = detalle.data;

  return (
    <PageContent>
      <PageHeader
        title="Devoluciones"
        description={
          "Solicitud, verificación física, aprobación y entrada de inventario. " +
          "Son cuatro actos y solo el último crea existencia."
        }
        crumbs={[{ label: "Ventas" }, { label: "Devoluciones" }]}
      />

      <Autorizado operacion={["POST", "/sales/devoluciones"]}>
        <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-2 text-base font-semibold text-text-900">Solicitar una devolución</h2>
          <div className="mb-3 flex flex-wrap items-end gap-3">
            <FormField label="Factura" required>
              <TextInput
                value={facturaId}
                onChange={(e) => setFacturaId(e.target.value)}
                placeholder="Identificador de la factura"
              />
            </FormField>
            <FormField label="Código" required>
              <TextInput value={codigo} onChange={(e) => setCodigo(e.target.value)} placeholder="DEV-0001" />
            </FormField>
            <FormField label="Motivo" required>
              <TextInput
                value={motivo}
                onChange={(e) => setMotivo(e.target.value)}
                placeholder="Por qué la devuelve el cliente"
              />
            </FormField>
          </div>

          {elegible.isError ? (
            <p className="text-sm text-text-700" role="status">
              No se encontró esa factura en esta empresa.
            </p>
          ) : null}

          {elegible.data && !elegible.data.dispatched ? (
            <p className="text-sm text-text-700" role="status">
              Ese pedido no salió del almacén. No se devuelve lo que nunca salió.
            </p>
          ) : null}

          {elegible.data?.dispatched ? (
            <>
              <table className="mb-3 w-full text-sm">
                <caption className="sr-only">Líneas devolvibles</caption>
                <thead>
                  <tr className="border-b border-border-default text-left text-text-700">
                    <th scope="col" className="py-1">Producto</th>
                    <th scope="col">Despachado</th>
                    <th scope="col">Ya devuelto</th>
                    <th scope="col">Se puede devolver</th>
                    <th scope="col">Devolver ahora</th>
                  </tr>
                </thead>
                <tbody>
                  {elegible.data.lines.map((l) => (
                    <tr key={l.invoice_line_id} className="border-b border-border-subtle">
                      <td className="py-1 font-mono text-xs">{corto(l.product_id)}</td>
                      <td>{l.dispatched_base_quantity}</td>
                      <td>{l.returned_base_quantity}</td>
                      <td>{l.returnable_base_quantity}</td>
                      <td>
                        <TextInput
                          aria-label={`Devolver de ${corto(l.product_id)}`}
                          value={cantidades[l.invoice_line_id] ?? ""}
                          onChange={(e) =>
                            setCantidades((c) => ({ ...c, [l.invoice_line_id]: e.target.value }))
                          }
                          placeholder="0"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="mb-3 text-sm text-text-500">
                Las cantidades son en unidad base: devolver una caja de doce devuelve doce unidades.
              </p>
              <AsyncButton onClick={solicitar}>Solicitar devolución</AsyncButton>
            </>
          ) : null}
        </section>
      </Autorizado>

      <section className="mb-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Devoluciones</h2>
        <DataTable
          data={devoluciones.data?.items ?? []}
          columns={columnas}
          loading={devoluciones.isLoading}
          error={devoluciones.isError ? "No fue posible cargar las devoluciones." : null}
          getRowId={(row) => row.id}
          emptyTitle="Sin devoluciones"
          emptyDescription="Ninguna devolución registrada."
        />
      </section>

      {d ? (
        <section className="rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-1 text-base font-semibold text-text-900">
            {d.code} · {ACTO[d.status] ?? d.status}
          </h2>
          <p className="mb-3 text-sm text-text-700">{d.reason}</p>

          <table className="mb-3 w-full text-sm">
            <caption className="sr-only">Líneas de la devolución</caption>
            <thead>
              <tr className="border-b border-border-default text-left text-text-700">
                <th scope="col" className="py-1">Producto</th>
                <th scope="col">En unidad base</th>
                <th scope="col">Aceptado</th>
                <th scope="col">Destino</th>
              </tr>
            </thead>
            <tbody>
              {d.lines.map((l) => (
                <tr key={l.id} className="border-b border-border-subtle">
                  <td className="py-1 font-mono text-xs">{corto(l.product_id)}</td>
                  <td>{l.base_quantity}</td>
                  <td>
                    {d.status === "RECEIVED" ? (
                      <TextInput
                        aria-label={`Aceptado de ${corto(l.product_id)}`}
                        value={aceptadas[l.id] ?? l.base_quantity}
                        onChange={(e) => setAceptadas((c) => ({ ...c, [l.id]: e.target.value }))}
                      />
                    ) : (
                      (l.accepted_base_quantity ?? "—")
                    )}
                  </td>
                  <td>
                    {d.status === "RECEIVED" ? (
                      <select
                        aria-label={`Destino de ${corto(l.product_id)}`}
                        value={dictamen[l.id] ?? "DISPONIBLE"}
                        onChange={(e) => setDictamen((c) => ({ ...c, [l.id]: e.target.value }))}
                        className={SELECT}
                      >
                        {DESTINOS.map((x) => (
                          <option key={x.value} value={x.value}>
                            {x.label}
                          </option>
                        ))}
                      </select>
                    ) : (
                      (l.disposition ?? "sin verificar")
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {d.status === "REQUESTED" ? (
            <div className="flex flex-wrap items-end gap-3">
              <FormField label="Ubicación de entrada" required>
                <select
                  value={ubicacion}
                  onChange={(e) => setUbicacion(e.target.value)}
                  className={SELECT}
                  aria-label="Ubicación de entrada"
                >
                  <option value="">Seleccionar…</option>
                  {(ubicaciones.data?.items ?? []).map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.code} · {u.name}
                    </option>
                  ))}
                </select>
              </FormField>
              {puede("POST", `/sales/devoluciones/${d.id}/recibir`) ? (
                <AsyncButton onClick={() => recibir(d)}>Registrar recepción</AsyncButton>
              ) : null}
            </div>
          ) : null}

          {d.status === "RECEIVED" ? (
            <>
              <p className="mb-3 text-sm text-text-700">
                La mercancía está en custodia de la empresa y todavía no es vendible. La
                verificación decide qué vuelve a existencia y qué no.
              </p>
              {puede("POST", `/sales/devoluciones/${d.id}/verificar`) ? (
                <AsyncButton onClick={() => verificar(d)}>Registrar verificación</AsyncButton>
              ) : null}
            </>
          ) : null}

          {d.status === "INSPECTED" ? (
            <div className="flex flex-wrap items-end gap-3">
              {puede("POST", `/sales/devoluciones/${d.id}/decidir`) ? (
                <>
                  <AsyncButton onClick={() => decidir(d, true)}>Aprobar</AsyncButton>
                  <FormField label="Motivo para denegar">
                    <TextInput
                      value={motivoDenegar}
                      onChange={(e) => setMotivoDenegar(e.target.value)}
                      placeholder="Por qué no procede"
                    />
                  </FormField>
                  <AsyncButton variant="secondary" onClick={() => decidir(d, false)}>
                    Denegar
                  </AsyncButton>
                </>
              ) : null}
            </div>
          ) : null}

          {d.status === "APPROVED" ? (
            <>
              <p className="mb-3 text-sm text-text-700">
                Es el cuarto acto y el único que crea existencia. Lo aceptado va a su destino; lo
                que no se aceptó se queda en custodia.
              </p>
              {puede("POST", `/sales/devoluciones/${d.id}/reingresar`) ? (
                <AsyncButton onClick={() => reingresar(d)}>Registrar entrada de inventario</AsyncButton>
              ) : null}
            </>
          ) : null}

          {d.status === "CLOSED" ? (
            <p className="text-sm text-text-700" role="status">
              Mercancía reingresada el {d.reentered_at?.slice(0, 16).replace("T", " ")}. La nota de
              crédito, si corresponde, se emite en la pantalla de notas: la devolución física no la
              sustituye.
            </p>
          ) : null}

          {d.status === "REJECTED" ? (
            <p className="text-sm text-text-700" role="status">
              Devolución denegada: {d.status_reason}. La mercancía sigue en custodia de la empresa.
            </p>
          ) : null}
        </section>
      ) : null}
    </PageContent>
  );
}
