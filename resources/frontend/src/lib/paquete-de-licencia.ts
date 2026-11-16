/**
 * Utilidades puras para interpretar el paquete de licencia firmado.
 * El frontend jamás verifica la firma ni usa claves: solo valida la forma
 * del paquete, extrae una vista previa y mapea los errores del servidor.
 */
import { ApiError } from "@/api/client";

export const CODIGO_PAQUETE_INVALIDO = "INVALID_LICENSE_PACKAGE";
export const TAMANO_MAXIMO_DEL_PAQUETE = 256 * 1024;
export const MENSAJE_LECTURA = "No fue posible leer el archivo seleccionado.";

export class PaqueteInvalidoError extends Error {
  code = CODIGO_PAQUETE_INVALIDO;

  constructor(message: string) {
    super(message);
    this.name = "PaqueteInvalidoError";
  }
}

import type { PerfilDeInstalacion } from "@/app/perfil/superficies";
import { modulosDeDerechos, perfilDeModulos } from "@/lib/licencia-presentacion";

export interface PaqueteDeLicencia {
  payload: Record<string, unknown>;
  signature_hex: string;
}

export interface VistaPreviaDeLicencia {
  licenseId: string;
  installationId: string;
  kid: string;
  periodStart: string;
  periodEnd: string;
  revision: string | null;
  minimumVersion: string | null;
  empresas: number | null;
  usuarios: number | null;
  modulos: string[];
  perfil: PerfilDeInstalacion;
}

export function validarArchivoDeLicencia(archivo: {
  name: string;
  type: string;
  size: number;
}): void {
  if (!/\.json$/i.test(archivo.name)) {
    throw new PaqueteInvalidoError("El archivo debe tener extensión .json.");
  }
  if (!["application/json", "text/json", ""].includes(archivo.type)) {
    throw new PaqueteInvalidoError("El tipo del archivo no es JSON.");
  }
  if (archivo.size > TAMANO_MAXIMO_DEL_PAQUETE) {
    throw new PaqueteInvalidoError("El archivo supera el tamaño máximo de 256 KiB.");
  }
  if (archivo.size === 0) {
    throw new PaqueteInvalidoError("El archivo está vacío.");
  }
}

export function contieneClavePrivada(texto: string): boolean {
  return /PRIVATE KEY/i.test(texto);
}

export function interpretarPaquete(texto: string): PaqueteDeLicencia {
  if (contieneClavePrivada(texto)) {
    throw new PaqueteInvalidoError(
      "El archivo contiene material de clave privada y se rechazó. No lo comparta.",
    );
  }

  let raiz: unknown;
  try {
    raiz = JSON.parse(texto);
  } catch {
    throw new PaqueteInvalidoError("El archivo no contiene JSON válido.");
  }

  if (raiz === null || typeof raiz !== "object" || Array.isArray(raiz)) {
    throw new PaqueteInvalidoError(
      "El paquete debe ser un objeto JSON con payload y signature_hex.",
    );
  }

  const objeto = raiz as Record<string, unknown>;
  const payload = objeto.payload;
  if (payload === null || typeof payload !== "object" || Array.isArray(payload)) {
    throw new PaqueteInvalidoError("El paquete no contiene un payload válido.");
  }

  const firma = objeto.signature_hex;
  if (typeof firma !== "string" || firma.trim() === "") {
    throw new PaqueteInvalidoError("El paquete no contiene la firma (signature_hex).");
  }

  const campos = ["license_id", "installation_id", "kid", "period_start", "period_end"];
  for (const campo of campos) {
    const valor = (payload as Record<string, unknown>)[campo];
    if (typeof valor !== "string" || valor.trim() === "") {
      throw new PaqueteInvalidoError(`El payload no contiene ${campo}.`);
    }
  }

  return { payload: payload as Record<string, unknown>, signature_hex: firma };
}

