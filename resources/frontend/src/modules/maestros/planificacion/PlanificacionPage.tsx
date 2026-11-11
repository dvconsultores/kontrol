import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { useState } from "react";

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
import { AvisoDeAlmacenes } from "@/modules/organizacion/almacenes/AvisoDeAlmacenes";
import { useAlmacenesDeEmpresa } from "@/modules/organizacion/almacenes/useAlmacenesDeEmpresa";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";

type Policy = {
  id: string;
  warehouse_id: string | null;
  warehouse_code: string | null;
  code: string;
  name: string;
  demand_source: string;
  lookback_days: number;
  horizon_days: number;
  lead_time_days: number;
  safety_mode: string;
  safety_value: string;
  rotation_metric: string;
  status: string;
  valid_from: string | null;
  valid_to: string | null;
  auto_replenishment_enabled: boolean;
  version: number;
};

type Band = {
  id: string;
  code: string;
  name: string;
  metric: string;
  lower_bound: string;
  upper_bound: string | null;
  sort_order: number;
  status: string;
  version: number;
};

type PageData<T> = { items: T[] };

const DEMAND_SOURCE_LABEL: Record<string, string> = {
  DISPATCHED_SALES: "Ventas despachadas (neto de devoluciones)",
  INVENTORY_ISSUES: "Salidas de inventario",
};

const SAFETY_MODE_LABEL: Record<string, string> = {
  NONE: "Sin stock de seguridad",
  FIXED_QTY: "Cantidad fija",
  DAYS: "Días de demanda media",
};

const ROTATION_METRIC_LABEL: Record<string, string> = {
  DEMAND_VELOCITY: "Velocidad de demanda (unidades por día)",
  TURNOVER: "Rotación (demanda / existencia media)",
};

const SAFETY_MODES = [
  { value: "NONE", label: SAFETY_MODE_LABEL.NONE },
  { value: "FIXED_QTY", label: SAFETY_MODE_LABEL.FIXED_QTY },
  { value: "DAYS", label: SAFETY_MODE_LABEL.DAYS },
];

const DEMAND_SOURCES = [
  { value: "DISPATCHED_SALES", label: DEMAND_SOURCE_LABEL.DISPATCHED_SALES },
  { value: "INVENTORY_ISSUES", label: DEMAND_SOURCE_LABEL.INVENTORY_ISSUES },
];

const ROTATION_METRICS = [
  { value: "DEMAND_VELOCITY", label: ROTATION_METRIC_LABEL.DEMAND_VELOCITY },
  { value: "TURNOVER", label: ROTATION_METRIC_LABEL.TURNOVER },
];

function etiqueta(value: string, source: Record<string, string>): string {
  return source[value] ?? value;
}

