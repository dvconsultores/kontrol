import { useId, useState } from "react";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import {
  ETIQUETA_TIPO_PERSONA,
  TipoPersona,
} from "@/modules/gobierno/api";

export interface DatosDestinatario {
  tipo_persona: TipoPersona;
  nombre: string;
  identificacion: string;
  domicilio: string;
  apoderado_nombre: string | null;
  apoderado_identificacion: string | null;
  recursos: string;
}

interface DestinatarioFormularioProps {
  titulo: string;
  textoConfirmar: string;
  inicial?: DatosDestinatario;
  onConfirmar: (datos: DatosDestinatario) => Promise<void>;
  onCancelar: () => void;
  erroresServidor: Record<string, string[]>;
}

export function DestinatarioFormulario(props: DestinatarioFormularioProps) {
  const { titulo, textoConfirmar, inicial, onConfirmar, onCancelar, erroresServidor } = props;

  const idTitulo = useId();
  const idTipoPersona = useId();
  const idNombre = useId();
  const idIdentificacion = useId();
  const idDomicilio = useId();
  const idApoderadoNombre = useId();
  const idApoderadoIdentificacion = useId();
  const idRecursos = useId();

  const [tipoPersona, setTipoPersona] = useState<TipoPersona | "">(
    inicial?.tipo_persona ?? "",
  );
  const [nombre, setNombre] = useState(inicial?.nombre ?? "");
  const [identificacion, setIdentificacion] = useState(
    inicial?.identificacion ?? "",
  );
  const [domicilio, setDomicilio] = useState(inicial?.domicilio ?? "");
  const [apoderadoNombre, setApoderadoNombre] = useState(
    inicial?.apoderado_nombre ?? "",
  );
  const [apoderadoIdentificacion, setApoderadoIdentificacion] = useState(
    inicial?.apoderado_identificacion ?? "",
  );
  const [recursos, setRecursos] = useState(inicial?.recursos ?? "");
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

  const validarRango = (
    valor: string,
    minimo: number,
    maximo: number,
  ): string | null => {
    const largo = valor.trim().length;
    if (largo < minimo || largo > maximo) {
      return `Debe tener entre ${minimo} y ${maximo} caracteres`;
    }
    return null;
  };

  const confirmar = async () => {
    const errores: Record<string, string> = {};
    if (!tipoPersona) {
      errores.tipo_persona = "Seleccione el tipo de persona";
    }
    const errorNombre = validarRango(nombre, 3, 200);
    if (errorNombre) errores.nombre = errorNombre;
    const errorIdentificacion = validarRango(identificacion, 5, 20);
    if (errorIdentificacion) errores.identificacion = errorIdentificacion;
    const errorDomicilio = validarRango(domicilio, 5, 500);
    if (errorDomicilio) errores.domicilio = errorDomicilio;

    const tieneApoderadoNombre = apoderadoNombre.trim().length > 0;
    const tieneApoderadoIdentificacion =
      apoderadoIdentificacion.trim().length > 0;

    if (tieneApoderadoNombre) {
      const errorNombreApoderado = validarRango(apoderadoNombre, 3, 200);
      if (errorNombreApoderado) {
        errores.apoderado_nombre = errorNombreApoderado;
      }
    }
    if (tieneApoderadoIdentificacion) {
      const errorIdentificacionApoderado = validarRango(
        apoderadoIdentificacion,
        5,
        20,
      );
      if (errorIdentificacionApoderado) {
        errores.apoderado_identificacion = errorIdentificacionApoderado;
      }
    }
    if (tieneApoderadoNombre && !tieneApoderadoIdentificacion) {
      errores.apoderado_identificacion = "Indique la cédula del apoderado";
    }
    if (!tieneApoderadoNombre && tieneApoderadoIdentificacion) {
      errores.apoderado_nombre = "Indique el nombre del apoderado";
    }

    const errorRecursos = validarRango(recursos, 5, 2000);
    if (errorRecursos) errores.recursos = errorRecursos;

    setErroresLocales(errores);

    if (Object.keys(errores).length > 0) return;

    await onConfirmar({
      tipo_persona: tipoPersona as TipoPersona,
      nombre: nombre.trim(),
      identificacion: identificacion.trim(),
      domicilio: domicilio.trim(),
      apoderado_nombre: tieneApoderadoNombre ? apoderadoNombre.trim() : null,
      apoderado_identificacion: tieneApoderadoIdentificacion
        ? apoderadoIdentificacion.trim()
        : null,
      recursos: recursos.trim(),
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
        {titulo}
      </h3>

      <fieldset id={idTipoPersona} className="grid grid-cols-1 gap-2">
        <legend className="text-sm font-medium text-text-900">
          Tipo de persona
        </legend>
        {(Object.keys(ETIQUETA_TIPO_PERSONA) as TipoPersona[]).map(
          (tipoValor: TipoPersona) => (
            <label
              key={tipoValor}
              className="flex items-center gap-2 text-sm text-text-900"
            >
              <input
                type="radio"
                name="tipo_persona"
                value={tipoValor}
                checked={tipoPersona === tipoValor}
                onChange={() => {
                  setTipoPersona(tipoValor);
                  limpiarError("tipo_persona");
                }}
                aria-invalid={Boolean(errorDe("tipo_persona"))}
              />
              {ETIQUETA_TIPO_PERSONA[tipoValor]}
            </label>
          ),
        )}
        {errorDe("tipo_persona") && (
          <p className="text-sm text-danger-600">{errorDe("tipo_persona")}</p>
        )}
      </fieldset>

      <FormField
        label="Nombre o razón social"
        htmlFor={idNombre}
        required
        error={errorDe("nombre")}
        help="Tal como consta en su documento"
      >
        <TextInput
          id={idNombre}
          value={nombre}
          maxLength={200}
          onChange={(evento) => {
            setNombre(evento.target.value);
            limpiarError("nombre");
          }}
          invalid={Boolean(errorDe("nombre"))}
        />
      </FormField>

      <FormField
        label="Cédula o RIF"
        htmlFor={idIdentificacion}
        required
        error={errorDe("identificacion")}
        help="Ej.: V-12345678 o J-12345678-9"
      >
        <TextInput
          id={idIdentificacion}
          value={identificacion}
          maxLength={20}
          onChange={(evento) => {
            setIdentificacion(evento.target.value);
            limpiarError("identificacion");
          }}
          invalid={Boolean(errorDe("identificacion"))}
        />
      </FormField>

      <FormField
        label="Domicilio o residencia"
        htmlFor={idDomicilio}
        required
        error={errorDe("domicilio")}
        help="Donde se entregará la notificación (LOPA art. 75)"
      >
        <textarea
          id={idDomicilio}
          value={domicilio}
          maxLength={500}
          onChange={(evento) => {
            setDomicilio(evento.target.value);
            limpiarError("domicilio");
          }}
          aria-invalid={Boolean(errorDe("domicilio"))}
          className={`min-h-24 w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600 ${
            errorDe("domicilio") ? "border-danger-600" : "border-border-default"
          }`}
        />
      </FormField>

      <FormField
        label="Apoderado (opcional)"
        htmlFor={idApoderadoNombre}
        error={errorDe("apoderado_nombre")}
      >
        <TextInput
          id={idApoderadoNombre}
          value={apoderadoNombre}
          maxLength={200}
          onChange={(evento) => {
            setApoderadoNombre(evento.target.value);
            limpiarError("apoderado_nombre");
            limpiarError("apoderado_identificacion");
          }}
          invalid={Boolean(errorDe("apoderado_nombre"))}
        />
      </FormField>

      <FormField
        label="Cédula del apoderado"
        htmlFor={idApoderadoIdentificacion}
        required={apoderadoNombre.trim().length > 0}
        error={errorDe("apoderado_identificacion")}
      >
        <TextInput
          id={idApoderadoIdentificacion}
          value={apoderadoIdentificacion}
          maxLength={20}
          onChange={(evento) => {
            setApoderadoIdentificacion(evento.target.value);
            limpiarError("apoderado_identificacion");
            limpiarError("apoderado_nombre");
          }}
          invalid={Boolean(errorDe("apoderado_identificacion"))}
        />
      </FormField>

      <FormField
        label="Recursos que proceden"
        htmlFor={idRecursos}
        required
        error={errorDe("recursos")}
        help={'Recursos, plazos y órgano ante el cual se interponen (LOPA art. 73), o "No proceden recursos"'}
      >
        <textarea
          id={idRecursos}
          value={recursos}
          maxLength={2000}
          onChange={(evento) => {
            setRecursos(evento.target.value);
            limpiarError("recursos");
          }}
          aria-invalid={Boolean(errorDe("recursos"))}
          className={`min-h-24 w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600 ${
            errorDe("recursos") ? "border-danger-600" : "border-border-default"
          }`}
        />
      </FormField>

      <div className="flex flex-wrap gap-3">
        <AsyncButton variant="primary" onClick={confirmar}>
          {textoConfirmar}
        </AsyncButton>
        <Button variant="secondary" type="button" onClick={onCancelar}>
          Cancelar
        </Button>
      </div>
    </form>
  );
}
