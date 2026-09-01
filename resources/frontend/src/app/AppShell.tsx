/** AppShell — envoltura del shell de la aplicación con layout y rutas. */
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { Outlet } from "react-router";

import { esErrorDeContexto } from "@/app/company/errores";
import { esClaveDeEmpresa } from "@/app/company/queryScope";
import { useCompany } from "@/app/contexts/CompanyContext";
import { PageLayout } from "@/layout/PageLayout";
import { EstadoDeEmpresa } from "@/components/company/EstadoDeEmpresa";

export function AppShell(): React.JSX.Element {
  const { activeCompanyId, estado, onCompanyRejected } = useCompany();
  const queryClient = useQueryClient();
  const anterior = useRef<string | null>(activeCompanyId);

  // Al cambiar de empresa se descartan las consultas de la anterior. La
  // separación por clave ya impide que se muestren bajo la nueva; esto evita
  // además que se queden ocupando memoria y que una respuesta tardía de la
  // empresa anterior siga refrescando algo que ya nadie mira.
  useEffect(() => {
    if (anterior.current === activeCompanyId) {
      return;
    }
    anterior.current = activeCompanyId;
    void queryClient.cancelQueries({ predicate: (q) => esClaveDeEmpresa(q.queryKey) });
    queryClient.removeQueries({ predicate: (q) => esClaveDeEmpresa(q.queryKey) });
  }, [activeCompanyId, queryClient]);

  // Si el servidor rechaza la empresa activa —acceso revocado, empresa
  // desactivada o borrada— se suelta el contexto y se vuelve a preguntar qué
  // empresas son operables. No es un cierre de sesión: perder el acceso a una
  // empresa no invalida la sesión ni el acceso a las demás.
  useEffect(() => {
    const cache = queryClient.getQueryCache();
    return cache.subscribe((evento) => {
      if (evento.type !== "updated" || evento.action.type !== "error") {
        return;
      }
      if (esErrorDeContexto(evento.action.error)) {
        onCompanyRejected();
      }
    });
  }, [queryClient, onCompanyRejected]);

  if (estado !== "READY") {
    // Sin empresa resuelta no se pinta ninguna pantalla de negocio: hacerlo
    // dispararía peticiones de empresa sin saber cuál.
    return (
      <PageLayout>
        <EstadoDeEmpresa />
      </PageLayout>
    );
  }

  return (
    <PageLayout>
      {/* El contenido se remonta al cambiar de empresa. Sin esto, un detalle de
          la empresa A seguiría en pantalla bajo la B, y las selecciones locales
          —sucursal, almacén, cuenta bancaria, filas marcadas— sobrevivirían al
          cambio apuntando a entidades de otra empresa. */}
      <Outlet key={activeCompanyId ?? "sin-empresa"} />
    </PageLayout>
  );
}
