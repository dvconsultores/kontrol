import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";
import { apiFetch } from "@/api/client";
import { PageHeader } from "@/components/PageHeader";
import { PageContent } from "@/layout/PageContent";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { Button } from "@/components/Button";
import { AsyncButton } from "@/components/AsyncButton";
import { Autorizado } from "@/components/Autorizado";
import { UnsavedChangesGuard } from "@/components/UnsavedChangesGuard";
import { SelectorDeTercero } from "@/modules/maestros/terceros/SelectorDeTercero";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { INCOTERMS } from "./tipos";

type NuevaImportacion = {
  code: string;
  supplier_id: string;
  currency: string;
  incoterm: string;
  incoterm_place: string;
  payment_conditions: string;
  delivery_conditions: string;
  expected_dispatch_date: string;
  expected_arrival_date: string;
  notes: string;
};

const VACIO: NuevaImportacion = {
  code: "",
  supplier_id: "",
  currency: "VED",
  incoterm: "",
  incoterm_place: "",
  payment_conditions: "",
  delivery_conditions: "",
  expected_dispatch_date: "",
  expected_arrival_date: "",
  notes: "",
};

export function ImportacionNuevaPage() {
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const [form, setForm] = useState<NuevaImportacion>(VACIO);
  const [createdId, setCreatedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const dirty = JSON.stringify(form) !== JSON.stringify(VACIO);

  useEffect(() => {
    if (createdId) {
      navigate(`/compras/importaciones/${createdId}`);
    }
  }, [createdId, navigate]);

  const set = (campo: keyof NuevaImportacion, valor: string) => {
    setForm((prev) => ({ ...prev, [campo]: valor }));
  };

  const guardar = async () => {
    if (!form.code.trim() || !form.supplier_id) {
      setError("Indica el código y el proveedor.");
      return;
    }

    const body: Record<string, string> = {
      code: form.code.trim(),
      supplier_id: form.supplier_id,
      currency: form.currency,
    };
    if (form.incoterm) body.incoterm = form.incoterm;
    if (form.incoterm_place.trim()) body.incoterm_place = form.incoterm_place.trim();
    if (form.payment_conditions.trim()) body.payment_conditions = form.payment_conditions.trim();
    if (form.delivery_conditions.trim()) body.delivery_conditions = form.delivery_conditions.trim();
    if (form.expected_dispatch_date) body.expected_dispatch_date = form.expected_dispatch_date;
    if (form.expected_arrival_date) body.expected_arrival_date = form.expected_arrival_date;
    if (form.notes.trim()) body.notes = form.notes.trim();

    try {
      const detalle = await apiFetch<{ id: string }>("/importaciones", {
        method: "POST",
        body,
      });
      setCreatedId(detalle.id);
      notify({ type: "success", title: "Importación creada." });
    } catch (err) {
      const mensaje = err instanceof Error ? err.message : "Error al guardar.";
      setError(mensaje);
    }
  };

  return (
    <PageContent maxWidth="lg">
      <UnsavedChangesGuard hasUnsavedChanges={dirty && createdId === null} />
      <PageHeader
        title="Nueva importación"
        crumbs={[
          { label: "Compras", to: "/compras" },
          { label: "Importaciones", to: "/compras/importaciones" },
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
            <TextInput
              value={form.code}
              onChange={(e) => set("code", e.target.value)}
            />
          </FormField>
          <FormField label="Proveedor" required>
            <SelectorDeTercero
              value={form.supplier_id}
              onChange={(id) => set("supplier_id", id)}
              role="PROVEEDOR"
              soloActivos
              id="proveedor"
            />
          </FormField>
          <FormField label="Moneda">
            <TextInput
              value={form.currency}
              onChange={(e) => set("currency", e.target.value)}
            />
          </FormField>
          <FormField label="INCOTERM">
            <select
              className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
              value={form.incoterm}
              onChange={(e) => set("incoterm", e.target.value)}
            >
              <option value="">Sin definir</option>
              {INCOTERMS.map((incoterm) => (
                <option key={incoterm} value={incoterm}>
                  {incoterm}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Lugar del INCOTERM">
            <TextInput
              value={form.incoterm_place}
              onChange={(e) => set("incoterm_place", e.target.value)}
            />
          </FormField>
        </div>
        <FormField label="Condiciones de pago">
          <textarea
            className="min-h-20 w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
            value={form.payment_conditions}
            onChange={(e) => set("payment_conditions", e.target.value)}
          />
        </FormField>
        <FormField label="Condiciones de entrega">
          <textarea
            className="min-h-20 w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
            value={form.delivery_conditions}
            onChange={(e) => set("delivery_conditions", e.target.value)}
          />
        </FormField>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <FormField label="Despacho previsto">
            <TextInput
              type="date"
              value={form.expected_dispatch_date}
              onChange={(e) => set("expected_dispatch_date", e.target.value)}
            />
          </FormField>
          <FormField label="Llegada prevista">
            <TextInput
              type="date"
              value={form.expected_arrival_date}
              onChange={(e) => set("expected_arrival_date", e.target.value)}
            />
          </FormField>
        </div>
        <FormField label="Notas">
          <textarea
            className="min-h-20 w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
            value={form.notes}
            onChange={(e) => set("notes", e.target.value)}
          />
        </FormField>
        {error && (
          <div className="rounded-md border border-danger-100 bg-danger-100/40 p-3 text-sm text-danger-600">
            {error}
          </div>
        )}
        <div className="mt-6 flex gap-3">
          <Autorizado operacion={["POST", "/importaciones"]}>
            <AsyncButton type="submit" onClick={guardar}>
              Guardar
            </AsyncButton>
          </Autorizado>
          <Link to="/compras/importaciones">
            <Button variant="ghost">Cancelar</Button>
          </Link>
        </div>
      </form>
    </PageContent>
  );
}
