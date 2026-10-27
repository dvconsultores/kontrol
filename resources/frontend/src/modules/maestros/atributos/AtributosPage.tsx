/** Atributos de catálogo — definición de atributos personalizados (FR-002-040). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { CatalogAttribute } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Autorizado } from "@/components/Autorizado";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

const columnHelper = createColumnHelper<CatalogAttribute>();

const DATA_TYPES = ["TEXT", "NUMBER", "DATE", "BOOLEAN", "ENUM"];

export function AtributosPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const [newCode, setNewCode] = useState("");
  const [newName, setNewName] = useState("");
  const [newType, setNewType] = useState("TEXT");
  const [newUnit, setNewUnit] = useState("");
  const [newOptions, setNewOptions] = useState("");

  const query = useQuery({
    queryKey: ["maestros", "atributos"],
    queryFn: () => apiFetch<CatalogAttribute[]>("/maestros/catalogos/atributos"),
    retry: false,
  });

  const refresh = async (): Promise<void> => {
    await queryClient.invalidateQueries({ queryKey: ["maestros", "atributos"] });
  };

  const createAttribute = async (): Promise<void> => {
    try {
      await apiFetch("/maestros/catalogos/atributos", {
        method: "POST",
        body: {
          code: newCode, name: newName, data_type: newType,
          unit: newUnit || null, required: false, multiple: false,
          options: newOptions ? newOptions.split(",").map((o) => o.trim()).filter(Boolean) : [],
          searchable: false,
        },
      });
      notify({ type: "success", title: "Atributo creado", description: newName });
      setNewCode(""); setNewName(""); setNewType("TEXT"); setNewUnit(""); setNewOptions("");
      void refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear el atributo";
      notify({ type: "error", title: "No fue posible crear el atributo", description: message });
    }
  };

  const columns = [
    columnHelper.accessor("code", { header: "Código" }),
    columnHelper.accessor("name", { header: "Nombre" }),
    columnHelper.accessor("data_type", { header: "Tipo" }),
    columnHelper.accessor("searchable", { header: "Buscable" }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Atributos de catálogo"
        description="Defina atributos personalizados para productos, servicios y terceros."
        crumbs={[{ label: "Maestros" }, { label: "Atributos" }]}
      />
      <Autorizado operacion={["POST", "/maestros/catalogos/atributos"]}>
        <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-2 text-base font-semibold text-text-900">Nuevo atributo</h2>
          <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
            <FormField label="Código" required>
              <TextInput value={newCode} onChange={(e) => setNewCode(e.target.value)} placeholder="COLOR" required />
            </FormField>
            <FormField label="Nombre" required>
              <TextInput value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Color" required />
            </FormField>
            <FormField label="Tipo" required>
              <select value={newType} onChange={(e) => setNewType(e.target.value)} className="h-10 w-36 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                {DATA_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </FormField>
            <FormField label="Unidad">
              <TextInput value={newUnit} onChange={(e) => setNewUnit(e.target.value)} placeholder="cm, kg…" />
            </FormField>
            <FormField label="Opciones (ENUM, separadas por coma)">
              <TextInput value={newOptions} onChange={(e) => setNewOptions(e.target.value)} placeholder="Rojo, Verde, Azul" />
            </FormField>
            <AsyncButton type="submit" variant="primary" onClick={createAttribute}>Crear</AsyncButton>
          </form>
        </section>
      </Autorizado>

      <DataTable
        columns={columns}
        data={query.data ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar los atributos." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin atributos"
        emptyDescription="Aún no hay atributos definidos."
      />
    </PageContent>
  );
}
