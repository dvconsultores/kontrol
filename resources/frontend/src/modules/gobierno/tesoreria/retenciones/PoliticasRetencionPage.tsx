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
  API_RETENCIONES,
  CLASES_CONCEPTO,
  CONSULTA_CATALOGO_RETENCION,
  CONSULTA_CONFIG_RETENCION,
  CONSULTA_POLITICAS_RETENCION,
  ESTADOS_POLITICA_RETENCION,
  RUTA_POLITICAS_RETENCION,
  type ConfiguracionRetencion,
  type ElementoCatalogoRetencion,
  type PoliticaRetencion,
} from "./api";

interface FormularioCatalogo {
  codigo: string;
  nombre: string;
  descripcion: string;
  clase: string;
  serie_comprobante: string;
}

const FORMULARIO_CATALOGO_INICIAL: FormularioCatalogo = {
  codigo: "",
  nombre: "",
  descripcion: "",
  clase: "",
  serie_comprobante: "",
};

export function PoliticasRetencionPage() {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const { notify } = useNotifications();
  const puedeVer = tiene("gobierno_retenciones:view", "empresa");
  const puedeGestionar = tiene("gobierno_retenciones:manage", "empresa");

  const [patron, setPatron] = useState("");
  const [patronError, setPatronError] = useState<string | null>(null);
  const [guardandoPatron, setGuardandoPatron] = useState(false);
  const patronPrecargado = useRef(false);

  const [formularioConcepto, setFormularioConcepto] =
    useState<FormularioCatalogo>(FORMULARIO_CATALOGO_INICIAL);
  const [errorConcepto, setErrorConcepto] = useState<string | null>(null);
  const [guardandoConcepto, setGuardandoConcepto] = useState(false);

  const [formularioCondicion, setFormularioCondicion] =
    useState<FormularioCatalogo>(FORMULARIO_CATALOGO_INICIAL);
  const [errorCondicion, setErrorCondicion] = useState<string | null>(null);
  const [guardandoCondicion, setGuardandoCondicion] = useState(false);

  const [cambiandoEstado, setCambiandoEstado] = useState<string | null>(null);

  const configuracion = useQuery({
    queryKey: [...CONSULTA_CONFIG_RETENCION, activeCompanyId],
    queryFn: () =>
      apiFetch<ConfiguracionRetencion>(`${API_RETENCIONES}/configuracion`),
    enabled: Boolean(activeCompanyId) && puedeVer,
    retry: false,
  });

  const politicas = useQuery({
    queryKey: [...CONSULTA_POLITICAS_RETENCION, activeCompanyId],
    queryFn: () => apiFetch<PoliticaRetencion[]>(`${API_RETENCIONES}/politicas`),
    enabled: Boolean(activeCompanyId) && puedeVer,
    retry: false,
  });

  const conceptos = useQuery({
    queryKey: [...CONSULTA_CATALOGO_RETENCION, "CONCEPTO", activeCompanyId],
    queryFn: () =>
      apiFetch<ElementoCatalogoRetencion[]>(
        `${API_RETENCIONES}/catalogo?tipo=CONCEPTO`,
      ),
    enabled: Boolean(activeCompanyId) && puedeVer,
    retry: false,
  });

  const condiciones = useQuery({
    queryKey: [...CONSULTA_CATALOGO_RETENCION, "CONDICION", activeCompanyId],
    queryFn: () =>
      apiFetch<ElementoCatalogoRetencion[]>(
        `${API_RETENCIONES}/catalogo?tipo=CONDICION`,
      ),
    enabled: Boolean(activeCompanyId) && puedeVer,
    retry: false,
  });

  useEffect(() => {
    if (
      configuracion.data?.patron &&
      patron === "" &&
      !patronPrecargado.current
    ) {
      setPatron(configuracion.data.patron);
      patronPrecargado.current = true;
    }
  }, [configuracion.data, patron]);

  const cabecera = (
    <PageHeader
      crumbs={[{ label: "Gobierno" }, { label: "Políticas de retención" }]}
      title="Políticas de retención"
      description="Reglas de retención adoptadas por el ente, con fuente y vigencia. El producto no trae ninguna precargada."
      actions={
        puedeGestionar ? (
          <Link
            to={`${RUTA_POLITICAS_RETENCION}/nueva`}
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
          description="No tiene permiso para ver las políticas de retención."
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
      await apiFetch<ConfiguracionRetencion>(
        `${API_RETENCIONES}/configuracion`,
        {
          method: "PUT",
          body: { patron },
          ifMatch: String(version),
        },
      );
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

  const guardarCatalogo = async (
    tipo: "CONCEPTO" | "CONDICION",
    formulario: FormularioCatalogo,
    setGuardando: (valor: boolean) => void,
    setError: (valor: string | null) => void,
    setFormulario: (valor: FormularioCatalogo) => void,
    refetch: () => Promise<unknown>,
  ) => {
    setGuardando(true);
    setError(null);
    try {
      await apiFetch<ElementoCatalogoRetencion>(`${API_RETENCIONES}/catalogo`, {
        method: "POST",
        body: {
          tipo,
          codigo: formulario.codigo,
          nombre: formulario.nombre,
          descripcion: formulario.descripcion || null,
          clase: tipo === "CONCEPTO" ? formulario.clase : null,
          serie_comprobante:
            tipo === "CONCEPTO" ? formulario.serie_comprobante || null : null,
        },
      });
      notify({
        type: "success",
        title: tipo === "CONCEPTO" ? "Concepto añadido" : "Condición añadida",
      });
      setFormulario(FORMULARIO_CATALOGO_INICIAL);
      await refetch();
    } catch (error) {
      setError(
        error instanceof ApiError
          ? error.message
          : "No fue posible añadir el elemento.",
      );
    } finally {
      setGuardando(false);
    }
  };

  const cambiarEstadoCatalogo = async (
    elemento: ElementoCatalogoRetencion,
    refetch: () => Promise<unknown>,
  ) => {
    if (cambiandoEstado) return;
    setCambiandoEstado(elemento.id);
    try {
      await apiFetch<ElementoCatalogoRetencion>(
        `${API_RETENCIONES}/catalogo/${elemento.id}`,
        {
          method: "PUT",
          body: {
            nombre: elemento.nombre,
            descripcion: elemento.descripcion,
            clase: elemento.clase,
            serie_comprobante: elemento.serie_comprobante,
            estado: elemento.estado === "ACTIVO" ? "INACTIVO" : "ACTIVO",
          },
          ifMatch: String(elemento.version),
        },
      );
      notify({ type: "success", title: "Estado actualizado" });
      await refetch();
    } catch (error) {
      notify({
        type: "error",
        title: "Error",
        description:
          error instanceof ApiError
            ? error.message
            : "No fue posible cambiar el estado.",
      });
    } finally {
      setCambiandoEstado(null);
    }
  };

  const tablaCatalogo = (
    titulo: string,
    vacio: string,
    datos: ElementoCatalogoRetencion[] | undefined,
    esConcepto: boolean,
    refetch: () => Promise<unknown>,
  ) => (
    <section aria-labelledby={`${titulo.replace(" ", "-").toLowerCase()}-titulo`}>
      <h3
        id={`${titulo.replace(" ", "-").toLowerCase()}-titulo`}
        className="text-base font-semibold text-text-900"
      >
        {titulo}
      </h3>
      {datos && datos.length === 0 ? (
        <EmptyState title={vacio} description="" />
      ) : (
        <div
          role="region"
          aria-label={`${titulo} (desplazable)`}
          tabIndex={0}
          className="overflow-x-auto"
        >
          <table className="w-full text-sm" aria-label={titulo}>
            <thead>
              <tr>
                <th className="px-3 py-2 text-left">Código</th>
                <th className="px-3 py-2 text-left">Nombre</th>
                <th className="px-3 py-2 text-left">
                  {esConcepto ? "Clase" : "—"}
                </th>
                <th className="px-3 py-2 text-left">
                  {esConcepto ? "Serie" : "—"}
                </th>
                <th className="px-3 py-2 text-left">Estado</th>
                <th className="px-3 py-2 text-left">Acción</th>
              </tr>
            </thead>
            <tbody>
              {datos?.map((elemento) => (
                <tr key={elemento.id}>
                  <td className="px-3 py-2">{elemento.codigo}</td>
                  <td className="px-3 py-2">{elemento.nombre}</td>
                  <td className="px-3 py-2">
                    {esConcepto && elemento.clase
                      ? CLASES_CONCEPTO[elemento.clase] ?? elemento.clase
                      : "—"}
                  </td>
                  <td className="px-3 py-2">
                    {esConcepto ? elemento.serie_comprobante ?? "—" : "—"}
                  </td>
                  <td className="px-3 py-2">
                    {elemento.estado === "ACTIVO" ? "Activo" : "Inactivo"}
                  </td>
                  <td className="px-3 py-2">
                    {puedeGestionar && (
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => cambiarEstadoCatalogo(elemento, refetch)}
                        disabled={cambiandoEstado === elemento.id}
                      >
                        {elemento.estado === "ACTIVO" ? "Inactivar" : "Activar"}
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );

  const formularioCatalogo = (
    tipo: "CONCEPTO" | "CONDICION",
    etiqueta: string,
    formulario: FormularioCatalogo,
    setFormulario: (valor: FormularioCatalogo) => void,
    error: string | null,
    guardando: boolean,
    refetch: () => Promise<unknown>,
    setError: (valor: string | null) => void,
    setGuardando: (valor: boolean) => void,
  ) => (
    <div className="rounded-lg border border-border-default p-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <FormField label="Código" htmlFor={`${tipo.toLowerCase()}-codigo`}>
          <TextInput
            id={`${tipo.toLowerCase()}-codigo`}
            value={formulario.codigo}
            onChange={(event) =>
              setFormulario({ ...formulario, codigo: event.target.value })
            }
          />
        </FormField>
        <FormField label="Nombre" htmlFor={`${tipo.toLowerCase()}-nombre`}>
          <TextInput
            id={`${tipo.toLowerCase()}-nombre`}
            value={formulario.nombre}
            onChange={(event) =>
              setFormulario({ ...formulario, nombre: event.target.value })
            }
          />
        </FormField>
        <FormField
          label="Descripción"
          htmlFor={`${tipo.toLowerCase()}-descripcion`}
        >
          <TextInput
            id={`${tipo.toLowerCase()}-descripcion`}
            value={formulario.descripcion}
            onChange={(event) =>
              setFormulario({ ...formulario, descripcion: event.target.value })
            }
          />
        </FormField>
        {tipo === "CONCEPTO" && (
          <>
            <FormField label="Clase" htmlFor={`${tipo.toLowerCase()}-clase`}>
              <select
                id={`${tipo.toLowerCase()}-clase`}
                className="w-full rounded-md border border-border-default px-3 py-2"
                value={formulario.clase}
                onChange={(event) =>
                  setFormulario({
                    ...formulario,
                    clase: event.target.value,
                  })
                }
              >
                <option value="">Seleccione…</option>
                {Object.entries(CLASES_CONCEPTO).map(([valor, texto]) => (
                  <option key={valor} value={valor}>
                    {texto}
                  </option>
                ))}
              </select>
            </FormField>
            <FormField
              label="Serie del comprobante"
              htmlFor={`${tipo.toLowerCase()}-serie`}
            >
              <TextInput
                id={`${tipo.toLowerCase()}-serie`}
                value={formulario.serie_comprobante}
                onChange={(event) =>
                  setFormulario({
                    ...formulario,
                    serie_comprobante: event.target.value,
                  })
                }
              />
            </FormField>
          </>
        )}
      </div>
      {error && (
        <p role="alert" className="mt-2 text-sm text-error-600">
          {error}
        </p>
      )}
      <div className="mt-3">
        <Button
          variant="primary"
          onClick={() =>
            guardarCatalogo(
              tipo,
              formulario,
              setGuardando,
              setError,
              setFormulario,
              refetch,
            )
          }
          disabled={guardando}
        >
          {etiqueta}
        </Button>
      </div>
    </div>
  );

  return (
    <PageContent>
      {cabecera}

      <section aria-labelledby="politicas-titulo">
        <h2 id="politicas-titulo" className="text-lg font-semibold text-text-900">
          Políticas
        </h2>
        {politicas.isLoading ? (
          <LoadingState />
        ) : politicas.isError ? (
          <ErrorState
            title="No se pudieron cargar las políticas"
            message={
              politicas.error instanceof ApiError
                ? politicas.error.message
                : "Error inesperado"
            }
          />
        ) : politicas.data && politicas.data.length === 0 ? (
          <EmptyState
            title="Aún no hay políticas de retención"
            description="El producto no trae ninguna precargada."
          />
        ) : (
          <div
            role="region"
            aria-label="Políticas de retención (desplazable)"
            tabIndex={0}
            className="overflow-x-auto"
          >
            <table
              className="w-full text-sm"
              aria-label="Políticas de retención"
            >
              <thead>
                <tr>
                  <th className="px-3 py-2 text-left">Código</th>
                  <th className="px-3 py-2 text-left">Versión</th>
                  <th className="px-3 py-2 text-left">Nombre</th>
                  <th className="px-3 py-2 text-left">Moneda</th>
                  <th className="px-3 py-2 text-left">Estado</th>
                  <th className="px-3 py-2 text-left">Vigencia</th>
                  <th className="px-3 py-2 text-left">Reglas</th>
                </tr>
              </thead>
              <tbody>
                {politicas.data?.map((politica) => (
                  <tr key={politica.id}>
                    <td className="px-3 py-2">
                      <Link
                        to={`${RUTA_POLITICAS_RETENCION}/${politica.id}`}
                        className="text-primary-600 hover:underline"
                      >
                        {politica.codigo}
                      </Link>
                    </td>
                    <td className="px-3 py-2">{politica.numero_version}</td>
                    <td className="px-3 py-2">{politica.nombre}</td>
                    <td className="px-3 py-2">{politica.moneda}</td>
                    <td className="px-3 py-2">
                      {ESTADOS_POLITICA_RETENCION[politica.estado] ??
                        politica.estado}
                    </td>
                    <td className="px-3 py-2">
                      {politica.vigente_desde
                        ? formatearFechaDeNegocio(politica.vigente_desde)
                        : "—"}
                      {" – "}
                      {politica.vigente_hasta
                        ? formatearFechaDeNegocio(politica.vigente_hasta)
                        : "—"}
                    </td>
                    <td className="px-3 py-2">{politica.reglas_count ?? 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section aria-labelledby="catalogo-titulo" className="mt-8">
        <h2 id="catalogo-titulo" className="text-lg font-semibold text-text-900">
          Catálogo del ente
        </h2>
        <div className="mt-4 space-y-6">
          {tablaCatalogo(
            "Conceptos de retención",
            "Aún no hay conceptos",
            conceptos.data,
            true,
            conceptos.refetch,
          )}
          {puedeGestionar &&
            formularioCatalogo(
              "CONCEPTO",
              "Añadir concepto",
              formularioConcepto,
              setFormularioConcepto,
              errorConcepto,
              guardandoConcepto,
              conceptos.refetch,
              setErrorConcepto,
              setGuardandoConcepto,
            )}
          {tablaCatalogo(
            "Condiciones del beneficiario",
            "Aún no hay condiciones",
            condiciones.data,
            false,
            condiciones.refetch,
          )}
          {puedeGestionar &&
            formularioCatalogo(
              "CONDICION",
              "Añadir condición",
              formularioCondicion,
              setFormularioCondicion,
              errorCondicion,
              guardandoCondicion,
              condiciones.refetch,
              setErrorCondicion,
              setGuardandoCondicion,
            )}
        </div>
      </section>

      <section
        aria-labelledby="numeracion-titulo"
        className="mt-8 max-w-2xl"
      >
        <h2
          id="numeracion-titulo"
          className="text-lg font-semibold text-text-900"
        >
          Numeración de comprobantes
        </h2>
        <div className="rounded-lg border border-border-default p-4">
          <FormField label="Patrón" htmlFor="patron-retencion">
            <TextInput
              id="patron-retencion"
              value={patron}
              onChange={(event) => setPatron(event.target.value)}
              aria-describedby="patron-retencion-ayuda"
            />
          </FormField>
          <p id="patron-retencion-ayuda" className="mt-1 text-sm text-text-500">
            Variables admitidas: {"{ANIO}"}, {"{NUMERO:n}"}, {"{SERIE}"}
          </p>
          {configuracion.data?.ejemplo && (
            <p className="mt-1 text-sm text-text-600">
              Ejemplo: {configuracion.data.ejemplo}
            </p>
          )}
          {patronError && (
            <p role="alert" className="mt-2 text-sm text-error-600">
              {patronError}
            </p>
          )}
          <div className="mt-3">
            <Button
              variant="primary"
              onClick={guardarPatron}
              disabled={!puedeGestionar || guardandoPatron}
            >
              Guardar patrón
            </Button>
          </div>
        </div>
      </section>
    </PageContent>
  );
}
