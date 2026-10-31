/**
 * Pantallas de contexto de empresa sin resolver (ARCH-MC-001, N6).
 *
 * Mientras no haya empresa activa no se pinta ninguna pantalla de negocio: si
 * se pintara, dispararía peticiones de empresa sin saber cuál, y la respuesta
 * a «¿de qué empresa son estos datos?» sería «de ninguna en concreto».
 */
import { AlertTriangle, Building2, RefreshCw } from "lucide-react";
import { useLocation } from "react-router";

import { useCompany } from "@/app/contexts/CompanyContext";
import { Button } from "@/components/Button";
import { LoadingState } from "@/components/LoadingState";
import { useModuloGobierno } from "@/modules/gobierno/api";

export function EstadoDeEmpresa(): React.JSX.Element | null {
  const { estado, companies, selectCompany, refreshCompanies } = useCompany();
  const { pathname } = useLocation();
  const gobiernoActivo = useModuloGobierno();
  const esGobierno = gobiernoActivo && pathname.startsWith("/gobierno");

  const textos = esGobierno
    ? {
        cargando: "Cargando entes…",
        error_titulo: "No se pudieron cargar los entes",
        error_texto: "Sin la lista de entes autorizados no es posible saber en cuál operar.",
        ninguna_titulo: "No tiene entes asignados",
        ninguna_texto:
          "Su usuario no puede operar en ningún ente activo. Solicite acceso a quien administre la cuenta.",
        elegir_titulo: "Seleccione un ente",
        elegir_texto: "Puede operar en varios. Elija en cuál desea trabajar en esta pestaña.",
      }
    : {
        cargando: "Cargando empresas…",
        error_titulo: "No se pudieron cargar las empresas",
        error_texto: "Sin la lista de empresas autorizadas no es posible saber en cuál operar.",
        ninguna_titulo: "No tiene empresas asignadas",
        ninguna_texto:
          "Su usuario no puede operar en ninguna empresa activa. Solicite acceso a quien administre la cuenta.",
        elegir_titulo: "Seleccione una empresa",
        elegir_texto: "Puede operar en varias. Elija en cuál desea trabajar en esta pestaña.",
      };

  if (estado === "AUTH_LOADING" || estado === "COMPANY_LOADING") {
    return <LoadingState label={textos.cargando} />;
  }

  if (estado === "ERROR") {
    return (
      <div className="mx-auto max-w-lg py-16 text-center" role="alert">
        <AlertTriangle className="mx-auto size-8 text-danger-500" aria-hidden="true" />
        <h1 className="mt-4 text-lg font-medium text-text-900">
          {textos.error_titulo}
        </h1>
        <p className="mt-2 text-sm text-text-600">
          {textos.error_texto}
        </p>
        <div className="mt-6">
          <Button onClick={() => void refreshCompanies()}>
            <RefreshCw className="size-4" aria-hidden="true" />
            Reintentar
          </Button>
        </div>
      </div>
    );
  }

  if (estado === "NO_COMPANIES") {
    return (
      <div className="mx-auto max-w-lg py-16 text-center">
        <Building2 className="mx-auto size-8 text-text-400" aria-hidden="true" />
        <h1 className="mt-4 text-lg font-medium text-text-900">
          {textos.ninguna_titulo}
        </h1>
        <p className="mt-2 text-sm text-text-600">
          {textos.ninguna_texto}
        </p>
      </div>
    );
  }

  if (estado === "COMPANY_SELECTION_REQUIRED") {
    const operables = companies.filter((c) => c.status === "ACTIVE");
    return (
      <div className="mx-auto max-w-lg py-12">
        <div className="text-center">
          <Building2 className="mx-auto size-8 text-text-400" aria-hidden="true" />
          <h1 className="mt-4 text-lg font-medium text-text-900">{textos.elegir_titulo}</h1>
          <p className="mt-2 text-sm text-text-600">
            {textos.elegir_texto}
          </p>
        </div>
        <ul className="mt-6 space-y-2">
          {operables.map((c) => (
            <li key={c.id}>
              <button
                type="button"
                data-testid={`elegir-empresa-${c.code}`}
                onClick={() => selectCompany(c.id)}
                className="flex w-full items-center gap-3 rounded-md border border-border-default px-4 py-3 text-left hover:bg-surface-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600"
              >
                <Building2 className="size-5 shrink-0 text-text-400" aria-hidden="true" />
                <span className="min-w-0">
                  <span className="block truncate font-medium text-text-900">{c.legal_name}</span>
                  <span className="block truncate text-xs text-text-500">
                    {c.code} · {c.rif}
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    );
  }

  return null;
}
