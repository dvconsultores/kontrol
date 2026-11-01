import { useId, useState } from "react";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { FormField } from "@/components/FormField";
import { MoneyInput } from "@/components/MoneyInput";
import { TextInput } from "@/components/TextInput";
import {
  AccionCompetencia,
  Competencia,
  ETIQUETA_ACCION,
  ETIQUETA_MATERIA,
  ETIQUETA_MONEDA,
  MateriaCompetencia,
  MonedaDeLimite,
  TipoDeLimite,
} from "@/modules/gobierno/api";
import { isZeroDecimal, toDecimalString } from "@/lib/decimal";

export interface DatosCompetencia {
  accion: AccionCompetencia;
  materia: MateriaCompetencia;
  tipo_limite: TipoDeLimite;
  monto: string | null;
  moneda: MonedaDeLimite | null;
  fundamento: string | null;
}

export interface CompetenciaFormularioProps {
  modo: "agregar" | "cambiar";
  cargoCodigo: string;
  cargoVigente: boolean;
  competencia?: Competencia;
  competenciasExistentes: Competencia[];
  onGuardar: (datos: DatosCompetencia, motivo: string | null) => Promise<void>;
  onCancelar: () => void;
  erroresServidor: Record<string, string[]>;
}

export function CompetenciaFormulario(props: CompetenciaFormularioProps) {
  const {
    modo,
    cargoCodigo,
    cargoVigente,
    competencia,
    competenciasExistentes,
    onGuardar,
    onCancelar,
    erroresServidor,
  } = props;

  const esAgregar = modo === "agregar";


  const idTitulo = useId();
  const idAccion = useId();
  const idMateria = useId();
  const idSinLimite = useId();
  const idMonto = useId();
  const idMontoCampo = useId();
  const idMoneda = useId();
  const idFundamento = useId();
  const idMotivo = useId();

  const [accion, setAccion] = useState<AccionCompetencia | "">(
    competencia?.accion ?? "",
  );
  const [materia, setMateria] = useState<MateriaCompetencia | "">(
    competencia?.materia ?? "",
  );
  const [tipoLimite, setTipoLimite] = useState<TipoDeLimite>(
    competencia?.tipo_limite ?? "SIN_LIMITE",
  );
  const [monto, setMonto] = useState(competencia?.monto ?? "");
  const [moneda, setMoneda] = useState<MonedaDeLimite | "">(
    competencia?.moneda ?? "",
  );
  const [fundamento, setFundamento] = useState(competencia?.fundamento ?? "");
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

  const validar = (): boolean => {
    const errores: Record<string, string> = {};

    if (esAgregar) {
      if (!accion) errores.accion = "Seleccione la acción";
      if (!materia) {
        errores.materia = "Seleccione la materia";
      } else if (
        accion &&
        competenciasExistentes.some(
          (existente) =>
            existente.accion === accion && existente.materia === materia,
        )
      ) {
        errores.materia = "El cargo ya tiene esa competencia";
      }
    }

    if (tipoLimite === "MONTO") {
      const texto = toDecimalString(monto);
      if (texto === null) {
        errores.monto = "Indique un monto válido, con hasta dos decimales";
      } else if (isZeroDecimal(texto)) {
        errores.monto = "El monto debe ser mayor que cero";
      } else if (texto.split(".")[0].length > 16) {
        errores.monto = "El monto admite como máximo 16 dígitos enteros";
      }
      if (!moneda) errores.moneda = "Seleccione la moneda";
    }

    if (fundamento.trim().length > 255) {
      errores.fundamento = "El fundamento admite como máximo 255 caracteres";
    }

    if (cargoVigente) {
      const largo = motivo.trim().length;
      if (largo < 5 || largo > 255) {
        errores.motivo = "Indique el motivo (de 5 a 255 caracteres)";
      }
    }

    setErroresLocales(errores);
    return Object.keys(errores).length === 0;
  };

  const construirDatos = (): DatosCompetencia | null => {
    if (esAgregar) {
      if (!accion || !materia) return null;
      return {
        accion,
        materia,
        tipo_limite: tipoLimite,
        monto: tipoLimite === "MONTO" ? toDecimalString(monto) : null,
        moneda: tipoLimite === "MONTO" ? (moneda as MonedaDeLimite) : null,
        fundamento: fundamento.trim() === "" ? null : fundamento.trim(),
      };
    }

    if (!competencia) return null;
    return {
      accion: competencia.accion,
      materia: competencia.materia,
      tipo_limite: tipoLimite,
      monto: tipoLimite === "MONTO" ? toDecimalString(monto) : null,
      moneda: tipoLimite === "MONTO" ? (moneda as MonedaDeLimite) : null,
      fundamento: fundamento.trim() === "" ? null : fundamento.trim(),
    };
  };

  const guardar = async () => {
    if (!validar()) return;

    const datos = construirDatos();
    if (!datos) {
      setErroresLocales({ accion: "Seleccione la acción", materia: "Seleccione la materia" });
      return;
    }

    await onGuardar(datos, cargoVigente ? motivo.trim() : null);
  };

  const etiquetaAccion = competencia ? ETIQUETA_ACCION[competencia.accion] : "";
  const etiquetaMateria = competencia
    ? ETIQUETA_MATERIA[competencia.materia]
    : "";

  const titulo = esAgregar
    ? `Agregar competencia al cargo ${cargoCodigo}`
    : `Cambiar el límite de ${etiquetaAccion} · ${etiquetaMateria}`;

  return (
    <form
      noValidate
      onSubmit={(evento) => {
        evento.preventDefault();
      }}
      aria-labelledby={idTitulo}
      className="grid grid-cols-1 gap-4 md:grid-cols-2"
    >
      <h2 id={idTitulo} className="md:col-span-2 text-lg font-semibold">
        {titulo}
      </h2>

      {esAgregar ? (
        <FormField
          label="Acción"
          htmlFor={idAccion}
          required
          error={errorDe("accion")}
        >
          <select
            id={idAccion}
            value={accion}
            onChange={(evento) => {
              setAccion(evento.target.value as AccionCompetencia | "");
              limpiarError("accion");
              limpiarError("materia");
            }}
            aria-invalid={Boolean(errorDe("accion"))}
            className={`h-10 w-full rounded-md border bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600 ${
              errorDe("accion") ? "border-danger-600" : "border-border-default"
            }`}
          >
            <option value="">Seleccione la acción</option>
            {Object.keys(ETIQUETA_ACCION).map((valor) => (
              <option key={valor} value={valor}>
                {ETIQUETA_ACCION[valor as AccionCompetencia]}
              </option>
            ))}
          </select>
        </FormField>
      ) : (
        <div className="md:col-span-2">
          <p className="text-sm text-text-500">
            {etiquetaAccion} · {etiquetaMateria}
          </p>
        </div>
      )}

      {esAgregar && (
        <FormField
          label="Materia"
          htmlFor={idMateria}
          required
          error={errorDe("materia")}
        >
          <select
            id={idMateria}
            value={materia}
            onChange={(evento) => {
              setMateria(evento.target.value as MateriaCompetencia | "");
              limpiarError("materia");
            }}
            aria-invalid={Boolean(errorDe("materia"))}
            className={`h-10 w-full rounded-md border bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600 ${
              errorDe("materia") ? "border-danger-600" : "border-border-default"
            }`}
          >
            <option value="">Seleccione la materia</option>
            {Object.keys(ETIQUETA_MATERIA).map((valor) => (
              <option key={valor} value={valor}>
                {ETIQUETA_MATERIA[valor as MateriaCompetencia]}
              </option>
            ))}
          </select>
        </FormField>
      )}

      <fieldset className="md:col-span-2 grid grid-cols-1 gap-3">
        <legend className="text-sm font-medium text-text-700">
          Límite de firma/aprobación
        </legend>
        <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
          <label className="flex items-center gap-2 text-sm text-text-900">
            <input
              id={idSinLimite}
              type="radio"
              name="tipoLimite"
              value="SIN_LIMITE"
              checked={tipoLimite === "SIN_LIMITE"}
              onChange={() => {
                setTipoLimite("SIN_LIMITE");
                limpiarError("tipo_limite");
              }}
            />
            Sin límite
          </label>
          <label className="flex items-center gap-2 text-sm text-text-900">
            <input
              id={idMonto}
              type="radio"
              name="tipoLimite"
              value="MONTO"
              checked={tipoLimite === "MONTO"}
              onChange={() => {
                setTipoLimite("MONTO");
                limpiarError("tipo_limite");
              }}
            />
            Hasta un monto por operación
          </label>
        </div>
        {errorDe("tipo_limite") && (
          <p className="text-sm text-danger-600">{errorDe("tipo_limite")}</p>
        )}
      </fieldset>

      {tipoLimite === "MONTO" && (
        <>
          <FormField
            label="Monto máximo por operación"
            htmlFor={idMontoCampo}
            required
            error={errorDe("monto")}
            help="Use coma o punto para los decimales; sin separador de miles. Ej.: 50000,00"
          >
            <MoneyInput
              id={idMontoCampo}
              value={monto}
              onChange={(evento) => {
                setMonto(evento.target.value);
                limpiarError("monto");
              }}
              currency={moneda ? moneda : undefined}
              invalid={Boolean(errorDe("monto"))}
            />
          </FormField>

          <FormField
            label="Moneda"
            htmlFor={idMoneda}
            required
            error={errorDe("moneda")}
          >
            <select
              id={idMoneda}
              value={moneda}
              onChange={(evento) => {
                setMoneda(evento.target.value as MonedaDeLimite | "");
                limpiarError("moneda");
              }}
              aria-invalid={Boolean(errorDe("moneda"))}
              className={`h-10 w-full rounded-md border bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600 ${
                errorDe("moneda") ? "border-danger-600" : "border-border-default"
              }`}
            >
              <option value="">Seleccione la moneda</option>
              {Object.keys(ETIQUETA_MONEDA).map((valor) => (
                <option key={valor} value={valor}>
                  {ETIQUETA_MONEDA[valor as MonedaDeLimite]}
                </option>
              ))}
            </select>
          </FormField>
        </>
      )}

      <FormField
        label="Fundamento"
        htmlFor={idFundamento}
        error={errorDe("fundamento")}
        help="Ej.: Reglamento interno, art. 12"
        className="md:col-span-2"
      >
        <TextInput
          id={idFundamento}
          value={fundamento}
          onChange={(evento) => {
            setFundamento(evento.target.value);
            limpiarError("fundamento");
          }}
          invalid={Boolean(errorDe("fundamento"))}
        />
      </FormField>

      {cargoVigente && (
        <FormField
          label="Motivo del cambio"
          htmlFor={idMotivo}
          required
          error={errorDe("motivo")}
          help="Queda en el historial y en la auditoría"
          className="md:col-span-2"
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
      )}

      <div className="md:col-span-2 flex flex-wrap gap-3">
        <AsyncButton onClick={guardar}>Guardar</AsyncButton>
        <Button variant="secondary" type="button" onClick={onCancelar}>
          Cancelar
        </Button>
      </div>
    </form>
  );
}
