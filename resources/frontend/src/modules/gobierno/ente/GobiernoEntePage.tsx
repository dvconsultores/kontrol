import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { useState } from "react";

import { ApiError, apiFetch } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Button } from "@/components/Button";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { ConflictState } from "@/components/ConflictState";
import { DataTable } from "@/components/DataTable";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { PageHeader } from "@/components/PageHeader";
import { formatearFecha } from "@/i18n";
import { PageContent } from "@/layout/PageContent";
import { AdjuntosPanel } from "@/modules/documentos/AdjuntosPanel";
import {
  CONSULTA_GOBIERNO,
  ETIQUETA_ACTO,
  ETIQUETA_CAMPO,
  ETIQUETA_ESTADO,
  ETIQUETA_FALTANTE,
  ETIQUETA_FORMA,
  ETIQUETA_NIVEL,
  type Ente,
  type EnteDatos,
  type VersionEnte,
  type VersionesEnte,
} from "@/modules/gobierno/api";

import { EnteFormulario, type CambiosEnte } from "./EnteFormulario";

type Modo = "ficha" | "alta" | "edicion" | "modificacion";

const COLUMNAS: ColumnDef<VersionEnte, unknown>[] = [
  { accessorKey: "version", header: "Versión" },
  {
    accessorKey: "estado",
    header: "Estado",
    cell: ({ row }) => ETIQUETA_ESTADO[row.original.estado],
  },
  {
    accessorKey: "creado_en",
    header: "Fecha",
    cell: ({ row }) => formatearFecha(row.original.creado_en),
  },
  {
    accessorKey: "motivo",
    header: "Motivo",
    cell: ({ row }) => row.original.motivo ?? "—",
  },
  {
    accessorKey: "actor_id",
    header: "Responsable",
    cell: ({ row }) => row.original.actor_id?.slice(0, 8) ?? "—",
  },
];

