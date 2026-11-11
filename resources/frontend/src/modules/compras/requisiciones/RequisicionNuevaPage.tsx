import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/api/client";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Autorizado } from "@/components/Autorizado";
import { AsyncButton } from "@/components/AsyncButton";
import { FormField } from "@/components/FormField";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";
import { AvisoDeAlmacenes } from "@/modules/organizacion/almacenes/AvisoDeAlmacenes";
import { useAlmacenesDeEmpresa } from "@/modules/organizacion/almacenes/useAlmacenesDeEmpresa";

type Need = {
  id: string;
  product: { id: string; code: string; name: string };
  warehouse: { id: string; code: string; name: string };
};

export function RequisicionNuevaPage(): React.JSX.Element {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const necessityId = searchParams.get("necesidad");
  const { notify } = useNotifications();
  const { activeCompany } = useCompany();

  const [code, setCode] = useState("");
  const [warehouseId, setWarehouseId] = useState("");
  const [needDate, setNeedDate] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [createdId, setCreatedId] = useState<string | null>(null);

  const almacenesQuery = useAlmacenesDeEmpresa(activeCompany?.id ?? null);

  const necesidadQuery = useQuery({
    queryKey: ["planificacion", "necesidad", necessityId],
    queryFn: () => apiFetch<Need>(`/planning/replenishment-needs/${necessityId}`),
    enabled: Boolean(necessityId),
    retry: false,
  });

  const need = necesidadQuery.data;

  useEffect(() => {
    if (need && !warehouseId) {
      setWarehouseId(need.warehouse.id);
    }
  }, [need, warehouseId]);

  useEffect(() => {
    if (createdId) {
      navigate(`/compras/requisiciones/${createdId}${necessityId ? `?necesidad=${necessityId}` : ""}`);
    }
  }, [createdId, navigate, necessityId]);

  const guardar = async (): Promise<void> => {
    if (!code.trim() || !warehouseId) {
      setError("Indica el código y el almacén.");
      return;
    }

    try {
      const detalle = await apiFetch<{ id: string }>("/purchasing/requisitions", {
        method: "POST",
        body: {
          code: code.trim(),
          warehouse_id: warehouseId,
          need_date: needDate || null,
        },
      });
      setCreatedId(detalle.id);
      notify({ type: "success", title: "Requisición creada" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al guardar.");
    }
  };

  return (
    <PageContent maxWidth="lg">
      <PageHeader
        title="Nueva requisición"
        crumbs={[
          { label: "Compras", to: "/compras" },
          { label: "Requisiciones", to: "/compras/requisiciones" },
          { label: "Nueva" },
        ]}
      />
      {need ? (
        <div role="status" className="mb-4">
          Desde la necesidad de reposición de {need.product.code} · {need.product.name} en{" "}
          {need.warehouse.code}.
        </div>
      ) : null}
      <form
        noValidate
        className="rounded-lg border border-border-default bg-surface-0 p-6"
        onSubmit={(e) => e.preventDefault()}
      >
        <div className="grid gap-4 md:grid-cols-2">
          <FormField label="Código" required>
            <TextInput value={code} onChange={(e) => setCode(e.target.value)} />
          </FormField>
          <FormField label="Almacén" required>
            <select value={warehouseId} onChange={(e) => setWarehouseId(e.target.value)}>
              <option value="">Selecciona un almacén</option>
              {(almacenesQuery.data?.items ?? []).map((almacen) => (
                <option key={almacen.id} value={almacen.id}>
                  {almacen.code} - {almacen.name}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Fecha de necesidad">
            <TextInput type="date" value={needDate} onChange={(e) => setNeedDate(e.target.value)} />
          </FormField>
        </div>
        <AvisoDeAlmacenes consulta={almacenesQuery} />
        {error ? (
          <div role="alert" className="mt-4">
            {error}
          </div>
        ) : null}
        <div className="mt-6 flex justify-end">
          <Autorizado operacion={["POST", "/purchasing/requisitions"]}>
            <AsyncButton onClick={guardar}>Crear requisición</AsyncButton>
          </Autorizado>
        </div>
      </form>
    </PageContent>
  );
}
