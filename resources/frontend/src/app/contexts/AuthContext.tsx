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
  useRef,
  useState,
  type ReactNode,
} from "react";

import { apiFetch, requestSessionRefresh, setAccessToken, setRefreshHandler } from "@/api/client";
import type { AuthenticatedLogin, LoginResponse, UserInfo } from "@/api/types";

interface AuthContextValue {
  user: UserInfo | null;
  accessToken: string | null;
  permissions: string[];
  tenantPermissions: string[];
  isAuthenticated: boolean;
  isReady: boolean;
  login: (tenantCode: string, username: string, password: string) => Promise<LoginResponse>;
  /** Completa un login pendiente de MFA una vez verificado/confirmado el segundo factor. */
  completeLogin: (data: AuthenticatedLogin) => void;
  logout: () => Promise<void>;
  refreshSession: () => Promise<boolean>;
  reloadMe: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }): React.JSX.Element {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [accessToken, setToken] = useState<string | null>(null);
  const [permissions, setPermissions] = useState<string[]>([]);
  const [tenantPermissions, setTenantPermissions] = useState<string[]>([]);
  // true una vez completado el intento inicial de restaurar sesión.
  const [isReady, setReady] = useState(false);

  // Carga usuario + permisos efectivos (KAUD-004: guard real de UI; el backend
  // sigue siendo la autoridad).
  const loadMe = useCallback(async (): Promise<void> => {
    try {
      const data = await apiFetch<{ user: UserInfo & { permissions?: string[] }; permissions: string[]; tenant_permissions?: string[] }>("/auth/me");
      setUser(data.user);
      setPermissions(data.permissions ?? []);
      setTenantPermissions(data.tenant_permissions ?? []);
    } catch {
      // sin sesión válida: se limpia vía refreshSession
    }
  }, []);

  const login = useCallback(async (tenantCode: string, username: string, password: string) => {
    const data = await apiFetch<LoginResponse>("/auth/login", {
      method: "POST",
      body: { tenant_code: tenantCode, username, password },
    });
    if (data.status === "AUTHENTICATED") {
      setAccessToken(data.access_token);
      setToken(data.access_token);
      setUser(data.user);
      void loadMe();
    }
    return data;
  }, [loadMe]);

  const completeLogin = useCallback((data: AuthenticatedLogin): void => {
    setAccessToken(data.access_token);
    setToken(data.access_token);
    setUser(data.user);
    void loadMe();
  }, [loadMe]);

  const logout = useCallback(async () => {
    try {
      await apiFetch("/auth/logout", { method: "POST" });
    } finally {
      setAccessToken(null);
      setToken(null);
      setUser(null);
      setPermissions([]);
      setTenantPermissions([]);
    }
  }, []);

  // La carga del usuario que puso en marcha la última renovación.
  const cargaDeUsuario = useRef<Promise<void>>(Promise.resolve());

  const refreshSession = useCallback(async (): Promise<boolean> => {
    try {
      const data = await apiFetch<{ access_token: string }>("/auth/refresh", { method: "POST" });
      setAccessToken(data.access_token);
      setToken(data.access_token);
      cargaDeUsuario.current = loadMe();
      return true;
    } catch {
      setAccessToken(null);
      setToken(null);
      setUser(null);
      setPermissions([]);
      setTenantPermissions([]);
      return false;
    }
  }, [loadMe]);

  // Renovación automática ante 401 (access token expirado): apiFetch renueva la
  // sesión y reintenta la petición sin recargar la página (ADR-004).
  //
  // Se registra **antes** de restaurar: el orden importa, porque la
  // restauración inicial pasa por la misma puerta y necesita encontrar el
  // manejador ya puesto.
  useEffect(() => {
    setRefreshHandler(refreshSession);
    return () => setRefreshHandler(null);
  }, [refreshSession]);

  // Restaurar sesión al recargar. Va por `requestSessionRefresh`, no por
  // `refreshSession` directamente: el refresh token es de un solo uso y dos
  // renovaciones simultáneas con la misma cookie dejan a la segunda con la
  // sesión ya revocada (401). Compartiendo la petición en vuelo, la segunda
  // espera a la primera en lugar de competir con ella.
  //
  // La sesión no está restaurada hasta que se sabe de quién es. Con el token y
  // todavía sin el usuario, `RouteGuard` veía «listo y sin sesión», mandaba a
  // /login y, al llegar el usuario, el login mandaba a Inicio: recargar una
  // pantalla llevaba a otra.
  useEffect(() => {
    void requestSessionRefresh()
      .then(() => cargaDeUsuario.current)
      .finally(() => setReady(true));
  }, [refreshSession]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      accessToken,
      permissions,
      tenantPermissions,
      isAuthenticated: Boolean(user && accessToken),
      isReady,
      login,
      completeLogin,
      logout,
      refreshSession,
      reloadMe: loadMe,
    }),
    [
      user,
      accessToken,
      permissions,
      tenantPermissions,
      isReady,
      login,
      completeLogin,
      logout,
      refreshSession,
      loadMe,
    ],
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
