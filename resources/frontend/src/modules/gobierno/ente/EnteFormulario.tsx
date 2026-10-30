import { useId, useState } from "react";

import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { DateInput } from "@/components/DateInput";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";

import {
  CAMPOS_ENTE,
  ETIQUETA_ACTO,
  ETIQUETA_CAMPO,
  ETIQUETA_FORMA,
  ETIQUETA_NIVEL,
  type EnteDatos,
} from "@/modules/gobierno/api";

const SELECTOR =
  "h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600";

/** Cambios del formulario: textos o null para vaciar; el servidor valida los catálogos. */
export type CambiosEnte = Partial<Record<keyof EnteDatos, string | null>>;

interface Props {
  modo: "alta" | "edicion" | "modificacion";
  inicial: EnteDatos | null;
  onGuardar: (cambios: CambiosEnte, motivo: string | null) => Promise<void>;
  onCancelar: () => void;
  erroresServidor: Record<string, string[]>;
}

type Campo = (typeof CAMPOS_ENTE)[number];

const VALOR_INICIAL: Record<Campo, string> = {
  denominacion: "",
  siglas: "",
  rif: "",
  nivel_territorial: "",
  forma_organizativa: "",
  organo_adscripcion: "",
  entidad_federal: "",
  municipio: "",
  acto_tipo: "",
  acto_numero: "",
  acto_fecha: "",
  acto_publicacion: "",
};

