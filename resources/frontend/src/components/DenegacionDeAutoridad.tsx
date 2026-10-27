import { ShieldX } from "lucide-react";
import { Link } from "react-router";

import { useCompany } from "@/app/contexts/CompanyContext";
import type { AlcanceDeCapacidad } from "@/app/autoridad/AutoridadContext";
import type { Motivo } from "@/app/autoridad/operaciones";

import { Button } from "./Button";

export function DenegacionDeAutoridad({
  motivo,
  alcance,
}: {
  motivo: Motivo;
  alcance: AlcanceDeCapacidad;
}): React.JSX.Element {
  const { companies, activeCompanyId } = useCompany();
  const empresaActiva = companies.find((empresa) => empresa.id === activeCompanyId);

  let titulo: string;
  let texto: string;

  if (motivo === "PERMISSION_DENIED") {
    titulo = "Acceso prohibido";
    texto =
      "No tiene permiso para esta pantalla. Si lo necesita, pídalo a su administrador.";
  } else if (motivo === "COMPANY_SCOPE_FORBIDDEN" && alcance === "tenant") {
    titulo = "Requiere autoridad en todas las empresas";
    texto =
      "Esta configuración afecta a todas las empresas del tenant; solo puede gestionarla quien tiene esta autoridad en todas ellas.";
  } else {
    titulo = "Sin autoridad en esta empresa";
    const nombreEmpresa = empresaActiva?.legal_name;
    texto =
      nombreEmpresa !== undefined
        ? `Su autoridad para esta pantalla no incluye la empresa activa (${nombreEmpresa}). Cambie a una empresa en la que la tenga o pida acceso a su administrador.`
        : "Su autoridad para esta pantalla no incluye la empresa activa. Cambie a una empresa en la que la tenga o pida acceso a su administrador.";
  }

  return (
    <div
      role="alert"
      className="flex flex-col items-center justify-center gap-3 px-6 py-16 text-center"
    >
      <ShieldX className="size-12 text-warning-600" aria-hidden="true" />
      <h1 className="text-xl font-semibold text-text-900">{titulo}</h1>
      <p className="max-w-md text-sm text-text-500">{texto}</p>
      <Link to="/" className="mt-2">
        <Button variant="secondary">Volver al inicio</Button>
      </Link>
    </div>
  );
}
