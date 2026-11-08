/** Autoridad única de selección de terceros: búsqueda en servidor y sin truncado. */
import { useCompany } from "@/app/contexts/CompanyContext";
import { AsyncCombobox } from "@/components/AsyncCombobox";

export interface SelectorDeTerceroProps {
  value: string;
  onChange: (id: string) => void;
  role?: "CLIENTE" | "PROVEEDOR" | "TRANSPORTISTA";
  soloActivos?: boolean;
  id?: string;
  "aria-describedby"?: string;
}

export function SelectorDeTercero({
  value,
  onChange,
  role,
  soloActivos,
  id,
  "aria-describedby": describedBy,
}: SelectorDeTerceroProps): React.JSX.Element {
  const { activeCompany } = useCompany();

  return (
    <AsyncCombobox
      id={id}
      aria-describedby={describedBy}
      value={value || null}
      onChange={(v) => onChange(v ?? "")}
      searchUrl="/maestros/terceros"
      resolveUrl="/maestros/terceros"
      scopeKey={activeCompany?.id ?? "sin-empresa"}
      extraParams={{
        ...(role ? { role } : {}),
        ...(soloActivos ? { status: "ACTIVE" } : {}),
      }}
      label="Buscar tercero"
      placeholder="Buscar por código, nombre o RIF…"
    />
  );
}
