/** Presentaciones de un producto (Spec 011, FR-011-091/092).
 *
 * Página completa con URL propia, no modal (P18). La equivalencia se configura
 * completando una oración —«Una CAJA equivale a ___ UND»— en lugar de rellenar
 * un factor abstracto: una conversión mal entendida se configura mal.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { History, Power, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { useParams } from "react-router";

import { apiFetch } from "@/api/client";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { Autorizado } from "@/components/Autorizado";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";
import { fechaDeNegocioDeInstante } from "@/lib/fecha-de-negocio";

import {
  can, formatDecimal,
  type ConversionPreview, type Presentation, type PresentationVersion,
} from "../unidades/types";

function blockReason(err: unknown): string {
  const details = (err as { details?: { reason?: string } })?.details;
  return details?.reason ?? (err instanceof Error ? err.message : "Operación rechazada");
}

export function PresentacionesPage(): React.JSX.Element {
  const { productId = "" } = useParams();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [factor, setFactor] = useState("");           // vacío al inicio
  const [exact, setExact] = useState(true);
  const [buyable, setBuyable] = useState(true);
  const [sellable, setSellable] = useState(true);
  const [storable, setStorable] = useState(false);
  const [dispatchable, setDispatchable] = useState(true);
  const [historyFor, setHistoryFor] = useState<string | null>(null);
  const [newFactor, setNewFactor] = useState("");
  const [preview, setPreview] = useState<ConversionPreview | null>(null);

  const presentations = useQuery({
    queryKey: ["maestros", "presentaciones", productId],
    queryFn: () => apiFetch<Presentation[]>(
      `/maestros/productos/${productId}/presentaciones`),
    enabled: Boolean(productId),
    retry: false,
  });

  const versions = useQuery({
    queryKey: ["maestros", "versiones", historyFor],
    queryFn: () => apiFetch<PresentationVersion[]>(
      `/maestros/presentaciones/${historyFor}/versiones`),
    enabled: Boolean(historyFor),
    retry: false,
  });

  const baseUnit = presentations.data?.[0]?.base_unit ?? null;
  const baseCode = baseUnit?.code ?? "unidad base";

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["maestros"] });
  };

  /** Vista previa **informativa**: el backend recalcula al guardar. */
  const runPreview = async (value: string): Promise<void> => {
    setFactor(value);
    setPreview(null);
    if (!value || Number.isNaN(Number(value)) || Number(value) <= 0) return;
    try {
      // Se previsualiza con 10 unidades de presentación, que es como el
      // usuario piensa la equivalencia.
      const explanation = `10 ${code || "presentaciones"} = ${formatDecimal(
        (Number(value) * 10).toFixed(6))} ${baseCode}`;
      setPreview({
        quantity: "10", presentation: null, factor_applied: value,
        version_id: null, base_quantity: (Number(value) * 10).toFixed(6),
        base_uom: baseUnit, exact: true, explanation,
      });
    } catch {
      setPreview(null);
    }
  };

  const createPresentation = async (): Promise<void> => {
    if (!code.trim() || !name.trim() || !factor.trim()) return;
    try {
      await apiFetch(`/maestros/productos/${productId}/presentaciones`, {
        method: "POST",
        body: {
          code, name, factor_to_base: factor, exact_in_base: exact,
          buyable, sellable, storable, dispatchable,
        },
      });
      notify({ type: "success", title: "Presentación creada", description: `${code} · ${name}` });
      setCode(""); setName(""); setFactor(""); setPreview(null);
      refresh();
    } catch (err) {
      notify({ type: "error", title: "No fue posible crear la presentación",
               description: blockReason(err) });
    }
  };

  const createVersion = async (): Promise<void> => {
    if (!historyFor || !newFactor.trim()) return;
    try {
      await apiFetch(`/maestros/presentaciones/${historyFor}/versiones`, {
        method: "POST", body: { factor_to_base: newFactor },
      });
      notify({ type: "success", title: "Equivalencia nueva registrada",
               description: "La anterior se conserva: los documentos emitidos no cambian." });
      setNewFactor("");
      refresh();
    } catch (err) {
      notify({ type: "error", title: "No fue posible registrar la equivalencia",
               description: blockReason(err) });
    }
  };

  const act = async (item: Presentation,
                     action: "activate" | "deactivate" | "delete"): Promise<void> => {
    try {
      await apiFetch(`/maestros/presentaciones/${item.id}${action === "delete" ? "" : `/${action}`}`,
        { method: action === "delete" ? "DELETE" : "POST" });
      notify({ type: "success", title: "Presentación actualizada" });
      refresh();
    } catch (err) {
      notify({ type: "error", title: "Operación rechazada", description: blockReason(err) });
    }
  };

  const columns = useMemo<ColumnDef<Presentation, unknown>[]>(() => [
    { accessorKey: "code", header: "Código" },
    { accessorKey: "name", header: "Nombre" },
    {
      id: "equivalence", header: "Equivale a",
      cell: ({ row }) => (
        <span className="text-text-700">
          {row.original.current_factor
            ? `${formatDecimal(row.original.current_factor)} ${row.original.base_unit?.code ?? ""}`
            : "Sin equivalencia"}
        </span>
      ),
    },
    {
      id: "uses", header: "Usos",
      cell: ({ row }) => {
        const uses = [
          row.original.buyable && "Compra",
          row.original.sellable && "Venta",
          row.original.storable && "Almacén",
          row.original.dispatchable && "Despacho",
        ].filter(Boolean);
        return uses.join(", ") || "—";
      },
    },
    { accessorKey: "status", header: "Estado" },
    {
      id: "actions", header: "Acciones",
      cell: ({ row }) => {
        const item = row.original;
        const toggle = can(item, "deactivate") ? "deactivate" : "activate";
        return (
          <div className="flex justify-end gap-1">
            <AsyncButton
              variant="ghost" size="sm"
              aria-label={`Ver el historial de equivalencias de ${item.code}`}
              title="Historial de equivalencias"
              onClick={async () => setHistoryFor(item.id)}
            >
              <History className="h-4 w-4" aria-hidden="true" />
            </AsyncButton>
            <AsyncButton
              variant="ghost" size="sm"
              aria-label={`${toggle === "deactivate" ? "Desactivar" : "Activar"} ${item.code}`}
              title={toggle === "deactivate" ? "Desactivar" : "Activar"}
              onClick={() => act(item, toggle)}
            >
              <Power className="h-4 w-4" aria-hidden="true" />
            </AsyncButton>
            <AsyncButton
              variant="ghost" size="sm" disabled={!item.can_delete}
              aria-label={item.can_delete
                ? `Eliminar ${item.code}`
                : `${item.code} no puede eliminarse: fue utilizada`}
              title={item.can_delete ? "Eliminar" : "Fue utilizada: desactívela en su lugar"}
              onClick={() => act(item, "delete")}
            >
              <Trash2 className="h-4 w-4" aria-hidden="true" />
            </AsyncButton>
          </div>
        );
      },
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], []);

  const versionColumns = useMemo<ColumnDef<PresentationVersion, unknown>[]>(() => [
    {
      id: "from", header: "Vigente desde",
      cell: ({ row }) => fechaDeNegocioDeInstante(row.original.valid_from),
    },
    {
      id: "to", header: "Hasta",
      cell: ({ row }) => fechaDeNegocioDeInstante(row.original.valid_to),
    },
    {
      id: "factor", header: "Equivale a",
      cell: ({ row }) => `${formatDecimal(row.original.factor_to_base)} ${baseCode}`,
    },
    {
      id: "state", header: "Estado",
      cell: ({ row }) => (row.original.is_open ? "Vigente" : "Cerrada 🔒"),
    },
     
  ], [baseCode]);

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Presentaciones del producto"
        description={baseUnit
          ? `Unidad base: ${baseUnit.code} (${baseUnit.symbol})`
          : "Formas de comprar o vender este producto."}
        crumbs={[{ label: "Maestros" }, { label: "Productos", to: "/maestros/productos" },
                 { label: "Presentaciones" }]}
      />

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-3 text-base font-semibold text-text-900">Nueva presentación</h2>
        <Autorizado operacion={["POST", `/maestros/productos/${productId || "_"}/presentaciones`]}>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Código" required>
            <TextInput value={code} onChange={(e) => setCode(e.target.value)}
                       placeholder="Ej. CAJA" required />
          </FormField>
          <FormField label="Nombre" required>
            <TextInput value={name} onChange={(e) => setName(e.target.value)} required />
          </FormField>
          <FormField
            label={`Una ${code || "presentación"} equivale a (${baseCode})`}
            required
            help="Debe ser mayor que cero. Admite decimales."
          >
            <TextInput
              type="number" step="0.000001" min="0" value={factor}
              onChange={(e) => void runPreview(e.target.value)} required
            />
          </FormField>
          <AsyncButton type="submit" variant="primary" onClick={createPresentation}>
            Guardar
          </AsyncButton>
        </form>

        {preview ? (
          <p className="mt-3 rounded-md border border-border-default bg-surface-50 px-3 py-2 text-sm text-text-700"
             role="status">
            Vista previa: <strong>{preview.explanation}</strong>
            <span className="ml-2 text-text-500">
              (informativa: el servidor recalcula al guardar)
            </span>
          </p>
        ) : null}

        <fieldset className="mt-4 border-t border-border-default pt-3">
          <legend className="text-sm font-medium text-text-700">Se puede usar en</legend>
          <div className="flex flex-wrap gap-4 pt-1">
            {([["Compras", buyable, setBuyable], ["Ventas", sellable, setSellable],
               ["Almacenamiento", storable, setStorable],
               ["Despacho", dispatchable, setDispatchable]] as const).map(([label, value, set]) => (
              <label key={label} className="flex cursor-pointer items-center gap-2 text-sm text-text-700">
                <input type="checkbox" checked={value} className="h-4 w-4 cursor-pointer"
                       onChange={(e) => set(e.target.checked)} />
                {label}
              </label>
            ))}
            <label className="flex cursor-pointer items-center gap-2 text-sm text-text-700">
              <input type="checkbox" checked={!exact} className="h-4 w-4 cursor-pointer"
                     onChange={(e) => setExact(!e.target.checked)} />
              La equivalencia produce fracciones en la unidad base
            </label>
          </div>
        </fieldset>
        </Autorizado>
      </section>

      <section className="rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-3 text-base font-semibold text-text-900">Presentaciones</h2>
        <DataTable
          columns={columns}
          data={presentations.data ?? []}
          loading={presentations.isLoading}
          error={presentations.isError ? "No fue posible cargar las presentaciones." : null}
          emptyTitle="Sin presentaciones"
          emptyDescription={`Este producto se maneja en ${baseCode}. No necesita presentaciones.`}
          getRowId={(row) => row.id}
        />
        <p className="mt-3 text-sm text-text-500">
          Las presentaciones son formas de comprar o vender este producto, no productos distintos.
        </p>
      </section>

      {historyFor ? (
        <section className="mt-4 rounded-lg border border-border-default bg-surface-0 p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-semibold text-text-900">Historial de equivalencias</h2>
            <button type="button" onClick={() => setHistoryFor(null)}
                    className="cursor-pointer text-sm text-text-600 hover:text-text-900">
              Cerrar
            </button>
          </div>
          <DataTable
            columns={versionColumns}
            data={versions.data ?? []}
            loading={versions.isLoading}
            error={versions.isError ? "No fue posible cargar el historial." : null}
            emptyTitle="Sin equivalencias registradas"
            getRowId={(row) => row.id}
          />
          <p className="mt-3 text-sm text-text-500">
            Las equivalencias cerradas no se editan ni se borran: los documentos emitidos con
            ellas siguen significando lo mismo. Para corregir, registre una nueva.
          </p>
          {puede("POST", `/maestros/presentaciones/${historyFor || "_"}/versiones`) ? (
          <form className="mt-3 flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
            <FormField label={`Nueva equivalencia (${baseCode})`} required>
              <TextInput type="number" step="0.000001" min="0" value={newFactor}
                         onChange={(e) => setNewFactor(e.target.value)} required />
            </FormField>
            <AsyncButton type="submit" variant="primary" onClick={createVersion}>
              Registrar equivalencia
            </AsyncButton>
          </form>
          ) : null}
        </section>
      ) : null}
    </PageContent>
  );
}
