/** Configuración de almacenamiento — condiciones, clases, perfiles, reglas y política. */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Autorizado } from "@/components/Autorizado";
import { AsyncButton } from "@/components/AsyncButton";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { AsyncCombobox } from "@/components/AsyncCombobox";
import { SelectorDeArticulo } from "@/modules/maestros/catalogo/SelectorDeArticulo";

interface CondicionAlmacen {
  id: string;
  code: string;
  name: string;
  description: string | null;
  status: string;
  version: number;
}

interface ClaseTamano {
  id: string;
  code: string;
  name: string;
  description: string | null;
  status: string;
  version: number;
}

interface UnidadMedida {
  id: string;
  code: string;
  name: string;
  symbol: string;
  dimension: string;
}

interface PerfilAlmacenamiento {
  id: string | null;
  item_id: string;
  version: number | null;
  weight_value: string | null;
  weight_unit: UnidadMedida | null;
  volume_value: string;
  volume_unit: UnidadMedida | null;
  size_class: ClaseTamano | null;
  conditions: CondicionAlmacen[];
}

interface ReglaAlmacenamiento {
  id: string;
  code: string;
  name: string;
  priority: number;
  status: string;
  version: number;
  warehouse_id: string | null;
  warehouse_code: string | null;
  taxonomy_name: string | null;
  size_class_name: string | null;
  condition_name: string | null;
  min_weight: string | null;
  max_weight: string | null;
  weight_unit_symbol: string | null;
  min_volume: string | null;
  max_volume: string | null;
  volume_unit_symbol: string | null;
  target_label: string;
  label_policy: string;
}

interface AlmacenInfo {
  id: string;
  code: string;
  name: string;
}

interface ZonaAlmacen {
  id: string;
  code: string;
  name: string;
  zone_type_id: string;
  status: string;
}

interface TipoZona {
  id: string;
  code: string;
  name: string;
  status: string;
}

interface PoliticaAlmacen {
  warehouse_id: string;
  mode: string;
  on_no_rule: string;
  version: number | null;
}

const LABEL_POLICIES = [
  { value: "REQUIRED", label: "Requerida" },
  { value: "OPTIONAL", label: "Opcional" },
  { value: "NOT_REQUIRED", label: "No requerida" },
];

const MODES = [
  { value: "DISABLED", label: "Desactivada (almacén simple)" },
  { value: "ENFORCED", label: "Obligatoria" },
];

const NO_RULE_ACTIONS = [
  { value: "BLOCK", label: "Bloquear la ubicación" },
  { value: "ALLOW_ANY", label: "Permitir cualquier ubicación" },
];

function SelectAlmacen({
  value,
  onChange,
  almacenes,
  placeholder = "Todos los almacenes",
  includeEmpty = true,
  id,
  "aria-invalid": ariaInvalid,
  "aria-describedby": ariaDescribedby,
}: {
  value: string;
  onChange: (id: string) => void;
  almacenes: AlmacenInfo[];
  placeholder?: string;
  includeEmpty?: boolean;
  id?: string;
  "aria-invalid"?: boolean;
  "aria-describedby"?: string;
}): React.JSX.Element {
  return (
    <select
      id={id}
      aria-invalid={ariaInvalid}
      aria-describedby={ariaDescribedby}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
    >
      {includeEmpty ? <option value="">{placeholder}</option> : null}
      {almacenes.map((almacen) => (
        <option key={almacen.id} value={almacen.id}>
          {almacen.code} - {almacen.name}
        </option>
      ))}
    </select>
  );
}