export function PlanificacionPage(): React.JSX.Element {
  const { activeCompany } = useCompany();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();

  const almacenesQuery = useAlmacenesDeEmpresa(activeCompany?.id ?? null);

  const politicas = useQuery({
    queryKey: ["planificacion", "politicas"],
    queryFn: () => apiFetch<PageData<Policy>>("/planning/policies"),
    enabled: Boolean(activeCompany),
    retry: false,
  });

  const bandas = useQuery({
    queryKey: ["planificacion", "bandas"],
    queryFn: () => apiFetch<PageData<Band>>("/planning/rotation-bands"),
    enabled: Boolean(activeCompany),
    retry: false,
  });

  const [submittedPolitica, setSubmittedPolitica] = useState(false);
  const [pCode, setPCode] = useState("");
  const [pName, setPName] = useState("");
  const [pAlcance, setPAlcance] = useState("");
  const [pFuente, setPFuente] = useState("DISPATCHED_SALES");
  const [pHistorico, setPHistorico] = useState("");
  const [pHorizonte, setPHorizonte] = useState("");
  const [pPlazo, setPPlazo] = useState("");
  const [pSeguridad, setPSeguridad] = useState("NONE");
  const [pValorSeguridad, setPValorSeguridad] = useState("");
  const [pMetrica, setPMetrica] = useState("DEMAND_VELOCITY");
  const [pDesde, setPDesde] = useState("");
  const [pHasta, setPHasta] = useState("");
  const [pAuto, setPAuto] = useState(false);

  const [submittedBanda, setSubmittedBanda] = useState(false);
  const [bCode, setBCode] = useState("");
  const [bName, setBName] = useState("");
  const [bMetrica, setBMetrica] = useState("DEMAND_VELOCITY");
  const [bDesde, setBDesde] = useState("");
  const [bHasta, setBHasta] = useState("");
  const [bOrden, setBOrden] = useState("");

  const limpiarPolitica = (): void => {
    setPCode("");
    setPName("");
    setPAlcance("");
    setPFuente("DISPATCHED_SALES");
    setPHistorico("");
    setPHorizonte("");
    setPPlazo("");
    setPSeguridad("NONE");
    setPValorSeguridad("");
    setPMetrica("DEMAND_VELOCITY");
    setPDesde("");
    setPHasta("");
    setPAuto(false);
    setSubmittedPolitica(false);
  };

  const validarPolitica = (): boolean => {
    if (
      !pCode.trim()
      || !pName.trim()
      || pHistorico === ""
      || pHorizonte === ""
      || pPlazo === ""
      || (pSeguridad !== "NONE" && pValorSeguridad === "")
    ) return false;
    if (!/^\d+$/.test(pHistorico) || Number(pHistorico) < 1) return false;
    if (!/^\d+$/.test(pHorizonte) || Number(pHorizonte) < 1) return false;
    if (!/^\d+$/.test(pPlazo) || Number(pPlazo) < 0) return false;
    if (pSeguridad !== "NONE" && (!/^\d+(\.\d+)?$/.test(pValorSeguridad) || Number(pValorSeguridad) < 0)) return false;
    return true;
  };

  const crearPolitica = async (): Promise<void> => {
    setSubmittedPolitica(true);
    if (!validarPolitica()) return;
    try {
      await apiFetch("/planning/policies", {
        method: "POST",
        body: {
          code: pCode.trim(),
          name: pName.trim(),
          warehouse_id: pAlcance || null,
          demand_source: pFuente,
          lookback_days: Number(pHistorico),
          horizon_days: Number(pHorizonte),
          lead_time_days: Number(pPlazo),
          safety_mode: pSeguridad,
          safety_value: pSeguridad === "NONE" ? "0" : pValorSeguridad,
          rotation_metric: pMetrica,
          status: "ACTIVE",
          valid_from: pDesde || null,
          valid_to: pHasta || null,
          auto_replenishment_enabled: pAuto,
        },
      });
      notify({ type: "success", title: "Política creada", description: `${pCode} · ${pName}` });
      limpiarPolitica();
      void queryClient.invalidateQueries({ queryKey: ["planificacion", "politicas"] });
    } catch (err) {
      notify({
        type: "error",
        title: "No fue posible crear la política",
        description: err instanceof Error ? err.message : "Error inesperado",
      });
    }
  };

  const cambiarEstadoPolitica = async (policy: Policy, status: "ACTIVE" | "INACTIVE"): Promise<void> => {
    try {
      await apiFetch(`/planning/policies/${policy.id}`, {
        method: "PATCH",
        body: { expected_version: policy.version, status },
      });
      notify({ type: "success", title: status === "ACTIVE" ? "Política activada" : "Política desactivada" });
      void queryClient.invalidateQueries({ queryKey: ["planificacion", "politicas"] });
    } catch (err) {
      notify({
        type: "error",
        title: "No fue posible cambiar la política",
        description: err instanceof Error ? err.message : "Error inesperado",
      });
    }
  };

  const limpiarBanda = (): void => {
    setBCode("");
    setBName("");
    setBMetrica("DEMAND_VELOCITY");
    setBDesde("");
    setBHasta("");
    setBOrden("");
    setSubmittedBanda(false);
  };

  const validarBanda = (): boolean => {
    if (!bCode.trim() || !bName.trim() || bDesde === "") return false;
    return true;
  };

  const crearBanda = async (): Promise<void> => {
    setSubmittedBanda(true);
    if (!validarBanda()) return;
    try {
      await apiFetch("/planning/rotation-bands", {
        method: "POST",
        body: {
          code: bCode.trim(),
          name: bName.trim(),
          metric: bMetrica,
          lower_bound: bDesde,
          upper_bound: bHasta || null,
          sort_order: Number(bOrden || 0),
          status: "ACTIVE",
        },
      });
      notify({ type: "success", title: "Banda creada", description: `${bCode} · ${bName}` });
      limpiarBanda();
      void queryClient.invalidateQueries({ queryKey: ["planificacion", "bandas"] });
    } catch (err) {
      notify({
        type: "error",
        title: "No fue posible crear la banda",
        description: err instanceof Error ? err.message : "Error inesperado",
      });
    }
  };

  const cambiarEstadoBanda = async (band: Band, status: "ACTIVE" | "INACTIVE"): Promise<void> => {
    try {
      await apiFetch(`/planning/rotation-bands/${band.id}`, {
        method: "PATCH",
        body: { expected_version: band.version, status },
      });
      notify({ type: "success", title: status === "ACTIVE" ? "Banda activada" : "Banda desactivada" });
      void queryClient.invalidateQueries({ queryKey: ["planificacion", "bandas"] });
    } catch (err) {
      notify({
        type: "error",
        title: "No fue posible cambiar la banda",
        description: err instanceof Error ? err.message : "Error inesperado",
      });
    }
  };

  const columnasPoliticas: ColumnDef<Policy, unknown>[] = [
    { accessorKey: "code", header: "Código" },
    { accessorKey: "name", header: "Nombre" },
    {
      id: "alcance",
      header: "Alcance",
      cell: ({ row }) => row.original.warehouse_code ?? "Empresa",
    },
    {
      id: "fuente",
      header: "Fuente",
      cell: ({ row }) => etiqueta(row.original.demand_source, DEMAND_SOURCE_LABEL),
    },
    {
      id: "historicohorizonteplazo",
      header: "Histórico / horizonte / plazo",
      cell: ({ row }) => `${row.original.lookback_days} / ${row.original.horizon_days} / ${row.original.lead_time_days} días`,
    },
    {
      id: "seguridad",
      header: "Seguridad",
      cell: ({ row }) => {
        if (row.original.safety_mode === "NONE") return SAFETY_MODE_LABEL.NONE;
        return `${SAFETY_MODE_LABEL[row.original.safety_mode] ?? row.original.safety_mode} (${row.original.safety_value})`;
      },
    },
    {
      id: "metrica",
      header: "Métrica",
      cell: ({ row }) => etiqueta(row.original.rotation_metric, ROTATION_METRIC_LABEL),
    },
    {
      id: "deteccion",
      header: "Detección",
      cell: ({ row }) => (row.original.auto_replenishment_enabled ? "Activa" : "Apagada"),
    },
    {
      id: "estado",
      header: "Estado",
      cell: ({ row }) => (row.original.status === "ACTIVE" ? "Activa" : "Inactiva"),
    },
    { accessorKey: "version", header: "Versión" },
    {
      id: "acciones",
      header: "Acciones",
      cell: ({ row }) => {
        const policy = row.original;
        if (!puede("PATCH", "/planning/policies/_")) return null;
        const activa = policy.status === "ACTIVE";
        const auto = policy.auto_replenishment_enabled;
        return (
          <div className="flex justify-end gap-1">
            <AsyncButton
              variant="ghost"
              size="sm"
              aria-label={`${activa ? "Desactivar" : "Activar"} ${policy.code}`}
              title={activa ? "Desactivar" : "Activar"}
              onClick={() => cambiarEstadoPolitica(policy, activa ? "INACTIVE" : "ACTIVE")}
            >
              {activa ? "Desactivar" : "Activar"}
            </AsyncButton>
            <AsyncButton
              variant="ghost"
              size="sm"
              aria-label={`${auto ? "Apagar" : "Activar"} detección ${policy.code}`}
              title={auto ? "Apagar detección" : "Activar detección"}
              onClick={() =>
                apiFetch(`/planning/policies/${policy.id}`, {
                  method: "PATCH",
                  body: {
                    expected_version: policy.version,
                    auto_replenishment_enabled: !auto,
                  },
                }).then(() => queryClient.invalidateQueries({ queryKey: ["planificacion", "politicas"] }))
              }
            >
              {auto ? "Apagar detección" : "Activar detección"}
            </AsyncButton>
          </div>
        );
      },
    },
  ];

  const columnasBandas: ColumnDef<Band, unknown>[] = [
    { accessorKey: "code", header: "Código" },
    { accessorKey: "name", header: "Nombre" },
    {
      id: "metrica",
      header: "Métrica",
      cell: ({ row }) => etiqueta(row.original.metric, ROTATION_METRIC_LABEL),
    },
    {
      id: "rango",
      header: "Rango",
      cell: ({ row }) => `[${row.original.lower_bound}, ${row.original.upper_bound ?? "∞"})`,
    },
    { accessorKey: "sort_order", header: "Orden" },
    {
      id: "estado",
      header: "Estado",
      cell: ({ row }) => (row.original.status === "ACTIVE" ? "Activa" : "Inactiva"),
    },
    { accessorKey: "version", header: "Versión" },
    {
      id: "acciones",
      header: "Acciones",
      cell: ({ row }) => {
        const band = row.original;
        if (!puede("PATCH", "/planning/rotation-bands/_")) return null;
        const activa = band.status === "ACTIVE";
        return (
          <div className="flex justify-end gap-1">
            <AsyncButton
              variant="ghost"
              size="sm"
              aria-label={`${activa ? "Desactivar" : "Activar"} ${band.code}`}
              title={activa ? "Desactivar" : "Activar"}
              onClick={() => cambiarEstadoBanda(band, activa ? "INACTIVE" : "ACTIVE")}
            >
              {activa ? "Desactivar" : "Activar"}
            </AsyncButton>
          </div>
        );
      },
    },
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Planificación de abastecimiento"
        description="Políticas de demanda, horizonte, plazo y stock de seguridad, y bandas de rotación. Sin política, la requisición no muestra sugerencia."
        crumbs={[{ label: "Maestros" }, { label: "Planificación de abastecimiento" }]}
      />

      {!activeCompany ? (
        <div className="rounded-md border border-warning-100 bg-warning-100/40 p-4 text-sm text-warning-600" role="alert">
          No hay una empresa activa. Vaya a <strong>Organización → Empresas</strong> y active la empresa.
        </div>
      ) : (
        <>
          <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
            <h2 className="mb-2 text-base font-semibold text-text-900">Políticas de planificación</h2>
            <Autorizado operacion={["POST", "/planning/policies"]}>
              <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
                <div data-invalid={submittedPolitica && !pCode.trim()}>
                  <FormField label="Código de la política" required error={submittedPolitica && !pCode.trim() ? "Campo obligatorio" : undefined}>
                    <TextInput value={pCode} onChange={(e) => setPCode(e.target.value)} />
                  </FormField>
                </div>
                <div data-invalid={submittedPolitica && !pName.trim()}>
                  <FormField label="Nombre de la política" required error={submittedPolitica && !pName.trim() ? "Campo obligatorio" : undefined}>
                    <TextInput value={pName} onChange={(e) => setPName(e.target.value)} />
                  </FormField>
                </div>
                <FormField label="Alcance">
                  <select
                    value={pAlcance}
                    onChange={(e) => setPAlcance(e.target.value)}
                    aria-label="Alcance"
                    className="h-10 w-full sm:w-56 cursor-pointer rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                  >
                    <option value="">Toda la empresa</option>
                    {(almacenesQuery.data?.items ?? []).map((wh) => (
                      <option key={wh.id} value={wh.id}>{`${wh.code} - ${wh.name}`}</option>
                    ))}
                  </select>
                </FormField>
                <AvisoDeAlmacenes consulta={almacenesQuery} />
                <FormField label="Fuente de demanda" required>
                  <select
                    value={pFuente}
                    onChange={(e) => setPFuente(e.target.value)}
                    aria-label="Fuente de demanda"
                    className="h-10 w-full sm:w-64 cursor-pointer rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                  >
                    {DEMAND_SOURCES.map((d) => (
                      <option key={d.value} value={d.value}>{d.label}</option>
                    ))}
                  </select>
                </FormField>
                <div data-invalid={submittedPolitica && (!/^\d+$/.test(pHistorico) || Number(pHistorico) < 1)}>
                  <FormField
                    label="Días de histórico"
                    required
                    error={submittedPolitica && (!/^\d+$/.test(pHistorico) || Number(pHistorico) < 1) ? "Debe ser un entero mayor o igual a 1" : undefined}
                  >
                    <TextInput type="number" min={1} value={pHistorico} onChange={(e) => setPHistorico(e.target.value)} />
                  </FormField>
                </div>
                <div data-invalid={submittedPolitica && (!/^\d+$/.test(pHorizonte) || Number(pHorizonte) < 1)}>
                  <FormField
                    label="Días de horizonte"
                    required
                    error={submittedPolitica && (!/^\d+$/.test(pHorizonte) || Number(pHorizonte) < 1) ? "Debe ser un entero mayor o igual a 1" : undefined}
                  >
                    <TextInput type="number" min={1} value={pHorizonte} onChange={(e) => setPHorizonte(e.target.value)} />
                  </FormField>
                </div>
                <div data-invalid={submittedPolitica && (!/^\d+$/.test(pPlazo) || Number(pPlazo) < 0)}>
                  <FormField
                    label="Plazo de reposición (días)"
                    required
                    error={submittedPolitica && (!/^\d+$/.test(pPlazo) || Number(pPlazo) < 0) ? "Debe ser un entero mayor o igual a 0" : undefined}
                  >
                    <TextInput type="number" min={0} value={pPlazo} onChange={(e) => setPPlazo(e.target.value)} />
                  </FormField>
                </div>
                <FormField label="Stock de seguridad" required>
                  <select
                    value={pSeguridad}
                    onChange={(e) => setPSeguridad(e.target.value)}
                    aria-label="Stock de seguridad"
                    className="h-10 w-full sm:w-56 cursor-pointer rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                  >
                    {SAFETY_MODES.map((m) => (
                      <option key={m.value} value={m.value}>{m.label}</option>
                    ))}
                  </select>
                </FormField>
                {pSeguridad !== "NONE" && (
                  <div data-invalid={submittedPolitica && (!/^\d+(\.\d+)?$/.test(pValorSeguridad) || Number(pValorSeguridad) < 0)}>
                    <FormField
                      label="Valor de seguridad"
                      required
                      help={pSeguridad === "FIXED_QTY" ? "Cantidad en unidad base" : "Días de demanda media"}
                      error={submittedPolitica && (!/^\d+(\.\d+)?$/.test(pValorSeguridad) || Number(pValorSeguridad) < 0) ? "Debe ser mayor o igual a 0" : undefined}
                    >
                      <TextInput type="number" min={0} value={pValorSeguridad} onChange={(e) => setPValorSeguridad(e.target.value)} />
                    </FormField>
                  </div>
                )}
                <FormField label="Métrica de rotación" required>
                  <select
                    value={pMetrica}
                    onChange={(e) => setPMetrica(e.target.value)}
                    aria-label="Métrica de rotación"
                    className="h-10 w-full sm:w-64 cursor-pointer rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                  >
                    {ROTATION_METRICS.map((m) => (
                      <option key={m.value} value={m.value}>{m.label}</option>
                    ))}
                  </select>
                </FormField>
                <FormField label="Vigente desde">
                  <TextInput type="date" value={pDesde} onChange={(e) => setPDesde(e.target.value)} />
                </FormField>
                <FormField label="Vigente hasta">
                  <TextInput type="date" value={pHasta} onChange={(e) => setPHasta(e.target.value)} />
                </FormField>
                <div>
                  <label htmlFor="auto-replenishment" className="font-medium">
                    Detección automática de reposición
                  </label>
                  <input
                    id="auto-replenishment"
                    type="checkbox"
                    checked={pAuto}
                    onChange={(e) => setPAuto(e.target.checked)}
                  />
                  <p className="text-sm">
                    Avisa cuando el disponible llega al punto de reorden. No crea compras.
                  </p>
                </div>
                <AsyncButton type="submit" variant="primary" onClick={crearPolitica}>
                  Crear política
                </AsyncButton>
              </form>
            </Autorizado>

            <DataTable
              columns={columnasPoliticas}
              data={politicas.data?.items ?? []}
              loading={politicas.isLoading}
              error={politicas.isError ? "No fue posible cargar las políticas." : null}
              emptyTitle="Sin políticas"
              emptyDescription="Sin política, la planificación responde «no configurada» y la requisición se hace a mano."
              getRowId={(row) => row.id}
            />
          </section>

          <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
            <h2 className="mb-2 text-base font-semibold text-text-900">Bandas de rotación</h2>
            <Autorizado operacion={["POST", "/planning/rotation-bands"]}>
              <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
                <div data-invalid={submittedBanda && !bCode.trim()}>
                  <FormField label="Código de la banda" required error={submittedBanda && !bCode.trim() ? "Campo obligatorio" : undefined}>
                    <TextInput value={bCode} onChange={(e) => setBCode(e.target.value)} />
                  </FormField>
                </div>
                <div data-invalid={submittedBanda && !bName.trim()}>
                  <FormField label="Nombre de la banda" required error={submittedBanda && !bName.trim() ? "Campo obligatorio" : undefined}>
                    <TextInput value={bName} onChange={(e) => setBName(e.target.value)} />
                  </FormField>
                </div>
                <FormField label="Métrica de la banda" required>
                  <select
                    value={bMetrica}
                    onChange={(e) => setBMetrica(e.target.value)}
                    aria-label="Métrica de la banda"
                    className="h-10 w-full sm:w-64 cursor-pointer rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                  >
                    {ROTATION_METRICS.map((m) => (
                      <option key={m.value} value={m.value}>{m.label}</option>
                    ))}
                  </select>
                </FormField>
                <div data-invalid={submittedBanda && bDesde === ""}>
                  <FormField label="Desde (incluido)" required error={submittedBanda && bDesde === "" ? "Campo obligatorio" : undefined}>
                    <TextInput value={bDesde} onChange={(e) => setBDesde(e.target.value)} />
                  </FormField>
                </div>
                <FormField label="Hasta (excluido)" help="Vacío: sin límite superior">
                  <TextInput value={bHasta} onChange={(e) => setBHasta(e.target.value)} />
                </FormField>
                <FormField label="Orden">
                  <TextInput type="number" value={bOrden} onChange={(e) => setBOrden(e.target.value)} />
                </FormField>
                <AsyncButton type="submit" variant="primary" onClick={crearBanda}>
                  Crear banda
                </AsyncButton>
              </form>
            </Autorizado>

            <DataTable
              columns={columnasBandas}
              data={bandas.data?.items ?? []}
              loading={bandas.isLoading}
              error={bandas.isError ? "No fue posible cargar las bandas." : null}
              emptyTitle="Sin bandas"
              emptyDescription="Registre bandas de rotación para clasificar la demanda."
              getRowId={(row) => row.id}
            />
          </section>
        </>
      )}
    </PageContent>
  );
}
