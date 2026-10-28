/** Asistente de producto — pantalla completa con pasos (FR-002-040, WF-002-A). */
import { useState, type ChangeEvent } from "react";
import { useNavigate } from "react-router";

import { apiFetch } from "@/api/client";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Autorizado } from "@/components/Autorizado";
import { AsyncCombobox } from "@/components/AsyncCombobox";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { UnsavedChangesGuard } from "@/components/UnsavedChangesGuard";

const STEPS = ["Identificación", "Datos fiscales", "Inventario", "Regulación"];

export function ProductoNuevoPage(): React.JSX.Element {
  const navigate = useNavigate();
  const { notify } = useNotifications();

  const [step, setStep] = useState(0);
  const [dirty, setDirty] = useState(false);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [shortDescription, setShortDescription] = useState("");
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [inventoryProfileId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const markDirty =
    (setter: (v: string) => void) => (e: ChangeEvent<HTMLInputElement>) => {
      setter(e.target.value);
      setDirty(true);
    };

  const canNext = step < STEPS.length - 1 && code.length > 0 && name.length > 0;

  const handleSubmit = async (): Promise<void> => {
    setError(null);
    try {
      await apiFetch("/maestros/catalogos/items", {
        method: "POST",
        body: {
          code,
          name,
          item_type: "PRODUCT",
          short_description: shortDescription || null,
          category_id: categoryId,
          inventory_profile_id: inventoryProfileId,
        },
      });
      notify({ type: "success", title: "Producto creado", description: `El producto ${name} fue registrado correctamente.` });
      navigate("/maestros/productos");
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear el producto";
      setError(message);
      notify({ type: "error", title: "No fue posible crear el producto", description: message });
    }
  };

  return (
    <PageContent maxWidth="lg">
      <UnsavedChangesGuard hasUnsavedChanges={dirty} />
      <PageHeader
        title="Nuevo producto"
        description="Asistente paso a paso para registrar un producto."
        crumbs={[{ label: "Maestros" }, { label: "Productos", to: "/maestros/productos" }, { label: "Nuevo" }]}
      />
      <nav aria-label="Progreso del asistente" className="mb-6 flex gap-2">
        {STEPS.map((label, i) => (
          <span
            key={label}
            className={`rounded px-3 py-1 text-sm ${i === step ? "bg-brand-600 text-white" : "bg-surface-100 text-text-500"}`}
          >
            {i + 1}. {label}
          </span>
        ))}
      </nav>

      <form
        className="space-y-5 rounded-lg border border-border-default bg-surface-0 p-6"
        onSubmit={(e) => {
          e.preventDefault();
          void handleSubmit();
        }}
        noValidate
      >
        {step === 0 ? (
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField label="Código" required>
              <TextInput value={code} onChange={markDirty(setCode)} required />
            </FormField>
            <FormField label="Nombre" required>
              <TextInput value={name} onChange={markDirty(setName)} required />
            </FormField>
            <FormField label="Descripción breve" className="sm:col-span-2">
              <TextInput value={shortDescription} onChange={markDirty(setShortDescription)} />
            </FormField>
            <FormField label="Rubro" help="Búsqueda asíncrona en el catálogo." className="sm:col-span-2">
              <AsyncCombobox
                value={categoryId}
                onChange={(v) => {
                  setCategoryId(v);
                  setDirty(true);
                }}
                searchUrl="/maestros/catalogos/taxonomia/search"
                label="Buscar rubro"
                placeholder="Buscar rubro…"
              />
            </FormField>
          </div>
        ) : null}

        {step === 1 ? (
          <div className="rounded-md border border-border-default p-4 text-sm text-text-500">
            Datos fiscales: el perfil fiscal se asigna versionado (no hardcodeado). Se conectará al núcleo fiscal en Spec 007.
          </div>
        ) : null}

        {step === 2 ? (
          <div className="rounded-md border border-border-default p-4 text-sm text-text-500">
            Inventario: se asigna un perfil de inventario versionado (stock/lote/serial/vencimiento).
          </div>
        ) : null}

        {step === 3 ? (
          <div className="rounded-md border border-border-default p-4 text-sm text-text-500">
            Regulación: perfil regulatorio (SICA/SIGESAI/SACS) — se detalla en Spec 008.
          </div>
        ) : null}

        {error ? (
          <p className="rounded-md border border-danger-100 bg-danger-100/40 p-3 text-sm text-danger-600" role="alert">
            {error}
          </p>
        ) : null}

        <div className="flex justify-between border-t border-border-default pt-4">
          <Button
            variant="secondary"
            onClick={() => setStep((s) => Math.max(0, s - 1))}
            disabled={step === 0}
          >
            Anterior
          </Button>
          {step < STEPS.length - 1 ? (
            <Button onClick={() => setStep((s) => s + 1)} disabled={!canNext}>
              Siguiente
            </Button>
          ) : (
            <Autorizado operacion={["POST", "/maestros/catalogos/items"]}>
              <AsyncButton type="submit" onClick={handleSubmit} loadingText="Guardando producto…">
                Guardar producto
              </AsyncButton>
            </Autorizado>
          )}
        </div>
      </form>
    </PageContent>
  );
}
