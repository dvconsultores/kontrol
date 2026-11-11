import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { apiFetch } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { EmptyState } from "@/components/EmptyState";
import { LoadingState } from "@/components/LoadingState";
import { PageHeader } from "@/components/PageHeader";
import { PageContent } from "@/layout/PageContent";
import { formatearFecha } from "@/i18n";
import { ErrorDeCarga } from "@/modules/gobierno/ocupacion/ErrorDeCarga";
import {
  CONSULTA_GOBIERNO,
  ETIQUETA_ACCION,
  ETIQUETA_MATERIA,
} from "@/modules/gobierno/api";

// Tipos equivalentes al contrato pydantic
type Competencia = {
  accion: string;
  materia: string;
};

type Ocupacion = {
  cargo: string;
  cargo_codigo: string;
  figura_etiqueta: string;
  unidad: string;
  competencias: Competencia[];
};

type Identidad = {
  vinculo_codigo: string | null;
  funcionario: string | null;
  ocupaciones: Ocupacion[];
  tiene_autoridad: boolean;
  motivo: string | null;
  motivo_etiqueta: string | null;
};

type Origen = {
  fuente: "INSTALACION" | "ASIGNACION" | "NO_REGISTRADO";
  actor: string | null;
  fecha: string | null;
};

type Rol = {
  codigo: string;
  nombre: string;
  protegido: boolean;
  tipo: "TECNICO" | "FUNCIONAL";
  alcance: "TODAS" | "ENTE";
  capacidades: number;
  categorias: string[];
  origen: Origen;
};

type Administrador = {
  usuario: string;
  estado: string;
  separacion:
    | "SOLO_TECNICO"
    | "TECNICO_Y_FUNCIONAL_CON_AUTORIDAD"
    | "TECNICO_Y_FUNCIONAL_SIN_AUTORIDAD";
  separacion_etiqueta: string;
  separacion_detalle: string;
  roles: Rol[];
  identidad: Identidad;
};

type RolProtegido = {
  codigo: string;
  nombre: string;
  capacidades: number;
  fuera_de_lugar: string[];
};

type Integridad = {
  integra: boolean;
  admin: RolProtegido | null;
  funcional: RolProtegido | null;
};

type Exigencia = {
  activa: boolean;
  version: number;
  efecto: string;
};

type Denegacion = {
  id: string;
  fecha: string;
  usuario: string | null;
  accion: string;
  codigo: string | null;
  codigo_etiqueta: string;
  rol: string | null;
  capacidades_excedidas: string[];
  en_bitacora: boolean;
};

type Separacion = {
  ente: string;
  integridad: Integridad;
  exigencia_identidad: Exigencia;
  administradores: Administrador[];
  denegaciones: Denegacion[];
};

function formatearOrigen(origen: Origen): string {
  switch (origen.fuente) {
    case "INSTALACION":
      return "Concedido en la instalación";
    case "ASIGNACION":
      if (origen.actor && origen.fecha) {
        return `Concedido por ${origen.actor} el ${formatearFecha(origen.fecha)}`;
      }
      if (origen.fecha) {
        return `Concedido el ${formatearFecha(origen.fecha)}`;
      }
      return "Concedido";
    case "NO_REGISTRADO":
      return "Origen no registrado";
  }
}

function sanearUsuario(usuario: string): string {
  return usuario.replace(/[^a-zA-Z0-9_-]/g, "-");
}