export function EnteFormulario(props: Props): React.JSX.Element {
  const { modo, inicial, onGuardar, onCancelar, erroresServidor } = props;
  const idBase = useId();
  const [valores, setValores] = useState<Record<Campo, string>>(() => {
    const base = { ...VALOR_INICIAL };
    if (inicial) {
      for (const campo of CAMPOS_ENTE) {
        const valor = inicial[campo];
        base[campo] = valor == null ? "" : String(valor);
      }
    }
    return base;
  });
  const [motivo, setMotivo] = useState("");
  const [aviso, setAviso] = useState<string | null>(null);
  const [erroresLocales, setErroresLocales] = useState<Record<string, string>>({});

  const titulo = modo === "alta" ? "Alta del ente" : modo === "edicion" ? "Editar el borrador" : "Modificar el ente activo";

  const id = (campo: Campo | "motivo"): string => `${idBase}-${campo}`;

  const errorDe = (campo: Campo): string | undefined => {
    const local = erroresLocales[campo];
    if (local) return local;
    const lista = erroresServidor[campo];
    return lista && lista.length > 0 ? lista[0] : undefined;
  };

  const errorMotivo = (): string | undefined => {
    const local = erroresLocales.motivo;
    if (local) return local;
    return erroresServidor.motivo?.[0];
  };

  const setCampo = (campo: Campo, valor: string): void => {
    setValores((prev) => ({ ...prev, [campo]: valor }));
    setAviso(null);
    setErroresLocales((prev) => {
      if (!prev[campo]) return prev;
      const copia = { ...prev };
      delete copia[campo];
      return copia;
    });
  };

  const nivel = valores.nivel_territorial;
  const forma = valores.forma_organizativa;

  async function guardar(): Promise<void> {
    const denominacion = valores.denominacion.trim();
    const motivoTrim = motivo.trim();
    const locales: Record<string, string> = {};

    if (denominacion.length < 3) {
      locales.denominacion = "Indique la denominación oficial (3 a 200 caracteres)";
    }
    if (modo === "modificacion" && motivoTrim.length < 5) {
      locales.motivo = "Indique el motivo (de 5 a 255 caracteres)";
    }

    if (Object.keys(locales).length > 0) {
      setErroresLocales(locales);
      setAviso(null);
      return;
    }

    const cambios: CambiosEnte = {};
    for (const campo of CAMPOS_ENTE) {
      const crudo = valores[campo];
      const valor = crudo.trim() === "" ? null : crudo.trim();
      const visible =
        campo !== "organo_adscripcion" || (forma !== "" && forma !== "ADMINISTRACION_CENTRAL");
      const visible2 =
        campo !== "entidad_federal" || (nivel === "ESTADAL" || nivel === "MUNICIPAL");
      const visible3 = campo !== "municipio" || nivel === "MUNICIPAL";
      if (!visible || !visible2 || !visible3) {
        if (modo !== "alta") {
          const previo = inicial?.[campo] ?? null;
          if (previo !== null) cambios[campo] = null;
        }
        continue;
      }
      if (modo === "alta") {
        if (valor !== null) cambios[campo] = valor;
      } else {
        const previo = inicial?.[campo] ?? null;
        if (previo !== valor) cambios[campo] = valor;
      }
    }

    if (modo !== "alta" && Object.keys(cambios).length === 0) {
      setAviso("No hay cambios que guardar");
      return;
    }

    await onGuardar(cambios, modo === "modificacion" ? motivoTrim : null);
  }

  return (
    <form
      aria-labelledby={`${idBase}-titulo`}
      className="rounded-lg border border-border-default bg-surface-0 p-4"
      noValidate
      onSubmit={(e) => {
        e.preventDefault();
      }}
    >
      <h2 id={`${idBase}-titulo`} className="mb-4 text-base font-semibold text-text-900">
        {titulo}
      </h2>

      <fieldset className="mb-4">
        <legend className="mb-2 text-sm font-semibold text-text-700">Identificación</legend>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <FormField label={ETIQUETA_CAMPO.denominacion} htmlFor={id("denominacion")} required error={errorDe("denominacion")}>
            <TextInput
              id={id("denominacion")}
              value={valores.denominacion}
              onChange={(e) => setCampo("denominacion", e.target.value)}
              required
              invalid={Boolean(errorDe("denominacion"))}
            />
          </FormField>
          <FormField label={ETIQUETA_CAMPO.siglas} htmlFor={id("siglas")} error={errorDe("siglas")}>
            <TextInput
              id={id("siglas")}
              value={valores.siglas}
              onChange={(e) => setCampo("siglas", e.target.value)}
              invalid={Boolean(errorDe("siglas"))}
            />
          </FormField>
          <FormField label={ETIQUETA_CAMPO.rif} htmlFor={id("rif")} help="Ej.: G-20000000-0" error={errorDe("rif")}>
            <TextInput
              id={id("rif")}
              value={valores.rif}
              onChange={(e) => setCampo("rif", e.target.value)}
              invalid={Boolean(errorDe("rif"))}
            />
          </FormField>
        </div>
      </fieldset>

      <fieldset className="mb-4">
        <legend className="mb-2 text-sm font-semibold text-text-700">Naturaleza</legend>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <FormField label={ETIQUETA_CAMPO.nivel_territorial} htmlFor={id("nivel_territorial")} error={errorDe("nivel_territorial")}>
            <select
              id={id("nivel_territorial")}
              className={SELECTOR}
              value={valores.nivel_territorial}
              onChange={(e) => setCampo("nivel_territorial", e.target.value)}
              aria-invalid={Boolean(errorDe("nivel_territorial"))}
            >
              <option value="">Seleccione…</option>
              {Object.entries(ETIQUETA_NIVEL).map(([valor, etiqueta]) => (
                <option key={valor} value={valor}>
                  {etiqueta}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label={ETIQUETA_CAMPO.forma_organizativa} htmlFor={id("forma_organizativa")} error={errorDe("forma_organizativa")}>
            <select
              id={id("forma_organizativa")}
              className={SELECTOR}
              value={valores.forma_organizativa}
              onChange={(e) => setCampo("forma_organizativa", e.target.value)}
              aria-invalid={Boolean(errorDe("forma_organizativa"))}
            >
              <option value="">Seleccione…</option>
              {Object.entries(ETIQUETA_FORMA).map(([valor, etiqueta]) => (
                <option key={valor} value={valor}>
                  {etiqueta}
                </option>
              ))}
            </select>
          </FormField>
          {forma !== "" && forma !== "ADMINISTRACION_CENTRAL" ? (
            <FormField
              label={ETIQUETA_CAMPO.organo_adscripcion}
              htmlFor={id("organo_adscripcion")}
              help="Ministerio, gobernación o alcaldía de adscripción"
              error={errorDe("organo_adscripcion")}
            >
              <TextInput
                id={id("organo_adscripcion")}
                value={valores.organo_adscripcion}
                onChange={(e) => setCampo("organo_adscripcion", e.target.value)}
                invalid={Boolean(errorDe("organo_adscripcion"))}
              />
            </FormField>
          ) : null}
          {nivel === "ESTADAL" || nivel === "MUNICIPAL" ? (
            <FormField label={ETIQUETA_CAMPO.entidad_federal} htmlFor={id("entidad_federal")} error={errorDe("entidad_federal")}>
              <TextInput
                id={id("entidad_federal")}
                value={valores.entidad_federal}
                onChange={(e) => setCampo("entidad_federal", e.target.value)}
                invalid={Boolean(errorDe("entidad_federal"))}
              />
            </FormField>
          ) : null}
          {nivel === "MUNICIPAL" ? (
            <FormField label={ETIQUETA_CAMPO.municipio} htmlFor={id("municipio")} error={errorDe("municipio")}>
              <TextInput
                id={id("municipio")}
                value={valores.municipio}
                onChange={(e) => setCampo("municipio", e.target.value)}
                invalid={Boolean(errorDe("municipio"))}
              />
            </FormField>
          ) : null}
        </div>
      </fieldset>

      <fieldset className="mb-4">
        <legend className="mb-2 text-sm font-semibold text-text-700">Acto de creación</legend>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <FormField label={ETIQUETA_CAMPO.acto_tipo} htmlFor={id("acto_tipo")} error={errorDe("acto_tipo")}>
            <select
              id={id("acto_tipo")}
              className={SELECTOR}
              value={valores.acto_tipo}
              onChange={(e) => setCampo("acto_tipo", e.target.value)}
              aria-invalid={Boolean(errorDe("acto_tipo"))}
            >
              <option value="">Seleccione…</option>
              {Object.entries(ETIQUETA_ACTO).map(([valor, etiqueta]) => (
                <option key={valor} value={valor}>
                  {etiqueta}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label={ETIQUETA_CAMPO.acto_numero} htmlFor={id("acto_numero")} error={errorDe("acto_numero")}>
            <TextInput
              id={id("acto_numero")}
              value={valores.acto_numero}
              onChange={(e) => setCampo("acto_numero", e.target.value)}
              invalid={Boolean(errorDe("acto_numero"))}
            />
          </FormField>
          <FormField label={ETIQUETA_CAMPO.acto_fecha} htmlFor={id("acto_fecha")} error={errorDe("acto_fecha")}>
            <DateInput
              id={id("acto_fecha")}
              value={valores.acto_fecha}
              onChange={(e) => setCampo("acto_fecha", e.target.value)}
              invalid={Boolean(errorDe("acto_fecha"))}
            />
          </FormField>
          <FormField
            label={ETIQUETA_CAMPO.acto_publicacion}
            htmlFor={id("acto_publicacion")}
            help="Ej.: G.O. N.º 6.147 Extraordinario del 17/11/2014"
            error={errorDe("acto_publicacion")}
          >
            <TextInput
              id={id("acto_publicacion")}
              value={valores.acto_publicacion}
              onChange={(e) => setCampo("acto_publicacion", e.target.value)}
              invalid={Boolean(errorDe("acto_publicacion"))}
            />
          </FormField>
        </div>
      </fieldset>

      {modo === "modificacion" ? (
        <fieldset className="mb-4">
          <legend className="mb-2 text-sm font-semibold text-text-700">Motivo de la modificación</legend>
          <FormField
            label="Motivo de la modificación"
            htmlFor={id("motivo")}
            required
            help="De 5 a 255 caracteres; queda en el historial y en la auditoría"
            error={errorMotivo()}
          >
            <textarea
              id={id("motivo")}
              className="min-h-24 w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              value={motivo}
              onChange={(e) => {
                setMotivo(e.target.value);
                setAviso(null);
                setErroresLocales((prev) => {
                  if (!prev.motivo) return prev;
                  const copia = { ...prev };
                  delete copia.motivo;
                  return copia;
                });
              }}
              maxLength={255}
              required
              aria-invalid={Boolean(errorMotivo())}
            />
          </FormField>
        </fieldset>
      ) : null}

      {aviso ? (
        <p role="status" className="mb-3 text-sm text-warning-700">
          {aviso}
        </p>
      ) : null}

      <div className="flex flex-wrap gap-2">
        <AsyncButton onClick={guardar} loadingText="Guardando…">
          Guardar
        </AsyncButton>
        <Button variant="secondary" onClick={onCancelar}>
          Cancelar
        </Button>
      </div>
    </form>
  );
}
