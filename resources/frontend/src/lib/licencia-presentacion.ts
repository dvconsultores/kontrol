// Spec 004 · presentación humana de la licencia.
import type { PerfilDeInstalacion } from "@/app/perfil/superficies";

export const TOKENS_EMPRESARIALES: readonly string[] = ["ventas","compras","inventario","tesoreria","fiscal","regulatorio","reportes"];

export function etiquetaDeModo(modo: string): string {
  switch (modo) {
    case "PENDING":
      return "Pendiente de activación";
    case "FULL_ACCESS":
      return "Acceso completo";
    case "RENEWAL_NOTICE":
      return "Renovación próxima";
    case "CRITICAL_RENEWAL_NOTICE":
      return "Renovación crítica";
    case "READ_ONLY":
      return "Solo consulta";
    case "SECURITY_SUSPENSION":
      return "Suspensión de seguridad";
    default:
      return modo.replaceAll("_", " ");
  }
}

export function etiquetaDePerfil(perfil: PerfilDeInstalacion): string {
  switch (perfil) {
    case "GOBIERNO":
      return "KONTROL Gobierno";
    case "MIXTO":
      return "KONTROL Mixto";
    case "EMPRESA":
      return "KONTROL Enterprise";
  }
}

export function etiquetaDeModulo(token: string): string {
  switch (token) {
    case "gobierno":
      return "Gobierno";
    case "ventas":
      return "Ventas";
    case "compras":
      return "Compras";
    case "inventario":
      return "Inventario";
    case "tesoreria":
      return "Tesorería";
    case "fiscal":
      return "Fiscal";
    case "regulatorio":
      return "Regulatorio";
    case "reportes":
      return "Reportes";
    default:
      return token;
  }
}

export function modulosDeDerechos(entitlements: unknown): string[] {
  if (entitlements !== null && typeof entitlements === "object" && !Array.isArray(entitlements)) {
    const obj = entitlements as Record<string, unknown>;
    const rawModules = obj.modules;
    if (Array.isArray(rawModules)) {
      return rawModules.filter((m): m is string => typeof m === "string");
    }
    if (rawModules !== null && typeof rawModules === "object" && !Array.isArray(rawModules)) {
      return Object.entries(rawModules as Record<string, unknown>)
        .filter(([, activo]) => activo === true)
        .map(([nombre]) => nombre);
    }
  }
  return [];
}

export function perfilDeModulos(modulos: readonly string[]): PerfilDeInstalacion {
  if (modulos.includes("gobierno")) {
    return modulos.some((modulo) => TOKENS_EMPRESARIALES.includes(modulo)) ? "MIXTO" : "GOBIERNO";
  }
  return "EMPRESA";
}

export interface TextosDeActivacion {
  titulo: string;
  descripcion: string;
  seleccionar: string;
  aplicar: string;
  destacada: boolean;
}

export function textosDeActivacion(modo: string): TextosDeActivacion {
  switch (modo) {
    case "PENDING":
      return {
        titulo: "Activar licencia",
        descripcion: "Cargue el archivo JSON firmado emitido para esta instalación.",
        seleccionar: "Seleccionar archivo de licencia",
        aplicar: "Validar y activar licencia",
        destacada: true,
      };
    case "FULL_ACCESS":
      return {
        titulo: "Actualizar o reemplazar licencia",
        descripcion:
          "Importe una nueva licencia firmada para renovar el período, actualizar los derechos o aplicar una revisión emitida por la Autoridad Central.",
        seleccionar: "Seleccionar nueva licencia",
        aplicar: "Validar y aplicar licencia",
        destacada: false,
      };
    case "RENEWAL_NOTICE":
    case "CRITICAL_RENEWAL_NOTICE":
      return {
        titulo: "Renovar licencia",
        descripcion:
          "Importe la licencia renovada emitida por la Autoridad Central para continuar sin interrupciones.",
        seleccionar: "Seleccionar licencia renovada",
        aplicar: "Validar y aplicar licencia",
        destacada: true,
      };
    case "READ_ONLY":
      return {
        titulo: "Reactivar licencia",
        descripcion:
          "Importe una licencia vigente firmada por la Autoridad Central para recuperar el acceso completo.",
        seleccionar: "Seleccionar licencia vigente",
        aplicar: "Validar y aplicar licencia",
        destacada: true,
      };
    case "SECURITY_SUSPENSION":
      return {
        titulo: "Restablecer licencia válida",
        descripcion:
          "Importe una licencia válida firmada por la Autoridad Central para levantar la suspensión de seguridad.",
        seleccionar: "Seleccionar licencia válida",
        aplicar: "Validar y aplicar licencia",
        destacada: true,
      };
    default:
      return {
        titulo: "Actualizar o reemplazar licencia",
        descripcion:
          "Importe una nueva licencia firmada para renovar el período, actualizar los derechos o aplicar una revisión emitida por la Autoridad Central.",
        seleccionar: "Seleccionar nueva licencia",
        aplicar: "Validar y aplicar licencia",
        destacada: false,
      };
  }
}
