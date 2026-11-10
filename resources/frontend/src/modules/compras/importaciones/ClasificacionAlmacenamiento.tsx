import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { apiFetch, type ArchivoDescargado } from "@/api/client";
import { descargarArchivo, mensajeDeDescarga } from "@/api/descargas";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Autorizado } from "@/components/Autorizado";
import { AsyncButton } from "@/components/AsyncButton";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import type { AlmacenamientoRespuesta } from "./tipos";

type Props = {
  importacionId: string;
  onCambios: () => void;
};

function textoPolitica(mode: string): string {
  if (mode === "ENFORCED") return "Clasificación obligatoria en este almacén";
  if (mode === "DISABLED") return "Almacén sin clasificación obligatoria";
  return `Política: ${mode}`;
}

function textoPerfil(row: AlmacenamientoRespuesta["rows"][number]): string {
  if (!row.profile) return "Sin perfil de almacenamiento";
  const partes: string[] = [];
  if (row.profile.weight_value) {
    const unidad = row.profile.weight_unit?.symbol ?? "";
    partes.push(`Peso: ${row.profile.weight_value} ${unidad}`.trim());
  }
  if (row.profile.volume_value) {
    const unidad = row.profile.volume_unit?.symbol ?? "";
    partes.push(`Volumen: ${row.profile.volume_value} ${unidad}`.trim());
  }
  if (row.profile.size_class) {
    partes.push(`Clase: ${row.profile.size_class.name}`);
  }
  if (row.profile.conditions.length > 0) {
    partes.push(`Condiciones: ${row.profile.conditions.map((c) => c.name).join(", ")}`);
  }
  return partes.join(" · ") || "Sin perfil de almacenamiento";
}

