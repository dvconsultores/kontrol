/** Listas de precios, versiones e ítems — Spec 012.
 *
 * Es la pantalla con más jerarquía de KONTROL: lista → versión → ítem. Los
 * identificadores de los padres quedan **fijados al abrir el formulario**, y la
 * empresa también: cambiar el selector con el formulario abierto no puede
 * convertir la escritura en otra empresa.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";
import { comercial, type PriceList, type PriceListItem, type PriceListVersion } from "./api";

interface Moneda {
  id: string;
  code: string;
}

export function ListasPrecioPage(): React.JSX.Element {
  const { activeCompany } = useCompany();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const companyId = activeCompany?.id ?? null;

  const [seleccionada, setSeleccionada] = useState<string | null>(null);
  const [versionAbierta, setVersionAbierta] = useState<PriceListVersion | null>(null);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [currencyId, setCurrencyId] = useState("");
  const [itemId, setItemId] = useState("");
  const [precio, setPrecio] = useState("");

  const listas = useQuery({
    queryKey: ["comercial", "listas-precio"],
    queryFn: () => comercial.listas(),
    enabled: Boolean(companyId),
    retry: false,
  });

  const monedas = useQuery({
    queryKey: ["tesoreria", "monedas"],
    queryFn: () => apiFetch<Moneda[]>("/treasury/currencies"),
    enabled: Boolean(companyId),
    retry: false,
  });

  const detalle = useQuery({
    queryKey: ["comercial", "listas-precio", seleccionada],
    queryFn: () => comercial.lista(seleccionada ?? ""),
    enabled: Boolean(companyId && seleccionada),
    retry: false,
  });

  const items = useQuery({
    queryKey: ["comercial", "items", versionAbierta?.price_list_id, versionAbierta?.id],
    queryFn: () => comercial.items(versionAbierta?.price_list_id ?? "", versionAbierta?.id ?? ""),
    enabled: Boolean(companyId && versionAbierta),
    retry: false,
  });

  const invalidar = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["comercial"] });
  };

  const crearLista = useMutation({
    mutationFn: () =>
      comercial.crearLista({ code, name, currency_id: currencyId }),
    onSuccess: (creada: PriceList) => {
      notify({ type: "success", title: "Lista creada", description: `${creada.code} · ${creada.name}` });
      setCode("");
      setName("");
      invalidar();
    },
    onError: (err: unknown) => {
      notify({
        type: "error",
        title: "No fue posible crear la lista",
        description: err instanceof Error ? err.message : "Error inesperado",
      });
    },
  });

  const crearVersion = useMutation({
    mutationFn: (listaId: string) =>
      comercial.crearVersion(listaId, { valid_from: new Date().toISOString().slice(0, 10) }),
    onSuccess: () => {
      notify({ type: "success", title: "Versión creada", description: "Nace como borrador." });
      invalidar();
    },
    onError: (err: unknown) => {
      notify({
        type: "error",
        title: "No fue posible crear la versión",
        description: err instanceof Error ? err.message : "Error inesperado",
      });
    },
  });

  const publicar = useMutation({
    mutationFn: (v: PriceListVersion) =>
      comercial.transicionarVersion(v.price_list_id, v.id, "ACTIVE"),
    onSuccess: () => {
      notify({
        type: "success",
        title: "Versión publicada",
        description: "Publicar es irreversible: para cambiarla, cree otra versión.",
      });
      invalidar();
    },
    onError: (err: unknown) => {
      notify({
        type: "error",
        title: "No fue posible publicar",
        description: err instanceof Error ? err.message : "Error inesperado",
      });
    },
  });

  const crearItem = useMutation({
    mutationFn: () => {
      // Los padres y la empresa se leen del estado fijado al abrir el
      // formulario, no de lo que esté seleccionado al pulsar enviar.
      const padre = versionAbierta;
      if (!padre) throw new Error("No hay una versión abierta");
      return apiFetch<PriceListItem>(
        `/comercial/listas-precio/${encodeURIComponent(padre.price_list_id)}/versiones/${encodeURIComponent(padre.id)}/items`,
        { method: "POST", body: { item_id: itemId, unit_price: precio }, companyId },
      );
    },
    onSuccess: () => {
      notify({ type: "success", title: "Ítem añadido", description: "Precio registrado en el borrador." });
      setItemId("");
      setPrecio("");
      invalidar();
    },
    onError: (err: unknown) => {
      notify({
        type: "error",
        title: "No fue posible añadir el ítem",
        description: err instanceof Error ? err.message : "Error inesperado",
      });
    },
  });

  if (!companyId) {
    return (
      <PageContent maxWidth="full">
        <PageHeader title="Listas de precios" crumbs={[{ label: "Comercial" }, { label: "Listas de precios" }]} />
        <div className="rounded-md border border-warning-100 bg-warning-100/40 p-4 text-sm text-warning-600" role="alert">
          Seleccione una empresa para trabajar con sus listas de precios.
        </div>
      </PageContent>
    );
  }

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Listas de precios"
        description="Los precios de esta empresa, por versión. Una lista no se edita: se versiona."
        crumbs={[{ label: "Comercial" }, { label: "Listas de precios" }]}
      />

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Nueva lista</h2>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Código" required>
            <TextInput value={code} onChange={(e) => setCode(e.target.value)} placeholder="Ej. GENERAL" required />
          </FormField>
          <FormField label="Nombre" required>
            <TextInput value={name} onChange={(e) => setName(e.target.value)} placeholder="Lista general" required />
          </FormField>
          <FormField label="Moneda" required>
            <select
              value={currencyId}
              onChange={(e) => setCurrencyId(e.target.value)}
              className="h-10 w-40 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
            >
              <option value="">Seleccionar…</option>
              {(monedas.data ?? []).map((m) => (
                <option key={m.id} value={m.id}>
                  {m.code}
                </option>
              ))}
            </select>
          </FormField>
          <AsyncButton
            type="submit"
            variant="primary"
            disabled={!code || !name || !currencyId}
            onClick={async () => {
              await crearLista.mutateAsync();
            }}
          >
            Crear lista
          </AsyncButton>
        </form>
      </section>

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <DataTable
          columns={[
            { header: "Código", accessorKey: "code" },
            { header: "Nombre", accessorKey: "name" },
            { header: "Estado", accessorKey: "status" },
            {
              id: "acciones",
              header: "",
              cell: ({ row }) => (
                <AsyncButton
                  variant="secondary"
                  onClick={async () => {
                    setSeleccionada(row.original.id);
                    setVersionAbierta(null);
                  }}
                >
                  Ver versiones
                </AsyncButton>
              ),
            },
          ]}
          data={listas.data?.items ?? []}
          loading={listas.isLoading}
          error={listas.isError ? "No fue posible cargar las listas de precios." : null}
          emptyTitle="Sin listas de precios"
          emptyDescription="El catálogo nace vacío: ningún precio viene de fábrica."
          getRowId={(f) => f.id}
        />
      </section>

      {seleccionada && detalle.data ? (
        <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-semibold text-text-900">
              Versiones de {detalle.data.code} · {detalle.data.name}
            </h2>
            <AsyncButton
              variant="secondary"
              onClick={async () => {
                await crearVersion.mutateAsync(seleccionada);
              }}
            >
              Nueva versión
            </AsyncButton>
          </div>
          <DataTable
            columns={[
              { header: "N.º", accessorKey: "version_number" },
              { header: "Desde", accessorKey: "valid_from" },
              {
                header: "Hasta",
                accessorFn: (f: PriceListVersion) => f.valid_to ?? "abierta",
                id: "valid_to",
              },
              { header: "Estado", accessorKey: "status" },
              {
                id: "acciones",
                header: "",
                cell: ({ row }) => (
                  <div className="flex gap-2">
                    <AsyncButton
                      variant="secondary"
                      onClick={async () => {
                        setVersionAbierta(row.original);
                      }}
                    >
                      Ítems
                    </AsyncButton>
                    {row.original.status === "DRAFT" ? (
                      <AsyncButton
                        variant="primary"
                        onClick={async () => {
                          await publicar.mutateAsync(row.original);
                        }}
                      >
                        Publicar
                      </AsyncButton>
                    ) : null}
                  </div>
                ),
              },
            ]}
            data={detalle.data.versions}
            emptyTitle="Sin versiones"
            emptyDescription="Cree una versión en borrador para cargar precios."
            getRowId={(f) => f.id}
          />
        </section>
      ) : null}

      {versionAbierta ? (
        <section className="rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-2 text-base font-semibold text-text-900">
            Ítems de la versión {versionAbierta.version_number}
          </h2>
          {versionAbierta.status === "DRAFT" ? (
            <form className="mb-3 flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
              <FormField label="Artículo" required>
                <TextInput value={itemId} onChange={(e) => setItemId(e.target.value)} placeholder="Id del artículo" required />
              </FormField>
              <FormField label="Precio unitario" required>
                <TextInput value={precio} onChange={(e) => setPrecio(e.target.value)} placeholder="0.0000" required />
              </FormField>
              <AsyncButton
                type="submit"
                variant="primary"
                disabled={!itemId || !precio}
                onClick={async () => {
                  await crearItem.mutateAsync();
                }}
              >
                Añadir ítem
              </AsyncButton>
            </form>
          ) : (
            <p className="mb-3 text-sm text-text-500">
              Esta versión ya no admite cambios. Para modificar precios, cree una versión nueva.
            </p>
          )}
          <DataTable
            columns={[
              { header: "Artículo", accessorFn: (f: PriceListItem) => f.item_id ?? f.category_id ?? "—", id: "objetivo" },
              { header: "Presentación", accessorFn: (f: PriceListItem) => f.presentation_id ?? "—", id: "pres" },
              { header: "Desde cantidad", accessorFn: (f: PriceListItem) => f.min_quantity ?? "—", id: "min" },
              { header: "Precio", accessorKey: "unit_price" },
            ]}
            data={items.data?.items ?? []}
            loading={items.isLoading}
            error={items.isError ? "No fue posible cargar los ítems." : null}
            emptyTitle="Sin ítems"
            emptyDescription="Añada precios al borrador antes de publicarlo."
            getRowId={(f) => f.id}
          />
        </section>
      ) : null}
    </PageContent>
  );
}
