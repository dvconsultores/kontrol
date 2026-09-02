/** Condiciones de pago — Spec 012.
 *
 * `FR-012-030`: es un maestro, nunca una cadena. Y `FR-012-032`: el catálogo
 * nace vacío — «contado» y «30 días» son datos de cada empresa, no constantes
 * del producto.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";
import { comercial, type PaymentTerm } from "./api";

const TIPOS = [
  { valor: "CASH", etiqueta: "Contado" },
  { valor: "DAYS", etiqueta: "A días" },
  { valor: "INSTALLMENTS", etiqueta: "En cuotas" },
  { valor: "ADVANCE", etiqueta: "Con anticipo" },
];

export function CondicionesPagoPage(): React.JSX.Element {
  const { activeCompany } = useCompany();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const companyId = activeCompany?.id ?? null;

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [kind, setKind] = useState("CASH");
  const [days, setDays] = useState("");

  const condiciones = useQuery({
    queryKey: ["comercial", "condiciones-pago"],
    queryFn: () => comercial.condicionesPago(),
    enabled: Boolean(companyId),
    retry: false,
  });

  const crear = useMutation({
    mutationFn: () =>
      comercial.crearCondicionPago({
        code,
        name,
        kind,
        days: kind === "DAYS" && days ? Number(days) : null,
      }),
    onSuccess: (creada: PaymentTerm) => {
      notify({ type: "success", title: "Condición registrada", description: `${creada.code} · ${creada.name}` });
      setCode("");
      setName("");
      setDays("");
      void queryClient.invalidateQueries({ queryKey: ["comercial", "condiciones-pago"] });
    },
    onError: (err: unknown) => {
      notify({
        type: "error",
        title: "No fue posible registrar la condición",
        description: err instanceof Error ? err.message : "Error inesperado",
      });
    },
  });

  if (!companyId) {
    return (
      <PageContent maxWidth="full">
        <PageHeader title="Condiciones de pago" crumbs={[{ label: "Comercial" }, { label: "Condiciones de pago" }]} />
        <div className="rounded-md border border-warning-100 bg-warning-100/40 p-4 text-sm text-warning-600" role="alert">
          Seleccione una empresa para trabajar con sus condiciones de pago.
        </div>
      </PageContent>
    );
  }

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Condiciones de pago"
        description="Los plazos con que opera esta empresa. Ninguno viene de fábrica."
        crumbs={[{ label: "Comercial" }, { label: "Condiciones de pago" }]}
      />

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Nueva condición</h2>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Código" required>
            <TextInput value={code} onChange={(e) => setCode(e.target.value)} placeholder="Ej. 30D" required />
          </FormField>
          <FormField label="Nombre" required>
            <TextInput value={name} onChange={(e) => setName(e.target.value)} placeholder="30 días" required />
          </FormField>
          <FormField label="Tipo" required>
            <select
              value={kind}
              onChange={(e) => setKind(e.target.value)}
              className="h-10 w-44 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
            >
              {TIPOS.map((t) => (
                <option key={t.valor} value={t.valor}>
                  {t.etiqueta}
                </option>
              ))}
            </select>
          </FormField>
          {kind === "DAYS" ? (
            <FormField label="Días" required>
              <TextInput value={days} onChange={(e) => setDays(e.target.value)} placeholder="30" required />
            </FormField>
          ) : null}
          <AsyncButton
            type="submit"
            variant="primary"
            disabled={!code || !name || (kind === "DAYS" && !days)}
            onClick={async () => {
              await crear.mutateAsync();
            }}
          >
            Registrar
          </AsyncButton>
        </form>
      </section>

      <section className="rounded-lg border border-border-default bg-surface-0 p-4">
        <DataTable
          columns={[
            { header: "Código", accessorKey: "code" },
            { header: "Nombre", accessorKey: "name" },
            { header: "Tipo", accessorKey: "kind" },
            { header: "Días", accessorFn: (f: PaymentTerm) => f.days ?? "—", id: "dias" },
            { header: "Estado", accessorKey: "status" },
          ]}
          data={condiciones.data?.items ?? []}
          loading={condiciones.isLoading}
          error={condiciones.isError ? "No fue posible cargar las condiciones de pago." : null}
          emptyTitle="Sin condiciones de pago"
          emptyDescription="El catálogo nace vacío: «contado» y «30 días» son datos de esta empresa."
          getRowId={(f) => f.id}
        />
      </section>
    </PageContent>
  );
}
