/**
 * Contexto de empresa activa y alcance (FR-001-030/032, ADR-011).
 * La empresa activa filtra cada consulta; el backend valida el alcance.
 * El alcance se persiste en localStorage para conservarse entre recargas.
 */
import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import type { CompanySummary } from "@/api/types";

const STORAGE_KEY = "kontrol.active-company.v1";

interface CompanyContextValue {
  activeCompany: CompanySummary | null;
  setActiveCompany: (company: CompanySummary | null) => void;
}

const CompanyContext = createContext<CompanyContextValue | null>(null);

function readStoredCompany(): CompanySummary | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as CompanySummary;
    if (parsed && typeof parsed.id === "string" && typeof parsed.legal_name === "string") {
      return parsed;
    }
    return null;
  } catch {
    return null;
  }
}

export function CompanyProvider({ children }: { children: ReactNode }): React.JSX.Element {
  const [activeCompany, setActiveCompany] = useState<CompanySummary | null>(readStoredCompany);

  // Persistir el alcance elegido; limpiar si se desactiva.
  useEffect(() => {
    try {
      if (activeCompany) {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(activeCompany));
      } else {
        window.localStorage.removeItem(STORAGE_KEY);
      }
    } catch {
      // Almacenamiento no disponible (privado/sandbox): el alcance vive solo en memoria.
    }
  }, [activeCompany]);

  const value = useMemo(() => ({ activeCompany, setActiveCompany }), [activeCompany, setActiveCompany]);

  return <CompanyContext.Provider value={value}>{children}</CompanyContext.Provider>;
}

export function useCompany(): CompanyContextValue {
  const ctx = useContext(CompanyContext);
  if (!ctx) {
    throw new Error("useCompany debe usarse dentro de <CompanyProvider>");
  }
  return ctx;
}
