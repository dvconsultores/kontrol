/** Sidebar — navegación colapsable (DOC-08 §5). */
import {
  Archive,
  ArrowLeftRight,
  BarChart3,
  Bell,
  BookOpen,
  Boxes,
  ClipboardCheck,
  ClipboardList,
  Cpu,
  CreditCard,
  FileCheck,
  FileDown,
  FileSearch,
  Gavel,
  FolderOpen,
  History,
  FileText,
  FileSignature,
  Grid3x3,
  Hash,
  Home,
  KeyRound,
  Landmark,
  LayoutDashboard,
  ListChecks,
  Lock,
  Network,
  BadgeCheck,
  Package,
  Percent,
  Ruler,
  Receipt,
  Repeat,
  Scale,
  ScrollText,
  Send,
  Settings,
  ShieldAlert,
  ShieldBan,
  ShieldCheck,
  WalletCards,
  Building2,
  ShoppingCart,
  ShoppingBag,
  SlidersHorizontal,
  StickyNote,
  Tags,
  CalendarClock,
  Truck,
  Contact,
  IdCard,
  UserCheck,
  Users,
  Wallet,
  Warehouse,
  CalendarRange,
  FolderCheck,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { NavLink } from "react-router";
import { useEffect, useRef, useState } from "react";

import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useModuloGobierno } from "@/modules/gobierno/api";
import { requisitoDe } from "@/app/autoridad/pantallas";
import { evaluarPantalla } from "@/app/autoridad/requisitos";
import { t } from "@/i18n";
import { clsx } from "clsx";

