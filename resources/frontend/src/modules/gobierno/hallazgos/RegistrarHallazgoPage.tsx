import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { formatearFecha } from "@/i18n";
import {
  CONSULTA_HALLAZGOS,
  ETIQUETA_RIESGO_HALLAZGO,
  type HallazgoDetalle,
  type HallazgoNuevo,
  type OrigenHallazgo,
  type RiesgoHallazgo,
  type AuditoriaMuestraDetalle,
} from "@/modules/gobierno/api";

type ErroresCampo = Partial<
  Record<
    | "titulo"
    | "condicion"
    | "criterio"
    | "causa"
    | "efecto"
    | "riesgo"
    | "origen_descripcion"
    | "muestra_id"
    | "partidas"
    | "general",
    string
  >
>;

export function RegistrarHallazgoPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const { tiene } = useAutoridad();
  const puedeRegistrar = tiene("gobierno_hallazgos:manage", "empresa");

  const [params] = useSearchParams();
  const muestraId = params.get("muestra");

  const [origen, setOrigen] = useState<OrigenHallazgo>(
    muestraId ? "MUESTRA" : "INDEPENDIENTE",
  );
  const [titulo, setTitulo] = useState("");
  const [condicion, setCondicion] = useState("");
  const [criterio, setCriterio] = useState("");
  const [causa, setCausa] = useState("");
  const [efecto, setEfecto] = useState("");
  const [riesgo, setRiesgo] = useState<RiesgoHallazgo | "">("");
  const [origenDescripcion, setOrigenDescripcion] = useState("");
  const [partidas, setPartidas] = useState<string[]>([]);
  const [errores, setErrores] = useState<ErroresCampo>({});

  const {
    data: muestra,
    isError: muestraNoDisponible,
    isLoading: cargandoMuestra,
  } = useQuery({
    queryKey: ["gobierno", "auditoria", "muestras", muestraId],
    queryFn: () =>
      apiFetch<AuditoriaMuestraDetalle>(
        `/gobierno/auditoria/muestras/${muestraId}`,
      ),
    enabled: Boolean(muestraId),
  });

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
    const condicionRecortada = condicion.trim();
    const criterioRecortado = criterio.trim();
    const causaRecortada = causa.trim();
    const efectoRecortado = efecto.trim();

    if (tituloRecortado.length < 3 || tituloRecortado.length > 200) {
      nuevos.titulo = "El título debe tener entre 3 y 200 caracteres.";
    }
    if (condicionRecortada.length < 10 || condicionRecortada.length > 4000) {
      nuevos.condicion =
        "La condición debe tener entre 10 y 4000 caracteres.";
    }
    if (criterioRecortado.length < 10 || criterioRecortado.length > 4000) {
      nuevos.criterio =
        "El criterio debe tener entre 10 y 4000 caracteres.";
    }
    if (causaRecortada.length < 10 || causaRecortada.length > 4000) {
      nuevos.causa = "La causa debe tener entre 10 y 4000 caracteres.";
    }
    if (efectoRecortado.length < 10 || efectoRecortado.length > 4000) {
      nuevos.efecto = "El efecto debe tener entre 10 y 4000 caracteres.";
    }
    if (riesgo === "") {
      nuevos.riesgo = "Elija el riesgo.";
    }
    if (origen === "INDEPENDIENTE") {
      const descripcionRecortada = origenDescripcion.trim();
      if (descripcionRecortada.length < 10 || descripcionRecortada.length > 500) {
        nuevos.origen_descripcion =
          "El origen descrito debe tener entre 10 y 500 caracteres.";
      }
    }

    return nuevos;
  };

  const enviar = async (): Promise<void> => {
    if (!puedeRegistrar) return;
    const erroresLocales = validar();
    setErrores(erroresLocales);
    if (Object.keys(erroresLocales).length > 0) return;

    const cuerpo: HallazgoNuevo = {
      origen,
      titulo: titulo.trim(),
      condicion: condicion.trim(),
      criterio: criterio.trim(),
      causa: causa.trim(),
      efecto: efecto.trim(),
      riesgo: riesgo as RiesgoHallazgo,
    };

    if (origen === "MUESTRA") {
      if (muestraId) {
        cuerpo.muestra_id = muestraId;
      }
      cuerpo.partidas = partidas;
    } else {
      cuerpo.origen_descripcion = origenDescripcion.trim();
    }

    try {
      const creado = await apiFetch<HallazgoDetalle>("/gobierno/hallazgos", {
        method: "POST",
        body: cuerpo,
      });
      notify({ type: "success", title: "Hallazgo registrado" });
      await queryClient.invalidateQueries({ queryKey: [...CONSULTA_HALLAZGOS] });
      navigate(`/gobierno/hallazgos/${creado.id}`);
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 422 && error.code === "VALIDATION_ERROR") {
          setErrores({
            titulo: error.fieldErrors.titulo?.[0],
            condicion: error.fieldErrors.condicion?.[0],
            criterio: error.fieldErrors.criterio?.[0],
            causa: error.fieldErrors.causa?.[0],
            efecto: error.fieldErrors.efecto?.[0],
            riesgo: error.fieldErrors.riesgo?.[0],
            origen_descripcion: error.fieldErrors.origen_descripcion?.[0],
            muestra_id: error.fieldErrors.muestra_id?.[0],
            partidas: error.fieldErrors.partidas?.[0],
          });
          return;
        }
        if (error.status === 422) {
          setErrores({ general: error.message });
          return;
        }
        if (error.status === 403) {
          notify({
            type: "error",
            title: "No tiene permiso para registrar hallazgos",
          });
          return;
        }
      }
      notify({ type: "error", title: "No fue posible registrar el hallazgo" });
    }
  };

  if (!puedeRegistrar) {
    return (
      <PageContent>
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para registrar hallazgos."
        />
      </PageContent>
    );
  }

  const opcionesRiesgo = Object.keys(
    ETIQUETA_RIESGO_HALLAZGO,
  ) as RiesgoHallazgo[];

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno", to: "/gobierno" },
          { label: "Hallazgos y acciones correctivas", to: "/gobierno/hallazgos" },
        ]}
        title="Registrar hallazgo"
      />

      <form
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          void enviar();
        }}
        className="mt-4 space-y-4"
      >
        <fieldset className="grid grid-cols-1 gap-2">
          <legend className="text-sm font-medium text-text-900">
            Origen del hallazgo
          </legend>
          {muestraId && (
            <label className="flex items-center gap-2 text-sm text-text-900">
              <input
                type="radio"
                name="origen"
                value="MUESTRA"
                checked={origen === "MUESTRA"}
                disabled={muestraNoDisponible}
                onChange={() => {
                  setOrigen("MUESTRA");
                  limpiarError("origen_descripcion");
                }}
              />
              Muestra de auditoría
            </label>
          )}
          <label className="flex items-center gap-2 text-sm text-text-900">
            <input
              type="radio"
              name="origen"
              value="INDEPENDIENTE"
              checked={origen === "INDEPENDIENTE"}
              onChange={() => {
                setOrigen("INDEPENDIENTE");
                limpiarError("muestra_id");
                limpiarError("partidas");
              }}
            />
            Independiente
          </label>
        </fieldset>

        {origen === "MUESTRA" && muestraId && (
          <>
            {cargandoMuestra && (
              <p className="text-sm text-text-600">Cargando muestra…</p>
            )}
            {muestraNoDisponible && (
              <p className="text-sm text-text-600">
                La muestra no está disponible.
              </p>
            )}
            {muestra && (
              <>
                <p className="text-sm text-text-900">
                  Muestra {muestra.codigo} · {muestra.titulo}
                </p>
                <fieldset className="grid grid-cols-1 gap-2">
                  <legend className="text-sm font-medium text-text-900">
                    Partidas que sustentan el hallazgo (opcional)
                  </legend>
                  {muestra.eventos.map((evento, indice) => (
                    <label
                      key={evento.id}
                      className="flex items-center gap-2 text-sm text-text-900"
                    >
                      <input
                        type="checkbox"
                        value={evento.id}
                        checked={partidas.includes(evento.id)}
                        onChange={(eventoCambio) => {
                          const id = eventoCambio.target.value;
                          setPartidas((previas) =>
                            eventoCambio.target.checked
                              ? [...previas, id]
                              : previas.filter((valor) => valor !== id),
                          );
                          limpiarError("partidas");
                        }}
                      />
                      Partida {indice + 1}: {evento.accion_etiqueta} ·{" "}
                      {formatearFecha(evento.fecha)}
                    </label>
                  ))}
                </fieldset>
              </>
            )}
          </>
        )}

        {origen === "INDEPENDIENTE" && (
          <FormField
            label="Origen descrito"
            htmlFor="hallazgo-origen-descripcion"
            required
            error={errores.origen_descripcion}
            help="Por ejemplo, una actuación fiscal externa o una denuncia"
          >
            <textarea
              id="hallazgo-origen-descripcion"
              value={origenDescripcion}
              maxLength={500}
              onChange={(evento) => {
                setOrigenDescripcion(evento.target.value);
                limpiarError("origen_descripcion");
              }}
              aria-invalid={Boolean(errores.origen_descripcion)}
              className={textareaClase(errores.origen_descripcion)}
            />
          </FormField>
        )}

        <FormField
          label="Título"
          htmlFor="hallazgo-titulo"
          required
          error={errores.titulo}
        >
          <TextInput
            id="hallazgo-titulo"
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
          label="Condición"
          htmlFor="hallazgo-condicion"
          required
          error={errores.condicion}
          help="Lo que se encontró"
        >
          <textarea
            id="hallazgo-condicion"
            value={condicion}
            maxLength={4000}
            onChange={(evento) => {
              setCondicion(evento.target.value);
              limpiarError("condicion");
            }}
            aria-invalid={Boolean(errores.condicion)}
            className={textareaClase(errores.condicion)}
          />
        </FormField>

        <FormField
          label="Criterio"
          htmlFor="hallazgo-criterio"
          required
          error={errores.criterio}
          help="La norma o referencia que debió cumplirse"
        >
          <textarea
            id="hallazgo-criterio"
            value={criterio}
            maxLength={4000}
            onChange={(evento) => {
              setCriterio(evento.target.value);
              limpiarError("criterio");
            }}
            aria-invalid={Boolean(errores.criterio)}
            className={textareaClase(errores.criterio)}
          />
        </FormField>

        <FormField
          label="Causa"
          htmlFor="hallazgo-causa"
          required
          error={errores.causa}
          help="Por qué ocurrió"
        >
          <textarea
            id="hallazgo-causa"
            value={causa}
            maxLength={4000}
            onChange={(evento) => {
              setCausa(evento.target.value);
              limpiarError("causa");
            }}
            aria-invalid={Boolean(errores.causa)}
            className={textareaClase(errores.causa)}
          />
        </FormField>

        <FormField
          label="Efecto"
          htmlFor="hallazgo-efecto"
          required
          error={errores.efecto}
          help="Consecuencia o riesgo"
        >
          <textarea
            id="hallazgo-efecto"
            value={efecto}
            maxLength={4000}
            onChange={(evento) => {
              setEfecto(evento.target.value);
              limpiarError("efecto");
            }}
            aria-invalid={Boolean(errores.efecto)}
            className={textareaClase(errores.efecto)}
          />
        </FormField>

        <FormField
          label="Riesgo"
          htmlFor="hallazgo-riesgo"
          required
          error={errores.riesgo}
        >
          <select
            id="hallazgo-riesgo"
            value={riesgo}
            onChange={(evento) => {
              setRiesgo(evento.target.value as RiesgoHallazgo);
              limpiarError("riesgo");
            }}
            aria-invalid={Boolean(errores.riesgo)}
            className={`w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600 ${
              errores.riesgo ? "border-danger-600" : "border-border-default"
            }`}
          >
            <option value="">Elija el riesgo</option>
            {opcionesRiesgo.map((valor) => (
              <option key={valor} value={valor}>
                {ETIQUETA_RIESGO_HALLAZGO[valor]}
              </option>
            ))}
          </select>
        </FormField>

        {errores.general && (
          <p role="alert" className="text-sm text-danger-600">
            {errores.general}
          </p>
        )}

        <div className="flex items-center gap-2">
          <AsyncButton variant="primary" onClick={enviar}>
            Registrar hallazgo
          </AsyncButton>
          <Button variant="secondary" onClick={() => navigate("/gobierno/hallazgos")}>
            Cancelar
          </Button>
        </div>
      </form>
    </PageContent>
  );
}
