import { useId, useState } from "react";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { FormField } from "@/components/FormField";
import {
  Competencia,
  describirLimite,
  ETIQUETA_ACCION,
  ETIQUETA_MATERIA,
} from "@/modules/gobierno/api";

export interface RetirarCompetenciaProps {
  competencia: Competencia;
  cargoVigente: boolean;
  onConfirmar: (motivo: string | null) => Promise<void>;
  onCancelar: () => void;
  erroresServidor: Record<string, string[]>;
}

export function RetirarCompetencia(props: RetirarCompetenciaProps) {
  const {
    competencia,
    cargoVigente,
    onConfirmar,
    onCancelar,
    erroresServidor,
  } = props;

  const idTitulo = useId();
  const idMotivo = useId();

  const [motivo, setMotivo] = useState("");
  const [erroresLocales, setErroresLocales] = useState<
    Record<string, string>
  >({});

  const limpiarError = () => {
    setErroresLocales((previos) =>
      "motivo" in previos ? {} : previos,
    );
  };

  const errorDe = (campo: string): string | undefined => {
    const local = erroresLocales[campo];
    if (local) return local;
    const servidor = erroresServidor[campo];
    return servidor && servidor.length > 0 ? servidor[0] : undefined;
  };

  const validar = (): boolean => {
    if (cargoVigente) {
      const largo = motivo.trim().length;
      if (largo < 5 || largo > 255) {
        setErroresLocales({
          motivo: "Indique el motivo (de 5 a 255 caracteres)",
        });
        return false;
      }
    }
    setErroresLocales({});
    return true;
  };

  const confirmar = async () => {
    if (!validar()) return;
    await onConfirmar(cargoVigente ? motivo.trim() : null);
  };

  const titulo = `Retirar la competencia ${ETIQUETA_ACCION[competencia.accion]} · ${ETIQUETA_MATERIA[competencia.materia]}`;

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
        {titulo}
      </h2>

      <p className="text-sm text-text-900">{describirLimite(competencia)}</p>

      <p className="text-sm text-text-500">
        El cargo deja de tener esta competencia; el historial la conserva.
      </p>

      {cargoVigente && (
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
              limpiarError();
            }}
            aria-invalid={Boolean(errorDe("motivo"))}
            className={`min-h-24 w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600 ${
              errorDe("motivo") ? "border-danger-600" : "border-border-default"
            }`}
          />
        </FormField>
      )}

      <div className="flex flex-wrap gap-3">
        <AsyncButton onClick={confirmar}>Retirar competencia</AsyncButton>
        <Button variant="secondary" type="button" onClick={onCancelar}>
          Cancelar
        </Button>
      </div>
    </form>
  );
}
