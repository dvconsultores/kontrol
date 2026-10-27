/** Tipos de movimiento — configuración de tipos de movimiento de inventario (FR-003-020/021). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { MovementType, PagedResult } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Autorizado } from "@/components/Autorizado";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

const columnHelper = createColumnHelper<MovementType>();

const DIRECTIONS = [
  { value: "IN", label: "Entrada" },
  { value: "OUT", label: "Salida" },
  { value: "INTERNAL", label: "Interno" },
];

export function TiposMovimientoPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const [newCode, setNewCode] = useState("");
  const [newName, setNewName] = useState("");
  const [newDirection, setNewDirection] = useState("IN");
  const [newGlobal, setNewGlobal] = useState(false);

  const query = useQuery({
    queryKey: ["inventario", "movement-types"],
    queryFn: () => apiFetch<PagedResult<MovementType>>("/inventory/movement-types"),
    retry: false,
  });

  const refresh = async (): Promise<void> => {
    await queryClient.invalidateQueries({ queryKey: ["inventario", "movement-types"] });
  };

  const createType = async (): Promise<void> => {
    try {
      await apiFetch("/inventory/movement-types", {
        method: "POST",
        body: { code: newCode, name: newName, direction: newDirection, global_scope: newGlobal },
      });
      notify({ type: "success", title: "Tipo creado", description: newCode });
      setNewCode(""); setNewName(""); setNewDirection("IN"); setNewGlobal(false);
      void refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear el tipo";
      notify({ type: "error", title: "No fue posible crear el tipo", description: message });
    }
  };

  const columns = [
    columnHelper.accessor("code", { header: "Código" }),
    columnHelper.accessor("name", { header: "Nombre" }),
    columnHelper.accessor("direction", { header: "Dirección" }),
    columnHelper.accessor("status", { header: "Estado" }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Tipos de movimiento"
        description="Configure los tipos de movimiento que determinan el efecto sobre existencias."
        crumbs={[{ label: "Inventario" }, { label: "Tipos de movimiento" }]}
      />
      <Autorizado operacion={["POST", "/inventory/movement-types"]}>
      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Nuevo tipo</h2>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Código" required>
            <TextInput value={newCode} onChange={(e) => setNewCode(e.target.value)} placeholder="ENTRADA_COMPRA" required />
          </FormField>
          <FormField label="Nombre" required>
            <TextInput value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Entrada por compra" required />
          </FormField>
          <FormField label="Dirección" required>
            <select value={newDirection} onChange={(e) => setNewDirection(e.target.value)} className="h-10 w-40 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              {DIRECTIONS.map((d) => (
                <option key={d.value} value={d.value}>{d.label}</option>
              ))}
            </select>
          </FormField>
          <FormField label="Global (todas las empresas)">
            <select value={newGlobal ? "yes" : "no"} onChange={(e) => setNewGlobal(e.target.value === "yes")} className="h-10 w-32 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="no">No</option>
              <option value="yes">Sí</option>
            </select>
          </FormField>
          <AsyncButton type="submit" variant="primary" onClick={createType}>Crear</AsyncButton>
        </form>
      </section>
      </Autorizado>

      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar los tipos de movimiento." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin tipos de movimiento"
        emptyDescription="Aún no hay tipos de movimiento configurados."
      />
    </PageContent>
  );
}
