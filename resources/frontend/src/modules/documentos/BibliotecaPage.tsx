/** Biblioteca documental (Spec 046, FR-046-085).
 *
 * Lista documentos, nunca binarios: esta pantalla no abre un solo archivo
 * (NFR-046-01). El vencimiento que muestra es derivado de la fecha, no un
 * estado guardado.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { AlertTriangle, ShieldAlert, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router";

import { apiFetch } from "@/api/client";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageHeader } from "@/components/PageHeader";
import { Pagination } from "@/components/Pagination";
import { SearchInput } from "@/components/SearchInput";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";

import {
  DOCUMENT_STATUSES, SECURITY_LABEL, STATUS_LABEL, formatSize, truncateName,
  uploadErrorMessage,
  type DocumentSummary, type DocumentTypeInfo, type Paged,
} from "./types";

const columnHelper = createColumnHelper<DocumentSummary>();

export function BibliotecaPage(): React.JSX.Element {
  const { activeCompany } = useCompany();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [expiringBefore, setExpiringBefore] = useState("");
  const [pageIndex, setPageIndex] = useState(0);
  const [pageSize, setPageSize] = useState(25);

  const [newTitle, setNewTitle] = useState("");
  const [newType, setNewType] = useState("");
  const [newNumber, setNewNumber] = useState("");
  const [newExpiration, setNewExpiration] = useState("");

  const params = new URLSearchParams({
    limit: String(pageSize), offset: String(pageIndex * pageSize),
  });
  if (search) params.set("q", search);
  if (typeFilter) params.set("document_type_id", typeFilter);
  if (statusFilter) params.set("status", statusFilter);
  if (expiringBefore) params.set("expiring_before", expiringBefore);

  const query = useQuery({
    queryKey: ["documentos", "biblioteca", params.toString()],
    queryFn: () => apiFetch<Paged<DocumentSummary>>(`/documentos?${params.toString()}`),
    retry: false,
  });

  const types = useQuery({
    queryKey: ["documentos", "tipos"],
    queryFn: () => apiFetch<DocumentTypeInfo[]>("/documentos/tipos"),
    retry: false,
  });

  const selectableTypes = (types.data ?? []).filter(
    (t) => !activeCompany || t.company_id === activeCompany.id);
  const selectedType = selectableTypes.find((t) => t.id === newType);

  const createDocument = async (): Promise<void> => {
    if (!activeCompany || !newType || !newTitle) return;
    try {
      await apiFetch("/documentos", {
        method: "POST",
        body: {
          company_id: activeCompany.id, document_type_id: newType, title: newTitle,
          document_number: newNumber || null,
          expiration_date: newExpiration || null,
        },
      });
      notify({ type: "success", title: "Documento creado",
               description: "Ya puede cargarle una versión." });
      setNewTitle(""); setNewNumber(""); setNewExpiration("");
      void queryClient.invalidateQueries({ queryKey: ["documentos"] });
    } catch (err) {
      notify({ type: "error", title: "No fue posible crear el documento",
               description: uploadErrorMessage(err) });
    }
  };

  const columns = [
    columnHelper.accessor("title", {
      header: "Documento",
      cell: (info) => (
        <Link to={`/documentos/${info.row.original.id}`}
              className="font-medium text-brand-600 hover:underline">
          {truncateName(info.getValue())}
        </Link>
      ),
    }),
    columnHelper.accessor("document_number", {
      header: "Número",
      cell: (info) => info.getValue() ?? "—",
    }),
    columnHelper.display({
      id: "version",
      header: "Versión",
      cell: ({ row }) => {
        const version = row.original.current_version;
        if (!version) return <span className="text-text-500">Sin archivo</span>;
        return (
          <span className="whitespace-nowrap">
            v{version.version_number}
            {version.file ? (
              <span className="ml-2 text-xs text-text-500">
                {formatSize(version.file.size)}
              </span>
            ) : null}
          </span>
        );
      },
    }),
    columnHelper.display({
      id: "security",
      header: "Archivo",
      cell: ({ row }) => {
        const file = row.original.current_version?.file;
        if (!file) return <span className="text-text-500">—</span>;
        const clean = file.security_status === "CLEAN";
        const bad = file.security_status === "INFECTED"
          || file.security_status === "SCAN_FAILED";
        const Icon = clean ? ShieldCheck : ShieldAlert;
        return (
          <span className={`inline-flex items-center gap-1 text-sm ${
            clean ? "text-success-600" : bad ? "text-danger-600" : "text-text-500"}`}>
            <Icon className="h-4 w-4" aria-hidden="true" />
            {SECURITY_LABEL[file.security_status] ?? file.security_status}
          </span>
        );
      },
    }),
    columnHelper.accessor("status", {
      header: "Estado",
      cell: (info) => STATUS_LABEL[info.getValue()] ?? info.getValue(),
    }),
    columnHelper.display({
      id: "expiration",
      header: "Vencimiento",
      cell: ({ row }) => {
        const { expiration_date, is_expired } = row.original;
        if (!expiration_date) return <span className="text-text-500">—</span>;
        return (
          <span className={`inline-flex items-center gap-1 whitespace-nowrap ${
            is_expired ? "text-danger-600" : ""}`}>
            {is_expired ? (
              <AlertTriangle className="h-4 w-4" aria-hidden="true" />
            ) : null}
            {expiration_date}
            {is_expired ? <span className="sr-only"> (vencido)</span> : null}
          </span>
        );
      },
    }),
  ];

  const total = query.data?.total ?? 0;

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Biblioteca documental"
        description="Documentos de la empresa, sus versiones y su estado de verificación."
      />

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <SearchInput value={search} label="Buscar documento"
                     placeholder="Título o número"
                     onChange={(value) => { setSearch(value); setPageIndex(0); }} />
        <FormField label="Tipo documental">
          <select value={typeFilter}
                  onChange={(e) => { setTypeFilter(e.target.value); setPageIndex(0); }}
                  aria-label="Filtrar por tipo documental"
                  className="h-10 w-full cursor-pointer rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 sm:w-56">
            <option value="">Todos</option>
            {selectableTypes.map((t) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
        </FormField>
        <FormField label="Estado">
          <select value={statusFilter}
                  onChange={(e) => { setStatusFilter(e.target.value); setPageIndex(0); }}
                  aria-label="Filtrar por estado del documento"
                  className="h-10 w-full cursor-pointer rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 sm:w-44">
            <option value="">Todos</option>
            {DOCUMENT_STATUSES.map((s) => (
              <option key={s} value={s}>{STATUS_LABEL[s]}</option>
            ))}
          </select>
        </FormField>
        <FormField label="Vence antes de">
          <TextInput type="date" value={expiringBefore} className="sm:w-44"
                     aria-label="Mostrar solo documentos que vencen antes de esta fecha"
                     onChange={(e) => { setExpiringBefore(e.target.value); setPageIndex(0); }} />
        </FormField>
      </div>

      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.error instanceof Error ? query.error.message : null}
        emptyTitle="No hay documentos"
        emptyDescription="Cree un documento y cárguele su primera versión."
        getRowId={(row) => row.id}
        footer={total > 10 ? (
          <Pagination pageIndex={pageIndex} pageSize={pageSize} total={total}
                      onPageChange={setPageIndex}
                      onPageSizeChange={(size) => { setPageSize(size); setPageIndex(0); }} />
        ) : undefined}
      />

      <section className="mt-6 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-3 text-base font-semibold text-text-900">Nuevo documento</h2>
        <p className="mb-3 text-sm text-text-500">
          El documento se crea primero y el archivo se carga después, como una versión.
        </p>
        <div className="flex flex-wrap items-end gap-3">
          <FormField label="Título" required>
            <TextInput value={newTitle} onChange={(e) => setNewTitle(e.target.value)}
                       aria-label="Título del documento" className="sm:w-64" />
          </FormField>
          <FormField label="Tipo documental" required>
            <select value={newType} onChange={(e) => setNewType(e.target.value)}
                    aria-label="Tipo documental del nuevo documento"
                    className="h-10 w-full cursor-pointer rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 sm:w-56">
              <option value="">Seleccione…</option>
              {selectableTypes.map((t) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          </FormField>
          <FormField label="Número">
            <TextInput value={newNumber} onChange={(e) => setNewNumber(e.target.value)}
                       aria-label="Número del documento" className="sm:w-40" />
          </FormField>
          <FormField label="Vencimiento"
                     required={Boolean(selectedType?.requires_expiration)}>
            <TextInput type="date" value={newExpiration} className="sm:w-44"
                       aria-label="Fecha de vencimiento"
                       onChange={(e) => setNewExpiration(e.target.value)} />
          </FormField>
          <AsyncButton
            variant="primary" onClick={createDocument}
            disabled={!activeCompany || !newTitle || !newType
              || (Boolean(selectedType?.requires_expiration) && !newExpiration)}
          >
            Crear documento
          </AsyncButton>
        </div>
      </section>
    </PageContent>
  );
}
