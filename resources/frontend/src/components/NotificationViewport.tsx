/** Contenedor global de notificaciones (renderiza #notification-root). */
import { useNotifications } from "@/app/contexts/NotificationContext";

import { PersistentNotification } from "./PersistentNotification";

export function NotificationViewport(): React.JSX.Element | null {
  const { notifications, dismiss } = useNotifications();
  if (notifications.length === 0) {
    return null;
  }
  return (
    <div id="notification-root">
      {notifications.map((n) => (
        <PersistentNotification key={n.id} notification={n} onDismiss={dismiss} />
      ))}
    </div>
  );
}
