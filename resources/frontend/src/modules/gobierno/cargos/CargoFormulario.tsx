import { useId, useState } from "react";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { DateInput } from "@/components/DateInput";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { Cargo, Unidad } from "@/modules/gobierno/api";

export type CambiosCargo = Partial<
  Record<"codigo" | "denominacion" | "unidad_id" | "vigente_desde", string>
>;

export interface CargoFormularioProps {
  modo: "crear" | "editar";
  ejercicio: number;
  unidades: Unidad[];
  cargo?: Cargo;
  unidadInicial?: string | null;
  onGuardar: (cambios: CambiosCargo, motivo: string | null) => Promise<void>;
  onCancelar: () => void;
  erroresServidor: Record<string, string[]>;
}

const REGEX_CODIGO = /^[A-Za-z0-9][A-Za-z0-9.-]{0,29}$/;

export function CargoFormulario(props: CargoFormularioProps) {
  const {
    modo,
    ejercicio,
    unidades,
    cargo,
    unidadInicial,
    onGuardar,
    onCancelar,
    erroresServidor,
  } = props;

  const esEditar = modo === "editar";
  const esVigente = cargo?.estado === "VIGENTE";

  const idTitulo = useId();
  const idCodigo = useId();
  const idDenominacion = useId();
  const idUnidad = useId();
  const idVigenteDesde = useId();
  const idMotivo = useId();

  const [codigo, setCodigo] = useState(cargo?.codigo ?? "");
  const [denominacion, setDenominacion] = useState(cargo?.denominacion ?? "");
  const [unidad, setUnidad] = useState(
    cargo ? cargo.unidad_id : (unidadInicial ?? ""),
  );
  const [vigenteDesde, setVigenteDesde] = useState(() => {
    if (cargo) return cargo.vigente_desde ?? "";
    return `${ejercicio}-01-01`;
  });
  const [motivo, setMotivo] = useState("");

  const [erroresLocales, setErroresLocales] = useState<
    Record<string, string>
  >({});
  const [aviso, setAviso] = useState<string | null>(null);

  const unidadesElegibles = unidades
    .filter((candidata) => candidata.estado === "ACTIVA")
    .sort((a, b) => a.codigo.localeCompare(b.codigo));

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
    setAviso(null);
  };

  const validar = (): boolean => {
    const errores: Record<string, string> = {};

    if (!esVigente && !REGEX_CODIGO.test(codigo.trim())) {
      errores.codigo = "Use de 1 a 30 letras, números, punto o guion";
    }
    const denominacionNormalizada = denominacion.trim();
    if (
      denominacionNormalizada.length < 3 ||
      denominacionNormalizada.length > 200
    ) {
      errores.denominacion =
        "La denominación debe tener entre 3 y 200 caracteres";
    }
    if (!unidad) {
      errores.unidad_id = "Seleccione la unidad";
    }
    if (!esVigente) {
      if (
        vigenteDesde < `${ejercicio}-01-01` ||
        vigenteDesde > `${ejercicio}-12-31`
      ) {
        errores.vigente_desde = "Debe estar dentro del ejercicio";
      }
    }
    if (esEditar && esVigente && motivo.trim().length < 5) {
      errores.motivo = "Indique el motivo (de 5 a 255 caracteres)";
    }

    setErroresLocales(errores);
    return Object.keys(errores).length === 0;
  };

  const construirCambios = (): CambiosCargo | null => {
    if (!esEditar) {
      return {
        codigo: codigo.trim().toUpperCase(),
        denominacion: denominacion.trim(),
        unidad_id: unidad,
        vigente_desde: vigenteDesde,
      };
    }

    if (!cargo) return null;

    const cambios: CambiosCargo = {};
    if (denominacion.trim() !== cargo.denominacion) {
      cambios.denominacion = denominacion.trim();
    }
    if (unidad !== cargo.unidad_id) {
      cambios.unidad_id = unidad;
    }
    if (!esVigente) {
      if (codigo.trim().toUpperCase() !== cargo.codigo) {
        cambios.codigo = codigo.trim().toUpperCase();
      }
      if (vigenteDesde !== cargo.vigente_desde) {
        cambios.vigente_desde = vigenteDesde;
      }
    }

    return Object.keys(cambios).length > 0 ? cambios : null;
  };

  const guardar = async () => {
    setAviso(null);

    if (!validar()) return;

    const cambios = construirCambios();
    if (!cambios) {
      setAviso("No hay cambios que guardar");
      return;
    }

    await onGuardar(cambios, esEditar && esVigente ? motivo.trim() : null);
  };

  const titulo =
    modo === "crear" ? "Registrar cargo" : `Editar cargo ${cargo?.codigo ?? ""}`;

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

      <FormField
        label="Código"
        htmlFor={idCodigo}
        required
        error={errorDe("codigo")}
        help="Ej.: DIR-ADM"
      >
        <TextInput
          id={idCodigo}
          value={codigo}
          onChange={(evento) => {
            setCodigo(evento.target.value);
            limpiarError("codigo");
          }}
          disabled={esEditar && esVigente}
          invalid={Boolean(errorDe("codigo"))}
        />
      </FormField>

      <FormField
        label="Denominación"
        htmlFor={idDenominacion}
        required
        error={errorDe("denominacion")}
      >
        <TextInput
          id={idDenominacion}
          value={denominacion}
          onChange={(evento) => {
            setDenominacion(evento.target.value);
            limpiarError("denominacion");
          }}
          invalid={Boolean(errorDe("denominacion"))}
        />
      </FormField>

      <FormField
        label="Unidad"
        htmlFor={idUnidad}
        required
        error={errorDe("unidad_id")}
      >
        <select
          id={idUnidad}
          value={unidad}
          onChange={(evento) => {
            setUnidad(evento.target.value);
            limpiarError("unidad_id");
          }}
          aria-invalid={Boolean(errorDe("unidad_id"))}
          className={`h-10 w-full rounded-md border bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600 ${
            errorDe("unidad_id") ? "border-danger-600" : "border-border-default"
          }`}
        >
          <option value="">Seleccione la unidad</option>
          {unidadesElegibles.map((candidata) => (
            <option key={candidata.id} value={candidata.id}>
              {candidata.codigo} — {candidata.denominacion}
            </option>
          ))}
        </select>
      </FormField>

      <FormField
        label="Vigente desde"
        htmlFor={idVigenteDesde}
        required
        error={errorDe("vigente_desde")}
        help={
          esEditar && esVigente
            ? "En un cargo vigente el código y el inicio de vigencia no se cambian."
            : undefined
        }
      >
        <DateInput
          id={idVigenteDesde}
          value={vigenteDesde}
          min={`${ejercicio}-01-01`}
          max={`${ejercicio}-12-31`}
          disabled={esEditar && esVigente}
          onChange={(evento) => {
            setVigenteDesde(evento.target.value);
            limpiarError("vigente_desde");
          }}
          invalid={Boolean(errorDe("vigente_desde"))}
        />
      </FormField>

      {esEditar && esVigente && (
        <FormField
          label="Motivo del cambio"
          htmlFor={idMotivo}
          required
          error={errorDe("motivo")}
          help="Queda en el historial y en la auditoría"
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

      {aviso && (
        <p role="status" className="md:col-span-2 text-sm text-warning-700">
          {aviso}
        </p>
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
