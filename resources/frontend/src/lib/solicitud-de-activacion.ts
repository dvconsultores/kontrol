/**
 * Utilidades puras para la solicitud de activación de una instalación.
 * Ninguna función usa almacenamiento ni red; la descarga se apoya en URL.createObjectURL.
 */
import type { InstallationRequest } from "@/api/types";

export const CODIGO_SOLICITUD_INVALIDA = "INVALID_INSTALLATION_REQUEST";

export class SolicitudInvalidaError extends Error {
  code: string = CODIGO_SOLICITUD_INVALIDA;

  constructor(message = "La solicitud de activación no es válida") {
    super(message);
    this.name = "SolicitudInvalidaError";
  }
}

/** Valida una respuesta de solicitud de activación y devuelve el mismo objeto recibido. */
export function validarSolicitud(valor: unknown): InstallationRequest {
  if (valor === null || typeof valor !== "object" || Array.isArray(valor)) {
    throw new SolicitudInvalidaError();
  }

  const candidato = valor as Record<string, unknown>;
  const installationId = candidato.installation_id;
  const publicKey = candidato.public_key;

  if (typeof installationId !== "string" || installationId.trim() === "") {
    throw new SolicitudInvalidaError();
  }
  if (typeof publicKey !== "string" || publicKey.trim() === "") {
    throw new SolicitudInvalidaError();
  }

  return valor as InstallationRequest;
}

/** Serializa la solicitud como JSON legible terminado en salto de línea. */
export function serializarSolicitud(s: InstallationRequest): string {
  return JSON.stringify(s, null, 2) + "\n";
}

/** Devuelve un nombre de archivo seguro para la solicitud de una instalación. */
export function nombreDeArchivoDeSolicitud(installationId: string): string {
  const saneado = installationId
    .replace(/[^A-Za-z0-9._-]/g, "_")
    .replace(/\.{2,}/g, "_")
    .replace(/^[.]+/, "")
    .slice(0, 100);
  const finalId = saneado === "" ? "sin-identificador" : saneado;
  return `kontrol-installation-request-${finalId}.json`;
}

/** Descarga un texto como archivo JSON en el navegador. */
export function descargarTexto(texto: string, nombre: string): void {
  const blob = new Blob([texto], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  try {
    const enlace = document.createElement("a");
    enlace.href = url;
    enlace.download = nombre;
    enlace.rel = "noopener";
    enlace.style.display = "none";
    document.body.appendChild(enlace);
    enlace.click();
    enlace.remove();
  } finally {
    URL.revokeObjectURL(url);
  }
}
