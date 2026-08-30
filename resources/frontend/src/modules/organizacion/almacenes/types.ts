/** Tipos de la estructura física de almacén (Spec 008).
 *
 * La jerarquía es `Warehouse → Zone? → Aisle? → Rack? → Level? → Location`.
 * Los cuatro tramos intermedios son opcionales **por almacén**: qué tramos usa
 * cada uno lo dice `structure_levels`, no el código.
 */

export const STRUCTURE_LEVELS = ["zone", "aisle", "rack", "level"] as const;
export type StructureLevel = (typeof STRUCTURE_LEVELS)[number];

/** Etiquetas de presentación de los tramos. No son datos de negocio: no
 *  nombran zonas concretas, solo el tipo de tramo. */
export const LEVEL_LABEL: Record<StructureLevel, { singular: string; plural: string; path: string }> = {
  zone: { singular: "Zona", plural: "Zonas", path: "zones" },
  aisle: { singular: "Pasillo", plural: "Pasillos", path: "aisles" },
  rack: { singular: "Rack", plural: "Racks", path: "racks" },
  level: { singular: "Nivel", plural: "Niveles", path: "levels" },
};

export type StructureLevels = Partial<Record<StructureLevel, boolean>>;

export interface Warehouse {
  id: string;
  company_id: string;
  branch_id: string | null;
  code: string;
  name: string;
  warehouse_type: string;
  address: string | null;
  manager_id: string | null;
  description: string | null;
  location_managed: boolean;
  structure_levels: StructureLevels;
  structure_regime: "INITIAL" | "OPERATIONAL";
  declared_levels: StructureLevel[];
  code_policy: string;
  code_pattern: string | null;
  status: string;
  version: number;
  can_delete: boolean;
  delete_blocked_by: Record<string, number> | null;
  allowed_actions: string[];
}

export interface StructureNode {
  id: string;
  level: StructureLevel;
  warehouse_id: string;
  code: string;
  name: string;
  sequence: number;
  description: string | null;
  parent_id: string | null;
  status: string;
  version: number;
  can_delete: boolean;
  delete_blocked_by: Record<string, unknown> | null;
  allowed_actions: string[];
}

export interface NodeRef {
  id: string;
  code: string;
  name: string;
}

export interface WarehouseLocation {
  id: string;
  warehouse_id: string;
  company_id: string;
  code: string;
  name: string | null;
  sequence: number;
  status: string;
  version: number;
  legacy_path: string | null;
  display_path: string;
  can_delete: boolean;
  allowed_actions: string[];
  zone?: NodeRef | null;
  aisle?: NodeRef | null;
  rack?: NodeRef | null;
  level?: NodeRef | null;
  type?: { id: string; code: string; is_storable: boolean } | null;
  capacity?: { units: number | null; weight: number | null; uom: string | null };
  delete_blocked_by?: Record<string, unknown> | null;
}

export interface Paged<T> {
  total: number;
  limit: number;
  offset: number;
  items: T[];
}

export interface CatalogType {
  id: string;
  company_id: string;
  code: string;
  name: string;
  status: string;
  is_storable?: boolean;
  description?: string | null;
}

/** Detalle que acompaña a un bloqueo estructural del backend.
 *
 * El frontend **refleja** este bloqueo; no lo produce ni inventa su texto. */
export interface BlockDetails {
  reason?: string;
  dependencies?: Record<string, unknown>;
  allowed_actions?: string[];
}

export function can(entity: { allowed_actions: string[] }, action: string): boolean {
  return entity.allowed_actions.includes(action);
}

/** Tramos que este almacén declara, en orden canónico. */
export function declaredLevels(warehouse: Pick<Warehouse, "structure_levels">): StructureLevel[] {
  return STRUCTURE_LEVELS.filter((level) => warehouse.structure_levels?.[level] === true);
}
