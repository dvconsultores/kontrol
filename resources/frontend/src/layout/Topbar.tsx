/** Topbar — empresa activa, usuario, licencia y salida (DOC-08 §5). */
import { LogOut, Lock, User as UserIcon } from "lucide-react";

import { useAuth } from "@/app/contexts/AuthContext";
import { useLicense } from "@/app/contexts/LicenseContext";
import { CompanySelector } from "@/components/company/CompanySelector";
import { NotificationBell } from "@/modules/notificaciones/NotificationBell";
import { Link } from "react-router";

export function Topbar(): React.JSX.Element {
  const { user, logout } = useAuth();
  const { mode } = useLicense();

  return (
    <header className="flex h-14 items-center justify-between border-b border-border-default bg-surface-0 px-4">
      {/* La empresa activa vive en el shell: cualquier pantalla de negocio es
          de una empresa concreta, y el usuario tiene que poder saber de cuál
          sin buscarla. */}
      <div className="flex min-w-0 items-center gap-2 text-sm">
        <CompanySelector />
      </div>
      <div className="flex items-center gap-3">
        <NotificationBell />
        {mode ? (
          <Link
            to="/mi-licencia"
            className="hidden items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-text-500 hover:bg-surface-100 sm:inline-flex"
          >
            <Lock className="size-3.5" aria-hidden="true" />
            {mode.replaceAll("_", " ")}
          </Link>
        ) : null}
        <div className="hidden items-center gap-2 sm:flex">
          <UserIcon className="size-4 text-text-400" aria-hidden="true" />
          <span className="text-sm text-text-700">{user?.username}</span>
        </div>
        <button
          type="button"
          onClick={() => void logout()}
          className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-sm text-text-500 hover:bg-surface-100 hover:text-danger-600"
        >
          <LogOut className="size-4" aria-hidden="true" />
          Salir
        </button>
      </div>
    </header>
  );
}
