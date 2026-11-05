import { useState } from "react";
import { Link } from "react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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
import {
  CONSULTA_CUENTAS,
  ETIQUETAS_ESTADO_BANCO,
} from "@/modules/gobierno/api";
import type {
  BancosListado,
  BancoEntrada,
  BancoCambios,
  EstadoBanco,
  Banco,
} from "@/modules/gobierno/api";

export function BancosPage(): React.JSX.Element {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();

  const [codigo, setCodigo] = useState("");
  const [nombre, setNombre] = useState("");
  const [errorCodigo, setErrorCodigo] = useState<string | null>(null);
  const [errorNombre, setErrorNombre] = useState<string | null>(null);
  const [editandoId, setEditandoId] = useState<string | null>(null);
  const [editandoNombre, setEditandoNombre] = useState("");
  const [errorEdicion, setErrorEdicion] = useState<string | null>(null);
  const [avisoVersion, setAvisoVersion] = useState<string | null>(null);

  const puedeVer = tiene("gobierno_cuentas:view", "empresa");
  const puedeGestionar = tiene("gobierno_cuentas:manage", "empresa");

  const consultaBancos = useQuery({
    queryKey: [...CONSULTA_CUENTAS, "bancos", activeCompanyId],
    queryFn: () =>
      apiFetch<BancosListado>(`/gobierno/tesoreria/bancos`),
    enabled: puedeVer && Boolean(activeCompanyId),
    retry: false,
  });

  const crearBanco = useMutation({
    mutationFn: (entrada: BancoEntrada) =>
      apiFetch<Banco>(`/gobierno/tesoreria/bancos`, {
        method: "POST",
        body: entrada,
      }),
    onSuccess: () => {
      setCodigo("");
      setNombre("");
      setErrorCodigo(null);
      setErrorNombre(null);
      void queryClient.invalidateQueries({ queryKey: CONSULTA_CUENTAS });
      notify({ type: "success", title: "Banco registrado" });
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError && error.status === 409 && error.code === "GOV_BANK_CODE_DUPLICATE") {
        setErrorCodigo("Ya existe un banco con este código.");
      } else {
        notify({ type: "error", title: "No fue posible registrar el banco" });
      }
    },
  });

  const actualizarBanco = useMutation({
    mutationFn: ({
      id,
      version,
      cambios,
    }: {
      id: string;
      version: number;
      cambios: BancoCambios;
    }) =>
      apiFetch<Banco>(`/gobierno/tesoreria/bancos/${id}`, {
        method: "PATCH",
        body: cambios,
        ifMatch: String(version),
      }),
    onSuccess: () => {
      setEditandoId(null);
      setEditandoNombre("");
      setErrorEdicion(null);
      setAvisoVersion(null);
      void queryClient.invalidateQueries({ queryKey: CONSULTA_CUENTAS });
      notify({ type: "success", title: "Banco actualizado" });
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError && error.status === 409 && error.code === "GOV_BANK_ACCOUNT_STALE") {
        setAvisoVersion("El banco fue modificado por otra persona. Se recargaron los datos; revise los cambios antes de continuar.");
        void queryClient.invalidateQueries({ queryKey: CONSULTA_CUENTAS });
      } else {
        notify({ type: "error", title: "No fue posible actualizar el banco" });
      }
    },
  });

  const cabecera = (
    <PageHeader
      crumbs={[{ label: "Gobierno" }, { label: "Tesorería" }]}
      title="Bancos"
      description="Catálogo de bancos de Tesorería. Registre cada banco con su código de 4 dígitos."
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <Link
            to="/gobierno/tesoreria/cuentas"
            className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
          >
            Cuentas bancarias
          </Link>
        </div>
      }
    />
  );

  if (!puedeVer) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para ver el catálogo de bancos."
        />
      </PageContent>
    );
  }

  if (consultaBancos.isLoading) {
    return (
      <PageContent>
        {cabecera}
        <LoadingState label="Cargando bancos…" />
      </PageContent>
    );
  }

  if (consultaBancos.isError) {
    const error = consultaBancos.error;
    if (
      error instanceof ApiError &&
      error.status === 403 &&
      error.code === "MODULE_NOT_ENTITLED"
    ) {
      return (
        <PageContent>
          {cabecera}
          <EmptyState
            title="Módulo no habilitado"
            description="El módulo de Gobierno no está habilitado en la licencia."
          />
        </PageContent>
      );
    }
    if (error instanceof ApiError && error.status === 403) {
      return (
        <PageContent>
          {cabecera}
          <EmptyState
            title="Sin acceso"
            description="No tiene permiso para ver el catálogo de bancos."
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        {cabecera}
        <ErrorState
          message="No fue posible cargar los bancos."
          onRetry={() => void consultaBancos.refetch()}
        />
      </PageContent>
    );
  }

  const bancos = consultaBancos.data?.items ?? [];

  const registrarBanco = () => {
    setErrorCodigo(null);
    setErrorNombre(null);

    const codigoLimpio = codigo.trim();
    const nombreLimpio = nombre.trim();

    if (!/^\d{4}$/.test(codigoLimpio)) {
      setErrorCodigo("El código debe tener 4 dígitos");
      return;
    }
    if (nombreLimpio.length < 3) {
      setErrorNombre("El nombre debe tener al menos 3 caracteres");
      return;
    }

    crearBanco.mutate({
      codigo: codigoLimpio,
      nombre: nombreLimpio,
    });
  };

  const iniciarEdicion = (banco: Banco) => {
    setAvisoVersion(null);
    setEditandoId(banco.id);
    setEditandoNombre(banco.nombre);
    setErrorEdicion(null);
  };

  const cancelarEdicion = () => {
    setEditandoId(null);
    setEditandoNombre("");
    setErrorEdicion(null);
  };

  const guardarEdicion = (banco: Banco) => {
    setErrorEdicion(null);
    if (editandoNombre.trim().length < 3) {
      setErrorEdicion("El nombre debe tener al menos 3 caracteres");
      return;
    }
    if (editandoNombre.trim() === banco.nombre) {
      cancelarEdicion();
      return;
    }
    actualizarBanco.mutate({
      id: banco.id,
      version: banco.version,
      cambios: { nombre: editandoNombre.trim() },
    });
  };

  const alternarEstado = (banco: Banco) => {
    setAvisoVersion(null);
    const nuevoEstado: EstadoBanco =
      banco.estado === "ACTIVO" ? "INACTIVO" : "ACTIVO";
    actualizarBanco.mutate({
      id: banco.id,
      version: banco.version,
      cambios: { estado: nuevoEstado },
    });
  };

  return (
    <PageContent>
      {cabecera}

      {avisoVersion ? (
        <div
          role="alert"
          className="mb-6 rounded-md bg-error-50 px-4 py-3 text-sm text-error-800"
        >
          {avisoVersion}
        </div>
      ) : null}

      {puedeGestionar ? (
        <section aria-labelledby="registrar-banco-titulo" className="mb-8">
          <h2 id="registrar-banco-titulo" className="text-lg font-semibold text-text-900 mb-4">
            Registrar banco
          </h2>
          <form
            onSubmit={(evento) => {
              evento.preventDefault();
              registrarBanco();
            }}
            className="relative grid gap-4 sm:grid-cols-[160px_1fr_auto] sm:items-end"
          >
            <FormField
              label="Código"
              required
              error={errorCodigo ?? undefined}
              help="Los 4 primeros dígitos de las cuentas de este banco"
            >
              <TextInput
                id="banco-codigo"
                value={codigo}
                onChange={(evento) => setCodigo(evento.target.value)}
                inputMode="numeric"
                maxLength={4}
                required
              />
            </FormField>
            <FormField
              label="Nombre"
              required
              error={errorNombre ?? undefined}
            >
              <TextInput
                id="banco-nombre"
                value={nombre}
                onChange={(evento) => setNombre(evento.target.value)}
                required
              />
            </FormField>
            <div className="flex items-center">
              <Button type="submit" disabled={crearBanco.isPending}>
                Registrar banco
              </Button>
            </div>
          </form>
        </section>
      ) : null}

      {bancos.length === 0 ? (
        <EmptyState
          title="Aún no hay bancos"
          description="Registre el primero con el formulario de arriba."
        />
      ) : (
        <>
          <div
            className="relative overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Tabla de bancos"
          >
            <table className="w-full min-w-[640px] border-collapse text-sm">
              <caption className="sr-only">Bancos del catálogo</caption>
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
                  {puedeGestionar ? (
                    <th scope="col" className="px-3 py-2 font-medium">
                      Acciones
                    </th>
                  ) : null}
                </tr>
              </thead>
              <tbody>
                {bancos.map((banco) => (
                  <tr
                    key={banco.id}
                    className="border-b border-border-subtle align-top"
                  >
                    <td className="px-3 py-2 font-medium text-text-900">
                      {banco.codigo}
                    </td>
                    <td className="px-3 py-2">
                      {editandoId === banco.id ? (
                        <div className="flex flex-col gap-1">
                          <TextInput
                            value={editandoNombre}
                            onChange={(evento) =>
                              setEditandoNombre(evento.target.value)
                            }
                            aria-label={`Nombre del banco ${banco.nombre}`}
                            aria-invalid={Boolean(errorEdicion)}
                          />
                          {errorEdicion ? (
                            <span className="text-sm text-danger-600">
                              {errorEdicion}
                            </span>
                          ) : null}
                        </div>
                      ) : (
                        <span className="text-text-900">{banco.nombre}</span>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className="inline-flex items-center rounded-full bg-surface-100 px-2 py-0.5 text-xs font-medium text-text-700"
                      >
                        {ETIQUETAS_ESTADO_BANCO[banco.estado]}
                      </span>
                    </td>
                    {puedeGestionar ? (
                      <td className="px-3 py-2">
                        {editandoId === banco.id ? (
                          <div className="flex flex-wrap items-center gap-2">
                            <Button
                              type="button"
                              onClick={() => guardarEdicion(banco)}
                            >
                              Guardar
                            </Button>
                            <button
                              type="button"
                              onClick={cancelarEdicion}
                              className="inline-flex h-8 items-center rounded-md border border-border-default px-2 text-sm font-medium text-text-700 hover:bg-surface-100"
                            >
                              Cancelar
                            </button>
                          </div>
                        ) : (
                          <div className="flex flex-wrap items-center gap-2">
                            <button
                              type="button"
                              onClick={() => iniciarEdicion(banco)}
                              aria-label={`Editar el banco ${banco.nombre}`}
                              className="inline-flex h-8 items-center rounded-md border border-border-default px-2 text-sm font-medium text-text-700 hover:bg-surface-100"
                            >
                              Editar
                            </button>
                            <Button
                              type="button"
                              onClick={() => alternarEstado(banco)}
                              aria-label={
                                banco.estado === "ACTIVO"
                                  ? `Inactivar el banco ${banco.nombre}`
                                  : `Activar el banco ${banco.nombre}`
                              }
                              className="inline-flex h-8 items-center rounded-md border border-border-default px-2 text-sm font-medium text-text-700 hover:bg-surface-100"
                            >
                              {banco.estado === "ACTIVO"
                                ? "Inactivar"
                                : "Activar"}
                            </Button>
                          </div>
                        )}
                      </td>
                    ) : null}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-4 text-sm text-text-600">
            Inactivar un banco no cambia sus cuentas: solo deja de ofrecerse
            para cuentas nuevas.
          </p>
        </>
      )}
    </PageContent>
  );
}
