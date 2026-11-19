import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_MEDIOS_PAGO,
  CONSULTA_POLITICAS_PAGO,
  ESTADOS_POLITICA_PAGO,
  RUTA_CONFIG_PAGOS,
  RUTA_MEDIOS_PAGO,
  RUTA_POLITICAS_PAGO,
  type ConfiguracionPagos,
  type MedioPago,
  type PoliticaPagoResumen,
} from "./api";

interface FormularioMedio {
  codigo: string;
  nombre: string;
  vigente_desde: string;
  exige_referencia: boolean;
  referencia_unica: boolean;
  patron_referencia: string;
  fundamento: string;
}

const FORMULARIO_MEDIO_INICIAL: FormularioMedio = {
  codigo: "",
  nombre: "",
  vigente_desde: "",
  exige_referencia: false,
  referencia_unica: false,
  patron_referencia: "",
  fundamento: "",
};

export function PoliticasPagoPage() {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const { notify } = useNotifications();
  const puedeVer = tiene("gobierno_pagos:view", "empresa");
  const puedeGestionar = tiene("gobierno_pagos:policy", "empresa");
  const [patron, setPatron] = useState("");
  const [patronError, setPatronError] = useState<string | null>(null);
  const [guardandoPatron, setGuardandoPatron] = useState(false);
  const patronPrecargado = useRef(false);
  const [formularioMedio, setFormularioMedio] = useState<FormularioMedio>(
    FORMULARIO_MEDIO_INICIAL,
  );
  const [errorMedio, setErrorMedio] = useState<string | null>(null);
  const [guardandoMedio, setGuardandoMedio] = useState(false);
  const [cambiandoEstado, setCambiandoEstado] = useState<string | null>(null);

  const configuracion = useQuery({
    queryKey: [...CONSULTA_POLITICAS_PAGO, "configuracion", activeCompanyId],
    queryFn: () => apiFetch<ConfiguracionPagos>(RUTA_CONFIG_PAGOS),
    enabled: Boolean(activeCompanyId) && puedeVer,
    retry: false,
  });

  const politicas = useQuery({
    queryKey: [...CONSULTA_POLITICAS_PAGO, "politicas", activeCompanyId],
    queryFn: () => apiFetch<PoliticaPagoResumen[]>(RUTA_POLITICAS_PAGO),
    enabled: Boolean(activeCompanyId) && puedeVer,
    retry: false,
  });

  const medios = useQuery({
    queryKey: [...CONSULTA_MEDIOS_PAGO, activeCompanyId],
    queryFn: () => apiFetch<MedioPago[]>(RUTA_MEDIOS_PAGO),
    enabled: Boolean(activeCompanyId) && puedeVer,
    retry: false,
  });

  useEffect(() => {
    if (configuracion.data?.patron && patron === "" && !patronPrecargado.current) {
      setPatron(configuracion.data.patron);
      patronPrecargado.current = true;
    }
  }, [configuracion.data, patron]);

  const cabecera = (
    <PageHeader
      crumbs={[{ label: "Gobierno" }, { label: "Políticas de pago" }]}
      title="Políticas de pago"
      description="Reglas, medios y numeración para registrar pagos de órdenes emitidas."
      actions={
        puedeGestionar ? (
          <Link
            to={`${RUTA_POLITICAS_PAGO}/nueva`}
            className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
          >
            Nueva política
          </Link>
        ) : null
      }
    />
  );

  if (!puedeVer) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para ver las políticas de pago."
        />
      </PageContent>
    );
  }

  const guardarPatron = async () => {
    if (guardandoPatron) return;
    setPatronError(null);
    const version = configuracion.data?.version ?? 0;
    setGuardandoPatron(true);
    try {
      await apiFetch<ConfiguracionPagos>(RUTA_CONFIG_PAGOS, {
        method: "PUT",
        body: { patron },
        ifMatch: String(version),
      });
      notify({ type: "success", title: "Patrón guardado" });
      await configuracion.refetch();
    } catch (error) {
      if (error instanceof ApiError && error.fieldErrors?.patron) {
        setPatronError(error.fieldErrors.patron.join(" "));
      } else if (error instanceof ApiError) {
        setPatronError(error.message);
      } else {
        setPatronError("No fue posible guardar el patrón.");
      }
    } finally {
      setGuardandoPatron(false);
    }
  };

  const guardarMedio = async () => {
    if (guardandoMedio) return;
    setErrorMedio(null);
    setGuardandoMedio(true);
    try {
      await apiFetch<MedioPago>(RUTA_MEDIOS_PAGO, {
        method: "POST",
        body: {
          codigo: formularioMedio.codigo,
          nombre: formularioMedio.nombre,
          vigente_desde: formularioMedio.vigente_desde,
          exige_referencia: formularioMedio.exige_referencia,
          referencia_unica: formularioMedio.referencia_unica,
          patron_referencia: formularioMedio.patron_referencia || null,
          fundamento: formularioMedio.fundamento || null,
        },
      });
      notify({ type: "success", title: "Medio de pago creado" });
      setFormularioMedio(FORMULARIO_MEDIO_INICIAL);
      await medios.refetch();
    } catch (error) {
      if (error instanceof ApiError) {
        setErrorMedio(error.message);
      } else {
        setErrorMedio("No fue posible crear el medio de pago.");
      }
    } finally {
      setGuardandoMedio(false);
    }
  };

  const cambiarEstadoMedio = async (medio: MedioPago) => {
    if (cambiandoEstado) return;
    setCambiandoEstado(medio.id);
    const nuevoEstado = medio.estado === "ACTIVO" ? "INACTIVO" : "ACTIVO";
    try {
      await apiFetch<MedioPago>(`${RUTA_MEDIOS_PAGO}/${medio.id}`, {
        method: "PUT",
        body: { estado: nuevoEstado },
        ifMatch: String(medio.version),
      });
      notify({
        type: "success",
        title: nuevoEstado === "ACTIVO" ? "Medio activado" : "Medio desactivado",
      });
      await medios.refetch();
    } catch (error) {
      if (error instanceof ApiError) {
        notify({
          type: "error",
          title: "No fue posible cambiar el estado",
          description: error.message,
        });
      } else {
        notify({ type: "error", title: "No fue posible cambiar el estado" });
      }
    } finally {
      setCambiandoEstado(null);
    }
  };

  if (politicas.isLoading || medios.isLoading || configuracion.isLoading) {
    return (
      <PageContent>
        {cabecera}
        <LoadingState label="Cargando políticas de pago…" />
      </PageContent>
    );
  }

  if (politicas.isError || medios.isError) {
    const error = politicas.error ?? medios.error;
    if (error instanceof ApiError && error.status === 403) {
      return (
        <PageContent>
          {cabecera}
          <EmptyState
            title="Sin acceso"
            description="No tiene permiso para ver las políticas de pago."
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        {cabecera}
        <ErrorState
          message="No fue posible cargar las políticas de pago."
          onRetry={() => {
            void politicas.refetch();
            void medios.refetch();
          }}
        />
      </PageContent>
    );
  }

  if (!politicas.data || !medios.data) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState title="Aún no hay datos" description="No fue posible cargar la información." />
      </PageContent>
    );
  }

  return (
    <PageContent>
      {cabecera}

      <section aria-labelledby="politicas-titulo" className="mb-10">
        <h2 id="politicas-titulo" className="text-lg font-semibold text-text-900">
          Políticas
        </h2>
        {politicas.data.length === 0 ? (
          <EmptyState
            title="Aún no hay políticas de pago"
            description="Cada ente define sus medios de pago, bandas de aprobación y documentos exigidos para registrar pagos."
          />
        ) : (
          <div
            className="relative overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Tabla de políticas de pago"
          >
            <table className="w-full min-w-[760px] border-collapse text-sm">
              <caption className="sr-only">Políticas de pago</caption>
              <thead>
                <tr className="border-b border-border-default text-left text-text-600">
                  <th scope="col" className="px-3 py-2 font-medium">
                    Código
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Versión
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Nombre
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Moneda
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Estado
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Vigencia
                  </th>
                </tr>
              </thead>
              <tbody>
                {politicas.data.map((politica) => (
                  <tr key={politica.id} className="border-b border-border-subtle align-top">
                    <td className="px-3 py-2">
                      <Link
                        to={`${RUTA_POLITICAS_PAGO}/${politica.id}`}
                        aria-label={`Abrir la política ${politica.codigo}`}
                        className="font-medium text-brand-700 underline"
                      >
                        {politica.codigo}
                      </Link>
                    </td>
                    <td className="px-3 py-2">v{politica.numero_version}</td>
                    <td className="px-3 py-2 text-text-900">{politica.nombre}</td>
                    <td className="px-3 py-2">{politica.moneda}</td>
                    <td className="px-3 py-2">{ESTADOS_POLITICA_PAGO[politica.estado]}</td>
                    <td className="px-3 py-2">
                      {formatearFechaDeNegocio(politica.vigente_desde)}
                      {politica.vigente_hasta
                        ? ` – ${formatearFechaDeNegocio(politica.vigente_hasta)}`
                        : ""}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section aria-labelledby="medios-titulo" className="mb-10">
        <h2 id="medios-titulo" className="text-lg font-semibold text-text-900">
          Medios de pago
        </h2>
        <p className="mt-1 text-sm text-text-600">
          KONTROL no trae medios precargados: cada ente registra los que tiene autorizados.
        </p>
        {puedeGestionar ? (
          <form
            className="mt-4 grid gap-3 rounded-lg border border-border-subtle p-4 sm:grid-cols-2"
            onSubmit={(evento) => {
              evento.preventDefault();
              void guardarMedio();
            }}
          >
            <FormField label="Código" htmlFor="medio-codigo">
              <TextInput
                id="medio-codigo"
                value={formularioMedio.codigo}
                onChange={(evento) =>
                  setFormularioMedio((previo) => ({ ...previo, codigo: evento.target.value }))
                }
              />
            </FormField>
            <FormField label="Nombre" htmlFor="medio-nombre">
              <TextInput
                id="medio-nombre"
                value={formularioMedio.nombre}
                onChange={(evento) =>
                  setFormularioMedio((previo) => ({ ...previo, nombre: evento.target.value }))
                }
              />
            </FormField>
            <FormField label="Vigente desde" htmlFor="medio-vigente-desde">
              <TextInput
                id="medio-vigente-desde"
                type="date"
                value={formularioMedio.vigente_desde}
                onChange={(evento) =>
                  setFormularioMedio((previo) => ({
                    ...previo,
                    vigente_desde: evento.target.value,
                  }))
                }
              />
            </FormField>
            <FormField
              label="Patrón de referencia"
              htmlFor="medio-patron"
              help="Expresión regular opcional que define el ente"
            >
              <TextInput
                id="medio-patron"
                value={formularioMedio.patron_referencia}
                onChange={(evento) =>
                  setFormularioMedio((previo) => ({
                    ...previo,
                    patron_referencia: evento.target.value,
                  }))
                }
              />
            </FormField>
            <div className="flex flex-wrap items-center gap-4">
              <label className="flex items-center gap-2 text-sm text-text-700">
                <input
                  type="checkbox"
                  checked={formularioMedio.exige_referencia}
                  onChange={(evento) =>
                    setFormularioMedio((previo) => ({
                      ...previo,
                      exige_referencia: evento.target.checked,
                    }))
                  }
                />
                Exige referencia
              </label>
              <label className="flex items-center gap-2 text-sm text-text-700">
                <input
                  type="checkbox"
                  checked={formularioMedio.referencia_unica}
                  onChange={(evento) =>
                    setFormularioMedio((previo) => ({
                      ...previo,
                      referencia_unica: evento.target.checked,
                    }))
                  }
                />
                Referencia única
              </label>
            </div>
            <FormField label="Fundamento" htmlFor="medio-fundamento" className="sm:col-span-2">
              <TextInput
                id="medio-fundamento"
                value={formularioMedio.fundamento}
                onChange={(evento) =>
                  setFormularioMedio((previo) => ({
                    ...previo,
                    fundamento: evento.target.value,
                  }))
                }
              />
            </FormField>
            {errorMedio ? (
              <p className="text-sm text-error-700 sm:col-span-2">{errorMedio}</p>
            ) : null}
            <Button type="submit" variant="primary" disabled={guardandoMedio}>
              {guardandoMedio ? "Creando…" : "Crear medio de pago"}
            </Button>
          </form>
        ) : null}
        {medios.data.length === 0 ? (
          <EmptyState
            title="Aún no hay medios de pago"
            description="Registre el primer medio autorizado por el ente."
          />
        ) : (
          <div
            className="relative mt-4 overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Tabla de medios de pago"
          >
            <table className="w-full min-w-[820px] border-collapse text-sm">
              <caption className="sr-only">Medios de pago</caption>
              <thead>
                <tr className="border-b border-border-default text-left text-text-600">
                  <th scope="col" className="px-3 py-2 font-medium">
                    Código
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Nombre
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Estado
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Exige referencia
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Referencia única
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Vigencia
                  </th>
                  {puedeGestionar ? (
                    <th scope="col" className="px-3 py-2 font-medium">
                      Acción
                    </th>
                  ) : null}
                </tr>
              </thead>
              <tbody>
                {medios.data.map((medio) => (
                  <tr key={medio.id} className="border-b border-border-subtle align-top">
                    <td className="px-3 py-2 font-medium text-text-900">{medio.codigo}</td>
                    <td className="px-3 py-2">{medio.nombre}</td>
                    <td className="px-3 py-2">{medio.estado}</td>
                    <td className="px-3 py-2">{medio.exige_referencia ? "Sí" : "No"}</td>
                    <td className="px-3 py-2">{medio.referencia_unica ? "Sí" : "No"}</td>
                    <td className="px-3 py-2">
                      {formatearFechaDeNegocio(medio.vigente_desde)}
                      {medio.vigente_hasta
                        ? ` – ${formatearFechaDeNegocio(medio.vigente_hasta)}`
                        : ""}
                    </td>
                    {puedeGestionar ? (
                      <td className="px-3 py-2">
                        <Button
                          type="button"
                          variant="secondary"
                          size="sm"
                          disabled={cambiandoEstado === medio.id}
                          onClick={() => void cambiarEstadoMedio(medio)}
                        >
                          {medio.estado === "ACTIVO" ? "Desactivar" : "Activar"}
                        </Button>
                      </td>
                    ) : null}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section aria-labelledby="numeracion-titulo">
        <h2 id="numeracion-titulo" className="text-lg font-semibold text-text-900">
          Numeración
        </h2>
        {configuracion.data?.patron ? (
          <p className="mt-1 text-sm text-text-700">
            Patrón: <span className="font-medium">{configuracion.data.patron}</span>
          </p>
        ) : (
          <p className="mt-1 text-sm text-text-600">Aún no se ha definido un patrón de numeración.</p>
        )}
        {puedeGestionar ? (
          <form
            className="mt-3 grid gap-3 sm:grid-cols-[1fr_auto] sm:items-start"
            onSubmit={(evento) => {
              evento.preventDefault();
              void guardarPatron();
            }}
          >
            <FormField
              label="Patrón"
              htmlFor="patron-numeracion-pagos"
              error={patronError ?? undefined}
              help="Variables admitidas: {ANIO}, {NUMERO:n}"
            >
              <TextInput
                id="patron-numeracion-pagos"
                value={patron}
                onChange={(evento) => setPatron(evento.target.value)}
              />
            </FormField>
            <Button type="submit" variant="primary" disabled={guardandoPatron}>
              {guardandoPatron ? "Guardando…" : "Guardar patrón"}
            </Button>
          </form>
        ) : null}
      </section>
    </PageContent>
  );
}
