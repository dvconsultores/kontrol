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

import { apiFetch, setAccessToken, setRefreshHandler } from "@/api/client";
import type { LoginResponse, UserInfo } from "@/api/types";

interface AuthContextValue {
  user: UserInfo | null;
  accessToken: string | null;
  permissions: string[];
  isAuthenticated: boolean;
  isReady: boolean;
  login: (tenantCode: string, username: string, password: string) => Promise<LoginResponse>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<boolean>;
  hasPermission: (permission: string) => boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }): React.JSX.Element {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [accessToken, setToken] = useState<string | null>(null);
  const [permissions, setPermissions] = useState<string[]>([]);
  // true una vez completado el intento inicial de restaurar sesión.
  const [isReady, setReady] = useState(false);

  // Carga usuario + permisos efectivos (KAUD-004: guard real de UI; el backend
  // sigue siendo la autoridad).
  const loadMe = useCallback(async (): Promise<void> => {
    try {
      const data = await apiFetch<{ user: UserInfo & { permissions?: string[] }; permissions: string[] }>("/auth/me");
      setUser(data.user);
      setPermissions(data.permissions ?? []);
    } catch {
      // sin sesión válida: se limpia vía refreshSession
    }
  }, []);

  const login = useCallback(async (tenantCode: string, username: string, password: string) => {
    const data = await apiFetch<LoginResponse>("/auth/login", {
      method: "POST",
      body: { tenant_code: tenantCode, username, password },
    });
    setAccessToken(data.access_token);
    setToken(data.access_token);
    setUser(data.user);
    void loadMe();
    return data;
  }, [loadMe]);

  const logout = useCallback(async () => {
    try {
      await apiFetch("/auth/logout", { method: "POST" });
    } finally {
      setAccessToken(null);
      setToken(null);
      setUser(null);
      setPermissions([]);
    }
  }, []);

  const refreshSession = useCallback(async (): Promise<boolean> => {
    try {
      const data = await apiFetch<{ access_token: string }>("/auth/refresh", { method: "POST" });
      setAccessToken(data.access_token);
      setToken(data.access_token);
      void loadMe();
      return true;
    } catch {
      setAccessToken(null);
      setToken(null);
      setUser(null);
      setPermissions([]);
      return false;
    }
  }, [loadMe]);

  // Restaurar sesión al recargar (refresh una sola vez); isReady evita que el
  // router quede esperando indefinidamente cuando no hay sesión.
  useEffect(() => {
    void refreshSession().finally(() => setReady(true));
  }, [refreshSession]);

  // Renovación automática ante 401 (access token expirado): apiFetch renueva la
  // sesión y reintenta la petición sin recargar la página (ADR-004).
  useEffect(() => {
    setRefreshHandler(refreshSession);
    return () => setRefreshHandler(null);
  }, [refreshSession]);

  const hasPermission = useCallback(
    (permission: string) => permissions.includes(permission),
    [permissions],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      accessToken,
      permissions,
      isAuthenticated: Boolean(user && accessToken),
      isReady,
      login,
      logout,
      refreshSession,
      hasPermission,
    }),
    [user, accessToken, permissions, isReady, login, logout, refreshSession, hasPermission],
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
