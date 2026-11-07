/** Autoridad del selector de orden de una recepción: búsqueda y paginación en el servidor. */
import { useInfiniteQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { apiFetch } from "@/api/client";
import type { PagedResult, PurchaseOrderSummary } from "@/api/types";

const TAMANO_DE_PAGINA = 50;
const ESPERA_DE_BUSQUEDA_MS = 300;

export function useOrdenesRecibibles(companyId: string | null) {
  const [busqueda, setBusqueda] = useState("");
  const [termino, setTermino] = useState("");

  useEffect(() => {
    const espera = setTimeout(() => setTermino(busqueda.trim()), ESPERA_DE_BUSQUEDA_MS);
    return () => clearTimeout(espera);
  }, [busqueda]);

  const consulta = useInfiniteQuery({
    queryKey: ["compras", "ordenes-recibibles", companyId, termino],
    initialPageParam: 1,
    queryFn: ({ pageParam }) => {
      const parametros = new URLSearchParams({
        receivable: "true",
        page: String(pageParam),
        page_size: String(TAMANO_DE_PAGINA),
      });
      if (termino) parametros.set("q", termino);
      return apiFetch<PagedResult<PurchaseOrderSummary>>(`/purchasing/orders?${parametros.toString()}`);
    },
    getNextPageParam: (ultima, paginas) =>
      paginas.length * TAMANO_DE_PAGINA < ultima.total ? paginas.length + 1 : undefined,
    enabled: Boolean(companyId),
    retry: false,
  });

  const ordenes = consulta.data?.pages.flatMap((pagina) => pagina.items) ?? [];
  const total = consulta.data?.pages.at(-1)?.total ?? 0;
  return { busqueda, setBusqueda, consulta, ordenes, total };
}
