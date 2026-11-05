import { useState } from "react";
import { Link } from "react-router";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { apiFetch } from "@/api/client";
import { Button } from "@/components/Button";
import { AsyncButton } from "@/components/AsyncButton";
import { FormField } from "@/components/FormField";
import {
  type AutorizadoCuenta,
  type CuentaDetalle,
  type CuentasOpciones,
  textoDeActo,
} from "@/modules/gobierno/api";
import { formatearFechaDeNegocio, hoyDeNegocio } from "@/lib/fecha-de-negocio";

export interface AutorizadosCuentaProps {
  cuenta: CuentaDetalle;
  opciones: CuentasOpciones | undefined;
  alCambiar: (cuenta: CuentaDetalle) => void;
  alFallar: (e: unknown) => void;
}

type FormularioFin = {
  autorizado: AutorizadoCuenta;
  acto_id: string;
  vigente_hasta: string;
  motivo: string;
  errores: Record<string, string>;
};

type FormularioAlta = {
  cargo_id: string;
  acto_id: string;
  vigente_desde: string;
  errores: Record<string, string>;
};

const INPUT_CLASSES =
  "w-full max-w-md rounded-md border border-border bg-surface px-3 py-2 text-sm";

export function AutorizadosCuenta({
  cuenta,
  opciones,
  alCambiar,
  alFallar,
}: AutorizadosCuentaProps): React.JSX.Element {
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const puedeGestionar = tiene("gobierno_cuentas:manage", "empresa");
  const abierta = cuenta.estado !== "CERRADA";

  const [finAbierto, setFinAbierto] = useState<FormularioFin | null>(null);
  const [altaAbierta, setAltaAbierta] = useState(false);
  const [alta, setAlta] = useState<FormularioAlta>({
    cargo_id: "",
    acto_id: "",
    vigente_desde: hoyDeNegocio(),
    errores: {},
  });

  const puedeRegistrarAlta =
    puedeGestionar && abierta && !cuenta.acto_sin_efecto && !finAbierto;

  const abrirFin = (autorizado: AutorizadoCuenta) => {
    setFinAbierto({
      autorizado,
      acto_id: "",
      vigente_hasta: hoyDeNegocio(),
      motivo: "",
      errores: {},
    });
    setAltaAbierta(false);
  };

  const cerrarFin = () => {
    setFinAbierto(null);
  };

  const abrirAlta = () => {
    setAltaAbierta(true);
    setFinAbierto(null);
    setAlta({
      cargo_id: "",
      acto_id: "",
      vigente_desde: hoyDeNegocio(),
      errores: {},
    });
  };

  const cerrarAlta = () => {
    setAltaAbierta(false);
    setAlta({
      cargo_id: "",
      acto_id: "",
      vigente_desde: hoyDeNegocio(),
      errores: {},
    });
  };

  const confirmarFin = async () => {
    if (!finAbierto) return;

    const errores: Record<string, string> = {};
    if (!finAbierto.acto_id) errores.acto_id = "Elija un acto";
    if (!finAbierto.vigente_hasta) errores.vigente_hasta = "Indique la fecha";
    if (finAbierto.motivo.trim().length < 10) {
      errores.motivo = "El motivo debe tener al menos 10 caracteres";
    }

    if (Object.keys(errores).length > 0) {
      setFinAbierto({ ...finAbierto, errores });
      return;
    }

    try {
      const respuesta = await apiFetch<CuentaDetalle>(
        `/gobierno/tesoreria/cuentas/${cuenta.id}/autorizados/${finAbierto.autorizado.id}/fin`,
        {
          method: "POST",
          body: {
            acto_id: finAbierto.acto_id,
            vigente_hasta: finAbierto.vigente_hasta,
            motivo: finAbierto.motivo.trim(),
          },
          ifMatch: String(cuenta.version),
        },
      );
      alCambiar(respuesta);
      setFinAbierto(null);
      notify({ type: "success", title: "Autorización terminada" });
    } catch (e) {
      alFallar(e);
    }
  };

  const confirmarAlta = async () => {
    const errores: Record<string, string> = {};
    if (!alta.cargo_id) errores.cargo_id = "Elija un cargo";
    if (!alta.acto_id) errores.acto_id = "Elija un acto";
    if (!alta.vigente_desde) errores.vigente_desde = "Indique la fecha";

    if (Object.keys(errores).length > 0) {
      setAlta({ ...alta, errores });
      return;
    }

    try {
      const respuesta = await apiFetch<CuentaDetalle>(
        `/gobierno/tesoreria/cuentas/${cuenta.id}/autorizados`,
        {
          method: "POST",
          body: {
            cargo_id: alta.cargo_id,
            acto_id: alta.acto_id,
            vigente_desde: alta.vigente_desde,
          },
          ifMatch: String(cuenta.version),
        },
      );
      alCambiar(respuesta);
      cerrarAlta();
      notify({ type: "success", title: "Autorización registrada" });
    } catch (e) {
      alFallar(e);
    }
  };

  return (
    <section aria-labelledby="autorizados-cuenta-titulo" className="space-y-4">
      <div>
        <h2 id="autorizados-cuenta-titulo" className="text-lg font-semibold">
          Cargos autorizados
        </h2>
        <p className="text-sm text-muted">
          Se autorizan cargos del ente, no personas. Cada cambio exige un acto
          y queda en la historia.
        </p>
      </div>

      {cuenta.autorizados.some(
        (a) => a.en_vigor && !a.cargo_vigente,
      ) && (
        <div className="space-y-2">
          {cuenta.autorizados
            .filter((a) => a.en_vigor && !a.cargo_vigente)
            .map((a) => (
              <div key={a.id} role="alert" className="text-sm text-danger">
                El cargo {a.cargo_codigo} ya no está vigente. Termine su
                autorización con el acto correspondiente.
              </div>
            ))}
        </div>
      )}

      <div
        role="region"
        aria-label="Tabla de cargos autorizados"
        tabIndex={0}
        className="overflow-x-auto"
      >
        <table className="w-full min-w-max border-collapse text-sm">
          <caption className="sr-only">
            Cargos autorizados de la cuenta
          </caption>
          <thead>
            <tr>
              <th scope="col" className="border-b px-3 py-2 text-left">
                Cargo
              </th>
              <th scope="col" className="border-b px-3 py-2 text-left">
                Unidad
              </th>
              <th scope="col" className="border-b px-3 py-2 text-left">
                Desde
              </th>
              <th scope="col" className="border-b px-3 py-2 text-left">
                Hasta
              </th>
              <th scope="col" className="border-b px-3 py-2 text-left">
                Acto de alta
              </th>
              <th scope="col" className="border-b px-3 py-2 text-left">
                Fin
              </th>
              <th scope="col" className="border-b px-3 py-2 text-left">
                Registró
              </th>
              {puedeGestionar && abierta && (
                <th scope="col" className="border-b px-3 py-2 text-left">
                  Acción
                </th>
              )}
            </tr>
          </thead>
          <tbody>
            {cuenta.autorizados.length === 0 ? (
              <tr>
                <td
                  colSpan={puedeGestionar && abierta ? 8 : 7}
                  className="px-3 py-4 text-center text-muted"
                >
                  Aún no hay cargos autorizados.
                </td>
              </tr>
            ) : (
              cuenta.autorizados.map((a) => (
                <tr key={a.id} className="align-top">
                  <td className="border-b px-3 py-2">
                    {a.cargo_codigo} · {a.cargo_denominacion}
                  </td>
                  <td className="border-b px-3 py-2">{a.cargo_unidad}</td>
                  <td className="border-b px-3 py-2">
                    {formatearFechaDeNegocio(a.vigente_desde)}
                  </td>
                  <td className="border-b px-3 py-2">
                    {a.vigente_hasta
                      ? formatearFechaDeNegocio(a.vigente_hasta)
                      : "En vigor"}
                  </td>
                  <td className="border-b px-3 py-2">
                    <Link
                      to={`/gobierno/actos/${a.acto_alta.id}`}
                      className="text-primary hover:underline"
                    >
                      {textoDeActo(a.acto_alta)}
                    </Link>
                  </td>
                  <td className="border-b px-3 py-2">
                    {a.acto_fin ? (
                      <div>
                        <Link
                          to={`/gobierno/actos/${a.acto_fin.id}`}
                          className="text-primary hover:underline"
                        >
                          {textoDeActo(a.acto_fin)}
                        </Link>
                        {a.motivo_fin ? <p className="mt-1 text-sm">{a.motivo_fin}</p> : null}
                      </div>
                    ) : a.motivo_fin ? (
                      <div>{a.motivo_fin}</div>
                    ) : (
                      <span className="text-muted">—</span>
                    )}
                  </td>
                  <td className="border-b px-3 py-2">
                    {a.registrada_por ?? "—"}
                  </td>
                  {puedeGestionar && abierta && (
                    <td className="border-b px-3 py-2">
                      {a.en_vigor && (
                        <Button
                          variant="secondary"
                          onClick={() => abrirFin(a)}
                          aria-label={`Terminar la autorización de ${a.cargo_codigo}`}
                        >
                          Terminar
                        </Button>
                      )}
                    </td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {finAbierto && (
        <div className="rounded-md border border-border p-4">
          <h3 className="mb-3 text-base font-semibold">
            Terminar la autorización de {finAbierto.autorizado.cargo_codigo}
          </h3>
          <div className="space-y-4">
            <FormField
              label="Acto de fin"
              required
              error={finAbierto.errores.acto_id}
            >
              <select
                className={INPUT_CLASSES}
                value={finAbierto.acto_id}
                onChange={(e) =>
                  setFinAbierto({
                    ...finAbierto,
                    acto_id: e.target.value,
                    errores: { ...finAbierto.errores, acto_id: "" },
                  })
                }
              >
                <option value="">Seleccione un acto</option>
                {(opciones?.actos ?? []).map((acto) => (
                  <option key={acto.id} value={acto.id}>
                    {textoDeActo(acto)}
                  </option>
                ))}
              </select>
            </FormField>
            <FormField
              label="Vigente hasta"
              required
              error={finAbierto.errores.vigente_hasta}
            >
              <input
                type="date"
                className={INPUT_CLASSES}
                value={finAbierto.vigente_hasta}
                max={hoyDeNegocio()}
                onChange={(e) =>
                  setFinAbierto({
                    ...finAbierto,
                    vigente_hasta: e.target.value,
                    errores: { ...finAbierto.errores, vigente_hasta: "" },
                  })
                }
              />
            </FormField>
            <FormField
              label="Motivo"
              required
              error={finAbierto.errores.motivo}
              help="Entre 10 y 500 caracteres"
            >
              <textarea
                className={INPUT_CLASSES}
                value={finAbierto.motivo}
                rows={3}
                maxLength={500}
                onChange={(e) =>
                  setFinAbierto({
                    ...finAbierto,
                    motivo: e.target.value,
                    errores: { ...finAbierto.errores, motivo: "" },
                  })
                }
              />
            </FormField>
            <div className="flex gap-2">
              <AsyncButton onClick={confirmarFin}>Confirmar fin</AsyncButton>
              <Button variant="secondary" onClick={cerrarFin}>
                Cancelar
              </Button>
            </div>
          </div>
        </div>
      )}

      {puedeRegistrarAlta && !altaAbierta && (
        <div>
          <Button onClick={abrirAlta}>Autorizar un cargo</Button>
        </div>
      )}

      {altaAbierta && puedeRegistrarAlta && (
        <div className="rounded-md border border-border p-4">
          <h3 className="mb-3 text-base font-semibold">Autorizar un cargo</h3>
          <div className="space-y-4">
            <FormField
              label="Cargo"
              required
              error={alta.errores.cargo_id}
              help="Solo cargos vigentes del ente"
            >
              <select
                className={INPUT_CLASSES}
                value={alta.cargo_id}
                onChange={(e) =>
                  setAlta({
                    ...alta,
                    cargo_id: e.target.value,
                    errores: { ...alta.errores, cargo_id: "" },
                  })
                }
              >
                <option value="">Seleccione un cargo</option>
                {(opciones?.cargos ?? []).map((cargo) => (
                  <option key={cargo.id} value={cargo.id}>
                    {cargo.codigo} · {cargo.denominacion} · {cargo.unidad}
                  </option>
                ))}
              </select>
            </FormField>
            <FormField
              label="Acto que lo autoriza"
              required
              error={alta.errores.acto_id}
            >
              <select
                className={INPUT_CLASSES}
                value={alta.acto_id}
                onChange={(e) =>
                  setAlta({
                    ...alta,
                    acto_id: e.target.value,
                    errores: { ...alta.errores, acto_id: "" },
                  })
                }
              >
                <option value="">Seleccione un acto</option>
                {(opciones?.actos ?? []).map((acto) => (
                  <option key={acto.id} value={acto.id}>
                    {textoDeActo(acto)}
                  </option>
                ))}
              </select>
            </FormField>
            <FormField
              label="Autorizado desde"
              required
              error={alta.errores.vigente_desde}
            >
              <input
                type="date"
                className={INPUT_CLASSES}
                value={alta.vigente_desde}
                max={hoyDeNegocio()}
                onChange={(e) =>
                  setAlta({
                    ...alta,
                    vigente_desde: e.target.value,
                    errores: { ...alta.errores, vigente_desde: "" },
                  })
                }
              />
            </FormField>
            <div className="flex gap-2">
              <AsyncButton onClick={confirmarAlta}>
                Registrar autorización
              </AsyncButton>
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
