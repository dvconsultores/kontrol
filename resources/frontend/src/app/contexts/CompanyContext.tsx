/**
 * Contexto de empresa activa (ARCH-MC-001, fase N6).
 *
 * El frontend **selecciona**; el backend **autoriza**. Nada de lo que hay aquí
 * concede acceso: la empresa viaja en cada petición y el servidor la vuelve a
 * validar. Si esta capa se equivocara, el peor resultado sería un error, nunca
 * un dato de otra empresa.
 *
 * Se distinguen cuatro cosas que antes estaban mezcladas en una sola:
 *
 * - **La preferencia** (`localStorage`): la última empresa elegida. Es una
 *   comodidad, no un permiso, y se revalida siempre contra la lista autorizada.
 * - **El contexto activo de esta pestaña** (`sessionStorage`): en qué empresa se
 *   está operando *aquí*. `localStorage` se comparte entre pestañas, así que
 *   usarlo para esto haría que cambiar de empresa en una pestaña cambiara la
 *   otra por debajo — con un formulario a medio llenar en pantalla.
 * - **Las empresas autorizadas**: vienen del backend, nunca del token ni de los
 *   roles. Un rol global significa «este rol vale donde el usuario opere», no
 *   «el usuario opera en todas»: confundirlo fue un defecto real de N1.
 * - **El estado de resolución**: explícito, no una suma de booleanos.
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

import { apiFetch, setCompanyResolver } from "@/api/client";
import type { CompanySummary } from "@/api/types";
import { useAuth } from "@/app/contexts/AuthContext";

/** Preferencia entre sesiones. Compartida entre pestañas **a propósito**. */
const CLAVE_PREFERENCIA = "kontrol.company-preference.v2";
/** Contexto operativo de esta pestaña. Nunca compartido. */
const CLAVE_PESTANA = "kontrol.company-tab.v1";

export type EstadoEmpresa =
  | "AUTH_LOADING"
  | "COMPANY_LOADING"
  | "COMPANY_SELECTION_REQUIRED"
  | "NO_COMPANIES"
  | "READY"
  | "ERROR";

interface CompanyContextValue {
  /** Empresas en las que este usuario puede operar, según el backend. */
  companies: CompanySummary[];
  /** La empresa de **esta** pestaña. */
  activeCompany: CompanySummary | null;
  activeCompanyId: string | null;
  estado: EstadoEmpresa;
  error: string | null;
  /** Cambia la empresa de esta pestaña. Rechaza cualquier id no autorizado. */
  selectCompany: (companyId: string) => boolean;
  /** Vuelve a preguntar al backend qué empresas puede operar el usuario. */
  refreshCompanies: () => Promise<void>;
  /** El backend rechazó la empresa activa: se descarta y se recalcula. */
  onCompanyRejected: () => void;
  /** Compatibilidad con el código anterior. */
  setActiveCompany: (company: CompanySummary | null) => void;
}

const Ctx = createContext<CompanyContextValue | null>(null);

// -- almacenamiento tolerante a fallos ---------------------------------------
// En navegación privada o dentro de un sandbox, tocar el almacenamiento lanza.
// Que no se pueda recordar la preferencia no puede tumbar la aplicación.
function leer(almacen: Storage | undefined, clave: string): string | null {
  try {
    return almacen?.getItem(clave) ?? null;
  } catch {
    return null;
  }
}

function escribir(almacen: Storage | undefined, clave: string, valor: string | null): void {
  try {
    if (valor === null) {
      almacen?.removeItem(clave);
    } else {
      almacen?.setItem(clave, valor);
    }
  } catch {
    // Sin almacenamiento: el contexto vive en memoria mientras dure la pestaña.
  }
}

/**
 * La preferencia se guarda junto al usuario que la eligió.
 *
 * Sin esto, quien inicie sesión después en el mismo navegador heredaría la
 * empresa del anterior: no vería sus datos —el backend lo impediría— pero
 * arrancaría apuntando a una empresa que no es suya.
 */
function clavePreferencia(userId: string | null): string {
  return `${CLAVE_PREFERENCIA}:${userId ?? "anon"}`;
}

