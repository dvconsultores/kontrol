import { useId, useState } from "react";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { FormField } from "@/components/FormField";
import { Notificacion } from "@/modules/gobierno/api";

interface AnularNotificacionProps {
  notificacion: Notificacion;
  onConfirmar: (motivo: string) => Promise<void>;
  onCancelar: () => void;
  erroresServidor: Record<string, string[]>;
}

export function AnularNotificacion(props: AnularNotificacionProps) {
  const { notificacion, onConfirmar, onCancelar, erroresServidor } = props;

  const idTitulo = useId();
  const idMotivo = useId();

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
    if (motivo.trim().length < 5 || motivo.trim().length > 255) {
      errores.motivo = "Debe tener entre 5 y 255 caracteres";
    }
    setErroresLocales(errores);

    if (Object.keys(errores).length > 0) return;

    await onConfirmar(motivo.trim());
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
      <h3 id={idTitulo} className="text-lg font-semibold">
        Anular la notificación de {notificacion.nombre}
      </h3>

      <FormField
        label="Motivo de la anulación"
        htmlFor={idMotivo}
        required
        error={errorDe("motivo")}
        help="Queda en el historial"
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

      <p className="text-sm text-text-600">
        La notificación anulada deja de contar para la eficacia del acto.
      </p>

      <div className="flex flex-wrap gap-3">
        <AsyncButton variant="danger" onClick={confirmar}>
          Anular notificación
        </AsyncButton>
        <Button variant="secondary" type="button" onClick={onCancelar}>
          Cancelar
        </Button>
      </div>
    </form>
  );
}
