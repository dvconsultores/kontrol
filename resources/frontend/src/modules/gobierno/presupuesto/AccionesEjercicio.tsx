import { useId, useState } from "react";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";

import type { DocumentSummary } from "@/modules/documentos/types";
import type { EjercicioDetalle, EscribirEjercicio } from "./api";

interface AccionesEjercicioProps {
  detalle: EjercicioDetalle;
  puedeAprobar: boolean;
  puedeCerrar: boolean;
  escribir: EscribirEjercicio;
  erroresServidor: Record<string, string[]>;
}

type TipoFijacion = "APROBAR" | "RECONDUCIR";

export function AccionesEjercicio({
  detalle,
  puedeAprobar,
  puedeCerrar,
  escribir,
  erroresServidor,
}: AccionesEjercicioProps) {
  const idTitulo = useId();

  const [tipoFijacion, setTipoFijacion] = useState<TipoFijacion>("APROBAR");
  const [referenciaFijacion, setReferenciaFijacion] = useState("");
  const [fechaFijacion, setFechaFijacion] = useState("");
  const [documentoFijacion, setDocumentoFijacion] = useState("");
  const [enviandoFijacion, setEnviandoFijacion] = useState(false);

  const [precompromisoActivo, setPrecompromisoActivo] = useState(
    detalle.precompromiso_activo,
  );
  const [precompromisoDesde, setPrecompromisoDesde] = useState(
    detalle.precompromiso_desde ?? "",
  );
  const [precompromisoMotivo, setPrecompromisoMotivo] = useState("");
  const [enviandoPrecompromiso, setEnviandoPrecompromiso] = useState(false);

  const [motivoCierre, setMotivoCierre] = useState("");
  const [enviandoCierre, setEnviandoCierre] = useState(false);

  const documentosQuery = useQuery({
    queryKey: [
      "documentos",
      "por-recurso",
      "GovernmentBudgetYear",
      detalle.id,
    ],
    queryFn: () =>
      apiFetch<DocumentSummary[]>(
        `/documentos/por-recurso/GovernmentBudgetYear/${encodeURIComponent(detalle.id)}`,
      ),
    retry: false,
  });

  const documentosValidos =
    documentosQuery.data?.filter(
      (documento) => documento.status === "ACTIVE",
    ) ?? [];

  async function fijarEjercicio() {
    setEnviandoFijacion(true);
    try {
      await escribir(
        tipoFijacion === "APROBAR" ? "/aprobar" : "/reconducir",
        "POST",
        {
          referencia: referenciaFijacion.trim(),
          fecha: fechaFijacion || null,
          documento_id: documentoFijacion || null,
        },
      );
      setReferenciaFijacion("");
      setFechaFijacion("");
      setDocumentoFijacion("");
    } catch {
      // La página ya informó del error.
    } finally {
      setEnviandoFijacion(false);
    }
  }

  async function guardarPrecompromiso() {
    setEnviandoPrecompromiso(true);
    try {
      await escribir("/precompromiso", "POST", {
        activo: precompromisoActivo,
        vigente_desde: precompromisoDesde || null,
        motivo: precompromisoMotivo.trim() || null,
      });
      setPrecompromisoMotivo("");
    } catch {
      // La página ya informó del error.
    } finally {
      setEnviandoPrecompromiso(false);
    }
  }

  async function cerrarEjercicio() {
    setEnviandoCierre(true);
    try {
      await escribir("/cerrar", "POST", { motivo: motivoCierre.trim() || null });
      setMotivoCierre("");
    } catch {
      // La página ya informó del error.
    } finally {
      setEnviandoCierre(false);
    }
  }

  const hayAccionFijacion =
    detalle.estado === "BORRADOR" && puedeAprobar;
  const hayAccionPrecompromiso =
    detalle.estado !== "CERRADO" && puedeAprobar;
  const hayAccionCierre =
    (detalle.estado === "APROBADO" || detalle.estado === "RECONDUCIDO") &&
    puedeCerrar;

  const hayAcciones =
    hayAccionFijacion || hayAccionPrecompromiso || hayAccionCierre;

  return (
    <section aria-labelledby={idTitulo}>
      <h2
        id={idTitulo}
        className="mb-4 text-lg font-semibold text-text-900"
      >
        Fijación, precompromiso y cierre
      </h2>

      {!hayAcciones ? (
        <p className="text-sm text-text-700">
          No hay acciones disponibles para este ejercicio con sus permisos.
        </p>
      ) : null}

      {hayAccionFijacion ? (
        <form
          onSubmit={(evento) => {
            evento.preventDefault();
            void fijarEjercicio();
          }}
          className="mb-6 rounded-md border border-border-default p-4"
        >
          <h3 className="mb-2 text-base font-medium text-text-800">
            Fijar el ejercicio
          </h3>
          <fieldset className="mb-4">
            <legend className="mb-2 text-sm font-medium text-text-700">
              Fundamento
            </legend>
            <label className="flex items-center gap-2 text-sm text-text-900">
              <input
                type="radio"
                name="tipo-fijacion"
                value="APROBAR"
                checked={tipoFijacion === "APROBAR"}
                onChange={() => setTipoFijacion("APROBAR")}
              />
              Ordenanza de presupuesto sancionada
            </label>
            <label className="mt-2 flex items-center gap-2 text-sm text-text-900">
              <input
                type="radio"
                name="tipo-fijacion"
                value="RECONDUCIR"
                checked={tipoFijacion === "RECONDUCIR"}
                onChange={() => setTipoFijacion("RECONDUCIR")}
              />
              Reconducción del presupuesto anterior (LOPPM art. 234)
            </label>
          </fieldset>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <FormField
              label="Referencia"
              htmlFor="fijacion-referencia"
              help="Gaceta y número"
              error={erroresServidor.referencia?.[0]}
            >
              <TextInput
                id="fijacion-referencia"
                value={referenciaFijacion}
                onChange={(evento) =>
                  setReferenciaFijacion(evento.target.value)
                }
                aria-invalid={Boolean(erroresServidor.referencia)}
              />
            </FormField>

            <FormField
              label={
                tipoFijacion === "APROBAR"
                  ? "Fecha de sanción"
                  : "Fecha de publicación del reconducido"
              }
              htmlFor="fijacion-fecha"
              error={erroresServidor.fecha?.[0]}
            >
              <input
                id="fijacion-fecha"
                type="date"
                value={fechaFijacion}
                onChange={(evento) => setFechaFijacion(evento.target.value)}
                aria-invalid={Boolean(erroresServidor.fecha)}
                className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
              />
            </FormField>

            <FormField
              label="Documento"
              htmlFor="fijacion-documento"
              error={erroresServidor.documento_id?.[0]}
            >
              <select
                id="fijacion-documento"
                value={documentoFijacion}
                onChange={(evento) => setDocumentoFijacion(evento.target.value)}
                aria-invalid={Boolean(erroresServidor.documento_id)}
                className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
              >
                <option value="">Sin documento</option>
                {documentosValidos.map((documento) => (
                  <option key={documento.id} value={documento.id}>
                    {documento.document_number ?? documento.title}
                  </option>
                ))}
              </select>
            </FormField>
          </div>

          <p className="mt-3 text-sm text-text-700">
            Al fijar el ejercicio, su estructura y su clasificador quedan
            inmutables.
          </p>

          <div className="mt-4">
            <button
              type="submit"
              disabled={enviandoFijacion}
              className="inline-flex h-10 items-center rounded-md bg-brand-600 px-3 text-sm font-medium text-white hover:bg-brand-700 focus-visible:outline-brand-600 disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-brand-300"
            >
              {tipoFijacion === "APROBAR"
                ? "Aprobar ejercicio"
                : "Reconducir ejercicio"}
            </button>
          </div>
        </form>
      ) : null}

      {hayAccionPrecompromiso ? (
        <form
          onSubmit={(evento) => {
            evento.preventDefault();
            void guardarPrecompromiso();
          }}
          className="mb-6 rounded-md border border-border-default p-4"
        >
          <h3 className="mb-2 text-base font-medium text-text-800">
            Precompromiso
          </h3>
          <p className="mb-3 text-sm text-text-700">
            Estado actual:{" "}
            {detalle.precompromiso_activo && detalle.precompromiso_desde
              ? `Activo desde ${formatearFechaDeNegocio(detalle.precompromiso_desde)}`
              : "No activo"}
          </p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <label className="flex items-center gap-2 text-sm text-text-900">
              <input
                type="checkbox"
                checked={precompromisoActivo}
                onChange={(evento) =>
                  setPrecompromisoActivo(evento.target.checked)
                }
              />
              Precompromiso activo
            </label>

            <FormField
              label="Vigente desde"
              htmlFor="precompromiso-desde"
              error={erroresServidor.vigente_desde?.[0]}
            >
              <input
                id="precompromiso-desde"
                type="date"
                value={precompromisoDesde}
                onChange={(evento) =>
                  setPrecompromisoDesde(evento.target.value)
                }
                aria-invalid={Boolean(erroresServidor.vigente_desde)}
                className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
              />
            </FormField>

            <FormField
              label="Motivo"
              htmlFor="precompromiso-motivo"
              error={erroresServidor.motivo?.[0]}
              className="sm:col-span-2"
            >
              <textarea
                id="precompromiso-motivo"
                value={precompromisoMotivo}
                onChange={(evento) =>
                  setPrecompromisoMotivo(evento.target.value)
                }
                aria-invalid={Boolean(erroresServidor.motivo)}
                rows={3}
                className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
              />
            </FormField>
          </div>
          <p className="mt-3 text-sm text-text-700">
            Solo registra la política; no crea reservas.
          </p>
          <div className="mt-4">
            <button
              type="submit"
              disabled={enviandoPrecompromiso}
              className="inline-flex h-10 items-center rounded-md bg-brand-600 px-3 text-sm font-medium text-white hover:bg-brand-700 focus-visible:outline-brand-600 disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-brand-300"
            >
              Guardar política de precompromiso
            </button>
          </div>
        </form>
      ) : null}

      {hayAccionCierre ? (
        <form
          onSubmit={(evento) => {
            evento.preventDefault();
            void cerrarEjercicio();
          }}
          className="rounded-md border border-border-default p-4"
        >
          <h3 className="mb-2 text-base font-medium text-text-800">
            Cerrar el ejercicio
          </h3>
          <FormField
            label="Motivo"
            htmlFor="cierre-motivo"
            help="Solo procede después del 31 de diciembre del año (LOPPM art. 248)."
            error={erroresServidor.motivo?.[0]}
          >
            <textarea
              id="cierre-motivo"
              value={motivoCierre}
              onChange={(evento) => setMotivoCierre(evento.target.value)}
              aria-invalid={Boolean(erroresServidor.motivo)}
              rows={3}
              className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
            />
          </FormField>
          <div className="mt-4">
            <button
              type="submit"
              disabled={enviandoCierre}
              className="inline-flex h-10 items-center rounded-md bg-brand-600 px-3 text-sm font-medium text-white hover:bg-brand-700 focus-visible:outline-brand-600 disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-brand-300"
            >
              Cerrar ejercicio
            </button>
          </div>
        </form>
      ) : null}
    </section>
  );
}