export function GobiernoEntePage(): React.JSX.Element {
  const { activeCompanyId } = useCompany();
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const qc = useQueryClient();
  const [modo, setModo] = useState<Modo>("ficha");
  const [erroresServidor, setErroresServidor] = useState<Record<string, string[]>>({});
  const [confirmarActivacion, setConfirmarActivacion] = useState(false);
  const [conflicto, setConflicto] = useState(false);

  const ente = useQuery({
    queryKey: [...CONSULTA_GOBIERNO, "ente", activeCompanyId],
    queryFn: () => apiFetch<Ente>("/gobierno/ente"),
    enabled: Boolean(activeCompanyId),
    retry: false,
  });

  const versiones = useQuery({
    queryKey: [...CONSULTA_GOBIERNO, "ente", activeCompanyId, "versiones"],
    queryFn: () => apiFetch<VersionesEnte>("/gobierno/ente/versiones"),
    enabled: Boolean(activeCompanyId && ente.data),
    retry: false,
  });

  const recargar = (): Promise<void> => qc.invalidateQueries({ queryKey: [...CONSULTA_GOBIERNO, "ente"] });

  function cambiarModo(nuevo: Modo): void {
    setErroresServidor({});
    setModo(nuevo);
  }

  function manejarError(e: unknown): void {
    if (e instanceof ApiError) {
      if (e.status === 409 && e.code === "GOV_ENTITY_STALE") {
        setConflicto(true);
        void recargar();
        return;
      }
      if (e.status === 409 && e.code === "GOV_ENTITY_INVALID_STATE") {
        notify({ type: "warning", title: "El ente ya estaba activo" });
        void recargar();
        return;
      }
      if (e.status === 422 && e.code === "GOV_ENTITY_INCOMPLETE") {
        const faltantes = Array.isArray(e.details?.faltantes) ? (e.details.faltantes as string[]) : [];
        notify({
          type: "error",
          title: "No se puede completar",
          description: faltantes.map((f) => ETIQUETA_FALTANTE[f] ?? f).join(", "),
        });
        return;
      }
      if (e.status === 422 && e.code === "GOV_ENTITY_REASON_REQUIRED") {
        setErroresServidor({ motivo: [e.message] });
        return;
      }
      if (e.status === 422 && e.code === "GOV_ENTITY_NO_CHANGES") {
        notify({ type: "warning", title: "No hay cambios que guardar" });
        return;
      }
      if (e.status === 422 && e.code === "VALIDATION_ERROR") {
        setErroresServidor(e.fieldErrors);
        return;
      }
      if (e.status === 403) {
        notify({ type: "error", title: "No tiene permiso para esta acción" });
        return;
      }
      notify({ type: "error", title: "No fue posible completar la operación", description: e.message });
      return;
    }
    notify({ type: "error", title: "No fue posible completar la operación" });
  }

  async function guardarAlta(cambios: CambiosEnte): Promise<void> {
    try {
      await apiFetch<Ente>("/gobierno/ente", { method: "POST", body: cambios });
      notify({ type: "success", title: "Ente registrado en borrador" });
      setErroresServidor({});
      setModo("ficha");
      await recargar();
    } catch (e) {
      manejarError(e);
    }
  }

  async function guardarCambios(cambios: CambiosEnte, motivo: string | null): Promise<void> {
    if (!ente.data) return;
    try {
      await apiFetch<Ente>("/gobierno/ente", {
        method: "PATCH",
        ifMatch: String(ente.data.version),
        body: { ...cambios, ...(modo === "modificacion" ? { motivo } : {}) },
      });
      notify({ type: "success", title: modo === "modificacion" ? "Modificación registrada" : "Cambios guardados" });
      setErroresServidor({});
      setModo("ficha");
      await recargar();
    } catch (e) {
      manejarError(e);
    }
  }

  async function activar(): Promise<void> {
    if (!ente.data) return;
    try {
      await apiFetch<Ente>("/gobierno/ente/activar", {
        method: "POST",
        ifMatch: String(ente.data.version),
      });
      notify({ type: "success", title: "Ente activado" });
      setConfirmarActivacion(false);
      await recargar();
    } catch (e) {
      manejarError(e);
    }
  }

  const crumbs = [{ label: "Gobierno" }, { label: "Configuración del ente" }];

  if (ente.isLoading) {
    return (
      <PageContent>
        <PageHeader title="Configuración del ente" crumbs={crumbs} />
        <LoadingState label="Cargando el ente…" />
      </PageContent>
    );
  }

  if (ente.error instanceof ApiError && ente.error.status === 403 && ente.error.code === "MODULE_NOT_ENTITLED") {
    return (
      <PageContent>
        <PageHeader title="Configuración del ente" crumbs={crumbs} />
        <EmptyState
          title="El módulo de Gobierno no está habilitado"
          description="La licencia de esta instalación no incluye el módulo de Gobierno. Consulte al responsable de la licencia."
        />
      </PageContent>
    );
  }

  if (ente.error instanceof ApiError && ente.error.status === 403) {
    return (
      <PageContent>
        <PageHeader title="Configuración del ente" crumbs={crumbs} />
        <EmptyState title="Sin acceso" description="No tiene permiso para ver el ente de este contenedor." />
      </PageContent>
    );
  }

  if (ente.error instanceof ApiError && ente.error.status === 404 && ente.error.code === "GOV_ENTITY_NOT_FOUND" && modo === "ficha") {
    return (
      <PageContent>
        <PageHeader title="Configuración del ente" crumbs={crumbs} />
        <EmptyState
          title="El ente aún no está configurado"
          description="Registre la identificación, la naturaleza y el acto de creación del ente."
          action={
            tiene("gobierno_ente:create", "empresa") ? (
              <Button onClick={() => cambiarModo("alta")}>Configurar el ente</Button>
            ) : undefined
          }
        />
      </PageContent>
    );
  }

  if (modo === "alta" && ente.error instanceof ApiError && ente.error.status === 404 && ente.error.code === "GOV_ENTITY_NOT_FOUND") {
    return (
      <PageContent>
        <PageHeader title="Configuración del ente" crumbs={crumbs} />
        <EnteFormulario
          modo="alta"
          inicial={null}
          onGuardar={guardarAlta}
          onCancelar={() => cambiarModo("ficha")}
          erroresServidor={erroresServidor}
        />
      </PageContent>
    );
  }

  if (ente.isError || !ente.data) {
    return (
      <PageContent>
        <PageHeader title="Configuración del ente" crumbs={crumbs} />
        <ErrorState message="No fue posible cargar el ente." onRetry={() => void ente.refetch()} />
      </PageContent>
    );
  }

  if (modo === "edicion" || modo === "modificacion") {
    const inicial: EnteDatos = {
      denominacion: ente.data.denominacion,
      siglas: ente.data.siglas,
      rif: ente.data.rif,
      nivel_territorial: ente.data.nivel_territorial,
      forma_organizativa: ente.data.forma_organizativa,
      organo_adscripcion: ente.data.organo_adscripcion,
      entidad_federal: ente.data.entidad_federal,
      municipio: ente.data.municipio,
      acto_tipo: ente.data.acto_tipo,
      acto_numero: ente.data.acto_numero,
      acto_fecha: ente.data.acto_fecha,
      acto_publicacion: ente.data.acto_publicacion,
    };
    return (
      <PageContent>
        <PageHeader title="Configuración del ente" crumbs={crumbs} />
        <EnteFormulario
          modo={modo}
          inicial={inicial}
          onGuardar={guardarCambios}
          onCancelar={() => cambiarModo("ficha")}
          erroresServidor={erroresServidor}
        />
      </PageContent>
    );
  }

  const datos = ente.data;
  const esBorrador = datos.estado === "BORRADOR";
  const faltantes = datos.faltantes_para_activar ?? [];
  const puedeEditar = tiene("gobierno_ente:edit", "empresa");
  const puedeActivar = tiene("gobierno_ente:activate", "empresa");

  const acciones: React.ReactNode[] = [];
  if (esBorrador) {
    if (puedeEditar) {
      acciones.push(
        <Button key="editar" variant="secondary" onClick={() => cambiarModo("edicion")}>
          Editar
        </Button>,
      );
    }
    if (puedeActivar) {
      acciones.push(
        <Button
          key="activar"
          disabled={faltantes.length > 0}
          aria-describedby={faltantes.length > 0 ? "requisitos-activar" : undefined}
          onClick={() => setConfirmarActivacion(true)}
        >
          Activar el ente
        </Button>,
      );
    }
  } else if (puedeEditar) {
    acciones.push(
      <Button key="modificar" variant="secondary" onClick={() => cambiarModo("modificacion")}>
        Modificar
      </Button>,
    );
  }

  const valorDe = (campo: keyof EnteDatos): string => {
    const valor = datos[campo];
    if (valor == null || valor === "") return "—";
    if (campo === "acto_fecha") {
      const [anio, mes, dia] = String(valor).split("-");
      return `${dia}/${mes}/${anio}`;
    }
    if (campo === "nivel_territorial") return ETIQUETA_NIVEL[valor as keyof typeof ETIQUETA_NIVEL] ?? String(valor);
    if (campo === "forma_organizativa") return ETIQUETA_FORMA[valor as keyof typeof ETIQUETA_FORMA] ?? String(valor);
    if (campo === "acto_tipo") return ETIQUETA_ACTO[valor as keyof typeof ETIQUETA_ACTO] ?? String(valor);
    return String(valor);
  };

  return (
    <PageContent>
      <PageHeader
        title={datos.denominacion}
        crumbs={crumbs}
        description={`Versión ${datos.version}`}
        status={
          <span className="rounded-full border border-border-default px-2 py-0.5 text-xs font-medium text-text-700">
            {ETIQUETA_ESTADO[datos.estado]}
          </span>
        }
        actions={acciones.length > 0 ? <div className="flex flex-wrap gap-2">{acciones}</div> : undefined}
      />

      {conflicto ? (
        <ConflictState
          message="Otra persona cambió el ente mientras lo editaba. Se cargó la versión vigente; revise y vuelva a intentarlo."
          onReload={() => {
            setConflicto(false);
            setModo("ficha");
          }}
        />
      ) : null}

      <section aria-labelledby="datos-ente" className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 id="datos-ente" className="mb-3 text-base font-semibold text-text-900">
          Datos del ente
        </h2>
        <div className="grid grid-cols-1 gap-x-6 gap-y-3 md:grid-cols-2">
          <div>
            <h3 className="mb-1 text-sm font-semibold text-text-700">Identificación</h3>
            <dl className="grid grid-cols-1 gap-x-6 gap-y-2 text-sm">
              {(["denominacion", "siglas", "rif"] as const).map((campo) => (
                <div key={campo}>
                  <dt className="text-text-500">{ETIQUETA_CAMPO[campo]}</dt>
                  <dd className="break-words text-text-900">{valorDe(campo)}</dd>
                </div>
              ))}
            </dl>
          </div>
          <div>
            <h3 className="mb-1 text-sm font-semibold text-text-700">Naturaleza</h3>
            <dl className="grid grid-cols-1 gap-x-6 gap-y-2 text-sm">
              {(["nivel_territorial", "forma_organizativa", "organo_adscripcion", "entidad_federal", "municipio"] as const).map(
                (campo) => (
                  <div key={campo}>
                    <dt className="text-text-500">{ETIQUETA_CAMPO[campo]}</dt>
                    <dd className="break-words text-text-900">{valorDe(campo)}</dd>
                  </div>
                ),
              )}
            </dl>
          </div>
          <div>
            <h3 className="mb-1 text-sm font-semibold text-text-700">Acto de creación</h3>
            <dl className="grid grid-cols-1 gap-x-6 gap-y-2 text-sm">
              {(["acto_tipo", "acto_numero", "acto_fecha", "acto_publicacion"] as const).map((campo) => (
                <div key={campo}>
                  <dt className="text-text-500">{ETIQUETA_CAMPO[campo]}</dt>
                  <dd className="break-words text-text-900">{valorDe(campo)}</dd>
                </div>
              ))}
            </dl>
          </div>
          {datos.estado === "ACTIVO" && datos.activado_en ? (
            <div>
              <h3 className="mb-1 text-sm font-semibold text-text-700">Activación</h3>
              <p className="text-sm text-text-900">Activado el {formatearFecha(datos.activado_en)}</p>
            </div>
          ) : null}
        </div>
      </section>

      {esBorrador ? (
        <section id="requisitos-activar" aria-labelledby="requisitos-titulo" className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 id="requisitos-titulo" className="mb-2 text-base font-semibold text-text-900">
            Requisitos para activar
          </h2>
          {faltantes.length > 0 ? (
            <>
              <p className="mb-2 text-sm text-text-700">Para activar el ente falta:</p>
              <ul className="list-inside list-disc text-sm text-text-900">
                {faltantes.map((f) => (
                  <li key={f}>{ETIQUETA_FALTANTE[f] ?? f}</li>
                ))}
              </ul>
            </>
          ) : (
            <p role="status" className="text-sm text-text-700">
              El ente está completo y puede activarse.
            </p>
          )}
        </section>
      ) : null}

      <section aria-labelledby="documento-acto" className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 id="documento-acto" className="mb-2 text-base font-semibold text-text-900">
          Documento del acto de creación
        </h2>
        <AdjuntosPanel
          resourceType="GovernmentEntity"
          resourceId={datos.id}
          title="Documento del acto de creación"
          onChange={() => void recargar()}
        />
        {datos.documento_vinculado === false ? (
          <p className="mt-2 text-sm text-text-700">
            Adjunte el acto de creación publicado (PDF o imagen) para poder activar el ente.
          </p>
        ) : null}
      </section>

      <section aria-labelledby="historial-versiones" className="rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 id="historial-versiones" className="mb-2 text-base font-semibold text-text-900">
          Historial de versiones
        </h2>
        <DataTable
          columns={COLUMNAS}
          data={versiones.data?.items ?? []}
          emptyTitle="Sin versiones"
          getRowId={(fila) => String(fila.version)}
        />
      </section>

      <ConfirmationDialog
        open={confirmarActivacion}
        title="¿Activar el ente?"
        description="Al activarlo, los datos quedan fijados en la versión vigente: cada cambio posterior exigirá un motivo y quedará en el historial y en la auditoría."
        confirmLabel="Activar"
        cancelLabel="Cancelar"
        onConfirm={activar}
        onCancel={() => setConfirmarActivacion(false)}
      />
    </PageContent>
  );
}
