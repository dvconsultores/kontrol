import { useState } from "react";
import { Link } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { apiFetch, ApiError } from "@/api/client";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { FormField } from "@/components/FormField";
import { formatMoney } from "@/lib/format";
import {
  CONSULTA_CAJA,
  ETIQUETAS_TIPO_RUBRO,
  NOMBRES_DE_MES,
  type LineaPrograma,
  type OpcionesPrograma,
  type ProgramaDetalle,
} from "@/modules/gobierno/api";

export interface LineasProgramaProps {
  programa: ProgramaDetalle;
  editable: boolean;
  onCambio: () => void;
}

type FormularioNueva = {
  rubro_id: string;
  mes: string;
  monto: string;
  errores: Record<string, string>;
};

type FormularioCambio = {
  linea: LineaPrograma;
  monto: string;
  errores: Record<string, string>;
};

const INPUT_CLASSES =
  "w-full max-w-md rounded-md border border-border bg-surface px-3 py-2 text-sm";

export function LineasPrograma({
  programa,
  editable,
  onCambio,
}: LineasProgramaProps): React.JSX.Element {
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const puedeGestionar = tiene("gobierno_caja:manage", "empresa");
  const puedeEscribir = editable && puedeGestionar;

  const opcionesQuery = useQuery<OpcionesPrograma>({
    queryKey: [...CONSULTA_CAJA, "opciones", programa.id],
    queryFn: () =>
      apiFetch<OpcionesPrograma>(
        `/gobierno/tesoreria/programas/${programa.id}/opciones`,
      ),
    enabled: puedeEscribir,
  });

  const [nueva, setNueva] = useState<FormularioNueva>({
    rubro_id: "",
    mes: "",
    monto: "",
    errores: {},
  });
  const [cambio, setCambio] = useState<FormularioCambio | null>(null);
  const [altaAbierta, setAltaAbierta] = useState(false);
  const [alerta, setAlerta] = useState<string | null>(null);

  const opciones = opcionesQuery.data;
  const hayRubrosActivos = (opciones?.rubros ?? []).length > 0;

  const abrirAlta = () => {
    setAltaAbierta(true);
    setCambio(null);
    setAlerta(null);
    setNueva({
      rubro_id: "",
      mes: "",
      monto: "",
      errores: {},
    });
  };

  const cerrarAlta = () => {
    setAltaAbierta(false);
    setAlerta(null);
    setNueva({
      rubro_id: "",
      mes: "",
      monto: "",
      errores: {},
    });
  };

  const abrirCambio = (linea: LineaPrograma) => {
    setCambio({
      linea,
      monto: String(linea.monto),
      errores: {},
    });
    setAltaAbierta(false);
    setAlerta(null);
  };

  const cerrarCambio = () => {
    setCambio(null);
    setAlerta(null);
  };

  const manejarError = (e: unknown) => {
    if (e instanceof ApiError) {
      if (e.code === "GOV_CASH_PROGRAM_STALE") {
        setAlerta("El programa fue modificado por otra persona");
        onCambio();
        return;
      }
      if (
        e.code === "GOV_CASH_LINE_DUPLICATE" ||
        e.code === "GOV_CASH_PROGRAM_PAST_MONTH" ||
        e.code === "GOV_CASH_PROGRAM_INVALID"
      ) {
        setAlerta(e.message);
        return;
      }
    }
    setAlerta("No se pudo guardar la línea");
  };

  const confirmarNueva = async () => {
    const errores: Record<string, string> = {};
    if (!nueva.rubro_id) errores.rubro_id = "Elija un rubro";
    if (!nueva.mes) errores.mes = "Elija un mes";
    if (!nueva.monto) {
      errores.monto = "Indique el monto";
    } else {
      const valor = Number(nueva.monto);
      if (Number.isNaN(valor) || valor <= 0) errores.monto = "Monto mayor que 0";
      if (!/^\d+(\.\d{1,2})?$/.test(nueva.monto)) errores.monto = "Máximo 2 decimales";
    }

    if (Object.keys(errores).length > 0) {
      setNueva({ ...nueva, errores });
      return;
    }

    try {
      await apiFetch<ProgramaDetalle>(
        `/gobierno/tesoreria/programas/${programa.id}/lineas`,
        {
          method: "POST",
          body: {
            rubro_id: nueva.rubro_id,
            mes: Number(nueva.mes),
            monto: nueva.monto,
          },
          ifMatch: String(programa.version),
        },
      );
      cerrarAlta();
      notify({ type: "success", title: "Línea añadida" });
      onCambio();
    } catch (e) {
      manejarError(e);
    }
  };

  const confirmarCambio = async () => {
    if (!cambio) return;

    const errores: Record<string, string> = {};
    if (!cambio.monto) {
      errores.monto = "Indique el monto";
    } else {
      const valor = Number(cambio.monto);
      if (Number.isNaN(valor) || valor <= 0) errores.monto = "Monto mayor que 0";
      if (!/^\d+(\.\d{1,2})?$/.test(cambio.monto)) errores.monto = "Máximo 2 decimales";
    }

    if (Object.keys(errores).length > 0) {
      setCambio({ ...cambio, errores });
      return;
    }

    try {
      await apiFetch<ProgramaDetalle>(
        `/gobierno/tesoreria/programas/${programa.id}/lineas/${cambio.linea.id}`,
        {
          method: "PATCH",
          body: { monto: cambio.monto },
          ifMatch: String(programa.version),
        },
      );
      setCambio(null);
      notify({ type: "success", title: "Línea actualizada" });
      onCambio();
    } catch (e) {
      manejarError(e);
    }
  };

  const confirmarQuitar = async (linea: LineaPrograma) => {
    try {
      await apiFetch<ProgramaDetalle>(
        `/gobierno/tesoreria/programas/${programa.id}/lineas/${linea.id}`,
        {
          method: "DELETE",
          ifMatch: String(programa.version),
        },
      );
      notify({ type: "success", title: "Línea eliminada" });
      onCambio();
    } catch (e) {
      manejarError(e);
    }
  };

  return (
    <section aria-labelledby="lineas-programa-titulo" className="space-y-4">
      <div>
        <h2 id="lineas-programa-titulo" className="text-lg font-semibold">
          Líneas programadas
        </h2>
        <p className="text-sm text-muted">
          Distribución mensual por rubro de la versión mostrada.
        </p>
      </div>

      {alerta && (
        <div role="alert" className="text-sm text-danger-600">
          {alerta}
        </div>
      )}

      {!hayRubrosActivos && puedeEscribir && (
        <div role="alert" className="text-sm text-danger-600">
          No hay rubros activos.{" "}
          <Link
            to="/gobierno/tesoreria/rubros"
            className="text-primary hover:underline"
          >
            Gestione los rubros
          </Link>
          .
        </div>
      )}

      <div
        role="region"
        aria-label="Tabla de líneas"
        tabIndex={0}
        className="overflow-x-auto"
      >
        <table className="w-full min-w-max border-collapse text-sm">
          <caption className="sr-only">
            Líneas programadas del programa
          </caption>
          <thead>
            <tr>
              <th scope="col" className="border-b px-3 py-2 text-left">
                Mes
              </th>
              <th scope="col" className="border-b px-3 py-2 text-left">
                Rubro
              </th>
              <th scope="col" className="border-b px-3 py-2 text-left">
                Tipo
              </th>
              <th scope="col" className="border-b px-3 py-2 text-right">
                Monto
              </th>
              {puedeEscribir && (
                <th scope="col" className="border-b px-3 py-2 text-left">
                  Acción
                </th>
              )}
            </tr>
          </thead>
          <tbody>
            {programa.lineas.length === 0 ? (
              <tr>
                <td
                  colSpan={puedeEscribir ? 5 : 4}
                  className="px-3 py-4 text-center text-muted"
                >
                  Aún no hay líneas programadas.
                </td>
              </tr>
            ) : (
              programa.lineas.map((linea) => (
                <tr key={linea.id} className="align-top">
                  <td className="border-b px-3 py-2">
                    {NOMBRES_DE_MES[linea.mes - 1]}
                  </td>
                  <td className="border-b px-3 py-2">
                    {linea.rubro_codigo} · {linea.rubro_nombre}
                  </td>
                  <td className="border-b px-3 py-2">
                    {ETIQUETAS_TIPO_RUBRO[linea.tipo]}
                  </td>
                  <td className="border-b px-3 py-2 text-right">
                    {formatMoney(linea.monto)}
                  </td>
                  {puedeEscribir && (
                    <td className="border-b px-3 py-2">
                      {cambio?.linea.id === linea.id ? (
                        <div className="relative space-y-2">
                          <FormField
                            label="Monto"
                            required
                            error={cambio.errores.monto}
                          >
                            <input
                              type="number"
                              step="0.01"
                              min="0.01"
                              className={INPUT_CLASSES}
                              value={cambio.monto}
                              onChange={(e) =>
                                setCambio({
                                  ...cambio,
                                  monto: e.target.value,
                                  errores: { ...cambio.errores, monto: "" },
                                })
                              }
                            />
                          </FormField>
                          <div className="flex gap-2">
                            <AsyncButton onClick={confirmarCambio}>
                              Guardar
                            </AsyncButton>
                            <Button variant="secondary" onClick={cerrarCambio}>
                              Cancelar
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <div className="flex gap-2">
                          <Button
                            variant="secondary"
                            onClick={() => abrirCambio(linea)}
                            aria-label={`Cambiar monto de la línea de ${NOMBRES_DE_MES[linea.mes - 1]}`}
                          >
                            Cambiar
                          </Button>
                          <Button
                            variant="secondary"
                            onClick={() => confirmarQuitar(linea)}
                            aria-label={`Quitar línea de ${NOMBRES_DE_MES[linea.mes - 1]}`}
                          >
                            Quitar
                          </Button>
                        </div>
                      )}
                    </td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {puedeEscribir && hayRubrosActivos && !altaAbierta && (
        <div>
          <Button onClick={abrirAlta}>Añadir línea</Button>
        </div>
      )}

      {puedeEscribir && hayRubrosActivos && altaAbierta && (
        <div className="rounded-md border border-border p-4">
          <h3 className="mb-3 text-base font-semibold">Añadir línea</h3>
          <div className="space-y-4">
            <FormField
              label="Rubro"
              required
              error={nueva.errores.rubro_id}
            >
              <select
                className={INPUT_CLASSES}
                value={nueva.rubro_id}
                onChange={(e) =>
                  setNueva({
                    ...nueva,
                    rubro_id: e.target.value,
                    errores: { ...nueva.errores, rubro_id: "" },
                  })
                }
              >
                <option value="">Seleccione un rubro</option>
                {(opciones?.rubros ?? []).map((rubro) => (
                  <option key={rubro.id} value={rubro.id}>
                    {rubro.codigo} · {rubro.nombre}
                  </option>
                ))}
              </select>
            </FormField>
            <FormField label="Mes" required error={nueva.errores.mes}>
              <select
                className={INPUT_CLASSES}
                value={nueva.mes}
                onChange={(e) =>
                  setNueva({
                    ...nueva,
                    mes: e.target.value,
                    errores: { ...nueva.errores, mes: "" },
                  })
                }
              >
                <option value="">Seleccione un mes</option>
                {Array.from(
                  { length: 12 - programa.mes_inicial + 1 },
                  (_, i) => programa.mes_inicial + i,
                ).map((mes) => (
                  <option key={mes} value={mes}>
                    {NOMBRES_DE_MES[mes - 1]}
                  </option>
                ))}
              </select>
            </FormField>
            <FormField
              label="Monto"
              required
              error={nueva.errores.monto}
              help="Monto mayor que 0, hasta 2 decimales"
            >
              <input
                type="number"
                step="0.01"
                min="0.01"
                className={INPUT_CLASSES}
                value={nueva.monto}
                onChange={(e) =>
                  setNueva({
                    ...nueva,
                    monto: e.target.value,
                    errores: { ...nueva.errores, monto: "" },
                  })
                }
              />
            </FormField>
            <div className="flex gap-2">
              <AsyncButton onClick={confirmarNueva}>Añadir línea</AsyncButton>
              <Button variant="secondary" onClick={cerrarAlta}>
                Cancelar
              </Button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
