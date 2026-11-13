import { useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { ApiError, apiFetch } from "@/api/client";
import type { CatalogItemSummary, PurchaseOrderSummary } from "@/api/types";
import { useCompany } from "@/app/contexts/CompanyContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Autorizado } from "@/components/Autorizado";
import { AvisoDeAlmacenes } from "@/modules/organizacion/almacenes/AvisoDeAlmacenes";
import { useAlmacenesDeEmpresa } from "@/modules/organizacion/almacenes/useAlmacenesDeEmpresa";

export function LineasDeOrden({
  orderId,
  onCambios,
}: {
  orderId: string;
  onCambios?: () => void | Promise<void>;
}): React.JSX.Element {
  const queryClient = useQueryClient();
  const { activeCompany } = useCompany();
  const almacenes = useAlmacenesDeEmpresa(activeCompany?.id ?? null);
  const almacenesActivos = (almacenes.data?.items ?? []).filter((w) => w.status === "ACTIVE");
  const [seleccion, setSeleccion] = useState<Record<string, string>>({});
  const [errorPorLinea, setErrorPorLinea] = useState<Record<string, string>>({});

  const orden = useQuery({
    queryKey: ["compras", "orden", orderId],
    queryFn: () => apiFetch<PurchaseOrderSummary>(`/purchasing/orders/${orderId}`),
    retry: false,
  });

  const lineas = orden.data?.lines ?? [];
  const idsDeProducto = [...new Set(lineas.map((l) => l.product_id))];
  const productos = useQueries({
    queries: idsDeProducto.map((id) => ({
      queryKey: ["maestros", "producto", id],
      queryFn: () => apiFetch<CatalogItemSummary>(`/maestros/catalogos/items/${id}`),
      retry: false,
    })),
  });

  const nombreDeProducto = (id: string): string => {
    const producto = productos[idsDeProducto.indexOf(id)]?.data;
    return producto ? `${producto.code} · ${producto.name}` : "Producto sin identificar";
  };

  const fijarDestino = async (lineId: string): Promise<void> => {
    const warehouseId = seleccion[lineId];
    if (!warehouseId) {
      setErrorPorLinea((previo) => ({ ...previo, [lineId]: "Elija el almacén destino." }));
      return;
    }
    try {
      await apiFetch(`/purchasing/orders/${orderId}/lines/${lineId}/destination`, {
        method: "POST",
        body: { warehouse_id: warehouseId },
      });
      setErrorPorLinea((previo) => {
        const resto = { ...previo };
        delete resto[lineId];
        return resto;
      });
      void queryClient.invalidateQueries({ queryKey: ["compras", "orden", orderId] });
      await onCambios?.();
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "No fue posible fijar el destino";
      setErrorPorLinea((previo) => ({ ...previo, [lineId]: message }));
    }
  };

  if (orden.isLoading) {
    return <p role="status">Cargando líneas…</p>;
  }
  if (orden.isError) {
    return <p role="alert">No fue posible cargar las líneas de la orden.</p>;
  }
  if (lineas.length === 0) {
    return <p role="status">La orden no tiene líneas.</p>;
  }

  const codigo = orden.data?.code ?? "";

  return (
    <section aria-labelledby="lineas-de-orden-titulo" className="rounded-lg border border-border-default bg-surface-0 p-4">
      <h2 id="lineas-de-orden-titulo" className="mb-3 text-base font-semibold text-text-900">
        Líneas de la orden {codigo}
      </h2>
      <AvisoDeAlmacenes consulta={almacenes} />
      <div role="region" aria-label={`Líneas de la orden ${codigo}`} tabIndex={0} className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead>
            <tr className="border-b border-border-default text-text-900">
              <th scope="col" className="py-2 pr-3 font-medium">Producto</th>
              <th scope="col" className="py-2 pr-3 font-medium">Pedido</th>
              <th scope="col" className="py-2 pr-3 font-medium">Recibido</th>
              <th scope="col" className="py-2 pr-3 font-medium">Pendiente para la planificación</th>
              <th scope="col" className="py-2 font-medium">Almacén destino</th>
            </tr>
          </thead>
          <tbody>
            {lineas.map((linea) => {
              const productLabel = nombreDeProducto(linea.product_id);
              const destino = linea.destination_warehouse;
              return (
                <tr key={linea.id} className="border-b border-border-default align-top">
                  <td className="py-2 pr-3">{productLabel}</td>
                  <td className="py-2 pr-3">{String(Number(linea.quantity_ordered))}</td>
                  <td className="py-2 pr-3">{String(Number(linea.quantity_received))}</td>
                  <td className="py-2 pr-3">{linea.open_quantity ?? "0.000000"}</td>
                  <td className="py-2">
                    {destino ? (
                      `${destino.code} · ${destino.name}`
                    ) : (
                      <>
                        <p>Sin almacén destino: no cuenta en la planificación</p>
                        {linea.can_set_destination ? (
                          <Autorizado operacion={["POST", `/purchasing/orders/${orderId}/lines/${linea.id}/destination`]}>
                            <div className="mt-2 flex flex-wrap items-center gap-2">
                              <select
                                aria-label={`Almacén destino de ${productLabel}`}
                                value={seleccion[linea.id] ?? ""}
                                onChange={(e) => setSeleccion((previo) => ({ ...previo, [linea.id]: e.target.value }))}
                                className="h-9 rounded-md border border-border-default bg-surface-0 px-2 text-sm text-text-900"
                              >
                                <option value="">Seleccionar…</option>
                                {almacenesActivos.map((w) => (
                                  <option key={w.id} value={w.id}>{w.code} · {w.name}</option>
                                ))}
                              </select>
                              <AsyncButton size="sm" variant="secondary" onClick={() => fijarDestino(linea.id)}>
                                Fijar destino de {productLabel}
                              </AsyncButton>
                            </div>
                            {errorPorLinea[linea.id] ? <p role="alert" className="mt-1 text-red-600">{errorPorLinea[linea.id]}</p> : null}
                          </Autorizado>
                        ) : null}
                      </>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
