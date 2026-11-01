import { useId, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { DateInput } from "@/components/DateInput";
import { FormField } from "@/components/FormField";
import { apiFetch } from "@/api/client";
import { Acto, nombreDeActo } from "@/modules/gobierno/api";
import { DocumentSummary } from "@/modules/documentos/types";

export interface EmitirActoProps {
  acto: Acto;
  onConfirmar: (datos: {
    documento_acto_id: string;
    fecha_eficacia: string | null;
  }) => Promise<void>;
  onCancelar: () => void;
  erroresServidor: Record<string, string[]>;
}

export function EmitirActo(props: EmitirActoProps) {
  const { acto, onConfirmar, onCancelar, erroresServidor } = props;

  const idTitulo = useId();
  const idDocumento = useId();
  const idFechaEficacia = useId();

  const [documentoActoId, setDocumentoActoId] = useState("");
  const [fechaEficacia, setFechaEficacia] = useState(acto.fecha);
  const [erroresLocales, setErroresLocales] = useState<
    Record<string, string>
  >({});

  const documentosQuery = useQuery<DocumentSummary[]>({
    queryKey: ["documentos", "por-recurso", "GovernmentAct", acto.id],
    queryFn: () =>
      apiFetch<DocumentSummary[]>(
        `/documentos/por-recurso/GovernmentAct/${encodeURIComponent(acto.id)}`,
      ),
    retry: false,
  });

  const documentosValidos: DocumentSummary[] =
    documentosQuery.data?.filter(
      (documento: DocumentSummary) => documento.status === "ACTIVE",
    ) ?? [];

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
    if (!documentoActoId) {
      errores.documento_acto_id = "Seleccione el PDF firmado del acto";
    }
    if (
      acto.caracter === "INTERNO" &&
      fechaEficacia &&
      fechaEficacia < acto.fecha
    ) {
      errores.fecha_eficacia =
        "La eficacia no puede ser anterior a la fecha del acto";
    }
    setErroresLocales(errores);

    if (Object.keys(errores).length > 0) return;

    await onConfirmar({
      documento_acto_id: documentoActoId,
      fecha_eficacia:
        acto.caracter === "INTERNO" && fechaEficacia ? fechaEficacia : null,
    });
  };

  const textoFechaEficacia =
    acto.caracter === "GENERAL"
      ? "Quedará pendiente de publicación en Gaceta."
      : acto.caracter === "PARTICULAR"
        ? "Quedará pendiente de notificación."
        : null;

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
        Emitir {nombreDeActo(acto)}
      </h3>
      <p className="text-sm text-text-600">
        Se registra como emitido el acto ya firmado. Después no se podrán
        cambiar sus datos: solo corregir errores materiales.
      </p>

      <FormField
        label="PDF firmado del acto"
        htmlFor={idDocumento}
        required
        error={errorDe("documento_acto_id")}
      >
        <select
          id={idDocumento}
          value={documentoActoId}
          onChange={(evento) => {
            setDocumentoActoId(evento.target.value);
            limpiarError("documento_acto_id");
          }}
          aria-invalid={Boolean(errorDe("documento_acto_id"))}
          className={`w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600 ${
            errorDe("documento_acto_id")
              ? "border-danger-600"
              : "border-border-default"
          }`}
        >
          <option value="">Seleccione…</option>
          {documentosValidos.map((documento: DocumentSummary) => (
            <option key={documento.id} value={documento.id}>
              {documento.document_number
                ? `${documento.title} (${documento.document_number})`
                : documento.title}
            </option>
          ))}
        </select>
      </FormField>

      {documentosValidos.length === 0 && (
        <p className="text-sm text-text-600">
          Adjunte primero el documento en «Documentos del acto».
        </p>
      )}

      {acto.caracter === "INTERNO" ? (
        <FormField
          label="Fecha de eficacia"
          htmlFor={idFechaEficacia}
          error={errorDe("fecha_eficacia")}
          help="Por defecto, la fecha del acto. Puede ser futura."
        >
          <DateInput
            id={idFechaEficacia}
            value={fechaEficacia}
            min={acto.fecha}
            onChange={(evento) => {
              setFechaEficacia(evento.target.value);
              limpiarError("fecha_eficacia");
            }}
            invalid={Boolean(errorDe("fecha_eficacia"))}
          />
        </FormField>
      ) : (
        <p className="text-sm text-text-600">{textoFechaEficacia}</p>
      )}

      <div className="flex flex-wrap gap-3">
        <AsyncButton
          variant="primary"
          onClick={confirmar}
          disabled={documentosValidos.length === 0}
        >
          Emitir
        </AsyncButton>
        <Button variant="secondary" type="button" onClick={onCancelar}>
          Cancelar
        </Button>
      </div>
    </form>
  );
}
