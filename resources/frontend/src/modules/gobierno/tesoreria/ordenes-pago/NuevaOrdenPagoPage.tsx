import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { PageHeader } from "@/components/PageHeader";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";
import { hoyDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_ORDENES,
  RUTA_ORDENES,
  type OpcionesOrden,
  type OrdenPago,
} from "./api";

interface DocumentoPolitica {
  document_type_id: string;
  obligatorio: boolean;
  etapa: string;
  tipo?: string | null;
  nombre?: string | null;
}

interface LineaSeleccionada {
  obligacionId: string;
  codigo: string;
  beneficiario: string;
  moneda: string;
  fechaEfectiva: string;
  montoCausado: string;
  montoOrdenado: string;
  pendienteDeOrdenar: string;
  compromisoCodigo: string;
}

function esDocumentoPolitica(valor: unknown): valor is DocumentoPolitica {
  if (typeof valor !== "object" || valor === null) return false;
  const candidato = valor as Record<string, unknown>;
  return (
    typeof candidato.document_type_id === "string" &&
    typeof candidato.obligatorio === "boolean" &&
    typeof candidato.etapa === "string"
  );
}

function aCentavos(valor: string): bigint {
  const texto = valor.trim();
  if (texto === "") return 0n;
  const negativo = texto.startsWith("-");
  const sinSigno = negativo ? texto.slice(1) : texto;
  const partes = sinSigno.split(".");
  const enteros = partes[0] || "0";
  const decimales = (partes[1] ?? "").padEnd(2, "0").slice(0, 2);
  const centavos = BigInt(enteros) * 100n + BigInt(decimales || "0");
  return negativo ? -centavos : centavos;
}

function esMontoValido(valor: string): boolean {
  const texto = valor.trim();
  if (texto === "") return false;
  return /^-?\d+(\.\d{1,2})?$/.test(texto);
}