export function CompanyProvider({ children }: { children: ReactNode }): React.JSX.Element {
  const { isAuthenticated, isReady: authReady, user } = useAuth();
  const [companies, setCompanies] = useState<CompanySummary[]>([]);
  const [activeCompanyId, setActiveId] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resuelto, setResuelto] = useState(false);

  const userId = user?.id ?? null;

  // El id activo se lee de forma síncrona por el cliente HTTP, que no puede
  // esperar a un render para saber en qué empresa va la petición.
  const idRef = useRef<string | null>(null);
  idRef.current = activeCompanyId;

  useEffect(() => {
    setCompanyResolver(() => idRef.current);
    return () => setCompanyResolver(null);
  }, []);

  const aplicarActiva = useCallback(
    (id: string | null) => {
      idRef.current = id;
      setActiveId(id);
      escribir(window.sessionStorage, CLAVE_PESTANA, id);
      if (id) {
        escribir(window.localStorage, clavePreferencia(userId), id);
      }
    },
    [userId],
  );

  /**
   * Decide la empresa de esta pestaña a partir de la lista autorizada.
   *
   * El orden importa: primero lo que ya estaba en esta pestaña, luego la
   * preferencia del usuario, y solo si hay **una sola** empresa se resuelve
   * sola. Con varias y sin preferencia válida no se elige la primera: elegir
   * por el usuario en qué empresa opera es precisamente lo que no debe hacerse.
   */
  const resolver = useCallback(
    (autorizadas: CompanySummary[]) => {
      const operables = autorizadas.filter((c) => c.status === "ACTIVE");
      const validas = new Set(operables.map((c) => c.id));

      const dePestana = leer(window.sessionStorage, CLAVE_PESTANA);
      if (dePestana && validas.has(dePestana)) {
        aplicarActiva(dePestana);
        return;
      }

      const preferida = leer(window.localStorage, clavePreferencia(userId));
      if (preferida && validas.has(preferida)) {
        aplicarActiva(preferida);
        return;
      }

      if (operables.length === 1) {
        aplicarActiva(operables[0].id);
        return;
      }

      // Preferencia caducada: ya no está autorizada, se desactivó o se borró.
      if (preferida) {
        escribir(window.localStorage, clavePreferencia(userId), null);
      }
      idRef.current = null;
      setActiveId(null);
      escribir(window.sessionStorage, CLAVE_PESTANA, null);
    },
    [aplicarActiva, userId],
  );

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const lista = await apiFetch<CompanySummary[]>("/organization/companies");
      const autorizadas = Array.isArray(lista) ? lista : [];
      setCompanies(autorizadas);
      resolver(autorizadas);
      setResuelto(true);
    } catch {
      setCompanies([]);
      setError("COMPANY_LIST_UNAVAILABLE");
      setResuelto(true);
    } finally {
      setCargando(false);
    }
  }, [resolver]);

  useEffect(() => {
    if (!authReady) {
      return;
    }
    if (!isAuthenticated) {
      // Cerrar sesión limpia el contexto de esta pestaña. La preferencia
      // sobrevive: es del usuario, y está guardada bajo su identificador.
      setCompanies([]);
      idRef.current = null;
      setActiveId(null);
      setResuelto(false);
      setError(null);
      escribir(window.sessionStorage, CLAVE_PESTANA, null);
      return;
    }
    void cargar();
  }, [authReady, isAuthenticated, cargar]);

  const selectCompany = useCallback(
    (companyId: string): boolean => {
      const elegida = companies.find((c) => c.id === companyId && c.status === "ACTIVE");
      if (!elegida) {
        // Un id que no está en la lista autorizada no se acepta ni se envía.
        return false;
      }
      aplicarActiva(elegida.id);
      return true;
    },
    [companies, aplicarActiva],
  );

  const onCompanyRejected = useCallback(() => {
    // El backend rechazó la empresa activa (perdió acceso, se desactivó o
    // desapareció). Se suelta el contexto y se vuelve a preguntar quién es
    // operable, en vez de reintentar contra una empresa que ya dijo que no.
    idRef.current = null;
    setActiveId(null);
    escribir(window.sessionStorage, CLAVE_PESTANA, null);
    escribir(window.localStorage, clavePreferencia(userId), null);
    void cargar();
  }, [cargar, userId]);

  const setActiveCompany = useCallback(
    (company: CompanySummary | null) => {
      if (company === null) {
        idRef.current = null;
        setActiveId(null);
        escribir(window.sessionStorage, CLAVE_PESTANA, null);
        return;
      }
      selectCompany(company.id);
    },
    [selectCompany],
  );

  const activeCompany = useMemo(
    () => companies.find((c) => c.id === activeCompanyId) ?? null,
    [companies, activeCompanyId],
  );

  const estado: EstadoEmpresa = useMemo(() => {
    if (!authReady) return "AUTH_LOADING";
    if (!isAuthenticated) return "AUTH_LOADING";
    if (cargando || !resuelto) return "COMPANY_LOADING";
    if (error) return "ERROR";
    const operables = companies.filter((c) => c.status === "ACTIVE");
    if (operables.length === 0) return "NO_COMPANIES";
    if (!activeCompanyId) return "COMPANY_SELECTION_REQUIRED";
    return "READY";
  }, [authReady, isAuthenticated, cargando, resuelto, error, companies, activeCompanyId]);

  const value = useMemo(
    () => ({
      companies,
      activeCompany,
      activeCompanyId,
      estado,
      error,
      selectCompany,
      refreshCompanies: cargar,
      onCompanyRejected,
      setActiveCompany,
    }),
    [companies, activeCompany, activeCompanyId, estado, error, selectCompany, cargar, onCompanyRejected, setActiveCompany],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useCompany(): CompanyContextValue {
  const ctx = useContext(Ctx);
  if (!ctx) {
    throw new Error("useCompany debe usarse dentro de <CompanyProvider>");
  }
  return ctx;
}
