import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { ApiError, apiFetch } from "@/api/client";
import { AsyncButton } from "@/components/AsyncButton";
import { Autorizado } from "@/components/Autorizado";
import { FormField } from "@/components/FormField";

export function ZonaTemporal({
  receiptId,
  codigo,
  onGuardada,
}: {
  receiptId: string;
  codigo: string;
  onGuardada: () => void | Promise<void>;
}): React.JSX.Element {
  const { data } = useQuery({
    queryKey: ["compras", "recepcion", receiptId, "zona-temporal"],
    queryFn: () =>
      apiFetch<{ items: Array<{ id: string; label: string }> }>(
        `/purchasing/receipts/${receiptId}/temporary-zone/options`,
      ),
  });

  const [elegida, setElegida] = useState("");
  const [error, setError] = useState<string | null>(null);

  const guardar = async (): Promise<void> => {
    if (!elegida) {
      setError("Elija la zona temporal.");
      return;
    }

    try {
      await apiFetch(`/purchasing/receipts/${receiptId}/temporary-zone`, {
        method: "POST",
        body: { temporary_location_id: elegida },
      });
      setElegida("");
      setError(null);
      await onGuardada();
    } catch (e) {
      setError(
        e instanceof ApiError
          ? e.message
          : "No se pudo registrar la zona temporal.",
      );
    }
  };

  return (
    <Autorizado
      operacion={[
        "POST",
        `/purchasing/receipts/${receiptId}/temporary-zone`,
      ]}
    >
      <div className="mt-3 flex flex-wrap items-end gap-3">
        <FormField
          label={`Zona temporal de ${codigo}`}
          help="Dónde queda la mercancía mientras se recibe y valida. No mueve inventario."
        >
          <select
            value={elegida}
            onChange={(e) => setElegida(e.currentTarget.value)}
            className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 sm:w-72"
          >
            <option value="">Seleccionar…</option>
            {(data?.items ?? []).map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
        </FormField>
        <AsyncButton type="button" onClick={guardar}>
          Registrar zona temporal de {codigo}
        </AsyncButton>
        {error ? (
          <p role="alert" className="w-full text-sm text-danger-700">
            {error}
          </p>
        ) : null}
      </div>
    </Autorizado>
  );
}
