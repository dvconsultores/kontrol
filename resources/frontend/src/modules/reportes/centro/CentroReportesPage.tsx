/** Centro de reportes — ejecutivos, operativos, financieros, fiscales, regulatorios (FR-009-010..015). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { ApiError, apiFetch } from "@/api/client";
import { descargarArchivo, mensajeDeDescarga } from "@/api/descargas";
import type { ReportResult } from "@/api/types";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { Autorizado } from "@/components/Autorizado";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

export const REPORTS: Array<{ category: string; key: string; label: string; capacidades: readonly string[] }> = [
  { category: "Ejecutivos", key: "executive_ventas", label: "Ventas (total/base/impuestos)", capacidades: ["ventas:view"] },
  { category: "Operativos", key: "operational_inventario", label: "Inventario (existencias)", capacidades: ["inventario:view"] },
  { category: "Financieros", key: "financial_aging", label: "CxC / CxP (aging)", capacidades: ["ventas:view", "compras:view"] },
  { category: "Fiscales", key: "fiscal_libros_VENTAS", label: "Libro de ventas (007)", capacidades: ["fiscal:view"] },
  { category: "Regulatorios", key: "regulatory_evaluaciones", label: "Evaluaciones de despacho (008)", capacidades: ["regulatorio:view"] },
];

const CATEGORIES = ["Ejecutivos", "Operativos", "Financieros", "Fiscales", "Regulatorios"];

export function CentroReportesPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { tiene } = useAutoridad();
  const [category, setCategory] = useState("Ejecutivos");
  const [period, setPeriod] = useState("");

  const disponibles = REPORTS.filter((r) => r.capacidades.every((c) => tiene(c, "empresa")));
  const current = disponibles.find((r) => r.category === category) ?? disponibles[0];
  const reportKey = current?.key;

  const report = useQuery({
    queryKey: ["reporting", "report", reportKey, period],
    queryFn: () => {
      const clave = current?.key;
      if (clave === undefined) {
        throw new Error("sin reporte");
      }
      return apiFetch<ReportResult>(`/reporting/reports/${clave}?period=${period || "0"}`);
    },
    enabled: current !== undefined,
    retry: false,
  });

  const exportCsv = async (): Promise<void> => {
    if (current === undefined) {
      return;
    }
    let creada: { id: string; file_ref: string | null; status: string };
    try {
      creada = await apiFetch<{ id: string; file_ref: string | null; status: string }>("/reporting/exports", {
        method: "POST",
        body: { report_key: current.key, format: "CSV", filters: { period } },
      });
    } catch (error) {
      notify({
        type: "error",
        title: "No fue posible exportar",
        description: error instanceof ApiError ? error.message : "No fue posible crear la exportación.",
      });
      return;
    }

    void queryClient.invalidateQueries({ queryKey: ["reporting", "exports"] });

    try {
      const nombre = await descargarArchivo(`/reporting/exports/${creada.id}/download`, `exportacion-${creada.id}`);
      notify({ type: "success", title: "Archivo descargado", description: nombre });
    } catch (error) {
      notify({
        type: "error",
        title: "No fue posible descargar",
        description: `${mensajeDeDescarga(error)} La exportación quedó creada; puede descargarla desde Exportaciones.`,
      });
    }
  };

  const reportRows = report.data?.rows ?? [];
  const firstRow = reportRows[0];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Centro de reportes"
        description="Reportes reconstruibles desde eventos (solo lectura); exportación auditada (FR-009-020)."
        crumbs={[{ label: "Reportes" }, { label: "Centro" }]}
      />

      {disponibles.length === 0 ? (
        <p className="text-sm text-text-500">No tiene autoridad para ver ningún reporte en esta empresa.</p>
      ) : (
        <>
          <nav aria-label="Categorías de reportes" className="mb-4 flex flex-wrap gap-2">
            {CATEGORIES.filter((c) => disponibles.some((r) => r.category === c)).map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setCategory(c)}
                aria-pressed={current?.category === c}
                className={`h-9 rounded-md border px-3 text-sm transition-colors ${
                  current?.category === c ? "border-brand-600 bg-brand-600 text-white" : "border-border-default bg-surface-0 text-text-500 hover:bg-surface-100"
                }`}
              >
                {c}
              </button>
            ))}
          </nav>

          <div className="mb-4 flex flex-wrap items-end gap-3 rounded-lg border border-border-default bg-surface-0 p-4">
            <div>
              <p className="text-sm text-text-700">{current?.label}</p>
              <p className="text-2xl font-semibold text-text-900">{report.data?.total?.toFixed(2) ?? "—"}</p>
            </div>
            <FormFieldPeriod value={period} onChange={setPeriod} />
            <Autorizado operacion={["POST", "/reporting/exports"]}>
              <AsyncButton variant="secondary" onClick={exportCsv}>
                Exportar CSV (auditado)
              </AsyncButton>
            </Autorizado>
          </div>

          <div className="overflow-hidden rounded-lg border border-border-default">
            <table className="w-full text-left text-sm">
              <thead className="bg-surface-100 text-text-700">
                <tr>
                  {firstRow
                    ? Object.keys(firstRow).map((col) => (
                        <th key={col} className="px-4 py-2 font-medium">{col}</th>
                      ))
                    : <th className="px-4 py-2 font-medium">Sin columnas</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-border-default">
                {reportRows.map((row, idx) => (
                  <tr key={idx}>
                    {Object.values(row).map((val, j) => (
                      <td key={j} className="px-4 py-1.5 text-text-700">{String(val ?? "")}</td>
                    ))}
                  </tr>
                ))}
                {reportRows.length === 0 ? (
                  <tr><td className="px-4 py-3 text-text-500">Sin datos para el reporte {current?.key}.</td></tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </>
      )}
    </PageContent>
  );
}

function FormFieldPeriod({ value, onChange }: { value: string; onChange: (v: string) => void }): React.JSX.Element {
  return (
    <label className="flex flex-col gap-1 text-sm text-text-500">
      Período
      <TextInput value={value} onChange={(e) => onChange(e.target.value)} placeholder="2026-01" />
    </label>
  );
}
