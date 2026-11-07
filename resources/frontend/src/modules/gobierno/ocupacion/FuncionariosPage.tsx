import { useState } from "react";
import { Link } from "react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { ErrorDeCarga } from "@/modules/gobierno/ocupacion/ErrorDeCarga";
import { LoadingState } from "@/components/LoadingState";
import { useNotifications } from "@/app/contexts/NotificationContext";
import {
  CONSULTA_OCUPACION,
  ETIQUETAS_ESTADO_FUNCIONARIO,
  ETIQUETAS_TIPO_DOCUMENTO_FUNCIONARIO,
  consultaDeFuncionarios,
} from "@/modules/gobierno/api";
import type {
  EstadoFuncionario,
  FuncionarioEntrada,
  FuncionariosListado,
  TipoDocumentoFuncionario,
} from "@/modules/gobierno/api";

export function FuncionariosPage() {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const [texto, setTexto] = useState("");
  const [estado, setEstado] = useState<EstadoFuncionario | "">("");
  const [pagina, setPagina] = useState(1);
  const [nombre, setNombre] = useState("");
  const [tipoDocumento, setTipoDocumento] = useState<TipoDocumentoFuncionario>("V");
  const [numeroDocumento, setNumeroDocumento] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);

  const puedeVer = tiene("gobierno_ocupacion:view", "empresa");
  const puedeGestionar = tiene("gobierno_ocupacion:manage", "empresa");

  const consultaFuncionarios = useQuery({
    queryKey: [
      ...CONSULTA_OCUPACION,
      "funcionarios",
      activeCompanyId,
      texto,
      estado,
      pagina,
    ],
    queryFn: () =>
      apiFetch<FuncionariosListado>(
        `/gobierno/ocupacion/funcionarios${consultaDeFuncionarios({
          texto,
          estado,
          pagina,
        })}`,
      ),
    enabled: puedeVer && Boolean(activeCompanyId),
    retry: false,
    placeholderData: (previousData) => previousData,
  });

  const registrarFuncionario = useMutation({
    mutationFn: (entrada: FuncionarioEntrada) =>
      apiFetch("/gobierno/ocupacion/funcionarios", {
        method: "POST",
        body: entrada,
      }),
    onSuccess: () => {
      setNombre("");
      setTipoDocumento("V");
      setNumeroDocumento("");
      setFieldErrors({});
      setFormError(null);
      void queryClient.invalidateQueries({
        queryKey: [...CONSULTA_OCUPACION, "funcionarios"],
      });
      notify({ type: "success", title: "Funcionario registrado" });
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError) {
        if (
          error.status === 409 &&
          error.code &&
          error.code.includes("DUPLICATE")
        ) {
          setFormError(error.message);
          return;
        }
        if (error.status === 422 && error.code === "VALIDATION_ERROR") {
          setFieldErrors(Object.fromEntries(Object.entries(error.fieldErrors).map(([campo, mensajes]) => [campo, mensajes[0] ?? ""])));
          setFormError(null);
          return;
        }
        if (error.status >= 400 && error.status < 500) {
          setFormError(error.message);
          return;
        }
      }
      setFormError("No fue posible registrar el funcionario.");
    },
  });

  const cabecera = (
    <PageHeader
      crumbs={[
        { label: "Gobierno" },
        { label: "Ocupación de cargos" },
        { label: "Funcionarios" },
      ]}
      title="Funcionarios"
      description="Personas del ente que pueden ejercer cargos. El documento se guarda completo y se muestra enmascarado."
    />
  );

  if (!puedeVer) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para ver los funcionarios."
        />
      </PageContent>
    );
  }

  const manejarCambioFiltros = (action: () => void) => {
    action();
    setPagina(1);
  };

  const manejarRegistro = (evento: React.FormEvent<HTMLFormElement>) => {
    evento.preventDefault();
    setFieldErrors({});
    setFormError(null);
    const entrada: FuncionarioEntrada = {
      nombre,
      tipo_documento: tipoDocumento,
      numero_documento: numeroDocumento,
    };
    registrarFuncionario.mutate(entrada);
  };

  return (
    <PageContent>
      {cabecera}

      <form
        role="search"
        aria-label="Filtrar funcionarios"
        className="mb-6"
        onSubmit={(evento) => evento.preventDefault()}
      >
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="flex flex-col gap-1">
            <span className="text-sm font-medium text-text-700">Buscar</span>
            <input
              type="text"
              className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              value={texto}
              onChange={(evento) =>
                manejarCambioFiltros(() => setTexto(evento.target.value))
              }
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-sm font-medium text-text-700">Estado</span>
            <select
              className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              value={estado}
              onChange={(evento) =>
                manejarCambioFiltros(() =>
                  setEstado(evento.target.value as EstadoFuncionario | ""),
                )
              }
            >
              <option value="">Todos</option>
              <option value="ACTIVO">{ETIQUETAS_ESTADO_FUNCIONARIO.ACTIVO}</option>
              <option value="INACTIVO">
                {ETIQUETAS_ESTADO_FUNCIONARIO.INACTIVO}
              </option>
            </select>
          </label>
        </div>
      </form>

      {puedeGestionar ? (
        <section aria-labelledby="registrar-funcionario-titulo" className="mb-8">
          <h2
            id="registrar-funcionario-titulo"
            className="mb-4 text-lg font-semibold text-text-900"
          >
            Registrar funcionario
          </h2>
          <form
            onSubmit={manejarRegistro}
            className="grid gap-4 rounded-md border border-border-subtle bg-surface-0 p-4 sm:grid-cols-3"
          >
            <label className="flex flex-col gap-1">
              <span className="text-sm font-medium text-text-700">
                Nombre completo
              </span>
              <input
                type="text"
                className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                value={nombre}
                onChange={(evento) => setNombre(evento.target.value)}
                minLength={3}
                maxLength={200}
                required
              />
              {fieldErrors.nombre ? (
                <span role="alert" className="text-sm text-danger-600">
                  {fieldErrors.nombre}
                </span>
              ) : null}
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-sm font-medium text-text-700">
                Tipo de documento
              </span>
              <select
                className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                value={tipoDocumento}
                onChange={(evento) =>
                  setTipoDocumento(
                    evento.target.value as TipoDocumentoFuncionario,
                  )
                }
                required
              >
                <option value="">Seleccione</option>
                <option value="V">
                  {ETIQUETAS_TIPO_DOCUMENTO_FUNCIONARIO.V}
                </option>
                <option value="E">
                  {ETIQUETAS_TIPO_DOCUMENTO_FUNCIONARIO.E}
                </option>

                <option value="P">
                  {ETIQUETAS_TIPO_DOCUMENTO_FUNCIONARIO.P}
                </option>
              </select>
              {fieldErrors.tipo_documento ? (
                <span role="alert" className="text-sm text-danger-600">
                  {fieldErrors.tipo_documento}
                </span>
              ) : null}
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-sm font-medium text-text-700">
                Número de documento
              </span>
              <input
                type="text"
                className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                value={numeroDocumento}
                onChange={(evento) => setNumeroDocumento(evento.target.value)}
                minLength={5}
                maxLength={20}
                pattern="^[0-9A-Za-z-]{5,20}$"
                required
              />
              {fieldErrors.numero_documento ? (
                <span role="alert" className="text-sm text-danger-600">
                  {fieldErrors.numero_documento}
                </span>
              ) : null}
            </label>
            {formError ? (
              <div role="alert" className="text-sm text-danger-600 sm:col-span-3">
                {formError}
              </div>
            ) : null}
            <div className="sm:col-span-3">
              <button
                type="submit"
                className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
                disabled={registrarFuncionario.isPending}
              >
                {registrarFuncionario.isPending
                  ? "Registrando…"
                  : "Registrar funcionario"}
              </button>
            </div>
          </form>
        </section>
      ) : null}

      {consultaFuncionarios.isLoading ? (
        <LoadingState label="Cargando funcionarios…" />
      ) : consultaFuncionarios.isError ? (
        (() => {
          const error = consultaFuncionarios.error;
          if (
            error instanceof ApiError &&
            error.status === 403 &&
            error.code === "MODULE_NOT_ENTITLED"
          ) {
            return (
              <EmptyState
                title="Módulo no habilitado"
                description="El módulo de Gobierno no está habilitado en la licencia."
              />
            );
          }
          if (error instanceof ApiError && error.status === 403) {
            return (
              <EmptyState
                title="Sin acceso"
                description="No tiene permiso para ver los funcionarios."
              />
            );
          }
          return (
            <ErrorDeCarga
              message="No fue posible cargar los funcionarios."
              onRetry={() => void consultaFuncionarios.refetch()}
            />
          );
        })()
      ) : !consultaFuncionarios.data ? (
        <EmptyState title="Aún no hay funcionarios" />
      ) : consultaFuncionarios.data.items.length === 0 ? (
        <EmptyState title="Aún no hay funcionarios" />
      ) : (
        <>
          <div
            className="relative overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Tabla de funcionarios del ente"
          >
            <table className="w-full min-w-[640px] border-collapse text-sm">
              <caption className="sr-only">Funcionarios del ente</caption>
              <thead>
                <tr className="border-b border-border-default text-left text-text-600">
                  <th scope="col" className="px-3 py-2 font-medium">
                    Código
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Nombre
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Documento
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Estado
                  </th>
                </tr>
              </thead>
              <tbody>
                {consultaFuncionarios.data.items.map((funcionario) => (
                  <tr
                    key={funcionario.id}
                    className="border-b border-border-subtle align-top"
                  >
                    <td className="px-3 py-2">
                      <Link
                        to={`/gobierno/ocupacion/funcionarios/${funcionario.id}`}
                        aria-label={`Abrir el funcionario ${funcionario.codigo}`}
                        className="font-medium text-brand-700 underline"
                      >
                        {funcionario.codigo}
                      </Link>
                    </td>
                    <td className="px-3 py-2 text-text-900">
                      {funcionario.nombre}
                    </td>
                    <td className="px-3 py-2">
                      {funcionario.documento}
                    </td>
                    <td className="px-3 py-2">
                      {ETIQUETAS_ESTADO_FUNCIONARIO[funcionario.estado]}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 flex items-center justify-between">
            <button
              type="button"
              className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100 disabled:opacity-50"
              onClick={() =>
                setPagina((actual) => Math.max(1, actual - 1))
              }
              disabled={pagina === 1}
            >
              Anterior
            </button>
            <span className="text-sm text-text-600">
              Página {pagina} de {Math.max(1, Math.ceil(consultaFuncionarios.data.total / consultaFuncionarios.data.por_pagina))}
            </span>
            <button
              type="button"
              className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100 disabled:opacity-50"
              onClick={() => setPagina((actual) => actual + 1)}
              disabled={pagina >= Math.max(1, Math.ceil(consultaFuncionarios.data.total / consultaFuncionarios.data.por_pagina))}
            >
              Siguiente
            </button>
          </div>
        </>
      )}
    </PageContent>
  );
}