export function AlmacenamientoPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  // Condiciones
  const [nuevaCondicionCode, setNuevaCondicionCode] = useState("");
  const [nuevaCondicionName, setNuevaCondicionName] = useState("");

  // Clases de tamaño
  const [nuevaClaseCode, setNuevaClaseCode] = useState("");
  const [nuevaClaseName, setNuevaClaseName] = useState("");

  // Perfil
  const [productoId, setProductoId] = useState("");
  const [perfilPeso, setPerfilPeso] = useState("");
  const [perfilUnidadPeso, setPerfilUnidadPeso] = useState("");
  const [perfilVolumen, setPerfilVolumen] = useState("");
  const [perfilUnidadVolumen, setPerfilUnidadVolumen] = useState("");
  const [perfilClaseTamano, setPerfilClaseTamano] = useState("");
  const [perfilCondiciones, setPerfilCondiciones] = useState<string[]>([]);

  // Reglas
  const [reglaCode, setReglaCode] = useState("");
  const [reglaName, setReglaName] = useState("");
  const [reglaPriority, setReglaPriority] = useState("1");
  const [reglaAlmacenId, setReglaAlmacenId] = useState("");
  const [reglaTipoDestino, setReglaTipoDestino] = useState<"ZONE" | "ZONE_TYPE">("ZONE");
  const [reglaZonaId, setReglaZonaId] = useState("");
  const [reglaTipoZonaId, setReglaTipoZonaId] = useState("");
  const [reglaTaxonomia, setReglaTaxonomia] = useState("");
  const [reglaClaseTamano, setReglaClaseTamano] = useState("");
  const [reglaCondicion, setReglaCondicion] = useState("");
  const [reglaPesoMin, setReglaPesoMin] = useState("");
  const [reglaPesoMax, setReglaPesoMax] = useState("");
  const [reglaUnidadPeso, setReglaUnidadPeso] = useState("");
  const [reglaVolumenMin, setReglaVolumenMin] = useState("");
  const [reglaVolumenMax, setReglaVolumenMax] = useState("");
  const [reglaUnidadVolumen, setReglaUnidadVolumen] = useState("");
  const [reglaEtiquetado, setReglaEtiquetado] = useState("REQUIRED");

  // Política
  const [politicaAlmacenId, setPoliticaAlmacenId] = useState("");
  const [politicaMode, setPoliticaMode] = useState("DISABLED");
  const [politicaNoRule, setPoliticaNoRule] = useState("BLOCK");

  const condicionesQuery = useQuery({
    queryKey: ["storage", "conditions"],
    queryFn: async () => {
      const resp = await apiFetch<{ items: CondicionAlmacen[] }>("/storage/conditions");
      return resp.items ?? [];
    },
    retry: false,
  });

  const clasesQuery = useQuery({
    queryKey: ["storage", "size-classes"],
    queryFn: async () => {
      const resp = await apiFetch<{ items: ClaseTamano[] }>("/storage/size-classes");
      return resp.items ?? [];
    },
    retry: false,
  });

  const unidadesMasaQuery = useQuery({
    queryKey: ["maestros", "unidades", "MASA"],
    queryFn: async () => {
      const resp = await apiFetch<{ items: UnidadMedida[] }>("/maestros/unidades?dimension=MASA");
      return resp.items ?? [];
    },
    retry: false,
  });

  const unidadesPesoQuery = useQuery({
    queryKey: ["maestros", "unidades", "PESO"],
    queryFn: async () => {
      const resp = await apiFetch<{ items: UnidadMedida[] }>("/maestros/unidades?dimension=PESO");
      return resp.items ?? [];
    },
    retry: false,
  });

  const unidadesVolumenQuery = useQuery({
    queryKey: ["maestros", "unidades", "VOLUMEN"],
    queryFn: async () => {
      const resp = await apiFetch<{ items: UnidadMedida[] }>("/maestros/unidades?dimension=VOLUMEN");
      return resp.items ?? [];
    },
    retry: false,
  });

  const almacenesQuery = useQuery({
    queryKey: ["organization", "warehouses", "ACTIVE"],
    queryFn: async () => {
      const resp = await apiFetch<{ items: AlmacenInfo[] }>("/organization/warehouses?status=ACTIVE");
      return resp.items ?? [];
    },
    retry: false,
  });

  const zonasQuery = useQuery({
    queryKey: ["organization", "warehouses", reglaAlmacenId, "zones"],
    queryFn: async () => {
      const resp = await apiFetch<ZonaAlmacen[]>(`/organization/warehouses/${reglaAlmacenId}/zones`);
      return Array.isArray(resp) ? resp : [];
    },
    enabled: Boolean(reglaAlmacenId),
    retry: false,
  });

  const tiposZonaQuery = useQuery({
    queryKey: ["organization", "zone-types"],
    queryFn: async () => {
      const resp = await apiFetch<TipoZona[]>("/organization/zone-types");
      return Array.isArray(resp) ? resp : [];
    },
    retry: false,
  });

  const perfilQuery = useQuery({
    queryKey: ["storage", "profiles", productoId],
    queryFn: async () => {
      const resp = await apiFetch<PerfilAlmacenamiento>(`/storage/profiles/${productoId}`);
      return resp;
    },
    enabled: Boolean(productoId),
    retry: false,
  });

  const politicaQuery = useQuery({
    queryKey: ["storage", "warehouse-policies", politicaAlmacenId],
    queryFn: async () => {
      const resp = await apiFetch<PoliticaAlmacen>(`/storage/warehouse-policies/${politicaAlmacenId}`);
      return resp;
    },
    enabled: Boolean(politicaAlmacenId),
    retry: false,
  });

  const reglasQuery = useQuery({
    queryKey: ["storage", "rules"],
    queryFn: async () => {
      const resp = await apiFetch<{ items: ReglaAlmacenamiento[] }>("/storage/rules");
      return resp.items ?? [];
    },
    retry: false,
  });

  const refresh = async (): Promise<void> => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["storage", "conditions"] }),
      queryClient.invalidateQueries({ queryKey: ["storage", "size-classes"] }),
      queryClient.invalidateQueries({ queryKey: ["storage", "rules"] }),
      queryClient.invalidateQueries({ queryKey: ["storage", "profiles", productoId] }),
      queryClient.invalidateQueries({ queryKey: ["storage", "warehouse-policies", politicaAlmacenId] }),
    ]);
  };

  const condiciones = condicionesQuery.data ?? [];
  const clases = clasesQuery.data ?? [];
  const unidadesPeso = [...(unidadesMasaQuery.data ?? []), ...(unidadesPesoQuery.data ?? [])];
  const unidadesVolumen = unidadesVolumenQuery.data ?? [];
  const almacenes = almacenesQuery.data ?? [];
  const zonas = (zonasQuery.data ?? []).filter((z) => z.status === "ACTIVE");
  const tiposZona = (tiposZonaQuery.data ?? []).filter((t) => t.status === "ACTIVE");
  const reglas = reglasQuery.data ?? [];
  const perfil = perfilQuery.data ?? null;
  const politica = politicaQuery.data ?? null;

  // Sincroniza el formulario del perfil al cargar
  const [perfilCargadoId, setPerfilCargadoId] = useState<string | null>(null);
  if (perfil && perfilCargadoId !== productoId) {
    setPerfilCargadoId(productoId);
    setPerfilPeso(perfil.weight_value ?? "");
    setPerfilUnidadPeso(perfil.weight_unit?.id ?? "");
    setPerfilVolumen(perfil.volume_value ?? "");
    setPerfilUnidadVolumen(perfil.volume_unit?.id ?? "");
    setPerfilClaseTamano(perfil.size_class?.id ?? "");
    setPerfilCondiciones(perfil.conditions.map((c) => c.id));
  }

  // Sincroniza política al cargar
  const [politicaCargadaId, setPoliticaCargadaId] = useState<string | null>(null);
  if (politica && politicaCargadaId !== politicaAlmacenId) {
    setPoliticaCargadaId(politicaAlmacenId);
    setPoliticaMode(politica.mode);
    setPoliticaNoRule(politica.on_no_rule);
  }

  async function crearCondicion() {
    try {
      await apiFetch("/storage/conditions", {
        method: "POST",
        body: { code: nuevaCondicionCode, name: nuevaCondicionName },
      });
      notify({ type: "success", title: "Condición creada", description: nuevaCondicionName });
      setNuevaCondicionCode("");
      setNuevaCondicionName("");
      void refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear la condición";
      notify({ type: "error", title: "No fue posible crear la condición", description: message });
    }
  }

  async function toggleCondicion(condicion: CondicionAlmacen) {
    const nuevoStatus = condicion.status === "ACTIVE" ? "INACTIVE" : "ACTIVE";
    try {
      await apiFetch(`/storage/conditions/${condicion.id}`, {
        method: "PATCH",
        body: { expected_version: condicion.version, status: nuevoStatus },
      });
      notify({ type: "success", title: nuevoStatus === "ACTIVE" ? "Condición activada" : "Condición desactivada" });
      void refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible actualizar la condición";
      notify({ type: "error", title: "No fue posible actualizar la condición", description: message });
    }
  }

  async function crearClase() {
    try {
      await apiFetch("/storage/size-classes", {
        method: "POST",
        body: { code: nuevaClaseCode, name: nuevaClaseName },
      });
      notify({ type: "success", title: "Clase de tamaño creada", description: nuevaClaseName });
      setNuevaClaseCode("");
      setNuevaClaseName("");
      void refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear la clase de tamaño";
      notify({ type: "error", title: "No fue posible crear la clase de tamaño", description: message });
    }
  }

  async function toggleClase(clase: ClaseTamano) {
    const nuevoStatus = clase.status === "ACTIVE" ? "INACTIVE" : "ACTIVE";
    try {
      await apiFetch(`/storage/size-classes/${clase.id}`, {
        method: "PATCH",
        body: { expected_version: clase.version, status: nuevoStatus },
      });
      notify({ type: "success", title: nuevoStatus === "ACTIVE" ? "Clase activada" : "Clase desactivada" });
      void refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible actualizar la clase";
      notify({ type: "error", title: "No fue posible actualizar la clase", description: message });
    }
  }

  async function guardarPerfil() {
    if (!productoId) return;
    const body: Record<string, unknown> = {
      expected_version: perfil?.version ?? null,
      weight_value: perfilPeso || null,
      weight_unit_id: perfilUnidadPeso || null,
      volume_value: perfilVolumen || null,
      volume_unit_id: perfilUnidadVolumen || null,
      size_class_id: perfilClaseTamano || null,
      condition_ids: perfilCondiciones,
    };
    try {
      await apiFetch(`/storage/profiles/${productoId}`, {
        method: "PUT",
        body,
      });
      notify({ type: "success", title: "Perfil guardado" });
      setPerfilCargadoId(null);
      await queryClient.invalidateQueries({ queryKey: ["storage", "profiles", productoId] });
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible guardar el perfil";
      notify({ type: "error", title: "No fue posible guardar el perfil", description: message });
    }
  }

  async function crearRegla() {
    const body: Record<string, unknown> = {
      code: reglaCode,
      name: reglaName,
      priority: Number(reglaPriority) || 1,
      status: "ACTIVE" as const,
      warehouse_id: reglaAlmacenId || null,
      label_policy: reglaEtiquetado,
    };
    if (reglaTaxonomia) body.taxonomy_id = reglaTaxonomia;
    if (reglaClaseTamano) body.size_class_id = reglaClaseTamano;
    if (reglaCondicion) body.condition_id = reglaCondicion;
    if (reglaPesoMin) body.min_weight = reglaPesoMin;
    if (reglaPesoMax) body.max_weight = reglaPesoMax;
    if (reglaUnidadPeso) body.weight_unit_id = reglaUnidadPeso;
    if (reglaVolumenMin) body.min_volume = reglaVolumenMin;
    if (reglaVolumenMax) body.max_volume = reglaVolumenMax;
    if (reglaUnidadVolumen) body.volume_unit_id = reglaUnidadVolumen;
    if (reglaTipoDestino === "ZONE") {
      if (reglaZonaId) body.target_zone_id = reglaZonaId;
    } else {
      if (reglaTipoZonaId) body.target_zone_type_id = reglaTipoZonaId;
    }
    try {
      await apiFetch("/storage/rules", {
        method: "POST",
        body,
      });
      notify({ type: "success", title: "Regla creada", description: reglaName });
      setReglaCode("");
      setReglaName("");
      setReglaPriority("1");
      setReglaAlmacenId("");
      setReglaTipoDestino("ZONE");
      setReglaZonaId("");
      setReglaTipoZonaId("");
      setReglaTaxonomia("");
      setReglaClaseTamano("");
      setReglaCondicion("");
      setReglaPesoMin("");
      setReglaPesoMax("");
      setReglaUnidadPeso("");
      setReglaVolumenMin("");
      setReglaVolumenMax("");
      setReglaUnidadVolumen("");
      setReglaEtiquetado("REQUIRED");
      void refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear la regla";
      notify({ type: "error", title: "No fue posible crear la regla", description: message });
    }
  }

  async function toggleRegla(regla: ReglaAlmacenamiento) {
    const nuevoStatus = regla.status === "ACTIVE" ? "INACTIVE" : "ACTIVE";
    try {
      await apiFetch(`/storage/rules/${regla.id}`, {
        method: "PATCH",
        body: { expected_version: regla.version, status: nuevoStatus },
      });
      notify({ type: "success", title: nuevoStatus === "ACTIVE" ? "Regla activada" : "Regla desactivada" });
      void refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible actualizar la regla";
      notify({ type: "error", title: "No fue posible actualizar la regla", description: message });
    }
  }

  async function guardarPolitica() {
    if (!politicaAlmacenId) return;
    try {
      await apiFetch(`/storage/warehouse-policies/${politicaAlmacenId}`, {
        method: "PUT",
        body: {
          expected_version: politica?.version ?? null,
          mode: politicaMode,
          on_no_rule: politicaNoRule,
        },
      });
      notify({ type: "success", title: "Política guardada" });
      setPoliticaCargadaId(null);
      await queryClient.invalidateQueries({ queryKey: ["storage", "warehouse-policies", politicaAlmacenId] });
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible guardar la política";
      notify({ type: "error", title: "No fue posible guardar la política", description: message });
    }
  }

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Almacenamiento"
        description="Configure condiciones, clases de tamaño, perfiles de producto, reglas y política de almacenamiento."
        crumbs={[{ label: "Maestros" }, { label: "Almacenamiento" }]}
      />

      <section aria-labelledby="condiciones-titulo" className="mb-6 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 id="condiciones-titulo" className="mb-3 text-base font-semibold text-text-900">Condiciones especiales</h2>
        {condicionesQuery.isLoading ? <p className="text-sm text-text-600">Cargando condiciones…</p> : null}
        {condicionesQuery.isError ? <p role="alert" className="text-sm text-danger-700">No fue posible cargar las condiciones.</p> : null}
        {!condicionesQuery.isLoading && !condicionesQuery.isError ? (
          <>
            <table className="mb-4 min-w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-border-default text-left">
                  <th className="py-2 pr-4 font-medium text-text-700">Código</th>
                  <th className="py-2 pr-4 font-medium text-text-700">Nombre</th>
                  <th className="py-2 pr-4 font-medium text-text-700">Estado</th>
                  <th className="py-2 pr-4 font-medium text-text-700">Acción</th>
                </tr>
              </thead>
              <tbody>
                {condiciones.map((c) => (
                  <tr key={c.id} className="border-b border-border-subtle">
                    <td className="py-2 pr-4">{c.code}</td>
                    <td className="py-2 pr-4">{c.name}</td>
                    <td className="py-2 pr-4">{c.status}</td>
                    <td className="py-2 pr-4">
                      <Autorizado operacion={["PATCH", `/storage/conditions/${c.id}`]}>
                        <AsyncButton type="button" variant="secondary" onClick={() => toggleCondicion(c)}>
                          {c.status === "ACTIVE" ? "Desactivar" : "Activar"}
                        </AsyncButton>
                      </Autorizado>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Autorizado operacion={["POST", "/storage/conditions"]}>
              <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
                <FormField label="Código" required>
                  <TextInput value={nuevaCondicionCode} onChange={(e) => setNuevaCondicionCode(e.target.value)} placeholder="FRAGIL" required />
                </FormField>
                <FormField label="Nombre" required>
                  <TextInput value={nuevaCondicionName} onChange={(e) => setNuevaCondicionName(e.target.value)} placeholder="Frágil" required />
                </FormField>
                <AsyncButton type="submit" variant="primary" onClick={crearCondicion}>Crear condición</AsyncButton>
              </form>
            </Autorizado>
          </>
        ) : null}
      </section>

      <section aria-labelledby="clases-titulo" className="mb-6 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 id="clases-titulo" className="mb-3 text-base font-semibold text-text-900">Clases de tamaño</h2>
        {clasesQuery.isLoading ? <p className="text-sm text-text-600">Cargando clases de tamaño…</p> : null}
        {clasesQuery.isError ? <p role="alert" className="text-sm text-danger-700">No fue posible cargar las clases de tamaño.</p> : null}
        {!clasesQuery.isLoading && !clasesQuery.isError ? (
          <>
            <table className="mb-4 min-w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-border-default text-left">
                  <th className="py-2 pr-4 font-medium text-text-700">Código</th>
                  <th className="py-2 pr-4 font-medium text-text-700">Nombre</th>
                  <th className="py-2 pr-4 font-medium text-text-700">Estado</th>
                  <th className="py-2 pr-4 font-medium text-text-700">Acción</th>
                </tr>
              </thead>
              <tbody>
                {clases.map((c) => (
                  <tr key={c.id} className="border-b border-border-subtle">
                    <td className="py-2 pr-4">{c.code}</td>
                    <td className="py-2 pr-4">{c.name}</td>
                    <td className="py-2 pr-4">{c.status}</td>
                    <td className="py-2 pr-4">
                      <Autorizado operacion={["PATCH", `/storage/size-classes/${c.id}`]}>
                        <AsyncButton type="button" variant="secondary" onClick={() => toggleClase(c)}>
                          {c.status === "ACTIVE" ? "Desactivar" : "Activar"}
                        </AsyncButton>
                      </Autorizado>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Autorizado operacion={["POST", "/storage/size-classes"]}>
              <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
                <FormField label="Código" required>
                  <TextInput value={nuevaClaseCode} onChange={(e) => setNuevaClaseCode(e.target.value)} placeholder="PEQUENO" required />
                </FormField>
                <FormField label="Nombre" required>
                  <TextInput value={nuevaClaseName} onChange={(e) => setNuevaClaseName(e.target.value)} placeholder="Pequeño" required />
                </FormField>
                <AsyncButton type="submit" variant="primary" onClick={crearClase}>Crear clase de tamaño</AsyncButton>
              </form>
            </Autorizado>
          </>
        ) : null}
      </section>

      <section aria-labelledby="perfil-titulo" className="mb-6 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 id="perfil-titulo" className="mb-3 text-base font-semibold text-text-900">Perfil de almacenamiento del producto</h2>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <FormField label="Producto" required className="md:col-span-3">
            <SelectorDeArticulo value={productoId} onChange={(id) => setProductoId(id)} itemType="PRODUCT" />
          </FormField>
            <FormField label="Peso">
              <TextInput value={perfilPeso} onChange={(e) => setPerfilPeso(e.target.value)} placeholder="kg" />
            </FormField>
            <FormField label="Unidad de peso">
              <select value={perfilUnidadPeso} onChange={(e) => setPerfilUnidadPeso(e.target.value)} className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                <option value="">Sin unidad</option>
                {unidadesPeso.map((u) => (
                  <option key={u.id} value={u.id}>{u.symbol} ({u.name})</option>
                ))}
              </select>
            </FormField>
            <FormField label="Volumen">
              <TextInput value={perfilVolumen} onChange={(e) => setPerfilVolumen(e.target.value)} placeholder="m³" />
            </FormField>
            <FormField label="Unidad de volumen">
              <select value={perfilUnidadVolumen} onChange={(e) => setPerfilUnidadVolumen(e.target.value)} className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                <option value="">Sin unidad</option>
                {unidadesVolumen.map((u) => (
                  <option key={u.id} value={u.id}>{u.symbol} ({u.name})</option>
                ))}
              </select>
            </FormField>
            <FormField label="Clase de tamaño">
              <select value={perfilClaseTamano} onChange={(e) => setPerfilClaseTamano(e.target.value)} className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                <option value="">Sin clase</option>
                {clases.filter((c) => c.status === "ACTIVE").map((c) => (
                  <option key={c.id} value={c.id}>{c.code} - {c.name}</option>
                ))}
              </select>
            </FormField>
          </div>
          <fieldset className="mt-3">
            <legend className="text-sm font-medium text-text-700">Condiciones del producto</legend>
            <div className="mt-2 flex flex-wrap gap-4">
              {condiciones.filter((c) => c.status === "ACTIVE").map((c) => (
                <label key={c.id} className="flex items-center gap-2 text-sm text-text-900">
                  <input
                    type="checkbox"
                    checked={perfilCondiciones.includes(c.id)}
                    onChange={(e) => {
                      setPerfilCondiciones((prev) =>
                        e.target.checked ? [...prev, c.id] : prev.filter((id) => id !== c.id),
                      );
                    }}
                  />
                  {c.code} - {c.name}
                </label>
              ))}
              {condiciones.filter((c) => c.status === "ACTIVE").length === 0 ? (
                <p className="text-sm text-text-600">No hay condiciones activas.</p>
              ) : null}
              </div>
          </fieldset>
        {productoId ? (
          <Autorizado operacion={["PUT", `/storage/profiles/${productoId}`]}>
            <div className="mt-3">
              <AsyncButton type="button" variant="primary" onClick={guardarPerfil} disabled={!productoId}>
                Guardar perfil
              </AsyncButton>
            </div>
          </Autorizado>
        ) : null}
      </section>

      <section aria-labelledby="reglas-titulo" className="mb-6 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 id="reglas-titulo" className="mb-3 text-base font-semibold text-text-900">Reglas de almacenamiento</h2>
        {reglasQuery.isLoading ? <p className="text-sm text-text-600">Cargando reglas…</p> : null}
        {reglasQuery.isError ? <p role="alert" className="text-sm text-danger-700">No fue posible cargar las reglas.</p> : null}
        {!reglasQuery.isLoading && !reglasQuery.isError ? (
          <>
            <table className="mb-4 min-w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-border-default text-left">
                  <th className="py-2 pr-4 font-medium text-text-700">Código</th>
                  <th className="py-2 pr-4 font-medium text-text-700">Nombre</th>
                  <th className="py-2 pr-4 font-medium text-text-700">Prioridad</th>
                  <th className="py-2 pr-4 font-medium text-text-700">Criterios</th>
                  <th className="py-2 pr-4 font-medium text-text-700">Destino</th>
                  <th className="py-2 pr-4 font-medium text-text-700">Etiqueta</th>
                  <th className="py-2 pr-4 font-medium text-text-700">Estado</th>
                  <th className="py-2 pr-4 font-medium text-text-700">Acción</th>
                </tr>
              </thead>
              <tbody>
                {reglas.map((r) => {
                  const criterios = [
                    r.taxonomy_name,
                    r.size_class_name,
                    r.condition_name,
                    r.min_weight || r.max_weight ? `Peso: ${r.min_weight ?? "—"} a ${r.max_weight ?? "—"} ${r.weight_unit_symbol ?? ""}` : null,
                    r.min_volume || r.max_volume ? `Volumen: ${r.min_volume ?? "—"} a ${r.max_volume ?? "—"} ${r.volume_unit_symbol ?? ""}` : null,
                  ].filter(Boolean).join(", ");
                  return (
                    <tr key={r.id} className="border-b border-border-subtle">
                      <td className="py-2 pr-4">{r.code}</td>
                      <td className="py-2 pr-4">{r.name}</td>
                      <td className="py-2 pr-4">{r.priority}</td>
                      <td className="py-2 pr-4">{criterios || "—"}</td>
                      <td className="py-2 pr-4">{r.target_label}</td>
                      <td className="py-2 pr-4">{LABEL_POLICIES.find((l) => l.value === r.label_policy)?.label ?? r.label_policy}</td>
                      <td className="py-2 pr-4">{r.status}</td>
                      <td className="py-2 pr-4">
                        <Autorizado operacion={["PATCH", `/storage/rules/${r.id}`]}>
                          <AsyncButton type="button" variant="secondary" onClick={() => toggleRegla(r)}>
                            {r.status === "ACTIVE" ? "Desactivar" : "Activar"}
                          </AsyncButton>
                        </Autorizado>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <Autorizado operacion={["POST", "/storage/rules"]}>
              <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
                <FormField label="Código" required>
                  <TextInput value={reglaCode} onChange={(e) => setReglaCode(e.target.value)} placeholder="REGLA-01" required />
                </FormField>
                <FormField label="Nombre" required>
                  <TextInput value={reglaName} onChange={(e) => setReglaName(e.target.value)} placeholder="Regla de fríos" required />
                </FormField>
                <FormField label="Prioridad" required>
                  <TextInput type="number" value={reglaPriority} onChange={(e) => setReglaPriority(e.target.value)} required />
                </FormField>
                <FormField label="Almacén">
                  <SelectAlmacen value={reglaAlmacenId} onChange={setReglaAlmacenId} almacenes={almacenes} />
                </FormField>
                <FormField label="Tipo de destino" required>
                  <select value={reglaTipoDestino} onChange={(e) => setReglaTipoDestino(e.target.value as "ZONE" | "ZONE_TYPE")} className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                    <option value="ZONE">Zona del almacén</option>
                    <option value="ZONE_TYPE">Tipo de zona</option>
                  </select>
                </FormField>
                {reglaTipoDestino === "ZONE" ? (
                  <FormField label="Zona">
                    <select value={reglaZonaId} onChange={(e) => setReglaZonaId(e.target.value)} className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                      <option value="">Selecciona una zona</option>
                      {zonas.map((z) => (
                        <option key={z.id} value={z.id}>{z.code} - {z.name}</option>
                      ))}
                    </select>
                  </FormField>
                ) : (
                  <FormField label="Tipo de zona">
                    <select value={reglaTipoZonaId} onChange={(e) => setReglaTipoZonaId(e.target.value)} className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                      <option value="">Selecciona un tipo de zona</option>
                      {tiposZona.map((t) => (
                        <option key={t.id} value={t.id}>{t.code} - {t.name}</option>
                      ))}
                    </select>
                  </FormField>
                )}
                <FormField label="Familia o categoría">
                  <AsyncCombobox
                    value={reglaTaxonomia || null}
                    onChange={(v) => setReglaTaxonomia(v ?? "")}
                    searchUrl="/maestros/catalogos/taxonomia/search"
                    label="Buscar familia o categoría"
                    placeholder="Buscar familia o categoría…"
                  />
                </FormField>
                <FormField label="Clase de tamaño">
                  <select value={reglaClaseTamano} onChange={(e) => setReglaClaseTamano(e.target.value)} className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                    <option value="">Sin clase</option>
                    {clases.filter((c) => c.status === "ACTIVE").map((c) => (
                      <option key={c.id} value={c.id}>{c.code} - {c.name}</option>
                    ))}
                  </select>
                </FormField>
                <FormField label="Condición especial">
                  <select value={reglaCondicion} onChange={(e) => setReglaCondicion(e.target.value)} className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                    <option value="">Sin condición</option>
                    {condiciones.filter((c) => c.status === "ACTIVE").map((c) => (
                      <option key={c.id} value={c.id}>{c.code} - {c.name}</option>
                    ))}
                  </select>
                </FormField>
                <FormField label="Peso mínimo">
                  <TextInput value={reglaPesoMin} onChange={(e) => setReglaPesoMin(e.target.value)} placeholder="0" />
                </FormField>
                <FormField label="Peso máximo">
                  <TextInput value={reglaPesoMax} onChange={(e) => setReglaPesoMax(e.target.value)} placeholder="100" />
                </FormField>
                <FormField label="Unidad de peso">
                  <select value={reglaUnidadPeso} onChange={(e) => setReglaUnidadPeso(e.target.value)} className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                    <option value="">Sin unidad</option>
                    {unidadesPeso.map((u) => (
                      <option key={u.id} value={u.id}>{u.symbol} ({u.name})</option>
                    ))}
                  </select>
                </FormField>
                <FormField label="Volumen mínimo">
                  <TextInput value={reglaVolumenMin} onChange={(e) => setReglaVolumenMin(e.target.value)} placeholder="0" />
                </FormField>
                <FormField label="Volumen máximo">
                  <TextInput value={reglaVolumenMax} onChange={(e) => setReglaVolumenMax(e.target.value)} placeholder="10" />
                </FormField>
                <FormField label="Unidad de volumen">
                  <select value={reglaUnidadVolumen} onChange={(e) => setReglaUnidadVolumen(e.target.value)} className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                    <option value="">Sin unidad</option>
                    {unidadesVolumen.map((u) => (
                      <option key={u.id} value={u.id}>{u.symbol} ({u.name})</option>
                    ))}
                  </select>
                </FormField>
                <FormField label="Etiquetado" required>
                  <select value={reglaEtiquetado} onChange={(e) => setReglaEtiquetado(e.target.value)} className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                    {LABEL_POLICIES.map((l) => (
                      <option key={l.value} value={l.value}>{l.label}</option>
                    ))}
                  </select>
                </FormField>
                <AsyncButton type="submit" variant="primary" onClick={crearRegla}>Crear regla</AsyncButton>
              </form>
            </Autorizado>
          </>
        ) : null}
      </section>

      <section aria-labelledby="politica-titulo" className="mb-6 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 id="politica-titulo" className="mb-3 text-base font-semibold text-text-900">Política del almacén</h2>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <FormField label="Almacén de la política" required>
            <SelectAlmacen value={politicaAlmacenId} onChange={setPoliticaAlmacenId} almacenes={almacenes} placeholder="Selecciona un almacén" />
          </FormField>
            <FormField label="Clasificación" required>
              <select value={politicaMode} onChange={(e) => setPoliticaMode(e.target.value)} disabled={!politicaAlmacenId || politicaCargadaId !== politicaAlmacenId} className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                {MODES.map((m) => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </select>
            </FormField>
            <FormField label="Sin regla aplicable" required>
              <select value={politicaNoRule} onChange={(e) => setPoliticaNoRule(e.target.value)} disabled={!politicaAlmacenId || politicaCargadaId !== politicaAlmacenId} className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                {NO_RULE_ACTIONS.map((a) => (
                  <option key={a.value} value={a.value}>{a.label}</option>
                ))}
              </select>
            </FormField>
        </div>
        {politicaAlmacenId ? (
          <Autorizado operacion={["PUT", `/storage/warehouse-policies/${politicaAlmacenId}`]}>
            <div className="mt-3">
              <AsyncButton type="button" variant="primary" onClick={guardarPolitica} disabled={!politicaAlmacenId}>
                Guardar política
              </AsyncButton>
            </div>
          </Autorizado>
        ) : null}
      </section>
    </PageContent>
  );
}