interface NavItem { to: string; label: string; icon: LucideIcon; /** Módulo de licencia que exige la entrada. */ modulo?: "gobierno" }
interface NavSection { title: string; items: NavItem[] }
const navSections: NavSection[] = [
  {
    title: "Principal",
    items: [
      { to: "/", label: "Inicio", icon: LayoutDashboard },
      // El detalle de la licencia lo gobierna el mismo permiso que la sección «Licenciamiento» (FR-010-114).
      { to: "/mi-licencia", label: "Mi licencia", icon: Lock },
    ],
  },
  // Línea de Gobierno (GOV-0-01): solo si la licencia habilita el módulo `gobierno`.
  {
    title: "Gobierno",
    items: [
      { to: "/gobierno/ente", label: "Configuración del ente", icon: Landmark, modulo: "gobierno" },
      { to: "/gobierno/estructura", label: "Estructura organizativa", icon: Network, modulo: "gobierno" },
      { to: "/gobierno/cargos", label: "Cargos y competencias", icon: BadgeCheck, modulo: "gobierno" },
      { to: "/gobierno/ocupacion", label: "Ocupación de cargos", icon: UserCheck, modulo: "gobierno" },
      { to: "/gobierno/identidad", label: "Identidad institucional", icon: IdCard, modulo: "gobierno" },
      { to: "/gobierno/identidad/mi-contexto", label: "Mi contexto institucional", icon: Contact, modulo: "gobierno" },
      { to: "/gobierno/actos", label: "Actos administrativos", icon: ScrollText, modulo: "gobierno" },
      { to: "/gobierno/notificaciones", label: "Notificaciones administrativas", icon: Send, modulo: "gobierno" },
      { to: "/gobierno/autoridad", label: "Matriz de autoridad", icon: Grid3x3, modulo: "gobierno" },
      { to: "/gobierno/auditoria", label: "Auditoría institucional", icon: FileSearch, modulo: "gobierno" },
      { to: "/gobierno/bitacora", label: "Bitácora institucional", icon: History, modulo: "gobierno" },
      { to: "/gobierno/control-interno", label: "Reporte de control interno", icon: BarChart3, modulo: "gobierno" },
      { to: "/gobierno/control/separacion", label: "Separación técnica y funcional", icon: ShieldCheck, modulo: "gobierno" },
      { to: "/gobierno/hallazgos", label: "Hallazgos y acciones correctivas", icon: ClipboardCheck, modulo: "gobierno" },
      { to: "/gobierno/paquetes", label: "Paquetes de auditoría", icon: Archive, modulo: "gobierno" },
      { to: "/gobierno/rendicion", label: "Expedientes de cuenta", icon: FolderCheck, modulo: "gobierno" },
      { to: "/gobierno/actas-entrega", label: "Actas de entrega", icon: FileSignature, modulo: "gobierno" },
      { to: "/gobierno/sod", label: "Segregación de funciones", icon: ShieldBan, modulo: "gobierno" },
      { to: "/gobierno/cierres", label: "Controles de cierre", icon: ShieldBan, modulo: "gobierno" },
    ],
  },
  // Contrataciones (PROC-02): sección propia, también sujeta al módulo `gobierno`.
  {
    title: "Gobierno · Contrataciones",
    items: [
      {
        to: "/gobierno/contrataciones/comisiones",
        label: "Comisiones",
        icon: Gavel,
        modulo: "gobierno",
      },
      {
        to: "/gobierno/contrataciones/expedientes",
        label: "Expedientes",
        icon: FolderOpen,
        modulo: "gobierno",
      },
      {
        to: "/gobierno/sod/funciones",
        label: "Funciones incompatibles",
        icon: ShieldAlert,
        modulo: "gobierno",
      },
    ],
  },
  // Tesorería de Gobierno (TRE-01): sección propia, también sujeta al módulo `gobierno`.
  {
    title: "Gobierno · Tesorería",
    items: [
      { to: "/gobierno/tesoreria/cuentas", label: "Cuentas bancarias", icon: WalletCards, modulo: "gobierno" },
      { to: "/gobierno/tesoreria/bancos", label: "Bancos", icon: Building2, modulo: "gobierno" },
      { to: "/gobierno/tesoreria/programacion", label: "Programación financiera", icon: CalendarRange, modulo: "gobierno" },
      { to: "/gobierno/tesoreria/rubros", label: "Rubros de caja", icon: Tags, modulo: "gobierno" },
    ],
  },
  {
    // Spec 047: textos desde el catálogo; cada entrada con su propio permiso.
    title: t("nav.seccion"),
    items: [
      { to: "/notificaciones", label: t("nav.notificaciones"), icon: Bell },
      { to: "/tareas", label: t("nav.tareas"), icon: ListChecks },
      { to: "/alertas", label: t("nav.alertas"), icon: ShieldAlert },
      { to: "/notificaciones/reglas", label: t("nav.reglas"), icon: SlidersHorizontal },
      { to: "/notificaciones/preferencias", label: t("nav.preferencias"), icon: Settings },
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
      { to: "/maestros/unidades", label: "Unidades de medida", icon: Ruler },
      { to: "/maestros/atributos", label: "Atributos", icon: ClipboardList },
      { to: "/maestros/almacenamiento", label: "Almacenamiento", icon: Warehouse },
      { to: "/maestros/planificacion", label: "Planificación de abastecimiento", icon: SlidersHorizontal },
      { to: "/maestros/perfiles", label: "Perfiles fiscales", icon: Percent },
    ],
  },
  {
    title: "Inventario",
    items: [
      { to: "/inventario/existencias", label: "Existencias", icon: Warehouse },
      { to: "/inventario/confirmacion", label: "Confirmación", icon: ClipboardList },
      { to: "/inventario/putaway", label: "Put-away", icon: Warehouse },
      { to: "/inventario/kardex", label: "Kardex", icon: ClipboardList },
      { to: "/inventario/movimientos", label: "Movimientos", icon: ArrowLeftRight },
      { to: "/inventario/tipos-movimiento", label: "Tipos de movimiento", icon: Settings },
      { to: "/inventario/transferencias", label: "Transferencias", icon: Boxes },
      { to: "/inventario/conteos", label: "Conteos", icon: Scale },
      { to: "/inventario/ajustes", label: "Ajustes", icon: FileText },
      { to: "/inventario/lotes", label: "Lotes", icon: Tags },
      { to: "/inventario/seriales", label: "Seriales", icon: Cpu },
      { to: "/inventario/reservas", label: "Reservas", icon: Lock },
      { to: "/inventario/valorizacion", label: "Valorización", icon: Percent },
    ],
  },
  {
    title: "Compras",
    items: [
      { to: "/compras/requisiciones", label: "Requisiciones", icon: ClipboardList },
      { to: "/compras/planificacion/necesidades", label: "Necesidades de reposición", icon: ListChecks },
      { to: "/compras/cotizaciones", label: "Cotizaciones", icon: FileText },
      { to: "/compras/ordenes", label: "Órdenes", icon: ShoppingCart },
      { to: "/compras/importaciones", label: "Importaciones", icon: Package },
      { to: "/compras/recepciones", label: "Recepciones", icon: Package },
      { to: "/compras/incidencias", label: "Incidencias", icon: Package },
      { to: "/compras/facturas", label: "Facturas", icon: Receipt },
      { to: "/compras/devoluciones", label: "Devoluciones", icon: Repeat },
      { to: "/compras/notas", label: "Notas de crédito", icon: StickyNote },
      { to: "/compras/cuentas-por-pagar", label: "CxP", icon: CreditCard },
    ],
  },
  {
    title: "Ventas",
    items: [
      { to: "/ventas/cotizaciones", label: "Cotizaciones", icon: ClipboardList },
      { to: "/ventas/ordenes", label: "Órdenes", icon: ShoppingBag },
      { to: "/ventas/preparacion", label: "Preparación de pedidos", icon: Truck },
      { to: "/ventas/confirmacion-pedido", label: "Confirmación de pedido", icon: ClipboardList },
      { to: "/ventas/facturacion", label: "Facturación", icon: ClipboardList },
      { to: "/ventas/despacho", label: "Despacho", icon: Truck },
      { to: "/ventas/facturas", label: "Facturas", icon: Receipt },
      { to: "/ventas/notas", label: "Notas", icon: StickyNote },
      { to: "/ventas/devoluciones", label: "Devoluciones", icon: Repeat },
      { to: "/ventas/cuentas-por-cobrar", label: "CxC", icon: Wallet },
      { to: "/ventas/estado-de-cuenta", label: "Estado de cuenta", icon: Wallet },
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
      { to: "/tesoreria/cambio", label: "Cambio de moneda", icon: Repeat },
      { to: "/tesoreria/reembolsos", label: "Reembolsos", icon: ArrowLeftRight },
      { to: "/tesoreria/posicion", label: "Posición de caja", icon: Wallet },
      { to: "/tesoreria/tasas", label: "Tasas de cambio", icon: Repeat },
      { to: "/tesoreria/fuentes", label: "Fuentes de tasa", icon: Settings },
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
      { to: "/fiscal/lotes-declaracion", label: "Lotes de declaración", icon: FileCheck },
    ],
  },
  {
    title: "Regulatorio",
    items: [
      { to: "/regulatorio/organismos", label: "Organismos", icon: Landmark },
      { to: "/regulatorio/vehiculos", label: "Vehículos", icon: Truck },
      { to: "/regulatorio/permisos", label: "Permisos y guías", icon: FileCheck },
      { to: "/regulatorio/evaluacion", label: "Evaluación", icon: ShieldAlert },
      { to: "/regulatorio/aprobaciones", label: "Aprobaciones", icon: ShieldCheck },
    ],
  },
  {
    title: "Aprobaciones",
    items: [
      { to: "/aprobaciones/bandeja", label: "Mis aprobaciones", icon: ClipboardCheck },
      { to: "/aprobaciones/politicas", label: "Políticas", icon: Scale },
      { to: "/aprobaciones/delegaciones", label: "Delegaciones", icon: Send },
    ],
  },
  {
    title: "Documentos",
    items: [
      { to: "/documentos", label: "Biblioteca", icon: FileText },
      { to: "/documentos/tipos", label: "Tipos documentales", icon: Settings },
    ],
  },
  {
    title: "Comercial",
    items: [
      { to: "/comercial/listas-precio", label: "Listas de precios", icon: Tags },
      { to: "/comercial/condiciones-pago", label: "Condiciones de pago", icon: CalendarClock },
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
      { to: "/seguridad/mfa", label: "Verificación en dos pasos", icon: KeyRound },
      { to: "/auditoria", label: "Auditoría", icon: FileText },
      // El diagnóstico de la instalación lo gobierna el mismo permiso que la sección «Licenciamiento».
      { to: "/diagnostico", label: "Diagnóstico", icon: Settings },
    ],
  },
];

