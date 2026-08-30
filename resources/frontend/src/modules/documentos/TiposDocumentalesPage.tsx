/** Tipos documentales (Spec 046, FR-046-088).
 *
 * Es aquí donde se decide qué se admite: formatos, tamaño, si se exige
 * vencimiento y si el archivo se analiza. Nada de eso está escrito en el
 * código (P8), y una lista de formatos vacía significa **ninguno**, nunca
 * «todos».
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { Check, Minus } from "lucide-react";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";

import { formatSize, uploadErrorMessage, type DocumentTypeInfo } from "./types";

interface CategoryInfo {
  id: string;
  company_id: string;
  code: string;
  name: string;
}

const columnHelper = createColumnHelper<DocumentTypeInfo>();

const yesNo = (value: boolean): React.JSX.Element =>
  value
    ? <Check className="h-4 w-4 text-success-600" aria-label="Sí" />
    : <Minus className="h-4 w-4 text-text-500" aria-label="No" />;

export function TiposDocumentalesPage(): React.JSX.Element {
  const { activeCompany } = useCompany();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [mimes, setMimes] = useState("application/pdf");
  const [maxMb, setMaxMb] = useState("10");
  const [requiresExpiration, setRequiresExpiration] = useState(false);
  const [scanRequired, setScanRequired] = useState(true);

  const types = useQuery({
    queryKey: ["documentos", "tipos"],
    queryFn: () => apiFetch<DocumentTypeInfo[]>("/documentos/tipos"),
    retry: false,
  });

  const categories = useQuery({
    queryKey: ["documentos", "categorias"],
    queryFn: () => apiFetch<CategoryInfo[]>("/documentos/categorias"),
    retry: false,
  });

  const rows = (types.data ?? []).filter(
    (t) => !activeCompany || t.company_id === activeCompany.id);

  const createType = async (): Promise<void> => {
    if (!activeCompany || !code || !name) return;
    const allowed = mimes.split(",").map((m) => m.trim()).filter(Boolean);
    try {
      await apiFetch("/documentos/tipos", {
        method: "POST",
        body: {
          company_id: activeCompany.id,
          category_id: categoryId || null,
          code, name,
          allowed_mime_types: allowed,
          max_size_bytes: maxMb ? Math.round(Number(maxMb) * 1024 * 1024) : null,
          requires_expiration: requiresExpiration,
          scan_required: scanRequired,
        },
      });
      notify({ type: "success", title: "Tipo documental creado", description: name });
      setCode(""); setName("");
      void queryClient.invalidateQueries({ queryKey: ["documentos", "tipos"] });
    } catch (err) {
      notify({ type: "error", title: "No fue posible crear el tipo",
               description: uploadErrorMessage(err) });
    }
  };

  const columns = [
    columnHelper.accessor("code", { header: "Código" }),
    columnHelper.accessor("name", { header: "Nombre" }),
    columnHelper.display({
      id: "formats",
      header: "Formatos admitidos",
      cell: ({ row }) => {
        const allowed = row.original.allowed_mime_types;
        return allowed.length > 0
          ? <span className="text-sm">{allowed.join(", ")}</span>
          : <span className="text-sm text-danger-600">Ninguno declarado</span>;
      },
    }),
    columnHelper.accessor("max_size_bytes", {
      header: "Tamaño máximo",
      cell: (info) => {
        const value = info.getValue();
        return value ? formatSize(value) : "Límite global";
      },
    }),
    columnHelper.accessor("versioning_policy", { header: "Versionado" }),
    columnHelper.accessor("requires_expiration", {
      header: "Exige vencimiento",
      cell: (info) => yesNo(info.getValue()),
    }),
    columnHelper.accessor("scan_required", {
      header: "Se analiza",
      cell: (info) => yesNo(info.getValue()),
    }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Tipos documentales"
        description="Qué formatos se admiten, con qué tamaño y bajo qué controles."
      />

      <DataTable
        columns={columns}
        data={rows}
        loading={types.isLoading}
        error={types.error instanceof Error ? types.error.message : null}
        emptyTitle="No hay tipos documentales"
        emptyDescription="Defina al menos uno antes de cargar archivos."
        getRowId={(row) => row.id}
      />

      <section className="mt-6 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-3 text-base font-semibold text-text-900">Nuevo tipo documental</h2>
        <div className="flex flex-wrap items-end gap-3">
          <FormField label="Código" required>
            <TextInput value={code} onChange={(e) => setCode(e.target.value)}
                       aria-label="Código del tipo documental" className="sm:w-32" />
          </FormField>
          <FormField label="Nombre" required>
            <TextInput value={name} onChange={(e) => setName(e.target.value)}
                       aria-label="Nombre del tipo documental" className="sm:w-56" />
          </FormField>
          <FormField label="Categoría">
            <select value={categoryId} onChange={(e) => setCategoryId(e.target.value)}
                    aria-label="Categoría del tipo documental"
                    className="h-10 w-full cursor-pointer rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 sm:w-48">
              <option value="">Sin categoría</option>
              {(categories.data ?? []).map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </FormField>
          <FormField label="Formatos admitidos" required
                     help="Separados por coma. Si se deja vacío, no se admite ningún archivo.">
            <TextInput value={mimes} onChange={(e) => setMimes(e.target.value)}
                       aria-label="Formatos MIME admitidos, separados por coma"
                       className="sm:w-72" />
          </FormField>
          <FormField label="Tamaño máximo (MB)">
            <TextInput type="number" min={1} value={maxMb} className="sm:w-32"
                       aria-label="Tamaño máximo en megabytes"
                       onChange={(e) => setMaxMb(e.target.value)} />
          </FormField>
          <label className="flex h-10 cursor-pointer items-center gap-2 text-sm text-text-700">
            <input type="checkbox" checked={requiresExpiration}
                   onChange={(e) => setRequiresExpiration(e.target.checked)}
                   className="h-4 w-4 cursor-pointer" />
            Exige vencimiento
          </label>
          <label className="flex h-10 cursor-pointer items-center gap-2 text-sm text-text-700">
            <input type="checkbox" checked={scanRequired}
                   onChange={(e) => setScanRequired(e.target.checked)}
                   className="h-4 w-4 cursor-pointer" />
            Analizar el archivo
          </label>
          <AsyncButton variant="primary" onClick={createType}
                       disabled={!activeCompany || !code || !name}>
            Crear tipo
          </AsyncButton>
        </div>
        {!scanRequired ? (
          <p className="mt-3 rounded-md border border-warning-100 bg-warning-100/30 px-3 py-2 text-sm text-text-700"
             role="status">
            Sin análisis, los archivos de este tipo quedarán marcados como
            «Sin analizar»: el sistema no afirmará que están limpios.
          </p>
        ) : null}
      </section>
    </PageContent>
  );
}