export function vistaPrevia(p: PaqueteDeLicencia): VistaPreviaDeLicencia {
  const license_id = p.payload.license_id as string;
  const installation_id = p.payload.installation_id as string;
  const kid = p.payload.kid as string;
  const period_start = p.payload.period_start as string;
  const period_end = p.payload.period_end as string;

  const revision: string | null =
    typeof p.payload.revision === "number" || typeof p.payload.revision === "string"
      ? String(p.payload.revision)
      : null;

  const minimumVersion: string | null =
    typeof p.payload.minimum_version === "string" ? p.payload.minimum_version : null;

  let empresas: number | null = null;
  let usuarios: number | null = null;
  if (
    p.payload.entitlements !== null &&
    typeof p.payload.entitlements === "object" &&
    !Array.isArray(p.payload.entitlements)
  ) {
    const ent = p.payload.entitlements as Record<string, unknown>;
    if (typeof ent.companies === "number") {
      empresas = ent.companies;
    }
    if (typeof ent.users === "number") {
      usuarios = ent.users;
    }
  }

  const modulos = modulosDeDerechos(p.payload.entitlements);

  return {
    licenseId: license_id,
    installationId: installation_id,
    kid,
    periodStart: period_start,
    periodEnd: period_end,
    revision,
    minimumVersion,
    empresas,
    usuarios,
    modulos,
    perfil: perfilDeModulos(modulos),
  };
}

export function mensajeDeErrorDeCarga(error: unknown): string {
  if (error instanceof PaqueteInvalidoError) {
    return `${error.message} (${CODIGO_PAQUETE_INVALIDO})`;
  }
  return MENSAJE_LECTURA;
}

export function mensajeDeErrorDeActivacion(error: unknown): string {
  if (error instanceof PaqueteInvalidoError) {
    return `${error.message} (${CODIGO_PAQUETE_INVALIDO})`;
  }
  if (!(error instanceof ApiError)) {
    return "No fue posible conectar con KONTROL para activar la licencia.";
  }

  if (error.status === 401) {
    return `La sesión venció. Inicie sesión nuevamente para activar la licencia. (${error.code})`;
  }

  if (error.code === "REAUTH_REQUIRED") {
    return "No se confirmó su identidad; la licencia no se activó. (REAUTH_REQUIRED)";
  }

  if (error.code === "PERMISSION_DENIED") {
    return "No tiene permiso para activar licencias. Se requiere license:create. (PERMISSION_DENIED)";
  }
  if (error.status === 403 && !error.code) {
    return "No tiene permiso para activar licencias. Se requiere license:create. (PERMISSION_DENIED)";
  }

  const porCodigo: Record<string, string> = {
    LICENSE_SIGNATURE_INVALID: "La firma de la licencia no es válida.",
    LICENSE_SIGNING_KID_UNKNOWN:
      "La licencia está firmada con una clave que esta instalación no reconoce.",
    LICENSE_SIGNING_KID_MISSING: "La licencia no indica la clave de firma (kid).",
    LICENSE_INSTALLATION_MISMATCH: "Esta licencia fue emitida para otra instalación.",
    LICENSE_PERIOD_DOWNGRADE: "La licencia corresponde a un período anterior al vigente.",
    LICENSE_PERIOD_CONFLICT: "El período de la licencia no es comparable con el vigente.",
    LICENSE_INVALID_REVISION: "La revisión de la licencia no es válida.",
    LICENSE_REVISION_DOWNGRADE: "La licencia tiene una revisión anterior a la vigente.",
    LICENSE_REVISION_CONFLICT: "Ya existe otra licencia con la misma revisión.",
    LICENSE_LEGACY_REISSUE_REQUIRES_REVISION:
      "La reemisión requiere una revisión firmada por la autoridad.",
    LICENSE_LEGACY_AFTER_REVISION:
      "No se admite una licencia sin revisión después de una revisionada.",
    LICENSE_CURRENT_ARTIFACT_INVALID:
      "La licencia vigente no cumple el contrato; contacte al propietario de KONTROL.",
    LICENSE_INVALID_MINIMUM_VERSION: "La versión mínima de la licencia no es válida.",
    LICENSE_MINIMUM_VERSION_INCOMPATIBLE:
      "La licencia exige una versión de KONTROL más reciente que la instalada.",
  };
  if (error.code in porCodigo) {
    return `${porCodigo[error.code]} (${error.code})`;
  }

  if (error.code.startsWith("LICENSE_TRUST_ANCHOR_")) {
    return `La instalación no tiene configurada la clave pública del propietario. (${error.code})`;
  }

  if (error.status >= 500) {
    const solicitud = error.requestId ? ` · solicitud ${error.requestId}` : "";
    return `KONTROL no pudo activar la licencia. Intente más tarde. (${error.code})${solicitud}`;
  }

  return `${error.message} (${error.code})`;
}
