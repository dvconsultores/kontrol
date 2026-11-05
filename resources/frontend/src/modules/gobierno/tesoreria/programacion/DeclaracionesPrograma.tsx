import { useState } from "react";
import { Link } from "react-router";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import { Button } from "@/components/Button";
import { AsyncButton } from "@/components/AsyncButton";
import { FormField } from "@/components/FormField";
import { CONSULTA_CAJA } from "@/modules/gobierno/api";
import { formatearFechaDeNegocio, hoyDeNegocio } from "@/lib/fecha-de-negocio";
import { formatMoney } from "@/lib/format";
import { formatearFecha } from "@/i18n";
import type {
  DeclaracionPrograma,
  OpcionesPrograma,
  ProgramaDetalle,
} from "@/modules/gobierno/api";

export interface DeclaracionesProgramaProps {
  programa: ProgramaDetalle;
  editable: boolean;
  onCambio: () => void;
}

type FormularioDeclarar = {
  cuenta_id: string;
  monto: string;
  fecha_corte: string;
  fundamento: string;
  errores: Record<string, string>;
};

const INPUT_CLASSES =
  "w-full max-w-md rounded-md border border-border bg-surface px-3 py-2 text-sm";

export function DeclaracionesPrograma({
  programa,
  editable,
  onCambio,
}: DeclaracionesProgramaProps): React.JSX.Element {
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const puedeEscribir =
    programa.estado === "BORRADOR" && editable && tiene("gobierno_caja:manage", "empresa");

  const [formularioAbierto, setFormularioAbierto] = useState(false);
  const [formulario, setFormulario] = useState<FormularioDeclarar>({
    cuenta_id: "",
    monto: "",
    fecha_corte: hoyDeNegocio(),
    fundamento: "",
    errores: {},
  });

  const opcionesQuery = useQuery({
    queryKey: [...CONSULTA_CAJA, "opciones", programa.id],
    queryFn: () =>
      apiFetch<OpcionesPrograma>(
        `/gobierno/tesoreria/programas/${programa.id}/opciones`,
      ),
    enabled: puedeEscribir,
  });

  const opciones = opcionesQuery.data;

  const abrirFormulario = () => {
    setFormulario({
      cuenta_id: "",
      monto: "",
      fecha_corte: hoyDeNegocio(),
      fundamento: "",
      errores: {},
    });
    setFormularioAbierto(true);
  };

  const cerrarFormulario = () => {
    setFormularioAbierto(false);
    setFormulario({
      cuenta_id: "",
      monto: "",
      fecha_corte: hoyDeNegocio(),
      fundamento: "",
      errores: {},
    });
  };

  const confirmarDeclarar = async () => {
    const errores: Record<string, string> = {};
    if (!formulario.cuenta_id) errores.cuenta_id = "Elija una cuenta";
    if (!formulario.monto || Number(formulario.monto) < 0)
      errores.monto = "Indique un monto válido";
    if (!formulario.fecha_corte) errores.fecha_corte = "Indique la fecha de corte";
    if (formulario.fundamento.trim().length < 10) {
      errores.fundamento = "El fundamento debe tener al menos 10 caracteres";
    }

    if (Object.keys(errores).length > 0) {
      setFormulario({ ...formulario, errores });
      return;
    }

    try {
      await apiFetch<DeclaracionPrograma>(
        `/gobierno/tesoreria/programas/${programa.id}/declaraciones`,
        {
          method: "POST",
          body: {
            cuenta_id: formulario.cuenta_id,
            monto: formulario.monto,
            fecha_corte: formulario.fecha_corte,
            fundamento: formulario.fundamento.trim(),
          },
          ifMatch: String(programa.version),
        },
      );
      cerrarFormulario();
      notify({ type: "success", title: "Declaración registrada" });
      onCambio();
    } catch (e) {
      const error = e as { code?: string; message?: string } | null;
      if (error && error.code === "GOV_CASH_DECLARATION_DUPLICATE") {
        setFormulario({
          ...formulario,
          errores: {
            ...formulario.errores,
            cuenta_id: "Ya existe una declaración para esta cuenta",
          },
        });
      } else if (error && error.code === "GOV_CASH_PROGRAM_INVALID") {
        setFormulario({
          ...formulario,
          errores: {
            ...formulario.errores,
            general: error.message || "El programa no es válido",
          },
        });
      } else if (error && error.code === "GOV_CASH_PROGRAM_STALE") {
        setFormulario({
          ...formulario,
          errores: {
            ...formulario.errores,
            general: "El programa fue modificado. Recargue la página.",
          },
        });
        onCambio();
      } else {
        notify({ type: "error", title: "No se pudo registrar la declaración" });
      }
    }
  };

  const confirmarQuitar = async (id: string) => {
    try {
      await apiFetch<void>(
        `/gobierno/tesoreria/programas/${programa.id}/declaraciones/${id}`,
        {
          method: "DELETE",
          ifMatch: String(programa.version),
        },
      );
      notify({ type: "success", title: "Declaración eliminada" });
      onCambio();
    } catch (e) {
      const error = e as { code?: string } | null;
      if (error && error.code === "GOV_CASH_PROGRAM_STALE") {
        setFormulario({
          ...formulario,
          errores: {
            ...formulario.errores,
            general: "El programa fue modificado. Recargue la página.",
          },
        });
        onCambio();
      } else {
        notify({ type: "error", title: "No se pudo eliminar la declaración" });
      }
    }
  };

  return (
    <section aria-labelledby="declaraciones-programa-titulo" className="space-y-4">
      <div>
        <h2 id="declaraciones-programa-titulo" className="text-lg font-semibold">
          Disponibilidad inicial declarada
        </h2>
        <p className="text-sm text-muted">
          Es lo que Tesorería declara bajo su responsabilidad; no es un saldo bancario consultado.
        </p>
      </div>

      {formulario.errores.general && (
        <div role="alert" className="bg-error-50 text-error-800 rounded-md p-3 text-sm">
          {formulario.errores.general}
        </div>
      )}

      <div
        role="region"
        aria-label="Tabla de declaraciones"
        tabIndex={0}
        className="overflow-x-auto"
      >
        <table className="w-full min-w-max border-collapse text-sm">
          <caption className="sr-only">
            Declaraciones de disponibilidad inicial del programa
          </caption>
          <thead>
            <tr>
              <th scope="col" className="border-b px-3 py-2 text-left">
                Cuenta
              </th>
              <th scope="col" className="border-b px-3 py-2 text-left">
                Banco
              </th>
              <th scope="col" className="border-b px-3 py-2 text-left">
                Monto
              </th>
              <th scope="col" className="border-b px-3 py-2 text-left">
                Fecha de corte
              </th>
              <th scope="col" className="border-b px-3 py-2 text-left">
                Fundamento
              </th>
              <th scope="col" className="border-b px-3 py-2 text-left">
                Declarado por
              </th>
              <th scope="col" className="border-b px-3 py-2 text-left">
                Cuándo
              </th>
              {puedeEscribir && (
                <th scope="col" className="border-b px-3 py-2 text-left">
                  Acción
                </th>
              )}
            </tr>
          </thead>
          <tbody>
            {programa.declaraciones.length === 0 ? (
              <tr>
                <td
                  colSpan={puedeEscribir ? 8 : 7}
                  className="px-3 py-4 text-center text-muted"
                >
                  Aún no hay declaraciones.
                </td>
              </tr>
            ) : (
              programa.declaraciones.map((d) => (
                <tr key={d.id} className="align-top">
                  <td className="border-b px-3 py-2">
                    {d.cuenta_codigo} · {d.cuenta_denominacion}
                  </td>
                  <td className="border-b px-3 py-2">{d.banco_nombre}</td>
                  <td className="border-b px-3 py-2">
                    {formatMoney(d.monto)}
                  </td>
                  <td className="border-b px-3 py-2">
                    {formatearFechaDeNegocio(d.fecha_corte)}
                  </td>
                  <td className="border-b px-3 py-2">
                    {d.fundamento}
                  </td>
                  <td className="border-b px-3 py-2">
                    {d.declarado_por ?? "—"}
                  </td>
                  <td className="border-b px-3 py-2">
                    {formatearFecha(d.declarado_en)}
                  </td>
                  {puedeEscribir && (
                    <td className="border-b px-3 py-2">
                      <Button
                        variant="secondary"
                        onClick={() => confirmarQuitar(d.id)}
                        aria-label={`Quitar declaración de ${d.cuenta_codigo}`}
                      >
                        Quitar
                      </Button>
                    </td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {puedeEscribir && !formularioAbierto && (
        <div>
          <Button onClick={abrirFormulario}>Declarar</Button>
        </div>
      )}

      {formularioAbierto && puedeEscribir && (
        <div className="rounded-md border border-border p-4 relative">
          <h3 className="mb-3 text-base font-semibold">Declarar disponibilidad</h3>
          <div className="space-y-4">
            {formulario.errores.general && (
              <div role="alert" className="bg-error-50 text-error-800 rounded-md p-3 text-sm">
                {formulario.errores.general}
              </div>
            )}
            {opciones && opciones.cuentas.length === 0 ? (
              <div role="alert" className="text-sm text-muted">
                No hay cuentas disponibles.{" "}
                <Link to="/gobierno/tesoreria/cuentas" className="text-primary hover:underline">
                  Administre cuentas
                </Link>
                .
              </div>
            ) : (
              <FormField
                label="Cuenta"
                required
                error={formulario.errores.cuenta_id}
              >
                <select
                  className={INPUT_CLASSES}
                  value={formulario.cuenta_id}
                  onChange={(e) =>
                    setFormulario({
                      ...formulario,
                      cuenta_id: e.target.value,
                      errores: { ...formulario.errores, cuenta_id: "" },
                    })
                  }
                >
                  <option value="">Seleccione una cuenta</option>
                  {(opciones?.cuentas ?? []).map((cuenta) => (
                    <option key={cuenta.id} value={cuenta.id}>
                      {cuenta.codigo} · {cuenta.denominacion}
                    </option>
                  ))}
                </select>
              </FormField>
            )}
            <FormField
              label="Monto"
              required
              error={formulario.errores.monto}
            >
              <input
                type="number"
                min="0"
                step="0.01"
                className={INPUT_CLASSES}
                value={formulario.monto}
                onChange={(e) =>
                  setFormulario({
                    ...formulario,
                    monto: e.target.value,
                    errores: { ...formulario.errores, monto: "" },
                  })
                }
              />
            </FormField>
            <FormField
              label="Fecha de corte"
              required
              error={formulario.errores.fecha_corte}
            >
              <input
                type="date"
                className={INPUT_CLASSES}
                value={formulario.fecha_corte}
                max={hoyDeNegocio()}
                onChange={(e) =>
                  setFormulario({
                    ...formulario,
                    fecha_corte: e.target.value,
                    errores: { ...formulario.errores, fecha_corte: "" },
                  })
                }
              />
            </FormField>
            <FormField
              label="Fundamento"
              required
              error={formulario.errores.fundamento}
              help="Entre 10 y 500 caracteres"
            >
              <textarea
                className={INPUT_CLASSES}
                value={formulario.fundamento}
                rows={3}
                maxLength={500}
                onChange={(e) =>
                  setFormulario({
                    ...formulario,
                    fundamento: e.target.value,
                    errores: { ...formulario.errores, fundamento: "" },
                  })
                }
              />
            </FormField>
            <div className="flex gap-2">
              <AsyncButton onClick={confirmarDeclarar}>Registrar declaración</AsyncButton>
              <Button variant="secondary" onClick={cerrarFormulario}>
                Cancelar
              </Button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
