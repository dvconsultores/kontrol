/** Topbar — empresa activa, usuario, licencia y salida (DOC-08 §5). */
import { LogOut, Lock, Menu, User as UserIcon } from "lucide-react";

import { useAuth } from "@/app/contexts/AuthContext";
import { useLicense } from "@/app/contexts/LicenseContext";
import { CompanySelector } from "@/components/company/CompanySelector";
import { NotificationBell } from "@/modules/notificaciones/NotificationBell";
import { Link } from "react-router";

export interface TopbarProps {
  onAbrirMenu?: () => void;
  botonMenuRef?: React.Ref<HTMLButtonElement>;
}

export function Topbar({ onAbrirMenu, botonMenuRef }: TopbarProps = {}): React.JSX.Element {
  const { user, logout } = useAuth();
  const { mode } = useLicense();

  return (
    <header className="flex h-14 min-w-0 items-center justify-between gap-2 border-b border-border-default bg-surface-0 px-4">
      <div className="flex min-w-0 items-center gap-2 text-sm">
        {onAbrirMenu ? (
          <button
            ref={botonMenuRef}
            type="button"
            onClick={onAbrirMenu}
            aria-label="Abrir menú"
            className="inline-flex size-9 items-center justify-center rounded-md text-text-600 hover:bg-surface-100 md:hidden"
          >
            <Menu className="size-5" aria-hidden="true" />
          </button>
        ) : null}
        <CompanySelector />
      </div>
      <div className="flex items-center gap-3">
        <NotificationBell />
        {mode ? (
          <Link
            to="/mi-licencia"
            aria-label={mode.replaceAll("_", " ")}
            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-text-500 hover:bg-surface-100"
          >
            <Lock className="size-3.5" aria-hidden="true" />
            <span className="hidden md:inline">{mode.replaceAll("_", " ")}</span>
          </Link>
        ) : null}
        <div className="flex items-center gap-2">
          <UserIcon className="size-4 text-text-400" aria-hidden="true" />
          <span className="hidden text-sm text-text-700 md:inline">{user?.username}</span>
          <span className="sr-only md:hidden">{user?.username}</span>
        </div>
        <button
          type="button"
          onClick={() => void logout()}
          aria-label="Salir"
          className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-sm text-text-500 hover:bg-surface-100 hover:text-danger-600"
        >
          <LogOut className="size-4" aria-hidden="true" />
          <span className="hidden md:inline">Salir</span>
        </button>
      </div>
    </header>
  );
}
