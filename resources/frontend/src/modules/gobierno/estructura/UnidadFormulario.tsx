import { useId, useState } from "react";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { DateInput } from "@/components/DateInput";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import {
  ETIQUETA_TIPO_UNIDAD,
  EstadoEstructura,
  Unidad,
} from "@/modules/gobierno/api";

export type CambiosUnidad = Partial<
  Record<
    | "codigo"
    | "denominacion"
    | "tipo"
    | "unidad_superior_id"
    | "vigente_desde",
    string | null
  >
>;

export interface UnidadFormularioProps {
  modo: "crear" | "editar";
  estadoEstructura: EstadoEstructura;
  ejercicio: number;
  unidades: Unidad[];
  unidad?: Unidad;
  superiorInicial?: string | null;
  onGuardar: (cambios: CambiosUnidad, motivo: string | null) => Promise<void>;
  onCancelar: () => void;
  erroresServidor: Record<string, string[]>;
}

const REGEX_CODIGO = /^[A-Za-z0-9][A-Za-z0-9.-]{0,29}$/;

function esDescendiente(
  candidatoId: string,
  raizId: string,
  unidades: Unidad[],
): boolean {
  const porPadre = new Map<string | null, Unidad[]>();
  for (const unidad of unidades) {
    const lista = porPadre.get(unidad.unidad_superior_id) ?? [];
    lista.push(unidad);
    porPadre.set(unidad.unidad_superior_id, lista);
  }

  const pila = [raizId];
  const visitados = new Set<string>();
  while (pila.length > 0) {
    const actual = pila.pop();
    if (!actual || visitados.has(actual)) continue;
    visitados.add(actual);
    if (actual === candidatoId) return true;
    const hijos = porPadre.get(actual) ?? [];
    for (const hijo of hijos) pila.push(hijo.id);
  }
  return false;
}

export function UnidadFormulario(props: UnidadFormularioProps) {
  const {
    modo,
    estadoEstructura,
    ejercicio,
    unidades,
    unidad,
    superiorInicial,
    onGuardar,
    onCancelar,
    erroresServidor,
  } = props;

  const esVigente = estadoEstructura === "VIGENTE";
  const esEditar = modo === "editar";

  const idTitulo = useId();
  const idCodigo = useId();
  const idDenominacion = useId();
  const idTipo = useId();
  const idSuperior = useId();
  const idVigenteDesde = useId();
  const idMotivo = useId();

  const [codigo, setCodigo] = useState(unidad?.codigo ?? "");
  const [denominacion, setDenominacion] = useState(unidad?.denominacion ?? "");
  const [tipo, setTipo] = useState(unidad?.tipo ?? "");
  const [superior, setSuperior] = useState(
    unidad ? (unidad.unidad_superior_id ?? "") : (superiorInicial ?? ""),
  );
  const [vigenteDesde, setVigenteDesde] = useState(() => {
    if (unidad) return unidad.vigente_desde ?? "";
    if (estadoEstructura === "BORRADOR") return `${ejercicio}-01-01`;
    return "";
  });
  const [motivo, setMotivo] = useState("");

  const [erroresLocales, setErroresLocales] = useState<
    Record<string, string>
  >({});
  const [aviso, setAviso] = useState<string | null>(null);

  const unidadesElegibles = unidades
    .filter(
      (candidata) =>
        candidata.estado === "ACTIVA" &&
        candidata.id !== unidad?.id &&
        !(unidad && esDescendiente(candidata.id, unidad.id, unidades)),
    )
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

    if (!REGEX_CODIGO.test(codigo)) {
      errores.codigo =
        "Código inválido: hasta 30 letras, números, punto o guion";
    }
    if (denominacion.trim().length < 3) {
      errores.denominacion = "Indique la denominación (3 a 200 caracteres)";
    }
    if (!tipo) {
      errores.tipo = "Elija el tipo de unidad";
    }
    if (esVigente && motivo.trim().length < 5) {
      errores.motivo = "Indique el motivo (de 5 a 255 caracteres)";
    }

    setErroresLocales(errores);
    return Object.keys(errores).length === 0;
  };

  const construirCambios = (): CambiosUnidad | null => {
    if (!esEditar) {
      const cambios: CambiosUnidad = {
        codigo: codigo.toUpperCase(),
        denominacion: denominacion.trim(),
        tipo,
        unidad_superior_id: superior === "" ? null : superior,
      };
      if (vigenteDesde) cambios.vigente_desde = vigenteDesde;
      return cambios;
    }

    if (!unidad) return null;

    const cambios: CambiosUnidad = {};
    if (codigo !== unidad.codigo && !esVigente) cambios.codigo = codigo;
    if (denominacion.trim() !== unidad.denominacion) {
      cambios.denominacion = denominacion.trim();
    }
    if (tipo !== unidad.tipo) cambios.tipo = tipo;
    const superiorActual = unidad.unidad_superior_id ?? "";
    if (superior !== superiorActual) {
      cambios.unidad_superior_id = superior === "" ? null : superior;
    }
    if (!esVigente && vigenteDesde !== (unidad.vigente_desde ?? "")) {
      cambios.vigente_desde = vigenteDesde;
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

    await onGuardar(cambios, esVigente ? motivo.trim() : null);
  };

  const titulo =
    modo === "crear" ? "Nueva unidad" : `Editar la unidad ${unidad?.codigo ?? ""}`;

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
        help="Letras, números, punto y guion; sin espacios"
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
        label="Tipo de unidad"
        htmlFor={idTipo}
        required
        error={errorDe("tipo")}
      >
        <select
          id={idTipo}
          value={tipo}
          onChange={(evento) => {
            setTipo(evento.target.value);
            limpiarError("tipo");
          }}
          aria-invalid={Boolean(errorDe("tipo"))}
          className={`h-10 w-full rounded-md border bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600 ${
            errorDe("tipo") ? "border-danger-600" : "border-border-default"
          }`}
        >
          <option value="">Seleccione…</option>
          {Object.entries(ETIQUETA_TIPO_UNIDAD).map(([valor, etiqueta]) => (
            <option key={valor} value={valor}>
              {etiqueta}
            </option>
          ))}
        </select>
      </FormField>

      <FormField
        label="Depende de"
        htmlFor={idSuperior}
        error={errorDe("unidad_superior_id")}
      >
        <select
          id={idSuperior}
          value={superior}
          onChange={(evento) => {
            setSuperior(evento.target.value);
            limpiarError("unidad_superior_id");
          }}
          aria-invalid={Boolean(errorDe("unidad_superior_id"))}
          className={`h-10 w-full rounded-md border bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600 ${
            errorDe("unidad_superior_id")
              ? "border-danger-600"
              : "border-border-default"
          }`}
        >
          <option value="">El ente (sin unidad superior)</option>
          {unidadesElegibles.map((candidata) => (
            <option key={candidata.id} value={candidata.id}>
              {candidata.codigo} · {candidata.denominacion}
            </option>
          ))}
        </select>
      </FormField>

      <FormField
        label="Vigente desde"
        htmlFor={idVigenteDesde}
        error={errorDe("vigente_desde")}
        help={
          esVigente ? "En una estructura vigente el inicio no se cambia" : undefined
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

      {esVigente && (
        <FormField
          label="Motivo del cambio"
          htmlFor={idMotivo}
          required
          error={errorDe("motivo")}
          help="De 5 a 255 caracteres; queda en el historial y en la auditoría"
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