export function SeparacionPage() {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const puedeVer = tiene("gobierno_auditoria:view", "empresa");

  const separacionQuery = useQuery({
    queryKey: [...CONSULTA_GOBIERNO, "control", "separacion", activeCompanyId],
    queryFn: () => apiFetch<Separacion>("/gobierno/control/separacion"),
    enabled: puedeVer && Boolean(activeCompanyId),
    retry: false,
  });

  if (!puedeVer) {
    return (
      <PageContent>
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para ver esta información"
        />
      </PageContent>
    );
  }

  if (!activeCompanyId) {
    return (
      <PageContent>
        <EmptyState
          title="Sin empresa"
          description="Selecciona una empresa para continuar."
        />
      </PageContent>
    );
  }

  if (separacionQuery.isLoading) {
    return (
      <PageContent>
        <PageHeader
          crumbs={[{ label: "Gobierno" }, { label: "Separación técnica y funcional" }]}
          title="Separación técnica y funcional"
          description="Quien administra la plataforma no obtiene por ello autoridad de negocio. Esta vista muestra, para cada administrador técnico, de dónde viene cada permiso y si ejerce un cargo."
        />
        <LoadingState />
      </PageContent>
    );
  }

  if (separacionQuery.isError) {
    const error = separacionQuery.error as { status?: number };
    const mensaje =
      error?.status === 403
        ? "No tiene permiso para ver esta información"
        : "No se pudo cargar la separación técnica y funcional.";
    return (
      <PageContent>
        <PageHeader
          crumbs={[{ label: "Gobierno" }, { label: "Separación técnica y funcional" }]}
          title="Separación técnica y funcional"
          description="Quien administra la plataforma no obtiene por ello autoridad de negocio. Esta vista muestra, para cada administrador técnico, de dónde viene cada permiso y si ejerce un cargo."
        />
        <ErrorDeCarga
          message={mensaje}
          onRetry={() => separacionQuery.refetch()}
        />
      </PageContent>
    );
  }

  const datos = separacionQuery.data;

  if (!datos) {
    return (
      <PageContent>
        <PageHeader
          crumbs={[{ label: "Gobierno" }, { label: "Separación técnica y funcional" }]}
          title="Separación técnica y funcional"
          description="Quien administra la plataforma no obtiene por ello autoridad de negocio. Esta vista muestra, para cada administrador técnico, de dónde viene cada permiso y si ejerce un cargo."
        />
        <EmptyState
          title="Sin datos"
          description="No hay información disponible."
        />
      </PageContent>
    );
  }

  const { integridad, exigencia_identidad, administradores, denegaciones } = datos;

  return (
    <PageContent>
      <PageHeader
        crumbs={[{ label: "Gobierno" }, { label: "Separación técnica y funcional" }]}
        title="Separación técnica y funcional"
        description="Quien administra la plataforma no obtiene por ello autoridad de negocio. Esta vista muestra, para cada administrador técnico, de dónde viene cada permiso y si ejerce un cargo."
      />

      <section aria-labelledby="sec-integridad" className="mb-8">
        <h2 id="sec-integridad" className="mb-4 text-lg font-semibold text-text-900">
          Integridad de la separación
        </h2>
        <div className="space-y-3 text-sm text-text-800">
          <p>
            {integridad.integra ? "Separación íntegra" : "Separación alterada"}
          </p>
          {integridad.admin && (
            <p>
              {integridad.admin.fuera_de_lugar.length === 0 ? (
                `El rol ${integridad.admin.nombre} tiene ${integridad.admin.capacidades} capacidades, todas técnicas.`
              ) : (
                <>
                  El rol {integridad.admin.nombre} tiene capacidades de negocio:{" "}
                  {integridad.admin.fuera_de_lugar.join(", ")}
                </>
              )}
            </p>
          )}
          {integridad.funcional && (
            <p>
              {integridad.funcional.fuera_de_lugar.length === 0 ? (
                `${integridad.funcional.nombre} tiene ${integridad.funcional.capacidades} capacidades, ninguna técnica.`
              ) : (
                <>
                  {integridad.funcional.nombre} tiene capacidades técnicas:{" "}
                  {integridad.funcional.fuera_de_lugar.join(", ")}
                </>
              )}
            </p>
          )}
          <p>
            Exigencia de identidad institucional:{" "}
            {exigencia_identidad.activa ? "Activa" : "Inactiva"}
          </p>
          <p className="text-text-600">{exigencia_identidad.efecto}</p>
        </div>
      </section>

      <section aria-labelledby="sec-administradores" className="mb-8">
        <h2 id="sec-administradores" className="mb-4 text-lg font-semibold text-text-900">
          Administradores técnicos
        </h2>
        {administradores.length === 0 ? (
          <EmptyState
            title="Sin administradores"
            description="No hay administradores técnicos con acceso a este ente."
          />
        ) : (
          <div className="space-y-6">
            {administradores.map((admin) => (
              <article
                key={admin.usuario}
                aria-labelledby={`adm-${sanearUsuario(admin.usuario)}`}
                className="rounded-lg border border-border-subtle p-4"
              >
                <h3
                  id={`adm-${sanearUsuario(admin.usuario)}`}
                  className="mb-2 text-base font-semibold text-text-900 break-words"
                >
                  {admin.usuario}
                </h3>
                <p className="text-sm text-text-800">
                  Estado de la cuenta:{" "}
                  {admin.estado === "ACTIVE" ? "Activa" : admin.estado}
                </p>
                <p className="mt-2 text-sm text-text-800">
                  <strong>{admin.separacion_etiqueta}</strong>
                </p>
                <p className="text-sm text-text-600">{admin.separacion_detalle}</p>

                <div className="mt-4">
                  <h4 className="text-sm font-medium text-text-900">Roles técnicos</h4>
                  {admin.roles.filter((r) => r.tipo === "TECNICO").length === 0 ? (
                    <p className="text-sm text-text-600">Ninguno</p>
                  ) : (
                    <ul className="mt-1 space-y-2">
                      {admin.roles
                        .filter((r) => r.tipo === "TECNICO")
                        .map((rol) => (
                          <li key={rol.codigo} className="text-sm text-text-800 break-words">
                            {rol.nombre} ({rol.codigo})
                            {rol.protegido && " · protegido"}
                            {rol.alcance === "TODAS"
                              ? " · Todas las empresas"
                              : " · Este ente"}
                            {" · "}
                            {rol.capacidades} capacidades
                            {rol.categorias.length > 0 &&
                              ` · ${rol.categorias.join(", ")}`}
                            {" · "}
                            {formatearOrigen(rol.origen)}
                          </li>
                        ))}
                    </ul>
                  )}
                </div>

                <div className="mt-4">
                  <h4 className="text-sm font-medium text-text-900">Roles de negocio</h4>
                  {admin.roles.filter((r) => r.tipo === "FUNCIONAL").length === 0 ? (
                    <p className="text-sm text-text-600">Ninguno</p>
                  ) : (
                    <ul className="mt-1 space-y-2">
                      {admin.roles
                        .filter((r) => r.tipo === "FUNCIONAL")
                        .map((rol) => (
                          <li key={rol.codigo} className="text-sm text-text-800 break-words">
                            {rol.nombre} ({rol.codigo})
                            {rol.protegido && " · protegido"}
                            {rol.alcance === "TODAS"
                              ? " · Todas las empresas"
                              : " · Este ente"}
                            {" · "}
                            {rol.capacidades} capacidades
                            {rol.categorias.length > 0 &&
                              ` · ${rol.categorias.join(", ")}`}
                            {" · "}
                            {formatearOrigen(rol.origen)}
                          </li>
                        ))}
                    </ul>
                  )}
                </div>

                <div className="mt-4">
                  <h4 className="text-sm font-medium text-text-900">
                    Identidad institucional
                  </h4>
                  {admin.identidad.funcionario ? (
                    <p className="text-sm text-text-800">
                      Funcionario: {admin.identidad.funcionario} (vínculo{" "}
                      {admin.identidad.vinculo_codigo})
                    </p>
                  ) : (
                    <p className="text-sm text-text-600">
                      Sin vínculo institucional vigente
                    </p>
                  )}
                  {admin.identidad.ocupaciones.length > 0 && (
                    <ul className="mt-2 space-y-2">
                      {admin.identidad.ocupaciones.map((ocupacion, idx) => (
                        <li key={idx} className="text-sm text-text-800 break-words">
                          {ocupacion.figura_etiqueta} de {ocupacion.cargo} (
                          {ocupacion.cargo_codigo}), {ocupacion.unidad}
                          {ocupacion.competencias.length > 0 && (
                            <ul className="ml-4 mt-1 list-disc">
                              {ocupacion.competencias.map((comp, compIdx) => (
                                <li key={compIdx} className="text-sm text-text-700">
                                  {(ETIQUETA_ACCION as Record<string, string>)[comp.accion] ??
                                    comp.accion}{" "}
                                  ·{" "}
                                  {(ETIQUETA_MATERIA as Record<string, string>)[comp.materia] ??
                                    comp.materia}
                                </li>
                              ))}
                            </ul>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                  {!admin.identidad.tiene_autoridad && (
                    <p className="mt-2 text-sm text-text-700">
                      Autoridad institucional: ninguna —{" "}
                      {admin.identidad.motivo_etiqueta ?? "Sin motivo"}
                    </p>
                  )}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <section aria-labelledby="sec-denegaciones">
        <h2 id="sec-denegaciones" className="mb-4 text-lg font-semibold text-text-900">
          Intentos denegados
        </h2>
        {denegaciones.length === 0 ? (
          <EmptyState
            title="Sin intentos"
            description="No hay intentos denegados."
          />
        ) : (
          <>
            <div
              className="hidden md:block relative overflow-x-auto"
              tabIndex={0}
              role="region"
              aria-label="Tabla de intentos denegados"
            >
              <table className="w-full border-collapse text-sm">
                <caption className="sr-only">Intentos denegados</caption>
                <thead>
                  <tr className="border-b border-border-subtle text-left">
                    <th className="px-3 py-2 font-medium text-text-700">Fecha</th>
                    <th className="px-3 py-2 font-medium text-text-700">Usuario</th>
                    <th className="px-3 py-2 font-medium text-text-700">Intento</th>
                    <th className="px-3 py-2 font-medium text-text-700">Motivo</th>
                    <th className="px-3 py-2 font-medium text-text-700">Capacidades</th>
                    <th className="px-3 py-2 font-medium text-text-700">Bitácora</th>
                  </tr>
                </thead>
                <tbody>
                  {denegaciones.map((denegacion) => (
                    <tr key={denegacion.id} className="border-b border-border-subtle">
                      <td className="px-3 py-2">{formatearFecha(denegacion.fecha)}</td>
                      <td className="px-3 py-2 break-words">{denegacion.usuario ?? "—"}</td>
                      <td className="px-3 py-2 break-words">
                        {denegacion.rol ?? denegacion.accion}
                      </td>
                      <td className="px-3 py-2 break-words">
                        {denegacion.codigo_etiqueta}
                      </td>
                      <td className="px-3 py-2 break-words">
                        {denegacion.capacidades_excedidas.join(", ") || "—"}
                      </td>
                      <td className="px-3 py-2">
                        {denegacion.en_bitacora && (
                          <Link
                            to={`/gobierno/bitacora/${denegacion.id}`}
                            className="font-medium text-brand-700 underline"
                            aria-label={`Ver en la bitácora el intento de ${
                              denegacion.usuario ?? "usuario desconocido"
                            } del ${formatearFecha(denegacion.fecha)}`}
                          >
                            Ver en la bitácora
                          </Link>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <ul className="md:hidden space-y-4">
              {denegaciones.map((denegacion) => (
                <li
                  key={denegacion.id}
                  className="rounded-lg border border-border-subtle p-4"
                >
                  <p className="text-sm text-text-800">
                    <strong>Fecha:</strong> {formatearFecha(denegacion.fecha)}
                  </p>
                  <p className="text-sm text-text-800 break-words">
                    <strong>Usuario:</strong> {denegacion.usuario ?? "—"}
                  </p>
                  <p className="text-sm text-text-800 break-words">
                    <strong>Intento:</strong> {denegacion.rol ?? denegacion.accion}
                  </p>
                  <p className="text-sm text-text-800 break-words">
                    <strong>Motivo:</strong> {denegacion.codigo_etiqueta}
                  </p>
                  <p className="text-sm text-text-800 break-words">
                    <strong>Capacidades:</strong>{" "}
                    {denegacion.capacidades_excedidas.join(", ") || "—"}
                  </p>
                  {denegacion.en_bitacora && (
                    <Link
                      to={`/gobierno/bitacora/${denegacion.id}`}
                      className="mt-2 inline-block text-sm font-medium text-brand-700 underline"
                      aria-label={`Ver en la bitácora el intento de ${
                        denegacion.usuario ?? "usuario desconocido"
                      } del ${formatearFecha(denegacion.fecha)}`}
                    >
                      Ver en la bitácora
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
    </PageContent>
  );
}
