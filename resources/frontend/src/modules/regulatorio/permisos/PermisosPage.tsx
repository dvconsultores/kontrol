/** Permisos y guías — registro y validación de documentos oficiales (FR-008-010/011/012/013). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { OfficialDocumentSummary, PermitInstanceSummary, PermitTypeSummary } from "@/api/types";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Autorizado } from "@/components/Autorizado";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

const columnHelper = createColumnHelper<PermitInstanceSummary>();

export function PermisosPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();

  const [permitTypeId, setPermitTypeId] = useState("");
  const [number, setNumber] = useState("");
  const [docKind, setDocKind] = useState<"SICA" | "SIGESAI" | "SACS" | "GUIA_FISCAL">("SICA");
  const [docNumber, setDocNumber] = useState("");

  const permits = useQuery({
    queryKey: ["regulatorio", "permits"],
    queryFn: () => apiFetch<{ items: PermitInstanceSummary[] }>("/regulatory/permits"),
    retry: false,
  });
  const permitTypes = useQuery({
    queryKey: ["regulatorio", "permit-types"],
    queryFn: () => apiFetch<{ items: PermitTypeSummary[] }>("/regulatory/permit-types"),
    retry: false,
  });
  const documents = useQuery({
    queryKey: ["regulatorio", "official-documents"],
    queryFn: () => apiFetch<{ items: OfficialDocumentSummary[] }>("/regulatory/official-documents"),
    retry: false,
  });

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["regulatorio"] });
  };

  const createPermit = async (): Promise<void> => {
    if (!permitTypeId) return;
    await apiFetch("/regulatory/permits", { method: "POST", body: { permit_type_id: permitTypeId, number } });
    notify({ type: "success", title: "Permiso creado", description: number });
    setNumber("");
    refresh();
  };

  const transition = async (id: string, target: string): Promise<void> => {
    await apiFetch(`/regulatory/permits/${id}/transition`, { method: "POST", body: { target } });
    notify({ type: "success", title: "Permiso actualizado", description: `Estado → ${target}` });
    refresh();
  };

  const registerDoc = async (): Promise<void> => {
    await apiFetch("/regulatory/official-documents", { method: "POST", body: { kind: docKind, number: docNumber, organism: docKind } });
    notify({ type: "success", title: "Guía registrada", description: `${docKind} · ${docNumber} (validada, no fabricada)` });
    setDocNumber("");
    refresh();
  };

  const columns = [
    columnHelper.accessor("number", { header: "Número" }),
    columnHelper.accessor("expires_at", { header: "Vence" }),
    columnHelper.accessor("hash", { header: "Hash", cell: (info) => (info.getValue() ?? "").slice(0, 10) }),
    columnHelper.accessor("verification", { header: "Verificación" }),
    columnHelper.accessor("status", { header: "Estado" }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => {
        const s = row.original.status;
        const next: Record<string, string> = {
          DRAFT: "REGISTERED",
          REGISTERED: "VERIFIED",
          VERIFIED: "APPROVED_FOR_USE",
          APPROVED_FOR_USE: "USED",
        };
        return (
          <div className="flex justify-end gap-1">
            {next[s] && puede("POST", `/regulatory/permits/${row.original.id}/transition`) ? <AsyncButton size="sm" variant="secondary" onClick={() => transition(row.original.id, next[s])}>{next[s]}</AsyncButton> : null}
          </div>
        );
      },
    }),
  ];

  const section = (title: string, body: React.JSX.Element): React.JSX.Element => (
    <div className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
      <h2 className="mb-2 text-base font-semibold text-text-900">{title}</h2>
      {body}
    </div>
  );

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Permisos y guías"
        description="Permisos con ciclo de vida y guías SICA/SIGESAI/SACS registradas y validadas (Kontrol no fabrica permisos externos)."
        crumbs={[{ label: "Regulatorio" }, { label: "Permisos y guías" }]}
      />

      <Autorizado operacion={["POST", "/regulatory/permits"]}>
        {section("Crear permiso", (
          <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
            <FormField label="Tipo">
              <select value={permitTypeId} onChange={(e) => setPermitTypeId(e.target.value)} className="h-10 w-52 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                <option value="">Seleccionar…</option>
                {(permitTypes.data?.items ?? []).map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              </select>
            </FormField>
            <FormField label="Número">
              <TextInput value={number} onChange={(e) => setNumber(e.target.value)} placeholder="Ej. PER-001" />
            </FormField>
            <AsyncButton type="submit" variant="secondary" onClick={createPermit}>Crear</AsyncButton>
          </form>
        ))}
      </Autorizado>

      <DataTable
        columns={columns}
        data={permits.data?.items ?? []}
        loading={permits.isLoading}
        error={permits.isError ? "No fue posible cargar los permisos." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin permisos"
        emptyDescription="Cree un permiso a partir de un tipo configurado."
      />

      <Autorizado operacion={["POST", "/regulatory/official-documents"]}>
        {section("Registrar guía oficial", (
          <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
            <FormField label="Tipo de guía">
              <select value={docKind} onChange={(e) => setDocKind(e.target.value as typeof docKind)} className="h-10 w-44 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                <option value="SICA">SICA</option>
                <option value="SIGESAI">SIGESAI</option>
                <option value="SACS">SACS</option>
                <option value="GUIA_FISCAL">Guía fiscal</option>
              </select>
            </FormField>
            <FormField label="Número">
              <TextInput value={docNumber} onChange={(e) => setDocNumber(e.target.value)} placeholder="Ej. G-2026-001" />
            </FormField>
            <AsyncButton type="submit" variant="secondary" onClick={registerDoc}>Registrar</AsyncButton>
          </form>
        ))}
      </Autorizado>

      {section("Guías y documentos oficiales", (
        <div>
          {(documents.data?.items ?? []).map((d) => (
            <div key={d.id} className="flex items-center justify-between border-b border-border-default px-4 py-2 text-sm last:border-b-0">
              <span className="text-text-700">{d.kind} · {d.number}</span>
              <span className="text-text-500">{d.verification ?? "—"} · {d.status}</span>
            </div>
          ))}
          {(documents.data?.items ?? []).length === 0 ? <p className="text-sm text-text-500">Sin guías registradas.</p> : null}
        </div>
      ))}
    </PageContent>
  );
}
