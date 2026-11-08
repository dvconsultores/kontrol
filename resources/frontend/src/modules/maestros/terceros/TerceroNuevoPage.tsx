/** Tercero nuevo — alta en pantalla completa (FR-002-042, WF-01). */
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";

import { ApiError, apiFetch } from "@/api/client";
import type { Party } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Autorizado } from "@/components/Autorizado";
import { Button } from "@/components/Button";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { UnsavedChangesGuard } from "@/components/UnsavedChangesGuard";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";

type PersonType = "JURIDICA" | "NATURAL" | "GUBERNAMENTAL" | "PUBLICA" | "EXTRANJERA";
type Role = "CLIENTE" | "PROVEEDOR" | "TRANSPORTISTA" | "CONDUCTOR" | "VENDEDOR" | "BENEFICIARIO";

const ROLES: Role[] = ["CLIENTE", "PROVEEDOR", "TRANSPORTISTA", "CONDUCTOR", "VENDEDOR", "BENEFICIARIO"];

const ROLE_LABELS: Record<Role, string> = {
  CLIENTE: "Cliente",
  PROVEEDOR: "Proveedor",
  TRANSPORTISTA: "Transportista",
  CONDUCTOR: "Conductor",
  VENDEDOR: "Vendedor",
  BENEFICIARIO: "Beneficiario",
};

const PERSON_TYPE_OPTIONS: { value: PersonType; label: string }[] = [
  { value: "JURIDICA", label: "Jurídica" },
  { value: "NATURAL", label: "Natural" },
  { value: "GUBERNAMENTAL", label: "Gubernamental" },
  { value: "PUBLICA", label: "Pública" },
  { value: "EXTRANJERA", label: "Extranjera" },
];


export function TerceroNuevoPage(): React.JSX.Element {
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [personType, setPersonType] = useState<PersonType>("JURIDICA");
  const [taxId, setTaxId] = useState("");
  const [legalName, setLegalName] = useState("");
  const [tradeName, setTradeName] = useState("");
  const [roles, setRoles] = useState<Role[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [duplicatePartyId, setDuplicatePartyId] = useState<string | null>(null);
    const [createdId, setCreatedId] = useState<string | null>(null);

  const dirty =
    code.trim() !== "" ||
    name.trim() !== "" ||
    personType !== "JURIDICA" ||
    taxId.trim() !== "" ||
    legalName.trim() !== "" ||
    tradeName.trim() !== "" ||
    roles.length > 0;

  const toggleRole = (role: Role) => {
    setRoles((current) =>
      current.includes(role) ? current.filter((candidate) => candidate !== role) : [...current, role],
    );
    setError(null);
  };

  const guardar = async () => {
    setError(null);
    setDuplicatePartyId(null);

    if (!code.trim()) {
      setError("El código es obligatorio.");
      return;
    }
    if (!name.trim()) {
      setError("El nombre es obligatorio.");
      return;
    }
    if (roles.length === 0) {
      setError("Seleccione al menos un rol.");
      return;
    }

    const body = {
      code: code.trim(),
      name: name.trim(),
      person_type: personType,
      roles,
      tax_id: taxId.trim() || null,
      legal_name: legalName.trim() || null,
      trade_name: tradeName.trim() || null,
    };

    try {
      const response = await apiFetch<Party>("/maestros/terceros", {
        method: "POST",
        body,
      });
      notify({ type: "success", title: "Tercero creado" });
      setCreatedId(response.id);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
        const duplicateId = err.details?.party_id;
        if (typeof duplicateId === "string") {
          setDuplicatePartyId(duplicateId);
        }
        notify({ type: "error", title: "No fue posible guardar el tercero", description: err.message });
      } else {
        setError("No fue posible guardar el tercero.");
        notify({ type: "error", title: "No fue posible guardar el tercero" });
      }
    }
  };

  useEffect(() => {
    if (createdId) {
      navigate(`/maestros/terceros/${createdId}`);
    }
  }, [createdId, navigate]);

  return (
    <PageContent maxWidth="lg">
      <UnsavedChangesGuard hasUnsavedChanges={dirty && createdId === null} />
      <PageHeader
        title="Nuevo tercero"
        crumbs={[
          { label: "Maestros" },
          { label: "Terceros", to: "/maestros/terceros" },
          { label: "Nuevo" },
        ]}
      />
      <form noValidate onSubmit={(e) => e.preventDefault()}>
        <div className="grid gap-5">
          <div className="grid gap-4 md:grid-cols-2">
            <FormField label="Código" htmlFor="code" required>
              <TextInput
                id="code"
                value={code}
                onChange={(e) => {
                  setCode(e.target.value);
                  setError(null);
                }}
                autoComplete="off"
              />
            </FormField>
            <FormField label="Nombre" htmlFor="name" required>
              <TextInput
                id="name"
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  setError(null);
                }}
                autoComplete="off"
              />
            </FormField>
            <FormField label="RIF" htmlFor="tax_id">
              <TextInput
                id="tax_id"
                value={taxId}
                onChange={(e) => {
                  setTaxId(e.target.value);
                  setError(null);
                }}
                autoComplete="off"
              />
            </FormField>
            <FormField label="Tipo de persona" htmlFor="person_type">
              <select
                id="person_type"
                value={personType}
                onChange={(e) => setPersonType(e.target.value as PersonType)}
                className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
              >
                {PERSON_TYPE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </FormField>
            <FormField label="Razón social" htmlFor="legal_name">
              <TextInput
                id="legal_name"
                value={legalName}
                onChange={(e) => {
                  setLegalName(e.target.value);
                  setError(null);
                }}
                autoComplete="off"
              />
            </FormField>
            <FormField label="Nombre comercial" htmlFor="trade_name">
              <TextInput
                id="trade_name"
                value={tradeName}
                onChange={(e) => {
                  setTradeName(e.target.value);
                  setError(null);
                }}
                autoComplete="off"
              />
            </FormField>
          </div>

          <fieldset className="rounded-lg border border-border-default p-4">
            <legend className="px-1 text-sm font-medium text-text-900">Roles</legend>
            <div className="grid gap-2 sm:grid-cols-2 md:grid-cols-3">
              {ROLES.map((role) => (
                <label key={role} className="flex items-center gap-2 text-sm text-text-900">
                  <input
                    type="checkbox"
                    checked={roles.includes(role)}
                    onChange={() => toggleRole(role)}
                    className="size-4 rounded border-border-default"
                  />
                  {ROLE_LABELS[role]}
                </label>
              ))}
            </div>
          </fieldset>

          {error ? (
            <p role="alert" className="text-sm text-danger-600">
              {error}{" "}
              {duplicatePartyId ? (
                <Link
                  to={`/maestros/terceros/${duplicatePartyId}`}
                  className="font-medium underline"
                >
                  Ver tercero existente
                </Link>
              ) : null}
            </p>
          ) : null}

          <div className="flex items-center justify-end gap-2">
            <Link to="/maestros/terceros">
              <Button variant="secondary" type="button">
                Cancelar
              </Button>
            </Link>
            <Autorizado operacion={["POST", "/maestros/terceros"]}>
              <AsyncButton type="submit" onClick={guardar}>
                Guardar tercero
              </AsyncButton>
            </Autorizado>
          </div>
        </div>
      </form>
    </PageContent>
  );
}
