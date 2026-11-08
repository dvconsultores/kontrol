import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, apiFetch } from "@/api/client";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { Autorizado } from "@/components/Autorizado";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { PageHeader } from "@/components/PageHeader";
import { PageContent } from "@/layout/PageContent";
import { UnsavedChangesGuard } from "@/components/UnsavedChangesGuard";
import { TerceroDatos } from "./TerceroDatos";
import { TerceroExtensiones } from "./TerceroExtensiones";
import { TerceroHistorial } from "./TerceroHistorial";
import { PERSON_TYPES, ROLE_LABELS, type PartyDetail, terceroKey } from "./tipos";

function IdentificacionForm({
  party,
  onRecargar,
}: {
  party: PartyDetail;
  onRecargar: () => void;
}) {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const [form, setForm] = useState({
    name: party.name || "",
    person_type: party.person_type || "",
    legal_name: party.legal_name ?? "",
    trade_name: party.trade_name ?? "",
    tax_id: party.tax_id ?? "",
    nationality: party.nationality ?? "",
    residence: party.residence ?? "",
    economic_activity: party.economic_activity ?? "",
  });
  const [conflicto, setConflicto] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const dirty =
    form.name !== (party.name || "") ||
    form.person_type !== (party.person_type || "") ||
    form.legal_name !== (party.legal_name ?? "") ||
    form.trade_name !== (party.trade_name ?? "") ||
    form.tax_id !== (party.tax_id ?? "") ||
    form.nationality !== (party.nationality ?? "") ||
    form.residence !== (party.residence ?? "") ||
    form.economic_activity !== (party.economic_activity ?? "");

  const guardar = async () => {
    setConflicto(false);
    setError(null);

    if (!form.name.trim()) {
      setError("El nombre es obligatorio.");
      return;
    }

    const changes: Record<string, unknown> = {};
    if (form.name !== (party.name || "")) changes.name = form.name;
    if (form.person_type !== (party.person_type || ""))
      changes.person_type = form.person_type;
    if (form.legal_name !== (party.legal_name ?? ""))
      changes.legal_name = form.legal_name || null;
    if (form.trade_name !== (party.trade_name ?? ""))
      changes.trade_name = form.trade_name || null;
    if (form.tax_id !== (party.tax_id ?? ""))
      changes.tax_id = form.tax_id || null;
    if (form.nationality !== (party.nationality ?? ""))
      changes.nationality = form.nationality || null;
    if (form.residence !== (party.residence ?? ""))
      changes.residence = form.residence || null;
    if (form.economic_activity !== (party.economic_activity ?? ""))
      changes.economic_activity = form.economic_activity || null;

    try {
      await apiFetch(`/maestros/terceros/${party.id}`, {
        method: "PATCH",
        body: changes,
        ifMatch: String(party.version),
      });
      notify({ type: "success", title: "Cambios guardados" });
      void queryClient.invalidateQueries({ queryKey: ["maestros"] });
    } catch (err) {
      if (
        err instanceof ApiError &&
        err.status === 409 &&
        err.code === "VERSION_CONFLICT"
      ) {
        setConflicto(true);
      } else {
        setError(err instanceof Error ? err.message : "Error desconocido");
      }
    }
  };

  const handleInputChange =
    (field: keyof typeof form) =>
    (event: React.ChangeEvent<HTMLInputElement>) => {
      setForm((prev) => ({ ...prev, [field]: event.target.value }));
    };

  const handleSelectChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setForm((prev) => ({ ...prev, person_type: event.target.value }));
  };

  return (
    <div className="space-y-4">
      <UnsavedChangesGuard hasUnsavedChanges={dirty} />
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField label="Código">
          <TextInput value={party.code} disabled />
        </FormField>
        <FormField label="Nombre" required>
          <TextInput
            value={form.name}
            onChange={handleInputChange("name")}
            disabled={!party.allowed_actions.edit}
          />
        </FormField>
        <FormField label="Tipo de persona" required>
          <select
            className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
            value={form.person_type}
            onChange={handleSelectChange}
            disabled={!party.allowed_actions.edit}
          >
            {PERSON_TYPES.map((pt) => (
              <option key={pt.value} value={pt.value}>
                {pt.label}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="RIF">
          <TextInput
            value={form.tax_id}
            onChange={handleInputChange("tax_id")}
            disabled={!party.allowed_actions.edit}
          />
        </FormField>
        <FormField label="Razón social">
          <TextInput
            value={form.legal_name}
            onChange={handleInputChange("legal_name")}
            disabled={!party.allowed_actions.edit}
          />
        </FormField>
        <FormField label="Nombre comercial">
          <TextInput
            value={form.trade_name}
            onChange={handleInputChange("trade_name")}
            disabled={!party.allowed_actions.edit}
          />
        </FormField>
        <FormField label="Nacionalidad">
          <TextInput
            value={form.nationality}
            onChange={handleInputChange("nationality")}
            disabled={!party.allowed_actions.edit}
          />
        </FormField>
        <FormField label="Residencia">
          <TextInput
            value={form.residence}
            onChange={handleInputChange("residence")}
            disabled={!party.allowed_actions.edit}
          />
        </FormField>
        <FormField label="Actividad económica">
          <TextInput
            value={form.economic_activity}
            onChange={handleInputChange("economic_activity")}
            disabled={!party.allowed_actions.edit}
          />
        </FormField>
      </div>
      {error && (
        <div
          role="alert"
          className="rounded-md border border-danger-100 bg-danger-100/40 p-3 text-sm text-danger-600"
        >
          <p>{error}</p>
        </div>
      )}
      {conflicto && (
        <div
          role="alert"
          className="rounded-md border border-danger-100 bg-danger-100/40 p-3 text-sm text-danger-600"
        >
          <p>Otro usuario modificó este tercero. Recargue para ver los cambios.</p>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => {
              onRecargar();
              setConflicto(false);
              setError(null);
            }}
          >
            Recargar
          </Button>
        </div>
      )}
      {party.allowed_actions.edit && (
        <Autorizado operacion={["PATCH", `/maestros/terceros/${party.id}`]}>
          <AsyncButton
            onClick={guardar}
            disabled={!dirty || !party.allowed_actions.edit}
          >
            Guardar cambios
          </AsyncButton>
        </Autorizado>
      )}
    </div>
  );
}

export function TerceroDetallePage() {
  const { partyId } = useParams<{ partyId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { activeCompany } = useCompany();
  const companyId = activeCompany?.id;
  const [resetKey, setResetKey] = useState(0);

  const partyQuery = useQuery({
    queryKey: terceroKey(companyId, partyId ?? ""),
    queryFn: () => apiFetch<PartyDetail>(`/maestros/terceros/${partyId}`),
    retry: false,
    enabled: Boolean(partyId),
  });

  const [deleted, setDeleted] = useState(false);
  const [deactivateDialog, setDeactivateDialog] = useState(false);
  const [deleteDialog, setDeleteDialog] = useState(false);
  const [rolNuevo, setRolNuevo] = useState("");

  useEffect(() => {
    if (deleted) {
      navigate("/maestros/terceros");
    }
  }, [deleted, navigate]);

  if (partyQuery.isLoading) {
    return <PageContent maxWidth="lg">Cargando…</PageContent>;
  }

  if (partyQuery.isError) {
    const err = partyQuery.error;
    if (err instanceof ApiError && err.status === 404) {
      return (
        <PageContent maxWidth="lg">
          <p role="alert">Tercero no encontrado en esta empresa.</p>
          <Link to="/maestros/terceros">Volver a terceros</Link>
        </PageContent>
      );
    }
    return (
      <PageContent maxWidth="lg">
        <p role="alert">No fue posible cargar el tercero.</p>
      </PageContent>
    );
  }

  const party = partyQuery.data;
  if (!party) return null;

  const rolesNoAsignados = Object.keys(ROLE_LABELS).filter(
    (role) => !party.roles.includes(role),
  );

  const handleActivate = async () => {
    try {
      await apiFetch(`/maestros/terceros/${party.id}/activate`, {
        method: "POST",
      });
      notify({ type: "success", title: "Tercero activado" });
      void queryClient.invalidateQueries({ queryKey: ["maestros"] });
    } catch (err) {
      notify({
        type: "error",
        title: "No fue posible activar el tercero",
        description: err instanceof Error ? err.message : "Error desconocido",
      });
    }
  };

  const handleDeactivate = async () => {
    try {
      await apiFetch(`/maestros/terceros/${party.id}/deactivate`, {
        method: "POST",
      });
      setDeactivateDialog(false);
      notify({ type: "success", title: "Tercero desactivado" });
      void queryClient.invalidateQueries({ queryKey: ["maestros"] });
    } catch (err) {
      notify({
        type: "error",
        title: "No fue posible desactivar el tercero",
        description: err instanceof Error ? err.message : "Error desconocido",
      });
    }
  };

  const handleDelete = async () => {
    try {
      await apiFetch(`/maestros/terceros/${party.id}`, {
        method: "DELETE",
      });
      setDeleteDialog(false);
      setDeleted(true);
      notify({ type: "success", title: "Tercero eliminado" });
      void queryClient.invalidateQueries({ queryKey: ["maestros"] });
    } catch (err) {
      notify({
        type: "error",
        title: "No fue posible eliminar el tercero",
        description: err instanceof Error ? err.message : "Error desconocido",
      });
    }
  };

  const addRole = async (role: string) => {
    try {
      await apiFetch(`/maestros/terceros/${party.id}/roles/${role}`, {
        method: "POST",
      });
      setRolNuevo("");
      notify({ type: "success", title: "Rol agregado" });
      void queryClient.invalidateQueries({ queryKey: ["maestros"] });
    } catch (err) {
      notify({
        type: "error",
        title: "No fue posible agregar el rol",
        description: err instanceof Error ? err.message : "Error desconocido",
      });
    }
  };

  const removeRole = async (role: string) => {
    try {
      await apiFetch(`/maestros/terceros/${party.id}/roles/${role}`, {
        method: "DELETE",
      });
      notify({ type: "success", title: "Rol eliminado" });
      void queryClient.invalidateQueries({ queryKey: ["maestros"] });
    } catch (err) {
      notify({
        type: "error",
        title: "No fue posible quitar el rol",
        description: err instanceof Error ? err.message : "Error desconocido",
      });
    }
  };

  const rol = rolNuevo || rolesNoAsignados[0] || "";

  return (
    <PageContent maxWidth="lg">
      <PageHeader
        title={`${party.code} · ${party.name}`}
        status={
          <span>{party.status === "ACTIVE" ? "Activo" : "Inactivo"}</span>
        }
        crumbs={[
          { label: "Maestros" },
          { label: "Terceros", to: "/maestros/terceros" },
          { label: party.code },
        ]}
        actions={
          <div className="flex gap-2">
            {party.allowed_actions.activate && (
              <Autorizado
                operacion={["POST", `/maestros/terceros/${party.id}/activate`]}
              >
                <AsyncButton onClick={handleActivate}>Activar</AsyncButton>
              </Autorizado>
            )}
            {party.allowed_actions.deactivate && (
              <Autorizado
                operacion={[
                  "POST",
                  `/maestros/terceros/${party.id}/deactivate`,
                ]}
              >
                <Button
                  variant="secondary"
                  onClick={() => setDeactivateDialog(true)}
                >
                  Desactivar
                </Button>
              </Autorizado>
            )}
            {party.allowed_actions.delete && (
              <Autorizado
                operacion={["DELETE", `/maestros/terceros/${party.id}`]}
              >
                <Button
                  variant="secondary"
                  onClick={() => setDeleteDialog(true)}
                >
                  Eliminar
                </Button>
              </Autorizado>
            )}
          </div>
        }
      />

      <div className="space-y-6">
        {party.blocking_documents.length > 0 && (
          <section
            role="note"
            className="rounded-lg border border-border-default bg-surface-0 p-6"
          >
            <h2 className="mb-4 text-lg font-semibold text-text-900">
              Documentos activos que impiden desactivar
            </h2>
            <ul className="list-disc pl-5">
              {party.blocking_documents.map((doc) => (
                <li key={`${doc.module}-${doc.document}`}>
                  {`${doc.document} (${doc.module}): ${doc.count}`}
                </li>
              ))}
            </ul>
          </section>
        )}

        <section className="rounded-lg border border-border-default bg-surface-0 p-6">
          <h2 className="mb-4 text-lg font-semibold text-text-900">
            Identificación
          </h2>
          <IdentificacionForm
            key={`${party.version}-${resetKey}`}
            party={party}
            onRecargar={() => {
              setResetKey((prev) => prev + 1);
              void queryClient.invalidateQueries({
                queryKey: terceroKey(companyId, party.id),
              });
            }}
          />
        </section>

        <section className="rounded-lg border border-border-default bg-surface-0 p-6">
          <h2 className="mb-4 text-lg font-semibold text-text-900">Roles</h2>
          {party.allowed_actions.edit ? (
            <>
              <ul className="space-y-2">
                {party.roles.map((role) => (
                  <li key={role} className="flex items-center gap-2">
                    <span>{ROLE_LABELS[role] ?? role}</span>
                    <Autorizado
                      operacion={[
                        "DELETE",
                        `/maestros/terceros/${party.id}/roles/${role}`,
                      ]}
                    >
                      <AsyncButton
                        variant="ghost"
                        size="sm"
                        aria-label={`Quitar rol ${ROLE_LABELS[role] ?? role}`}
                        onClick={() => removeRole(role)}
                      >
                        Quitar
                      </AsyncButton>
                    </Autorizado>
                  </li>
                ))}
              </ul>
              {rolesNoAsignados.length > 0 && (
                <div className="mt-4 flex items-center gap-2">
                  <select
                    aria-label="Rol a agregar"
                    className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                    value={rol}
                    onChange={(e) => setRolNuevo(e.target.value)}
                  >
                    {rolesNoAsignados.map((role) => (
                      <option key={role} value={role}>
                        {ROLE_LABELS[role] ?? role}
                      </option>
                    ))}
                  </select>
                  <Autorizado
                    operacion={[
                      "POST",
                      `/maestros/terceros/${party.id}/roles/${rol}`,
                    ]}
                  >
                    <AsyncButton onClick={() => addRole(rol)}>
                      Agregar rol
                    </AsyncButton>
                  </Autorizado>
                </div>
              )}
            </>
          ) : (
            <ul className="list-disc pl-5">
              {party.roles.map((role) => (
                <li key={role}>{ROLE_LABELS[role] ?? role}</li>
              ))}
            </ul>
          )}
        </section>

        <TerceroDatos partyId={party.id} editable={party.allowed_actions.edit === true} />

        <TerceroExtensiones
          partyId={party.id}
          roles={party.roles}
          editable={party.allowed_actions.edit === true}
          allowedActions={party.allowed_actions}
        />

        <TerceroHistorial partyId={party.id} />
      </div>

      <ConfirmationDialog
        open={deactivateDialog}
        title="¿Desactivar este tercero?"
        danger
        onConfirm={handleDeactivate}
        onCancel={() => setDeactivateDialog(false)}
      />
      <ConfirmationDialog
        open={deleteDialog}
        title="¿Eliminar este tercero?"
        danger
        onConfirm={handleDelete}
        onCancel={() => setDeleteDialog(false)}
      />
    </PageContent>
  );
}
