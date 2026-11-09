/** PersistentNotification — notificación persistente hasta cierre manual (FR-008). */
import { AlertCircle, CheckCircle2, Info, X, XCircle } from "lucide-react";

import type { Notification } from "@/app/contexts/NotificationContext";
import { clsx } from "clsx";

const styles: Record<Notification["type"], { icon: typeof Info; classes: string }> = {
  success: { icon: CheckCircle2, classes: "border-success-100 bg-success-100 text-success-600" },
  error: { icon: XCircle, classes: "border-danger-100 bg-danger-100 text-danger-600" },
  warning: { icon: AlertCircle, classes: "border-warning-100 bg-warning-100 text-warning-600" },
  info: { icon: Info, classes: "border-info-100 bg-info-100 text-info-600" },
};

export interface PersistentNotificationProps {
  notification: Notification;
  onDismiss: (id: string) => void;
}

export function PersistentNotification({
  notification,
  onDismiss,
}: PersistentNotificationProps): React.JSX.Element {
  const { icon: Icon, classes } = styles[notification.type];
  return (
    <div
      role={notification.type === "error" ? "alert" : "status"}
      aria-live={notification.type === "error" ? "assertive" : "polite"}
      className={clsx(
        "flex items-start gap-3 rounded-md border p-4 shadow-sm",
        classes,
      )}
    >
      <Icon className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-text-900">{notification.title}</p>
        {notification.description ? (
          <p className="mt-0.5 text-sm text-text-700">{notification.description}</p>
        ) : null}
        {notification.requestId ? (
          <p className="mt-0.5 text-xs text-text-400">ID de solicitud: {notification.requestId}</p>
        ) : null}
      </div>
      <button
        type="button"
        onClick={() => onDismiss(notification.id)}
        aria-label="Cerrar notificación"
        className="shrink-0 rounded p-1 text-text-500 hover:bg-surface-100 hover:text-text-900"
      >
        <X className="size-4" aria-hidden="true" />
      </button>
    </div>
  );
}
