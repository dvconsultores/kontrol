import { useState } from "react";
import { Link } from "react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { formatearFechaDeNegocio, formatearInstante } from "@/lib/fecha-de-negocio";
import { EmptyState } from "@/components/EmptyState";
import { ErrorDeCarga } from "@/modules/gobierno/ocupacion/ErrorDeCarga";
import { LoadingState } from "@/components/LoadingState";
import { useNotifications } from "@/app/contexts/NotificationContext";
import {
  CONSULTA_IDENTIDAD,
  ETIQUETAS_CATEGORIA_SEPARACION,
} from "@/modules/gobierno/api";
import type {
  CategoriaRol,
  CategoriasListado,
  CategoriaSeparacion,
  ConflictosIdentidad,
  PoliticaIdentidad,
  RolIdentidad,
} from "@/modules/gobierno/api";

type FormularioCategoriaErrors = Record<string, string>;
type FormularioRetiroErrors = Record<string, string>;

interface FormularioCategoria {
  role_id: string;
  categoria: CategoriaSeparacion | "";
  desde: string;
  motivo: string;
}

interface FormularioRetiro {
  fecha: string;
  motivo: string;
}

export function CategoriasPage() {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const [formCategoria, setFormCategoria] = useState<FormularioCategoria>({
    role_id: "",
    categoria: "",
    desde: "",
    motivo: "",
  });
  const [formErrors, setFormErrors] = useState<FormularioCategoriaErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [retiroActivo, setRetiroActivo] = useState<CategoriaRol | null>(null);
  const [formRetiro, setFormRetiro] = useState<FormularioRetiro>({
    fecha: "",
    motivo: "",
  });
  const [retiroErrors, setRetiroErrors] = useState<FormularioRetiroErrors>({});
  const [retiroError, setRetiroError] = useState<string | null>(null);
  const [motivoPolitica, setMotivoPolitica] = useState("");
  const [politicaErrors, setPoliticaErrors] = useState<FormularioCategoriaErrors>(
    {},
  );
  const [politicaError, setPoliticaError] = useState<string | null>(null);

  const puedeVer = tiene("gobierno_identidad:view", "empresa");
  const puedeGestionar = tiene("gobierno_identidad:manage", "empresa");
  const puedeActivar = tiene("gobierno_identidad:activate", "empresa");

  const consultaCategorias = useQuery({
    queryKey: [...CONSULTA_IDENTIDAD, activeCompanyId, "categorias"],
    queryFn: () =>
      apiFetch<CategoriasListado>("/gobierno/identidad/categorias"),
    enabled: puedeVer && Boolean(activeCompanyId),
    retry: false,
    placeholderData: (previousData) => previousData,
  });

  const consultaConflictos = useQuery({
    queryKey: [...CONSULTA_IDENTIDAD, activeCompanyId, "conflictos"],
    queryFn: () =>
      apiFetch<ConflictosIdentidad>("/gobierno/identidad/conflictos"),
    enabled: puedeVer && Boolean(activeCompanyId),
    retry: false,
    placeholderData: (previousData) => previousData,
  });

  const consultaPolitica = useQuery({
    queryKey: [...CONSULTA_IDENTIDAD, activeCompanyId, "politica"],
    queryFn: () =>
      apiFetch<PoliticaIdentidad>("/gobierno/identidad/politica"),
    enabled: puedeVer && Boolean(activeCompanyId),
    retry: false,
    placeholderData: (previousData) => previousData,
  });

  const crearCategoria = useMutation({
    mutationFn: (entrada: {
      role_id: string;
      categoria: CategoriaSeparacion;
      desde: string;
      motivo: string;
    }) =>
      apiFetch("/gobierno/identidad/categorias", {
        method: "POST",
        body: entrada,
      }),
    onSuccess: () => {
      setFormCategoria({ role_id: "", categoria: "", desde: "", motivo: "" });
      setFormErrors({});
      setFormError(null);
      void queryClient.invalidateQueries({
        queryKey: [...CONSULTA_IDENTIDAD, activeCompanyId],
      });
      notify({ type: "success", title: "Categoría registrada" });
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError) {
        if (
          error.status === 409 &&
          error.code &&
          (error.code === "GOV_ROLE_CATEGORY_DUPLICATE" ||
            error.code === "GOV_SOD_CONFLICT")
        ) {
          setFormError(error.message);
          return;
        }
        if (error.status === 422 && Object.keys(error.fieldErrors).length > 0) {
          setFormErrors(
            Object.fromEntries(
              Object.entries(error.fieldErrors).map(([campo, mensajes]) => [
                campo,
                mensajes[0] ?? "",
              ]),
            ),
          );
          setFormError(null);
          return;
        }
        if (error.status >= 400 && error.status < 500) {
          setFormError(error.message);
          return;
        }
      }
      setFormError("No fue posible registrar la categoría.");
    },
  });

  const retirarCategoria = useMutation({
    mutationFn: ({
      id,
      version,
      body,
    }: {
      id: string;
      version: number;
      body: { fecha: string; motivo: string };
    }) =>
      apiFetch(`/gobierno/identidad/categorias/${id}/retirar`, {
        method: "POST",
        ifMatch: String(version),
        body,
      }),
    onSuccess: () => {
      setRetiroActivo(null);
      setFormRetiro({ fecha: "", motivo: "" });
      setRetiroErrors({});
      setRetiroError(null);
      void queryClient.invalidateQueries({
        queryKey: [...CONSULTA_IDENTIDAD, activeCompanyId],
      });
      notify({ type: "success", title: "Categoría retirada" });
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError) {
        if (error.status === 422 && Object.keys(error.fieldErrors).length > 0) {
          setRetiroErrors(
            Object.fromEntries(
              Object.entries(error.fieldErrors).map(([campo, mensajes]) => [
                campo,
                mensajes[0] ?? "",
              ]),
            ),
          );
          setRetiroError(null);
          return;
        }
        if (error.status >= 400 && error.status < 500) {
          setRetiroError(error.message);
          return;
        }
      }
      setRetiroError("No fue posible retirar la categoría.");
    },
  });

  const cambiarPolitica = useMutation({
    mutationFn: ({
      version,
      body,
    }: {
      version: number;
      body: { exige_identidad: boolean; motivo: string };
    }) =>
      apiFetch("/gobierno/identidad/politica", {
        method: "POST",
        ifMatch: String(version),
        body,
      }),
    onSuccess: () => {
      setMotivoPolitica("");
      setPoliticaErrors({});
      setPoliticaError(null);
      void queryClient.invalidateQueries({
        queryKey: [...CONSULTA_IDENTIDAD, activeCompanyId],
      });
      notify({ type: "success", title: "Política actualizada" });
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError) {
        if (error.status === 422 && Object.keys(error.fieldErrors).length > 0) {
          setPoliticaErrors(
            Object.fromEntries(
              Object.entries(error.fieldErrors).map(([campo, mensajes]) => [
                campo,
                mensajes[0] ?? "",
              ]),
            ),
          );
          setPoliticaError(null);
          return;
        }
        if (error.status >= 400 && error.status < 500) {
          setPoliticaError(error.message);
          return;
        }
      }
      setPoliticaError("No fue posible actualizar la política.");
    },
  });

  const cabecera = (
    <PageHeader
      crumbs={[
        { label: "Gobierno" },
        { label: "Identidad institucional", to: "/gobierno/identidad" },
        { label: "Categorías y separación" },
      ]}
      title="Categorías y separación"
      description="Clasificación de roles en categorías de separación, conflictos vigentes y exigencia de identidad del ente."
    />
  );

  if (!puedeVer) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para ver las categorías y separación."
        />
      </PageContent>
    );
  }

  const manejarRegistroCategoria = (evento: React.FormEvent<HTMLFormElement>) => {
    evento.preventDefault();
    setFormErrors({});
    setFormError(null);
    if (formCategoria.categoria === "") {
      setFormErrors((prev) => ({
        ...prev,
        categoria: "Seleccione una categoría.",
      }));
      return;
    }
    crearCategoria.mutate({
      role_id: formCategoria.role_id,
      categoria: formCategoria.categoria,
      desde: formCategoria.desde,
      motivo: formCategoria.motivo,
    });
  };

  const manejarRetiro = (evento: React.FormEvent<HTMLFormElement>) => {
    evento.preventDefault();
    if (!retiroActivo) return;
    setRetiroErrors({});
    setRetiroError(null);
    retirarCategoria.mutate({
      id: retiroActivo.id,
      version: retiroActivo.version,
      body: {
        fecha: formRetiro.fecha,
        motivo: formRetiro.motivo,
      },
    });
  };

  const manejarCambioPolitica = (evento: React.FormEvent<HTMLFormElement>) => {
    evento.preventDefault();
    if (!consultaPolitica.data) return;
    setPoliticaErrors({});
    setPoliticaError(null);
    cambiarPolitica.mutate({
      version: consultaPolitica.data.version,
      body: {
        exige_identidad: !consultaPolitica.data.exige_identidad,
        motivo: motivoPolitica,
      },
    });
  };

  const etiquetaCategoria = (categoria: string) =>
    (ETIQUETAS_CATEGORIA_SEPARACION as Record<string, string>)[categoria] ??
    categoria;

  const renderErrorConsulta = (
    error: unknown,
    mensajeCarga: string,
    onRetry: () => void,
  ) => {
    if (error instanceof ApiError && error.status === 403) {
      return (
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para ver esta información."
        />
      );
    }
    return <ErrorDeCarga message={mensajeCarga} onRetry={onRetry} />;
  };

  return (
    <PageContent>
      {cabecera}

      <section aria-labelledby="clasificacion-titulo" className="mb-8">
        <h2
          id="clasificacion-titulo"
          className="mb-4 text-lg font-semibold text-text-900"
        >
          Clasificación de roles
        </h2>
        <p className="mb-4 text-sm text-text-600">
          Las incompatibilidades entre categorías se definen como reglas del
          proceso Identidad institucional en{" "}
          <Link
            to="/gobierno/sod"
            className="font-medium text-brand-700 underline"
          >
            Segregación de funciones
          </Link>
          .
        </p>

        {puedeGestionar ? (
          <form
            onSubmit={manejarRegistroCategoria}
            className="mb-6 grid gap-4 rounded-md border border-border-subtle bg-surface-0 p-4 sm:grid-cols-2"
          >
            <label className="flex flex-col gap-1">
              <span className="text-sm font-medium text-text-700">Rol</span>
              <select
                className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                value={formCategoria.role_id}
                onChange={(evento) =>
                  setFormCategoria((prev) => ({
                    ...prev,
                    role_id: evento.target.value,
                  }))
                }
                required
              >
                <option value="">Seleccione</option>
                {consultaCategorias.data?.roles.map((rol: RolIdentidad) => (
                  <option key={rol.id} value={rol.id}>
                    {rol.nombre} ({rol.codigo})
                  </option>
                )) ?? null}
              </select>
              {formErrors.role_id ? (
                <span role="alert" className="text-sm text-danger-600">
                  {formErrors.role_id}
                </span>
              ) : null}
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-sm font-medium text-text-700">
                Categoría
              </span>
              <select
                className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                value={formCategoria.categoria}
                onChange={(evento) =>
                  setFormCategoria((prev) => ({
                    ...prev,
                    categoria: evento.target.value as CategoriaSeparacion | "",
                  }))
                }
                required
              >
                <option value="">Seleccione</option>
                <option value="OPERATIVO">
                  {ETIQUETAS_CATEGORIA_SEPARACION.OPERATIVO}
                </option>
                <option value="APROBADOR">
                  {ETIQUETAS_CATEGORIA_SEPARACION.APROBADOR}
                </option>
                <option value="CONTROL_INTERNO">
                  {ETIQUETAS_CATEGORIA_SEPARACION.CONTROL_INTERNO}
                </option>
                <option value="AUDITORIA">
                  {ETIQUETAS_CATEGORIA_SEPARACION.AUDITORIA}
                </option>
                <option value="ADMINISTRACION_TECNICA">
                  {ETIQUETAS_CATEGORIA_SEPARACION.ADMINISTRACION_TECNICA}
                </option>
              </select>
              {formErrors.categoria ? (
                <span role="alert" className="text-sm text-danger-600">
                  {formErrors.categoria}
                </span>
              ) : null}
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-sm font-medium text-text-700">Desde</span>
              <input
                type="date"
                className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                value={formCategoria.desde}
                onChange={(evento) =>
                  setFormCategoria((prev) => ({
                    ...prev,
                    desde: evento.target.value,
                  }))
                }
                required
              />
              {formErrors.desde ? (
                <span role="alert" className="text-sm text-danger-600">
                  {formErrors.desde}
                </span>
              ) : null}
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-sm font-medium text-text-700">Motivo</span>
              <textarea
                className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                value={formCategoria.motivo}
                onChange={(evento) =>
                  setFormCategoria((prev) => ({
                    ...prev,
                    motivo: evento.target.value,
                  }))
                }
                minLength={10}
                maxLength={500}
                required
              />
              {formErrors.motivo ? (
                <span role="alert" className="text-sm text-danger-600">
                  {formErrors.motivo}
                </span>
              ) : null}
            </label>
            {formError ? (
              <div role="alert" className="text-sm text-danger-600 sm:col-span-2">
                {formError}
              </div>
            ) : null}
            <div className="sm:col-span-2">
              <button
                type="submit"
                className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
                disabled={crearCategoria.isPending}
              >
                {crearCategoria.isPending
                  ? "Registrando…"
                  : "Registrar categoría"}
              </button>
            </div>
          </form>
        ) : null}

        {consultaCategorias.isLoading ? (
          <LoadingState label="Cargando categorías…" />
        ) : consultaCategorias.isError ? (
          renderErrorConsulta(
            consultaCategorias.error,
            "No fue posible cargar las categorías.",
            () => void consultaCategorias.refetch(),
          )
        ) : !consultaCategorias.data ? (
          <EmptyState title="Aún no hay categorías" />
        ) : consultaCategorias.data.items.length === 0 ? (
          <EmptyState title="Aún no hay categorías" />
        ) : (
          <div
            className="relative overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Tabla de categorías de rol"
          >
            <table className="w-full min-w-[640px] border-collapse text-sm">
              <caption className="sr-only">Categorías de rol</caption>
              <thead>
                <tr className="border-b border-border-default text-left text-text-600">
                  <th scope="col" className="px-3 py-2 font-medium">
                    Rol
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Categoría
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Desde
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Hasta
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Estado
                  </th>
                  {puedeGestionar ? (
                    <th scope="col" className="px-3 py-2 font-medium">
                      Acción
                    </th>
                  ) : null}
                </tr>
              </thead>
              <tbody>
                {consultaCategorias.data.items.map((categoria) => (
                  <tr
                    key={categoria.id}
                    className="border-b border-border-subtle align-top"
                  >
                    <td className="px-3 py-2 text-text-900">
                      {categoria.rol_nombre} ({categoria.rol_codigo})
                    </td>
                    <td className="px-3 py-2">
                      {categoria.categoria_etiqueta}
                    </td>
                    <td className="px-3 py-2">
                      {formatearFechaDeNegocio(categoria.desde)}
                    </td>
                    <td className="px-3 py-2">
                      {categoria.hasta
                        ? formatearFechaDeNegocio(categoria.hasta)
                        : "Vigente"}
                    </td>
                    <td className="px-3 py-2">
                      {categoria.status === "ACTIVA" ? "Activa" : "Retirada"}
                    </td>
                    {puedeGestionar ? (
                      <td className="px-3 py-2">
                        {categoria.status === "ACTIVA" ? (
                          <button
                            type="button"
                            className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
                            onClick={() => {
                              setRetiroActivo(categoria);
                              setFormRetiro({ fecha: "", motivo: "" });
                              setRetiroErrors({});
                              setRetiroError(null);
                            }}
                          >
                            Retirar
                          </button>
                        ) : null}
                      </td>
                    ) : null}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {retiroActivo ? (
          <form
            onSubmit={manejarRetiro}
            className="mt-4 grid gap-4 rounded-md border border-border-subtle bg-surface-0 p-4 sm:grid-cols-2"
          >
            <h3 className="text-sm font-semibold text-text-900 sm:col-span-2">
              Retirar categoría de {retiroActivo.rol_nombre} (
              {retiroActivo.rol_codigo})
            </h3>
            <label className="flex flex-col gap-1">
              <span className="text-sm font-medium text-text-700">Fecha</span>
              <input
                type="date"
                className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                value={formRetiro.fecha}
                onChange={(evento) =>
                  setFormRetiro((prev) => ({
                    ...prev,
                    fecha: evento.target.value,
                  }))
                }
                required
              />
              {retiroErrors.fecha ? (
                <span role="alert" className="text-sm text-danger-600">
                  {retiroErrors.fecha}
                </span>
              ) : null}
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-sm font-medium text-text-700">Motivo</span>
              <textarea
                className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                value={formRetiro.motivo}
                onChange={(evento) =>
                  setFormRetiro((prev) => ({
                    ...prev,
                    motivo: evento.target.value,
                  }))
                }
                minLength={10}
                maxLength={500}
                required
              />
              {retiroErrors.motivo ? (
                <span role="alert" className="text-sm text-danger-600">
                  {retiroErrors.motivo}
                </span>
              ) : null}
            </label>
            {retiroError ? (
              <div role="alert" className="text-sm text-danger-600 sm:col-span-2">
                {retiroError}
              </div>
            ) : null}
            <div className="flex gap-2 sm:col-span-2">
              <button
                type="submit"
                className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
                disabled={retirarCategoria.isPending}
              >
                {retirarCategoria.isPending ? "Retirando…" : "Retirar"}
              </button>
              <button
                type="button"
                className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
                onClick={() => setRetiroActivo(null)}
              >
                Cancelar
              </button>
            </div>
          </form>
        ) : null}
      </section>

      <section aria-labelledby="conflictos-titulo" className="mb-8">
        <h2
          id="conflictos-titulo"
          className="mb-4 text-lg font-semibold text-text-900"
        >
          Conflictos vigentes
        </h2>
        {consultaConflictos.isLoading ? (
          <LoadingState label="Cargando conflictos…" />
        ) : consultaConflictos.isError ? (
          renderErrorConsulta(
            consultaConflictos.error,
            "No fue posible cargar los conflictos.",
            () => void consultaConflictos.refetch(),
          )
        ) : !consultaConflictos.data ? (
          <EmptyState title="Sin conflictos de separación entre los vínculos vigentes." />
        ) : consultaConflictos.data.items.length === 0 ? (
          <EmptyState title="Sin conflictos de separación entre los vínculos vigentes." />
        ) : (
          <div
            className="relative overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Tabla de conflictos de separación"
          >
            <table className="w-full min-w-[640px] border-collapse text-sm">
              <caption className="sr-only">Conflictos de separación</caption>
              <thead>
                <tr className="border-b border-border-default text-left text-text-600">
                  <th scope="col" className="px-3 py-2 font-medium">
                    Vínculo
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Cuenta
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Funcionario
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Conflictos
                  </th>
                </tr>
              </thead>
              <tbody>
                {consultaConflictos.data.items.map((conflicto) => (
                  <tr
                    key={conflicto.vinculo_id}
                    className="border-b border-border-subtle align-top"
                  >
                    <td className="px-3 py-2">
                      <Link
                        to={`/gobierno/identidad/vinculos/${conflicto.vinculo_id}`}
                        className="font-medium text-brand-700 underline"
                      >
                        {conflicto.codigo}
                      </Link>
                    </td>
                    <td className="px-3 py-2 text-text-900">
                      {conflicto.cuenta.usuario}
                    </td>
                    <td className="px-3 py-2 text-text-900">
                      {conflicto.funcionario.nombre}
                    </td>
                    <td className="px-3 py-2">
                      <ul className="list-disc pl-5">
                        {conflicto.conflictos.map((item, index) => (
                          <li key={`${item.regla_codigo}-${index}`}>
                            {item.regla_codigo} · {item.regla_nombre}:{" "}
                            {etiquetaCategoria(item.categoria_a)} y{" "}
                            {etiquetaCategoria(item.categoria_b)}
                          </li>
                        ))}
                      </ul>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section aria-labelledby="politica-titulo" className="mb-8">
        <h2
          id="politica-titulo"
          className="mb-4 text-lg font-semibold text-text-900"
        >
          Exigencia de identidad del ente
        </h2>
        {consultaPolitica.isLoading ? (
          <LoadingState label="Cargando política de identidad…" />
        ) : consultaPolitica.isError ? (
          renderErrorConsulta(
            consultaPolitica.error,
            "No fue posible cargar la política de identidad.",
            () => void consultaPolitica.refetch(),
          )
        ) : !consultaPolitica.data ? (
          <EmptyState title="Sin política de identidad" />
        ) : (
          <>
            <p className="mb-4 text-sm text-text-900">
              {consultaPolitica.data.exige_identidad
                ? "Activa: emitir un acto exige que su funcionario ejerza hoy el cargo con esa competencia."
                : "Inactiva: el ente aún no exige vínculo institucional para operar."}
            </p>
            {puedeActivar ? (
              <form
                onSubmit={manejarCambioPolitica}
                className="mb-6 grid gap-4 rounded-md border border-border-subtle bg-surface-0 p-4"
              >
                <label className="flex flex-col gap-1">
                  <span className="text-sm font-medium text-text-700">
                    Motivo
                  </span>
                  <textarea
                    className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                    value={motivoPolitica}
                    onChange={(evento) => setMotivoPolitica(evento.target.value)}
                    minLength={10}
                    maxLength={500}
                    required
                  />
                  {politicaErrors.motivo ? (
                    <span role="alert" className="text-sm text-danger-600">
                      {politicaErrors.motivo}
                    </span>
                  ) : null}
                </label>
                <div>
                  <button
                    type="submit"
                    className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
                    disabled={cambiarPolitica.isPending}
                  >
                    {cambiarPolitica.isPending
                      ? "Actualizando…"
                      : consultaPolitica.data.exige_identidad
                        ? "Desactivar la exigencia"
                        : "Activar la exigencia"}
                  </button>
                </div>
                {politicaError ? (
                  <div role="alert" className="text-sm text-danger-600">
                    {politicaError}
                  </div>
                ) : null}
              </form>
            ) : null}
            <h3 className="mb-2 text-sm font-semibold text-text-900">
              Historia
            </h3>
            <ul className="list-disc pl-5 text-sm text-text-900">
              {consultaPolitica.data.historia.map((historia) => (
                <li key={historia.id} className="mb-1">
                  {formatearInstante(historia.creado_en)} —{" "}
                  {historia.actor ?? "Sistema"}:{" "}
                  {typeof historia.detalle === "object" &&
                  historia.detalle !== null &&
                  !Array.isArray(historia.detalle) &&
                  "despues" in historia.detalle &&
                  typeof (historia.detalle as Record<string, unknown>).despues ===
                    "object" &&
                  (historia.detalle as Record<string, unknown>).despues !==
                    null &&
                  "exige_identidad" in
                    ((historia.detalle as Record<string, unknown>)
                      .despues as Record<string, unknown>)
                    ? ((historia.detalle as Record<string, unknown>).despues as Record<string, unknown>)
                        .exige_identidad
                      ? "Activa"
                      : "Inactiva"
                    : "—"}
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
    </PageContent>
  );
}
