import { useId, useState } from "react";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { Acto, nombreDeActo } from "@/modules/gobierno/api";

export type CorreccionActo = Partial<
  Record<
    | "lugar"
    | "asunto"
    | "destinatario"
    | "funcionario"
    | "hechos"
    | "fundamentos"
    | "decision"
    | "fundamento_competencia",
    string | null
  >
> & { motivo: string };

export interface CorregirActoProps {
  acto: Acto;
  onConfirmar: (datos: CorreccionActo) => Promise<void>;
  onCancelar: () => void;
  erroresServidor: Record<string, string[]>;
}

type CampoCorreccion =
  | "lugar"
  | "asunto"
  | "destinatario"
  | "funcionario"
  | "hechos"
  | "fundamentos"
  | "decision"
  | "fundamento_competencia";

const textoInicial = (valor: string | null): string => valor ?? "";

const normalizar = (valor: string): string | null => {
  const texto = valor.trim();
  return texto.length === 0 ? null : texto;
};

export function CorregirActo(props: CorregirActoProps) {
  const { acto, onConfirmar, onCancelar, erroresServidor } = props;

  const idTitulo = useId();
  const idLugar = useId();
  const idAsunto = useId();
  const idDestinatario = useId();
  const idFuncionario = useId();
  const idFundamentoCompetencia = useId();
  const idHechos = useId();
  const idFundamentos = useId();
  const idDecision = useId();
  const idMotivo = useId();

  const [valores, setValores] = useState<Record<CampoCorreccion, string>>({
    lugar: textoInicial(acto.lugar),
    asunto: acto.asunto,
    destinatario: textoInicial(acto.destinatario),
    funcionario: acto.funcionario,
    hechos: textoInicial(acto.hechos),
    fundamentos: textoInicial(acto.fundamentos),
    decision: textoInicial(acto.decision),
    fundamento_competencia: acto.fundamento_competencia,
  });
  const [motivo, setMotivo] = useState("");
  const [aviso, setAviso] = useState<string | null>(null);
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

  const validarCampo = (
    valor: string,
    minimo: number,
    maximo: number,
    obligatorio: boolean,
  ): string | undefined => {
    const texto = valor.trim();
    if (obligatorio && texto.length === 0) {
      return "Campo obligatorio";
    }
    if (texto.length > 0 && texto.length < minimo) {
      return `Debe tener entre ${minimo} y ${maximo} caracteres`;
    }
    if (texto.length > maximo) {
      return `Debe tener como máximo ${maximo} caracteres`;
    }
    return undefined;
  };

  const confirmar = async () => {
    setAviso(null);
    const errores: Record<string, string> = {};

    const reglas: Array<{
      campo: CampoCorreccion;
      minimo: number;
      maximo: number;
      obligatorio: boolean;
    }> = [
      { campo: "lugar", minimo: 2, maximo: 120, obligatorio: true },
      { campo: "asunto", minimo: 3, maximo: 200, obligatorio: true },
      { campo: "destinatario", minimo: 3, maximo: 200, obligatorio: false },
      { campo: "funcionario", minimo: 3, maximo: 200, obligatorio: true },
      { campo: "hechos", minimo: 1, maximo: 8000, obligatorio: false },
      { campo: "fundamentos", minimo: 1, maximo: 4000, obligatorio: false },
      { campo: "decision", minimo: 3, maximo: 8000, obligatorio: true },
      {
        campo: "fundamento_competencia",
        minimo: 5,
        maximo: 500,
        obligatorio: true,
      },
    ];

    reglas.forEach(({ campo, minimo, maximo, obligatorio }) => {
      const mensaje = validarCampo(
        valores[campo],
        minimo,
        maximo,
        obligatorio,
      );
      if (mensaje) errores[campo] = mensaje;
    });

    const motivoTexto = motivo.trim();
    if (motivoTexto.length < 5 || motivoTexto.length > 255) {
      errores.motivo = "Indique el motivo (de 5 a 255 caracteres)";
    }

    if (Object.keys(errores).length > 0) {
      setErroresLocales(errores);
      return;
    }

    const originales: Record<CampoCorreccion, string | null> = {
      lugar: acto.lugar,
      asunto: acto.asunto,
      destinatario: acto.destinatario,
      funcionario: acto.funcionario,
      hechos: acto.hechos,
      fundamentos: acto.fundamentos,
      decision: acto.decision,
      fundamento_competencia: acto.fundamento_competencia,
    };

    const cambios: Partial<Record<CampoCorreccion, string | null>> = {};
    (Object.keys(valores) as CampoCorreccion[]).forEach((campo) => {
      const normalizado = normalizar(valores[campo]);
      if (normalizado !== originales[campo]) {
        cambios[campo] = normalizado;
      }
    });

    if (Object.keys(cambios).length === 0) {
      setAviso("No hay cambios que guardar");
      return;
    }

    await onConfirmar({ ...cambios, motivo: motivoTexto });
  };

  const actualizar = (campo: CampoCorreccion, valor: string) => {
    setValores((previos) => ({ ...previos, [campo]: valor }));
    limpiarError(campo);
    setAviso(null);
  };

  const claseTextarea = (campo: string) =>
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
        Corregir un error material de {nombreDeActo(acto)}
      </h3>
      <p className="text-sm text-text-600">
        Solo para errores materiales o de cálculo (LOPA art. 84). El tipo, el
        número, la fecha, la autoridad, el carácter y la eficacia no se corrigen.
      </p>

      <FormField
        label="Lugar"
        htmlFor={idLugar}
        required
        error={errorDe("lugar")}
      >
        <TextInput
          id={idLugar}
          value={valores.lugar}
          maxLength={120}
          onChange={(evento) => actualizar("lugar", evento.target.value)}
          invalid={Boolean(errorDe("lugar"))}
        />
      </FormField>

      <FormField label="Asunto" htmlFor={idAsunto} required error={errorDe("asunto")}>
        <TextInput
          id={idAsunto}
          value={valores.asunto}
          maxLength={200}
          onChange={(evento) => actualizar("asunto", evento.target.value)}
          invalid={Boolean(errorDe("asunto"))}
        />
      </FormField>

      <FormField
        label="Destinatario"
        htmlFor={idDestinatario}
        error={errorDe("destinatario")}
      >
        <TextInput
          id={idDestinatario}
          value={valores.destinatario}
          maxLength={200}
          onChange={(evento) => actualizar("destinatario", evento.target.value)}
          invalid={Boolean(errorDe("destinatario"))}
        />
      </FormField>

      <FormField
        label="Funcionario que suscribe"
        htmlFor={idFuncionario}
        required
        error={errorDe("funcionario")}
      >
        <TextInput
          id={idFuncionario}
          value={valores.funcionario}
          maxLength={200}
          onChange={(evento) => actualizar("funcionario", evento.target.value)}
          invalid={Boolean(errorDe("funcionario"))}
        />
      </FormField>

      <FormField
        label="Fundamento de la competencia"
        htmlFor={idFundamentoCompetencia}
        required
        error={errorDe("fundamento_competencia")}
      >
        <textarea
          id={idFundamentoCompetencia}
          value={valores.fundamento_competencia}
          maxLength={500}
          rows={4}
          onChange={(evento) =>
            actualizar("fundamento_competencia", evento.target.value)
          }
          aria-invalid={Boolean(errorDe("fundamento_competencia"))}
          className={claseTextarea("fundamento_competencia")}
        />
      </FormField>

      <FormField label="Hechos" htmlFor={idHechos} error={errorDe("hechos")}>
        <textarea
          id={idHechos}
          value={valores.hechos}
          maxLength={8000}
          rows={5}
          onChange={(evento) => actualizar("hechos", evento.target.value)}
          aria-invalid={Boolean(errorDe("hechos"))}
          className={claseTextarea("hechos")}
        />
      </FormField>

      <FormField
        label="Fundamentos legales"
        htmlFor={idFundamentos}
        error={errorDe("fundamentos")}
      >
        <textarea
          id={idFundamentos}
          value={valores.fundamentos}
          maxLength={4000}
          rows={5}
          onChange={(evento) => actualizar("fundamentos", evento.target.value)}
          aria-invalid={Boolean(errorDe("fundamentos"))}
          className={claseTextarea("fundamentos")}
        />
      </FormField>

      <FormField
        label="Decisión"
        htmlFor={idDecision}
        required
        error={errorDe("decision")}
      >
        <textarea
          id={idDecision}
          value={valores.decision}
          maxLength={8000}
          rows={5}
          onChange={(evento) => actualizar("decision", evento.target.value)}
          aria-invalid={Boolean(errorDe("decision"))}
          className={claseTextarea("decision")}
        />
      </FormField>

      <FormField
        label="Motivo de la corrección"
        htmlFor={idMotivo}
        required
        error={errorDe("motivo")}
        help="Queda en el historial y en la auditoría"
      >
        <textarea
          id={idMotivo}
          value={motivo}
          maxLength={255}
          rows={4}
          onChange={(evento) => {
            setMotivo(evento.target.value);
            limpiarError("motivo");
            setAviso(null);
          }}
          aria-invalid={Boolean(errorDe("motivo"))}
          className={claseTextarea("motivo")}
        />
      </FormField>

      {aviso ? (
        <p role="status" className="text-sm text-text-600">
          {aviso}
        </p>
      ) : null}

      <div className="flex flex-wrap gap-3">
        <AsyncButton onClick={confirmar}>Guardar corrección</AsyncButton>
        <Button variant="secondary" type="button" onClick={onCancelar}>
          Cancelar
        </Button>
      </div>
    </form>
  );
}
