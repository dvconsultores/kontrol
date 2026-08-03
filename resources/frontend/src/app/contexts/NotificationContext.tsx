/**
 * Contexto de notificaciones persistentes (FR-001-063, DOC-08 §8.2).
 * Éxito/error permanecen hasta cierre manual; sin auto-dismiss en
 * operaciones importantes; sin duplicados.
 */
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

export type NotificationType = "success" | "error" | "warning" | "info";

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  description?: string;
  requestId?: string;
}

interface NotificationContextValue {
  notifications: Notification[];
  notify: (n: Omit<Notification, "id">) => void;
  dismiss: (id: string) => void;
}

const NotificationContext = createContext<NotificationContextValue | null>(null);

let counter = 0;

export function NotificationProvider({ children }: { children: ReactNode }): React.JSX.Element {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const seen = useRef<Set<string>>(new Set());

  const notify = useCallback((n: Omit<Notification, "id">) => {
    setNotifications((prev) => {
      // Evitar duplicados por clave (título + descripción).
      const key = `${n.type}:${n.title}:${n.description ?? ""}`;
      if (seen.current.has(key)) {
        return prev;
      }
      seen.current.add(key);
      const id = `n-${Date.now()}-${counter++}`;
      return [...prev, { ...n, id }];
    });
  }, []);

  const dismiss = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  const value = useMemo(() => ({ notifications, notify, dismiss }), [notifications, notify, dismiss]);

  return <NotificationContext.Provider value={value}>{children}</NotificationContext.Provider>;
}

export function useNotifications(): NotificationContextValue {
  const ctx = useContext(NotificationContext);
  if (!ctx) {
    throw new Error("useNotifications debe usarse dentro de <NotificationProvider>");
  }
  return ctx;
}