export function ClasificacionAlmacenamiento({ importacionId, onCambios }: Props): React.JSX.Element {
  const { notify } = useNotifications();
  const urlsImpresion = useRef<string[]>([]);

  const query = useQuery({
    queryKey: ["importaciones", importacionId, "almacenamiento"],
    queryFn: async () => {
      const resp = await apiFetch<AlmacenamientoRespuesta>(`/importaciones/${importacionId}/storage`);
      return resp;
    },
    refetchOnMount: "always",
    retry: false,
  });

  useEffect(() => {
    const urls = urlsImpresion.current;
    return () => {
      urls.forEach((url) => URL.revokeObjectURL(url));
    };
  }, []);

  async function refrescar() {
    await query.refetch();
    onCambios();
  }

  async function clasificar(row: AlmacenamientoRespuesta["rows"][number]): Promise<void> {
    try {
      await apiFetch(`/importaciones/${importacionId}/storage/classify`, {
        method: "POST",
        body: {
          receipt_id: row.receipt_id,
          product_id: row.product_id,
          state: row.state,
        },
      });
      notify({ type: "success", title: "Mercancía clasificada" });
      await refrescar();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible clasificar la mercancía";
      notify({ type: "error", title: "No fue posible clasificar la mercancía", description: message });
    }
  }

  async function generarEtiqueta(row: AlmacenamientoRespuesta["rows"][number]): Promise<void> {
    if (!row.classification) return;
    try {
      await apiFetch(`/importaciones/${importacionId}/storage/labels`, {
        method: "POST",
        body: { classification_id: row.classification.id },
      });
      notify({ type: "success", title: "Etiqueta generada" });
      await refrescar();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible generar la etiqueta";
      notify({ type: "error", title: "No fue posible generar la etiqueta", description: message });
    }
  }

  async function descargarEtiqueta(
    row: AlmacenamientoRespuesta["rows"][number],
    reference: string,
    fileId: string,
    fileName: string,
  ): Promise<void> {
    try {
      const nombre = await descargarArchivo(
        `/importaciones/${importacionId}/storage/labels/${fileId}/pdf`,
        fileName,
      );
      notify({ type: "success", title: `Descargado ${nombre}` });
      void row;
      void reference;
    } catch (error) {
      notify({ type: "error", title: mensajeDeDescarga(error) });
    }
  }

  async function imprimirEtiqueta(
    row: AlmacenamientoRespuesta["rows"][number],
    reference: string,
    fileId: string,
  ): Promise<void> {
    try {
      const archivo = await apiFetch<ArchivoDescargado>(
        `/importaciones/${importacionId}/storage/labels/${fileId}/pdf?inline=true`,
        { responseType: "archivo" },
      );
      const url = URL.createObjectURL(archivo.blob);
      urlsImpresion.current.push(url);
      window.open(url, "_blank");
      void row;
      void reference;
    } catch (error) {
      notify({ type: "error", title: mensajeDeDescarga(error) });
    }
  }

  async function ubicar(
    row: AlmacenamientoRespuesta["rows"][number],
    ubicacion: string,
    cantidad: string,
  ): Promise<void> {
    try {
      await apiFetch(`/importaciones/${importacionId}/storage/putaway`, {
        method: "POST",
        body: {
          receipt_id: row.receipt_id,
          product_id: row.product_id,
          state: row.state,
          target_location_id: ubicacion,
          quantity: cantidad,
        },
      });
      notify({ type: "success", title: "Mercancía ubicada" });
      await refrescar();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible ubicar la mercancía";
      notify({ type: "error", title: "No fue posible ubicar la mercancía", description: message });
    }
  }

  if (query.isLoading) {
    return (
      <section aria-labelledby="clasificacion-almacenamiento-titulo" className="rounded-lg border border-border-default bg-surface-0 p-6">
        <h3 id="clasificacion-almacenamiento-titulo" className="mb-4 text-lg font-semibold text-text-900">Clasificación de almacenamiento</h3>
        <p className="text-sm text-text-600">Cargando clasificación de almacenamiento…</p>
      </section>
    );
  }

  if (query.isError) {
    return (
      <section aria-labelledby="clasificacion-almacenamiento-titulo" className="rounded-lg border border-border-default bg-surface-0 p-6">
        <h3 id="clasificacion-almacenamiento-titulo" className="mb-4 text-lg font-semibold text-text-900">Clasificación de almacenamiento</h3>
        <div role="alert" className="rounded-md border border-danger-200 bg-danger-50 p-3 text-sm text-danger-700">
          No fue posible cargar la clasificación de almacenamiento.
        </div>
      </section>
    );
  }

  const data = query.data!;
  const filas = data.rows;

  return (
    <section aria-labelledby="clasificacion-almacenamiento-titulo" className="rounded-lg border border-border-default bg-surface-0 p-6">
      <h3 id="clasificacion-almacenamiento-titulo" className="mb-4 text-lg font-semibold text-text-900">Clasificación de almacenamiento</h3>
      {filas.length === 0 ? (
        <p className="text-sm text-text-600">Sin mercancía pendiente de ubicar.</p>
      ) : (
        <div className="space-y-4">
          {filas.map((row) => (
            <FilaClasificacion
              key={`${row.receipt_id}-${row.product_id}`}
              row={row}
              importacionId={importacionId}
              onClasificar={() => clasificar(row)}
              onGenerarEtiqueta={() => generarEtiqueta(row)}
              onDescargarEtiqueta={(fileId, fileName, reference) => descargarEtiqueta(row, reference, fileId, fileName)}
              onImprimirEtiqueta={(fileId, reference) => imprimirEtiqueta(row, reference, fileId)}
              onUbicar={(ubicacion, cantidad) => ubicar(row, ubicacion, cantidad)}
            />
          ))}
        </div>
      )}
    </section>
  );
}

