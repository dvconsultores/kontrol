/** Detalle de cotización — Spec 029.
 *
 * Es la pantalla donde la evidencia deja de ser una columna en la base y pasa a
 * ser algo que alguien puede leer: de qué lista salió cada precio, de qué
 * versión, y si lo escribió una persona, por qué.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router";

import { apiFetch } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Autorizado } from "@/components/Autorizado";
import { DataTable } from "@/components/DataTable";
import { PageHeader } from "@/components/PageHeader";
import { PageContent } from "@/layout/PageContent";

interface LineaCotizacion {
  id: string;
  product_id: string;
  quantity: string;
  unit_price: string;
  discount: string;
  pricing_source: string | null;
  price_source_version_id: string | null;
  resolved_unit_price: string | null;
  manual_reason: string | null;
  discount_policy_version: number | null;
}

interface DetalleCotizacion {
  id: string;
  code: string;
  status: string;
  customer_id: string;
  currency: string;
  validity_until: string | null;
  price_list_legacy: string | null;
  order_id: string | null;
  lines: LineaCotizacion[];
}

const ORIGEN: Record<string, string> = {
  RESOLVED: "De la lista de precios",
  MANUAL_JUSTIFIED: "Escrito a mano, con motivo",
  LEGACY_FREETEXT: "Heredado, sin origen conocido",
};

export function CotizacionDetallePage(): React.JSX.Element {
  const { quoteId = "" } = useParams();
  const { activeCompany } = useCompany();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();
  const companyId = activeCompany?.id ?? null;

  const detalle = useQuery({
    queryKey: ["ventas", "cotizaciones", quoteId],
    queryFn: () => apiFetch<DetalleCotizacion>(`/sales/quotes/${encodeURIComponent(quoteId)}`),
    enabled: Boolean(companyId && quoteId),
    retry: false,
  });

  const invalidar = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["ventas"] });
  };

  const transicionar = useMutation({
    mutationFn: (target: string) =>
      apiFetch(`/sales/quotes/${encodeURIComponent(quoteId)}/transition`, {
        method: "POST",
        body: { target },
        // La empresa queda fijada al abrir la pantalla: cambiar el selector con
        // la acción a medio hacer no puede redirigirla a otra empresa.
        companyId,
      }),
    onSuccess: () => {
      notify({ type: "success", title: "Cotización actualizada", description: "Estado cambiado." });
      invalidar();
    },
    onError: (err: unknown) => {
      notify({
        type: "error",
        title: "No fue posible cambiar el estado",
        description: err instanceof Error ? err.message : "Error inesperado",
      });
    },
  });

  const convertir = useMutation({
    mutationFn: () =>
      apiFetch<{ id: string; created: boolean }>(
        `/sales/quotes/${encodeURIComponent(quoteId)}/convertir`,
        { method: "POST", body: {}, companyId },
      ),
    onSuccess: (res) => {
      notify({
        type: "success",
        title: res.created ? "Pedido creado" : "El pedido ya existía",
        description: res.created
          ? "La evidencia comercial viajó al pedido."
          : "Esta cotización ya se había convertido; se muestra el mismo pedido.",
      });
      invalidar();
    },
    onError: (err: unknown) => {
      notify({
        type: "error",
        title: "No fue posible convertir",
        description: err instanceof Error ? err.message : "Error inesperado",
      });
    },
  });

  if (!companyId) {
    return (
      <PageContent maxWidth="full">
        <PageHeader title="Cotización" crumbs={[{ label: "Ventas" }, { label: "Cotizaciones" }]} />
        <div className="rounded-md border border-warning-100 bg-warning-100/40 p-4 text-sm text-warning-600" role="alert">
          Seleccione una empresa para ver esta cotización.
        </div>
      </PageContent>
    );
  }

  const c = detalle.data;

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title={c ? `Cotización ${c.code}` : "Cotización"}
        description="El precio de cada línea, y de dónde salió."
        crumbs={[{ label: "Ventas" }, { label: "Cotizaciones" }, { label: c?.code ?? "" }]}
      />

      {detalle.isLoading ? <p className="text-sm text-text-500">Cargando…</p> : null}
      {detalle.isError ? (
        <div className="rounded-md border border-danger-100 bg-danger-100/40 p-4 text-sm text-danger-600" role="alert">
          No fue posible cargar la cotización, o no pertenece a la empresa activa.
        </div>
      ) : null}

      {c ? (
        <>
          <section className="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-border-default bg-surface-0 p-4">
            <span className="text-sm text-text-700">
              Estado <strong className="text-text-900">{c.status}</strong>
            </span>
            {c.validity_until ? (
              <span className="text-sm text-text-500">Vigente hasta {c.validity_until}</span>
            ) : (
              <span className="text-sm text-text-500">Sin vencimiento</span>
            )}
            {c.order_id ? (
              <span className="text-sm text-success-600">Convertida en pedido</span>
            ) : null}
            <div className="ml-auto flex gap-2">
              {c.status === "DRAFT" && puede("POST", `/sales/quotes/${encodeURIComponent(quoteId)}/transition`) ? (
                <AsyncButton variant="secondary" onClick={async () => { await transicionar.mutateAsync("SENT"); }}>
                  Enviar al cliente
                </AsyncButton>
              ) : null}
              {c.status === "SENT" && puede("POST", `/sales/quotes/${encodeURIComponent(quoteId)}/transition`) ? (
                <>
                  <AsyncButton variant="primary" onClick={async () => { await transicionar.mutateAsync("ACCEPTED"); }}>
                    Marcar aceptada
                  </AsyncButton>
                  <AsyncButton variant="secondary" onClick={async () => { await transicionar.mutateAsync("REJECTED"); }}>
                    Marcar rechazada
                  </AsyncButton>
                </>
              ) : null}
              {c.status === "ACCEPTED" ? (
                <Autorizado operacion={["POST", `/sales/quotes/${encodeURIComponent(quoteId)}/convertir`]}>
                  <AsyncButton variant="primary" onClick={async () => { await convertir.mutateAsync(); }}>
                    Convertir en pedido
                  </AsyncButton>
                </Autorizado>
              ) : null}
            </div>
          </section>

          {c.price_list_legacy ? (
            <p className="mb-3 text-sm text-text-500">
              Lista de precios heredada, en texto libre: <em>{c.price_list_legacy}</em>. Se conserva
              porque es el único rastro que dejó quien la escribió.
            </p>
          ) : null}

          <DataTable
            columns={[
              { header: "Producto", accessorKey: "product_id" },
              { header: "Cantidad", accessorKey: "quantity" },
              { header: "Precio", accessorKey: "unit_price" },
              { header: "Descuento", accessorKey: "discount" },
              {
                id: "origen",
                header: "Origen del precio",
                cell: ({ row }) => {
                  const l = row.original;
                  if (!l.pricing_source) {
                    return <span className="text-sm text-text-500">Sin origen registrado</span>;
                  }
                  return (
                    <div className="text-sm">
                      <div className="text-text-900">{ORIGEN[l.pricing_source] ?? l.pricing_source}</div>
                      {l.pricing_source === "MANUAL_JUSTIFIED" && l.resolved_unit_price ? (
                        <div className="text-text-500">
                          La lista decía {l.resolved_unit_price} · {l.manual_reason}
                        </div>
                      ) : null}
                    </div>
                  );
                },
              },
            ]}
            data={c.lines}
            emptyTitle="Sin líneas"
            emptyDescription="Añada líneas desde el listado de cotizaciones."
            getRowId={(f) => f.id}
          />
        </>
      ) : null}
    </PageContent>
  );
}
