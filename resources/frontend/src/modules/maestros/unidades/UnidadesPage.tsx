/** Unidades de medida — listado y alta (Spec 011, FR-011-090).
 *
 * La lista incluye el catálogo global de la plataforma, que es de **solo
 * lectura** para la empresa, y las unidades propias. En una instalación nueva
 * está vacía: KONTROL no entrega unidades (FR-011-004, P8).
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Lock, Power, Search, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";

import { apiFetch } from "@/api/client";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Autorizado } from "@/components/Autorizado";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";

import {
  DIMENSION_LABEL, DIMENSIONS, ROUNDING_MODES, can,
  type Paged, type Unit,
} from "./types";

export function UnidadesPage(): React.JSX.Element {
  const { activeCompany } = useCompany();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const [query, setQuery] = useState("");
  const [dimension, setDimension] = useState("");
  const [scope, setScope] = useState("");
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [symbol, setSymbol] = useState("");
  const [newDimension, setNewDimension] = useState<string>("CANTIDAD");
  // Vacío al inicio: no se precarga 0 (FR-011-095).
  const [decimals, setDecimals] = useState("");
  const [rounding, setRounding] = useState("HALF_UP");
  const [submitted, setSubmitted] = useState(false);

  const units = useQuery({
    queryKey: ["maestros", "unidades", query, dimension, scope],
    queryFn: () => apiFetch<Paged<Unit>>(
      "/maestros/unidades?limit=200"
      + (query ? `&q=${encodeURIComponent(query)}` : "")
      + (dimension ? `&dimension=${dimension}` : "")
      + (scope ? `&scope=${scope}` : "")),
    enabled: Boolean(activeCompany),
    retry: false,
  });

  const missing = !code.trim() || !name.trim() || !symbol.trim() || decimals === "";

  const createUnit = async (): Promise<void> => {
    setSubmitted(true);
    if (missing) {
      document.querySelector<HTMLInputElement>("[data-invalid='true'] input")?.focus();
      return;
    }
    try {
      await apiFetch("/maestros/unidades", {
        method: "POST",
        body: {
          code, name, symbol, dimension: newDimension,
          decimals: Number(decimals), rounding_mode: rounding,
        },
      });
      notify({ type: "success", title: "Unidad creada", description: `${code} · ${name}` });
      setCode(""); setName(""); setSymbol(""); setDecimals(""); setSubmitted(false);
      void queryClient.invalidateQueries({ queryKey: ["maestros", "unidades"] });
    } catch (err) {
      notify({
        type: "error", title: "No fue posible crear la unidad",
        description: err instanceof Error ? err.message : "Error inesperado",
      });
    }
  };

  const act = async (unit: Unit, action: "activate" | "deactivate" | "delete"): Promise<void> => {
    const labels = { activate: "Unidad activada", deactivate: "Unidad desactivada",
                     delete: "Unidad eliminada" };
    try {
      await apiFetch(`/maestros/unidades/${unit.id}${action === "delete" ? "" : `/${action}`}`,
        { method: action === "delete" ? "DELETE" : "POST" });
      notify({ type: "success", title: labels[action] });
      void queryClient.invalidateQueries({ queryKey: ["maestros", "unidades"] });
    } catch (err) {
      const details = (err as { details?: { reason?: string } })?.details;
      notify({
        type: "error", title: `No fue posible ${action === "delete" ? "eliminar" : "cambiar"} la unidad`,
        description: details?.reason ?? (err instanceof Error ? err.message : "Error inesperado"),
      });
    }
  };

  const columns = useMemo<ColumnDef<Unit, unknown>[]>(() => [
    { accessorKey: "code", header: "Código" },
    { accessorKey: "name", header: "Nombre" },
    { accessorKey: "symbol", header: "Símbolo" },
    {
      id: "dimension", header: "Dimensión",
      cell: ({ row }) => DIMENSION_LABEL[row.original.dimension] ?? row.original.dimension,
    },
    {
      id: "decimals", header: "Decimales",
      cell: ({ row }) => (
        <span title={row.original.decimals === 0 ? "No admite fracciones" : undefined}>
          {row.original.decimals}
        </span>
      ),
    },
    {
      id: "scope", header: "Ámbito",
      cell: ({ row }) => (
        <span className="inline-flex items-center gap-1 text-text-600">
          {row.original.scope === "GLOBAL" ? (
            <>
              <Lock className="h-3.5 w-3.5" aria-hidden="true" />
              Global
            </>
          ) : "Empresa"}
        </span>
      ),
    },
    { accessorKey: "status", header: "Estado" },
    {
      id: "actions", header: "Acciones",
      cell: ({ row }) => {
        const unit = row.original;
        if (unit.scope === "GLOBAL") {
          return <span className="text-xs text-text-500">Solo lectura</span>;
        }
        const toggle = can(unit, "deactivate") ? "deactivate" : "activate";
        return (
          <div className="flex justify-end gap-1">
            <AsyncButton
              variant="ghost" size="sm"
              aria-label={`${toggle === "deactivate" ? "Desactivar" : "Activar"} ${unit.code}`}
              title={toggle === "deactivate" ? "Desactivar" : "Activar"}
              onClick={() => act(unit, toggle)}
            >
              <Power className="h-4 w-4" aria-hidden="true" />
            </AsyncButton>
            <AsyncButton
              variant="ghost" size="sm" disabled={!unit.can_delete}
              aria-label={unit.can_delete
                ? `Eliminar ${unit.code}`
                : `${unit.code} no puede eliminarse: está en uso`}
              title={unit.can_delete ? "Eliminar" : "En uso: desactívela en su lugar"}
              onClick={() => act(unit, "delete")}
            >
              <Trash2 className="h-4 w-4" aria-hidden="true" />
            </AsyncButton>
          </div>
        );
      },
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], []);

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Unidades de medida"
        description="Las que usa su empresa, más el catálogo estándar de la plataforma."
        crumbs={[{ label: "Maestros" }, { label: "Unidades de medida" }]}
      />

      {!activeCompany ? (
        <div className="rounded-md border border-warning-100 bg-warning-100/40 p-4 text-sm text-warning-600" role="alert">
          No hay una empresa activa. Vaya a <strong>Organización → Empresas</strong> y active la empresa.
        </div>
      ) : (
        <>
          <Autorizado operacion={["POST", "/maestros/unidades"]}>
          <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
            <h2 className="mb-2 text-base font-semibold text-text-900">Nueva unidad</h2>
            <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
              <div data-invalid={submitted && !code.trim()}>
                <FormField label="Código" required
                           error={submitted && !code.trim() ? "Campo obligatorio" : undefined}>
                  <TextInput value={code} onChange={(e) => setCode(e.target.value)} required />
                </FormField>
              </div>
              <div data-invalid={submitted && !name.trim()}>
                <FormField label="Nombre" required
                           error={submitted && !name.trim() ? "Campo obligatorio" : undefined}>
                  <TextInput value={name} onChange={(e) => setName(e.target.value)} required />
                </FormField>
              </div>
              <div data-invalid={submitted && !symbol.trim()}>
                <FormField label="Símbolo" required
                           error={submitted && !symbol.trim() ? "Campo obligatorio" : undefined}>
                  <TextInput value={symbol} onChange={(e) => setSymbol(e.target.value)} required />
                </FormField>
              </div>
              <FormField label="Dimensión" required>
                <select
                  value={newDimension} onChange={(e) => setNewDimension(e.target.value)}
                  aria-label="Dimensión de la unidad"
                  className="h-10 w-full sm:w-44 cursor-pointer rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                >
                  {DIMENSIONS.map((d) => (
                    <option key={d} value={d}>{DIMENSION_LABEL[d]}</option>
                  ))}
                </select>
              </FormField>
              <div data-invalid={submitted && decimals === ""}>
                <FormField
                  label="Decimales" required
                  help="Cuántos decimales admite. 0 = no admite fracciones."
                  error={submitted && decimals === "" ? "Campo obligatorio" : undefined}
                >
                  <TextInput
                    type="number" min={0} max={6} value={decimals}
                    onChange={(e) => setDecimals(e.target.value)} required
                  />
                </FormField>
              </div>
              <FormField label="Redondeo" required>
                <select
                  value={rounding} onChange={(e) => setRounding(e.target.value)}
                  aria-label="Modo de redondeo"
                  className="h-10 w-full sm:w-52 cursor-pointer rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                >
                  {ROUNDING_MODES.map((m) => (
                    <option key={m.value} value={m.value}>{m.label}</option>
                  ))}
                </select>
              </FormField>
              <AsyncButton type="submit" variant="primary" onClick={createUnit}>
                Guardar
              </AsyncButton>
            </form>
          </section>
          </Autorizado>

          <section className="rounded-lg border border-border-default bg-surface-0 p-4">
            <div className="mb-3 flex flex-wrap items-end gap-3">
              <FormField label="Buscar">
                <div className="relative">
                  <Search className="pointer-events-none absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-text-500" aria-hidden="true" />
                  <TextInput
                    value={query} onChange={(e) => setQuery(e.target.value)}
                    aria-label="Buscar unidad por código o nombre"
                    placeholder="Código o nombre" className="pl-8"
                  />
                </div>
              </FormField>
              <FormField label="Dimensión">
                <select
                  value={dimension} onChange={(e) => setDimension(e.target.value)}
                  aria-label="Filtrar por dimensión"
                  className="h-10 w-full sm:w-44 cursor-pointer rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                >
                  <option value="">Todas</option>
                  {DIMENSIONS.map((d) => <option key={d} value={d}>{DIMENSION_LABEL[d]}</option>)}
                </select>
              </FormField>
              <FormField label="Ámbito">
                <select
                  value={scope} onChange={(e) => setScope(e.target.value)}
                  aria-label="Filtrar por ámbito"
                  className="h-10 w-full sm:w-40 cursor-pointer rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                >
                  <option value="">Todos</option>
                  <option value="GLOBAL">Global</option>
                  <option value="COMPANY">Empresa</option>
                </select>
              </FormField>
            </div>
            <DataTable
              columns={columns}
              data={units.data?.items ?? []}
              loading={units.isLoading}
              error={units.isError ? "No fue posible cargar las unidades." : null}
              emptyTitle="Sin unidades registradas"
              emptyDescription="KONTROL no entrega unidades predefinidas: registre las que use su empresa."
              getRowId={(row) => row.id}
            />
          </section>
        </>
      )}
    </PageContent>
  );
}
