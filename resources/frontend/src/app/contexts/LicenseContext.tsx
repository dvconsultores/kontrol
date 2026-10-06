/**
 * Contexto global de licencia (FR-001-067, DOC-08 §15.3).
 * Informa FULL_ACCESS/RENEWAL_NOTICE/CRITICAL_RENEWAL_NOTICE/READ_ONLY a partir del contrato
 * mínimo pre-sesión de `GET /license/status` (FR-010-102/112): solo `mode` y `license_url`.
 * El reloj del navegador nunca decide el estado (FR-001-056).
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { apiFetch } from "@/api/client";
import type { LicensePublicStatus } from "@/api/types";

export const LICENSE_BLOCKS_WRITE = new Set([
  "READ_ONLY",
  "SECURITY_SUSPENSION",
]);

/** El permiso que gobierna leer el detalle de la licencia: «Mi licencia», su entrada de menú y el enlace del aviso. */
export const PERMISO_DE_LICENCIA = "license:view";

interface LicenseContextValue {
  status: LicensePublicStatus | null;
  mode: LicensePublicStatus["mode"] | null;
  loading: boolean;
  blocksWrite: boolean;
  refresh: () => Promise<void>;
}

const LicenseContext = createContext<LicenseContextValue | null>(null);

export function LicenseProvider({ children }: { children: ReactNode }): React.JSX.Element {
  const [status, setStatus] = useState<LicensePublicStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const data = await apiFetch<LicensePublicStatus>("/license/status");
      setStatus(data);
    } catch {
      setStatus(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const value = useMemo<LicenseContextValue>(
    () => ({
      status,
      mode: status?.mode ?? null,
      loading,
      blocksWrite: status ? LICENSE_BLOCKS_WRITE.has(status.mode) : false,
      refresh,
    }),
    [status, loading, refresh],
  );

  return <LicenseContext.Provider value={value}>{children}</LicenseContext.Provider>;
}

export function useLicense(): LicenseContextValue {
  const ctx = useContext(LicenseContext);
  if (!ctx) {
    throw new Error("useLicense debe usarse dentro de <LicenseProvider>");
  }
  return ctx;
}
