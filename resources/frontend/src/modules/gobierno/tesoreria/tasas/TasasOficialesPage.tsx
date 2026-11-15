import { useState } from "react";
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { TextInput } from "@/components/TextInput";
import { FormField } from "@/components/FormField";
import { Button } from "@/components/Button";
import { AsyncButton } from "@/components/AsyncButton";
import { AdjuntosPanel } from "@/modules/documentos/AdjuntosPanel";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_TASAS,
  ETIQUETAS_ESTADO_TASA,
  consultaDeTasas,
  normalizarTasa,
  expresionTasa,
} from "./api";
import type {
  TasaOficial,
  TasaOficialDetalle,
  TasasOficialesVista,
  FiltrosTasas,
} from "./api";

const MONEDAS = ["USD", "EUR"] as const;

export function TasasOficialesPage(): React.JSX.Element {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();

  const puedeVer = tiene("gobierno_tasas:view", "empresa");
  const puedeGestionar = tiene("gobierno_tasas:manage", "empresa");
  const puedeAprobar = tiene("gobierno_tasas:approve", "empresa");

  const [filtroMoneda, setFiltroMoneda] = useState("");
  const [filtroEstado, setFiltroEstado] = useState("");
  const [filtroDesde, setFiltroDesde] = useState("");
  const [filtroHasta, setFiltroHasta] = useState("");
  const [seleccionada, setSeleccionada] = useState<string | null>(null);

  const [moneda, setMoneda] = useState("");
  const [fechaEfectiva, setFechaEfectiva] = useState("");
  const [valor, setValor] = useState("");
  const [fuenteReferencia, setFuenteReferencia] = useState("");
  const [publicadaEn, setPublicadaEn] = useState("");
  const [erroresRegistro, setErroresRegistro] = useState<Record<string, string[]>>({});
  const [errorRegistro, setErrorRegistro] = useState<string | null>(null);

  const [nuevoValor, setNuevoValor] = useState("");
  const [nuevaReferencia, setNuevaReferencia] = useState("");
  const [motivoCorreccion, setMotivoCorreccion] = useState("");
  const [nuevaPublicadaEn, setNuevaPublicadaEn] = useState("");
  const [erroresCorreccion, setErroresCorreccion] = useState<Record<string, string[]>>({});

  const [motivoAnulacion, setMotivoAnulacion] = useState("");

  const filtros: FiltrosTasas = {
    ...(filtroMoneda ? { moneda: filtroMoneda } : {}),
    ...(filtroEstado ? { estado: filtroEstado } : {}),
    ...(filtroDesde ? { desde: filtroDesde } : {}),
    ...(filtroHasta ? { hasta: filtroHasta } : {}),
  };

  const consultaTasas = useQuery({
    queryKey: [...CONSULTA_TASAS, "tasas", activeCompanyId, filtros],
    queryFn: () =>
      apiFetch<TasasOficialesVista>(
        `/gobierno/tesoreria/tasas${consultaDeTasas(filtros)}`,
      ),
    enabled: puedeVer && Boolean(activeCompanyId),
    placeholderData: keepPreviousData,
    retry: false,
  });

  const consultaDetalle = useQuery({
    queryKey: [...CONSULTA_TASAS, "detalle", seleccionada],
    queryFn: () =>
      apiFetch<TasaOficialDetalle>(
        `/gobierno/tesoreria/tasas/${seleccionada}`,
      ),
    enabled: Boolean(seleccionada),
    retry: false,
  });

  const registrarTasa = useMutation({
    mutationFn: (entrada: {
      moneda: string;
      fecha_efectiva: string;
      valor: string;
      fuente_referencia: string;
      publicada_en: string | null;
    }) =>
      apiFetch<TasaOficial>(`/gobierno/tesoreria/tasas`, {
        method: "POST",
        body: entrada,
      }),
    onSuccess: (tasa) => {
      setMoneda("");
      setFechaEfectiva("");
      setValor("");
      setFuenteReferencia("");
      setPublicadaEn("");
      setErroresRegistro({});
      setErrorRegistro(null);
      setSeleccionada(tasa.id);
      void queryClient.invalidateQueries({ queryKey: CONSULTA_TASAS });
      notify({
        type: "success",
        title:
          "Tasa registrada en borrador: adjunte la evidencia del BCV y pida la aprobación a otro usuario.",
      });
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError) {
        if (error.status === 422 && error.fieldErrors) {
          setErroresRegistro(error.fieldErrors);
          return;
        }
        setErrorRegistro(error.message);
      }
    },
  });

  const aprobarTasa = useMutation({
    mutationFn: (id: string) =>
      apiFetch<TasaOficial>(`/gobierno/tesoreria/tasas/${id}/aprobar`, {
        method: "POST",
        body: {},
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: CONSULTA_TASAS });
      notify({ type: "success", title: "Tasa aprobada" });
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError) {
        notify({ type: "error", title: error.message });
      }
    },
  });

  const corregirTasa = useMutation({
    mutationFn: ({
      id,
      entrada,
    }: {
      id: string;
      entrada: {
        valor: string;
        fuente_referencia: string;
        publicada_en: string | null;
        motivo: string;
      };
    }) =>
      apiFetch<TasaOficial>(`/gobierno/tesoreria/tasas/${id}/correccion`, {
        method: "POST",
        body: entrada,
      }),
    onSuccess: (tasa) => {
      setNuevoValor("");
      setNuevaReferencia("");
      setMotivoCorreccion("");
      setNuevaPublicadaEn("");
      setErroresCorreccion({});
      setSeleccionada(tasa.id);
      void queryClient.invalidateQueries({ queryKey: CONSULTA_TASAS });
      notify({ type: "success", title: "Corrección registrada en borrador" });
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError) {
        if (error.status === 422 && error.fieldErrors) {
          setErroresCorreccion(error.fieldErrors);
          return;
        }
        notify({ type: "error", title: error.message });
      }
    },
  });

  const anularTasa = useMutation({
    mutationFn: ({ id, motivo }: { id: string; motivo: string }) =>
      apiFetch<TasaOficial>(`/gobierno/tesoreria/tasas/${id}/anular`, {
        method: "POST",
        body: { motivo },
      }),
    onSuccess: () => {
      setMotivoAnulacion("");
      void queryClient.invalidateQueries({ queryKey: CONSULTA_TASAS });
      notify({ type: "success", title: "Tasa anulada" });
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError) {
        notify({ type: "error", title: error.message });
      }
    },
  });

  const cabecera = (
    <PageHeader
      crumbs={[
        { label: "Gobierno", to: "/gobierno" },
        { label: "Tesorería", to: "/gobierno/tesoreria/cuentas" },
        { label: "Tasas oficiales" },
      ]}
      title="Tasas oficiales"
      description="Tasas oficiales del BCV con procedencia verificable (1 unidad de moneda extranjera = X VES). Solo una tasa aprobada por otro usuario sirve para comparar límites; una operación registrada nunca se recalcula."
    />
  );

  if (!puedeVer) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para ver las tasas oficiales."
        />
      </PageContent>
    );
  }

  if (consultaTasas.isLoading) {
    return (
      <PageContent>
        {cabecera}
        <LoadingState label="Cargando tasas…" />
      </PageContent>
    );
  }

  if (consultaTasas.isError || !consultaTasas.data) {
    return (
      <PageContent>
        {cabecera}
        <ErrorState title="No fue posible cargar las tasas oficiales." message="Vuelva a intentarlo en unos minutos." />
      </PageContent>
    );
  }

  const tasas = consultaTasas.data.items;
  const detalle = consultaDetalle.data;

  return (
    <PageContent>
      {cabecera}
      <div className="flex flex-wrap items-center gap-2">
        <select
          className="h-10 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
          value={filtroMoneda}
          onChange={(event) => setFiltroMoneda(event.target.value)}
          aria-label="Moneda"
        >
          <option value="">Todas</option>
          {MONEDAS.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
        <select
          className="h-10 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
          value={filtroEstado}
          onChange={(event) => setFiltroEstado(event.target.value)}
          aria-label="Estado"
        >
          <option value="">Todos</option>
          {Object.entries(ETIQUETAS_ESTADO_TASA).map(([valor, etiqueta]) => (
            <option key={valor} value={valor}>
              {etiqueta}
            </option>
          ))}
        </select>
        <input
          type="date"
          className="h-10 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
          value={filtroDesde}
          onChange={(event) => setFiltroDesde(event.target.value)}
          aria-label="Desde"
        />
        <input
          type="date"
          className="h-10 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
          value={filtroHasta}
          onChange={(event) => setFiltroHasta(event.target.value)}
          aria-label="Hasta"
        />
      </div>

      {puedeGestionar ? (
        <>
          <h2>Registrar tasa</h2>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              registrarTasa.mutate({
                moneda,
                fecha_efectiva: fechaEfectiva,
                valor: normalizarTasa(valor),
                fuente_referencia: fuenteReferencia,
                publicada_en: publicadaEn || null,
              });
            }}
          >
            <FormField
              label="Moneda"
              required
              error={erroresRegistro.moneda?.[0]}
            >
              <select
                className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                value={moneda}
                onChange={(event) => setMoneda(event.target.value)}
              >
                <option value="">Seleccione…</option>
                {MONEDAS.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </FormField>
            <FormField
              label="Fecha efectiva"
              required
              error={erroresRegistro.fecha_efectiva?.[0]}
            >
              <input
                type="date"
                className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                value={fechaEfectiva}
                onChange={(event) => setFechaEfectiva(event.target.value)}
              />
            </FormField>
            <FormField
              label="Valor en VES por unidad"
              required
              error={erroresRegistro.valor?.[0]}
            >
              <TextInput
                value={valor}
                onChange={(evento) => setValor(evento.target.value)}
                inputMode="decimal"
              />
            </FormField>
            <FormField
              label="Referencia oficial del BCV"
              required
              error={erroresRegistro.fuente_referencia?.[0]}
            >
              <TextInput
                value={fuenteReferencia}
                onChange={(evento) => setFuenteReferencia(evento.target.value)}
              />
            </FormField>
            <FormField
              label="Fecha de publicación"
              error={erroresRegistro.publicada_en?.[0]}
            >
              <input
                type="date"
                className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                value={publicadaEn}
                onChange={(event) => setPublicadaEn(event.target.value)}
              />
            </FormField>
            {errorRegistro ? <p role="alert">{errorRegistro}</p> : null}
            <Button type="submit">Registrar tasa</Button>
          </form>
        </>
      ) : null}

      <div role="region" aria-label="Tabla de tasas oficiales">
        {tasas.length === 0 ? (
          <p>Sin tasas registradas.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th>Fecha efectiva</th>
                <th>Moneda</th>
                <th>Tasa</th>
                <th>Fuente</th>
                <th>Referencia</th>
                <th>Estado</th>
                <th>Versión</th>
                <th>Capturada por</th>
                <th>Aprobada por</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {tasas.map((tasa) => (
                <tr key={tasa.id}>
                  <td>{formatearFechaDeNegocio(tasa.fecha_efectiva)}</td>
                  <td>{tasa.moneda}</td>
                  <td>{expresionTasa(tasa)}</td>
                  <td>{tasa.fuente}</td>
                  <td>{tasa.fuente_referencia}</td>
                  <td>{ETIQUETAS_ESTADO_TASA[tasa.estado]}</td>
                  <td>{tasa.version}</td>
                  <td>{tasa.capturada_por}</td>
                  <td>{tasa.aprobada_por ?? "—"}</td>
                  <td>
                    <Button
                      variant="secondary"
                      onClick={() => setSeleccionada(tasa.id)}
                    >
                      {`Ver ${tasa.moneda} ${formatearFechaDeNegocio(tasa.fecha_efectiva)} v${tasa.version}`}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {seleccionada && detalle ? (
        <section aria-labelledby="detalle-tasa">
          <h2 id="detalle-tasa">
            {`Tasa ${detalle.moneda} del ${formatearFechaDeNegocio(detalle.fecha_efectiva)} · versión ${detalle.version}`}
          </h2>
          <p className="text-lg font-semibold">{expresionTasa(detalle)}</p>
          <dl>
            <dt>Fuente</dt>
            <dd>{detalle.fuente}</dd>
            <dt>Fecha efectiva</dt>
            <dd>{formatearFechaDeNegocio(detalle.fecha_efectiva)}</dd>
            <dt>Fecha de publicación</dt>
            <dd>
              {detalle.publicada_en
                ? formatearFechaDeNegocio(detalle.publicada_en)
                : "—"}
            </dd>
            <dt>Referencia oficial</dt>
            <dd>{detalle.fuente_referencia}</dd>
            <dt>Estado</dt>
            <dd>{ETIQUETAS_ESTADO_TASA[detalle.estado]}</dd>
            <dt>Capturada por</dt>
            <dd>{detalle.capturada_por}</dd>
            <dt>Aprobada por</dt>
            <dd>{detalle.aprobada_por ?? "Pendiente de aprobación"}</dd>
            <dt>Huella de la evidencia</dt>
            <dd>{detalle.evidencia_sha256 ?? "Sin evidencia aprobada"}</dd>
            {detalle.motivo_correccion ? (
              <>
                <dt>Motivo de la corrección</dt>
                <dd>{detalle.motivo_correccion}</dd>
              </>
            ) : null}
            {detalle.motivo_anulacion ? (
              <>
                <dt>Motivo de anulación</dt>
                <dd>{detalle.motivo_anulacion}</dd>
              </>
            ) : null}
          </dl>
          <h3>Historia de versiones</h3>
          <ul>
            {detalle.historia.map((version) => (
              <li key={version.id}>
                {`Versión ${version.version} · ${expresionTasa(version)} · ${ETIQUETAS_ESTADO_TASA[version.estado]}`}
              </li>
            ))}
          </ul>
          <AdjuntosPanel
            resourceType="GovernmentOfficialExchangeRate"
            resourceId={detalle.id}
            title="Evidencia oficial del BCV"
            onChange={() =>
              void queryClient.invalidateQueries({ queryKey: CONSULTA_TASAS })
            }
          />
          {detalle.estado === "BORRADOR" && puedeAprobar ? (
            <AsyncButton
              idleText="Aprobar tasa"
              onClick={async () => {
                await aprobarTasa.mutateAsync(detalle.id);
                void queryClient.invalidateQueries({ queryKey: CONSULTA_TASAS });
              }}
            />
          ) : null}
          {detalle.estado === "APROBADA" && puedeGestionar ? (
            <>
              <h3>Corregir con una nueva versión</h3>
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  corregirTasa.mutate({
                    id: detalle.id,
                    entrada: {
                      valor: normalizarTasa(nuevoValor),
                      fuente_referencia: nuevaReferencia,
                      publicada_en: nuevaPublicadaEn || null,
                      motivo: motivoCorreccion,
                    },
                  });
                }}
              >
                <FormField
                  label="Nuevo valor en VES por unidad"
                  required
                  error={erroresCorreccion.valor?.[0]}
                >
                  <TextInput
                    value={nuevoValor}
                    onChange={(evento) => setNuevoValor(evento.target.value)}
                    inputMode="decimal"
                  />
                </FormField>
                <FormField
                  label="Referencia oficial del BCV de la corrección"
                  required
                  error={erroresCorreccion.fuente_referencia?.[0]}
                >
                  <TextInput
                    value={nuevaReferencia}
                    onChange={(evento) => setNuevaReferencia(evento.target.value)}
                  />
                </FormField>
                <FormField
                  label="Motivo de la corrección"
                  required
                  error={erroresCorreccion.motivo?.[0]}
                >
                  <TextInput
                    value={motivoCorreccion}
                    onChange={(evento) => setMotivoCorreccion(evento.target.value)}
                  />
                </FormField>
                <FormField
                  label="Fecha de publicación de la corrección"
                  error={erroresCorreccion.publicada_en?.[0]}
                >
                  <input
                    type="date"
                    className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                    value={nuevaPublicadaEn}
                    onChange={(event) => setNuevaPublicadaEn(event.target.value)}
                  />
                </FormField>
                <Button type="submit">Registrar corrección</Button>
              </form>
            </>
          ) : null}
          {(detalle.estado === "BORRADOR" || detalle.estado === "APROBADA") &&
          puedeAprobar ? (
            <div className="flex items-center gap-2">
              <TextInput
                value={motivoAnulacion}
                onChange={(evento) => setMotivoAnulacion(evento.target.value)}
                aria-label="Motivo de anulación"
              />
              <AsyncButton
                idleText="Anular tasa"
                onClick={async () => {
                  await anularTasa.mutateAsync({
                    id: detalle.id,
                    motivo: motivoAnulacion,
                  });
                  void queryClient.invalidateQueries({ queryKey: CONSULTA_TASAS });
                }}
              />
            </div>
          ) : null}
        </section>
      ) : null}
    </PageContent>
  );
}
