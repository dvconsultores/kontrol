/** Autoridad única de los selectores de almacén: el conjunto completo de la empresa activa. */
import { useQuery } from "@tanstack/react-query";

import { listAllWarehouses } from "@/api/organization";

export function useAlmacenesDeEmpresa(companyId: string | null) {
  return useQuery({
    queryKey: ["organizacion", "almacenes", companyId],
    // Si una página falla, la consulta falla entera: nunca se pinta una lista parcial como si fuera completa.
    queryFn: async () => ({ items: await listAllWarehouses(companyId ?? undefined) }),
    enabled: Boolean(companyId),
    retry: false,
  });
}
