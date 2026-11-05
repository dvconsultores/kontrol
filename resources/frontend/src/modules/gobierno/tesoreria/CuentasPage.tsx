import { useState } from "react";
import { Link } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import {
  CONSULTA_CUENTAS,
  ETIQUETAS_ESTADO_CUENTA,
  ETIQUETAS_TIPO_CUENTA,
  MONEDAS_CUENTA,
  consultaDeCuentas,
} from "@/modules/gobierno/api";
import type {
  BancosListado,
  CuentasListado,
  CuentasOpciones,
  EstadoCuenta,
  MonedaCuenta,
} from "@/modules/gobierno/api";

export function CuentasPage(): React.JSX.Element {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const [estado, setEstado] = useState<EstadoCuenta | "">("");
  const [bancoId, setBancoId] = useState("");
  const [moneda, setMoneda] = useState<MonedaCuenta | "">("");
  const [cargoId, setCargoId] = useState("");

  const puedeVer = tiene("gobierno_cuentas:view", "empresa");
  const puedeGestionar = tiene("gobierno_cuentas:manage", "empresa");

  const consultaBancos = useQuery({
    queryKey: [...CONSULTA_CUENTAS, "bancos", activeCompanyId],
    queryFn: () => apiFetch<BancosListado>("/gobierno/tesoreria/bancos"),
    enabled: puedeVer && Boolean(activeCompanyId),
    retry: false,
  });

  const consultaOpciones = useQuery({
    queryKey: [...CONSULTA_CUENTAS, "opciones", activeCompanyId],
    queryFn: () => apiFetch<CuentasOpciones>("/gobierno/tesoreria/opciones"),
    enabled: puedeVer && Boolean(activeCompanyId),
    retry: false,
  });

  const consultaCuentas = useQuery({
    queryKey: [
      ...CONSULTA_CUENTAS,
      "cuentas",
      activeCompanyId,
      estado,
      bancoId,
      moneda,
      cargoId,
    ],
    queryFn: () =>
      apiFetch<CuentasListado>(
        `/gobierno/tesoreria/cuentas${consultaDeCuentas({
          estado,
          banco_id: bancoId,
          moneda,
          cargo_id: cargoId,
        })}`,
      ),
    enabled: puedeVer && Boolean(activeCompanyId),
    retry: false,
  });

  const cabecera = (
    <PageHeader
      crumbs={[{ label: "Gobierno" }, { label: "Tesorería" }]}
      title="Cuentas bancarias"
      description="Cuentas del ente con su banco, moneda, autorizados y acto habilitante."
      actions={
        <div className="flex flex-wrap items-center gap-2">
          {puedeGestionar ? (
            <Link
              to="/gobierno/tesoreria/cuentas/nueva"
              className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
            >
              Nueva cuenta
            </Link>
          ) : null}
          <Link
            to="/gobierno/tesoreria/bancos"
            className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
          >
            Bancos
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
          description="No tiene permiso para ver las cuentas bancarias."
        />
      </PageContent>
    );
  }

  if (consultaCuentas.isLoading) {
    return (
      <PageContent>
        {cabecera}
        <LoadingState label="Cargando cuentas…" />
      </PageContent>
    );
  }

  if (consultaCuentas.isError) {
    const error = consultaCuentas.error;
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
            description="No tiene permiso para ver las cuentas bancarias."
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        {cabecera}
        <ErrorState
          message="No fue posible cargar las cuentas."
          onRetry={() => void consultaCuentas.refetch()}
        />
      </PageContent>
    );
  }

  if (!consultaCuentas.data) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState
          title="No hay cuentas bancarias"
          description="Registre la primera cuenta del ente."
          action={
            puedeGestionar ? (
              <Link
                to="/gobierno/tesoreria/cuentas/nueva"
                className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
              >
                Nueva cuenta
              </Link>
            ) : undefined
          }
        />
      </PageContent>
    );
  }

  const cuentas = consultaCuentas.data.items;
  const resumen = consultaCuentas.data.resumen;
  const bancos = consultaBancos.data?.items ?? [];
  const cargos = consultaOpciones.data?.cargos ?? [];
  const hayFiltros = Boolean(estado || bancoId || moneda || cargoId);

  const alternarEstado = (nuevoEstado: EstadoCuenta) => {
    setEstado((actual) => (actual === nuevoEstado ? "" : nuevoEstado));
  };

  return (
    <PageContent>
      {cabecera}

      <section aria-labelledby="resumen-cuentas-titulo" className="mb-8">
        <h2 id="resumen-cuentas-titulo" className="sr-only">
          Resumen
        </h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <button
            type="button"
            onClick={() => alternarEstado("VIGENTE")}
            aria-pressed={estado === "VIGENTE"}
            className="rounded-md border border-border-subtle bg-surface-0 p-4 text-left"
          >
            <span className="block text-2xl font-semibold">
              {resumen.vigentes}
            </span>
            <span className="text-sm text-text-600">Vigentes</span>
          </button>
          <button
            type="button"
            onClick={() => alternarEstado("BORRADOR")}
            aria-pressed={estado === "BORRADOR"}
            className="rounded-md border border-border-subtle bg-surface-0 p-4 text-left"
          >
            <span className="block text-2xl font-semibold">
              {resumen.borradores}
            </span>
            <span className="text-sm text-text-600">Borradores</span>
          </button>
          <button
            type="button"
            onClick={() => alternarEstado("INACTIVA")}
            aria-pressed={estado === "INACTIVA"}
            className="rounded-md border border-border-subtle bg-surface-0 p-4 text-left"
          >
            <span className="block text-2xl font-semibold">
              {resumen.inactivas}
            </span>
            <span className="text-sm text-text-600">Inactivas</span>
          </button>
          <button
            type="button"
            onClick={() => alternarEstado("CERRADA")}
            aria-pressed={estado === "CERRADA"}
            className="rounded-md border border-border-subtle bg-surface-0 p-4 text-left"
          >
            <span className="block text-2xl font-semibold">
              {resumen.cerradas}
            </span>
            <span className="text-sm text-text-600">Cerradas</span>
          </button>
        </div>
      </section>

      <form role="search" aria-label="Filtrar cuentas" className="mb-6" onSubmit={(evento) => evento.preventDefault()}>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <label className="flex max-w-xs flex-col gap-1">
            <span className="text-sm font-medium text-text-700">Estado</span>
            <select
              className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              value={estado}
              onChange={(evento) =>
                setEstado(evento.target.value as EstadoCuenta | "")
              }
            >
              <option value="">Todos</option>
              <option value="BORRADOR">
                {ETIQUETAS_ESTADO_CUENTA.BORRADOR}
              </option>
              <option value="VIGENTE">
                {ETIQUETAS_ESTADO_CUENTA.VIGENTE}
              </option>
              <option value="INACTIVA">
                {ETIQUETAS_ESTADO_CUENTA.INACTIVA}
              </option>
              <option value="CERRADA">
                {ETIQUETAS_ESTADO_CUENTA.CERRADA}
              </option>
            </select>
          </label>
          <label className="flex max-w-xs flex-col gap-1">
            <span className="text-sm font-medium text-text-700">Banco</span>
            <select
              className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              value={bancoId}
              onChange={(evento) => setBancoId(evento.target.value)}
            >
              <option value="">Todos</option>
              {bancos.map((banco) => (
                <option key={banco.id} value={banco.id}>
                  {banco.nombre}
                </option>
              ))}
            </select>
          </label>
          <label className="flex max-w-xs flex-col gap-1">
            <span className="text-sm font-medium text-text-700">Moneda</span>
            <select
              className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              value={moneda}
              onChange={(evento) =>
                setMoneda(evento.target.value as MonedaCuenta | "")
              }
            >
              <option value="">Todos</option>
              {MONEDAS_CUENTA.map((monedaCuenta) => (
                <option key={monedaCuenta} value={monedaCuenta}>
                  {monedaCuenta}
                </option>
              ))}
            </select>
          </label>
          <label className="flex max-w-xs flex-col gap-1">
            <span className="text-sm font-medium text-text-700">
              Cargo autorizado
            </span>
            <select
              className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              value={cargoId}
              onChange={(evento) => setCargoId(evento.target.value)}
            >
              <option value="">Todos</option>
              {cargos.map((cargo) => (
                <option key={cargo.id} value={cargo.id}>
                  {`${cargo.codigo} · ${cargo.denominacion}`}
                </option>
              ))}
            </select>
          </label>
        </div>
      </form>

      {cuentas.length === 0 ? (
        hayFiltros ? (
          <EmptyState
            title="No hay cuentas bancarias"
            description="No hay cuentas con estos filtros."
          />
        ) : (
          <EmptyState
            title="No hay cuentas bancarias"
            description="Registre la primera cuenta del ente."
            action={
              puedeGestionar ? (
                <Link
                  to="/gobierno/tesoreria/cuentas/nueva"
                  className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
                >
                  Nueva cuenta
                </Link>
              ) : undefined
            }
          />
        )
      ) : (
        <div
          className="relative overflow-x-auto"
          tabIndex={0}
          role="region"
          aria-label="Tabla de cuentas bancarias"
        >
          <table className="w-full min-w-[900px] border-collapse text-sm">
            <caption className="sr-only">
              Cuentas bancarias del ente
            </caption>
            <thead>
              <tr className="border-b border-border-default text-left text-text-600">
                <th scope="col" className="px-3 py-2 font-medium">
                  Código
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Denominación
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Banco
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Tipo
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Moneda
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Número
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Estado
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Autorizados
                </th>
              </tr>
            </thead>
            <tbody>
              {cuentas.map((cuenta) => {
                const estadoTexto = ETIQUETAS_ESTADO_CUENTA[cuenta.estado];
                const detallesEstado = [
                  cuenta.acto_sin_efecto ? "Acto sin efecto" : "",
                  cuenta.estado === "VIGENTE" && !cuenta.en_vigor
                    ? "Fuera de vigencia"
                    : "",
                ].filter(Boolean);

                return (
                  <tr
                    key={cuenta.id}
                    className="border-b border-border-subtle align-top"
                  >
                    <td className="px-3 py-2">
                      <Link
                        to={`/gobierno/tesoreria/cuentas/${cuenta.id}`}
                        aria-label={`Abrir la cuenta ${cuenta.codigo}`}
                        className="font-medium text-brand-700 underline"
                      >
                        {cuenta.codigo}
                      </Link>
                    </td>
                    <td className="px-3 py-2 text-text-900">
                      {cuenta.denominacion}
                    </td>
                    <td className="px-3 py-2">{cuenta.banco_nombre}</td>
                    <td className="px-3 py-2">
                      {ETIQUETAS_TIPO_CUENTA[cuenta.tipo]}
                    </td>
                    <td className="px-3 py-2">{cuenta.moneda}</td>
                    <td className="px-3 py-2">{cuenta.numero_enmascarado}</td>
                    <td className="px-3 py-2">
                      {`${estadoTexto}${
                        detallesEstado.length > 0
                          ? ` · ${detallesEstado.join(" · ")}`
                          : ""
                      }`}
                    </td>
                    <td className="px-3 py-2">
                      {cuenta.autorizados_en_vigor}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </PageContent>
  );
}
