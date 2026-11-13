import { useState } from "react";
import { Link } from "react-router";

import { apiFetch } from "@/api/client";
import { AsyncButton } from "@/components/AsyncButton";
import { Autorizado } from "@/components/Autorizado";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { useCompany } from "@/app/contexts/CompanyContext";
import { CondicionDelProceso } from "@/modules/compras/recepciones/CondicionDelProceso";
import { ZonaTemporal } from "@/modules/compras/recepciones/ZonaTemporal";
import { useAlmacenesDeEmpresa } from "@/modules/organizacion/almacenes/useAlmacenesDeEmpresa";
import { formatearInstante, instanteDesdeHoraDeCaracas } from "@/lib/fecha-de-negocio";

import { ESTADOS_CONFIRMACION, ESTADOS_RECEPCION, type DetalleImportacion } from "./tipos";

type Props = {
  detalle: DetalleImportacion;
  onCambios: () => void;
};

export function ImportacionRecepcion({ detalle, onCambios }: Props): React.JSX.Element {
  const { activeCompany } = useCompany();
  const almacenesQuery = useAlmacenesDeEmpresa(activeCompany?.id ?? null);
  const almacenes = almacenesQuery.data?.items ?? [];
  const [codigo, setCodigo] = useState("");
  const [almacenId, setAlmacenId] = useState("");
  const [packingList, setPackingList] = useState("");
  const [factura, setFactura] = useState("");
  const [bultosDeclarados, setBultosDeclarados] = useState("");
  const [descargaNueva, setDescargaNueva] = useState("");
  const [errorCrear, setErrorCrear] = useState<string | null>(null);
  const [bultosRecibidos, setBultosRecibidos] = useState<Record<string, string>>({});
  const [errorArribo, setErrorArribo] = useState<string | null>(null);
  const [descargas, setDescargas] = useState<Record<string, string>>({});
  const [errorDescarga, setErrorDescarga] = useState<string | null>(null);

  const recibidas = detalle.logistics?.receipts ?? [];

  async function crearRecepcion() {
    setErrorCrear(null);
    if (!codigo.trim() || !almacenId) {
      setErrorCrear("Código y almacén son obligatorios");
      return;
    }
    try {
      await apiFetch(`/importaciones/${detalle.id}/receipts`, {
        method: "POST",
        body: {
          code: codigo.trim(),
          warehouse_id: almacenId,
          packing_list_ref: packingList.trim() || null,
          supplier_invoice_ref: factura.trim() || null,
          packages_declared: bultosDeclarados ? Number(bultosDeclarados) : null,
          unloading_scheduled_at: descargaNueva ? instanteDesdeHoraDeCaracas(descargaNueva) : null,
        },
      });
      setCodigo("");
      setPackingList("");
      setFactura("");
      setBultosDeclarados("");
      setDescargaNueva("");
      onCambios();
    } catch (err) {
      setErrorCrear(err instanceof Error ? err.message : "No se pudo crear la recepción");
    }
  }

  async function confirmarArribo(recepcionId: string) {
    setErrorArribo(null);
    try {
      const valor = bultosRecibidos[recepcionId];
      await apiFetch(`/purchasing/receipts/${recepcionId}/arrival`, {
        method: "POST",
        body: {
          packages_received: valor ? Number(valor) : null,
        },
      });
      onCambios();
    } catch (err) {
      setErrorArribo(err instanceof Error ? err.message : "No se pudo confirmar el arribo");
    }
  }

  async function programarDescarga(recepcionId: string) {
    setErrorDescarga(null);
    const valor = descargas[recepcionId];
    const instante = valor ? instanteDesdeHoraDeCaracas(valor) : null;
    if (!valor || !instante) {
      setErrorDescarga("Indique la fecha y la hora de la descarga.");
      return;
    }
    try {
      await apiFetch(`/purchasing/receipts/${recepcionId}/unloading-schedule`, {
        method: "POST",
        body: {
          unloading_scheduled_at: instante,
        },
      });
      setDescargas((prev) => ({ ...prev, [recepcionId]: "" }));
      onCambios();
    } catch (err) {
      setErrorDescarga(err instanceof Error ? err.message : "No se pudo programar la descarga");
    }
  }

  return (
    <>
      <section id="arribo" className="mb-8">
        <h2 className="mb-4 text-lg font-semibold text-text-900">Arribo</h2>
        {recibidas.length === 0 ? (
          <p className="text-sm text-text-600">Primero registra la recepción.</p>
        ) : (
          <div className="space-y-4">
            {errorArribo ? (
              <div role="alert" className="rounded-md border border-danger-200 bg-danger-50 p-3 text-sm text-danger-700">
                {errorArribo}
              </div>
            ) : null}
            {errorDescarga ? (
              <div role="alert" className="rounded-md border border-danger-200 bg-danger-50 p-3 text-sm text-danger-700">
                {errorDescarga}
              </div>
            ) : null}
            {recibidas.map((recepcion) => (
              <div key={recepcion.id} className="rounded-md border border-border-default bg-surface-0 p-4">
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="text-text-600">Código:</span> {recepcion.code}
                  </div>
                  <div>
                    <span className="text-text-600">Arribo:</span>{" "}
                    {recepcion.arrival_at ? formatearInstante(recepcion.arrival_at) : "Sin confirmar"}
                  </div>
                  <div>
                    <span className="text-text-600">Bultos:</span>{" "}
                    {recepcion.packages_received ?? recepcion.packages_declared ?? "—"}
                  </div>
                  <div>
                    <span className="text-text-600">Zona temporal:</span>{" "}
                    {recepcion.temporary_location_label ?? "Sin registrar"}
                  </div>
                  <div>
                    <span className="text-text-600">Descarga programada:</span>{" "}
                    {recepcion.unloading_scheduled_at
                      ? formatearInstante(recepcion.unloading_scheduled_at)
                      : "Sin programar"}
                  </div>
                </div>
                {recepcion.can_confirm_arrival ? (
                  <Autorizado operacion={["POST", `/purchasing/receipts/${recepcion.id}/arrival`]}>
                    <div className="mt-4 flex items-end gap-3">
                      <FormField label="Bultos recibidos">
                        <TextInput
                          type="number"
                          min="0"
                          value={bultosRecibidos[recepcion.id] ?? ""}
                          onChange={(e) =>
                            setBultosRecibidos((prev) => ({ ...prev, [recepcion.id]: e.target.value }))
                          }
                        />
                      </FormField>
                      <AsyncButton
                        type="button"
                        onClick={() => confirmarArribo(recepcion.id)}
                      >
                        Confirmar arribo de {recepcion.code}
                      </AsyncButton>
                    </div>
                  </Autorizado>
                ) : null}
                {recepcion.can_schedule_unloading ? (
                  <Autorizado operacion={["POST", `/purchasing/receipts/${recepcion.id}/unloading-schedule`]}>
                    <div className="mt-4 flex items-end gap-3">
                      <FormField label="Nueva descarga programada">
                        <TextInput
                          type="datetime-local"
                          value={descargas[recepcion.id] ?? ""}
                          onChange={(e) =>
                            setDescargas((prev) => ({ ...prev, [recepcion.id]: e.target.value }))
                          }
                        />
                      </FormField>
                      <AsyncButton
                        type="button"
                        onClick={() => programarDescarga(recepcion.id)}
                      >
                        Programar descarga de {recepcion.code}
                      </AsyncButton>
                    </div>
                  </Autorizado>
                ) : null}
                {recepcion.can_set_temporary_location ? (
                  <ZonaTemporal receiptId={recepcion.id} codigo={recepcion.code} onGuardada={onCambios} />
                ) : null}
              </div>
            ))}
          </div>
        )}
      </section>

      <section id="recepcion" className="mb-8">
        <h2 className="mb-4 text-lg font-semibold text-text-900">Recepción</h2>
        {recibidas.length > 0 ? (
          <ul className="space-y-3">
            {recibidas.map((recepcion) => (
              <li key={recepcion.id} className="rounded-md border border-border-default bg-surface-0 p-4">
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="text-text-600">Código:</span> {recepcion.code}
                  </div>
                  <div>
                    <span className="text-text-600">Almacén:</span>{" "}
                    {recepcion.warehouse_name ?? "Sin almacén"}
                  </div>
                  <div>
                    <span className="text-text-600">Estado:</span>{" "}
                    {ESTADOS_RECEPCION[recepcion.status] ?? recepcion.status}
                  </div>
                  <div>
                    <span className="text-text-600">Confirmación:</span>{" "}
                    {recepcion.confirmation_status
                      ? ESTADOS_CONFIRMACION[recepcion.confirmation_status]
                      : "Pendiente"}
                  </div>
                </div>
                <div className="mt-3">
                  <span className="text-sm text-text-600">Condición del proceso:</span>
                  <div className="mt-1">
                    <CondicionDelProceso
                      condicion={recepcion.process_condition}
                      receiptId={recepcion.id}
                      importacionId={detalle.id}
                    />
                  </div>
                </div>
                <Link
                  to={`/compras/recepciones?recepcion=${recepcion.id}&importacion=${detalle.id}`}
                  className="mt-3 inline-block text-sm font-medium text-brand-600 hover:text-brand-700"
                >
                  Abrir recepción {recepcion.code}
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mb-4 text-sm text-text-600">Sin recepciones registradas.</p>
        )}

        {detalle.allowed_actions.create_receipt ? (
          <Autorizado operacion={["POST", `/importaciones/${detalle.id}/receipts`]}>
            <form className="mt-6 space-y-4 rounded-md border border-border-default bg-surface-0 p-4">
              {errorCrear ? (
                <div role="alert" className="rounded-md border border-danger-200 bg-danger-50 p-3 text-sm text-danger-700">
                  {errorCrear}
                </div>
              ) : null}
              <div className="grid grid-cols-2 gap-4">
                <FormField label="Código" required>
                  <TextInput
                    value={codigo}
                    onChange={(e) => setCodigo(e.target.value)}
                  />
                </FormField>
                <FormField label="Almacén" required>
                  <select
                    className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                    value={almacenId}
                    onChange={(e) => setAlmacenId(e.target.value)}
                    required
                  >
                    <option value="" disabled>
                      Selecciona un almacén
                    </option>
                    {almacenes.map((almacen) => (
                      <option key={almacen.id} value={almacen.id}>
                        {almacen.name ?? almacen.code ?? almacen.id}
                      </option>
                    ))}
                  </select>
                </FormField>
                <FormField label="Descarga programada" help="Hora de Caracas">
                  <TextInput
                    type="datetime-local"
                    value={descargaNueva}
                    onChange={(e) => setDescargaNueva(e.target.value)}
                  />
                </FormField>
                <FormField label="Packing list">
                  <TextInput
                    value={packingList}
                    onChange={(e) => setPackingList(e.target.value)}
                  />
                </FormField>
                <FormField label="Factura del proveedor">
                  <TextInput
                    value={factura}
                    onChange={(e) => setFactura(e.target.value)}
                  />
                </FormField>
                <FormField label="Bultos declarados">
                  <TextInput
                    type="number"
                    min="0"
                    value={bultosDeclarados}
                    onChange={(e) => setBultosDeclarados(e.target.value)}
                  />
                </FormField>
              </div>
              <p className="text-sm text-text-600">
                La orden es la del expediente{detalle.order_code ? `: ${detalle.order_code}` : ""}.
              </p>
              <AsyncButton type="button" onClick={crearRecepcion}>
                Crear recepción
              </AsyncButton>
            </form>
          </Autorizado>
        ) : null}
      </section>
    </>
  );
}
