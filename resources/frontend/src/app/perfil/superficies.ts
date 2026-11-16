/**
 * Superficies de KONTROL Gobierno (Spec 004 delta §5 · OD-LICACT-01).
 * El perfil de instalación viene firmado por derechos y decide qué superficies
 * son visibles. La autoridad de pantalla sigue mandando pantalla a pantalla;
 * esto es solo el mapa ruta → superficie para el guard de UI y el menú.
 */
export type Superficie = "SHARED" | "GOVERNMENT" | "ENTERPRISE";

export type PerfilDeInstalacion = "GOBIERNO" | "MIXTO" | "EMPRESA";

export type EstadoDePerfil =
  | { estado: "RESOLVIENDO" }
  | { estado: "RESUELTO"; perfil: PerfilDeInstalacion }
  | { estado: "ERROR" };

/** mapa exhaustivo; la guarda de inventario de superficies.test.ts exige una clave por segmento. */
export const SUPERFICIE_POR_SEGMENTO: Readonly<Record<string, Superficie>> = {
  gobierno: "GOVERNMENT", // superficie exclusiva del módulo de Gobierno
  organizacion: "ENTERPRISE", // estructura organizativa empresarial
  maestros: "ENTERPRISE", // catálogos maestros empresariales
  inventario: "ENTERPRISE", // kardex y control de existencias
  compras: "ENTERPRISE", // proceso de compras y aprovisionamiento
  ventas: "ENTERPRISE", // proceso de ventas y pedidos
  tesoreria: "ENTERPRISE", // gestión de tesorería y cajas
  fiscal: "ENTERPRISE", // emisión fiscal y tributaria
  regulatorio: "ENTERPRISE", // cumplimiento regulatorio empresarial
  comercial: "ENTERPRISE", // listas de precios y actividad comercial
  reportes: "ENTERPRISE", // reportes privados de negocio
  homologacion: "ENTERPRISE", // homologación de productos empresariales
  aprobaciones: "ENTERPRISE", // motor de aprobaciones de compras y ventas
  "mi-licencia": "SHARED", // licencia de instalación visible para todos
  notificaciones: "SHARED", // bandeja de notificaciones compartida
  tareas: "SHARED", // tareas operativas compartidas
  alertas: "SHARED", // alertas de contratos de Gobierno y empresa
  documentos: "SHARED", // servicio documental compartido
  licenciamiento: "SHARED", // licenciamiento de instalación compartido
  seguridad: "SHARED", // gestión de seguridad compartida
  auditoria: "SHARED", // auditoría usada también por Gobierno
  diagnostico: "SHARED", // diagnóstico del sistema compartido
  forbidden: "SHARED", // pantalla de acceso denegado compartida
  "cambiar-contrasena": "SHARED", // cambio de contraseña compartido
};

export function superficieDeRuta(ruta: string): Superficie {
  const sinQueryYHash = ruta.split(/[?#]/, 1)[0] ?? "";
  const primerSegmento = sinQueryYHash.split("/").find((segmento) => segmento.length > 0);
  if (primerSegmento === undefined) {
    return "SHARED";
  }
  return SUPERFICIE_POR_SEGMENTO[primerSegmento] ?? "SHARED";
}

export function superficieVisible(perfil: EstadoDePerfil, superficie: Superficie): boolean {
  if (superficie === "SHARED") {
    return true;
  }
  // fail-closed: resolviendo o en error solo se ve lo compartido; un error nunca significa Enterprise.
  if (perfil.estado !== "RESUELTO") {
    return false;
  }
  switch (perfil.perfil) {
    case "GOBIERNO":
      return superficie === "GOVERNMENT";
    case "MIXTO":
      return superficie === "GOVERNMENT" || superficie === "ENTERPRISE";
    case "EMPRESA":
      return superficie === "ENTERPRISE";
  }
}
