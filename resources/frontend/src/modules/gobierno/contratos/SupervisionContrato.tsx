import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { Button } from "@/components/Button";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { EmptyState } from "@/components/EmptyState";
import { FormField } from "@/components/FormField";
import { formatearFechaDeNegocio, hoyDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_CONTRATOS,
  type DesignacionSupervisor,
  type OpcionesSupervision,
  type Supervision,
} from "./api";

function CampoTexto({ etiqueta, valor }: { etiqueta: string; valor: string }) {
  return (
    <div>
      <dt className="text-sm font-medium text-text-600">{etiqueta}</dt>
      <dd className="break-words text-sm text-text-900">{valor || "—"}</dd>
    </div>
  );
}

function FilaHistorial({ designacion }: { designacion: DesignacionSupervisor }) {
  return (
    <tr className="border-t border-border-subtle">
      <td className="px-3 py-2 text-sm text-text-900">
        {designacion.referencia} · {designacion.estado_etiqueta}
      </td>
      <td className="break-words px-3 py-2 text-sm text-text-900">
        {designacion.funcionario.nombre} · {designacion.funcionario.documento}
      </td>
      <td className="px-3 py-2 text-sm text-text-900">
        {designacion.cargo.codigo} · {designacion.cargo.nombre}
      </td>
      <td className="break-words px-3 py-2 text-sm text-text-900">{designacion.unidad.nombre}</td>
      <td className="break-words px-3 py-2 text-sm text-text-900">{designacion.acto.etiqueta}</td>
      <td className="px-3 py-2 text-sm text-text-900">{formatearFechaDeNegocio(designacion.desde)}</td>
      <td className="px-3 py-2 text-sm text-text-900">
        {designacion.hasta ? formatearFechaDeNegocio(designacion.hasta) : "—"}
      </td>
      <td className="px-3 py-2 text-sm text-text-900">{designacion.situacion_etiqueta} · {designacion.estado_etiqueta}</td>
      <td className="break-words px-3 py-2 text-sm text-text-900">{designacion.motivo ?? "—"}</td>
    </tr>
  );
}

