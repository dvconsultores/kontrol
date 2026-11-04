import { useState } from "react";
import { useNavigate } from "react-router";
import { useQueryClient } from "@tanstack/react-query";

import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import {
  AuditoriaMuestraDetalle,
  AuditoriaMuestraNueva,
  CONSULTA_AUDITORIA,
  ETIQUETA_METODO_MUESTREO,
  FiltrosAuditoria,
  filtrosLimpios,
  MetodoMuestreo,
} from "@/modules/gobierno/api";

type ErroresCampo = Partial<
  Record<"titulo" | "criterio" | "justificacion" | "tamano" | "semilla" | "eventos" | "general", string>
>;

export function RegistrarMuestra({
  filtros,
  seleccion,
  onCancelar,
}: {
  filtros: FiltrosAuditoria;
  seleccion: string[];
  onCancelar: () => void;
}): React.JSX.Element {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const { tiene } = useAutoridad();
  const puedeRegistrar = tiene("gobierno_auditoria:sample", "empresa");

  const [titulo, setTitulo] = useState("");
  const [criterio, setCriterio] = useState("");
  const [justificacion, setJustificacion] = useState("");
  const [metodo, setMetodo] = useState<MetodoMuestreo>("ALEATORIA");
  const [tamano, setTamano] = useState("");
  const [semilla, setSemilla] = useState("");
  const [errores, setErrores] = useState<ErroresCampo>({});

  const textareaClase = (error?: string) =>
    `min-h-24 w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600 ${
      error ? "border-danger-600" : "border-border-default"
    }`;

  const limpiarError = (campo: keyof ErroresCampo) => {
    setErrores((previos) => {
      if (!(campo in previos)) return previos;
      const copia = { ...previos };
      delete copia[campo];
      return copia;
    });
  };

  const validar = (): ErroresCampo => {
    const nuevos: ErroresCampo = {};
    const tituloRecortado = titulo.trim();
    const criterioRecortado = criterio.trim();
    const justificacionRecortada = justificacion.trim();

    if (tituloRecortado.length < 3 || tituloRecortado.length > 200) {
      nuevos.titulo = "El título debe tener entre 3 y 200 caracteres.";
    }
    if (criterioRecortado.length < 10 || criterioRecortado.length > 2000) {
      nuevos.criterio =
        "El criterio debe tener entre 10 y 2000 caracteres.";
    }
    if (justificacionRecortada.length < 10 || justificacionRecortada.length > 2000) {
      nuevos.justificacion =
        "La justificación debe tener entre 10 y 2000 caracteres.";
    }

    if (metodo === "ALEATORIA") {
      const tamanoNumero = Number(tamano);
      if (!Number.isInteger(tamanoNumero) || tamanoNumero < 1) {
        nuevos.tamano = "Indique un tamaño entero mayor o igual a 1.";
      }
      if (semilla.trim() !== "") {
        const semillaNumero = Number(semilla);
        if (
          !Number.isInteger(semillaNumero) ||
          semillaNumero < 1 ||
          semillaNumero > 999999999
        ) {
          nuevos.semilla = "La semilla debe ser un entero entre 1 y 999999999.";
        }
      }
    }

    if (metodo === "ESPECIFICA" && seleccion.length === 0) {
      nuevos.eventos = "Marque al menos una partida en la tabla.";
    }

    return nuevos;
  };

  const enviar = async (): Promise<void> => {
    if (!puedeRegistrar) return;
    const erroresLocales = validar();
    setErrores(erroresLocales);
    if (Object.keys(erroresLocales).length > 0) return;

    const cuerpo: AuditoriaMuestraNueva = {
      titulo: titulo.trim(),
      criterio: criterio.trim(),
      justificacion: justificacion.trim(),
      metodo,
      filtros: filtrosLimpios(filtros),
    };

    if (metodo === "ALEATORIA") {
      cuerpo.tamano = Number(tamano);
      if (semilla.trim() !== "") {
        cuerpo.semilla = Number(semilla);
      }
    } else {
      cuerpo.eventos = seleccion;
    }

    try {
      const creada = await apiFetch<AuditoriaMuestraDetalle>(
        "/gobierno/auditoria/muestras",
        { method: "POST", body: cuerpo },
      );
      notify({ type: "success", title: `Muestra ${creada.codigo} registrada` });
      await queryClient.invalidateQueries({ queryKey: [...CONSULTA_AUDITORIA] });
      navigate(`/gobierno/auditoria/muestras/${creada.id}`);
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 422) {
          if (error.code === "VALIDATION_ERROR") {
            setErrores({
              titulo: error.fieldErrors.titulo?.[0],
              criterio: error.fieldErrors.criterio?.[0],
              justificacion: error.fieldErrors.justificacion?.[0],
              tamano: error.fieldErrors.tamano?.[0],
              semilla: error.fieldErrors.semilla?.[0],
              eventos: error.fieldErrors.eventos?.[0],
            });
            return;
          }
          if (error.code === "GOV_AUDIT_INVALID_SAMPLE_SIZE") {
            setErrores({ tamano: error.message });
            return;
          }
          if (error.code === "GOV_AUDIT_EVENT_OUTSIDE_POPULATION") {
            setErrores({ eventos: error.message });
            return;
          }
          if (error.code === "GOV_AUDIT_EMPTY_POPULATION") {
            setErrores({
              general: "La población filtrada está vacía: amplíe los filtros.",
            });
            return;
          }
          if (error.code === "GOV_AUDIT_POPULATION_TOO_LARGE") {
            setErrores({
              general:
                "La población supera 2000 eventos: acote los filtros o use otro medio.",
            });
            return;
          }
          if (error.code === "INVALID_DATE_RANGE") {
            setErrores({ general: "La fecha inicial es posterior a la final." });
            return;
          }
        }
        if (error.status === 403) {
          notify({
            type: "error",
            title: "No tiene permiso para registrar muestras",
          });
          return;
        }
      }
      notify({ type: "error", title: "No fue posible registrar la muestra" });
    }
  };

  const metodos = Object.keys(ETIQUETA_METODO_MUESTREO) as MetodoMuestreo[];

  if (!puedeRegistrar) {
    return (
      <EmptyState
        title="Sin permiso"
        description="No tiene permiso para registrar muestras de auditoría."
      />
    );
  }

  return (
    <section aria-labelledby="registrar-muestra-titulo">
      <h2
        id="registrar-muestra-titulo"
        className="text-lg font-semibold text-text-900"
      >
        Registrar muestra
      </h2>
      <p className="mt-1 text-sm text-text-600">
        La muestra se toma de la población filtrada. Queda guardada como papel
        de trabajo y no se puede editar ni borrar.
      </p>

      <form
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          void enviar();
        }}
        className="mt-4 space-y-4"
      >
        <FormField
          label="Título"
          htmlFor="muestra-titulo"
          required
          error={errores.titulo}
        >
          <TextInput
            id="muestra-titulo"
            value={titulo}
            maxLength={200}
            onChange={(evento) => {
              setTitulo(evento.target.value);
              limpiarError("titulo");
            }}
            aria-invalid={Boolean(errores.titulo)}
          />
        </FormField>

        <FormField
          label="Criterio de selección"
          htmlFor="muestra-criterio"
          required
          error={errores.criterio}
          help="Qué partidas se escogen y por qué (Normas CGR, Muestra de auditoría)"
        >
          <textarea
            id="muestra-criterio"
            value={criterio}
            maxLength={2000}
            onChange={(evento) => {
              setCriterio(evento.target.value);
              limpiarError("criterio");
            }}
            aria-invalid={Boolean(errores.criterio)}
            className={textareaClase(errores.criterio)}
          />
        </FormField>

        <FormField
          label="Justificación"
          htmlFor="muestra-justificacion"
          required
          error={errores.justificacion}
        >
          <textarea
            id="muestra-justificacion"
            value={justificacion}
            maxLength={2000}
            onChange={(evento) => {
              setJustificacion(evento.target.value);
              limpiarError("justificacion");
            }}
            aria-invalid={Boolean(errores.justificacion)}
            className={textareaClase(errores.justificacion)}
          />
        </FormField>

        <fieldset id="muestra-medio" className="grid grid-cols-1 gap-2">
          <legend className="text-sm font-medium text-text-900">
            Medio de selección
          </legend>
          {metodos.map((metodoValor) => (
            <label
              key={metodoValor}
              className="flex items-center gap-2 text-sm text-text-900"
            >
              <input
                type="radio"
                name="metodo"
                value={metodoValor}
                checked={metodo === metodoValor}
                onChange={() => {
                  setMetodo(metodoValor);
                  limpiarError("tamano");
                  limpiarError("semilla");
                  limpiarError("eventos");
                }}
              />
              {ETIQUETA_METODO_MUESTREO[metodoValor]}
            </label>
          ))}
        </fieldset>

        {metodo === "ALEATORIA" && (
          <>
            <FormField
              label="Tamaño de la muestra"
              htmlFor="muestra-tamano"
              required
              error={errores.tamano}
            >
              <TextInput
                id="muestra-tamano"
                type="number"
                min={1}
                value={tamano}
                onChange={(evento) => {
                  setTamano(evento.target.value);
                  limpiarError("tamano");
                }}
                aria-invalid={Boolean(errores.tamano)}
              />
            </FormField>
            <FormField
              label="Semilla"
              htmlFor="muestra-semilla"
              error={errores.semilla}
              help="Déjela vacía para que el sistema la genere; con la misma semilla y los mismos filtros se obtienen las mismas partidas."
            >
              <TextInput
                id="muestra-semilla"
                type="number"
                min={1}
                max={999999999}
                value={semilla}
                onChange={(evento) => {
                  setSemilla(evento.target.value);
                  limpiarError("semilla");
                }}
                aria-invalid={Boolean(errores.semilla)}
              />
            </FormField>
          </>
        )}

        {metodo === "ESPECIFICA" && (
          <>
            <p aria-live="polite" className="text-sm text-text-600">
              {seleccion.length > 0
                ? `${seleccion.length} partidas marcadas en la tabla`
                : "Marque las partidas en la tabla de la población."}
            </p>
            {errores.eventos && (
              <p className="text-sm text-danger-600">{errores.eventos}</p>
            )}
          </>
        )}

        {errores.general && (
          <p role="alert" className="text-sm text-danger-600">
            {errores.general}
          </p>
        )}

        <div className="flex items-center gap-2">
          <AsyncButton variant="primary" onClick={enviar}>
            Registrar muestra
          </AsyncButton>
          <Button variant="ghost" onClick={onCancelar}>
            Cancelar
          </Button>
        </div>
      </form>
    </section>
  );
}