function FilaClasificacion({
  row,
  importacionId,
  onClasificar,
  onGenerarEtiqueta,
  onDescargarEtiqueta,
  onImprimirEtiqueta,
  onUbicar,
}: {
  row: AlmacenamientoRespuesta["rows"][number];
  importacionId: string;
  onClasificar: () => Promise<void>;
  onGenerarEtiqueta: () => Promise<void>;
  onDescargarEtiqueta: (fileId: string, fileName: string, reference: string) => Promise<void>;
  onImprimirEtiqueta: (fileId: string, reference: string) => Promise<void>;
  onUbicar: (ubicacion: string, cantidad: string) => Promise<void>;
}): React.JSX.Element {
  const [ubicacion, setUbicacion] = useState("");
  const [cantidad, setCantidad] = useState(row.pending_base ?? "");
  const classification = row.classification;
  const labelPolicy = classification?.label_policy;

  const etiquetaTexto = labelPolicy === "REQUIRED"
    ? "Etiqueta requerida"
    : labelPolicy === "OPTIONAL"
      ? "Etiqueta opcional"
      : labelPolicy === "NOT_REQUIRED"
        ? "Etiqueta no requerida"
        : null;

  return (
    <div role="group" aria-label={`${row.product_name} · ${row.receipt_code}`} className="rounded-md border border-border-default bg-surface-0 p-4">
      <div className="mb-2 text-sm">
        <span className="font-medium">{row.product_name}</span>{" "}
        <span className="text-text-600">· Recepción {row.receipt_code} · Pendiente: {row.pending_base ?? "—"}</span>
      </div>
      <p className="mb-2 text-sm text-text-600">{textoPolitica(row.policy.mode)}</p>
      <p className="mb-2 text-sm text-text-600">{textoPerfil(row)}</p>

      <div role="status" className="mb-2 text-sm text-text-900">
        {!classification ? (
          "Sin clasificar"
        ) : (
          <>
            {classification.result === "CLASSIFIED" ? (
              <>
                <p>Zona determinada: {classification.target_label}</p>
                <p>Regla: {classification.rule_code} · {classification.rule_name}</p>
              </>
            ) : classification.result === "NO_RULE" ? (
              <p>No existe una regla de almacenamiento aplicable</p>
            ) : classification.result === "AMBIGUOUS" ? (
              <p>Clasificación ambigua: revise las reglas</p>
            ) : null}
            {classification.stale ? <p>La regla cambió: vuelva a clasificar</p> : null}
          </>
        )}
      </div>

      {classification ? (
        <>
          {classification.reasons.length > 0 ? (
            <ul aria-label="Razones de la clasificación" className="mb-2 list-disc pl-5 text-sm text-text-700">
              {classification.reasons.map((reason, index) => (
                <li key={index}>{reason}</li>
              ))}
            </ul>
          ) : null}
          {classification.missing_criteria.length > 0 ? (
            <p className="mb-2 text-sm text-text-700">
              Faltan datos: {classification.missing_criteria.join(", ")}
            </p>
          ) : null}
        </>
      ) : null}

      {etiquetaTexto ? <p className="mb-2 text-sm text-text-700">{etiquetaTexto}</p> : null}

      <div className="mb-3 flex flex-wrap gap-3">
        <Autorizado operacion={["POST", `/importaciones/${importacionId}/storage/classify`]}>
          <AsyncButton type="button" variant="primary" onClick={() => onClasificar()}>
            {classification ? "Volver a clasificar" : "Clasificar"}
          </AsyncButton>
        </Autorizado>

        {classification && (labelPolicy === "REQUIRED" || labelPolicy === "OPTIONAL") ? (
          <Autorizado operacion={["POST", `/importaciones/${importacionId}/storage/labels`]}>
            <AsyncButton type="button" variant="secondary" onClick={() => onGenerarEtiqueta()}>
              Generar etiqueta
            </AsyncButton>
          </Autorizado>
        ) : null}

        {row.labels.map((label) => (
          <div key={label.id} className="flex gap-2">
            <Autorizado operacion={["GET", `/importaciones/${importacionId}/storage/labels/${label.id}/pdf`]}>
              <AsyncButton type="button" variant="secondary" onClick={() => onDescargarEtiqueta(label.id, label.file_name, label.reference)}>
                Descargar {label.reference}
              </AsyncButton>
            </Autorizado>
            <Autorizado operacion={["GET", `/importaciones/${importacionId}/storage/labels/${label.id}/pdf`]}>
              <AsyncButton type="button" variant="secondary" onClick={() => onImprimirEtiqueta(label.id, label.reference)}>
                Imprimir {label.reference}
              </AsyncButton>
            </Autorizado>
          </div>
        ))}
      </div>

      {row.blocking_reason ? (
        <p role="status" className="mb-3 text-sm text-warning-700">{row.blocking_reason}</p>
      ) : null}

      <div className="grid grid-cols-2 gap-3">
        <FormField label="Ubicación de destino" required>
          <select
            className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
            value={ubicacion}
            onChange={(e) => setUbicacion(e.target.value)}
          >
            <option value="" disabled>
              Selecciona una ubicación
            </option>
            {row.candidates.map((candidate) => (
              <option key={candidate.id} value={candidate.id}>
                {candidate.code} · {candidate.path}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Cantidad" required>
          <TextInput
            value={cantidad}
            onChange={(e) => setCantidad(e.target.value)}
          />
        </FormField>
      </div>
      <div className="mt-3">
        <Autorizado operacion={["POST", `/importaciones/${importacionId}/storage/putaway`]}>
          <AsyncButton
            type="button"
            variant="primary"
            disabled={!row.can_putaway || !ubicacion}
            onClick={() => onUbicar(ubicacion, cantidad)}
          >
            Ubicar {row.product_name}
          </AsyncButton>
        </Autorizado>
      </div>
    </div>
  );
}
