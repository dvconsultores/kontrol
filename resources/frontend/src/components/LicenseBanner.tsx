/** LicenseBanner — banner de estado de licencia (FR-001-067, DOC-08 §15.3). */
import { Link } from "react-router";

import { useLicense } from "@/app/contexts/LicenseContext";

const messages: Record<string, { title: string; detail: string; tone: "warning" | "danger" }> = {
  RENEWAL_NOTICE: {
    title: "Su licencia anual requiere renovación",
    detail: "Puede continuar operando durante el período de gracia hasta el 30 de abril. Realice el pago y cargue el comprobante.",
    tone: "warning",
  },
  CRITICAL_RENEWAL_NOTICE: {
    title: "Renovación crítica",
    detail: "KONTROL pasará a modo solo consulta el 1 de mayo si no se confirma la renovación.",
    tone: "warning",
  },
  READ_ONLY: {
    title: "KONTROL está en modo solo consulta",
    detail: "La renovación anual no ha sido confirmada. Puede consultar, reportar, exportar y reimprimir información existente.",
    tone: "danger",
  },
};

export function LicenseBanner(): React.JSX.Element | null {
  const { mode, status } = useLicense();
  if (!mode || !(mode in messages)) {
    return null;
  }
  const info = messages[mode];
  return (
    <div
      role="status"
      className={`flex flex-wrap items-center justify-between gap-2 border-b px-4 py-2 text-sm ${
        info.tone === "danger" ? "border-danger-100 bg-danger-100/60" : "border-warning-100 bg-warning-100/60"
      }`}
    >
      <p className="font-medium text-text-900">
        {info.title} — <span className="font-normal text-text-700">{info.detail}</span>
      </p>
      <Link
        to={status?.license_url ?? "/mi-licencia"}
        className="rounded px-2 py-1 font-medium text-brand-700 underline-offset-2 hover:underline"
      >
        Ver Mi licencia
      </Link>
    </div>
  );
}