export function SupervisionContrato({ contratoId }: { contratoId: string }) {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const queryClient = useQueryClient();
  const claveSupervision = [...CONSULTA_CONTRATOS, activeCompanyId, "supervision", contratoId];

  const supervisionQuery = useQuery({
    queryKey: claveSupervision,
    queryFn: () => apiFetch<Supervision>(`/gobierno/contratos/${contratoId}/supervision`),
  });

  const [formularioAbierto, setFormularioAbierto] = useState(false);
  const [desde, setDesde] = useState(hoyDeNegocio());
  const [funcionarioId, setFuncionarioId] = useState("");
  const [ocupacionAsignacionId, setOcupacionAsignacionId] = useState("");
  const [actoId, setActoId] = useState("");
  const [motivo, setMotivo] = useState("");
  const [modalConfirmar, setModalConfirmar] = useState(false);
  const [mensajeExito, setMensajeExito] = useState<string | null>(null);
  const [mensajeError, setMensajeError] = useState<string | null>(null);

  const opcionesQuery = useQuery({
    queryKey: [...CONSULTA_CONTRATOS, activeCompanyId, "supervision", contratoId, "opciones", desde],
    queryFn: () =>
      apiFetch<OpcionesSupervision>(
        `/gobierno/contratos/${contratoId}/supervision/opciones?fecha=${desde}`,
      ),
    enabled: formularioAbierto && !!desde,
  });

  if (supervisionQuery.isLoading) {
    return (
      <section aria-labelledby="supervision-titulo" className="mb-6">
        <h2 id="supervision-titulo" className="text-lg font-semibold text-text-900">
          Supervisor / responsable del contrato
        </h2>
        <p className="mt-2 text-sm text-text-600">Cargando la supervisión…</p>
      </section>
    );
  }

  if (supervisionQuery.isError) {
    return (
      <section aria-labelledby="supervision-titulo" className="mb-6">
        <h2 id="supervision-titulo" className="text-lg font-semibold text-text-900">
          Supervisor / responsable del contrato
        </h2>
        <p role="alert" className="mt-2 text-sm text-red-700">
          {supervisionQuery.error instanceof Error
            ? supervisionQuery.error.message
            : "No se pudo cargar la supervisión."}
        </p>
      </section>
    );
  }

  const supervision = supervisionQuery.data!;
  const opciones = opcionesQuery.data;
  const puedeDesignar = tiene("gobierno_contratos:assign_supervisor", "empresa") && supervision.puede_designar;
  const funcionarioSeleccionado = opciones?.funcionarios.find((f) => f.id === funcionarioId);
  const ocupacionSeleccionada = funcionarioSeleccionado?.ocupaciones.find(
    (o) => o.asignacion_id === ocupacionAsignacionId,
  );
  const camposIncompletos =
    !desde || !funcionarioId || !ocupacionAsignacionId || !actoId || (!!supervision.ultima_id && !motivo.trim());

  function limpiarFormulario() {
    setFormularioAbierto(false);
    setDesde(hoyDeNegocio());
    setFuncionarioId("");
    setOcupacionAsignacionId("");
    setActoId("");
    setMotivo("");
    setMensajeError(null);
    setMensajeExito(null);
  }

  function elegirFuncionario(id: string) {
    setFuncionarioId(id);
    const funcionario = opciones?.funcionarios.find((f) => f.id === id);
    if (funcionario && funcionario.ocupaciones.length === 1) {
      setOcupacionAsignacionId(funcionario.ocupaciones[0].asignacion_id);
    } else {
      setOcupacionAsignacionId("");
    }
  }

  async function registrarDesignacion() {
    try {
      const respuesta = await apiFetch<Supervision>(
        `/gobierno/contratos/${contratoId}/supervision/designaciones`,
        {
          method: "POST",
          body: {
            funcionario_id: funcionarioId,
            asignacion_id: ocupacionAsignacionId,
            acto_id: actoId,
            desde,
            motivo: supervision.ultima_id ? motivo : null,
            sustituye_id: supervision.ultima_id,
          },
        },
      );
      setModalConfirmar(false);
      queryClient.setQueryData(claveSupervision, respuesta);
      await queryClient.invalidateQueries({
        queryKey: [...CONSULTA_CONTRATOS, activeCompanyId],
      });
      limpiarFormulario();
      setMensajeExito(`Designación ${(respuesta.programada ?? respuesta.vigente)?.referencia} registrada.`);
    } catch (error) {
      setModalConfirmar(false);
      setMensajeError(
        error instanceof ApiError ? error.message : "No se pudo registrar la designación.",
      );
    }
  }

  return (
    <section aria-labelledby="supervision-titulo" className="mb-6">
      <h2 id="supervision-titulo" className="text-lg font-semibold text-text-900">
        Supervisor / responsable del contrato
      </h2>

      {mensajeExito ? (
        <p role="status" className="mt-2 text-sm text-text-900">
          {mensajeExito}
        </p>
      ) : null}
      {mensajeError ? (
        <p role="alert" className="mt-2 text-sm text-red-700">
          {mensajeError}
        </p>
      ) : null}

      <h3 className="mt-4 text-base font-medium text-text-900">Supervisor vigente</h3>
      {supervision.vigente ? (
        <dl className="mt-3 grid gap-4 sm:grid-cols-2">
          <CampoTexto
            etiqueta="Funcionario"
            valor={`${supervision.vigente.funcionario.nombre} · ${supervision.vigente.funcionario.documento}`}
          />
          <CampoTexto
            etiqueta="Cargo"
            valor={`${supervision.vigente.cargo.codigo} · ${supervision.vigente.cargo.nombre}`}
          />
          <CampoTexto etiqueta="Unidad" valor={supervision.vigente.unidad.nombre} />
          <CampoTexto etiqueta="Figura" valor={supervision.vigente.figura_etiqueta} />
          <CampoTexto
            etiqueta="Desde"
            valor={formatearFechaDeNegocio(supervision.vigente.desde)}
          />
          <CampoTexto etiqueta="Acto de designación" valor={supervision.vigente.acto.etiqueta} />
          <CampoTexto etiqueta="Emitido por" valor={supervision.vigente.acto.emisor_cargo} />
          <CampoTexto
            etiqueta="Designación"
            valor={`${supervision.vigente.referencia} · ${supervision.vigente.estado_etiqueta}`}
          />
        </dl>
      ) : (
        <EmptyState
          title="Sin supervisor designado"
          description="Este contrato aún no tiene supervisor o responsable designado."
        />
      )}
      {supervision.programada && (
        <>
          <h3 className="mt-4 text-base font-medium text-text-900">Designación programada</h3>
          <p className="mt-2 text-sm text-text-900">
            {supervision.programada.funcionario.nombre} · {supervision.programada.cargo.nombre} · desde{" "}
            {formatearFechaDeNegocio(supervision.programada.desde)} · {supervision.programada.referencia}
          </p>
        </>
      )}

      {supervision.historia.length > 0 ? (
        <>
          <h3 className="mt-4 text-base font-medium text-text-900">Historial de supervisores</h3>
          <div className="mt-2 overflow-x-auto" tabIndex={0} role="region" aria-label="Historial de supervisores">
            <table className="w-full border-collapse text-left">
              <caption className="sr-only">Historial de supervisores</caption>
              <thead>
                <tr className="border-b border-border-subtle">
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-600">Designación</th>
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-600">Funcionario</th>
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-600">Cargo</th>
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-600">Unidad</th>
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-600">Acto</th>
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-600">Desde</th>
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-600">Hasta</th>
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-600">Estado</th>
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-600">Motivo</th>
                </tr>
              </thead>
              <tbody>
                {supervision.historia.map((designacion) => (
                  <FilaHistorial key={designacion.id} designacion={designacion} />
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}

      {puedeDesignar ? (
        <div className="mt-4">
          {!formularioAbierto ? (
            <Button
              type="button"
              onClick={() => {
                setFormularioAbierto(true);
                setMensajeError(null);
                setMensajeExito(null);
              }}
            >
              {supervision.ultima_id ? "Sustituir supervisor" : "Nueva designación"}
            </Button>
          ) : (
            <div className="mt-3 grid gap-4 sm:grid-cols-2">
              <FormField label="Fecha efectiva" htmlFor="supervision-desde" required error={undefined}>
                <input
                  id="supervision-desde"
                  type="date"
                  className="w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
                  value={desde}
                  onChange={(event) => setDesde(event.target.value)}
                  required
                />
              </FormField>

              <FormField label="Funcionario" htmlFor="supervision-funcionario" required error={undefined}>
                <select
                  id="supervision-funcionario"
                  className="w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
                  value={funcionarioId}
                  onChange={(event) => elegirFuncionario(event.target.value)}
                  required
                >
                  <option value="">Elija un funcionario</option>
                  {(opciones?.funcionarios ?? []).map((funcionario) => (
                    <option key={funcionario.id} value={funcionario.id}>
                      {funcionario.nombre} · {funcionario.documento}
                    </option>
                  ))}
                </select>
              </FormField>

              <FormField label="Ocupación" htmlFor="supervision-ocupacion" required error={undefined}>
                <select
                  id="supervision-ocupacion"
                  className="w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
                  value={ocupacionAsignacionId}
                  onChange={(event) => setOcupacionAsignacionId(event.target.value)}
                  disabled={!funcionarioId}
                  required
                >
                  <option value="">Elija una ocupación</option>
                  {(funcionarioSeleccionado?.ocupaciones ?? []).map((ocupacion) => (
                    <option key={ocupacion.asignacion_id} value={ocupacion.asignacion_id}>
                      {ocupacion.cargo} · {ocupacion.unidad ?? "—"} · {ocupacion.figura_etiqueta}
                    </option>
                  ))}
                </select>
              </FormField>

              {ocupacionSeleccionada ? (
                <p className="mt-1 text-sm text-text-600">
                  Cargo: {ocupacionSeleccionada.cargo} · Unidad: {ocupacionSeleccionada.unidad ?? "—"}
                </p>
              ) : null}

              <FormField label="Acto de designación" htmlFor="supervision-acto" required error={undefined}>
                <select
                  id="supervision-acto"
                  className="w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
                  value={actoId}
                  onChange={(event) => setActoId(event.target.value)}
                  required
                >
                  <option value="">Elija el acto</option>
                  {(opciones?.actos ?? []).map((acto) => (
                    <option key={acto.id} value={acto.id}>
                      {acto.etiqueta} · {acto.emisor_cargo}
                    </option>
                  ))}
                </select>
              </FormField>

              {supervision.ultima_id ? (
                <FormField label="Motivo del cambio" htmlFor="supervision-motivo" required error={undefined}>
                  <textarea
                    id="supervision-motivo"
                    className="w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
                    value={motivo}
                    onChange={(event) => setMotivo(event.target.value)}
                    maxLength={500}
                    required
                  />
                </FormField>
              ) : null}

              {opciones && opciones.funcionarios.length === 0 ? (
                <p className="mt-2 text-sm text-text-600 sm:col-span-2">
                  No hay funcionarios con ocupación vigente para la fecha efectiva elegida.
                </p>
              ) : null}

              {opciones && opciones.actos.length === 0 ? (
                <p className="mt-2 text-sm text-text-600 sm:col-span-2">
                  No hay actos de designación eficaces emitidos por un cargo con la competencia Aprobar sobre
                  Contrataciones.
                </p>
              ) : null}

              <div className="mt-2 flex gap-3 sm:col-span-2">
                <Button type="button" onClick={() => setModalConfirmar(true)} disabled={camposIncompletos}>
                  Formalizar designación
                </Button>
                <Button type="button" onClick={limpiarFormulario}>
                  Cancelar
                </Button>
              </div>
            </div>
          )}
        </div>
      ) : null}

      <ConfirmationDialog
        open={modalConfirmar}
        title="Formalizar la designación del supervisor"
        description="La designación queda registrada con su acto y no se modifica: un cambio posterior se registra como sustitución."
        confirmLabel="Formalizar"
        cancelLabel="Cancelar"
        onConfirm={async () => {
          await registrarDesignacion();
        }}
        onCancel={() => setModalConfirmar(false)}
      />
    </section>
  );
}
