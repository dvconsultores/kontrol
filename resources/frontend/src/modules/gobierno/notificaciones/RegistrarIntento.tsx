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
  DIAS_PRENSA,
  IntentoEntrada,
  nombreDeActo,
  Notificacion,
} from "@/modules/gobierno/api";
import { DocumentSummary } from "@/modules/documentos/types";

export type ModoIntento = "ENTREGADA" | "FALLIDA" | "PRENSA";

interface RegistrarIntentoProps {
  notificacion: Notificacion;
  modo: ModoIntento;
  onConfirmar: (datos: IntentoEntrada) => Promise<void>;
  onCancelar: () => void;
  erroresServidor: Record<string, string[]>;
}

export function RegistrarIntento(props: RegistrarIntentoProps) {
  const { notificacion, modo, onConfirmar, onCancelar, erroresServidor } =
    props;

  const idTitulo = useId();
  const idFecha = useId();
  const idOficio = useId();
  const idConstancia = useId();
  const idReceptorNombre = useId();
  const idReceptorIdentificacion = useId();
  const idMotivoFallo = useId();
  const idDiario = useId();
  const idReferencia = useId();

  const [fecha, setFecha] = useState("");
  const [oficioId, setOficioId] = useState(
    notificacion.documento_oficio_id ?? "",
  );
  const [constanciaId, setConstanciaId] = useState("");
  const [receptorNombre, setReceptorNombre] = useState("");
  const [receptorIdentificacion, setReceptorIdentificacion] = useState("");
  const [motivoFallo, setMotivoFallo] = useState("");
  const [diario, setDiario] = useState("");
  const [referencia, setReferencia] = useState("");
  const [erroresLocales, setErroresLocales] = useState<
    Record<string, string>
  >({});

  const documentosQuery = useQuery<DocumentSummary[]>({
    queryKey: [
      "documentos",
      "por-recurso",
      "GovernmentNotification",
      notificacion.id,
    ],
    queryFn: () =>
      apiFetch<DocumentSummary[]>(
        `/documentos/por-recurso/GovernmentNotification/${encodeURIComponent(
          notificacion.id,
        )}`,
      ),
    retry: false,
  });

  const documentosValidos: DocumentSummary[] =
    documentosQuery.data?.filter(
      (documento: DocumentSummary) => documento.status === "ACTIVE",
    ) ?? [];

  const oficioFijado = notificacion.documento_oficio_id !== null;
  const documentosUsados = new Set(
    notificacion.intentos.map((intento) => intento.documento_id),
  );

  const opcionesConstancia = documentosValidos.filter(
    (documento: DocumentSummary) => {
      const oficioActual = oficioFijado
        ? notificacion.documento_oficio_id
        : oficioId;
      if (oficioActual && documento.id === oficioActual) {
        return false;
      }
      if (documentosUsados.has(documento.id)) {
        return false;
      }
      return true;
    },
  );

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

  const titulo =
    modo === "ENTREGADA"
      ? "Registrar la entrega personal"
      : modo === "FALLIDA"
        ? "Registrar un intento fallido"
        : "Registrar la publicación en prensa";
  const botonTexto =
    modo === "ENTREGADA"
      ? "Registrar entrega"
      : modo === "FALLIDA"
        ? "Registrar intento fallido"
        : "Registrar publicación";
  const tituloFecha =
    modo === "ENTREGADA"
      ? "Fecha de la entrega"
      : modo === "FALLIDA"
        ? "Fecha del intento"
        : "Fecha de la publicación";
  const rotuloConstancia =
    modo === "ENTREGADA"
      ? "Recibo firmado"
      : modo === "FALLIDA"
        ? "Constancia del intento"
        : "Ejemplar del diario";

  const fechaPrensa = fecha
    ? formatearFechaDeNegocio(sumarDiasDeNegocio(fecha, DIAS_PRENSA))
    : null;

  const faltanDocumentos = oficioFijado
    ? opcionesConstancia.length === 0
    : documentosValidos.length < 2;

  const confirmar = async () => {
    const errores: Record<string, string> = {};
    if (!fecha) {
      errores.fecha = "Indique la fecha";
    } else if (fecha < notificacion.acto.fecha) {
      errores.fecha = "La fecha no puede ser anterior a la fecha del acto";
    } else if (fecha > hoyDeNegocio()) {
      errores.fecha = "La fecha no puede ser posterior a hoy";
    }

    const oficioActual = oficioFijado
      ? (notificacion.documento_oficio_id as string)
      : oficioId;

    if (!oficioActual) {
      errores.documento_oficio_id = "Seleccione el oficio";
    }

    if (!constanciaId) {
      errores.documento_id = "Seleccione la constancia";
    }

    if (modo === "ENTREGADA") {
      if (
        receptorNombre.trim().length < 3 ||
        receptorNombre.trim().length > 200
      ) {
        errores.receptor_nombre = "Debe tener entre 3 y 200 caracteres";
      }
      if (
        receptorIdentificacion.trim().length < 5 ||
        receptorIdentificacion.trim().length > 20
      ) {
        errores.receptor_identificacion = "Debe tener entre 5 y 20 caracteres";
      }
    } else if (modo === "FALLIDA") {
      if (
        motivoFallo.trim().length < 5 ||
        motivoFallo.trim().length > 500
      ) {
        errores.motivo_fallo = "Debe tener entre 5 y 500 caracteres";
      }
    } else if (modo === "PRENSA") {
      if (diario.trim().length < 3 || diario.trim().length > 120) {
        errores.diario = "Debe tener entre 3 y 120 caracteres";
      }
      if (referencia.trim().length < 3 || referencia.trim().length > 120) {
        errores.referencia = "Debe tener entre 3 y 120 caracteres";
      }
    }
    setErroresLocales(errores);

    if (Object.keys(errores).length > 0) return;

    await onConfirmar({
      medio: modo === "PRENSA" ? "PRENSA" : "PERSONAL",
      resultado:
        modo === "ENTREGADA"
          ? "ENTREGADA"
          : modo === "FALLIDA"
            ? "FALLIDA"
            : "PUBLICADA",
      fecha,
      documento_oficio_id: oficioActual,
      documento_id: constanciaId,
      receptor_nombre:
        modo === "ENTREGADA" ? receptorNombre.trim() : null,
      receptor_identificacion:
        modo === "ENTREGADA" ? receptorIdentificacion.trim() : null,
      motivo_fallo: modo === "FALLIDA" ? motivoFallo.trim() : null,
      diario: modo === "PRENSA" ? diario.trim() : null,
      referencia: modo === "PRENSA" ? referencia.trim() : null,
    });
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
        {titulo} a {notificacion.nombre}
      </h3>
      <p className="text-sm text-text-600">
        {nombreDeActo(notificacion.acto)}
      </p>

      <FormField
        label={tituloFecha}
        htmlFor={idFecha}
        required
        error={errorDe("fecha")}
      >
        <DateInput
          id={idFecha}
          value={fecha}
          min={notificacion.acto.fecha}
          max={hoyDeNegocio()}
          onChange={(evento) => {
            setFecha(evento.target.value);
            limpiarError("fecha");
          }}
          invalid={Boolean(errorDe("fecha"))}
        />
      </FormField>

      {modo === "PRENSA" && fechaPrensa && (
        <p role="status" className="text-sm text-text-600">
          Se entenderá notificada el {fechaPrensa}.
        </p>
      )}

      <FormField
        label="Oficio de notificación"
        htmlFor={idOficio}
        required
        error={errorDe("documento_oficio_id")}
        help="Texto íntegro del acto con los recursos"
      >
        {oficioFijado ? (
          <>
            <select
              id={idOficio}
              value={notificacion.documento_oficio_id ?? ""}
              disabled
              aria-invalid={Boolean(errorDe("documento_oficio_id"))}
              className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 opacity-70"
            >
              {documentosValidos
                .filter(
                  (documento: DocumentSummary) =>
                    documento.id === notificacion.documento_oficio_id,
                )
                .map((documento: DocumentSummary) => (
                  <option key={documento.id} value={documento.id}>
                    {documento.document_number
                      ? `${documento.title} (${documento.document_number})`
                      : documento.title}
                  </option>
                ))}
            </select>
            <p className="mt-1 text-sm text-text-600">
              El oficio quedó fijado en el primer intento
            </p>
          </>
        ) : (
          <select
            id={idOficio}
            value={oficioId}
            onChange={(evento) => {
              const nuevoOficio = evento.target.value;
              setOficioId(nuevoOficio);
              limpiarError("documento_oficio_id");
              if (constanciaId === nuevoOficio) {
                setConstanciaId("");
              }
            }}
            aria-invalid={Boolean(errorDe("documento_oficio_id"))}
            className={`w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600 ${
              errorDe("documento_oficio_id")
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
        )}
      </FormField>

      <FormField
        label={rotuloConstancia}
        htmlFor={idConstancia}
        required
        error={errorDe("documento_id")}
      >
        <select
          id={idConstancia}
          value={constanciaId}
          onChange={(evento) => {
            setConstanciaId(evento.target.value);
            limpiarError("documento_id");
          }}
          aria-invalid={Boolean(errorDe("documento_id"))}
          className={`w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600 ${
            errorDe("documento_id")
              ? "border-danger-600"
              : "border-border-default"
          }`}
        >
          <option value="">Seleccione…</option>
          {opcionesConstancia.map((documento: DocumentSummary) => (
            <option key={documento.id} value={documento.id}>
              {documento.document_number
                ? `${documento.title} (${documento.document_number})`
                : documento.title}
            </option>
          ))}
        </select>
      </FormField>

      {faltanDocumentos && (
        <p className="text-sm text-text-600">
          Adjunte primero el oficio y la constancia en «Oficio y constancias».
        </p>
      )}

      {modo === "ENTREGADA" && (
        <>
          <FormField
            label="Recibido por"
            htmlFor={idReceptorNombre}
            required
            error={errorDe("receptor_nombre")}
            help="Quien firmó el recibo"
          >
            <TextInput
              id={idReceptorNombre}
              value={receptorNombre}
              maxLength={200}
              onChange={(evento) => {
                setReceptorNombre(evento.target.value);
                limpiarError("receptor_nombre");
              }}
              invalid={Boolean(errorDe("receptor_nombre"))}
            />
          </FormField>
          <FormField
            label="Cédula de quien recibe"
            htmlFor={idReceptorIdentificacion}
            required
            error={errorDe("receptor_identificacion")}
          >
            <TextInput
              id={idReceptorIdentificacion}
              value={receptorIdentificacion}
              maxLength={20}
              onChange={(evento) => {
                setReceptorIdentificacion(evento.target.value);
                limpiarError("receptor_identificacion");
              }}
              invalid={Boolean(errorDe("receptor_identificacion"))}
            />
          </FormField>
        </>
      )}

      {modo === "FALLIDA" && (
        <FormField
          label="Motivo del intento fallido"
          htmlFor={idMotivoFallo}
          required
          error={errorDe("motivo_fallo")}
          help="Ej.: domicilio cerrado, se negó a recibir"
        >
          <textarea
            id={idMotivoFallo}
            value={motivoFallo}
            maxLength={500}
            onChange={(evento) => {
              setMotivoFallo(evento.target.value);
              limpiarError("motivo_fallo");
            }}
            aria-invalid={Boolean(errorDe("motivo_fallo"))}
            className={`min-h-24 w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600 ${
              errorDe("motivo_fallo")
                ? "border-danger-600"
                : "border-border-default"
            }`}
          />
        </FormField>
      )}

      {modo === "PRENSA" && (
        <>
          <FormField
            label="Diario"
            htmlFor={idDiario}
            required
            error={errorDe("diario")}
            help="Diario de mayor circulación de la entidad (LOPA art. 76)"
          >
            <TextInput
              id={idDiario}
              value={diario}
              maxLength={120}
              onChange={(evento) => {
                setDiario(evento.target.value);
                limpiarError("diario");
              }}
              invalid={Boolean(errorDe("diario"))}
            />
          </FormField>
          <FormField
            label="Edición o referencia"
            htmlFor={idReferencia}
            required
            error={errorDe("referencia")}
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
        </>
      )}

      <div className="flex flex-wrap gap-3">
        <AsyncButton
          variant="primary"
          onClick={confirmar}
          disabled={faltanDocumentos}
        >
          {botonTexto}
        </AsyncButton>
        <Button variant="secondary" type="button" onClick={onCancelar}>
          Cancelar
        </Button>
      </div>
    </form>
  );
}
