/** Componente transversal de adjuntos (Spec 046, FR-046-092).
 *
 * Es lo que cualquier dominio incrusta para tener documentos: recibe
 * `resourceType` y `resourceId`, y resuelve por sí mismo lista, carga,
 * descarga, estado y versión. **Ningún módulo consumidor duplica esta lógica**
 * (P22, R-D0-08-1).
 *
 * La carga es operable **solo con teclado**: arrastrar y soltar es un extra,
 * nunca el único camino (§92).
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, FileText, Link2Off, Lock, ShieldAlert, ShieldCheck, Upload, X } from "lucide-react";
import { useId, useRef, useState } from "react";

import { Autorizado } from "@/components/Autorizado";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { apiFetch } from "@/api/client";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { FormField } from "@/components/FormField";

import {
  SECURITY_LABEL, can, formatSize, truncateName, uploadErrorMessage,
  type DocumentSummary, type DocumentTypeInfo,
} from "./types";

/** Estados visibles de la carga. Ninguno finge un porcentaje (§93). */
type UploadPhase = "idle" | "uploading" | "processing" | "done" | "error";

export interface AdjuntosPanelProps {
  resourceType: string;
  resourceId: string;
  /** Tipo documental por defecto para lo que se cargue desde aquí. */
  documentTypeId?: string;
  title?: string;
}

