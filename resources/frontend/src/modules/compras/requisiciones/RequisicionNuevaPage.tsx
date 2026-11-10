import { useEffect, useState } from "react";
import { useNavigate } from "react-router";

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

export function RequisicionNuevaPage(): React.JSX.Element {
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const { activeCompany } = useCompany();

  const [code, setCode] = useState("");
  const [warehouseId, setWarehouseId] = useState("");
  const [needDate, setNeedDate] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [createdId, setCreatedId] = useState<string | null>(null);

  const almacenesQuery = useAlmacenesDeEmpresa(activeCompany?.id ?? null);

  useEffect(() => {
    if (createdId) {
      navigate(`/compras/requisiciones/${createdId}`);
    }
  }, [createdId, navigate]);

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
