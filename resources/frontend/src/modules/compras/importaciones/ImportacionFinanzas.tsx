import { useState } from "react";
import { Link } from "react-router";
import { useInfiniteQuery, useQueryClient } from "@tanstack/react-query";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { Autorizado } from "@/components/Autorizado";
import { apiFetch, ApiError } from "@/api/client";
import { formatearInstante } from "@/lib/fecha-de-negocio";
import type { PagedResult } from "@/api/types";
import type { DetalleImportacion } from "./ImportacionDetallePage";

type Props = {
  detalle: DetalleImportacion;
  onCambios: () => void;
};

type Candidato = {
  id: string;
  amount: string;
  currency: string;
  status: string;
  created_at: string;
};

type RespuestaCandidatos = PagedResult<Candidato>;

const ESTADOS_FINANCIEROS: Record<string, string> = {
  DRAFT: "Borrador",
  APPROVED: "Aprobado",
  PAID: "Pagado",
  ACTIVE: "Activo",
  APPLIED: "Aplicado",
  CANCELLED: "Anulado",
  REJECTED: "Rechazado",
  PENDING: "Pendiente",
  POSTED: "Contabilizado",
};

const ESTADOS_FORMULARIO = new Set([
  "ORDERED",
  "DOCUMENTS_COMPLETE",
  "DISPATCHED",
]);

function EstadoFinanciero({ estado }: { estado: string }) {
  return <span>{ESTADOS_FINANCIEROS[estado] ?? "Sin estado"}</span>;
}

