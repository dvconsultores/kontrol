import { useId, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { DateInput } from "@/components/DateInput";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { apiFetch } from "@/api/client";
import {
  formatearFechaDeNegocio,
  hoyDeNegocio,
  sumarDiasDeNegocio,
} from "@/lib/fecha-de-negocio";
import {
  Acto,
  ETIQUETA_MEDIO,
  MEDIOS_POR_CARACTER,
  MedioEficacia,
  nombreDeActo,
} from "@/modules/gobierno/api";
import { DocumentSummary } from "@/modules/documentos/types";

export interface RegistrarEficaciaProps {
  acto: Acto;
  onConfirmar: (datos: {
    medio: MedioEficacia;
    referencia: string | null;
    fecha: string;
    documento_eficacia_id: string;
    fecha_eficacia: string | null;
  }) => Promise<void>;
  onCancelar: () => void;
  erroresServidor: Record<string, string[]>;
}



export function RegistrarEficacia(props: RegistrarEficaciaProps) {
  const { acto, onConfirmar, onCancelar, erroresServidor } = props;

  const idTitulo = useId();
  const idMedio = useId();
  const idReferencia = useId();
  const idFecha = useId();
  const idSoporte = useId();
  const idFechaEficacia = useId();

  const medios = MEDIOS_POR_CARACTER[acto.caracter];
  const [medio, setMedio] = useState<MedioEficacia | "">(
    medios.length === 1 ? medios[0] : "",
  );
  const [referencia, setReferencia] = useState("");
  const [fecha, setFecha] = useState("");
  const [documentoEficaciaId, setDocumentoEficaciaId] = useState("");
  const [fechaEficacia, setFechaEficacia] = useState("");
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
      (documento: DocumentSummary) =>
        documento.status === "ACTIVE" &&
        documento.id !== acto.documento_acto_id,
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

  const fechaBaseEficacia =
    medio && fecha
      ? medio === "PRENSA"
        ? sumarDiasDeNegocio(fecha, 15)
        : fecha
      : null;

  const confirmar = async () => {
    const errores: Record<string, string> = {};
    if (!medio) {
      errores.medio = "Seleccione el medio";
    }
    if (medio === "GACETA" || medio === "PRENSA") {
      if (referencia.trim().length < 3 || referencia.trim().length > 120) {
        errores.referencia = "Indique la referencia (de 3 a 120 caracteres)";
      }
    }
    if (!fecha) {
      errores.fecha = "Indique la fecha";
    } else if (fecha < acto.fecha) {
      errores.fecha = "La fecha no puede ser anterior a la fecha del acto";
    } else if (fecha > hoyDeNegocio()) {
      errores.fecha = "La fecha no puede ser posterior a hoy";
    }
    if (!documentoEficaciaId) {
      errores.documento_eficacia_id = "Seleccione el soporte";
    }
    if (
      fechaEficacia &&
      fechaBaseEficacia &&
      fechaEficacia < fechaBaseEficacia
    ) {
      errores.fecha_eficacia = `No puede ser anterior a ${formatearFechaDeNegocio(
        fechaBaseEficacia,
      )}`;
    }
    setErroresLocales(errores);

    if (Object.keys(errores).length > 0) return;

    await onConfirmar({
      medio: medio as MedioEficacia,
      referencia:
        medio === "GACETA" || medio === "PRENSA" ? referencia.trim() : null,
      fecha,
      documento_eficacia_id: documentoEficaciaId,
      fecha_eficacia: fechaEficacia || null,
    });
  };

  const titulo =
    acto.caracter === "GENERAL"
      ? "Registrar la publicación"
      : "Registrar la notificación";

  const tituloFecha =
    medio === "PERSONAL"
      ? "Fecha de la notificación"
      : "Fecha de la publicación";

  const fechaEficaciaMostrada = fechaEficacia || fechaBaseEficacia;
  const textoEficacia = fechaEficaciaMostrada
    ? `Será eficaz desde ${formatearFechaDeNegocio(fechaEficaciaMostrada)}`
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
        {titulo} de {nombreDeActo(acto)}
      </h3>

      <fieldset id={idMedio} className="grid grid-cols-1 gap-2">
        <legend className="text-sm font-medium text-text-900">Medio</legend>
        {medios.map((medioValor: MedioEficacia) => (
          <label
            key={medioValor}
            className="flex items-center gap-2 text-sm text-text-900"
          >
            <input
              type="radio"
              name="medio"
              value={medioValor}
              checked={medio === medioValor}
              onChange={() => {
                setMedio(medioValor);
                limpiarError("medio");
                limpiarError("referencia");
                limpiarError("fecha_eficacia");
              }}
              aria-invalid={Boolean(errorDe("medio"))}
            />
            {ETIQUETA_MEDIO[medioValor]}
          </label>
        ))}
        {errorDe("medio") && (
          <p className="text-sm text-danger-600">{errorDe("medio")}</p>
        )}
      </fieldset>

      {(medio === "GACETA" || medio === "PRENSA") && (
        <FormField
          label="Referencia de la publicación"
          htmlFor={idReferencia}
          required
          error={errorDe("referencia")}
          help="Gaceta Oficial Nº… o nombre del diario"
        >
          <TextInput
            id={idReferencia}
            value={referencia}
            maxLength={120}
            onChange={(evento) => {
              setReferencia(evento.target.value);
              limpiarError("referencia");
            }}
            invalid={Boolean(errorDe("referencia"))}
          />
        </FormField>
      )}

      <FormField
        label={tituloFecha}
        htmlFor={idFecha}
        required
        error={errorDe("fecha")}
      >
        <DateInput
          id={idFecha}
          value={fecha}
          min={acto.fecha}
          max={hoyDeNegocio()}
          onChange={(evento) => {
            setFecha(evento.target.value);
            limpiarError("fecha");
            limpiarError("fecha_eficacia");
          }}
          invalid={Boolean(errorDe("fecha"))}
        />
      </FormField>

      <FormField
        label="Soporte"
        htmlFor={idSoporte}
        required
        error={errorDe("documento_eficacia_id")}
        help="Gaceta, recibo firmado o ejemplar del diario"
      >
        <select
          id={idSoporte}
          value={documentoEficaciaId}
          onChange={(evento) => {
            setDocumentoEficaciaId(evento.target.value);
            limpiarError("documento_eficacia_id");
          }}
          aria-invalid={Boolean(errorDe("documento_eficacia_id"))}
          className={`w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600 ${
            errorDe("documento_eficacia_id")
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

      <FormField
        label="Fecha de eficacia (opcional)"
        htmlFor={idFechaEficacia}
        error={errorDe("fecha_eficacia")}
      >
        <DateInput
          id={idFechaEficacia}
          value={fechaEficacia}
          min={fechaBaseEficacia ?? undefined}
          onChange={(evento) => {
            setFechaEficacia(evento.target.value);
            limpiarError("fecha_eficacia");
          }}
          invalid={Boolean(errorDe("fecha_eficacia"))}
        />
      </FormField>

      {textoEficacia && (
        <p className="text-sm text-text-600">{textoEficacia}</p>
      )}

      <div className="flex flex-wrap gap-3">
        <AsyncButton
          variant="primary"
          onClick={confirmar}
          disabled={documentosValidos.length === 0}
        >
          Registrar
        </AsyncButton>
        <Button variant="secondary" type="button" onClick={onCancelar}>
          Cancelar
        </Button>
      </div>
    </form>
  );
}
