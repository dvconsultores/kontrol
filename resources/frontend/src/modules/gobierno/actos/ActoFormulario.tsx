import { useQuery } from "@tanstack/react-query";
import { useId, useState } from "react";
import { apiFetch } from "@/api/client";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { DateInput } from "@/components/DateInput";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { hoyDeNegocio } from "@/lib/fecha-de-negocio";
import {
  AccionCompetencia,
  Acto,
  CaracterActo,
  CONSULTA_ACTOS,
  ETIQUETA_ACCION,
  ETIQUETA_CARACTER,
  ETIQUETA_MATERIA,
  ETIQUETA_TIPO_ACTO,
  ETIQUETA_TITULARIDAD,
  ListaAutoridades,
  MateriaCompetencia,
  TipoActo,
  Titularidad,
} from "@/modules/gobierno/api";

export type DatosActo = {
  tipo?: TipoActo;
  denominacion_tipo?: string | null;
  numero?: string;
  fecha?: string;
  lugar?: string;
  cargo_id?: string;
  competencia?: { accion: AccionCompetencia; materia: MateriaCompetencia };
  fundamento_competencia?: string;
  funcionario?: string;
  titularidad?: Titularidad;
  delegacion_numero?: string | null;
  delegacion_fecha?: string | null;
  caracter?: CaracterActo;
  simple_tramite?: boolean;
  destinatario?: string | null;
  asunto?: string;
  hechos?: string | null;
  fundamentos?: string | null;
  decision?: string | null;
};

export interface ActoFormularioProps {
  modo: "crear" | "editar";
  acto?: Acto;
  onGuardar: (datos: DatosActo) => Promise<void>;
  onCancelar: () => void;
  erroresServidor: Record<string, string[]>;
}

const CLAVES_ESCALARES = [
  "tipo",
  "denominacion_tipo",
  "numero",
  "fecha",
  "lugar",
  "cargo_id",
  "fundamento_competencia",
  "funcionario",
  "titularidad",
  "delegacion_numero",
  "delegacion_fecha",
  "caracter",
  "simple_tramite",
  "destinatario",
  "asunto",
  "hechos",
  "fundamentos",
  "decision",
] as const satisfies readonly (keyof DatosActo)[];

const stringVacioANulo = (texto: string): string | null =>
  texto.trim() === "" ? null : texto.trim();

function copiar<K extends keyof DatosActo>(
  destino: DatosActo,
  origen: DatosActo,
  k: K,
): void {
  destino[k] = origen[k];
}

