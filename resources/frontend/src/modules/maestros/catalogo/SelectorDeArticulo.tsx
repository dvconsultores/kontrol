/** Autoridad única de selección de artículos del catálogo (FR-002-043): búsqueda en servidor y sin truncado. */
import { useCompany } from "@/app/contexts/CompanyContext";
import { AsyncCombobox } from "@/components/AsyncCombobox";

export interface SelectorDeArticuloProps {
  value: string;
  onChange: (id: string) => void;
  /** Solo los procesos de inventario lo fijan: su backend exige PRODUCT. */
  itemType?: "PRODUCT" | "SERVICE";
  id?: string;
  "aria-describedby"?: string;
}

export function SelectorDeArticulo({
  value,
  onChange,
  itemType,
  id,
  "aria-describedby": describedBy,
}: SelectorDeArticuloProps): React.JSX.Element {
  const { activeCompany } = useCompany();

  return (
    <AsyncCombobox
      id={id}
      aria-describedby={describedBy}
      value={value || null}
      onChange={(v) => onChange(v ?? "")}
      searchUrl="/maestros/catalogos/items/search"
      resolveUrl="/maestros/catalogos/items"
      scopeKey={activeCompany?.id ?? "sin-empresa"}
      itemType={itemType}
      label="Buscar artículo"
      placeholder="Buscar por código o nombre…"
    />
  );
}
