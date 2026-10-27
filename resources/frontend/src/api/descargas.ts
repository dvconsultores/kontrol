/** Descarga autenticada de archivos del backend (Spec 009, 02E): el token viaja solo en la cabecera de la petición; el navegador recibe un `blob:` que se revoca tras el clic. */
import { ApiError, apiFetch, type ArchivoDescargado } from "@/api/client";

const NOMBRE_MAXIMO = 150;

function sanearCandidato(candidato: string): string {
  const sinRuta = candidato.slice(Math.max(candidato.lastIndexOf("/"), candidato.lastIndexOf("\\")) + 1);
  const sinControlNiComillas = Array.from(sinRuta)
    .filter((c) => {
      const n = c.codePointAt(0) ?? 0;
      return n > 0x1f && n !== 0x7f && c !== '"';
    })
    .join("")
    .trim()
    .replace(/^\.+/, "");
  return sinControlNiComillas.slice(0, NOMBRE_MAXIMO);
}

export function nombreSeguro(contentDisposition: string | null, reserva: string): string {
  const candidato = contentDisposition
    ? extraerNombreDeCabecera(contentDisposition) ?? reserva
    : reserva;
  const saneado = sanearCandidato(candidato);
  return saneado || sanearCandidato(reserva) || "descarga";
}

function extraerNombreDeCabecera(contentDisposition: string): string | null {
  const utf8 = /filename\*\s*=\s*UTF-8''([^;]+)/i.exec(contentDisposition);
  if (utf8?.[1]) {
    try {
      return decodeURIComponent(utf8[1]);
    } catch {
      // ignorar y continuar con filename normal
    }
  }

  const normal = /filename\s*=\s*(?:"([^"]*)"|([^;]+))/i.exec(contentDisposition);
  return normal?.[1] ?? normal?.[2] ?? null;
}

export function mensajeDeDescarga(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "PERMISSION_DENIED") {
      return "No tiene permiso para descargar este archivo.";
    }
    if (error.code === "COMPANY_SCOPE_FORBIDDEN") {
      return "No tiene esa autoridad en esta empresa.";
    }
    if (
      error.status === 404 ||
      error.code.endsWith("_NOT_FOUND") ||
      error.code === "EXPORT_FILE_MISSING"
    ) {
      return "El archivo ya no existe o no está disponible.";
    }
  }

  if (error instanceof TypeError) {
    return "No hay conexión con el servidor. Inténtelo de nuevo.";
  }

  return "No fue posible descargar el archivo.";
}

export async function descargarArchivo(ruta: string, reserva: string): Promise<string> {
  const { blob, contentDisposition } = await apiFetch<ArchivoDescargado>(ruta, {
    responseType: "archivo",
  });

  const nombre = nombreSeguro(contentDisposition, reserva);
  const url = URL.createObjectURL(blob);

  try {
    const ancla = document.createElement("a");
    ancla.href = url;
    ancla.download = nombre;
    ancla.rel = "noopener";
    document.body.appendChild(ancla);
    ancla.click();
    ancla.remove();
  } finally {
    URL.revokeObjectURL(url);
  }

  return nombre;
}