export function AdjuntosPanel({
  resourceType, resourceId, documentTypeId, title = "Documentos",
}: AdjuntosPanelProps): React.JSX.Element {
  const queryClient = useQueryClient();
  const { activeCompany } = useCompany();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [phase, setPhase] = useState<UploadPhase>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [typeId, setTypeId] = useState(documentTypeId ?? "");

  const documents = useQuery({
    queryKey: ["documentos", "por-recurso", resourceType, resourceId],
    queryFn: () => apiFetch<DocumentSummary[]>(
      `/documentos/por-recurso/${resourceType}/${encodeURIComponent(resourceId)}`),
    enabled: Boolean(resourceType && resourceId),
    retry: false,
  });

  const types = useQuery({
    queryKey: ["documentos", "tipos"],
    queryFn: () => apiFetch<DocumentTypeInfo[]>("/documentos/tipos"),
    retry: false,
  });

  // Solo tipos de la empresa activa: adjuntar a un recurso de otra empresa
  // no es una opción que deba llegar siquiera a ofrecerse (P1).
  const availableTypes = (types.data ?? []).filter(
    (t) => !activeCompany || t.company_id === activeCompany.id);
  const selectedType = availableTypes.find((t) => t.id === typeId);

  const reset = (): void => {
    setFile(null);
    setPhase("idle");
    setErrorMessage(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  const upload = async (): Promise<void> => {
    if (!file || !typeId || !selectedType) return;
    setErrorMessage(null);
    setPhase("uploading");
    try {
      // El documento lógico primero; el archivo después. Son cosas distintas.
      const created = await apiFetch<DocumentSummary>("/documentos", {
        method: "POST",
        body: {
          company_id: activeCompany?.id ?? selectedType.company_id,
          document_type_id: typeId,
          title: file.name,
        },
      });
      setPhase("processing");
      const form = new FormData();
      form.append("file", file);
      await apiFetch(`/documentos/${created.id}/versiones`, { method: "POST", body: form });
      await apiFetch(`/documentos/${created.id}/vinculos`, {
        method: "POST",
        body: { resource_type: resourceType, resource_id: resourceId },
      });
      setPhase("done");
      notify({ type: "success", title: "Documento adjuntado", description: file.name });
      reset();
      void queryClient.invalidateQueries({ queryKey: ["documentos"] });
    } catch (err) {
      setPhase("error");
      const message = uploadErrorMessage(err);
      setErrorMessage(message);
      notify({ type: "error", title: "No fue posible adjuntar el documento",
               description: message });
    }
  };

  const download = async (document_: DocumentSummary): Promise<void> => {
    try {
      // Se pide al endpoint autorizado; no se construye ninguna URL física.
      const blob = await apiFetch<Blob>(`/documentos/${document_.id}/descargar`,
        { responseType: "blob" });
      const url = URL.createObjectURL(blob as Blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = document_.current_version?.file?.original_name ?? document_.title;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      notify({ type: "error", title: "No fue posible descargar",
               description: uploadErrorMessage(err) });
    }
  };

  const detach = async (item: DocumentSummary): Promise<void> => {
    if (!item.link) return;
    try {
      await apiFetch(`/documentos/vinculos/${item.link.id}`, { method: "DELETE" });
      notify({ type: "success", title: "Documento desvinculado", description: item.title });
      void queryClient.invalidateQueries({ queryKey: ["documentos"] });
    } catch (err) {
      notify({ type: "error", title: "No fue posible desvincular",
               description: uploadErrorMessage(err) });
    }
  };

  const securityIcon = (status: string): React.JSX.Element => {
    if (status === "CLEAN") {
      return <ShieldCheck className="h-4 w-4 text-success-600" aria-hidden="true" />;
    }
    if (status === "INFECTED" || status === "SCAN_FAILED") {
      return <ShieldAlert className="h-4 w-4 text-danger-600" aria-hidden="true" />;
    }
    return <ShieldAlert className="h-4 w-4 text-text-500" aria-hidden="true" />;
  };

  return (
    <section className="rounded-lg border border-border-default bg-surface-0 p-4">
      <h2 className="mb-3 text-base font-semibold text-text-900">{title}</h2>

      <ul className="mb-4 divide-y divide-border-default">
        {(documents.data ?? []).map((item) => {
          const info = item.current_version?.file;
          return (
            <li key={item.id} className="flex flex-wrap items-center gap-3 py-2 text-sm">
              <FileText className="h-4 w-4 shrink-0 text-text-500" aria-hidden="true" />
              <span className="min-w-0 flex-1 truncate text-text-900"
                    title={info?.original_name ?? item.title}>
                {truncateName(info?.original_name ?? item.title)}
              </span>
              {item.current_version ? (
                <span className="text-xs text-text-500">v{item.current_version.version_number}</span>
              ) : null}
              {info ? (
                <span className="text-xs text-text-500">{formatSize(info.size)}</span>
              ) : null}
              {info ? (
                <span className="inline-flex items-center gap-1 text-xs text-text-700"
                      title={SECURITY_LABEL[info.security_status] ?? info.security_status}>
                  {securityIcon(info.security_status)}
                  {SECURITY_LABEL[info.security_status] ?? info.security_status}
                </span>
              ) : null}
              {item.link?.is_frozen ? (
                <Lock className="h-4 w-4 text-text-500" aria-hidden="true"
                      aria-label="Vínculo congelado: el proceso que lo usó no se reinterpreta" />
              ) : null}
              {can(item, "download") ? (
                <AsyncButton
                  variant="ghost" size="sm"
                  aria-label={`Descargar ${info?.original_name ?? item.title}`}
                  title="Descargar"
                  onClick={() => download(item)}
                >
                  <Download className="h-4 w-4" aria-hidden="true" />
                </AsyncButton>
              ) : null}
              {item.link && !item.link.is_frozen && can(item, "link")
                && puede("DELETE", `/documentos/vinculos/${item.link.id}`) ? (
                <AsyncButton
                  variant="ghost" size="sm"
                  aria-label={`Desvincular ${item.title}`}
                  title="Desvincular"
                  onClick={() => detach(item)}
                >
                  <Link2Off className="h-4 w-4" aria-hidden="true" />
                </AsyncButton>
              ) : null}
            </li>
          );
        })}
        {documents.isSuccess && (documents.data ?? []).length === 0 ? (
          <li className="py-2 text-sm text-text-500">Sin documentos adjuntos.</li>
        ) : null}
      </ul>

      <Autorizado
        operacion={["POST", "/documentos"]}
        fallback={<p className="py-2 text-sm text-text-500">No tiene permiso para adjuntar documentos.</p>}
      >
        <div className="border-t border-border-default pt-3">
          <div className="flex flex-wrap items-end gap-3">
            <FormField label="Tipo documental" required>
              <select
                value={typeId} onChange={(e) => setTypeId(e.target.value)}
                aria-label="Tipo documental del archivo"
                className="h-10 w-full cursor-pointer rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 sm:w-56"
              >
                <option value="">Seleccione…</option>
                {availableTypes.map((t) => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
            </FormField>

            <div className="flex flex-col gap-1.5">
              <label htmlFor={inputId} className="text-sm font-medium text-text-700">
                Archivo <span aria-hidden="true" className="text-danger-600">*</span>
                <span className="sr-only"> (obligatorio)</span>
              </label>
              {/* El control nativo recibe foco y funciona con teclado. */}
              <input
                id={inputId} ref={inputRef} type="file"
                onChange={(e) => { setFile(e.target.files?.[0] ?? null); setPhase("idle"); }}
                className="block w-full cursor-pointer text-sm text-text-700 file:mr-3 file:cursor-pointer file:rounded-md file:border file:border-border-default file:bg-surface-50 file:px-3 file:py-1.5 file:text-sm"
              />
            </div>

            <AsyncButton
              type="button" variant="primary" onClick={upload}
              disabled={!file || !typeId || phase === "uploading" || phase === "processing"}
            >
              <Upload className="mr-1 h-4 w-4" aria-hidden="true" />
              Adjuntar
            </AsyncButton>
          </div>

        {selectedType ? (
          <p className="mt-2 text-xs text-text-500">
            Admite: {selectedType.allowed_mime_types.join(", ") || "ningún formato declarado"}
            {selectedType.max_size_bytes
              ? ` · Máximo ${formatSize(selectedType.max_size_bytes)}`
              : ""}
          </p>
        ) : null}

        {file ? (
          <p className="mt-2 flex items-center gap-2 text-sm text-text-700">
            <FileText className="h-4 w-4" aria-hidden="true" />
            <span className="truncate" title={file.name}>{truncateName(file.name)}</span>
            <span className="text-text-500">{formatSize(file.size)}</span>
            <button type="button" onClick={reset} aria-label="Quitar el archivo seleccionado"
                    className="cursor-pointer text-text-500 hover:text-text-900">
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
          </p>
        ) : null}

        {/* Estado real, sin porcentaje inventado (§93). */}
        {phase === "uploading" || phase === "processing" ? (
          <p className="mt-2 text-sm text-text-700" role="status" aria-live="polite">
            {phase === "uploading" ? "Subiendo el archivo…" : "Verificando el archivo…"}
          </p>
        ) : null}

        {errorMessage ? (
          <p className="mt-2 rounded-md border border-danger-100 bg-danger-100/30 px-3 py-2 text-sm text-danger-600"
             role="alert">
            {errorMessage}
          </p>
        ) : null}
        </div>
      </Autorizado>
    </section>
  );
}
