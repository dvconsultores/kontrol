/**
 * Tasas de cambio — Spec 013.
 *
 * Aquí vive la autoridad de la tasa: de qué fuente viene, qué par expresa y
 * desde cuándo rige. La 038 dejó de inventarlas y con eso quedó a la vista que
 * **nadie las registraba**; esta pantalla es donde se registran.
 *
 * Dos cosas que la pantalla dice en voz alta a propósito. La primera, qué
 * significa el número: **1 base = tasa quote**, escrito, porque «USD/VES» a
 * secas no dice si son cien bolívares por dólar o al revés. La segunda, que
 * corregir una tasa **no la reescribe**: crea la siguiente versión y la
 * anterior queda marcada, porque la operación que ya usó la vieja sigue
 * apuntando a ella.
 *
 * Ninguna regla legal venezolana está escrita aquí. La fuente se configura, se
 * le declara su autoridad y se puede desactivar sin perder su historia.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { ApiError, apiFetch } from "@/api/client";
import type {
  CurrencySummary,
  RateImportResult,
  RateObservation,
  RatePolicy,
  RateResolution,
  RateSource,
} from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { FormField } from "@/components/FormField";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";

const SELECT =
  "h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900";

const ESTADO: Record<string, string> = {
  ACTIVE: "Vigente",
  SUPERSEDED: "Sustituida",
  PENDING_APPROVAL: "Pendiente de aprobación",
  IDENTITY: "Identidad",
};

const DERIVACION: Record<string, string> = {
  INVERSE: "invertida",
  TRIANGULATION: "triangulada",
};

/**
 * Ahora, en hora local, con el formato que espera `datetime-local`.
 *
 * `toISOString()` da UTC, y el control lo lee como local: en Caracas o en
 * Madrid el campo aparecía desplazado horas respecto a la hora a la que la
 * persona está registrando la tasa, y esa hora es la vigencia.
 */
function ahoraLocal(): string {
  const d = new Date();
  const p = (n: number): string => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
}