export function NuevaOrdenPagoPage() {
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { ordenId } = useParams<{ ordenId: string }>();
  const [searchParams] = useSearchParams();
  const yearIdParam = searchParams.get("ejercicio");

  const esEdicion = Boolean(ordenId);

  const [seleccionadas, setSeleccionadas] = useState<Set<string>>(new Set());
  const [montos, setMontos] = useState<Record<string, string>>({});
  const [politicaId, setPoliticaId] = useState<string>("");
  const [fechaOrden, setFechaOrden] = useState<string>(hoyDeNegocio());
  const [concepto, setConcepto] = useState<string>("");
  const [autoridadCargoId, setAutoridadCargoId] = useState<string>("");
  const [documentosSeleccionados, setDocumentosSeleccionados] = useState<Set<string>>(new Set());
  const [inicializado, setInicializado] = useState<boolean>(false);
  const [errorFormulario, setErrorFormulario] = useState<string>("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});

  const tienePermiso = tiene("gobierno_ordenes_pago:manage", "empresa");

  const ordenQuery = useQuery({
    queryKey: [...CONSULTA_ORDENES, "edicion", ordenId],
    queryFn: async () => {
      if (!ordenId) return null;
      try {
        return await apiFetch<OrdenPago>(`/gobierno/tesoreria/ordenes-pago/${ordenId}`);
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) {
          return null;
        }
        throw error;
      }
    },
    enabled: Boolean(ordenId) && tienePermiso,
  });

  const orden = ordenQuery.data;

  useEffect(() => {
    if (!esEdicion || !orden || inicializado) return;
    const nuevasSeleccionadas = new Set<string>();
    const nuevosMontos: Record<string, string> = {};
    for (const linea of orden.lineas) {
      nuevasSeleccionadas.add(linea.cause_id);
      nuevosMontos[linea.cause_id] = linea.monto_asignado;
    }
    setSeleccionadas(nuevasSeleccionadas);
    setMontos(nuevosMontos);
    setPoliticaId(orden.policy.id);
    setFechaOrden(orden.fecha_orden);
    setConcepto(orden.concepto);
    setAutoridadCargoId(orden.autoridad.cargo_id ?? "");
    const nuevosDocumentos = new Set<string>();
    for (const documento of orden.documentos) {
      nuevosDocumentos.add(documento.document_id);
    }
    setDocumentosSeleccionados(nuevosDocumentos);
    setInicializado(true);
  }, [esEdicion, orden, inicializado]);

  const yearId = esEdicion ? orden?.year_id : yearIdParam;

  const opcionesQuery = useQuery({
    queryKey: [...CONSULTA_ORDENES, "opciones", yearId],
    queryFn: async () => {
      if (!yearId) return null;
      return await apiFetch<OpcionesOrden>(
        `/gobierno/tesoreria/ejercicios/${yearId}/ordenes-pago/opciones`,
      );
    },
    enabled: Boolean(yearId) && tienePermiso,
  });

  const opciones = opcionesQuery.data;

  const lineasSeleccionadas = useMemo<LineaSeleccionada[]>(() => {
    if (!opciones) return [];
    return (opciones.obligaciones ?? [])
      .filter((obligacion) => seleccionadas.has(obligacion.id))
      .map((obligacion) => ({
        obligacionId: obligacion.id,
        codigo: obligacion.codigo,
        beneficiario: obligacion.beneficiario,
        moneda: obligacion.moneda,
        fechaEfectiva: obligacion.fecha_efectiva,
        montoCausado: obligacion.monto_causado,
        montoOrdenado: obligacion.monto_ordenado,
        pendienteDeOrdenar: obligacion.pendiente_de_ordenar,
        compromisoCodigo: obligacion.compromiso_codigo,
      }));
  }, [opciones, seleccionadas]);

  const politicaElegida = useMemo(() => {
    if (!opciones || !politicaId) return null;
    return opciones.politicas.find((p) => p.id === politicaId) ?? null;
  }, [opciones, politicaId]);

  const documentosPolitica = useMemo<DocumentoPolitica[]>(() => {
    if (!politicaElegida) return [];
    return (politicaElegida.documentos ?? [])
      .filter(esDocumentoPolitica);
  }, [politicaElegida]);

  const beneficiariosDistintos = useMemo(() => {
    if (lineasSeleccionadas.length < 2) return false;
    const primero = lineasSeleccionadas[0]?.beneficiario ?? "";
    return lineasSeleccionadas.some((linea) => linea.beneficiario !== primero);
  }, [lineasSeleccionadas]);

  const monedasDistintas = useMemo(() => {
    if (lineasSeleccionadas.length < 2) return false;
    const primera = lineasSeleccionadas[0]?.moneda ?? "";
    return lineasSeleccionadas.some((linea) => linea.moneda !== primera);
  }, [lineasSeleccionadas]);

  const incompatibles = beneficiariosDistintos || monedasDistintas;

  const hayExceso = useMemo(() => {
    return lineasSeleccionadas.some((linea) => {
      const monto = montos[linea.obligacionId];
      if (!monto || !esMontoValido(monto)) return false;
      return aCentavos(monto) > aCentavos(linea.pendienteDeOrdenar);
    });
  }, [lineasSeleccionadas, montos]);

  const totalDeLaOrdenCentavos = useMemo(() => {
    return lineasSeleccionadas.reduce((total, linea) => {
      const monto = montos[linea.obligacionId];
      if (!monto || !esMontoValido(monto)) return total;
      return total + aCentavos(monto);
    }, 0n);
  }, [lineasSeleccionadas, montos]);

  const totalDeLaOrden = useMemo(() => {
    const negativo = totalDeLaOrdenCentavos < 0n;
    const absoluto = negativo ? -totalDeLaOrdenCentavos : totalDeLaOrdenCentavos;
    const enteros = absoluto / 100n;
    const decimales = (absoluto % 100n).toString().padStart(2, "0");
    return `${negativo ? "-" : ""}${enteros}.${decimales}`;
  }, [totalDeLaOrdenCentavos]);

  const monedaDeLaOrden = useMemo(() => {
    return lineasSeleccionadas[0]?.moneda ?? "";
  }, [lineasSeleccionadas]);

  const mutacionGuardar = useMutation({
    mutationFn: async () => {
      if (!yearId) throw new Error("Falta el ejercicio");

      const lineas = lineasSeleccionadas.map((linea) => ({
        cause_id: linea.obligacionId,
        monto: montos[linea.obligacionId] ?? "",
      }));

      const body = {
        policy_id: politicaId,
        fecha_orden: fechaOrden,
        concepto,
        lineas,
        documentos: Array.from(documentosSeleccionados),
        autoridad_cargo_id: autoridadCargoId === "" ? null : autoridadCargoId,
      };

      if (esEdicion && ordenId) {
        return await apiFetch<OrdenPago>(`/gobierno/tesoreria/ordenes-pago/${ordenId}`, {
          method: "PUT",
          body,
          ifMatch: String(orden?.version ?? ""),
        });
      }

      return await apiFetch<OrdenPago>(`/gobierno/tesoreria/ejercicios/${yearId}/ordenes-pago`, {
        method: "POST",
        body,
      });
    },
    onSuccess: async (ordenGuardada) => {
      await queryClient.invalidateQueries({ queryKey: [...CONSULTA_ORDENES] });
      notify({ type: "success", title: "Borrador guardado" });
      navigate(`${RUTA_ORDENES}/ordenes-pago/${ordenGuardada.id}`);
    },
    onError: (error: unknown) => {
      setFieldErrors({});
      setErrorFormulario("");
      if (error instanceof ApiError) {
        if (error.status === 403) {
          setErrorFormulario("No tiene permiso para preparar órdenes de pago");
          return;
        }
        if (error.status === 409) {
          setErrorFormulario("La orden cambió; recargue la página");
          return;
        }
        setErrorFormulario(error.message);
        if (error.fieldErrors && Object.keys(error.fieldErrors).length > 0) {
          setFieldErrors(error.fieldErrors);
        }
      } else {
        setErrorFormulario("No se pudo guardar la orden de pago");
      }
    },
  });

  const puedeGuardar = useMemo(() => {
    if (!politicaId) return false;
    if (concepto.trim().length < 3 || concepto.trim().length > 500) return false;
    if (lineasSeleccionadas.length === 0) return false;
    if (incompatibles) return false;
    if (hayExceso) return false;
    const hayMontoPositivo = lineasSeleccionadas.some((linea) => {
      const monto = montos[linea.obligacionId];
      return monto && esMontoValido(monto) && aCentavos(monto) > 0n;
    });
    if (!hayMontoPositivo) return false;
    return true;
  }, [politicaId, concepto, lineasSeleccionadas, incompatibles, hayExceso, montos]);

  if (!tienePermiso) {
    return (
      <PageContent>
        <EmptyState
          title="No tiene permiso para preparar órdenes de pago"
          description="Necesita la capacidad gobierno_ordenes_pago:manage"
        />
      </PageContent>
    );
  }

  if (esEdicion) {
    if (ordenQuery.isLoading) {
      return (
        <PageContent>
          <LoadingState />
        </PageContent>
      );
    }
    if (ordenQuery.isError) {
      return (
        <PageContent>
          <ErrorState
            title="Error al cargar la orden de pago"
            message={
              ordenQuery.error instanceof Error
                ? ordenQuery.error.message
                : "No se pudo cargar la orden de pago"
            }
            onRetry={() => void ordenQuery.refetch()}
          />
        </PageContent>
      );
    }
    if (!orden) {
      return (
        <PageContent>
          <EmptyState
            title="No se encontró la orden de pago"
            action={<Link to={`${RUTA_ORDENES}/ordenes-pago`}>Volver a órdenes de pago</Link>}
          />
        </PageContent>
      );
    }
    if (orden.estado !== "BORRADOR") {
      return (
        <PageContent>
          <ErrorState
            title="No editable"
            message="Solo se puede editar una orden en borrador"
          />
        </PageContent>
      );
    }
  } else {
    if (!yearId) {
      return (
        <PageContent>
          <EmptyState
            title="Falta el ejercicio"
            action={<Link to={`${RUTA_ORDENES}/ordenes-pago`}>Volver a órdenes de pago</Link>}
          />
        </PageContent>
      );
    }
  }

  if (opcionesQuery.isLoading) {
    return (
      <PageContent>
        <LoadingState />
      </PageContent>
    );
  }

  if (opcionesQuery.isError) {
    return (
      <PageContent>
        <ErrorState
          title="Error al cargar las opciones"
          message={
            opcionesQuery.error instanceof Error
              ? opcionesQuery.error.message
              : "No se pudieron cargar las opciones"
          }
          onRetry={() => void opcionesQuery.refetch()}
        />
      </PageContent>
    );
  }

  if (!opciones) {
    return (
      <PageContent>
        <EmptyState title="No hay opciones disponibles" />
      </PageContent>
    );
  }

  const titulo = esEdicion ? "Editar borrador de orden de pago" : "Nueva orden de pago";
  const rutaCancelar =
    esEdicion && orden ? `${RUTA_ORDENES}/ordenes-pago/${orden.id}` : `${RUTA_ORDENES}/ordenes-pago`;

  function manejarSeleccion(obligacionId: string, marcado: boolean, pendiente: string) {
    setSeleccionadas((previas) => {
      const nuevas = new Set(previas);
      if (marcado) {
        nuevas.add(obligacionId);
      } else {
        nuevas.delete(obligacionId);
      }
      return nuevas;
    });
    setMontos((previos) => {
      const nuevos = { ...previos };
      if (marcado) {
        nuevos[obligacionId] = pendiente;
      } else {
        delete nuevos[obligacionId];
      }
      return nuevos;
    });
  }

  function manejarCambioMonto(obligacionId: string, valor: string) {
    setMontos((previos) => ({ ...previos, [obligacionId]: valor }));
  }

  function manejarCambioDocumento(documentoId: string, marcado: boolean) {
    setDocumentosSeleccionados((previos) => {
      const nuevas = new Set(previos);
      if (marcado) {
        nuevas.add(documentoId);
      } else {
        nuevas.delete(documentoId);
      }
      return nuevas;
    });
  }

  function manejarEnvio(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    mutacionGuardar.mutate();
  }

  return (
    <PageContent>
      <PageHeader
        title={titulo}
        crumbs={[
          { label: "Órdenes de pago", to: `${RUTA_ORDENES}/ordenes-pago` },
          { label: titulo },
        ]}
      />
      <form onSubmit={manejarEnvio} className="space-y-8">
        {errorFormulario && (
          <div
            role="alert"
            className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-700"
          >
            {errorFormulario}
          </div>
        )}

        <section aria-labelledby="seccion-obligaciones">
          <h2 id="seccion-obligaciones" className="text-lg font-semibold">
            Obligaciones pendientes de ordenar
          </h2>
          {incompatibles && (
            <div
              role="alert"
              className="mt-4 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800"
            >
              {beneficiariosDistintos && <p>Las obligaciones seleccionadas tienen beneficiarios distintos</p>}
              {monedasDistintas && <p>Las obligaciones seleccionadas tienen monedas distintas</p>}
            </div>
          )}
          <div
            className="mt-4 overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Tabla de causados disponibles"
          >
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th scope="col" className="px-3 py-2 text-left text-xs font-medium text-slate-500">Seleccionar</th>
                  <th scope="col" className="px-3 py-2 text-left text-xs font-medium text-slate-500">Causado</th>
                  <th scope="col" className="px-3 py-2 text-left text-xs font-medium text-slate-500">Compromiso</th>
                  <th scope="col" className="px-3 py-2 text-left text-xs font-medium text-slate-500">Beneficiario</th>
                  <th scope="col" className="px-3 py-2 text-left text-xs font-medium text-slate-500">Moneda</th>
                  <th scope="col" className="px-3 py-2 text-left text-xs font-medium text-slate-500">Fecha efectiva</th>
                  <th scope="col" className="px-3 py-2 text-right text-xs font-medium text-slate-500">Monto causado</th>
                  <th scope="col" className="px-3 py-2 text-right text-xs font-medium text-slate-500">Monto ordenado</th>
                  <th scope="col" className="px-3 py-2 text-right text-xs font-medium text-slate-500">Pendiente de ordenar</th>
                  <th scope="col" className="px-3 py-2 text-right text-xs font-medium text-slate-500">Monto a ordenar</th>
                  <th scope="col" className="px-3 py-2 text-right text-xs font-medium text-slate-500">Pendiente tras esta orden</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {opciones.obligaciones.map((obligacion) => {
                  const seleccionada = seleccionadas.has(obligacion.id);
                  const elegible = obligacion.elegible === true && obligacion.pendiente_de_ordenar !== "0.00";
                  const monto = montos[obligacion.id] ?? "";
                  const excede =
                    seleccionada &&
                    monto !== "" &&
                    esMontoValido(monto) &&
                    aCentavos(monto) > aCentavos(obligacion.pendiente_de_ordenar);
                  const pendienteCentavos = aCentavos(obligacion.pendiente_de_ordenar);
                  const montoCentavos =
                    seleccionada && monto !== "" && esMontoValido(monto) ? aCentavos(monto) : 0n;
                  const pendienteTrasCentavos = pendienteCentavos - montoCentavos;
                  const pendienteTrasNegativo = pendienteTrasCentavos < 0n;
                  const pendienteTrasAbsoluto = pendienteTrasNegativo
                    ? -pendienteTrasCentavos
                    : pendienteTrasCentavos;
                  const pendienteTras = `${pendienteTrasNegativo ? "-" : ""}${pendienteTrasAbsoluto / 100n}.${(pendienteTrasAbsoluto % 100n).toString().padStart(2, "0")}`;
                  return (
                    <tr key={obligacion.id} className={elegible ? "" : "bg-slate-50 text-slate-400"}>
                      <td className="px-3 py-2">
                        <input
                          type="checkbox"
                          aria-label={`Seleccionar causado ${obligacion.codigo}`}
                          disabled={!elegible}
                          checked={seleccionada}
                          onChange={(e) =>
                            manejarSeleccion(obligacion.id, e.target.checked, obligacion.pendiente_de_ordenar)
                          }
                        />
                      </td>
                      <td className="px-3 py-2 text-sm text-slate-700">
                        {obligacion.codigo}
                        {!elegible && obligacion.motivo && (
                          <p className="mt-1 text-xs text-slate-400">{obligacion.motivo}</p>
                        )}
                      </td>
                      <td className="px-3 py-2 text-sm text-slate-700">{obligacion.compromiso_codigo}</td>
                      <td className="px-3 py-2 text-sm text-slate-700">{obligacion.beneficiario}</td>
                      <td className="px-3 py-2 text-sm text-slate-700">{obligacion.moneda}</td>
                      <td className="px-3 py-2 text-sm text-slate-700">{obligacion.fecha_efectiva}</td>
                      <td className="px-3 py-2 text-right text-sm text-slate-700">{obligacion.monto_causado}</td>
                      <td className="px-3 py-2 text-right text-sm text-slate-700">{obligacion.monto_ordenado}</td>
                      <td className="px-3 py-2 text-right text-sm text-slate-700">{obligacion.pendiente_de_ordenar}</td>
                      <td className="px-3 py-2 text-right">
                        <input
                          type="text"
                          inputMode="decimal"
                          aria-label={`Monto a ordenar de ${obligacion.codigo}`}
                          disabled={!seleccionada}
                          className="w-full rounded-md border border-slate-300 px-2 py-1 text-right text-sm disabled:bg-slate-100 disabled:text-slate-400"
                          value={monto}
                          onChange={(e) => manejarCambioMonto(obligacion.id, e.target.value)}
                        />
                        {excede && (
                          <p role="alert" className="mt-1 text-xs text-red-700">
                            Supera el pendiente de la línea
                          </p>
                        )}
                      </td>
                      <td className="px-3 py-2 text-right text-sm text-slate-700">
                        {seleccionada ? pendienteTras : obligacion.pendiente_de_ordenar}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {fieldErrors["lineas"] && (
            <p role="alert" className="mt-2 text-sm text-red-700">
              {fieldErrors["lineas"].join(", ")}
            </p>
          )}
          <div className="mt-4 flex justify-end gap-6 text-sm">
            <span>
              TOTAL DE LA ORDEN: {totalDeLaOrden}
              {monedaDeLaOrden ? ` ${monedaDeLaOrden}` : ""}
            </span>
          </div>
          <p className="mt-2 text-right text-xs text-slate-500">
            Estimación; el saldo definitivo lo valida el sistema al emitir.
          </p>
        </section>

        <section aria-labelledby="seccion-politica">
          <h2 id="seccion-politica" className="text-lg font-semibold">
            Política aplicable
          </h2>
          <div className="mt-4">
            <label htmlFor="politica" className="block text-sm font-medium text-slate-700">
              Política
            </label>
            <select
              id="politica"
              className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              value={politicaId}
              onChange={(e) => setPoliticaId(e.target.value)}
            >
              <option value="">Seleccione una política</option>
              {opciones.politicas.map((politica) => (
                <option key={politica.id} value={politica.id}>
                  {politica.codigo} · {politica.nombre}
                  {politica.tipo_gasto ? ` · ${politica.tipo_gasto}` : ""}
                </option>
              ))}
            </select>
            {fieldErrors["policy_id"] && (
              <p role="alert" className="mt-2 text-sm text-red-700">
                {fieldErrors["policy_id"].join(", ")}
              </p>
            )}
          </div>

          {politicaElegida && documentosPolitica.length > 0 && (
            <div className="mt-4">
              <p className="text-sm font-medium text-slate-700">Documentos exigidos</p>
              <ul className="mt-2 list-disc pl-5 text-sm text-slate-700">
                {documentosPolitica.map((documento, indice) => (
                  <li key={`${documento.document_type_id}-${indice}`}>
                    {documento.nombre ?? documento.tipo ?? documento.document_type_id}
                    {documento.obligatorio ? " (obligatorio)" : " (opcional)"} · {documento.etapa}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>

        <section aria-labelledby="seccion-datos">
          <h2 id="seccion-datos" className="text-lg font-semibold">
            Datos de la orden
          </h2>
          <div className="mt-4 space-y-4">
            <FormField
              label="Fecha de la orden"
              htmlFor="fecha-orden"
              required
              error={fieldErrors["fecha_orden"]?.join(", ")}
            >
              <TextInput
                id="fecha-orden"
                type="date"
                value={fechaOrden}
                onChange={(e) => setFechaOrden(e.target.value)}
                required
              />
            </FormField>
            <FormField
              label="Concepto"
              htmlFor="concepto"
              required
              help="Entre 3 y 500 caracteres"
              error={fieldErrors["concepto"]?.join(", ")}
            >
              <textarea
                id="concepto"
                rows={3}
                className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
                value={concepto}
                onChange={(e) => setConcepto(e.target.value)}
                maxLength={500}
                required
              />
            </FormField>
            <FormField
              label="Cargo que ordena el pago"
              htmlFor="autoridad-cargo"
              help="Competencia Ordenar pago × Tesorería en la fecha de la orden"
              error={fieldErrors["autoridad_cargo_id"]?.join(", ")}
            >
              <select
                id="autoridad-cargo"
                className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                value={autoridadCargoId}
                onChange={(e) => setAutoridadCargoId(e.target.value)}
              >
                <option value="">Sin indicar</option>
                {opciones.cargos.map((cargo) => (
                  <option key={cargo.id} value={cargo.id}>
                    {cargo.codigo} · {cargo.nombre}
                  </option>
                ))}
              </select>
            </FormField>
          </div>
        </section>

        <section aria-labelledby="seccion-documentos">
          <h2 id="seccion-documentos" className="text-lg font-semibold">
            Documentos de soporte
          </h2>
          <div className="mt-4 space-y-2">
            {opciones.documentos.map((documento) => (
              <label
                key={documento.id}
                className="flex items-start gap-2 text-sm text-slate-700"
              >
                <input
                  type="checkbox"
                  aria-label={`Documento ${documento.titulo}`}
                  className="mt-1"
                  checked={documentosSeleccionados.has(documento.id)}
                  onChange={(e) => manejarCambioDocumento(documento.id, e.target.checked)}
                />
                <span>
                  {documento.titulo} · {documento.tipo}
                </span>
              </label>
            ))}
            {fieldErrors["documentos"] && (
              <p role="alert" className="mt-2 text-sm text-red-700">
                {fieldErrors["documentos"].join(", ")}
              </p>
            )}
          </div>
        </section>

        <div className="flex items-center gap-4">
          <Button type="submit" variant="primary" disabled={!puedeGuardar || mutacionGuardar.isPending}>
            {mutacionGuardar.isPending ? "Guardando..." : "Guardar borrador"}
          </Button>
          <Link
            className="inline-flex items-center rounded-md border border-slate-300 px-3 py-2 text-sm"
            to={rutaCancelar}
          >
            Cancelar
          </Link>
        </div>
      </form>
    </PageContent>
  );
}
