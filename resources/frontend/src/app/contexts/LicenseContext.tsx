/**
 * Contexto global de licencia (FR-001-067, DOC-08 §15.3).
 * Informa FULL_ACCESS/RENEWAL_NOTICE/CRITICAL_RENEWAL_NOTICE/READ_ONLY.
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
import type { LicenseStatus } from "@/api/types";

export const LICENSE_BLOCKS_WRITE = new Set([
  "READ_ONLY",
  "SECURITY_SUSPENSION",
]);

interface LicenseContextValue {
  status: LicenseStatus | null;
  mode: LicenseStatus["mode"] | null;
  loading: boolean;
  blocksWrite: boolean;
  refresh: () => Promise<void>;
}

const LicenseContext = createContext<LicenseContextValue | null>(null);

export function LicenseProvider({ children }: { children: ReactNode }): React.JSX.Element {
  const [status, setStatus] = useState<LicenseStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const data = await apiFetch<LicenseStatus>("/license/status");
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
