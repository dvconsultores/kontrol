/** Tipos de unidades, presentaciones y conversiones (Spec 011).
 *
 * Las cantidades y factores viajan como **texto**, no como `number`: un
 * `NUMERIC(18,6)` convertido a `Number` en JavaScript perdería precisión, que
 * es exactamente lo que esta Spec existe para evitar.
 */

export const DIMENSIONS = [
  "CANTIDAD", "MASA", "PESO", "VOLUMEN", "LONGITUD", "AREA", "TIEMPO",
] as const;
export type Dimension = (typeof DIMENSIONS)[number];

export const ROUNDING_MODES = [
  { value: "HALF_UP", label: "Medio hacia arriba" },
  { value: "HALF_EVEN", label: "Medio al par" },
  { value: "DOWN", label: "Hacia abajo" },
  { value: "UP", label: "Hacia arriba" },
] as const;

export const DIMENSION_LABEL: Record<string, string> = {
  CANTIDAD: "Cantidad",
  MASA: "Masa",
  PESO: "Peso",
  VOLUMEN: "Volumen",
  LONGITUD: "Longitud",
  AREA: "Área",
  TIEMPO: "Tiempo",
};

export interface Unit {
  id: string;
  code: string;
  name: string;
  symbol: string;
  dimension: string;
  decimals: number;
  rounding_mode: string;
  status: string;
  scope: "GLOBAL" | "COMPANY";
  company_id: string | null;
  version: number;
  can_delete: boolean;
  allowed_actions: string[];
}

export interface PresentationVersion {
  id: string;
  presentation_id: string;
  /** Texto decimal: nunca `number`. */
  factor_to_base: string;
  factor_uom_id: string | null;
  exact_in_base: boolean;
  valid_from: string | null;
  valid_to: string | null;
  status: string;
  is_open: boolean;
  in_use: boolean;
  allowed_actions: string[];
}

export interface Presentation {
  id: string;
  product_id: string;
  company_id: string | null;
  code: string;
  name: string;
  status: string;
  buyable: boolean;
  sellable: boolean;
  storable: boolean;
  dispatchable: boolean;
  barcode: string | null;
  version: number;
  legacy_content: number | null;
  base_unit: { id: string; code: string; symbol: string } | null;
  current_factor: string | null;
  current_version_id: string | null;
  in_use: boolean;
  can_delete: boolean;
  allowed_actions: string[];
}

export interface ConversionPreview {
  quantity: string;
  presentation: { id: string; code: string; label: string } | null;
  factor_applied: string;
  version_id: string | null;
  base_quantity: string;
  base_uom: { id: string; code: string; symbol: string } | null;
  exact: boolean;
  explanation: string;
}

export interface Paged<T> {
  total: number;
  limit: number;
  offset: number;
  items: T[];
}

export function can(entity: { allowed_actions: string[] }, action: string): boolean {
  return entity.allowed_actions.includes(action);
}

/** Formatea un decimal en texto sin pasar por `Number`. */
export function formatDecimal(value: string | null): string {
  if (!value) return "—";
  const [whole, fraction = ""] = value.split(".");
  const trimmed = fraction.replace(/0+$/, "");
  return trimmed ? `${whole},${trimmed}` : whole;
}
