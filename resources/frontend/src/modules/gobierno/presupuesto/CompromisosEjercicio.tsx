import { useId, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import { descargarArchivo } from "@/api/descargas";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { formatMoney } from "@/lib/format";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import { formatearDecimal } from "@/modules/gobierno/tesoreria/tasas/api";
import {
  CONSULTA_PRESUPUESTO,
  type Compromiso,
  type CompromisosVista,
  type EjercicioDetalle,
  type EscribirBloque,
  type OpcionesCompromisoVista,
  type VerificacionLimite,
  type ConversionLimite,
} from "./api";

interface CompromisosEjercicioProps {
  detalle: EjercicioDetalle;
  puedeComprometer: boolean;
  escribirBloque: EscribirBloque;
  erroresServidor: Record<string, string[]>;
}

const errorDe = (
  erroresServidor: Record<string, string[]>,
  campo: string,
): string | undefined => erroresServidor[campo]?.[0];

const normalizarMonto = (texto: string): string => {
  const sinEspacios = texto.replace(/\s+/g, "");
  const sinPuntosMiles = sinEspacios.replace(/\.(?=\d{3}(\D|$))/g, "");
  return sinPuntosMiles.replace(",", ".");
};

const aCentimos = (texto: string): bigint | null => {
  const monto = normalizarMonto(texto);
  if (!/^\d+(\.\d{1,2})?$/.test(monto)) return null;

  const [entero, decimal] = monto.split(".");
  const enteroCentimos = BigInt(entero) * 100n;
  const decimalCentimos = decimal ? BigInt(decimal.padEnd(2, "0")) : 0n;
  return enteroCentimos + decimalCentimos;
};

function BloqueConversion({
  conversion,
}: {
  conversion: ConversionLimite;
}): React.JSX.Element {
  if (conversion.resultado === "SIN_TASA") {
    return (
      <div role="group" aria-label="Verificación del límite con tasa oficial">
        <p role="alert">
          {`No hay tasa oficial BCV aprobada aplicable al ${formatearFechaDeNegocio(conversion.fecha)} para ${conversion.monedas_sin_tasa.join(", ")}: el compromiso no podrá registrarse hasta que Tesorería apruebe la tasa.`}
        </p>
      </div>
    );
  }

  if (conversion.requiere_conversion) {
    return (
      <div role="group" aria-label="Verificación del límite con tasa oficial">
        <p>{`Moneda de operación: ${conversion.moneda_operacion}`}</p>
        <p>{`Moneda del límite: ${conversion.moneda_limite}`}</p>
        {conversion.tasas.map((t) => (
          <div key={t.tasa_id}>
            <p>{`Tasa oficial utilizada: 1 ${t.moneda} = ${formatearDecimal(t.valor, 8)} VES`}</p>
            <p>{`Fecha de la tasa: ${formatearFechaDeNegocio(t.fecha_efectiva)}`}</p>
            <p>{`Fuente: ${t.fuente} · ${t.fuente_referencia}`}</p>
          </div>
        ))}
        <p>
          {`Resultado de la comparación: ${conversion.dentro_del_limite ? "dentro del límite" : "excede el límite"} (${formatearDecimal(conversion.total_ves ?? "0", 2)} VES ${conversion.dentro_del_limite ? "≤" : ">"} ${formatearDecimal(conversion.limite_ves ?? "0", 2)} VES)`}
        </p>
      </div>
    );
  }

  return (
    <div role="group" aria-label="Verificación del límite con tasa oficial">
      <p>
        {`Misma moneda (${conversion.moneda_operacion}): comparación directa · ${conversion.dentro_del_limite ? "dentro del límite" : "excede el límite"}`}
      </p>
    </div>
  );
}

export function CompromisosEjercicio({
  detalle,
  puedeComprometer,
  escribirBloque,
  erroresServidor,
}: CompromisosEjercicioProps) {
  const idSeccion = useId();
  const [lineas, setLineas] = useState<{ certificadoId: string; monto: string }[]>([
    { certificadoId: "", monto: "" },
  ]);
  const [concepto, setConcepto] = useState("");
  const [autoridadId, setAutoridadId] = useState("");
  const [soporteId, setSoporteId] = useState("");
  const [motivos, setMotivos] = useState<Record<string, string>>({});
  const [ultimo, setUltimo] = useState<Compromiso | null>(null);

  const totalCentimos = lineas.reduce<bigint | null>((acumulado, linea) => {
    const centimos = aCentimos(linea.monto);
    if (centimos === null || acumulado === null) return null;
    return acumulado + centimos;
  }, 0n);

  const totalTexto =
    totalCentimos === null
      ? "0.00"
      : `${String(totalCentimos / 100n)}.${String(totalCentimos % 100n).padStart(2, "0")}`;

  const opcionesQuery = useQuery({
    queryKey: [...CONSULTA_PRESUPUESTO, "compromisos-opciones", detalle.id],
    queryFn: () =>
      apiFetch<OpcionesCompromisoVista>(
        `/gobierno/presupuesto/ejercicios/${detalle.id}/compromisos/opciones`,
      ),
    retry: false,
  });

  const compromisosQuery = useQuery({
    queryKey: [...CONSULTA_PRESUPUESTO, "compromisos", detalle.id],
    queryFn: () =>
      apiFetch<CompromisosVista>(
        `/gobierno/presupuesto/ejercicios/${detalle.id}/compromisos`,
      ),
    retry: false,
  });

  const autoridadSeleccionada = opcionesQuery.data?.autoridades.find(
    (a) => a.cargo_id === autoridadId,
  );

  const verificacionQuery = useQuery({
    queryKey: [
      ...CONSULTA_PRESUPUESTO,
      "verificacion-limite",
      detalle.id,
      autoridadId,
      totalTexto,
    ],
    queryFn: () =>
      apiFetch<VerificacionLimite>(
        `/gobierno/presupuesto/ejercicios/${detalle.id}/compromisos/verificacion-limite?autoridad_cargo_id=${encodeURIComponent(autoridadId)}&total=${totalTexto}`,
      ),
    enabled:
      autoridadSeleccionada?.limite_tipo === "MONTO" &&
      totalCentimos !== null &&
      totalCentimos > 0n,
    retry: false,
  });

  if (opcionesQuery.isLoading || compromisosQuery.isLoading) {
    return <p>Cargando compromisos…</p>;
  }

  if (opcionesQuery.isError || !opcionesQuery.data) {
    return <p>No fue posible cargar los compromisos.</p>;
  }

  const opciones = opcionesQuery.data;
  const compromisos = compromisosQuery.data?.items ?? [];

  const puedeAnularVigentes =
    puedeComprometer &&
    (detalle.estado === "APROBADO" || detalle.estado === "RECONDUCIDO");


  const submitCompromiso = async () => {
    try {
      const k = await escribirBloque<Compromiso>("/compromisos", "POST", {
        concepto,
        autoridad_cargo_id: autoridadId,
        soporte_documento_id: soporteId,
        lineas: lineas.map((l) => ({
          certificado_id: l.certificadoId,
          monto: normalizarMonto(l.monto),
        })),
      });
      setUltimo(k);
      setLineas([{ certificadoId: "", monto: "" }]);
      setConcepto("");
    } catch {
      // ya informado
    }
  };

  const actualizarLinea = (indice: number, campo: "certificadoId" | "monto", valor: string) => {
    setLineas((previas) =>
      previas.map((linea, i) => (i === indice ? { ...linea, [campo]: valor } : linea)),
    );
  };

  const quitarLinea = (indice: number) => {
    setLineas((previas) => previas.filter((_, i) => i !== indice));
  };

  const anadirLinea = () => {
    setLineas((previas) => [...previas, { certificadoId: "", monto: "" }]);
  };

  const certificadosDisponiblesParaLinea = (indice: number) => {
    const idsUsados = new Set(
      lineas
        .filter((_, i) => i !== indice)
        .map((linea) => linea.certificadoId)
        .filter((id) => id !== ""),
    );
    return opciones.certificados.filter((cert) => !idsUsados.has(cert.certificado_id));
  };

  const primeraLineaConCertificado = lineas.find((linea) => linea.certificadoId !== "");

  return (
    <section aria-labelledby={idSeccion}>
      <h2 id={idSeccion}>Compromisos</h2>
      <p>
        Cada compromiso consume certificaciones vigentes. Comprometer no reduce
        dos veces la disponibilidad: el monto pasa de certificado a comprometido
        (LOPPM arts. 242 y 248). Quien certifica no compromete.
      </p>

      {!opciones.comprometible ? (
        <p>
          El ejercicio no admite compromisos: debe estar aprobado o reconducido
          y dentro de su año.
        </p>
      ) : null}

      {opciones.comprometible && puedeComprometer ? (
        <>
          <h3>Registrar compromiso</h3>
          {opciones.certificados.length === 0 ? (
            <p>No hay certificaciones con remanente disponible.</p>
          ) : (
            <form
              onSubmit={(event) => {
                event.preventDefault();
                void submitCompromiso();
              }}
            >
              {lineas.map((linea, indice) => {
                const certificadosDisponibles = certificadosDisponiblesParaLinea(indice);
                const certificadoSeleccionado = opciones.certificados.find(
                  (cert) => cert.certificado_id === linea.certificadoId,
                );

                return (
                  <div key={indice}>
                    <FormField label={`Certificación de la imputación ${indice + 1}`} required>
                      <select
                        className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                        value={linea.certificadoId}
                        onChange={(event) => actualizarLinea(indice, "certificadoId", event.target.value)}
                      >
                        <option value="">Seleccione…</option>
                        {certificadosDisponibles.map((cert) => (
                          <option key={cert.certificado_id} value={cert.certificado_id}>
                            {cert.etiqueta}
                          </option>
                        ))}
                      </select>
                    </FormField>
                    {certificadoSeleccionado ? (
                      <p>
                        {`${certificadoSeleccionado.categoria} | ${certificadoSeleccionado.partida} | ${certificadoSeleccionado.fuente} — certificado ${formatMoney(certificadoSeleccionado.monto)}, consumido ${formatMoney(certificadoSeleccionado.consumido)}, remanente ${formatMoney(certificadoSeleccionado.remanente)} ${opciones.moneda}`}
                      </p>
                    ) : null}
                    <FormField label={`Monto de la imputación ${indice + 1}`} required>
                      <TextInput
                        value={linea.monto}
                        onChange={(evento) => actualizarLinea(indice, "monto", evento.target.value)}
                        inputMode="decimal"
                      />
                    </FormField>
                    {lineas.length > 1 ? (
                      <Button
                        variant="secondary"
                        type="button"
                        onClick={() => quitarLinea(indice)}
                      >
                        {`Quitar imputación ${indice + 1}`}
                      </Button>
                    ) : null}
                  </div>
                );
              })}

              <Button
                variant="secondary"
                type="button"
                onClick={anadirLinea}
                disabled={lineas.length >= 20}
              >
                Añadir imputación
              </Button>

              {primeraLineaConCertificado ? (
                <p>
                  Expediente:{" "}
                  {opciones.certificados.find(
                    (cert) => cert.certificado_id === primeraLineaConCertificado.certificadoId,
                  )?.expediente_referencia ?? ""}
                </p>
              ) : null}

              {errorDe(erroresServidor, "lineas") && (
                <p role="alert">{errorDe(erroresServidor, "lineas")}</p>
              )}
              <p>
                Total del compromiso: {formatMoney(totalTexto)} {opciones.moneda}
              </p>

              <FormField label="Concepto" required error={errorDe(erroresServidor, "concepto")}>
                <TextInput
                  value={concepto}
                  onChange={(evento) => setConcepto(evento.target.value)}
                />
              </FormField>

              <FormField label="Autoridad que compromete (cargo)" required error={errorDe(erroresServidor, "autoridad_cargo_id")}>
                {opciones.autoridades.length === 0 ? (
                  <p>
                    No hay cargos con competencia COMPROMETER en materia de
                    PRESUPUESTO vigentes hoy (ORG-03).
                  </p>
                ) : (
                  <select
                    className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                    value={autoridadId}
                    onChange={(event) => setAutoridadId(event.target.value)}
                  >
                    <option value="">Seleccione…</option>
                    {opciones.autoridades.map((autoridad) => (
                      <option key={autoridad.cargo_id} value={autoridad.cargo_id}>
                        {`${autoridad.etiqueta} (${autoridad.unidad}) · límite ${autoridad.limite}`}
                      </option>
                    ))}
                  </select>
                )}
              </FormField>
              {verificacionQuery.data?.verificacion ? (
                <BloqueConversion conversion={verificacionQuery.data.verificacion} />
              ) : null}

              <FormField label="Soporte documental" required error={errorDe(erroresServidor, "soporte_documento_id")}>
                {opciones.soportes.length === 0 ? (
                  <p>
                    Vincule primero al ejercicio el documento de soporte del
                    compromiso.
                  </p>
                ) : (
                  <select
                    className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                    value={soporteId}
                    onChange={(event) => setSoporteId(event.target.value)}
                  >
                    <option value="">Seleccione…</option>
                    {opciones.soportes.map((soporte) => (
                      <option key={soporte.id} value={soporte.id}>
                        {soporte.etiqueta}
                      </option>
                    ))}
                  </select>
                )}
              </FormField>

              <Button type="submit">Registrar compromiso</Button>
            </form>
          )}
          {ultimo ? (
            <p>
              Compromiso {ultimo.codigo} registrado por{" "}
              {formatMoney(ultimo.total)} {ultimo.moneda}.
            </p>
          ) : null}
          {ultimo?.conversion ? (
            <BloqueConversion conversion={ultimo.conversion} />
          ) : null}
        </>
      ) : null}

      <h3>Compromisos registrados</h3>
      <div
        role="region"
        aria-label="Tabla de compromisos"
        className="overflow-x-auto"
        tabIndex={0}
      >
        {compromisos.length === 0 ? (
          <p>Sin compromisos.</p>
        ) : (
          <table className="min-w-max">
            <thead>
              <tr>
                <th>Identificador</th>
                <th>Fecha</th>
                <th>Imputaciones</th>
                <th>Total</th>
                <th>Expediente</th>
                <th>Autoridad</th>
                <th>Soporte</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {compromisos.map((k) => (
                <tr key={k.id}>
                  <td>{k.codigo}</td>
                  <td>{k.fecha}</td>
                  <td>
                    <ul>
                      {k.lineas.map((linea) => (
                        <li key={linea.linea}>
                          {`${linea.certificado_codigo}: ${formatMoney(linea.monto)}`}
                        </li>
                      ))}
                    </ul>
                  </td>
                  <td>
                    {formatMoney(k.total)} {k.moneda}
                  </td>
                  <td>{k.expediente_referencia}</td>
                  <td>
                    {k.autoridad_cargo}
                    {k.autoridad_funcionario ? ` · ${k.autoridad_funcionario}` : ""}
                    {k.conversion && k.conversion.tasas.length > 0 ? (
                      <>
                        <br />
                        {`Tasa BCV: ${k.conversion.tasas
                          .map(
                            (t) =>
                              `1 ${t.moneda} = ${formatearDecimal(t.valor, 8)} VES (${formatearFechaDeNegocio(t.fecha_efectiva)})`,
                          )
                          .join("; ")}`}
                      </>
                    ) : null}
                  </td>
                  <td>{k.soporte}</td>
                  <td>
                    {k.estado === "VIGENTE"
                      ? "Vigente"
                      : `Anulado: ${k.motivo_anulacion ?? ""}`}
                  </td>
                  <td>
                    <Button
                      variant="secondary"
                      onClick={() =>
                        void descargarArchivo(
                          `/gobierno/presupuesto/ejercicios/${detalle.id}/compromisos/${k.id}/documento`,
                          k.documento_nombre,
                        )
                      }
                    >
                      {`Descargar ${k.codigo}`}
                    </Button>
                    {k.estado === "VIGENTE" && puedeAnularVigentes ? (
                      <>
                        <TextInput
                          aria-label={`Motivo de anulación de ${k.codigo}`}
                          value={motivos[k.id] ?? ""}
                          onChange={(evento) =>
                            setMotivos((previos) => ({
                              ...previos,
                              [k.id]: evento.target.value,
                            }))
                          }
                        />
                        <AsyncButton
                          idleText={`Anular ${k.codigo}`}
                          onClick={async () => {
                            try {
                              await escribirBloque<Compromiso>(
                                `/compromisos/${k.id}/anular`,
                                "POST",
                                { motivo: motivos[k.id] ?? "" },
                              );
                            } catch {
                              /* ya informado */
                            }
                          }}
                        />
                      </>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