export function ActoFormulario(props: ActoFormularioProps) {
  const { modo, acto, onGuardar, onCancelar, erroresServidor } = props;

  const esEditar = modo === "editar";

  const idTitulo = useId();
  const idTipo = useId();
  const idDenominacion = useId();
  const idNumero = useId();
  const idFecha = useId();
  const idLugar = useId();
  const idCargo = useId();
  const idCompetencia = useId();
  const idFundamentoCompetencia = useId();
  const idFuncionario = useId();
  const idTitularidad = useId();
  const idDelegacionNumero = useId();
  const idDelegacionFecha = useId();
  const idCaracterGeneral = useId();
  const idCaracterParticular = useId();
  const idCaracterInterno = useId();
  const idSimpleTramite = useId();
  const idDestinatario = useId();
  const idAsunto = useId();
  const idHechos = useId();
  const idFundamentos = useId();
  const idDecision = useId();

  const [tipo, setTipo] = useState<TipoActo | "">(acto?.tipo ?? "");
  const [denominacionTipo, setDenominacionTipo] = useState(
    acto?.denominacion_tipo ?? "",
  );
  const [numero, setNumero] = useState(acto?.numero ?? "");
  const [fecha, setFecha] = useState(acto?.fecha ?? hoyDeNegocio());
  const [lugar, setLugar] = useState(acto?.lugar ?? "");
  const [cargoId, setCargoId] = useState(acto?.cargo.id ?? "");
  const [competencia, setCompetencia] = useState(
    acto ? `${acto.competencia.accion}|${acto.competencia.materia}` : "",
  );
  const [fundamentoCompetencia, setFundamentoCompetencia] = useState(
    acto?.fundamento_competencia ?? "",
  );
  const [funcionario, setFuncionario] = useState(acto?.funcionario ?? "");
  const [titularidad, setTitularidad] = useState<Titularidad | "">(
    acto?.titularidad ?? "",
  );
  const [delegacionNumero, setDelegacionNumero] = useState(
    acto?.delegacion_numero ?? "",
  );
  const [delegacionFecha, setDelegacionFecha] = useState(
    acto?.delegacion_fecha ?? "",
  );
  const [caracter, setCaracter] = useState<CaracterActo | "">(
    acto?.caracter ?? "",
  );
  const [simpleTramite, setSimpleTramite] = useState(
    acto?.simple_tramite ?? false,
  );
  const [destinatario, setDestinatario] = useState(acto?.destinatario ?? "");
  const [asunto, setAsunto] = useState(acto?.asunto ?? "");
  const [hechos, setHechos] = useState(acto?.hechos ?? "");
  const [fundamentos, setFundamentos] = useState(acto?.fundamentos ?? "");
  const [decision, setDecision] = useState(acto?.decision ?? "");

  const [erroresLocales, setErroresLocales] = useState<
    Record<string, string>
  >({});
  const [aviso, setAviso] = useState<string | null>(null);

  const autoridades = useQuery({
    queryKey: [...CONSULTA_ACTOS, "autoridades", fecha],
    queryFn: () =>
      apiFetch<ListaAutoridades>(`/gobierno/actos/autoridades?fecha=${fecha}`),
    enabled: Boolean(fecha),
    retry: false,
  });

  const autoridadesEnFecha = autoridades.data?.items ?? [];
  const incluirCargoActual =
    esEditar &&
    acto !== undefined &&
    !autoridadesEnFecha.some(
      (autoridad) => autoridad.cargo_id === acto.cargo.id,
    );

  const opcionesCargo = incluirCargoActual
    ? [
        ...autoridadesEnFecha,
        {
          cargo_id: acto.cargo.id,
          unidad_codigo: acto.cargo.unidad_codigo,
          codigo: acto.cargo.codigo,
          denominacion: acto.cargo.denominacion,
          competencias: [acto.competencia],
        },
      ]
    : autoridadesEnFecha;

  const cargoElegido = opcionesCargo.find(
    (autoridad) => autoridad.cargo_id === cargoId,
  );

  const errorDe = (campo: string): string | undefined => {
    const local = erroresLocales[campo];
    if (local) return local;
    const servidor = erroresServidor[campo];
    return servidor && servidor.length > 0 ? servidor[0] : undefined;
  };

  const errorCompetencia =
    errorDe("competencia.accion") ?? errorDe("competencia");

  const limpiarError = (campo: string) => {
    setErroresLocales((previos) => {
      if (!(campo in previos)) return previos;
      const copia = { ...previos };
      delete copia[campo];
      return copia;
    });
    setAviso(null);
  };

  const cambiarCargo = (nuevoCargoId: string) => {
    setCargoId(nuevoCargoId);
    setCompetencia("");
    limpiarError("cargo_id");
    limpiarError("competencia");
  };

  const validar = (): boolean => {
    const errores: Record<string, string> = {};

    if (!tipo) {
      errores.tipo = "Seleccione el tipo de acto";
    }

    if (tipo === "OTRA_DECISION") {
      const denominacion = denominacionTipo.trim();
      if (denominacion.length < 3 || denominacion.length > 80) {
        errores.denominacion_tipo =
          "La denominación debe tener entre 3 y 80 caracteres";
      }
    }

    const numeroLimpio = numero.trim();
    if (numeroLimpio.length < 1 || numeroLimpio.length > 60) {
      errores.numero = "El número debe tener entre 1 y 60 caracteres";
    }

    const hoy = hoyDeNegocio();
    if (!fecha) {
      errores.fecha = "Seleccione la fecha del acto";
    } else if (fecha > hoy) {
      errores.fecha = "La fecha del acto no puede ser posterior a hoy";
    }

    const lugarLimpio = lugar.trim();
    if (lugarLimpio.length < 2 || lugarLimpio.length > 120) {
      errores.lugar = "El lugar debe tener entre 2 y 120 caracteres";
    }

    if (!cargoId) {
      errores.cargo_id = "Seleccione el cargo que dicta el acto";
    }

    if (!competencia) {
      errores.competencia = "Seleccione la competencia";
    }

    const fundamentoCompetenciaLimpio = fundamentoCompetencia.trim();
    if (
      fundamentoCompetenciaLimpio.length < 5 ||
      fundamentoCompetenciaLimpio.length > 500
    ) {
      errores.fundamento_competencia =
        "El fundamento de la competencia debe tener entre 5 y 500 caracteres";
    }

    const funcionarioLimpio = funcionario.trim();
    if (funcionarioLimpio.length < 3 || funcionarioLimpio.length > 200) {
      errores.funcionario =
        "El funcionario debe tener entre 3 y 200 caracteres";
    }

    if (!titularidad) {
      errores.titularidad = "Seleccione la titularidad";
    }

    if (titularidad === "DELEGACION") {
      const delegacionNumeroLimpio = delegacionNumero.trim();
      if (
        delegacionNumeroLimpio.length < 1 ||
        delegacionNumeroLimpio.length > 60
      ) {
        errores.delegacion_numero =
          "El número del acto de delegación debe tener entre 1 y 60 caracteres";
      }

      if (!delegacionFecha) {
        errores.delegacion_fecha =
          "Seleccione la fecha del acto de delegación";
      } else if (fecha && delegacionFecha > fecha) {
        errores.delegacion_fecha =
          "La fecha de delegación no puede ser posterior a la fecha del acto";
      }
    }

    if (!caracter) {
      errores.caracter = "Seleccione el carácter";
    }

    const destinatarioLimpio = destinatario.trim();
    if (
      destinatarioLimpio !== "" &&
      (destinatarioLimpio.length < 3 || destinatarioLimpio.length > 200)
    ) {
      errores.destinatario =
        "El destinatario debe tener entre 3 y 200 caracteres";
    }

    const asuntoLimpio = asunto.trim();
    if (asuntoLimpio.length < 3 || asuntoLimpio.length > 200) {
      errores.asunto = "El asunto debe tener entre 3 y 200 caracteres";
    }

    const hechosLimpio = hechos.trim();
    if (hechosLimpio.length > 8000) {
      errores.hechos = "Los hechos admiten como máximo 8000 caracteres";
    }

    const fundamentosLimpio = fundamentos.trim();
    if (fundamentosLimpio.length > 4000) {
      errores.fundamentos =
        "Los fundamentos legales admiten como máximo 4000 caracteres";
    }

    const decisionLimpio = decision.trim();
    if (decisionLimpio !== "" && decisionLimpio.length < 3) {
      errores.decision = "La decisión debe tener entre 3 y 8000 caracteres";
    } else if (decisionLimpio.length > 8000) {
      errores.decision = "La decisión admite como máximo 8000 caracteres";
    }

    setErroresLocales(errores);
    return Object.keys(errores).length === 0;
  };

  const normalizarDatos = (): DatosActo => {
    const [accion, materia] = competencia.split("|") as [
      AccionCompetencia,
      MateriaCompetencia,
    ];

    return {
      tipo: tipo as TipoActo,
      denominacion_tipo:
        tipo === "OTRA_DECISION" ? stringVacioANulo(denominacionTipo) : null,
      numero: numero.trim(),
      fecha,
      lugar: lugar.trim(),
      cargo_id: cargoId,
      competencia: { accion, materia },
      fundamento_competencia: fundamentoCompetencia.trim(),
      funcionario: funcionario.trim(),
      titularidad: titularidad as Titularidad,
      delegacion_numero:
        titularidad === "DELEGACION" ? delegacionNumero.trim() : null,
      delegacion_fecha: titularidad === "DELEGACION" ? delegacionFecha : null,
      caracter: caracter as CaracterActo,
      simple_tramite: caracter === "PARTICULAR" ? simpleTramite : false,
      destinatario: stringVacioANulo(destinatario),
      asunto: asunto.trim(),
      hechos: stringVacioANulo(hechos),
      fundamentos: stringVacioANulo(fundamentos),
      decision: stringVacioANulo(decision),
    };
  };

  const construirDatosOriginal = (): DatosActo => {
    if (!acto) {
      return {};
    }

    return {
      tipo: acto.tipo,
      denominacion_tipo: acto.denominacion_tipo,
      numero: acto.numero,
      fecha: acto.fecha,
      lugar: acto.lugar,
      cargo_id: acto.cargo.id,
      competencia: acto.competencia,
      fundamento_competencia: acto.fundamento_competencia,
      funcionario: acto.funcionario,
      titularidad: acto.titularidad,
      delegacion_numero: acto.delegacion_numero,
      delegacion_fecha: acto.delegacion_fecha,
      caracter: acto.caracter,
      simple_tramite: acto.simple_tramite,
      destinatario: acto.destinatario,
      asunto: acto.asunto,
      hechos: acto.hechos,
      fundamentos: acto.fundamentos,
      decision: acto.decision,
    };
  };

  const construirDatos = (): DatosActo | null => {
    const normalizados = normalizarDatos();

    if (!esEditar) {
      return normalizados;
    }

    if (!acto) return null;

    const original = construirDatosOriginal();
    const cambios: DatosActo = {};

    for (const clave of CLAVES_ESCALARES) {
      const valor = normalizados[clave];
      const previo = original[clave];
      if ((previo ?? null) !== (valor ?? null)) {
        copiar(cambios, normalizados, clave);
      }
    }

    const competenciaOriginal = original.competencia;
    const competenciaNueva = normalizados.competencia;
    if (
      competenciaOriginal?.accion !== competenciaNueva?.accion ||
      competenciaOriginal?.materia !== competenciaNueva?.materia
    ) {
      cambios.competencia = competenciaNueva;
    }

    return Object.keys(cambios).length > 0 ? cambios : null;
  };

  const guardar = async () => {
    setAviso(null);

    if (!validar()) return;

    const datos = construirDatos();
    if (!datos) {
      setAviso("No hay cambios que guardar");
      return;
    }

    await onGuardar(datos);
  };

  const titulo =
    modo === "crear"
      ? "Registrar acto"
      : `Editar acto ${acto?.numero ? `Nº ${acto.numero}` : ""}`.trim();

  const textareaClase = (error?: string) =>
    `min-h-24 w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600 ${
      error ? "border-danger-600" : "border-border-default"
    }`;

  const selectClase = (error?: string) =>
    `h-10 w-full rounded-md border bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600 ${
      error ? "border-danger-600" : "border-border-default"
    }`;

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
        label="Tipo de acto"
        htmlFor={idTipo}
        required
        error={errorDe("tipo")}
        help="Según la jerarquía de la LOPA"
      >
        <select
          id={idTipo}
          value={tipo}
          onChange={(evento) => {
            setTipo(evento.target.value as TipoActo | "");
            limpiarError("tipo");
            limpiarError("denominacion_tipo");
          }}
          aria-invalid={Boolean(errorDe("tipo"))}
          className={selectClase(errorDe("tipo"))}
        >
          <option value="">Seleccione el tipo</option>
          {Object.keys(ETIQUETA_TIPO_ACTO).map((valor) => (
            <option key={valor} value={valor}>
              {ETIQUETA_TIPO_ACTO[valor as TipoActo]}
            </option>
          ))}
        </select>
      </FormField>

      {tipo === "OTRA_DECISION" && (
        <FormField
          label="Denominación"
          htmlFor={idDenominacion}
          required
          error={errorDe("denominacion_tipo")}
          help="Ej.: Punto de cuenta"
        >
          <TextInput
            id={idDenominacion}
            value={denominacionTipo}
            maxLength={80}
            onChange={(evento) => {
              setDenominacionTipo(evento.target.value);
              limpiarError("denominacion_tipo");
            }}
            invalid={Boolean(errorDe("denominacion_tipo"))}
          />
        </FormField>
      )}

      <FormField
        label="Número"
        htmlFor={idNumero}
        required
        error={errorDe("numero")}
        help="Tal como consta en el acto"
      >
        <TextInput
          id={idNumero}
          value={numero}
          maxLength={60}
          onChange={(evento) => {
            setNumero(evento.target.value);
            limpiarError("numero");
          }}
          invalid={Boolean(errorDe("numero"))}
        />
      </FormField>

      <FormField
        label="Fecha del acto"
        htmlFor={idFecha}
        required
        error={errorDe("fecha")}
      >
        <DateInput
          id={idFecha}
          value={fecha}
          max={hoyDeNegocio()}
          onChange={(evento) => {
            setFecha(evento.target.value);
            limpiarError("fecha");
          }}
          invalid={Boolean(errorDe("fecha"))}
        />
      </FormField>

      <FormField
        label="Lugar"
        htmlFor={idLugar}
        required
        error={errorDe("lugar")}
      >
        <TextInput
          id={idLugar}
          value={lugar}
          maxLength={120}
          onChange={(evento) => {
            setLugar(evento.target.value);
            limpiarError("lugar");
          }}
          invalid={Boolean(errorDe("lugar"))}
        />
      </FormField>

      {autoridades.isLoading && (
        <p className="md:col-span-2 text-sm text-text-500">
          Cargando autoridades…
        </p>
      )}

      {!autoridades.isLoading && opcionesCargo.length === 0 && (
        <p className="md:col-span-2 text-sm text-warning-700">
          No hay cargos vigentes en esa fecha. Revise Gobierno › Cargos y
          competencias.
        </p>
      )}

      <FormField
        label="Cargo que lo dicta"
        htmlFor={idCargo}
        required
        error={errorDe("cargo_id")}
        help="Cargo vigente en la fecha del acto"
      >
        <select
          id={idCargo}
          value={cargoId}
          onChange={(evento) => cambiarCargo(evento.target.value)}
          disabled={!autoridades.isLoading && opcionesCargo.length === 0}
          aria-invalid={Boolean(errorDe("cargo_id"))}
          className={selectClase(errorDe("cargo_id"))}
        >
          <option value="">Seleccione el cargo</option>
          {opcionesCargo.map((autoridad) => (
            <option key={autoridad.cargo_id} value={autoridad.cargo_id}>
              {autoridad.unidad_codigo} · {autoridad.codigo} —{" "}
              {autoridad.denominacion}
            </option>
          ))}
        </select>
      </FormField>

      <FormField
        label="Competencia"
        htmlFor={idCompetencia}
        required
        error={errorCompetencia}
      >
        <select
          id={idCompetencia}
          value={competencia}
          onChange={(evento) => {
            setCompetencia(evento.target.value);
            limpiarError("competencia");
          }}
          disabled={!cargoElegido}
          aria-invalid={Boolean(errorCompetencia)}
          className={selectClase(errorCompetencia)}
        >
          <option value="">Seleccione la competencia</option>
          {cargoElegido?.competencias.map((competenciaCargo) => (
            <option
              key={`${competenciaCargo.accion}|${competenciaCargo.materia}`}
              value={`${competenciaCargo.accion}|${competenciaCargo.materia}`}
            >
              {ETIQUETA_ACCION[competenciaCargo.accion]} ·{" "}
              {ETIQUETA_MATERIA[competenciaCargo.materia]}
            </option>
          ))}
        </select>
      </FormField>

      <FormField
        label="Fundamento de la competencia"
        htmlFor={idFundamentoCompetencia}
        required
        error={errorDe("fundamento_competencia")}
        help="Norma que atribuye la competencia"
      >
        <textarea
          id={idFundamentoCompetencia}
          value={fundamentoCompetencia}
          maxLength={500}
          onChange={(evento) => {
            setFundamentoCompetencia(evento.target.value);
            limpiarError("fundamento_competencia");
          }}
          aria-invalid={Boolean(errorDe("fundamento_competencia"))}
          className={textareaClase(errorDe("fundamento_competencia"))}
        />
      </FormField>

      <FormField
        label="Funcionario que suscribe"
        htmlFor={idFuncionario}
        required
        error={errorDe("funcionario")}
        help="Tal como consta en el acto"
      >
        <TextInput
          id={idFuncionario}
          value={funcionario}
          maxLength={200}
          onChange={(evento) => {
            setFuncionario(evento.target.value);
            limpiarError("funcionario");
          }}
          invalid={Boolean(errorDe("funcionario"))}
        />
      </FormField>

      <FormField
        label="Titularidad"
        htmlFor={idTitularidad}
        required
        error={errorDe("titularidad")}
      >
        <select
          id={idTitularidad}
          value={titularidad}
          onChange={(evento) => {
            setTitularidad(evento.target.value as Titularidad | "");
            limpiarError("titularidad");
            limpiarError("delegacion_numero");
            limpiarError("delegacion_fecha");
          }}
          aria-invalid={Boolean(errorDe("titularidad"))}
          className={selectClase(errorDe("titularidad"))}
        >
          <option value="">Seleccione la titularidad</option>
          {Object.keys(ETIQUETA_TITULARIDAD).map((valor) => (
            <option key={valor} value={valor}>
              {ETIQUETA_TITULARIDAD[valor as Titularidad]}
            </option>
          ))}
        </select>
      </FormField>

      {titularidad === "DELEGACION" && (
        <>
          <FormField
            label="Nº del acto de delegación"
            htmlFor={idDelegacionNumero}
            required
            error={errorDe("delegacion_numero")}
          >
            <TextInput
              id={idDelegacionNumero}
              value={delegacionNumero}
              maxLength={60}
              onChange={(evento) => {
                setDelegacionNumero(evento.target.value);
                limpiarError("delegacion_numero");
              }}
              invalid={Boolean(errorDe("delegacion_numero"))}
            />
          </FormField>

          <FormField
            label="Fecha del acto de delegación"
            htmlFor={idDelegacionFecha}
            required
            error={errorDe("delegacion_fecha")}
          >
            <DateInput
              id={idDelegacionFecha}
              value={delegacionFecha}
              max={fecha}
              onChange={(evento) => {
                setDelegacionFecha(evento.target.value);
                limpiarError("delegacion_fecha");
              }}
              invalid={Boolean(errorDe("delegacion_fecha"))}
            />
          </FormField>
        </>
      )}

      <fieldset className="md:col-span-2 grid grid-cols-1 gap-3">
        <legend className="text-sm font-medium text-text-700">Carácter</legend>
        <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
          <label className="flex items-center gap-2 text-sm text-text-900">
            <input
              id={idCaracterGeneral}
              type="radio"
              name="caracter"
              value="GENERAL"
              checked={caracter === "GENERAL"}
              onChange={() => {
                setCaracter("GENERAL");
                limpiarError("caracter");
              }}
            />
            {ETIQUETA_CARACTER.GENERAL}
          </label>
          <label className="flex items-center gap-2 text-sm text-text-900">
            <input
              id={idCaracterParticular}
              type="radio"
              name="caracter"
              value="PARTICULAR"
              checked={caracter === "PARTICULAR"}
              onChange={() => {
                setCaracter("PARTICULAR");
                limpiarError("caracter");
              }}
            />
            {ETIQUETA_CARACTER.PARTICULAR}
          </label>
          <label className="flex items-center gap-2 text-sm text-text-900">
            <input
              id={idCaracterInterno}
              type="radio"
              name="caracter"
              value="INTERNO"
              checked={caracter === "INTERNO"}
              onChange={() => {
                setCaracter("INTERNO");
                limpiarError("caracter");
              }}
            />
            {ETIQUETA_CARACTER.INTERNO}
          </label>
        </div>
        {errorDe("caracter") && (
          <p className="text-sm text-danger-600" role="alert">
            {errorDe("caracter")}
          </p>
        )}
      </fieldset>

      {caracter === "PARTICULAR" && (
        <div className="md:col-span-2 flex flex-col gap-1.5">
          <label
            htmlFor={idSimpleTramite}
            className="flex items-center gap-2 text-sm font-medium text-text-700"
          >
            <input
              id={idSimpleTramite}
              type="checkbox"
              checked={simpleTramite}
              onChange={(evento) => {
                setSimpleTramite(evento.target.checked);
                limpiarError("simple_tramite");
              }}
              aria-invalid={Boolean(errorDe("simple_tramite"))}
              className="h-4 w-4 rounded border-border-default text-brand-600 focus:outline-brand-600"
            />
            De simple trámite
          </label>
          <p className="text-xs text-text-500">
            LOPA art. 9: no exige hechos ni fundamentos
          </p>
          {errorDe("simple_tramite") && (
            <p className="text-sm text-danger-600" role="alert">
              {errorDe("simple_tramite")}
            </p>
          )}
        </div>
      )}

      <FormField
        label="Destinatario"
        htmlFor={idDestinatario}
        error={errorDe("destinatario")}
        help="Persona u órgano a quien va dirigido"
      >
        <TextInput
          id={idDestinatario}
          value={destinatario}
          maxLength={200}
          onChange={(evento) => {
            setDestinatario(evento.target.value);
            limpiarError("destinatario");
          }}
          invalid={Boolean(errorDe("destinatario"))}
        />
      </FormField>

      <FormField
        label="Asunto"
        htmlFor={idAsunto}
        required
        error={errorDe("asunto")}
      >
        <TextInput
          id={idAsunto}
          value={asunto}
          maxLength={200}
          onChange={(evento) => {
            setAsunto(evento.target.value);
            limpiarError("asunto");
          }}
          invalid={Boolean(errorDe("asunto"))}
        />
      </FormField>

      <FormField
        label="Hechos"
        htmlFor={idHechos}
        error={errorDe("hechos")}
      >
        <textarea
          id={idHechos}
          value={hechos}
          maxLength={8000}
          onChange={(evento) => {
            setHechos(evento.target.value);
            limpiarError("hechos");
          }}
          aria-invalid={Boolean(errorDe("hechos"))}
          className={textareaClase(errorDe("hechos"))}
        />
      </FormField>

      <FormField
        label="Fundamentos legales"
        htmlFor={idFundamentos}
        error={errorDe("fundamentos")}
      >
        <textarea
          id={idFundamentos}
          value={fundamentos}
          maxLength={4000}
          onChange={(evento) => {
            setFundamentos(evento.target.value);
            limpiarError("fundamentos");
          }}
          aria-invalid={Boolean(errorDe("fundamentos"))}
          className={textareaClase(errorDe("fundamentos"))}
        />
      </FormField>

      <FormField
        label="Decisión"
        htmlFor={idDecision}
        error={errorDe("decision")}
        help="Lo que el acto dispone"
      >
        <textarea
          id={idDecision}
          value={decision}
          maxLength={8000}
          onChange={(evento) => {
            setDecision(evento.target.value);
            limpiarError("decision");
          }}
          aria-invalid={Boolean(errorDe("decision"))}
          className={textareaClase(errorDe("decision"))}
        />
      </FormField>

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
