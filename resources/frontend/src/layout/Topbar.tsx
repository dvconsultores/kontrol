/** Topbar — empresa activa, usuario, licencia y salida (DOC-08 §5). */
import { LogOut, Lock, User as UserIcon } from "lucide-react";

import { useAuth } from "@/app/contexts/AuthContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useLicense } from "@/app/contexts/LicenseContext";
import { Link } from "react-router-dom";

export function Topbar(): React.JSX.Element {
  const { user, logout } = useAuth();
  const { activeCompany } = useCompany();
  const { mode } = useLicense();

  return (
    <header className="flex h-14 items-center justify-between border-b border-border-default bg-surface-0 px-4">
      <div className="flex items-center gap-2 text-sm">
        {activeCompany ? (
          <>
            <span className="font-medium text-text-900">{activeCompany.legal_name}</span>
            <span className="text-text-400">·</span>
            <span className="text-text-500">{activeCompany.rif}</span>
          </>
        ) : (
          <span className="text-text-400">Sin empresa activa</span>
        )}
      </div>
      <div className="flex items-center gap-3">
        {mode ? (
          <Link
            to="/mi-licencia"
            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-text-500 hover:bg-surface-100"
          >
            <Lock className="size-3.5" aria-hidden="true" />
            {mode.replaceAll("_", " ")}
          </Link>
        ) : null}
        <div className="flex items-center gap-2">
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
