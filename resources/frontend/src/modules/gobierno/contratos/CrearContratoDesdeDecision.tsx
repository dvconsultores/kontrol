import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { Button } from "@/components/Button";
import { rutaContrato, type Contrato } from "./api";

interface ContratoResumenDecision {
  id: string;
  identificacion: string;
  estado: string;
}

export function CrearContratoDesdeDecision({
  expedienteId,
  contrato,
  onCreado,
}: {
  expedienteId: string;
  contrato: ContratoResumenDecision | null;
  onCreado?: () => void;
}) {
  const { tiene } = useAutoridad();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  async function crearContrato() {
    setError(null);
    try {
      const respuesta = await apiFetch<Contrato>("/gobierno/contratos", {
        method: "POST",
        body: { expediente_id: expedienteId },
      });
      onCreado?.();
      navigate(rutaContrato(respuesta.id));
    } catch (errorCreado) {
      setError(errorCreado instanceof ApiError ? errorCreado.message : "No se pudo crear el contrato.");
    }
  }

  return (
    <section aria-labelledby="contrato-derivado-titulo">
      <h3 id="contrato-derivado-titulo" className="text-sm font-semibold text-text-900">
        Contrato u orden
      </h3>
      {contrato ? (
        <div className="mt-2">
          <p className="break-words text-sm text-text-900">
            {contrato.identificacion} · {contrato.estado === "FORMALIZADO" ? "Formalizado" : "Borrador"}
          </p>
          <Link className="mt-1 inline-block text-sm text-brand-700 underline" to={rutaContrato(contrato.id)}>
            Ver contrato u orden
          </Link>
        </div>
      ) : tiene("gobierno_contratos:manage", "empresa") ? (
        <div className="mt-2">
          {error ? (
            <div role="alert" className="mb-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {error}
            </div>
          ) : null}
          <Button type="button" variant="secondary" onClick={() => void crearContrato()}>
            Crear contrato u orden
          </Button>
        </div>
      ) : (
        <p className="mt-2 text-sm text-text-600">
          El contrato u orden lo crea la Unidad Contratante desde aquí.
        </p>
      )}
    </section>
  );
}
