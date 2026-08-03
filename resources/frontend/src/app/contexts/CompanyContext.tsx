/**
 * Contexto de empresa activa y alcance (FR-001-030/032, ADR-011).
 * La empresa activa filtra cada consulta; el backend valida el alcance.
 */
import {
  createContext,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import type { CompanySummary } from "@/api/types";

interface CompanyContextValue {
  activeCompany: CompanySummary | null;
  setActiveCompany: (company: CompanySummary | null) => void;
}

const CompanyContext = createContext<CompanyContextValue | null>(null);

export function CompanyProvider({ children }: { children: ReactNode }): React.JSX.Element {
  const [activeCompany, setActiveCompany] = useState<CompanySummary | null>(null);

  const value = useMemo(() => ({ activeCompany, setActiveCompany }), [activeCompany]);

  return <CompanyContext.Provider value={value}>{children}</CompanyContext.Provider>;
}

export function useCompany(): CompanyContextValue {
  const ctx = useContext(CompanyContext);
  if (!ctx) {
    throw new Error("useCompany debe usarse dentro de <CompanyProvider>");
  }
  return ctx;
}
