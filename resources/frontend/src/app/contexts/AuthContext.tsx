/**
 * Contexto de autenticación (ADR-004).
 * Guarda el access token en memoria; el refresh vive en cookie HttpOnly.
 * Expone login/logout/refresh y el usuario actual.
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

import { apiFetch, setAccessToken } from "@/api/client";
import type { LoginResponse, UserInfo } from "@/api/types";

interface AuthContextValue {
  user: UserInfo | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  login: (tenantCode: string, username: string, password: string) => Promise<LoginResponse>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }): React.JSX.Element {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [accessToken, setToken] = useState<string | null>(null);

  const login = useCallback(async (tenantCode: string, username: string, password: string) => {
    const data = await apiFetch<LoginResponse>("/auth/login", {
      method: "POST",
      body: { tenant_code: tenantCode, username, password },
    });
    setAccessToken(data.access_token);
    setToken(data.access_token);
    setUser(data.user);
    return data;
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiFetch("/auth/logout", { method: "POST" });
    } finally {
      setAccessToken(null);
      setToken(null);
      setUser(null);
    }
  }, []);

  const refreshSession = useCallback(async (): Promise<boolean> => {
    try {
      const data = await apiFetch<{ access_token: string }>("/auth/refresh", { method: "POST" });
      setAccessToken(data.access_token);
      setToken(data.access_token);
      return true;
    } catch {
      setAccessToken(null);
      setToken(null);
      setUser(null);
      return false;
    }
  }, []);

  // Restaurar sesión al recargar (refresh una sola vez).
  useEffect(() => {
    void refreshSession();
  }, [refreshSession]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      accessToken,
      isAuthenticated: Boolean(user && accessToken),
      login,
      logout,
      refreshSession,
    }),
    [user, accessToken, login, logout, refreshSession],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  }
  return ctx;
}
