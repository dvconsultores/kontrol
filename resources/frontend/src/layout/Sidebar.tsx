/** Sidebar — navegación colapsable (DOC-08 §5). */
import {
  ArrowLeftRight,
  BarChart3,
  BookOpen,
  Boxes,
  ClipboardCheck,
  ClipboardList,
  CreditCard,
  FileCheck,
  FileDown,
  FileText,
  Hash,
  Home,
  Landmark,
  LayoutDashboard,
  Lock,
  Package,
  Percent,
  Receipt,
  Repeat,
  Scale,
  ScrollText,
  Settings,
  ShieldAlert,
  ShieldCheck,
  ShoppingCart,
  ShoppingBag,
  StickyNote,
  Tags,
  Truck,
  Users,
  Wallet,
  Warehouse,
} from "lucide-react";
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
      { to: "/organizacion/establecimientos", label: "Establecimientos", icon: Home },
      { to: "/organizacion/almacenes", label: "Almacenes", icon: Boxes },
      { to: "/organizacion/ubicaciones", label: "Ubicaciones", icon: Warehouse },
    ],
  },
  {
    title: "Maestros",
    items: [
      { to: "/maestros/terceros", label: "Terceros", icon: Users },
      { to: "/maestros/productos", label: "Productos", icon: Package },
      { to: "/maestros/servicios", label: "Servicios", icon: Tags },
      { to: "/maestros/catalogos", label: "Catálogo", icon: Tags },
      { to: "/maestros/perfiles", label: "Perfiles fiscales", icon: Percent },
    ],
  },
  {
    title: "Inventario",
    items: [
      { to: "/inventario/existencias", label: "Existencias", icon: Warehouse },
      { to: "/inventario/kardex", label: "Kardex", icon: ClipboardList },
      { to: "/inventario/transferencias", label: "Transferencias", icon: Boxes },
      { to: "/inventario/conteos", label: "Conteos", icon: Scale },
      { to: "/inventario/ajustes", label: "Ajustes", icon: FileText },
    ],
  },
  {
    title: "Compras",
    items: [
      { to: "/compras/requisiciones", label: "Requisiciones", icon: ClipboardList },
      { to: "/compras/ordenes", label: "Órdenes", icon: ShoppingCart },
      { to: "/compras/recepciones", label: "Recepciones", icon: Package },
      { to: "/compras/facturas", label: "Facturas", icon: Receipt },
      { to: "/compras/cuentas-por-pagar", label: "CxP", icon: CreditCard },
    ],
  },
  {
    title: "Ventas",
    items: [
      { to: "/ventas/cotizaciones", label: "Cotizaciones", icon: ClipboardList },
      { to: "/ventas/ordenes", label: "Órdenes", icon: ShoppingBag },
      { to: "/ventas/facturas", label: "Facturas", icon: Receipt },
      { to: "/ventas/cuentas-por-cobrar", label: "CxC", icon: Wallet },
    ],
  },
  {
    title: "Tesorería",
    items: [
      { to: "/tesoreria/cajas", label: "Cajas y arqueo", icon: Wallet },
      { to: "/tesoreria/ingresos-egresos", label: "Ingresos y egresos", icon: ArrowLeftRight },
      { to: "/tesoreria/transferencias", label: "Transferencias", icon: Repeat },
      { to: "/tesoreria/conciliacion", label: "Conciliación", icon: ClipboardCheck },
      { to: "/tesoreria/igft", label: "IGTF", icon: Percent },
      { to: "/tesoreria/maestros", label: "Maestros", icon: Settings },
    ],
  },
  {
    title: "Fiscal",
    items: [
      { to: "/fiscal/configuracion", label: "Configuración", icon: Settings },
      { to: "/fiscal/numeracion", label: "Numeración", icon: Hash },
      { to: "/fiscal/emision", label: "Emisión", icon: FileText },
      { to: "/fiscal/notas", label: "Notas", icon: StickyNote },
      { to: "/fiscal/retenciones", label: "Retenciones", icon: Percent },
      { to: "/fiscal/libros", label: "Libros y períodos", icon: BookOpen },
    ],
  },
  {
    title: "Regulatorio",
    items: [
      { to: "/regulatorio/organismos", label: "Organismos", icon: Landmark },
      { to: "/regulatorio/vehiculos", label: "Vehículos", icon: Truck },
      { to: "/regulatorio/permisos", label: "Permisos y guías", icon: FileCheck },
      { to: "/regulatorio/evaluacion", label: "Evaluación", icon: ShieldAlert },
    ],
  },
  {
    title: "Reportes",
    items: [
      { to: "/reportes/centro", label: "Centro de reportes", icon: BarChart3 },
      { to: "/reportes/exportaciones", label: "Exportaciones", icon: FileDown },
      { to: "/reportes/auditoria", label: "Auditoría", icon: ScrollText },
    ],
  },
  {
    title: "Licenciamiento",
    items: [
      { to: "/licenciamiento/configuracion", label: "Configuración central", icon: Settings },
      { to: "/licenciamiento/entitlements", label: "Entitlements", icon: ShieldCheck },
      { to: "/licenciamiento/renovacion", label: "Renovación", icon: Repeat },
      { to: "/licenciamiento/eventos", label: "Eventos", icon: ScrollText },
    ],
  },
  {
    title: "Homologación",
    items: [
      { to: "/homologacion/actos", label: "Actos", icon: FileCheck },
      { to: "/homologacion/versiones", label: "Versiones", icon: Hash },
      { to: "/homologacion/timeline", label: "Timeline", icon: ScrollText },
    ],
  },
  {
    title: "Seguridad",
    items: [
      { to: "/seguridad/usuarios", label: "Usuarios", icon: Users },
      { to: "/seguridad/roles", label: "Roles", icon: ShieldCheck },
      { to: "/seguridad/sesiones", label: "Sesiones", icon: Lock },
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
