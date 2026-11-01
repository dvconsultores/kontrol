import { useId, useState } from "react";
import { apiFetch } from "@/api/client";
import { useQuery } from "@tanstack/react-query";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { FormField } from "@/components/FormField";
import {
  Acto,
  ActoResumen,
  CONSULTA_ACTOS,
  ListaActos,
  nombreDeActo,
} from "@/modules/gobierno/api";
import { formatearFechaDeNegocio, hoyDeNegocio } from "@/lib/fecha-de-negocio";

export interface ReferenciarActoProps {
  acto: Acto;
  modo: "revocar" | "anular";
  onConfirmar: (datos: {
    acto_id_referencia: string;
    motivo: string;
  }) => Promise<void>;
  onCancelar: () => void;
  erroresServidor: Record<string, string[]>;
}

export function ReferenciarActo(props: ReferenciarActoProps) {
  const { acto, modo, onConfirmar, onCancelar, erroresServidor } = props;

  const idTitulo = useId();
  const idAnio = useId();
  const idActoReferencia = useId();
  const idMotivo = useId();

  const anioActual = Number(hoyDeNegocio().slice(0, 4));
  const [anio, setAnio] = useState(anioActual);
  const [actoIdReferencia, setActoIdReferencia] = useState("");
  const [motivo, setMotivo] = useState("");
  const [aviso, setAviso] = useState<string | null>(null);
  const [erroresLocales, setErroresLocales] = useState<
    Record<string, string>
  >({});

  const { data, isLoading, isError } = useQuery({
    queryKey: [...CONSULTA_ACTOS, "lista", anio],
    queryFn: () => apiFetch<ListaActos>(`/gobierno/actos?anio=${anio}`),
    retry: false,
  });

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

  const opcionesReferencia: ActoResumen[] =
    data?.items.filter((item) => {
      const estadoValido =
        item.estado === "EMITIDO" || item.estado === "EFICAZ";
      const distinto = item.id !== acto.id;
      const fechaMayorOIgual = item.fecha >= acto.fecha;
      return estadoValido && distinto && fechaMayorOIgual;
    }) ?? [];

  const accion =
    modo === "revocar"
      ? {
          titulo: "Registrar la revocación",
          explicacion:
            "Indique el acto que lo revoca (LOPA art. 82). Si ese acto no está en el registro, regístrelo y emítalo primero.",
          boton: "Registrar revocación",
        }
      : {
          titulo: "Registrar la nulidad",
          explicacion:
            "Indique el acto que declara su nulidad (LOPA art. 83). Si ese acto no está en el registro, regístrelo y emítalo primero.",
          boton: "Registrar nulidad",
        };

  const confirmar = async () => {
    setAviso(null);
    const errores: Record<string, string> = {};

    if (!actoIdReferencia) {
      errores.acto_id_referencia = "Seleccione un acto de referencia";
    }
    const motivoTexto = motivo.trim();
    if (motivoTexto.length < 5 || motivoTexto.length > 255) {
      errores.motivo = "Indique el motivo (de 5 a 255 caracteres)";
    }
    setErroresLocales(errores);

    if (Object.keys(errores).length > 0) return;

    await onConfirmar({
      acto_id_referencia: actoIdReferencia,
      motivo: motivoTexto,
    });
  };

  const claseSelect = (campo: string) =>
    `w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600 ${
      errorDe(campo) ? "border-danger-600" : "border-border-default"
    }`;

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
        {accion.titulo} de {nombreDeActo(acto)}
      </h3>
      <p className="text-sm text-text-600">{accion.explicacion}</p>

      <FormField
        label={
          modo === "revocar"
            ? "Año del acto que revoca"
            : "Año del acto que declara la nulidad"
        }
        htmlFor={idAnio}
      >
        <select
          id={idAnio}
          value={anio}
          onChange={(evento) => {
            setAnio(Number(evento.target.value));
            setActoIdReferencia("");
            limpiarError("acto_id_referencia");
            setAviso(null);
          }}
          className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
        >
          {Array.from({ length: 6 }, (_, indice) => anioActual - indice).map(
            (anioOpcion) => (
              <option key={anioOpcion} value={anioOpcion}>
                {anioOpcion}
              </option>
            ),
          )}
        </select>
      </FormField>

      <FormField
        label="Acto de referencia"
        htmlFor={idActoReferencia}
        required
        error={errorDe("acto_id_referencia")}
      >
        <select
          id={idActoReferencia}
          value={actoIdReferencia}
          disabled={isLoading || isError}
          onChange={(evento) => {
            setActoIdReferencia(evento.target.value);
            limpiarError("acto_id_referencia");
            setAviso(null);
          }}
          aria-invalid={Boolean(errorDe("acto_id_referencia"))}
          className={claseSelect("acto_id_referencia")}
        >
          <option value="">Seleccione un acto</option>
          {opcionesReferencia.map((item) => (
            <option key={item.id} value={item.id}>
              {nombreDeActo(item)} — {formatearFechaDeNegocio(item.fecha)} —{" "}
              {item.asunto}
            </option>
          ))}
        </select>
      </FormField>

      {isLoading ? (
        <p className="text-sm text-text-600">Cargando actos…</p>
      ) : null}
      {isError ? (
        <p className="text-sm text-text-600">No se pudieron cargar los actos</p>
      ) : null}
      {!isLoading && !isError && opcionesReferencia.length === 0 ? (
        <p className="text-sm text-text-600">
          No hay actos emitidos que puedan servir de referencia en ese año.
        </p>
      ) : null}

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
            setAviso(null);
          }}
          aria-invalid={Boolean(errorDe("motivo"))}
          className={`min-h-24 w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600 ${
            errorDe("motivo") ? "border-danger-600" : "border-border-default"
          }`}
        />
      </FormField>

      {aviso ? (
        <p role="status" className="text-sm text-text-600">
          {aviso}
        </p>
      ) : null}

      <div className="flex flex-wrap gap-3">
        <AsyncButton
          variant="danger"
          disabled={isLoading || isError || opcionesReferencia.length === 0}
          onClick={confirmar}
        >
          {accion.boton}
        </AsyncButton>
        <Button variant="secondary" type="button" onClick={onCancelar}>
          Cancelar
        </Button>
      </div>
    </form>
  );
}
