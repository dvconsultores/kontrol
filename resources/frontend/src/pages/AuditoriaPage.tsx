/** Auditoría — timeline de eventos con filtros y paginación (FR-001-070). */
import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { getAuditFilters, listAuditEvents, type ConsultaDeAuditoria } from "@/api/audit";
import type { AuditEvent } from "@/api/types";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { Button } from "@/components/Button";
import { DataTable } from "@/components/DataTable";
import { DateInput } from "@/components/DateInput";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { Pagination } from "@/components/Pagination";
import { TextInput } from "@/components/TextInput";
import { formatearFecha } from "@/i18n";
import { createColumnHelper } from "@tanstack/react-table";

const columnHelper = createColumnHelper<AuditEvent>();

interface FiltrosAplicados {
  desde: string;
  hasta: string;
  action: string;
  entity_type: string;
  username: string;
  scope: string;
  company_id: string;
  request_id: string;
}

const FILTROS_VACIOS: FiltrosAplicados = {
  desde: "",
  hasta: "",
  action: "",
  entity_type: "",
  username: "",
  scope: "",
  company_id: "",
  request_id: "",
};

interface FiltrosBorrador {
  desde: string;
  hasta: string;
  accion: string;
  entidad: string;
  username: string;
  ambito: string;
  request_id: string;
}

const BORRADOR_VACIO: FiltrosBorrador = {
  desde: "",
  hasta: "",
  accion: "",
  entidad: "",
  username: "",
  ambito: "",
  request_id: "",
};

function errorDeConsulta(error: unknown): string {
  const status = (error as { status?: number }).status;
  const code = (error as { code?: string }).code;
  if (status === 403) {
    return "No tiene autoridad de auditoría para consultar estos eventos.";
  }
  if (code === "INVALID_DATE_RANGE") {
    return "El rango de fechas no es válido: “Desde” no puede ser posterior a “Hasta”.";
  }
  return "No fue posible cargar la auditoría.";
}