export function TasasPage(): React.JSX.Element {
  const qc = useQueryClient();
  const { notify } = useNotifications();

  const [base, setBase] = useState("");
  const [quote, setQuote] = useState("");
  const [tasa, setTasa] = useState("");
  const [fuenteId, setFuenteId] = useState("");
  const [vigencia, setVigencia] = useState(ahoraLocal);
  const [motivo, setMotivo] = useState("");

  const [consultaBase, setConsultaBase] = useState("");
  const [consultaQuote, setConsultaQuote] = useState("");
  const [resuelta, setResuelta] = useState<RateResolution | null>(null);

  const [fichero, setFichero] = useState("");
  const [nombreFichero, setNombreFichero] = useState("");
  const [resultadoImport, setResultadoImport] = useState<RateImportResult | null>(null);

  const [pagina, setPagina] = useState(1);

  const monedas = useQuery({
    queryKey: ["tasas", "monedas"],
    queryFn: () => apiFetch<{ items: CurrencySummary[] }>("/treasury/currencies"),
  });

  const fuentes = useQuery({
    queryKey: ["tasas", "fuentes"],
    queryFn: () => apiFetch<{ items: RateSource[] }>("/treasury/rate-sources"),
  });

  const politicas = useQuery({
    queryKey: ["tasas", "politicas"],
    queryFn: () => apiFetch<{ items: RatePolicy[] }>("/treasury/rate-policies"),
  });

  // Paginado con `page`/`page_size`, que es el contrato real del endpoint. Un
  // `limit` inventado se ignora en silencio: es el defecto del selector de
  // almacén de la 031 y el del de clientes de la 037.
  const observaciones = useQuery({
    queryKey: ["tasas", "observaciones", pagina],
    queryFn: () =>
      apiFetch<{ items: RateObservation[]; total: number; page: number; page_size: number }>(
        `/treasury/exchange-rates/observations?page=${pagina}&page_size=50`,
      ),
  });

  const politicaActiva = (politicas.data?.items ?? []).find((p) => p.status === "ACTIVE");

  function fallo(titulo: string) {
    return (e: unknown) =>
      notify({
        type: "error",
        title: titulo,
        description: e instanceof ApiError ? e.message : undefined,
      });
  }

  async function refrescar(): Promise<void> {
    await qc.invalidateQueries({ queryKey: ["tasas"] });
  }

  async function registrar(): Promise<void> {
    // El importe no se cuela por `Number(...) || 0`: un valor que no es número
    // no es cero, y mandarlo como cero convertía un error de tecleo en una tasa.
    if (!base || !quote || !tasa.trim() || Number.isNaN(Number(tasa)) || Number(tasa) <= 0) {
      notify({ type: "error", title: "Indique el par y una tasa mayor que cero" });
      return;
    }
    if (base === quote) {
      notify({
        type: "error",
        title: "Una moneda no cotiza contra sí misma",
        description: "Eso es la identidad, no una tasa.",
      });
      return;
    }
    try {
      await apiFetch("/treasury/exchange-rates/observations", {
        method: "POST",
        body: {
          base_currency: base,
          quote_currency: quote,
          rate: tasa,
          effective_at: new Date(vigencia).toISOString(),
          source_id: fuenteId || null,
          reason: motivo || null,
        },
      });
      notify({
        type: "success",
        title: "Tasa registrada",
        description: `1 ${base} = ${tasa} ${quote}.`,
      });
      setTasa("");
      setMotivo("");
      setPagina(1);
      await refrescar();
    } catch (e) {
      fallo("No se pudo registrar la tasa")(e);
    }
  }

  async function resolver(): Promise<void> {
    if (!consultaBase || !consultaQuote) {
      notify({ type: "error", title: "Indique las dos monedas" });
      return;
    }
    try {
      const r = await apiFetch<RateResolution>(
        `/treasury/exchange-rates/resolve?base_currency=${consultaBase}&quote_currency=${consultaQuote}`,
      );
      setResuelta(r);
    } catch (e) {
      setResuelta(null);
      fallo("No hay tasa para ese par")(e);
    }
  }

  async function corregir(o: RateObservation): Promise<void> {
    const valor = window.prompt(
      `Nueva tasa para 1 ${o.base_currency} = ? ${o.quote_currency}`,
      o.rate,
    );
    if (!valor) return;
    const razon = window.prompt("Motivo de la corrección");
    if (!razon) {
      notify({ type: "error", title: "Corregir una tasa exige motivo" });
      return;
    }
    try {
      await apiFetch(`/treasury/exchange-rates/observations/${o.id}/correct`, {
        method: "POST",
        body: { rate: valor, reason: razon },
      });
      notify({
        type: "success",
        title: "Tasa corregida",
        description: "La anterior se conserva: lo que se creó es su versión siguiente.",
      });
      await refrescar();
    } catch (e) {
      fallo("No se pudo corregir la tasa")(e);
    }
  }

  async function aprobar(o: RateObservation): Promise<void> {
    try {
      await apiFetch(`/treasury/exchange-rates/observations/${o.id}/approve`, {
        method: "POST",
        body: {},
      });
      notify({ type: "success", title: "Tasa aprobada" });
      await refrescar();
    } catch (e) {
      fallo("No se pudo aprobar la tasa")(e);
    }
  }

  async function importar(): Promise<void> {
    if (!fuenteId || !fichero.trim()) {
      notify({ type: "error", title: "Indique la fuente y el contenido del fichero" });
      return;
    }
    try {
      const r = await apiFetch<RateImportResult>("/treasury/exchange-rates/import", {
        method: "POST",
        body: { source_id: fuenteId, content: fichero, filename: nombreFichero || "tasas.csv" },
      });
      setResultadoImport(r);
      notify({
        type: r.rejected > 0 ? "warning" : "success",
        title: `Importadas ${r.imported} de ${r.rows}`,
        description:
          r.rejected > 0 ? `${r.rejected} filas quedaron fuera, con su motivo.` : undefined,
      });
      setPagina(1);
      await refrescar();
    } catch (e) {
      setResultadoImport(null);
      fallo("No se pudo importar")(e);
    }
  }

  const total = observaciones.data?.total ?? 0;
  const tam = observaciones.data?.page_size ?? 50;
  const paginas = Math.max(1, Math.ceil(total / tam));

  return (
    <PageContent>
      <PageHeader
        title="Tasas de cambio"
        description="1 base = tasa quote. La tasa no se inventa: si falta, la operación se bloquea."
        crumbs={[{ label: "Tesorería" }, { label: "Tasas de cambio" }]}
      />

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Política de resolución</h2>
        {politicaActiva ? (
          <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm sm:grid-cols-3">
            <dt className="text-text-700">Política</dt>
            <dd>
              {politicaActiva.policy_code} · v{politicaActiva.version}
            </dd>
            <dt className="text-text-700">Invertir el par</dt>
            <dd>{politicaActiva.allow_inversion ? "Permitido" : "No permitido"}</dd>
            <dt className="text-text-700">Triangular</dt>
            <dd>
              {politicaActiva.allow_triangulation
                ? `Permitido por ${politicaActiva.triangulation_currency ?? "la moneda funcional"}`
                : "No permitido"}
            </dd>
            <dt className="text-text-700">Antigüedad máxima</dt>
            <dd>
              {politicaActiva.max_age_days === null
                ? "Sin tope"
                : `${politicaActiva.max_age_days} días`}
            </dd>
            <dt className="text-text-700">Aprobación de tasas</dt>
            <dd>{politicaActiva.require_rate_approval ? "Obligatoria" : "No exigida"}</dd>
            <dt className="text-text-700">Decimales de la tasa</dt>
            <dd>{politicaActiva.rate_scale}</dd>
          </dl>
        ) : (
          <p className="text-sm text-text-700" role="status">
            No hay política activa. Sin ella no se invierte ni se triangula: derivar una tasa es
            una decisión económica y el sistema no la toma solo.
          </p>
        )}
      </section>

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Registrar una tasa</h2>
        <div className="mb-3 flex flex-wrap items-end gap-3">
          <FormField label="Moneda base" required>
            <select
              value={base}
              onChange={(e) => setBase(e.target.value)}
              className={SELECT}
              aria-label="Moneda base"
            >
              <option value="">Seleccionar…</option>
              {(monedas.data?.items ?? []).map((m) => (
                <option key={m.id} value={m.code}>
                  {m.code}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Moneda cotizada" required>
            <select
              value={quote}
              onChange={(e) => setQuote(e.target.value)}
              className={SELECT}
              aria-label="Moneda cotizada"
            >
              <option value="">Seleccionar…</option>
              {(monedas.data?.items ?? []).map((m) => (
                <option key={m.id} value={m.code}>
                  {m.code}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Tasa" required>
            <TextInput
              value={tasa}
              onChange={(e) => setTasa(e.target.value)}
              placeholder="0.000000"
            />
          </FormField>
          <FormField label="Vigente desde" required>
            <TextInput
              type="datetime-local"
              value={vigencia}
              onChange={(e) => setVigencia(e.target.value)}
            />
          </FormField>
          <FormField label="Fuente">
            <select
              value={fuenteId}
              onChange={(e) => setFuenteId(e.target.value)}
              className={SELECT}
              aria-label="Fuente"
            >
              <option value="">Sin declarar…</option>
              {(fuentes.data?.items ?? [])
                .filter((f) => f.status === "ACTIVE")
                .map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.code} · {f.name}
                  </option>
                ))}
            </select>
          </FormField>
          <FormField label="Motivo">
            <TextInput
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              placeholder="Opcional"
            />
          </FormField>
          <AsyncButton onClick={registrar}>Registrar</AsyncButton>
        </div>
        <p className="text-sm text-text-500" role="status">
          {base && quote && tasa
            ? `Significa: 1 ${base} = ${tasa} ${quote}.`
            : "1 unidad de la base equivale a la tasa en unidades de la cotizada."}
        </p>
      </section>

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Consultar</h2>
        <div className="mb-3 flex flex-wrap items-end gap-3">
          <FormField label="Convertir de" required>
            <select
              value={consultaBase}
              onChange={(e) => setConsultaBase(e.target.value)}
              className={SELECT}
              aria-label="Convertir de"
            >
              <option value="">Seleccionar…</option>
              {(monedas.data?.items ?? []).map((m) => (
                <option key={m.id} value={m.code}>
                  {m.code}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Convertir a" required>
            <select
              value={consultaQuote}
              onChange={(e) => setConsultaQuote(e.target.value)}
              className={SELECT}
              aria-label="Convertir a"
            >
              <option value="">Seleccionar…</option>
              {(monedas.data?.items ?? []).map((m) => (
                <option key={m.id} value={m.code}>
                  {m.code}
                </option>
              ))}
            </select>
          </FormField>
          <AsyncButton variant="secondary" onClick={resolver}>
            Resolver
          </AsyncButton>
        </div>
        {resuelta ? (
          <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm sm:grid-cols-3">
            <dt className="text-text-700">Significa</dt>
            <dd className="font-mono">{resuelta.meaning}</dd>
            <dt className="text-text-700">Procedencia</dt>
            <dd>
              {resuelta.identity
                ? "Identidad de la misma moneda"
                : (resuelta.source_code ?? "—")}
              {resuelta.derived ? ` · tasa ${DERIVACION[resuelta.derived] ?? resuelta.derived}` : ""}
            </dd>
            <dt className="text-text-700">Vigente desde</dt>
            <dd>{resuelta.effective_at?.slice(0, 16).replace("T", " ") ?? "—"}</dd>
          </dl>
        ) : (
          <p className="text-sm text-text-500">
            Si no hay tasa para ese par, la consulta lo dice. No se supone un uno a uno.
          </p>
        )}
      </section>

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Importar</h2>
        <p className="mb-2 text-sm text-text-500">
          Columnas: <code>base_currency, quote_currency, rate, effective_at</code>. Reimportar el
          mismo fichero no duplica nada, y ninguna fila inválida se descarta en silencio.
        </p>
        <div className="mb-3 flex flex-wrap items-end gap-3">
          <FormField label="Fuente" required>
            <select
              value={fuenteId}
              onChange={(e) => setFuenteId(e.target.value)}
              className={SELECT}
              aria-label="Fuente del fichero"
            >
              <option value="">Seleccionar…</option>
              {(fuentes.data?.items ?? [])
                .filter((f) => f.status === "ACTIVE")
                .map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.code} · {f.name}
                  </option>
                ))}
            </select>
          </FormField>
          <FormField label="Nombre del fichero">
            <TextInput
              value={nombreFichero}
              onChange={(e) => setNombreFichero(e.target.value)}
              placeholder="tasas.csv"
            />
          </FormField>
          <AsyncButton onClick={importar}>Importar</AsyncButton>
        </div>
        <FormField label="Contenido">
          <textarea
            value={fichero}
            onChange={(e) => setFichero(e.target.value)}
            aria-label="Contenido"
            rows={4}
            className="w-full rounded-md border border-border-default bg-surface-0 p-3 font-mono text-xs text-text-900"
            placeholder="base_currency,quote_currency,rate,effective_at"
          />
        </FormField>
        {resultadoImport && resultadoImport.errors.length > 0 ? (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-sm">
              <caption className="sr-only">Filas rechazadas</caption>
              <thead>
                <tr className="border-b border-border-default text-left text-text-700">
                  <th scope="col" className="py-1">Fila</th>
                  <th scope="col">Motivo</th>
                </tr>
              </thead>
              <tbody>
                {resultadoImport.errors.map((e) => (
                  <tr key={`${e.row}-${e.code}`} className="border-b border-border-subtle">
                    <td className="py-1">{e.row}</td>
                    <td>{e.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      <section>
        <h2 className="mb-2 text-base font-semibold text-text-900">Histórico</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <caption className="sr-only">Observaciones de tasa</caption>
            <thead>
              <tr className="border-b border-border-default text-left text-text-700">
                <th scope="col" className="py-1">Vigente desde</th>
                <th scope="col">Par</th>
                <th scope="col">Tasa</th>
                <th scope="col">Fuente</th>
                <th scope="col">Versión</th>
                <th scope="col">Estado</th>
                <th scope="col">Acción</th>
              </tr>
            </thead>
            <tbody>
              {(observaciones.data?.items ?? []).map((o) => (
                <tr key={o.id} className="border-b border-border-subtle">
                  <td className="py-1">
                    {o.effective_at?.slice(0, 16).replace("T", " ") ?? "—"}
                  </td>
                  <td>
                    {o.base_currency ?? "—"} → {o.quote_currency ?? "—"}
                  </td>
                  <td className="font-mono">{o.rate}</td>
                  <td>{o.source_code ?? "—"}</td>
                  <td>v{o.version}</td>
                  <td>{ESTADO[o.status] ?? o.status}</td>
                  <td className="flex flex-wrap gap-2 py-1">
                    {o.status === "ACTIVE" ? (
                      <AsyncButton size="sm" variant="secondary" onClick={() => corregir(o)}>
                        Corregir
                      </AsyncButton>
                    ) : null}
                    {o.status === "PENDING_APPROVAL" ? (
                      <AsyncButton size="sm" onClick={() => aprobar(o)}>
                        Aprobar
                      </AsyncButton>
                    ) : null}
                    {o.status !== "ACTIVE" && o.status !== "PENDING_APPROVAL" ? "—" : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-3 flex items-center gap-3 text-sm">
          <AsyncButton
            size="sm"
            variant="secondary"
            disabled={pagina <= 1}
            onClick={async () => setPagina((p) => Math.max(1, p - 1))}
          >
            Anterior
          </AsyncButton>
          <span className="text-text-700">
            Página {observaciones.data?.page ?? pagina} de {paginas} · {total} observaciones
          </span>
          <AsyncButton
            size="sm"
            variant="secondary"
            disabled={pagina >= paginas}
            onClick={async () => setPagina((p) => p + 1)}
          >
            Siguiente
          </AsyncButton>
        </div>
        <p className="mt-2 text-sm text-text-500">
          Corregir una tasa no la reescribe: crea su versión siguiente. La operación que usó la
          anterior sigue apuntando a la anterior.
        </p>
      </section>
    </PageContent>
  );
}