export function ImportacionFinanzas({ detalle, onCambios }: Props) {
  const [pagoTipo, setPagoTipo] = useState<"PAYMENT" | "ADVANCE">("PAYMENT");
  const [pagoMonto, setPagoMonto] = useState("");
  const [tipoCandidato, setTipoCandidato] = useState<"PAYMENT" | "ADVANCE">(
    "PAYMENT",
  );
  const [error, setError] = useState<ApiError | null>(null);
  const queryClient = useQueryClient();

  const esNegociando = detalle.status === "NEGOTIATING";
  const esCancelada = detalle.status === "CANCELLED";
  const mostrarFormulario = ESTADOS_FORMULARIO.has(detalle.status);

  const candidatosQuery = useInfiniteQuery({
    queryKey: [
      "importaciones",
      detalle.id,
      "financial-candidates",
      tipoCandidato,
    ],
    queryFn: ({ pageParam = 1 }) =>
      apiFetch<RespuestaCandidatos>(
        `/importaciones/${detalle.id}/financial-candidates?kind=${tipoCandidato}&page=${pageParam}&page_size=20`,
      ),
    getNextPageParam: (lastPage, allPages) => {
      const candidatos = allPages.flatMap((page) => page.items);
      return candidatos.length < lastPage.total
        ? allPages.length + 1
        : undefined;
    },
    initialPageParam: 1,
    enabled: mostrarFormulario,
  });

  const candidatos =
    candidatosQuery.data?.pages.flatMap((page) => page.items) ?? [];
  const total = candidatosQuery.data?.pages[0]?.total ?? 0;
  const cargando = candidatosQuery.isLoading;

  const cambiarTipoCandidato = (tipo: "PAYMENT" | "ADVANCE") => {
    setTipoCandidato(tipo);
  };

  const mostrarErrorApi = (err: unknown, fallback: string) => {
    setError(err instanceof ApiError ? err : new ApiError(500, {
      code: "ERROR_DESCONOCIDO",
      message: err instanceof Error ? err.message : fallback,
    }));
  };

  const registrarPago = async () => {
    if (!pagoMonto.trim()) return;
    setError(null);
    try {
      await apiFetch(`/importaciones/${detalle.id}/payments`, {
        method: "POST",
        body: { kind: pagoTipo, amount: pagoMonto.trim() },
      });
      setPagoMonto("");
      onCambios();
    } catch (err) {
      mostrarErrorApi(err, "Error al registrar pago.");
    }
  };

  const vincularCandidato = async (candidatoId: string) => {
    setError(null);
    try {
      await apiFetch(`/importaciones/${detalle.id}/financial-links`, {
        method: "POST",
        body: { kind: tipoCandidato, target_id: candidatoId },
      });
      onCambios();
    } catch (err) {
      mostrarErrorApi(err, "Error al vincular pago.");
    }
  };

  const desvincular = async (linkId: string) => {
    setError(null);
    try {
      await apiFetch(`/importaciones/${detalle.id}/financial-links/${linkId}`, {
        method: "DELETE",
      });
      onCambios();
      void queryClient.invalidateQueries({
        queryKey: ["importaciones", detalle.id, "financial-candidates"],
      });
    } catch (err) {
      mostrarErrorApi(err, "Error al desvincular pago.");
    }
  };

  const errorMessage =
    error?.message ?? "Error en operación financiera.";
  const esProveedorNoAprobado = error?.code === "SUPPLIER_NOT_APPROVED";

  return (
    <section
      id="finanzas"
      className="rounded-lg border border-border-default bg-surface-0 p-6"
    >
      <h2 className="mb-4 text-lg font-semibold text-text-900">Finanzas</h2>

      {esNegociando && (
        <p className="mb-4 text-sm text-text-600">
          Se habilita al vincular la orden de compra.
        </p>
      )}

      {esCancelada ? null : (
        <>
          <div className="space-y-2">
            <h3 className="font-medium">Pagos y anticipos</h3>
            {detalle.financial.length === 0 ? (
              <p className="text-sm text-text-600">Sin pagos registrados.</p>
            ) : (
              <ul className="space-y-1">
                {detalle.financial.map((pago) => (
                  <li key={pago.id} className="flex flex-wrap items-center gap-2 text-sm">
                    <span>
                      {pago.kind === "PAYMENT" ? "Pago" : "Anticipo"}{" "}
                      {pago.amount} {pago.currency}
                    </span>
                    <EstadoFinanciero estado={pago.status} />
                    <span>{pago.date}</span>
                    {mostrarFormulario && (
                      <Autorizado
                        operacion={[
                          "DELETE",
                          `/importaciones/${detalle.id}/financial-links/${pago.id}`,
                        ]}
                      >
                        <AsyncButton
                          variant="secondary"
                          size="sm"
                          onClick={() => desvincular(pago.id)}
                        >
                          Desvincular
                        </AsyncButton>
                      </Autorizado>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="mt-4">
            <Link
              to="/compras/cuentas-por-pagar"
              className="text-sm font-medium text-brand-600 hover:text-brand-700"
            >
              Ir a Cuentas por pagar
            </Link>
          </div>

          {mostrarFormulario && (
            <>
              <div className="mt-6 space-y-4">
                <FormField label="Tipo">
                  <select
                    className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                    value={pagoTipo}
                    onChange={(e) =>
                      setPagoTipo(e.target.value as "PAYMENT" | "ADVANCE")
                    }
                  >
                    <option value="PAYMENT">Pago</option>
                    <option value="ADVANCE">Anticipo</option>
                  </select>
                </FormField>
                <FormField label="Monto" required>
                  <TextInput
                    inputMode="decimal"
                    value={pagoMonto}
                    onChange={(e) => setPagoMonto(e.target.value)}
                  />
                </FormField>

                <Autorizado
                  operacion={["POST", `/importaciones/${detalle.id}/payments`]}
                >
                  <AsyncButton disabled={!pagoMonto.trim()} onClick={registrarPago}>
                    Registrar
                  </AsyncButton>
                </Autorizado>
              </div>

              <div className="mt-8 space-y-4">
                <h3 className="font-medium">Vincular pago existente</h3>
                <FormField label="Tipo de pago">
                  <select
                    className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                    value={tipoCandidato}
                    onChange={(e) =>
                      cambiarTipoCandidato(e.target.value as "PAYMENT" | "ADVANCE")
                    }
                  >
                    <option value="PAYMENT">Pagos</option>
                    <option value="ADVANCE">Anticipos</option>
                  </select>
                </FormField>

                {candidatos.length === 0 && !cargando && !candidatosQuery.error ? (
                  <p className="text-sm text-text-600">
                    No hay candidatos pendientes.
                  </p>
                ) : (
                  <div className="space-y-2">
                    {candidatos.map((candidato) => (
                      <div
                        key={candidato.id}
                        className="flex items-center gap-2 text-sm"
                      >
                        <span>
                          {candidato.amount} {candidato.currency}
                        </span>
                        <EstadoFinanciero estado={candidato.status} />
                        <span>{formatearInstante(candidato.created_at)}</span>
                        <Autorizado
                          operacion={[
                            "POST",
                            `/importaciones/${detalle.id}/financial-links`,
                          ]}
                        >
                          <AsyncButton
                            variant="secondary"
                            size="sm"
                            onClick={() => vincularCandidato(candidato.id)}
                          >
                            Vincular
                          </AsyncButton>
                        </Autorizado>
                      </div>
                    ))}
                  </div>
                )}

                <p className="text-sm text-text-600">
                  Mostrando {candidatos.length} de {total}
                </p>

                {candidatos.length < total && !cargando && (
                  <Button
                    variant="secondary"
                    onClick={() => {
                      void candidatosQuery.fetchNextPage();
                    }}
                  >
                    Cargar más
                  </Button>
                )}
              </div>
            </>
          )}
        </>
      )}

      {error && (
        <div
          role="alert"
          className="mt-4 rounded-md border border-danger-100 bg-danger-100/40 p-3 text-sm text-danger-600"
        >
          <p>{errorMessage}</p>
          {esProveedorNoAprobado && detalle.supplier_id && (
            <Link
              to={`/maestros/terceros/${detalle.supplier_id}`}
              className="mt-2 inline-block text-sm font-medium text-brand-600 hover:text-brand-700"
            >
              Ver proveedor
            </Link>
          )}
        </div>
      )}
    </section>
  );
}