export function AuditoriaPage(): React.JSX.Element {
  const { tiene } = useAutoridad();
  // Paginación de servidor (contrato de listados), como en Empresas: la
  // página es cero-based en la interfaz y uno-based en la petición, y
  // cambiar el tamaño vuelve a la primera.
  const [pagina, setPagina] = useState(0);
  const [tamano, setTamano] = useState(10);
  const [borrador, setBorrador] = useState<FiltrosBorrador>(BORRADOR_VACIO);
  const [aplicados, setAplicados] = useState<FiltrosAplicados>(FILTROS_VACIOS);
  const [errorDesde, setErrorDesde] = useState<string | undefined>(undefined);
  const [eventoAbiertoId, setEventoAbiertoId] = useState<string | null>(null);
  const tituloDetalle = useRef<HTMLHeadingElement | null>(null);

  const filtros = useQuery({
    queryKey: ["audit", "filters"],
    queryFn: getAuditFilters,
    retry: false,
  });

  const acciones = filtros.data?.actions ?? [];
  const accionesOrdenadas = [...acciones].sort((a, b) => a.label.localeCompare(b.label, "es"));
  const empresas = filtros.data?.companies ?? [];
  const tenantWide = filtros.data?.tenant_wide ?? false;

  const consulta: ConsultaDeAuditoria = {
    page: pagina + 1,
    page_size: tamano,
    ...(aplicados.desde ? { desde: aplicados.desde } : {}),
    ...(aplicados.hasta ? { hasta: aplicados.hasta } : {}),
    ...(aplicados.action ? { action: aplicados.action } : {}),
    ...(aplicados.entity_type ? { entity_type: aplicados.entity_type } : {}),
    ...(aplicados.scope ? { scope: aplicados.scope as "TENANT" | "COMPANY" } : {}),
    ...(aplicados.company_id ? { company_id: aplicados.company_id } : {}),
    ...(aplicados.username ? { username: aplicados.username } : {}),
    ...(aplicados.request_id ? { request_id: aplicados.request_id } : {}),
  };

  const query = useQuery({
    queryKey: ["audit", "events", aplicados, pagina, tamano],
    queryFn: () => listAuditEvents(consulta),
    retry: false,
  });

  const columns = [
    columnHelper.accessor("event_time", {
      header: "Fecha",
      cell: (info) => formatearFecha(info.getValue()),
    }),
    columnHelper.accessor("action", {
      header: "Acción",
      cell: (info) => {
        const evento = info.row.original;
        return (
          <div>
            <div>{evento.action_label}</div>
            <div className="text-xs text-text-500">{evento.action}</div>
          </div>
        );
      },
    }),
    columnHelper.accessor("entity_type", {
      header: "Entidad",
      cell: (info) => {
        const evento = info.row.original;
        return (
          <div>
            <div>{evento.entity_type}</div>
            <div className="text-xs text-text-500">{evento.entity_id ?? "—"}</div>
          </div>
        );
      },
    }),
    columnHelper.accessor("user_id", {
      header: "Usuario",
      cell: (info) => {
        const evento = info.row.original;
        return evento.username ?? (evento.user_id ? evento.user_id : "Sistema");
      },
    }),
    columnHelper.accessor("scope", {
      header: "Ámbito",
      cell: (info) => {
        const evento = info.row.original;
        if (evento.scope === "TENANT") return "Tenant";
        return evento.company_name ?? (evento.company_id ?? "Empresa no registrada (evento histórico)");
      },
    }),
    columnHelper.accessor("request_id", {
      header: "Correlación",
      cell: (info) => info.getValue() ?? "—",
    }),
    columnHelper.display({
      id: "detalle",
      header: "Detalle",
      cell: (info) => {
        const evento = info.row.original;
        const abierto = eventoAbiertoId === evento.id;
        return (
          <Button
            variant="secondary"
            size="sm"
            data-evento-id={evento.id}
            aria-expanded={abierto}
            aria-controls="detalle-auditoria"
            onClick={() => setEventoAbiertoId(abierto ? null : evento.id)}
          >
            Ver detalle
          </Button>
        );
      },
    }),
  ];

  const eventoAbierto = query.data?.items?.find((evento) => evento.id === eventoAbiertoId) ?? null;

  useEffect(() => {
    if (eventoAbiertoId) {
      tituloDetalle.current?.focus();
    }
  }, [eventoAbiertoId]);

  useEffect(() => {
    if (!eventoAbiertoId) {
      return;
    }
    return () => {
      const boton = document.querySelector<HTMLButtonElement>(`[data-evento-id="${eventoAbiertoId}"]`);
      boton?.focus();
    };
  }, [eventoAbiertoId]);

  function traducirBorrador(borradorActual: FiltrosBorrador): FiltrosAplicados {
    const [action, entityTypeDeAccion] = borradorActual.accion ? borradorActual.accion.split("|") : ["", ""];
    return {
      desde: borradorActual.desde,
      hasta: borradorActual.hasta,
      action,
      entity_type: action ? entityTypeDeAccion : borradorActual.entidad,
      username: borradorActual.username,
      scope: borradorActual.ambito === "TENANT" ? "TENANT" : "",
      company_id: borradorActual.ambito.startsWith("company:") ? borradorActual.ambito.slice("company:".length) : "",
      request_id: borradorActual.request_id,
    };
  }

  function aplicarBorrador(): void {
    if (borrador.desde && borrador.hasta && borrador.desde > borrador.hasta) {
      setErrorDesde("“Desde” no puede ser posterior a “Hasta”.");
      return;
    }
    setErrorDesde(undefined);
    setAplicados(traducirBorrador(borrador));
    setPagina(0);
  }

  function limpiar(): void {
    setBorrador(BORRADOR_VACIO);
    setAplicados(FILTROS_VACIOS);
    setErrorDesde(undefined);
    setPagina(0);
  }

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Auditoría"
        description={tiene("audit:view", "tenant") ? "Eventos de acceso y operaciones de todas las empresas del tenant, incluidos los que no pertenecen a ninguna empresa (como los inicios de sesión)." : "Eventos de las empresas en las que usted tiene autoridad de auditoría. Los eventos sin empresa (como los inicios de sesión) solo los ve quien audita todas las empresas del tenant."}
        crumbs={[{ label: "Auditoría" }]}
      />
      <form
        aria-label="Filtros de auditoría"
        className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4"
        onSubmit={(evento) => {
          evento.preventDefault();
          aplicarBorrador();
        }}
      >
        <FormField label="Desde" error={errorDesde} help="Día de Caracas, incluido">
          <DateInput value={borrador.desde} onChange={(evento) => setBorrador({ ...borrador, desde: evento.target.value })} />
        </FormField>
        <FormField label="Hasta" help="Día de Caracas, incluido">
          <DateInput value={borrador.hasta} onChange={(evento) => setBorrador({ ...borrador, hasta: evento.target.value })} />
        </FormField>
        <FormField label="Acción">
          <select
            className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
            value={borrador.accion}
            onChange={(evento) => setBorrador({ ...borrador, accion: evento.target.value })}
          >
            <option value="">Todas</option>
            {accionesOrdenadas.map((accion) => (
              <option key={`${accion.code}|${accion.entity_type}`} value={`${accion.code}|${accion.entity_type}`}>
                {`${accion.label} (${accion.code} · ${accion.entity_type})`}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Entidad" help="Tipo exacto, p. ej. Document">
          <TextInput value={borrador.entidad} onChange={(evento) => setBorrador({ ...borrador, entidad: evento.target.value })} />
        </FormField>
        <FormField label="Usuario" help="Nombre de usuario exacto">
          <TextInput value={borrador.username} onChange={(evento) => setBorrador({ ...borrador, username: evento.target.value })} />
        </FormField>
        <FormField label="Ámbito">
          <select
            className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
            value={borrador.ambito}
            onChange={(evento) => setBorrador({ ...borrador, ambito: evento.target.value })}
          >
            <option value="">Todas las que audito</option>
            {tenantWide ? <option value="TENANT">Solo eventos del tenant</option> : null}
            {empresas.map((empresa) => (
              <option key={empresa.id} value={`company:${empresa.id}`}>
                {`Empresa ${empresa.code} · ${empresa.name}`}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Correlación" help="Identificador de la petición (request ID)">
          <TextInput value={borrador.request_id} onChange={(evento) => setBorrador({ ...borrador, request_id: evento.target.value })} />
        </FormField>
        <div className="flex items-end gap-2 sm:col-span-2 lg:col-span-4">
          <Button type="submit">Aplicar filtros</Button>
          <Button type="button" variant="secondary" onClick={limpiar}>Limpiar</Button>
        </div>
      </form>
      {query.isFetching && !query.isLoading ? <p role="status">Actualizando…</p> : null}
      <DataTable
        columns={columns}
        // El servidor ya entrega una página: las filas son `items` y la tabla no vuelve a paginar.
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? errorDeConsulta(query.error) : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin eventos"
        emptyDescription="No hay eventos de auditoría registrados con los filtros actuales."
        manualPagination
      />
      {query.isError ? (
        <div className="mt-3">
          <Button variant="secondary" onClick={() => void query.refetch()}>Reintentar</Button>
        </div>
      ) : null}
      {query.data && query.data.total > 10 ? (
        <Pagination
          pageIndex={pagina}
          pageSize={tamano}
          total={query.data.total}
          onPageChange={setPagina}
          onPageSizeChange={(valor) => {
            setTamano(valor);
            setPagina(0);
          }}
        />
      ) : null}
      {eventoAbierto ? (
        <section id="detalle-auditoria" aria-labelledby="detalle-auditoria-titulo" className="mt-6 rounded-md border border-border-default bg-surface-0 p-4">
          <h2 id="detalle-auditoria-titulo" tabIndex={-1} ref={tituloDetalle} className="text-lg font-semibold text-text-900">
            Detalle del evento
          </h2>
          <dl className="mt-3 grid gap-3 sm:grid-cols-2">
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-text-600">Acción</dt>
              <dd className="text-sm text-text-700">{eventoAbierto.action_label}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-text-600">Código</dt>
              <dd className="text-sm text-text-700">{eventoAbierto.action}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-text-600">Entidad</dt>
              <dd className="text-sm text-text-700">{eventoAbierto.entity_type}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-text-600">Identificador</dt>
              <dd className="text-sm text-text-700">{eventoAbierto.entity_id ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-text-600">Fecha (Caracas)</dt>
              <dd className="text-sm text-text-700">{formatearFecha(eventoAbierto.event_time)}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-text-600">Usuario</dt>
              <dd className="text-sm text-text-700">{eventoAbierto.username ?? (eventoAbierto.user_id ?? "—")}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-text-600">Ámbito</dt>
              <dd className="text-sm text-text-700">{eventoAbierto.scope === "TENANT" ? "Tenant" : (eventoAbierto.company_name ?? (eventoAbierto.company_id ?? "Empresa no registrada (evento histórico)"))}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-text-600">Origen</dt>
              <dd className="text-sm text-text-700">{eventoAbierto.source ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-text-600">Motivo</dt>
              <dd className="text-sm text-text-700">{eventoAbierto.reason ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-text-600">Correlación</dt>
              <dd className="text-sm text-text-700">{eventoAbierto.request_id ?? "—"}</dd>
            </div>
          </dl>
          {Object.keys(eventoAbierto.details).length === 0 ? (
            <p className="mt-4 text-sm text-text-500">Sin detalle registrado para este evento.</p>
          ) : (
            <div className="mt-4 space-y-4">
              {Object.entries(eventoAbierto.details).map(([seccion, valores]) => {
                const rotulo = seccion === "before" ? "Antes" : seccion === "after" ? "Después" : seccion === "evidence" ? "Evidencia" : seccion;
                return (
                  <div key={seccion}>
                    <h3 className="text-sm font-semibold text-text-900">{rotulo}</h3>
                    <dl className="mt-2 space-y-2">
                      {Object.entries(valores).map(([clave, valor]) => (
                        <div key={clave}>
                          <dt className="text-xs font-semibold text-text-600">{clave}</dt>
                          <dd className="text-sm text-text-700">{typeof valor === "string" ? valor : JSON.stringify(valor)}</dd>
                        </div>
                      ))}
                    </dl>
                  </div>
                );
              })}
            </div>
          )}
          <Button
            variant="secondary"
            className="mt-4"
            onClick={() => setEventoAbiertoId(null)}
          >
            Cerrar detalle
          </Button>
        </section>
      ) : null}
    </PageContent>
  );
}
