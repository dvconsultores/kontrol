/** Detalle de almacén — estructura adaptada al almacén (Spec 008, FR-008-072/078).
 *
 * La regla de esta pantalla: **muestra solo los tramos que el almacén
 * declara**. Un almacén simple no ve pestañas vacías de zona, pasillo, rack ni
 * nivel; uno complejo las ve todas. Es la mitigación del riesgo dominante de
 * la Spec (RSK-008-01): que la jerarquía sea tan pesada que nadie la mantenga.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Ban, Power, Trash2 } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { useParams } from "react-router";

import { apiFetch } from "@/api/client";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";

import {
  LEVEL_LABEL, STRUCTURE_LEVELS, can,
  type BlockDetails, type Paged, type StructureLevel, type StructureNode,
  type Warehouse, type WarehouseLocation,
} from "./types";

type Tab = StructureLevel | "locations";

/** Extrae el motivo y las dependencias que **devuelve el backend**. La UI no
 *  redacta la explicación de un bloqueo: la muestra. */
function blockMessage(err: unknown): string {
  const details = (err as { details?: BlockDetails })?.details;
  if (details?.reason) {
    const deps = details.dependencies
      ? Object.entries(details.dependencies)
          .filter(([, v]) => typeof v === "number" || typeof v === "string")
          .map(([k, v]) => `${k}: ${String(v)}`).join(", ")
      : "";
    return deps ? `${details.reason} (${deps})` : details.reason;
  }
  return err instanceof Error ? err.message : "Operación rechazada";
}

