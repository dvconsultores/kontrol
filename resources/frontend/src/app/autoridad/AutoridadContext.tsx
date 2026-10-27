import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
} from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, setAuthorityDenialHandler } from "@/api/client";
import { useAuth } from "@/app/contexts/AuthContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import {
  crearIndice,
  evaluar,
  resolver,
  type Conjuntos,
  type Motivo,
  type Operacion,
} from "./operaciones";

export type AlcanceDeCapacidad = "empresa" | "tenant" | "global";
export type EstadoDeAutoridad = "CARGANDO" | "LISTA" | "ERROR";

export interface AutoridadValue {
  estado: EstadoDeAutoridad;
  puede: (metodo: string, ruta: string) => boolean;
  motivo: (metodo: string, ruta: string) => Motivo | null;
  tiene: (capacidad: string, alcance: AlcanceDeCapacidad) => boolean;
  motivoDeCapacidad: (capacidad: string, alcance: AlcanceDeCapacidad) => Motivo | null;
}

export const AutoridadContext = createContext<AutoridadValue | null>(null);

export function useAutoridad(): AutoridadValue {
  const ctx = useContext(AutoridadContext);
  if (!ctx) {
    throw new Error("useAutoridad debe usarse dentro de <AutoridadProvider>");
  }
  return ctx;
}

export function AutoridadProvider({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, user, permissions, tenantPermissions, reloadMe } = useAuth();
  const { activeCompanyId, estado: estadoDeEmpresa } = useCompany();
  const queryClient = useQueryClient();
  const ultimaDenegacion = useRef(0);

  const catalogo = useQuery({
    queryKey: ["auth", "operaciones"],
    queryFn: () => apiFetch<{ operations: Operacion[] }>("/auth/operations"),
    enabled: isAuthenticated,
    staleTime: Infinity,
  });

  const indice = useMemo(() => {
    if (!catalogo.data?.operations) {
      return null;
    }
    return crearIndice(catalogo.data.operations);
  }, [catalogo.data]);

  const conEmpresa = isAuthenticated && estadoDeEmpresa === "READY" && activeCompanyId !== null;

  const autoridadEmpresa = useQuery({
    queryKey: ["autoridad", "empresa", user?.id ?? null],
    queryFn: () =>
      apiFetch<{ company_id: string; permissions: string[] }>("/authority/company"),
    enabled: conEmpresa,
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
  });

  useEffect(() => {
    const manejador = () => {
      const ahora = Date.now();
      if (ahora - ultimaDenegacion.current < 2000) {
        return;
      }
      ultimaDenegacion.current = ahora;
      void queryClient.invalidateQueries({ queryKey: ["autoridad"] });
      void reloadMe();
    };
    setAuthorityDenialHandler(manejador);
    return () => setAuthorityDenialHandler(null);
  }, [queryClient, reloadMe]);

  const conjuntos = useMemo<Conjuntos>(() => {
    const empresa =
      autoridadEmpresa.data && autoridadEmpresa.data.company_id === activeCompanyId
        ? new Set(autoridadEmpresa.data.permissions)
        : new Set<string>();
    return {
      empresa,
      tenant: new Set(tenantPermissions),
      global: new Set(permissions),
    };
  }, [autoridadEmpresa.data, activeCompanyId, tenantPermissions, permissions]);

  const valor = useMemo<AutoridadValue>(() => {
    const falloCatalogo = catalogo.isError;
    const falloEmpresa = conEmpresa && autoridadEmpresa.isError;
    const esperandoCatalogo = !catalogo.data || !indice;
    const esperandoEmpresa =
      conEmpresa &&
      (!autoridadEmpresa.data ||
        autoridadEmpresa.data.company_id !== activeCompanyId);

    let estado: EstadoDeAutoridad = "LISTA";
    if (!isAuthenticated || esperandoCatalogo || esperandoEmpresa) {
      estado = "CARGANDO";
    }
    if (falloCatalogo || falloEmpresa) {
      estado = "ERROR";
    }

    const puede = (metodo: string, ruta: string): boolean => {
      if (estado !== "LISTA" || !indice) {
        return false;
      }
      const operacion = resolver(indice, metodo, ruta);
      if (!operacion) {
        return false;
      }
      return evaluar(operacion, conjuntos).permitido;
    };

    const motivo = (metodo: string, ruta: string): Motivo | null => {
      if (estado !== "LISTA" || !indice) {
        return null;
      }
      const operacion = resolver(indice, metodo, ruta);
      if (!operacion) {
        return null;
      }
      const resultado = evaluar(operacion, conjuntos);
      return resultado.permitido ? null : resultado.motivo;
    };

    const tiene = (capacidad: string, alcance: AlcanceDeCapacidad): boolean => {
      if (estado !== "LISTA") {
        return false;
      }
      return conjuntos[alcance].has(capacidad);
    };

    const motivoDeCapacidad = (
      capacidad: string,
      alcance: AlcanceDeCapacidad,
    ): Motivo | null => {
      if (estado !== "LISTA") {
        return null;
      }
      if (conjuntos[alcance].has(capacidad)) {
        return null;
      }
      if (alcance !== "global" && conjuntos.global.has(capacidad)) {
        return "COMPANY_SCOPE_FORBIDDEN";
      }
      return "PERMISSION_DENIED";
    };

    return {
      estado,
      puede,
      motivo,
      tiene,
      motivoDeCapacidad,
    };
  }, [
    isAuthenticated,
    catalogo.data,
    catalogo.isError,
    indice,
    conEmpresa,
    autoridadEmpresa.data,
    autoridadEmpresa.isError,
    activeCompanyId,
    conjuntos,
  ]);

  return <AutoridadContext.Provider value={valor}>{children}</AutoridadContext.Provider>;
}
