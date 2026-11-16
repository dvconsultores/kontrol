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
  | { estado: "RESUELTO"; perfil: PerfilDeInstalacion };

/** Primer segmento de ruta → superficie (fuente: GOVERNMENT_PRODUCT_INVENTORY.md §3; «reportes» es superficie de reportes privados). */
export const SUPERFICIE_POR_SEGMENTO: Readonly<Record<string, Superficie>> = {
  gobierno: "GOVERNMENT",
  organizacion: "ENTERPRISE",
  maestros: "ENTERPRISE",
  inventario: "ENTERPRISE",
  compras: "ENTERPRISE",
  ventas: "ENTERPRISE",
  tesoreria: "ENTERPRISE",
  fiscal: "ENTERPRISE",
  regulatorio: "ENTERPRISE",
  comercial: "ENTERPRISE",
  reportes: "ENTERPRISE",
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
  if (perfil.estado === "RESOLVIENDO") {
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