export interface SidebarProps {
  /** Si se define, se llama al elegir una entrada (p. ej. cerrar el panel). */
  onNavigated?: () => void;
  /** Si se define, se muestra un control «Cerrar menú» en la cabecera. */
  onClose?: () => void;
  /** Si es `true`, el foco inicial se coloca en el panel al montar. */
  autoFocus?: boolean;
}

export function Sidebar({ onNavigated, onClose, autoFocus }: SidebarProps = {}): React.JSX.Element {
  const [collapsed, setCollapsed] = useState(false);
  const asideRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!autoFocus) return;
    // Coloca el foco en el panel para lectores de pantalla y navegación con
    // teclado cuando el menú se abre como superposición.
    asideRef.current?.focus();
  }, [autoFocus]);

  useEffect(() => {
    if (!onClose) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);
  const autoridad = useAutoridad();
  const moduloGobierno = useModuloGobierno();
  // Una entrada se ve si su pantalla está permitida (registro único `pantallas.ts`, Spec 003). Mientras la autoridad carga, las entradas
  // con requisito no se muestran: nunca se ofrece autoridad desconocida o de otra empresa.
  const visibleSections = navSections
    .map((section) => ({
      ...section,
      items: section.items.filter(
        (item) =>
          (item.modulo !== "gobierno" || moduloGobierno) &&
          evaluarPantalla(autoridad, requisitoDe(item.to.replace(/^\//, ""))).estado === "PERMITIDA",
      ),
    }))
    .filter((section) => section.items.length > 0);

  return (
    <aside
      ref={asideRef}
      tabIndex={autoFocus ? -1 : undefined}
      className={clsx(
        "flex h-full flex-col border-r border-border-default bg-surface-0 transition-[width] outline-none",
        collapsed ? "w-16" : "w-64",
      )}
    >
      <div className="flex h-14 items-center justify-between border-b border-border-default px-4">
        {!collapsed ? <span className="text-lg font-bold text-brand-700">KONTROL</span> : null}
        <div className="flex items-center gap-1">
          {onClose ? (
            <button
              type="button"
              onClick={onClose}
              aria-label="Cerrar menú"
              className="rounded p-1 text-text-500 hover:bg-surface-100"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            </button>
          ) : null}
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
      </div>
      {/* Los títulos de sección usan text-500 (4,76:1 sobre blanco) y no
          text-400 (2,56:1): incumplían WCAG 2.2 AA en TODAS las páginas
          autenticadas. Detectado al hacer que la suite axe midiera la ruta
          real en lugar de la de inicio (Spec 045, CVG-045-07). */}
      <nav aria-label="Menú principal" className="flex-1 overflow-y-auto px-2 py-3">
        {visibleSections.map((section) => (
          <div key={section.title} className="mb-4">
            {!collapsed ? (
              <p className="px-2 pb-1 text-xs font-semibold uppercase tracking-wide text-text-500">
                {section.title}
              </p>
            ) : null}
            <ul className="space-y-1">
              {section.items.map((item) => (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    title={item.label}
                    onClick={onNavigated}
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