export function AlmacenDetallePage(): React.JSX.Element {
  const { warehouseId = "" } = useParams();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const [tab, setTab] = useState<Tab>("locations");
  const [nodeCode, setNodeCode] = useState("");
  const [nodeName, setNodeName] = useState("");
  const [parentId, setParentId] = useState("");
  const [locationCode, setLocationCode] = useState("");

  const warehouse = useQuery({
    queryKey: ["organization", "warehouse", warehouseId],
    queryFn: () => apiFetch<Warehouse>(`/organization/warehouses/${warehouseId}`),
    enabled: Boolean(warehouseId), retry: false,
  });

  const declared = useMemo(() => warehouse.data?.declared_levels ?? [], [warehouse.data]);
  const activeTab: Tab = tab !== "locations" && !declared.includes(tab) ? "locations" : tab;
  const nodeLevel = activeTab === "locations" ? null : activeTab;

  const nodes = useQuery({
    queryKey: ["organization", "nodes", warehouseId, nodeLevel],
    queryFn: () => apiFetch<StructureNode[]>(
      `/organization/warehouses/${warehouseId}/${LEVEL_LABEL[nodeLevel as StructureLevel].path}`),
    enabled: Boolean(warehouseId) && nodeLevel !== null, retry: false,
  });

  const parentLevel: StructureLevel | null = useMemo(() => {
    if (!nodeLevel) return null;
    const index = declared.indexOf(nodeLevel);
    return index > 0 ? declared[index - 1] : null;
  }, [declared, nodeLevel]);

  const parents = useQuery({
    queryKey: ["organization", "nodes", warehouseId, parentLevel],
    queryFn: () => apiFetch<StructureNode[]>(
      `/organization/warehouses/${warehouseId}/${LEVEL_LABEL[parentLevel as StructureLevel].path}`),
    enabled: Boolean(warehouseId) && parentLevel !== null, retry: false,
  });

  const locations = useQuery({
    queryKey: ["organization", "locations", warehouseId],
    queryFn: () => apiFetch<Paged<WarehouseLocation>>(
      `/organization/locations?warehouse_id=${warehouseId}&limit=100`),
    enabled: Boolean(warehouseId) && activeTab === "locations", retry: false,
  });

  const runAction = useCallback(async (label: string, fn: () => Promise<unknown>): Promise<void> => {
    try {
      await fn();
      notify({ type: "success", title: label });
      void queryClient.invalidateQueries({ queryKey: ["organization"] });
    } catch (err) {
      notify({ type: "error", title: `No fue posible ${label.toLowerCase()}`, description: blockMessage(err) });
    }
  }, [notify, queryClient]);

  /** Si el almacén declara un tramo padre, el nodo debe colgar de él: crear un
   *  pasillo suelto en un almacén con zonas produce un nodo que nunca podrá
   *  formar parte de una cadena completa. */
  const parentRequired = parentLevel !== null && (parents.data ?? []).length > 0;
  const parentMissing = parentRequired && !parentId;

  const createNode = async (): Promise<void> => {
    if (!nodeLevel || !nodeCode.trim() || !nodeName.trim() || parentMissing) return;
    await runAction(`${LEVEL_LABEL[nodeLevel].singular} creado`, async () => {
      await apiFetch(`/organization/warehouses/${warehouseId}/${LEVEL_LABEL[nodeLevel].path}`, {
        method: "POST",
        body: { code: nodeCode, name: nodeName, parent_id: parentId || null },
      });
      setNodeCode(""); setNodeName("");
    });
  };

  const createLocation = async (): Promise<void> => {
    await runAction("Ubicación creada", async () => {
      await apiFetch("/organization/locations", {
        method: "POST",
        body: { warehouse_id: warehouseId, code: locationCode || null },
      });
      setLocationCode("");
    });
  };

  const nodeColumns = useMemo<ColumnDef<StructureNode, unknown>[]>(() => [
    { accessorKey: "code", header: "Código" },
    { accessorKey: "name", header: "Nombre" },
    { accessorKey: "sequence", header: "Secuencia" },
    { accessorKey: "status", header: "Estado" },
    {
      id: "actions", header: "Acciones",
      cell: ({ row }) => {
        const node = row.original;
        const level = nodeLevel as StructureLevel;
        return (
          <div className="flex justify-end gap-1">
            {can(node, "deactivate") || can(node, "activate") ? (
              <AsyncButton
                variant="ghost" size="sm"
                aria-label={`${can(node, "deactivate") ? "Desactivar" : "Activar"} ${node.code}`}
                title={can(node, "deactivate") ? "Desactivar" : "Activar"}
                onClick={() => runAction(
                  can(node, "deactivate") ? "Nodo desactivado" : "Nodo activado",
                  () => apiFetch(
                    `/organization/${LEVEL_LABEL[level].path}/${node.id}/` +
                    (can(node, "deactivate") ? "deactivate" : "activate"), { method: "POST" }))}
              >
                <Power className="h-4 w-4" aria-hidden="true" />
              </AsyncButton>
            ) : null}
            <AsyncButton
              variant="ghost" size="sm" disabled={!can(node, "delete")}
              aria-label={can(node, "delete")
                ? `Eliminar ${node.code}`
                : `${node.code} no puede eliminarse: tiene descendientes o histórico`}
              title={can(node, "delete") ? "Eliminar" : "No puede eliminarse: desactívelo"}
              onClick={() => runAction("Nodo eliminado", () => apiFetch(
                `/organization/${LEVEL_LABEL[level].path}/${node.id}`, { method: "DELETE" }))}
            >
              {can(node, "delete")
                ? <Trash2 className="h-4 w-4" aria-hidden="true" />
                : <Ban className="h-4 w-4" aria-hidden="true" />}
            </AsyncButton>
          </div>
        );
      },
    },
  ], [nodeLevel, runAction]);

  const locationColumns = useMemo<ColumnDef<WarehouseLocation, unknown>[]>(() => [
    { accessorKey: "code", header: "Código" },
    { id: "path", header: "Ubicación física", cell: ({ row }) => row.original.display_path },
    { accessorKey: "status", header: "Estado" },
    {
      id: "actions", header: "Acciones",
      cell: ({ row }) => {
        const loc = row.original;
        return (
          <div className="flex justify-end gap-1">
            <AsyncButton
              variant="ghost" size="sm"
              aria-label={`${can(loc, "deactivate") ? "Desactivar" : "Activar"} la ubicación ${loc.code}`}
              title={can(loc, "deactivate") ? "Desactivar" : "Activar"}
              onClick={() => runAction(
                can(loc, "deactivate") ? "Ubicación desactivada" : "Ubicación activada",
                () => apiFetch(`/organization/locations/${loc.id}/` +
                  (can(loc, "deactivate") ? "deactivate" : "activate"), { method: "POST" }))}
            >
              <Power className="h-4 w-4" aria-hidden="true" />
            </AsyncButton>
            <AsyncButton
              variant="ghost" size="sm" disabled={!loc.can_delete}
              aria-label={loc.can_delete
                ? `Eliminar la ubicación ${loc.code}`
                : `${loc.code} no puede eliminarse: tiene historial de inventario`}
              title={loc.can_delete ? "Eliminar" : "No puede eliminarse: tiene historial. Desactívela."}
              onClick={() => runAction("Ubicación eliminada", () => apiFetch(
                `/organization/locations/${loc.id}`, { method: "DELETE" }))}
            >
              {loc.can_delete
                ? <Trash2 className="h-4 w-4" aria-hidden="true" />
                : <Ban className="h-4 w-4" aria-hidden="true" />}
            </AsyncButton>
          </div>
        );
      },
    },
  ], [runAction]);

  const data = warehouse.data;

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title={data ? `${data.code} · ${data.name}` : "Almacén"}
        description={
          data
            ? declared.length === 0
              ? "Almacén simple: las ubicaciones se crean directamente, sin tramos intermedios."
              : `Estructura: ${declared.map((l) => LEVEL_LABEL[l].singular).join(" → ")} → Ubicación`
            : undefined
        }
        crumbs={[{ label: "Organización" }, { label: "Almacenes", to: "/organizacion/almacenes" },
                 { label: data?.code ?? "Detalle" }]}
      />

      {warehouse.isError ? (
        <p className="text-sm text-danger-600" role="alert">No fue posible cargar el almacén.</p>
      ) : null}

      {data ? (
        <>
          {data.structure_regime === "OPERATIONAL" ? (
            <div className="mb-4 rounded-md border border-border-default bg-surface-50 p-3 text-sm text-text-600" role="note">
              Este almacén está en operación. Los tramos que ya tienen nodos no pueden retirarse ni
              reordenarse: cambiarlos reinterpretaría las ubicaciones y el historial existentes.
            </div>
          ) : null}

          <div className="mb-4 flex flex-wrap gap-1 border-b border-border-default" role="tablist"
               aria-label="Secciones del almacén">
            {/* Solo se ofrecen los tramos que el almacén declara (FR-008-078). */}
            {STRUCTURE_LEVELS.filter((level) => declared.includes(level)).map((level) => (
              <button
                key={level} type="button" role="tab" aria-selected={activeTab === level}
                onClick={() => { setTab(level); setParentId(""); }}
                className={`cursor-pointer border-b-2 px-4 py-2 text-sm ${
                  activeTab === level
                    ? "border-primary-600 font-medium text-primary-700"
                    : "border-transparent text-text-600 hover:text-text-900"}`}
              >
                {LEVEL_LABEL[level].plural}
              </button>
            ))}
            <button
              type="button" role="tab" aria-selected={activeTab === "locations"}
              onClick={() => setTab("locations")}
              className={`cursor-pointer border-b-2 px-4 py-2 text-sm ${
                activeTab === "locations"
                  ? "border-primary-600 font-medium text-primary-700"
                  : "border-transparent text-text-600 hover:text-text-900"}`}
            >
              Ubicaciones
            </button>
          </div>

          {nodeLevel ? (
            <section className="rounded-lg border border-border-default bg-surface-0 p-4">
              <h2 className="mb-3 text-base font-semibold text-text-900">
                {LEVEL_LABEL[nodeLevel].plural}
              </h2>
              <form className="mb-4 flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
                <FormField label="Código" required>
                  <TextInput value={nodeCode} onChange={(e) => setNodeCode(e.target.value)} required />
                </FormField>
                <FormField label="Nombre" required>
                  <TextInput value={nodeName} onChange={(e) => setNodeName(e.target.value)} required />
                </FormField>
                {parentLevel ? (
                  <FormField
                    label={LEVEL_LABEL[parentLevel].singular}
                    required={parentRequired}
                    help={parentRequired
                      ? undefined
                      : `Todavía no hay ${LEVEL_LABEL[parentLevel].plural.toLowerCase()}: el nodo se creará sin asignar.`}
                  >
                    <select
                      value={parentId} onChange={(e) => setParentId(e.target.value)}
                      aria-label={`${LEVEL_LABEL[parentLevel].singular} al que pertenece`}
                      className="h-10 w-56 cursor-pointer rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                    >
                      <option value="">{parentRequired ? "Seleccione…" : "Sin asignar"}</option>
                      {(parents.data ?? []).map((p) => (
                        <option key={p.id} value={p.id}>{p.code} · {p.name}</option>
                      ))}
                    </select>
                  </FormField>
                ) : null}
                <AsyncButton type="submit" variant="primary" onClick={createNode} disabled={parentMissing}>
                  Añadir {LEVEL_LABEL[nodeLevel].singular.toLowerCase()}
                </AsyncButton>
              </form>
              <DataTable
                columns={nodeColumns} data={nodes.data ?? []} loading={nodes.isLoading}
                error={nodes.isError ? "No fue posible cargar los nodos." : null}
                emptyTitle={`Sin ${LEVEL_LABEL[nodeLevel].plural.toLowerCase()}`}
                emptyDescription="Añada el primero con el formulario superior."
                getRowId={(row) => row.id}
              />
            </section>
          ) : (
            <section className="rounded-lg border border-border-default bg-surface-0 p-4">
              <h2 className="mb-3 text-base font-semibold text-text-900">Ubicaciones</h2>
              <form className="mb-4 flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
                <FormField
                  label="Código"
                  help={data.code_policy === "GENERATED" ? "Vacío = se genera con el patrón del almacén" : undefined}
                  required={data.code_policy === "MANUAL"}
                >
                  <TextInput
                    value={locationCode} onChange={(e) => setLocationCode(e.target.value)}
                    placeholder={data.code_policy === "GENERATED" ? "Automático" : "Ej. A-0001"}
                  />
                </FormField>
                <AsyncButton type="submit" variant="primary" onClick={createLocation}>
                  Añadir ubicación
                </AsyncButton>
              </form>
              <DataTable
                columns={locationColumns} data={locations.data?.items ?? []}
                loading={locations.isLoading}
                error={locations.isError ? "No fue posible cargar las ubicaciones." : null}
                emptyTitle="Sin ubicaciones"
                emptyDescription="Añada la primera con el formulario superior."
                getRowId={(row) => row.id}
              />
            </section>
          )}
        </>
      ) : null}
    </PageContent>
  );
}
