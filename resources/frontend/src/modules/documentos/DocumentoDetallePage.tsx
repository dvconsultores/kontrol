/** Detalle de un documento y su historial de versiones (Spec 046, FR-046-086).
 *
 * Las versiones no se sobrescriben ni se borran: la lista es acumulativa y
 * cada línea se puede descargar tal como se guardó. Archivar conserva el
 * binario; solo cambia el estado del documento.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Archive, Download, FileText, Lock, ShieldAlert, ShieldCheck, Upload,
} from "lucide-react";
import { useId, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";

import { apiFetch } from "@/api/client";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { AsyncButton } from "@/components/AsyncButton";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { ErrorState } from "@/components/ErrorState";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";

import {
  SECURITY_LABEL, STATUS_LABEL, can, formatSize, truncateName, uploadErrorMessage,
  type DocumentSummary, type DocumentTypeInfo, type DocumentVersionInfo,
} from "./types";

export function DocumentoDetallePage(): React.JSX.Element {
  const { documentId = "" } = useParams();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();
  const navigate = useNavigate();

  const fileInputId = useId();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [reason, setReason] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [confirmArchive, setConfirmArchive] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const document_ = useQuery({
    queryKey: ["documentos", "detalle", documentId],
    queryFn: () => apiFetch<DocumentSummary>(`/documentos/${documentId}`),
    enabled: Boolean(documentId),
    retry: false,
  });

  const versions = useQuery({
    queryKey: ["documentos", "versiones", documentId],
    queryFn: () => apiFetch<DocumentVersionInfo[]>(`/documentos/${documentId}/versiones`),
    enabled: Boolean(documentId),
    retry: false,
  });

  const types = useQuery({
    queryKey: ["documentos", "tipos"],
    queryFn: () => apiFetch<DocumentTypeInfo[]>("/documentos/tipos"),
    retry: false,
  });

  const doc = document_.data;
  const docType = (types.data ?? []).find((t) => t.id === doc?.document_type_id);
  // Ya hay una versión: la siguiente carga es un reemplazo y merece motivo.
  const isReplacement = (versions.data ?? []).length > 0;

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["documentos"] });
  };

  const uploadVersion = async (): Promise<void> => {
    if (!file) return;
    setUploadError(null);
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      if (reason) form.append("replacement_reason", reason);
      await apiFetch(`/documentos/${documentId}/versiones`, {
        method: "POST", body: form,
        // Un doble clic no crea dos versiones (§101).
        idempotencyKey: crypto.randomUUID(),
      });
      notify({ type: "success", title: "Versión cargada", description: file.name });
      setFile(null);
      setReason("");
      if (fileInputRef.current) fileInputRef.current.value = "";
      refresh();
    } catch (err) {
      const message = uploadErrorMessage(err);
      setUploadError(message);
      notify({ type: "error", title: "No fue posible cargar la versión",
               description: message });
    } finally {
      setUploading(false);
    }
  };

  const downloadVersion = async (version: DocumentVersionInfo): Promise<void> => {
    try {
      const blob = await apiFetch<Blob>(
        `/documentos/${documentId}/versiones/${version.id}/descargar`,
        { responseType: "blob" });
      const url = URL.createObjectURL(blob);
      const anchor = window.document.createElement("a");
      anchor.href = url;
      anchor.download = version.file?.original_name ?? `v${version.version_number}`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      notify({ type: "error", title: "No fue posible descargar",
               description: uploadErrorMessage(err) });
    }
  };

  const archive = async (): Promise<void> => {
    try {
      await apiFetch(`/documentos/${documentId}/archive`, { method: "POST" });
      notify({ type: "success", title: "Documento archivado",
               description: "Los archivos se conservan." });
      setConfirmArchive(false);
      refresh();
    } catch (err) {
      notify({ type: "error", title: "No fue posible archivar",
               description: uploadErrorMessage(err) });
    }
  };

  const remove = async (): Promise<void> => {
    try {
      await apiFetch(`/documentos/${documentId}`, { method: "DELETE" });
      notify({ type: "success", title: "Documento eliminado" });
      setConfirmDelete(false);
      refresh();
      void navigate("/documentos");
    } catch (err) {
      notify({ type: "error", title: "No fue posible eliminar",
               description: uploadErrorMessage(err) });
    }
  };

  if (document_.isLoading) return <LoadingState />;
  if (document_.error || !doc) {
    return (
      <ErrorState
        message={document_.error instanceof Error
          ? document_.error.message
          : "No fue posible cargar el documento"}
      />
    );
  }

  const securityBadge = (status: string): React.JSX.Element => {
    const clean = status === "CLEAN";
    const bad = status === "INFECTED" || status === "SCAN_FAILED";
    const Icon = clean ? ShieldCheck : ShieldAlert;
    return (
      <span className={`inline-flex items-center gap-1 text-sm ${
        clean ? "text-success-600" : bad ? "text-danger-600" : "text-text-500"}`}>
        <Icon className="h-4 w-4" aria-hidden="true" />
        {SECURITY_LABEL[status] ?? status}
      </span>
    );
  };

  return (
    <PageContent maxWidth="full">
      <PageHeader
        crumbs={[{ label: "Documentos", to: "/documentos" }, { label: doc.title }]}
        title={doc.title}
        description={docType?.name}
        status={
          <span className="rounded-full bg-surface-100 px-3 py-1 text-xs text-text-700">
            {STATUS_LABEL[doc.status] ?? doc.status}
          </span>
        }
        actions={
          <>
            {can(doc, "archive") && puede("POST", "/documentos/_/archive") ? (
              <AsyncButton variant="secondary"
                           onClick={async () => { setConfirmArchive(true); }}>
                <Archive className="mr-1 h-4 w-4" aria-hidden="true" />
                Archivar
              </AsyncButton>
            ) : null}
            {can(doc, "delete") && puede("DELETE", "/documentos/_") ? (
              <AsyncButton variant="danger"
                           onClick={async () => { setConfirmDelete(true); }}>
                Eliminar
              </AsyncButton>
            ) : null}
          </>
        }
      />

      <dl className="mb-6 grid grid-cols-1 gap-4 rounded-lg border border-border-default bg-surface-0 p-4 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <dt className="text-xs text-text-500">Número</dt>
          <dd className="text-sm text-text-900">{doc.document_number ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-xs text-text-500">Emisor</dt>
          <dd className="text-sm text-text-900">{doc.issuer ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-xs text-text-500">Emitido</dt>
          <dd className="text-sm text-text-900">{doc.issued_at ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-xs text-text-500">Vencimiento</dt>
          <dd className={`text-sm ${doc.is_expired ? "text-danger-600" : "text-text-900"}`}>
            {doc.expiration_date ?? "—"}
            {doc.is_expired ? " (vencido)" : ""}
          </dd>
        </div>
        {doc.external_url ? (
          <div className="sm:col-span-2 lg:col-span-4">
            <dt className="text-xs text-text-500">Referencia externa</dt>
            <dd className="truncate text-sm text-text-900">{doc.external_url}</dd>
          </div>
        ) : null}
      </dl>

      <section className="mb-6 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-3 text-base font-semibold text-text-900">Versiones</h2>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[40rem] text-sm">
            <caption className="sr-only">
              Historial de versiones del documento, de la más reciente a la más antigua
            </caption>
            <thead>
              <tr className="border-b border-border-default text-left text-text-500">
                <th scope="col" className="py-2 pr-3 font-medium">Versión</th>
                <th scope="col" className="py-2 pr-3 font-medium">Archivo</th>
                <th scope="col" className="py-2 pr-3 font-medium">Tamaño</th>
                <th scope="col" className="py-2 pr-3 font-medium">Verificación</th>
                <th scope="col" className="py-2 pr-3 font-medium">Motivo</th>
                <th scope="col" className="py-2 pr-3 font-medium">Fecha</th>
                <th scope="col" className="py-2 font-medium">
                  <span className="sr-only">Acciones</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {(versions.data ?? []).map((version) => (
                <tr key={version.id} className="border-b border-border-default last:border-0">
                  <td className="py-2 pr-3 whitespace-nowrap">
                    v{version.version_number}
                    {version.id === doc.current_version?.id ? (
                      <span className="ml-2 rounded bg-brand-600/10 px-1.5 py-0.5 text-xs text-brand-600">
                        vigente
                      </span>
                    ) : null}
                  </td>
                  <td className="py-2 pr-3" title={version.file?.original_name}>
                    {version.file ? truncateName(version.file.original_name, 32) : "—"}
                  </td>
                  <td className="py-2 pr-3 whitespace-nowrap">
                    {version.file ? formatSize(version.file.size) : "—"}
                  </td>
                  <td className="py-2 pr-3">
                    {version.file ? securityBadge(version.file.security_status) : "—"}
                  </td>
                  <td className="py-2 pr-3">{version.replacement_reason ?? "—"}</td>
                  <td className="py-2 pr-3 whitespace-nowrap">
                    {version.created_at ? version.created_at.slice(0, 10) : "—"}
                  </td>
                  <td className="py-2">
                    {can(doc, "download") && version.file ? (
                      <AsyncButton
                        variant="ghost" size="sm"
                        aria-label={`Descargar la versión ${version.version_number}`}
                        onClick={() => downloadVersion(version)}
                      >
                        <Download className="h-4 w-4" aria-hidden="true" />
                      </AsyncButton>
                    ) : null}
                  </td>
                </tr>
              ))}
              {versions.isSuccess && (versions.data ?? []).length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-4 text-text-500">
                    Este documento todavía no tiene archivos.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>

        {can(doc, "upload") && puede("POST", "/documentos/_/versiones") ? (
          <div className="mt-4 border-t border-border-default pt-4">
            <h3 className="mb-2 text-sm font-semibold text-text-900">
              {isReplacement ? "Cargar una versión nueva" : "Cargar el archivo"}
            </h3>
            <div className="flex flex-wrap items-end gap-3">
              <div className="flex flex-col gap-1.5">
                <label htmlFor={fileInputId} className="text-sm font-medium text-text-700">
                  Archivo <span aria-hidden="true" className="text-danger-600">*</span>
                  <span className="sr-only"> (obligatorio)</span>
                </label>
                <input
                  id={fileInputId} ref={fileInputRef} type="file"
                  onChange={(e) => { setFile(e.target.files?.[0] ?? null); setUploadError(null); }}
                  className="block w-full cursor-pointer text-sm text-text-700 file:mr-3 file:cursor-pointer file:rounded-md file:border file:border-border-default file:bg-surface-50 file:px-3 file:py-1.5 file:text-sm"
                />
              </div>
              {isReplacement ? (
                <FormField label="Motivo del reemplazo"
                           help="Queda registrado junto a la versión.">
                  <TextInput value={reason} onChange={(e) => setReason(e.target.value)}
                             aria-label="Motivo del reemplazo" className="sm:w-72" />
                </FormField>
              ) : null}
              <AsyncButton variant="primary" onClick={uploadVersion}
                           disabled={!file || uploading}>
                <Upload className="mr-1 h-4 w-4" aria-hidden="true" />
                Cargar
              </AsyncButton>
            </div>
            {docType ? (
              <p className="mt-2 text-xs text-text-500">
                Admite: {docType.allowed_mime_types.join(", ") || "ningún formato declarado"}
                {docType.max_size_bytes
                  ? ` · Máximo ${formatSize(docType.max_size_bytes)}` : ""}
                {docType.scan_required ? " · Se analiza antes de quedar disponible" : ""}
              </p>
            ) : null}
            {file ? (
              <p className="mt-2 flex items-center gap-2 text-sm text-text-700">
                <FileText className="h-4 w-4" aria-hidden="true" />
                <span title={file.name}>{truncateName(file.name)}</span>
                <span className="text-text-500">{formatSize(file.size)}</span>
              </p>
            ) : null}
            {uploading ? (
              <p className="mt-2 text-sm text-text-700" role="status" aria-live="polite">
                Verificando el archivo…
              </p>
            ) : null}
            {uploadError ? (
              <p className="mt-2 rounded-md border border-danger-100 bg-danger-100/30 px-3 py-2 text-sm text-danger-600"
                 role="alert">
                {uploadError}
              </p>
            ) : null}
          </div>
        ) : null}
      </section>

      <section className="rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-3 text-base font-semibold text-text-900">Vínculos</h2>
        <ul className="divide-y divide-border-default">
          {(doc.links ?? []).map((link) => (
            <li key={link.id} className="flex flex-wrap items-center gap-3 py-2 text-sm">
              <span className="text-text-900">{link.resource_type}</span>
              <span className="font-mono text-xs text-text-500">{link.resource_id}</span>
              <span className="text-xs text-text-500">{link.role}</span>
              {link.is_frozen ? (
                <span className="inline-flex items-center gap-1 text-xs text-text-700">
                  <Lock className="h-3.5 w-3.5" aria-hidden="true" />
                  congelado en la versión usada
                </span>
              ) : null}
            </li>
          ))}
          {(doc.links ?? []).length === 0 ? (
            <li className="py-2 text-sm text-text-500">
              Este documento no está vinculado a ningún recurso.
            </li>
          ) : null}
        </ul>
      </section>

      {doc.delete_blocked_by ? (
        <p className="mt-4 text-sm text-text-500">
          No puede eliminarse porque está en uso.{" "}
          <Link to="/documentos" className="text-brand-600 hover:underline">
            Volver a la biblioteca
          </Link>
        </p>
      ) : null}

      <ConfirmationDialog
        open={confirmArchive}
        title="¿Archivar el documento?"
        description="Deja de ofrecerse para nuevos usos. Los archivos y los vínculos existentes se conservan."
        confirmLabel="Archivar"
        onConfirm={archive}
        onCancel={() => setConfirmArchive(false)}
      />
      <ConfirmationDialog
        open={confirmDelete}
        danger
        title="¿Eliminar el documento?"
        description="Solo es posible porque no tiene versiones ni vínculos. Esta acción no se puede deshacer."
        confirmLabel="Eliminar"
        onConfirm={remove}
        onCancel={() => setConfirmDelete(false)}
      />
    </PageContent>
  );
}
