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
import { AdjuntosPanel } from "@/modules/documentos/AdjuntosPanel";
import { formatearFechaDeNegocio, hoyDeNegocio } from "@/lib/fecha-de-negocio";
import { CONSULTA_CAUSADOS, RUTA_CAUSADOS, DISPARADORES, type Causado, type OpcionesCausado } from "./api";

type EvidenciaSeleccion = `${string}:${string}`;

export function NuevoCausadoPage() {
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { causadoId } = useParams<{ causadoId: string }>();
  const [searchParams] = useSearchParams();
  const yearIdParam = searchParams.get("ejercicio");

  const esEdicion = Boolean(causadoId);

  const [compromisoId, setCompromisoId] = useState<string>("");
  const [politicaId, setPoliticaId] = useState<string>("");
  const [montos, setMontos] = useState<Record<string, string>>({});
  const [evidenciasSeleccionadas, setEvidenciasSeleccionadas] = useState<Set<EvidenciaSeleccion>>(new Set());
  const [fechaEfectiva, setFechaEfectiva] = useState<string>(hoyDeNegocio());
  const [concepto, setConcepto] = useState<string>("");
  const [beneficiario, setBeneficiario] = useState<string>("");
  const [autoridadCargoId, setAutoridadCargoId] = useState<string>("");
  const [inicializado, setInicializado] = useState<boolean>(false);
  const [errorFormulario, setErrorFormulario] = useState<string>("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});

  const tienePermiso = tiene("gobierno_presupuesto:cause", "empresa");

  const causadoQuery = useQuery({
    queryKey: [...CONSULTA_CAUSADOS, "edicion", causadoId],
    queryFn: async () => {
      if (!causadoId) return null;
      try {
        return await apiFetch<Causado>(`/gobierno/presupuesto/causados/${causadoId}`);
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) {
          return null;
        }
        throw error;
      }
    },
    enabled: Boolean(causadoId) && tienePermiso,
  });

  const causado = causadoQuery.data;

  useEffect(() => {
    if (!esEdicion || !causado || inicializado) return;
    setCompromisoId(causado.compromiso.id);
    setPoliticaId(causado.politica.id);
    const nuevosMontos: Record<string, string> = {};
    for (const linea of causado.lineas) {
      nuevosMontos[linea.linea_compromiso_id] = linea.monto;
    }
    setMontos(nuevosMontos);
    const nuevasEvidencias = new Set<EvidenciaSeleccion>();
    for (const evidencia of causado.evidencias) {
      nuevasEvidencias.add(`${evidencia.tipo}:${evidencia.recurso_id}`);
    }
    setEvidenciasSeleccionadas(nuevasEvidencias);
    setFechaEfectiva(causado.fecha_efectiva);
    setConcepto(causado.concepto);
    setBeneficiario(causado.beneficiario ?? "");
    setAutoridadCargoId(causado.autoridad_cargo_id ?? "");
    setInicializado(true);
  }, [esEdicion, causado, inicializado]);

  const yearId = esEdicion ? causado?.year_id : yearIdParam;

  const opcionesQuery = useQuery({
    queryKey: [...CONSULTA_CAUSADOS, "opciones", yearId, compromisoId],
    queryFn: async () => {
      if (!yearId) return null;
      const ruta = compromisoId
        ? `/gobierno/presupuesto/ejercicios/${yearId}/causados/opciones?compromiso_id=${compromisoId}`
        : `/gobierno/presupuesto/ejercicios/${yearId}/causados/opciones`;
      return await apiFetch<OpcionesCausado>(ruta);
    },
    enabled: Boolean(yearId) && tienePermiso,
  });

  const opciones = opcionesQuery.data;

  const mutacionGuardar = useMutation({
    mutationFn: async () => {
      if (!yearId) throw new Error("Falta el ejercicio");
      if (!compromisoId) throw new Error("Falta el compromiso");
      if (!politicaId) throw new Error("Falta la política");

      const lineas = (opciones?.compromisos ?? [])
        .flatMap((c) => (c.id === compromisoId ? c.lineas : []))
        .filter((linea) => {
          const monto = montos[linea.id];
          return monto && Number(monto) > 0;
        })
        .map((linea) => ({
          linea_compromiso_id: linea.id,
          monto: montos[linea.id],
        }));

      const evidencias = Array.from(evidenciasSeleccionadas).map((clave) => {
        const separador = clave.indexOf(":");
        return {
          tipo: clave.slice(0, separador),
          id: clave.slice(separador + 1),
        };
      });

      const body = {
        compromiso_id: compromisoId,
        politica_id: politicaId,
        fecha_efectiva: fechaEfectiva,
        concepto,
        beneficiario: beneficiario.trim() === "" ? null : beneficiario,
        autoridad_cargo_id: autoridadCargoId === "" ? null : autoridadCargoId,
        lineas,
        evidencias,
      };

      if (esEdicion && causadoId) {
        const causadoGuardado = await apiFetch<Causado>(`/gobierno/presupuesto/causados/${causadoId}`, {
          method: "PUT",
          body,
          ifMatch: String(causado?.version ?? ""),
        });
        return causadoGuardado;
      }

      return await apiFetch<Causado>(`/gobierno/presupuesto/ejercicios/${yearId}/causados`, {
        method: "POST",
        body,
      });
    },
    onSuccess: async (causadoGuardado) => {
      await queryClient.invalidateQueries({ queryKey: [...CONSULTA_CAUSADOS] });
      notify({ type: "success", title: "Borrador guardado" });
      navigate(`${RUTA_CAUSADOS}/${causadoGuardado.id}`);
    },
    onError: (error: unknown) => {
      setFieldErrors({});
      setErrorFormulario("");
      if (error instanceof ApiError) {
        setErrorFormulario(error.message);
        if (error.code === "GOV_BUDGET_CAUSE_STALE") {
          setErrorFormulario(error.message);
        }
        if (error.fieldErrors) {
          setFieldErrors(error.fieldErrors);
        }
      } else {
        setErrorFormulario("No se pudo guardar el causado");
      }
    },
  });

  const compromisoElegido = useMemo(() => {
    if (!opciones || !compromisoId) return null;
    return opciones.compromisos.find((c) => c.id === compromisoId) ?? null;
  }, [opciones, compromisoId]);

  const lineasCompromiso = useMemo(() => {
    return compromisoElegido?.lineas ?? [];
  }, [compromisoElegido]);

  const politicaElegida = useMemo(() => {
    if (!opciones || !politicaId) return null;
    return opciones.politicas.find((p) => p.id === politicaId) ?? null;
  }, [opciones, politicaId]);

  const hayExceso = useMemo(() => {
    return lineasCompromiso.some((linea) => {
      const monto = montos[linea.id];
      if (!monto || Number(monto) <= 0) return false;
      return Number(monto) > Number(linea.pendiente);
    });
  }, [lineasCompromiso, montos]);

  const totalACausar = useMemo(() => {
    return lineasCompromiso.reduce((total, linea) => {
      const monto = montos[linea.id];
      if (!monto || Number(monto) <= 0) return total;
      return total + Number(monto);
    }, 0);
  }, [lineasCompromiso, montos]);

  const totalPendienteTras = useMemo(() => {
    return lineasCompromiso.reduce((total, linea) => {
      const monto = montos[linea.id];
      if (!monto || Number(monto) <= 0) return total + Number(linea.pendiente);
      return total + Number(linea.pendiente) - Number(monto);
    }, 0);
  }, [lineasCompromiso, montos]);

  const evidenciasValidas = useMemo(() => {
    if (!opciones) return [];
    return opciones.evidencias.filter((e) => e.valida);
  }, [opciones]);

  const evidenciasInvalidas = useMemo(() => {
    if (!opciones) return [];
    return opciones.evidencias.filter((e) => !e.valida);
  }, [opciones]);

  const documentosObligatorios = useMemo(() => {
    if (!politicaElegida) return [];
    return politicaElegida.documentos.filter((d) => d.obligatorio);
  }, [politicaElegida]);

  const puedeGuardar = useMemo(() => {
    if (!compromisoId || !politicaId) return false;
    if (concepto.trim().length < 10) return false;
    const hayMontoPositivo = lineasCompromiso.some((linea) => {
      const monto = montos[linea.id];
      return monto && Number(monto) > 0;
    });
    if (!hayMontoPositivo) return false;
    if (hayExceso) return false;
    return true;
  }, [compromisoId, politicaId, concepto, lineasCompromiso, montos, hayExceso]);

  if (!tienePermiso) {
    return (
      <PageContent>
        <EmptyState title="Sin acceso" />
      </PageContent>
    );
  }

  if (esEdicion) {
    if (causadoQuery.isLoading) {
      return (
        <PageContent>
          <LoadingState />
        </PageContent>
      );
    }
    if (causadoQuery.isError) {
      return (
        <PageContent>
          <ErrorState title="Error al cargar el causado" message={causadoQuery.error instanceof Error ? causadoQuery.error.message : "No se pudo cargar el causado"} onRetry={() => void causadoQuery.refetch()} />
        </PageContent>
      );
    }
    if (!causado) {
      return (
        <PageContent>
          <EmptyState title="No se encontró el causado" action={<Link to={RUTA_CAUSADOS}>Volver a Causados</Link>} />
        </PageContent>
      );
    }
    if (causado.estado !== "BORRADOR") {
      return (
        <PageContent>
          <EmptyState title="Solo se edita un borrador" action={<Link to={`${RUTA_CAUSADOS}/${causado.id}`}>Ir al detalle</Link>} />
        </PageContent>
      );
    }
  } else {
    if (!yearId) {
      return (
        <PageContent>
          <EmptyState title="Falta el ejercicio" action={<Link to={RUTA_CAUSADOS}>Volver a Causados</Link>} />
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
        <ErrorState title="Error al cargar las opciones" message={opcionesQuery.error instanceof Error ? opcionesQuery.error.message : "No se pudieron cargar las opciones"} onRetry={() => void opcionesQuery.refetch()} />
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

  const titulo = esEdicion ? "Editar borrador de causado" : "Nuevo causado";
  const rutaCancelar = esEdicion && causado ? `${RUTA_CAUSADOS}/${causado.id}` : RUTA_CAUSADOS;

  function manejarCambioMonto(lineaId: string, valor: string) {
    setMontos((previos) => ({ ...previos, [lineaId]: valor }));
  }

  function manejarCambioEvidencia(clave: EvidenciaSeleccion, marcado: boolean) {
    setEvidenciasSeleccionadas((previas) => {
      const nuevas = new Set(previas);
      if (marcado) {
        nuevas.add(clave);
      } else {
        nuevas.delete(clave);
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
        crumbs={[{ label: "Causados", to: RUTA_CAUSADOS }, { label: titulo }]}
      />
      <form onSubmit={manejarEnvio} className="space-y-8">
        {errorFormulario && (
          <div role="alert" className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-700">
            {errorFormulario}
            {mutacionGuardar.error instanceof ApiError && mutacionGuardar.error.code === "GOV_BUDGET_CAUSE_STALE" && (
              <button
                type="button"
                onClick={() => {
                  setInicializado(false);
                  setErrorFormulario("");
                  setFieldErrors({});
                  void causadoQuery.refetch();
                }}
                className="ml-4 font-semibold underline"
              >
                Recargar
              </button>
            )}
          </div>
        )}

        <section aria-labelledby="seccion-compromiso">
          <h2 id="seccion-compromiso" className="text-lg font-semibold">Compromiso</h2>
          <div className="mt-4">
            <label htmlFor="compromiso" className="block text-sm font-medium text-slate-700">
              Compromiso
            </label>
            <select
              id="compromiso"
              className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              value={compromisoId}
              onChange={(e) => {
                setCompromisoId(e.target.value);
                setMontos({});
              }}
            >
              <option value="">Seleccione un compromiso</option>
              {opciones.compromisos.map((compromiso) => (
                <option key={compromiso.id} value={compromiso.id}>
                  {compromiso.codigo} · {compromiso.concepto} · {compromiso.pendiente} {opciones.moneda}
                </option>
              ))}
            </select>
          </div>

          {compromisoElegido && (
            <>
              <div className="mt-4 overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200">
                  <thead className="bg-slate-50">
                    <tr>
                      <th scope="col" className="px-3 py-2 text-left text-xs font-medium text-slate-500">Partida</th>
                      <th scope="col" className="px-3 py-2 text-left text-xs font-medium text-slate-500">Categoría</th>
                      <th scope="col" className="px-3 py-2 text-right text-xs font-medium text-slate-500">Comprometido</th>
                      <th scope="col" className="px-3 py-2 text-right text-xs font-medium text-slate-500">Causado</th>
                      <th scope="col" className="px-3 py-2 text-right text-xs font-medium text-slate-500">Pendiente</th>
                      <th scope="col" className="px-3 py-2 text-right text-xs font-medium text-slate-500">Monto a causar</th>
                      <th scope="col" className="px-3 py-2 text-right text-xs font-medium text-slate-500">Pendiente tras este causado</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {lineasCompromiso.map((linea) => {
                      const monto = montos[linea.id] ?? "";
                      const montoNumerico = Number(monto);
                      const excede = monto !== "" && montoNumerico > Number(linea.pendiente);
                      const pendienteTras = monto !== "" && montoNumerico > 0 ? Number(linea.pendiente) - montoNumerico : Number(linea.pendiente);
                      return (
                        <tr key={linea.id}>
                          <td className="px-3 py-2 text-sm text-slate-700">{linea.partida}</td>
                          <td className="px-3 py-2 text-sm text-slate-700">{linea.categoria}</td>
                          <td className="px-3 py-2 text-right text-sm text-slate-700">{linea.comprometido}</td>
                          <td className="px-3 py-2 text-right text-sm text-slate-700">{linea.causado}</td>
                          <td className="px-3 py-2 text-right text-sm text-slate-700">{linea.pendiente}</td>
                          <td className="px-3 py-2 text-right">
                            <input
                              type="text"
                              inputMode="decimal"
                              aria-label={`Monto a causar ${linea.partida}`}
                              className="w-full rounded-md border border-slate-300 px-2 py-1 text-right text-sm"
                              value={monto}
                              onChange={(e) => manejarCambioMonto(linea.id, e.target.value)}
                            />
                            {excede && (
                              <p role="alert" className="mt-1 text-xs text-red-700">
                                Supera el pendiente de la línea
                              </p>
                            )}
                          </td>
                          <td className="px-3 py-2 text-right text-sm text-slate-700">{pendienteTras.toFixed(2)}</td>
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
                <span>Total a causar: {totalACausar.toFixed(2)}</span>
                <span>Total pendiente tras: {totalPendienteTras.toFixed(2)}</span>
              </div>
            </>
          )}
        </section>

        <section aria-labelledby="seccion-politica">
          <h2 id="seccion-politica" className="text-lg font-semibold">Política aplicable</h2>
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
                  {politica.nombre} · {politica.tipo_gasto} · {DISPARADORES[politica.disparador]}
                </option>
              ))}
            </select>
          </div>

          {politicaElegida && (
            <div className="mt-4">
              <p className="text-sm font-medium text-slate-700">Se exige</p>
              <ul className="mt-2 list-disc pl-5 text-sm text-slate-700">
                <li>{DISPARADORES[politicaElegida.disparador]}</li>
                {politicaElegida.requiere_recepcion && <li>Recepción conforme</li>}
                {politicaElegida.requiere_valuacion && <li>Valuación conformada</li>}
                {politicaElegida.requiere_conformidad && <li>Conformidad</li>}
                {documentosObligatorios.map((documento) => {
                  const tipoDocumental = opciones.documentos.find((d) => d.tipo_documental_id === documento.document_type_id)?.tipo_documental ?? "Tipo documental requerido";
                  return <li key={documento.id}>{tipoDocumental}</li>;
                })}
              </ul>
            </div>
          )}
        </section>

        {compromisoId && (
          <section aria-labelledby="seccion-evidencias">
            <h2 id="seccion-evidencias" className="text-lg font-semibold">Evidencias</h2>
            <div className="mt-4 space-y-2">
              {evidenciasValidas.map((evidencia) => {
                const clave: EvidenciaSeleccion = `${evidencia.tipo}:${evidencia.id}`;
                return (
                  <label key={clave} className="flex items-start gap-2 text-sm text-slate-700">
                    <input
                      type="checkbox"
                      className="mt-1"
                      checked={evidenciasSeleccionadas.has(clave)}
                      onChange={(e) => manejarCambioEvidencia(clave, e.target.checked)}
                    />
                    <span>{evidencia.etiqueta} · {evidencia.estado} · {formatearFechaDeNegocio(evidencia.fecha)}</span>
                  </label>
                );
              })}
              {opciones.documentos.map((documento) => {
                const clave: EvidenciaSeleccion = `DOCUMENT:${documento.id}`;
                return (
                  <label key={clave} className="flex items-start gap-2 text-sm text-slate-700">
                    <input
                      type="checkbox"
                      className="mt-1"
                      checked={evidenciasSeleccionadas.has(clave)}
                      onChange={(e) => manejarCambioEvidencia(clave, e.target.checked)}
                    />
                    <span>{documento.etiqueta} · {documento.tipo_documental}</span>
                  </label>
                );
              })}
              {fieldErrors["evidencias"] && (
                <p role="alert" className="mt-2 text-sm text-red-700">
                  {fieldErrors["evidencias"].join(", ")}
                </p>
              )}
              {evidenciasInvalidas.length > 0 && (
                <div className="mt-4">
                  <p className="text-sm font-medium text-slate-700">No válidas</p>
                  {evidenciasInvalidas.map((evidencia) => (
                    <label key={`${evidencia.tipo}:${evidencia.id}`} className="flex items-start gap-2 text-sm text-slate-400">
                      <input type="checkbox" disabled className="mt-1" />
                      <span>{evidencia.etiqueta} · {evidencia.estado} · No válida</span>
                    </label>
                  ))}
                </div>
              )}
              <AdjuntosPanel
                resourceType="GovernmentBudgetYear"
                resourceId={yearId ?? ""}
                title="Subir un documento de soporte"
                onChange={() => void opcionesQuery.refetch()}
              />
            </div>
          </section>
        )}

        <section aria-labelledby="seccion-datos">
          <h2 id="seccion-datos" className="text-lg font-semibold">Datos</h2>
          <div className="mt-4 space-y-4">
            <FormField
              label="Fecha efectiva"
              htmlFor="fecha-efectiva"
              required
              error={fieldErrors["fecha_efectiva"]?.join(", ")}
            >
              <TextInput
                id="fecha-efectiva"
                type="date"
                value={fechaEfectiva}
                onChange={(e) => setFechaEfectiva(e.target.value)}
                required
              />
            </FormField>
            <FormField
              label="Concepto"
              htmlFor="concepto"
              required
              help="Entre 10 y 500 caracteres"
              error={fieldErrors["concepto"]?.join(", ")}
            >
              <textarea
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                maxLength={500}
                value={concepto}
                onChange={(e) => setConcepto(e.target.value)}
                required
              />
            </FormField>
            <p id="concepto-contador" aria-live="polite" className="mt-1 text-right text-xs text-slate-500">{concepto.length}/500</p>
            <FormField label="Beneficiario" htmlFor="beneficiario">
              <TextInput
                id="beneficiario"
                value={beneficiario}
                onChange={(e) => setBeneficiario(e.target.value)}
              />
            </FormField>
            <FormField label="Autoridad que formalizará" htmlFor="autoridad-cargo" help="Se exige al formalizar">
              <select
                id="autoridad-cargo"
                className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                value={autoridadCargoId}
                onChange={(e) => setAutoridadCargoId(e.target.value)}
              >
                <option value="">Sin indicar</option>
                {opciones.cargos.map((cargo) => (
                  <option key={cargo.id} value={cargo.id}>
                    {cargo.etiqueta}
                  </option>
                ))}
              </select>
            </FormField>
          </div>
        </section>

        <div className="flex items-center gap-4">
          <Button type="submit" variant="primary" disabled={!puedeGuardar || mutacionGuardar.isPending}>
            {mutacionGuardar.isPending ? "Guardando..." : "Guardar borrador"}
          </Button>
          <Link className="inline-flex items-center rounded-md border border-slate-300 px-3 py-2 text-sm" to={rutaCancelar}>
            Cancelar
          </Link>
        </div>
      </form>
    </PageContent>
  );
}
