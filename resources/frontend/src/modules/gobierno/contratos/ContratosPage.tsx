import { Link, useSearchParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { EmptyState } from "@/components/EmptyState";
import { LoadingState } from "@/components/LoadingState";
import { PageHeader } from "@/components/PageHeader";
import { PageContent } from "@/layout/PageContent";
import { ErrorDeCarga } from "@/modules/gobierno/ocupacion/ErrorDeCarga";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import { CONSULTA_CONTRATOS, rutaContrato, TIPOS_INSTRUMENTO, type ContratoResumen } from "./api";

interface ListaResponse {
  items: ContratoResumen[];
}

function formatearPlazo(inicio: string | null, fin: string | null): string {
  if (!inicio && !fin) return "—";
  if (inicio && fin) return `${formatearFechaDeNegocio(inicio)} al ${formatearFechaDeNegocio(fin)}`;
  if (inicio) return `Desde ${formatearFechaDeNegocio(inicio)}`;
  return `Hasta ${formatearFechaDeNegocio(fin)}`;
}

export function ContratosPage() {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const [searchParams, setSearchParams] = useSearchParams();
  const estado = searchParams.get("estado") ?? "";
  const tipo = searchParams.get("tipo") ?? "";

  const consulta = useQuery({
    queryKey: [...CONSULTA_CONTRATOS, activeCompanyId, estado, tipo],
    queryFn: async () => {
      const query = new URLSearchParams();
      if (estado) query.set("estado", estado);
      if (tipo) query.set("tipo", tipo);
      const sufijo = query.toString();
      const ruta = sufijo ? `/gobierno/contratos?${sufijo}` : "/gobierno/contratos";
      return apiFetch<ListaResponse>(ruta);
    },
    enabled: tiene("gobierno_contratos:view", "empresa"),
  });

  const permisos = { vista: tiene("gobierno_contratos:view", "empresa") };

  function actualizarFiltro(nombre: "estado" | "tipo", valor: string) {
    const siguientes = new URLSearchParams(searchParams);
    if (nombre === "estado") {
      if (valor) siguientes.set("estado", valor);
      else siguientes.delete("estado");
    } else {
      if (valor) siguientes.set("tipo", valor);
      else siguientes.delete("tipo");
    }
    setSearchParams(siguientes);
  }

  return (
    <PageContent>
      <PageHeader
        crumbs={[{ label: "Gobierno" }, { label: "Contratos y órdenes" }]}
        title="Contratos y órdenes"
        description="Instrumentos derivados de adjudicaciones vigentes (CNT-01). Se crean desde la decisión ADJUDICADA del expediente."
      />

      {!permisos.vista ? (
        <EmptyState title="Sin acceso" description="No tiene permiso para ver contratos y órdenes." />
      ) : (
        <>
          <div className="mb-4 grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="filtro-estado" className="mb-1 block text-sm font-medium text-text-900">
                Estado
              </label>
              <select
                id="filtro-estado"
                className="w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
                value={estado}
                onChange={(evento) => actualizarFiltro("estado", evento.target.value)}
              >
                <option value="">Todos</option>
                <option value="BORRADOR">Borrador</option>
                <option value="FORMALIZADO">Formalizado</option>
              </select>
            </div>
            <div>
              <label htmlFor="filtro-tipo" className="mb-1 block text-sm font-medium text-text-900">
                Tipo
              </label>
              <select
                id="filtro-tipo"
                className="w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
                value={tipo}
                onChange={(evento) => actualizarFiltro("tipo", evento.target.value)}
              >
                <option value="">Todos</option>
                {TIPOS_INSTRUMENTO.map((instrumento) => (
                  <option key={instrumento.codigo} value={instrumento.codigo}>
                    {instrumento.etiqueta}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {consulta.isLoading ? (
            <LoadingState />
          ) : consulta.isError ? (
            <ErrorDeCarga
              message={consulta.error instanceof Error ? consulta.error.message : "No se pudieron cargar los contratos."}
              onRetry={() => void consulta.refetch()}
            />
          ) : consulta.data && consulta.data.items.length === 0 ? (
            <EmptyState
              title="Sin contratos ni órdenes"
              description="Cree uno desde la decisión ADJUDICADA de un expediente de contratación."
            />
          ) : (
            <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Lista de contratos y órdenes">
              <table className="w-full min-w-[800px] border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-border-subtle text-text-600">
                    <th className="px-3 py-2 font-medium">Identificación</th>
                    <th className="px-3 py-2 font-medium">Tipo</th>
                    <th className="px-3 py-2 font-medium">Estado</th>
                    <th className="px-3 py-2 font-medium">Expediente</th>
                    <th className="px-3 py-2 font-medium">Decisión</th>
                    <th className="px-3 py-2 font-medium">Contratista</th>
                    <th className="px-3 py-2 font-medium">Monto</th>
                    <th className="px-3 py-2 font-medium">Plazo</th>
                  </tr>
                </thead>
                <tbody>
                  {consulta.data?.items.map((contrato) => (
                    <tr key={contrato.id} className="border-b border-border-subtle align-top">
                      <td className="break-words px-3 py-2 text-text-900">
                        <Link className="text-brand-700 underline" to={rutaContrato(contrato.id)}>
                          {contrato.identificacion}
                        </Link>
                      </td>
                      <td className="px-3 py-2 text-text-900">{contrato.tipo_etiqueta ?? "—"}</td>
                      <td className="px-3 py-2 text-text-900">{contrato.estado_etiqueta}</td>
                      <td className="px-3 py-2 text-text-900">{contrato.expediente_numero}</td>
                      <td className="break-words px-3 py-2 text-text-900">{contrato.decision_referencia}</td>
                      <td className="break-words px-3 py-2 text-text-900">{contrato.contratista_nombre}</td>
                      <td className="px-3 py-2 text-text-900">
                        {contrato.monto} {contrato.moneda}
                      </td>
                      <td className="px-3 py-2 text-text-900">{formatearPlazo(contrato.fecha_inicio, contrato.fecha_fin)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </PageContent>
  );
}
