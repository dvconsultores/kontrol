/** Requisiciones — necesidades y aprobación (FR-004-001/002, WF-02). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { Link } from "react-router";

import { apiFetch } from "@/api/client";
import type { PagedResult, RequisitionSummary } from "@/api/types";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Autorizado } from "@/components/Autorizado";
import { Button } from "@/components/Button";
import { DataTable } from "@/components/DataTable";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";

const columnHelper = createColumnHelper<RequisitionSummary>();

export function RequisicionesPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();

  const query = useQuery({
    queryKey: ["compras", "requisiciones"],
    queryFn: () => apiFetch<PagedResult<RequisitionSummary>>("/purchasing/requisitions"),
    retry: false,
  });

  const runTransition = async (id: string, target: string): Promise<void> => {
    await apiFetch(`/purchasing/requisitions/${id}/transition`, { method: "POST", body: { target } });
    await queryClient.invalidateQueries({ queryKey: ["compras", "requisiciones"] });
    notify({ type: "success", title: "Requisición actualizada", description: `Estado → ${target}` });
  };

  const columns = [
    columnHelper.accessor("code", { header: "Código" }),
    columnHelper.accessor("requester_id", { header: "Solicitante" }),
    columnHelper.accessor("cost_center_id", { header: "Centro de costo" }),
    columnHelper.accessor("need_date", { header: "Necesidad" }),
    columnHelper.accessor("status", { header: "Estado" }),
    columnHelper.display({
      id: "ver",
      header: "Ver",
      cell: ({ row }) => (
        <Link to={`/compras/requisiciones/${row.original.id}`}>
          <Button variant="secondary" size="sm">
            Ver
          </Button>
        </Link>
      ),
    }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => {
        const s = row.original.status;
        const autorizado = puede("POST", "/purchasing/requisitions/_/transition");
        if (!autorizado) {
          return null;
        }
        return (
          <div className="flex justify-end gap-1">
            {s === "DRAFT" ? (
              <AsyncButton size="sm" variant="secondary" onClick={() => runTransition(row.original.id, "SUBMITTED")}>
                enviar
              </AsyncButton>
            ) : null}
            {s === "SUBMITTED" ? (
              <>
                <AsyncButton size="sm" variant="secondary" onClick={() => runTransition(row.original.id, "APPROVED")}>
                  aprobar
                </AsyncButton>
                <AsyncButton size="sm" variant="danger" onClick={() => runTransition(row.original.id, "REJECTED")}>
                  rechazar
                </AsyncButton>
              </>
            ) : null}
          </div>
        );
      },
    }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Requisiciones"
        description="Necesidades de compra con líneas y aprobación."
        crumbs={[{ label: "Compras" }, { label: "Requisiciones" }]}
        actions={
          <Autorizado operacion={["POST", "/purchasing/requisitions"]}>
            <Link to="/compras/requisiciones/nueva">
              <Button>Nueva requisición</Button>
            </Link>
          </Autorizado>
        }
      />
      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar las requisiciones." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin requisiciones"
        emptyDescription="Aún no hay requisiciones registradas."
      />
    </PageContent>
  );
}
