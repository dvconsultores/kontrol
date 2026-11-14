import { useId, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import { descargarArchivo } from "@/api/descargas";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { formatMoney } from "@/lib/format";
import {
  CONSULTA_PRESUPUESTO,
  type Certificacion,
  type CertificacionesVista,
  type DisponibilidadVista,
  type EjercicioDetalle,
  type EscribirBloque,
} from "./api";

interface DisponibilidadEjercicioProps {
  detalle: EjercicioDetalle;
  puedeCertificar: boolean;
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

export function DisponibilidadEjercicio({
  detalle,
  puedeCertificar,
  escribirBloque,
  erroresServidor,
}: DisponibilidadEjercicioProps) {
  const idSeccion = useId();
  const [categoria, setCategoria] = useState("");
  const [unidad, setUnidad] = useState("");
  const [partida, setPartida] = useState("");
  const [fuente, setFuente] = useState("");

  const [creditoId, setCreditoId] = useState("");
  const [monto, setMonto] = useState("");
  const [concepto, setConcepto] = useState("");
  const [expedienteId, setExpedienteId] = useState("");
  const [referencia, setReferencia] = useState("");
  const [firmanteId, setFirmanteId] = useState("");
  const [motivos, setMotivos] = useState<Record<string, string>>({});
  const [ultima, setUltima] = useState<Certificacion | null>(null);

  const filtrosActivos = new URLSearchParams();
  if (categoria) filtrosActivos.set("categoria_id", categoria);
  if (unidad) filtrosActivos.set("unidad_id", unidad);
  if (partida) filtrosActivos.set("partida_id", partida);
  if (fuente) filtrosActivos.set("fuente_id", fuente);
  const qs = filtrosActivos.size > 0 ? `?${filtrosActivos.toString()}` : "";

  const vistaQuery = useQuery({
    queryKey: [
      ...CONSULTA_PRESUPUESTO,
      "disponibilidad",
      detalle.id,
      categoria,
      unidad,
      partida,
      fuente,
    ],
    queryFn: () =>
      apiFetch<DisponibilidadVista>(
        `/gobierno/presupuesto/ejercicios/${detalle.id}/disponibilidad${qs}`,
      ),
    retry: false,
  });

  const certificacionesQuery = useQuery({
    queryKey: [...CONSULTA_PRESUPUESTO, "certificaciones", detalle.id],
    queryFn: () =>
      apiFetch<CertificacionesVista>(
        `/gobierno/presupuesto/ejercicios/${detalle.id}/certificaciones`,
      ),
    retry: false,
  });

  if (vistaQuery.isLoading) {
    return <p>Cargando disponibilidad…</p>;
  }

  if (vistaQuery.isError || !vistaQuery.data) {
    return <p>No fue posible cargar la disponibilidad.</p>;
  }

  const vista = vistaQuery.data;
  const certificaciones = certificacionesQuery.data?.items ?? [];
  const creditoSeleccionado = vista.items.find(
    (item) => item.credito_id === creditoId,
  );
  const puedeAnularVigentes =
    puedeCertificar &&
    (detalle.estado === "APROBADO" || detalle.estado === "RECONDUCIDO");

  const submitCertificacion = async () => {
    try {
      const c = await escribirBloque<Certificacion>("/certificaciones", "POST", {
        credito_id: creditoId,
        monto: normalizarMonto(monto),
        concepto,
        expediente_id: expedienteId || null,
        expediente_referencia: expedienteId ? null : referencia,
        firmante_cargo_id: firmanteId,
      });
      setUltima(c);
      setMonto("");
      setConcepto("");
      setReferencia("");
    } catch {
      // ya informado
    }
  };

  return (
    <section aria-labelledby={idSeccion}>
      <h2 id={idSeccion}>Disponibilidad y certificaciones</h2>
      <p>
        La disponibilidad se calcula al momento: crédito aprobado menos
        certificaciones vigentes (LOPPM art. 242). No es disponibilidad de caja.
      </p>

      <FormField label="Categoría programática">
        <select
          className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
          value={categoria}
          onChange={(event) => setCategoria(event.target.value)}
        >
          <option value="">Todas</option>
          {vista.filtros.categorias.map((opcion) => (
            <option key={opcion.id} value={opcion.id}>
              {opcion.etiqueta}
            </option>
          ))}
        </select>
      </FormField>
      <FormField label="Unidad ejecutora">
        <select
          className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
          value={unidad}
          onChange={(event) => setUnidad(event.target.value)}
        >
          <option value="">Todas</option>
          {vista.filtros.unidades.map((opcion) => (
            <option key={opcion.id} value={opcion.id}>
              {opcion.etiqueta}
            </option>
          ))}
        </select>
      </FormField>
      <FormField label="Partida">
        <select
          className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
          value={partida}
          onChange={(event) => setPartida(event.target.value)}
        >
          <option value="">Todas</option>
          {vista.filtros.partidas.map((opcion) => (
            <option key={opcion.id} value={opcion.id}>
              {opcion.etiqueta}
            </option>
          ))}
        </select>
      </FormField>
      <FormField label="Fuente">
        <select
          className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
          value={fuente}
          onChange={(event) => setFuente(event.target.value)}
        >
          <option value="">Todas</option>
          {vista.filtros.fuentes.map((opcion) => (
            <option key={opcion.id} value={opcion.id}>
              {opcion.etiqueta}
            </option>
          ))}
        </select>
      </FormField>

      <div role="region" aria-label="Tabla de disponibilidad" className="overflow-x-auto" tabIndex={0}>
        {vista.items.length === 0 ? (
          <p>Sin créditos.</p>
        ) : (
          <table className="min-w-max">
            <thead>
              <tr>
                <th>Categoría</th>
                <th>Unidad ejecutora</th>
                <th>Partida</th>
                <th>Fuente</th>
                <th>Crédito</th>
                <th>Certificado</th>
                <th>Disponible</th>
              </tr>
            </thead>
            <tbody>
              {vista.items.map((item) => (
                <tr key={item.credito_id}>
                  <td>{item.categoria.etiqueta}</td>
                  <td>{item.unidad?.etiqueta ?? "Sin asignar"}</td>
                  <td>{item.partida.etiqueta}</td>
                  <td>{item.fuente.etiqueta}</td>
                  <td>{formatMoney(item.credito)} {vista.moneda}</td>
                  <td>{formatMoney(item.certificado)} {vista.moneda}</td>
                  <td>{formatMoney(item.disponible)} {vista.moneda}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={4}>Totales</td>
                <td>{formatMoney(vista.totales.credito)} {vista.moneda}</td>
                <td>{formatMoney(vista.totales.certificado)} {vista.moneda}</td>
                <td>{formatMoney(vista.totales.disponible)} {vista.moneda}</td>
              </tr>
            </tfoot>
          </table>
        )}
      </div>

      {!vista.certificable ? (
        <p>
          El ejercicio no admite certificaciones: debe estar aprobado o
          reconducido y dentro de su año.
        </p>
      ) : null}

      {vista.certificable && puedeCertificar ? (
        <>
          <h3>Emitir certificación</h3>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void submitCertificacion();
            }}
          >
            <FormField label="Crédito presupuestario" required error={errorDe(erroresServidor, "credito_id")}>
              <select
                className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                value={creditoId}
                onChange={(event) => setCreditoId(event.target.value)}
              >
                <option value="">Seleccione…</option>
                {vista.items.map((item) => (
                  <option key={item.credito_id} value={item.credito_id}>
                    {`${item.categoria.etiqueta} | ${item.partida.etiqueta} | ${item.fuente.etiqueta} — disponible ${formatMoney(item.disponible)} ${vista.moneda}`}
                  </option>
                ))}
              </select>
            </FormField>
            {creditoSeleccionado ? (
              <p>
                Disponible: {formatMoney(creditoSeleccionado.disponible)}{" "}
                {vista.moneda}
              </p>
            ) : null}
            <FormField label="Monto" required error={errorDe(erroresServidor, "monto")}>
              <TextInput
                value={monto}
                onChange={(evento) => setMonto(evento.target.value)}
                inputMode="decimal"
              />
            </FormField>
            <FormField label="Concepto" required error={errorDe(erroresServidor, "concepto")}>
              <TextInput value={concepto} onChange={(evento) => setConcepto(evento.target.value)} />
            </FormField>
            <FormField label="Expediente de contratación" error={errorDe(erroresServidor, "expediente_id")}>
              <select
                className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                value={expedienteId}
                onChange={(event) => setExpedienteId(event.target.value)}
              >
                <option value="">Sin expediente de contratación</option>
                {vista.expedientes.map((opcion) => (
                  <option key={opcion.id} value={opcion.id}>
                    {opcion.etiqueta}
                  </option>
                ))}
              </select>
            </FormField>
            {expedienteId === "" ? (
              <FormField
                label="Referencia del expediente"
                required
                error={errorDe(erroresServidor, "expediente_referencia")}
              >
                <TextInput value={referencia} onChange={(evento) => setReferencia(evento.target.value)} />
              </FormField>
            ) : null}
            <FormField
              label="Firmante (cargo)"
              required
              error={errorDe(erroresServidor, "firmante_cargo_id")}
            >
              {vista.firmantes.length === 0 ? (
                <p>
                  No hay cargos con competencia FIRMAR en materia de PRESUPUESTO
                  vigentes hoy (ORG-03).
                </p>
              ) : (
                <select
                  className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                  value={firmanteId}
                  onChange={(event) => setFirmanteId(event.target.value)}
                >
                  <option value="">Seleccione…</option>
                  {vista.firmantes.map((firmante) => (
                    <option key={firmante.cargo_id} value={firmante.cargo_id}>
                      {`${firmante.etiqueta} (${firmante.unidad})`}
                    </option>
                  ))}
                </select>
              )}
            </FormField>
            <Button type="submit">Emitir certificación</Button>
          </form>
          {ultima ? (
            <p>
              Certificación {ultima.codigo} emitida: saldo antes{" "}
              {formatMoney(ultima.saldo_antes)} {ultima.moneda}, saldo después{" "}
              {formatMoney(ultima.saldo_despues)} {ultima.moneda}.
            </p>
          ) : null}
        </>
      ) : null}

      <h3>Certificaciones emitidas</h3>
      <div role="region" aria-label="Tabla de certificaciones" className="overflow-x-auto" tabIndex={0}>
        {certificaciones.length === 0 ? (
          <p>Sin certificaciones.</p>
        ) : (
          <table className="min-w-max">
            <thead>
              <tr>
                <th>Identificador</th>
                <th>Fecha</th>
                <th>Crédito</th>
                <th>Expediente</th>
                <th>Monto</th>
                <th>Saldo antes</th>
                <th>Saldo después</th>
                <th>Firmante</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {certificaciones.map((c) => (
                <tr key={c.id}>
                  <td>{c.codigo}</td>
                  <td>{c.fecha}</td>
                  <td>{`${c.categoria} | ${c.partida} | ${c.fuente}`}</td>
                  <td>{c.expediente_referencia}</td>
                  <td>{formatMoney(c.monto)} {c.moneda}</td>
                  <td>{formatMoney(c.saldo_antes)} {c.moneda}</td>
                  <td>{formatMoney(c.saldo_despues)} {c.moneda}</td>
                  <td>
                    {c.firmante_cargo}
                    {c.firmante_funcionario ? ` · ${c.firmante_funcionario}` : ""}
                  </td>
                  <td>
                    {c.estado === "VIGENTE"
                      ? "Vigente"
                      : `Anulada: ${c.motivo_anulacion ?? ""}`}
                  </td>
                  <td>
                    <Button
                      variant="secondary"
                      onClick={() =>
                        void descargarArchivo(
                          `/gobierno/presupuesto/ejercicios/${detalle.id}/certificaciones/${c.id}/documento`,
                          c.documento_nombre,
                        )
                      }
                    >
                      {`Descargar ${c.codigo}`}
                    </Button>
                    {c.estado === "VIGENTE" && puedeAnularVigentes ? (
                      <>
                        <TextInput
                          aria-label={`Motivo de anulación de ${c.codigo}`}
                          value={motivos[c.id] ?? ""}
                          onChange={(evento) =>
                            setMotivos((previos) => ({
                              ...previos,
                              [c.id]: evento.target.value,
                            }))
                          }
                        />
                        <AsyncButton
                          idleText={`Anular ${c.codigo}`}
                          onClick={async () => {
                            try {
                              await escribirBloque<Certificacion>(
                                `/certificaciones/${c.id}/anular`,
                                "POST",
                                { motivo: motivos[c.id] ?? "" },
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
