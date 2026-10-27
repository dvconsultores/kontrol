/**
 * Fuentes de tasa y política de resolución — Spec 013.
 *
 * De dónde viene una tasa dejó de ser texto libre en una fila. Aquí la fuente
 * se declara, se le pone la autoridad que la respalda y se puede desactivar sin
 * que su historia desaparezca: lo que deja de producir son tasas nuevas.
 *
 * La política de resolución es de esta Spec y no debe confundirse con la
 * política cambiaria de la 038: aquélla decide **si se puede convertir**, ésta
 * decide **de dónde sale el número**. Nace denegando invertir y triangular,
 * porque derivar una tasa es una decisión económica.
 *
 * Ninguna regla venezolana está cableada. Que el BCV sea la fuente oficial se
 * configura aquí; y mientras no exista un canal automatizable verificado, la
 * ingesta externa sigue siendo de la Spec 048 y esto funciona a mano.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { ApiError, apiFetch } from "@/api/client";
import type { RateImportBatch, RatePolicy, RateSource } from "@/api/types";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Autorizado } from "@/components/Autorizado";
import { AsyncButton } from "@/components/AsyncButton";
import { FormField } from "@/components/FormField";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";

export function FuentesPage(): React.JSX.Element {
  const qc = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();

  const [codigo, setCodigo] = useState("");
  const [nombre, setNombre] = useState("");
  const [tipo, setTipo] = useState("OFFICIAL");
  const [autoridad, setAutoridad] = useState("");
  const [prioridad, setPrioridad] = useState("100");

  const [politicaCodigo, setPoliticaCodigo] = useState("");
  const [desde, setDesde] = useState("");
  const [inversion, setInversion] = useState(false);
  const [triangulacion, setTriangulacion] = useState(false);
  const [antiguedad, setAntiguedad] = useState("");
  const [aprobacion, setAprobacion] = useState(false);

  const fuentes = useQuery({
    queryKey: ["fuentes", "lista"],
    queryFn: () => apiFetch<{ items: RateSource[] }>("/treasury/rate-sources"),
  });

  const politicas = useQuery({
    queryKey: ["fuentes", "politicas"],
    queryFn: () => apiFetch<{ items: RatePolicy[] }>("/treasury/rate-policies"),
  });

  const lotes = useQuery({
    queryKey: ["fuentes", "lotes"],
    queryFn: () => apiFetch<{ items: RateImportBatch[] }>("/treasury/exchange-rates/import-batches"),
  });

  function fallo(titulo: string) {
    return (e: unknown) =>
      notify({
        type: "error",
        title: titulo,
        description: e instanceof ApiError ? e.message : undefined,
      });
  }

  async function refrescar(): Promise<void> {
    await qc.invalidateQueries({ queryKey: ["fuentes"] });
  }

  async function crearFuente(): Promise<void> {
    if (!codigo.trim() || !nombre.trim()) {
      notify({ type: "error", title: "Indique código y nombre" });
      return;
    }
    try {
      await apiFetch("/treasury/rate-sources", {
        method: "POST",
        body: {
          code: codigo.toUpperCase(),
          name: nombre,
          source_type: tipo,
          authority_reference: autoridad || null,
          priority: Number(prioridad) || 100,
        },
      });
      notify({ type: "success", title: "Fuente creada", description: codigo.toUpperCase() });
      setCodigo("");
      setNombre("");
      setAutoridad("");
      await refrescar();
    } catch (e) {
      fallo("No se pudo crear la fuente")(e);
    }
  }

  async function cambiarEstado(f: RateSource): Promise<void> {
    const siguiente = f.status === "ACTIVE" ? "DISABLED" : "ACTIVE";
    try {
      await apiFetch(`/treasury/rate-sources/${f.id}/status`, {
        method: "POST",
        body: { status: siguiente },
      });
      notify({
        type: "success",
        title: siguiente === "ACTIVE" ? "Fuente activada" : "Fuente desactivada",
        description:
          siguiente === "DISABLED"
            ? "Deja de producir tasas nuevas; su historia se conserva."
            : undefined,
      });
      await refrescar();
    } catch (e) {
      fallo("No se pudo cambiar el estado")(e);
    }
  }

  async function crearPolitica(): Promise<void> {
    if (!politicaCodigo.trim() || !desde) {
      notify({ type: "error", title: "Indique código y vigencia" });
      return;
    }
    try {
      const p = await apiFetch<RatePolicy>("/treasury/rate-policies", {
        method: "POST",
        body: {
          policy_code: politicaCodigo,
          effective_from: desde,
          allow_inversion: inversion,
          allow_triangulation: triangulacion,
          max_age_days: antiguedad.trim() === "" ? null : Number(antiguedad),
          require_rate_approval: aprobacion,
        },
      });
      notify({
        type: "success",
        title: "Política creada en borrador",
        description: `${p.policy_code} v${p.version}. Todavía no rige.`,
      });
      setPoliticaCodigo("");
      await refrescar();
    } catch (e) {
      fallo("No se pudo crear la política")(e);
    }
  }

  async function activarPolitica(p: RatePolicy): Promise<void> {
    try {
      await apiFetch(`/treasury/rate-policies/${p.id}/activate`, { method: "POST", body: {} });
      notify({
        type: "success",
        title: `Rige ${p.policy_code} v${p.version}`,
        description: "La versión anterior queda sustituida; no se borra.",
      });
      await refrescar();
    } catch (e) {
      fallo("No se pudo activar la política")(e);
    }
  }

  return (
    <PageContent>
      <PageHeader
        title="Fuentes de tasa"
        description="De dónde viene cada tasa y cómo se resuelve. Ninguna regla legal está en el código."
        crumbs={[{ label: "Tesorería" }, { label: "Fuentes de tasa" }]}
      />

      <Autorizado operacion={["POST", "/treasury/rate-sources"]}>
        <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-2 text-base font-semibold text-text-900">Nueva fuente</h2>
          <div className="flex flex-wrap items-end gap-3">
            <FormField label="Código" required>
              <TextInput value={codigo} onChange={(e) => setCodigo(e.target.value)} placeholder="BCV" />
            </FormField>
            <FormField label="Nombre" required>
              <TextInput
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                placeholder="Banco Central"
              />
            </FormField>
            <FormField label="Tipo">
              <TextInput value={tipo} onChange={(e) => setTipo(e.target.value)} />
            </FormField>
            <FormField label="Autoridad que la respalda">
              <TextInput
                value={autoridad}
                onChange={(e) => setAutoridad(e.target.value)}
                placeholder="De dónde sale esta fuente"
              />
            </FormField>
            <FormField label="Prioridad">
              <TextInput value={prioridad} onChange={(e) => setPrioridad(e.target.value)} />
            </FormField>
            <AsyncButton onClick={crearFuente}>Crear fuente</AsyncButton>
          </div>
          <p className="mt-2 text-sm text-text-500">
            La prioridad decide qué fuente gana cuando dos cotizan lo mismo el mismo día. Menor
            número, antes.
          </p>
        </section>
      </Autorizado>

      <section className="mb-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Fuentes</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <caption className="sr-only">Fuentes de tasa</caption>
            <thead>
              <tr className="border-b border-border-default text-left text-text-700">
                <th scope="col" className="py-1">Código</th>
                <th scope="col">Nombre</th>
                <th scope="col">Tipo</th>
                <th scope="col">Prioridad</th>
                <th scope="col">Autoridad</th>
                <th scope="col">Última sincronización</th>
                <th scope="col">Estado</th>
                <th scope="col">Acción</th>
              </tr>
            </thead>
            <tbody>
              {(fuentes.data?.items ?? []).map((f) => (
                <tr key={f.id} className="border-b border-border-subtle">
                  <td className="py-1">{f.code}</td>
                  <td>{f.name}</td>
                  <td>{f.source_type}</td>
                  <td>{f.priority}</td>
                  <td>{f.authority_reference ?? "Sin declarar"}</td>
                  <td>
                    {f.provider_code
                      ? (f.last_success_at?.slice(0, 16).replace("T", " ") ?? "Nunca")
                      : "Sin proveedor"}
                    {f.last_error ? ` · ${f.last_error.slice(0, 40)}` : ""}
                  </td>
                  <td>{f.status === "ACTIVE" ? "Activa" : "Desactivada"}</td>
                  <td>
                    {puede("POST", "/treasury/rate-sources/_/status") && (
                      <AsyncButton size="sm" variant="secondary" onClick={() => cambiarEstado(f)}>
                        {f.status === "ACTIVE" ? "Desactivar" : "Activar"}
                      </AsyncButton>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <Autorizado operacion={["POST", "/treasury/rate-policies"]}>
        <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-2 text-base font-semibold text-text-900">
            Nueva política de resolución
          </h2>
          <div className="mb-3 flex flex-wrap items-end gap-3">
            <FormField label="Código" required>
              <TextInput
                value={politicaCodigo}
                onChange={(e) => setPoliticaCodigo(e.target.value)}
                placeholder="RES-GENERAL"
              />
            </FormField>
            <FormField label="Vigente desde" required>
              <TextInput type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
            </FormField>
            <FormField label="Antigüedad máxima (días)">
              <TextInput
                value={antiguedad}
                onChange={(e) => setAntiguedad(e.target.value)}
                placeholder="Vacío = sin tope"
              />
            </FormField>
          </div>
          <div className="mb-3 flex flex-wrap gap-4 text-sm">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={inversion}
                onChange={(e) => setInversion(e.target.checked)}
              />
              Permitir invertir el par
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={triangulacion}
                onChange={(e) => setTriangulacion(e.target.checked)}
              />
              Permitir triangular
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={aprobacion}
                onChange={(e) => setAprobacion(e.target.checked)}
              />
              Exigir aprobación de cada tasa
            </label>
          </div>
          <AsyncButton onClick={crearPolitica}>Crear en borrador</AsyncButton>
          <p className="mt-2 text-sm text-text-500">
            Invertir y triangular vienen denegados. Derivar una tasa de otra es una decisión
            económica, y queda marcada como derivada allí donde se use.
          </p>
        </section>
      </Autorizado>

      <section className="mb-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Políticas</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <caption className="sr-only">Políticas de resolución</caption>
            <thead>
              <tr className="border-b border-border-default text-left text-text-700">
                <th scope="col" className="py-1">Código</th>
                <th scope="col">Versión</th>
                <th scope="col">Invertir</th>
                <th scope="col">Triangular</th>
                <th scope="col">Antigüedad</th>
                <th scope="col">Aprobación</th>
                <th scope="col">Desde</th>
                <th scope="col">Estado</th>
                <th scope="col">Acción</th>
              </tr>
            </thead>
            <tbody>
              {(politicas.data?.items ?? []).map((p) => (
                <tr key={p.id} className="border-b border-border-subtle">
                  <td className="py-1">{p.policy_code}</td>
                  <td>v{p.version}</td>
                  <td>{p.allow_inversion ? "Sí" : "No"}</td>
                  <td>{p.allow_triangulation ? "Sí" : "No"}</td>
                  <td>{p.max_age_days === null ? "Sin tope" : `${p.max_age_days} días`}</td>
                  <td>{p.require_rate_approval ? "Obligatoria" : "No"}</td>
                  <td>{p.effective_from}</td>
                  <td>{p.status}</td>
                  <td>
                    {p.status === "DRAFT" && puede("POST", "/treasury/rate-policies/_/activate") ? (
                      <AsyncButton
                        size="sm"
                        variant="secondary"
                        onClick={() => activarPolitica(p)}
                      >
                        Activar
                      </AsyncButton>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="mb-2 text-base font-semibold text-text-900">Importaciones</h2>
        {(lotes.data?.items ?? []).length === 0 ? (
          <p className="text-sm text-text-700">Todavía no se ha importado ningún fichero.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <caption className="sr-only">Lotes de importación</caption>
              <thead>
                <tr className="border-b border-border-default text-left text-text-700">
                  <th scope="col" className="py-1">Fecha</th>
                  <th scope="col">Fichero</th>
                  <th scope="col">Filas</th>
                  <th scope="col">Importadas</th>
                  <th scope="col">Rechazadas</th>
                  <th scope="col">Estado</th>
                </tr>
              </thead>
              <tbody>
                {(lotes.data?.items ?? []).map((b) => (
                  <tr key={b.id} className="border-b border-border-subtle">
                    <td className="py-1">{b.created_at?.slice(0, 10) ?? "—"}</td>
                    <td>{b.filename ?? "—"}</td>
                    <td>{b.rows}</td>
                    <td>{b.imported}</td>
                    <td>{b.rejected}</td>
                    <td>{b.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </PageContent>
  );
}
