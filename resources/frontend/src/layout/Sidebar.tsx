/** Sidebar — navegación colapsable (DOC-08 §5). */
import { Boxes, FileText, Home, LayoutDashboard, Lock, Settings, ShieldCheck, Users } from "lucide-react";
import { NavLink } from "react-router";
import { useState } from "react";

import { clsx } from "clsx";

const navSections = [
  {
    title: "Principal",
    items: [
      { to: "/", label: "Inicio", icon: LayoutDashboard },
      { to: "/mi-licencia", label: "Mi licencia", icon: Lock },
    ],
  },
  {
    title: "Organización",
    items: [
      { to: "/organizacion/empresas", label: "Empresas", icon: Home },
      { to: "/organizacion/sucursales", label: "Sucursales", icon: Boxes },
      { to: "/organizacion/almacenes", label: "Almacenes", icon: Boxes },
    ],
  },
  {
    title: "Seguridad",
    items: [
      { to: "/seguridad/usuarios", label: "Usuarios", icon: Users },
      { to: "/seguridad/roles", label: "Roles", icon: ShieldCheck },
    ],
  },
  {
    title: "Sistema",
    items: [
      { to: "/auditoria", label: "Auditoría", icon: FileText },
      { to: "/diagnostico", label: "Diagnóstico", icon: Settings },
    ],
  },
];

export function Sidebar(): React.JSX.Element {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={clsx(
        "flex h-full flex-col border-r border-border-default bg-surface-0 transition-[width]",
        collapsed ? "w-16" : "w-64",
      )}
    >
      <div className="flex h-14 items-center justify-between border-b border-border-default px-4">
        {!collapsed ? <span className="text-lg font-bold text-brand-700">KONTROL</span> : null}
        <button
          type="button"
          onClick={() => setCollapsed((v) => !v)}
          aria-label={collapsed ? "Expandir menú" : "Colapsar menú"}
          className="rounded p-1 text-text-500 hover:bg-surface-100"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M6 3l5 5-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </button>
      </div>
      <nav aria-label="Menú principal" className="flex-1 overflow-y-auto px-2 py-3">
        {navSections.map((section) => (
          <div key={section.title} className="mb-4">
            {!collapsed ? (
              <p className="px-2 pb-1 text-xs font-semibold uppercase tracking-wide text-text-400">
                {section.title}
              </p>
            ) : null}
            <ul className="space-y-1">
              {section.items.map((item) => (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    title={item.label}
                    className={({ isActive }) =>
                      clsx(
                        "flex items-center gap-3 rounded-md px-2 py-2 text-sm",
                        isActive
                          ? "bg-brand-50 font-medium text-brand-700"
                          : "text-text-700 hover:bg-surface-100",
                        collapsed && "justify-center",
                      )
                    }
                  >
                    <item.icon className="size-4 shrink-0" aria-hidden="true" />
                    {!collapsed ? <span>{item.label}</span> : null}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>
    </aside>
  );
}
