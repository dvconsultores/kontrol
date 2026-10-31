import { useId, useState } from "react";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { DateInput } from "@/components/DateInput";
import { FormField } from "@/components/FormField";
import { Unidad } from "@/modules/gobierno/api";

export interface DesactivarUnidadProps {
  unidad: Unidad;
  ejercicio: number;
  onConfirmar: (fecha: string, motivo: string) => Promise<void>;
  onCancelar: () => void;
  erroresServidor: Record<string, string[]>;
}

export function DesactivarUnidad(props: DesactivarUnidadProps) {
  const { unidad, ejercicio, onConfirmar, onCancelar, erroresServidor } = props;

  const idTitulo = useId();
  const idFecha = useId();
  const idMotivo = useId();

  const [fecha, setFecha] = useState(`${ejercicio}-12-31`);
  const [motivo, setMotivo] = useState("");
  const [erroresLocales, setErroresLocales] = useState<
    Record<string, string>
  >({});

  const errorDe = (campo: string): string | undefined => {
    const local = erroresLocales[campo];
    if (local) return local;
    const servidor = erroresServidor[campo];
    return servidor && servidor.length > 0 ? servidor[0] : undefined;
  };

  const limpiarError = (campo: string) => {
    setErroresLocales((previos) => {
      if (!(campo in previos)) return previos;
      const copia = { ...previos };
      delete copia[campo];
      return copia;
    });
  };

  const confirmar = async () => {
    const errores: Record<string, string> = {};
    if (!fecha) errores.fecha = "Indique la fecha";
    if (motivo.trim().length < 5) {
      errores.motivo = "Indique el motivo (de 5 a 255 caracteres)";
    }
    setErroresLocales(errores);

    if (Object.keys(errores).length > 0) return;

    await onConfirmar(fecha, motivo.trim());
  };

  return (
    <form
      noValidate
      onSubmit={(evento) => {
        evento.preventDefault();
      }}
      aria-labelledby={idTitulo}
      className="grid grid-cols-1 gap-4"
    >
      <h2 id={idTitulo} className="text-lg font-semibold">
        Desactivar la unidad {unidad.codigo}
      </h2>
      <p className="text-sm text-text-600">
        La unidad dejará de estar vigente desde la fecha indicada; queda en el
        historial y no se borra.
      </p>

      <FormField
        label="Fecha de fin de vigencia"
        htmlFor={idFecha}
        required
        error={errorDe("fecha")}
      >
        <DateInput
          id={idFecha}
          value={fecha}
          min={unidad.vigente_desde ?? undefined}
          max={`${ejercicio}-12-31`}
          onChange={(evento) => {
            setFecha(evento.target.value);
            limpiarError("fecha");
          }}
          invalid={Boolean(errorDe("fecha"))}
        />
      </FormField>

      <FormField
        label="Motivo"
        htmlFor={idMotivo}
        required
        error={errorDe("motivo")}
      >
        <textarea
          id={idMotivo}
          value={motivo}
          maxLength={255}
          onChange={(evento) => {
            setMotivo(evento.target.value);
            limpiarError("motivo");
          }}
          aria-invalid={Boolean(errorDe("motivo"))}
          className={`min-h-24 w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600 ${
            errorDe("motivo") ? "border-danger-600" : "border-border-default"
          }`}
        />
      </FormField>

      <div className="flex flex-wrap gap-3">
        <AsyncButton variant="danger" onClick={confirmar}>
          Desactivar unidad
        </AsyncButton>
        <Button variant="secondary" type="button" onClick={onCancelar}>
          Cancelar
        </Button>
      </div>
    </form>
  );
}
