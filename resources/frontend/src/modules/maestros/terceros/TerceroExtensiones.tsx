import { useState } from "react";
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
import type { Party } from "@/api/types";
import type { ReactNode } from "react";

type CampoExtension = {
  name: string;
  label: string;
  tipo?: "texto" | "numero" | "booleano" | "lista" | "fecha";
};

type FilaExtension = {
  id: string;
  party_id: string;
  version: number;
  credit_days?: number;
  approval_status?: string;
  [campo: string]: unknown;
};

const SECCIONES: Record<
  string,
  { titulo: string; ruta: string; campos: CampoExtension[] }
> = {
  CLIENTE: {
    titulo: "Cliente",
    ruta: "customer",
    campos: [
      { name: "salesperson", label: "Vendedor" },
      { name: "zone", label: "Zona" },
      { name: "price_list", label: "Lista de precios" },
      { name: "payment_term", label: "Condición de pago" },
      { name: "credit_days", label: "Días de crédito", tipo: "numero" },
      { name: "credit_limit", label: "Límite de crédito", tipo: "texto" },
      { name: "blocked", label: "Bloqueado", tipo: "booleano" },
      { name: "block_reason", label: "Motivo de bloqueo" },
    ],
  },
  PROVEEDOR: {
    titulo: "Proveedor",
    ruta: "supplier",
    campos: [
      { name: "category", label: "Categoría" },
      { name: "buyer", label: "Comprador" },
      { name: "payment_term", label: "Condición de pago" },
      { name: "default_currency", label: "Moneda" },
      { name: "withholding_profile", label: "Perfil de retención" },
    ],
  },
  TRANSPORTISTA: {
    titulo: "Transportista",
    ruta: "carrier",
    campos: [
      { name: "registration", label: "Matrícula o registro" },
      { name: "insurance", label: "Seguro" },
      { name: "permits", label: "Permisos", tipo: "lista" },
    ],
  },
  CONDUCTOR: {
    titulo: "Conductor",
    ruta: "driver",
    campos: [
      { name: "license", label: "Licencia" },
      { name: "categories", label: "Categorías", tipo: "lista" },
      { name: "expiry", label: "Vencimiento", tipo: "fecha" },
      { name: "restrictions", label: "Restricciones" },
    ],
  },
};

function valorInicial(fila: FilaExtension, campo: CampoExtension): string | boolean {
  const valor = fila[campo.name];
  if (campo.tipo === "booleano") return Boolean(valor);
  if (Array.isArray(valor)) return valor.join(", ");
  if (campo.tipo === "fecha" && typeof valor === "string") return valor.slice(0, 10);
  if (valor === null || valor === undefined) return "";
  return String(valor);
}

function valorEnviado(campo: CampoExtension, valor: string | boolean): unknown {
  if (campo.tipo === "booleano") return valor;
  if (campo.tipo === "lista") {
    const lista = String(valor)
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    return lista;
  }
  if (campo.tipo === "numero") return Number(valor);
  if (campo.tipo === "fecha") return valor ? `${valor}T00:00:00+00:00` : null;
  if (campo.name === "credit_days" && valor === "") return 0;
  return valor === "" ? null : String(valor);
}

function FormularioExtension({
  fila,
  campos,
  editable,
  partyId,
  titulo,
  ruta,
  children,
}: {
  fila: FilaExtension;
  campos: CampoExtension[];
  editable: boolean;
  partyId: string;
  titulo: string;
  ruta: string;
  children?: (fila: FilaExtension) => ReactNode;
}) {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const [valores, setValores] = useState(() => {
    const iniciales: Record<string, string | boolean> = {};
    for (const campo of campos) {
      iniciales[campo.name] = valorInicial(fila, campo);
    }
    return iniciales;
  });
  const [errorVersion, setErrorVersion] = useState(false);
  const [errorPantalla, setErrorPantalla] = useState<string | null>(null);

  const cambios: Record<string, unknown> = {};
  for (const campo of campos) {
    const actual = valores[campo.name];
    const inicial = valorInicial(fila, campo);
    if (actual !== inicial) {
      cambios[campo.name] = valorEnviado(campo, actual);
    }
  }
  const hayCambios = Object.keys(cambios).length > 0;

  async function guardar() {
    setErrorPantalla(null);
    try {
      await apiFetch(`/maestros/terceros/${partyId}/${ruta}`, {
        method: "PUT",
        body: cambios,
        ifMatch: String(fila.version),
      });
      notify({ type: "success", title: `${titulo} guardado` });
      await queryClient.invalidateQueries({ queryKey: ["maestros"] });
      setErrorVersion(false);
    } catch (err) {
      if (
        err instanceof ApiError &&
        err.status === 409 &&
        err.code === "VERSION_CONFLICT"
      ) {
        setErrorVersion(true);
        setErrorPantalla(null);
        return;
      }
      const mensaje =
        err instanceof ApiError ? err.message : "Error al guardar";
      setErrorVersion(false);
      setErrorPantalla(mensaje);
    }
  }

  return (
    <div key={fila.version} className="space-y-4">
      {campos.map((campo) => (
        <FormField key={campo.name} label={campo.label}>
          {campo.tipo === "booleano" ? (
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={Boolean(valores[campo.name])}
                disabled={!editable}
                onChange={(event) =>
                  setValores((previos) => ({
                    ...previos,
                    [campo.name]: event.target.checked,
                  }))
                }
              />
              {campo.label}
            </label>
          ) : (
            <TextInput
              type={
                campo.tipo === "numero"
                  ? "number"
                  : campo.tipo === "fecha"
                    ? "date"
                    : "text"
              }
              min={campo.tipo === "numero" ? 0 : undefined}
              inputMode={campo.name === "credit_limit" ? "decimal" : undefined}
              value={String(valores[campo.name] ?? "")}
              disabled={!editable}
              onChange={(event) =>
                setValores((previos) => ({
                  ...previos,
                  [campo.name]: event.target.value,
                }))
              }
            />
          )}
        </FormField>
      ))}
      {errorPantalla && (
        <div
          role="alert"
          className="rounded-md border border-danger-100 bg-danger-100/40 p-3 text-sm text-danger-600"
        >
          {errorPantalla}
        </div>
      )}
      {errorVersion && (
        <div
          role="alert"
          className="rounded-md border border-danger-100 bg-danger-100/40 p-3 text-sm text-danger-600"
        >
          Otro usuario modificó este registro. Recargue para ver los cambios.
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              void queryClient.invalidateQueries({ queryKey: ["maestros"] });
            }}
          >
            Recargar
          </Button>
        </div>
      )}
      {editable && (
        <Autorizado
          operacion={["PUT", `/maestros/terceros/${partyId}/${ruta}`]}
        >
          <AsyncButton onClick={guardar} disabled={!hayCambios}>
            Guardar {titulo}
          </AsyncButton>
        </Autorizado>
      )}
      {children?.(fila)}
    </div>
  );
}

function SeccionExtension({
  partyId,
  titulo,
  ruta,
  campos,
  editable,
  children,
}: {
  partyId: string;
  titulo: string;
  ruta: string;
  campos: CampoExtension[];
  editable: boolean;
  children?: (fila: FilaExtension) => ReactNode;
}) {
  const { activeCompany } = useCompany();
  const query = useQuery<FilaExtension, ApiError>({
    queryKey: ["maestros", "tercero-extension", activeCompany?.id, partyId, ruta],
    queryFn: () => apiFetch<FilaExtension>(`/maestros/terceros/${partyId}/${ruta}`),
    retry: false,
  });

  if (query.isError) {
    return (
      <div className="rounded-lg border border-border-default bg-surface-0 p-6">
        <h2 className="mb-4 text-lg font-semibold text-text-900">{titulo}</h2>
        <div
          role="alert"
          className="rounded-md border border-danger-100 bg-danger-100/40 p-3 text-sm text-danger-600"
        >
          No fue posible cargar {titulo}.
        </div>
      </div>
    );
  }

  if (!query.data) return null;
  const fila = query.data;

  return (
    <div className="rounded-lg border border-border-default bg-surface-0 p-6">
      <h2 className="mb-4 text-lg font-semibold text-text-900">{titulo}</h2>
      <FormularioExtension
        fila={fila}
        campos={campos}
        editable={editable}
        partyId={partyId}
        titulo={titulo}
        ruta={ruta}
      >
        {children}
      </FormularioExtension>
    </div>
  );
}

function AprobacionProveedor({
  partyId,
  estado,
  allowedActions,
}: {
  partyId: string;
  estado: string;
  allowedActions: Party["allowed_actions"];
}) {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const [motivo, setMotivo] = useState("");
  const [abierto, setAbierto] = useState(false);
  const [errorAprobacion, setErrorAprobacion] = useState<string[] | null>(null);
  const [errorRechazo, setErrorRechazo] = useState<string | null>(null);
  const [errorPantalla, setErrorPantalla] = useState<string | null>(null);

  const estadoTexto =
    estado === "PENDING_APPROVAL"
      ? "Pendiente"
      : estado === "APPROVED"
        ? "Aprobado"
        : "Rechazado";

  async function aprobar() {
    setErrorPantalla(null);
    setErrorAprobacion(null);
    try {
      await apiFetch(`/maestros/terceros/${partyId}/roles/PROVEEDOR/approve`, {
        method: "POST",
      });
      notify({ type: "success", title: "Proveedor aprobado" });
      await queryClient.invalidateQueries({ queryKey: ["maestros"] });
    } catch (err) {
      if (
        err instanceof ApiError &&
        err.status === 409 &&
        err.code === "SUPPLIER_APPROVAL_PRECONDITION"
      ) {
        const missing = (err.details?.missing as string[] | undefined) ?? [];
        const requisitos: string[] = [];
        if (missing.includes("tax_id")) requisitos.push("RIF del tercero");
        if (missing.includes("verified_bank_account"))
          requisitos.push("Una cuenta bancaria verificada");
        setErrorAprobacion(requisitos);
        return;
      }
      const mensaje =
        err instanceof ApiError ? err.message : "Error al aprobar";
      setErrorPantalla(mensaje);
    }
  }

  async function rechazar() {
    if (!motivo.trim()) {
      setErrorRechazo("Indica el motivo del rechazo");
      return;
    }
    setErrorRechazo(null);
    setErrorPantalla(null);
    try {
      await apiFetch(`/maestros/terceros/${partyId}/roles/PROVEEDOR/reject`, {
        method: "POST",
        body: { reason: motivo.trim() },
      });
      notify({ type: "success", title: "Proveedor rechazado" });
      await queryClient.invalidateQueries({ queryKey: ["maestros"] });
      setAbierto(false);
      setMotivo("");
    } catch (err) {
      const mensaje =
        err instanceof ApiError ? err.message : "Error al rechazar";
      setErrorPantalla(mensaje);
    }
  }

  async function reenviar() {
    setErrorPantalla(null);
    try {
      await apiFetch(`/maestros/terceros/${partyId}/roles/PROVEEDOR/resubmit`, {
        method: "POST",
      });
      notify({ type: "success", title: "Proveedor reenviado a aprobación" });
      await queryClient.invalidateQueries({ queryKey: ["maestros"] });
    } catch (err) {
      const mensaje =
        err instanceof ApiError ? err.message : "Error al reenviar";
      setErrorPantalla(mensaje);
    }
  }

  return (
    <div className="mt-4 space-y-3">
      <div className="text-sm text-text-900">
        Estado de aprobación: {estadoTexto}
      </div>
      {estado !== "APPROVED" && (
        <div
          role="note"
          className="rounded-md border border-danger-100 bg-danger-100/40 p-3 text-sm text-danger-600"
        >
          No se pueden registrar pagos ni anticipos a este proveedor hasta
          aprobarlo.
        </div>
      )}
      {errorAprobacion && (
        <div
          role="alert"
          className="rounded-md border border-danger-100 bg-danger-100/40 p-3 text-sm text-danger-600"
        >
          Faltan requisitos para aprobar:
          <ul className="list-disc pl-5">
            {errorAprobacion.map((requisito) => (
              <li key={requisito}>{requisito}</li>
            ))}
          </ul>
        </div>
      )}
      {errorPantalla && (
        <div
          role="alert"
          className="rounded-md border border-danger-100 bg-danger-100/40 p-3 text-sm text-danger-600"
        >
          {errorPantalla}
        </div>
      )}
      {allowedActions.approve === true && (
        <Autorizado
          operacion={[
            "POST",
            `/maestros/terceros/${partyId}/roles/PROVEEDOR/approve`,
          ]}
        >
          <AsyncButton onClick={aprobar}>Aprobar proveedor</AsyncButton>
        </Autorizado>
      )}
      {allowedActions.reject === true && (
        <Autorizado
          operacion={[
            "POST",
            `/maestros/terceros/${partyId}/roles/PROVEEDOR/reject`,
          ]}
        >
          <Button variant="secondary" onClick={() => setAbierto(true)}>
            Rechazar proveedor
          </Button>
        </Autorizado>
      )}
      {allowedActions.resubmit === true && (
        <Autorizado
          operacion={[
            "POST",
            `/maestros/terceros/${partyId}/roles/PROVEEDOR/resubmit`,
          ]}
        >
          <AsyncButton onClick={reenviar}>Reenviar a aprobación</AsyncButton>
        </Autorizado>
      )}
      <ConfirmationDialog
        open={abierto}
        title="Rechazar proveedor"
        danger
        confirmLabel="Rechazar"
        onConfirm={rechazar}
        onCancel={() => {
          setAbierto(false);
          setErrorRechazo(null);
        }}
      >
        <div className="space-y-2">
          <TextInput
            aria-label="Motivo del rechazo"
            value={motivo}
            onChange={(event) => setMotivo(event.target.value)}
          />
          {errorRechazo && (
            <div
              role="alert"
              className="rounded-md border border-danger-100 bg-danger-100/40 p-3 text-sm text-danger-600"
            >
              {errorRechazo}
            </div>
          )}
        </div>
      </ConfirmationDialog>
    </div>
  );
}

export function TerceroExtensiones({
  partyId,
  roles,
  editable,
  allowedActions,
}: {
  partyId: string;
  roles: string[];
  editable: boolean;
  allowedActions: Party["allowed_actions"];
}) {
  return (
    <div className="space-y-6">
      {roles.map((rol) => {
        const seccion = SECCIONES[rol];
        if (!seccion) return null;
        return (
          <SeccionExtension
            key={rol}
            partyId={partyId}
            titulo={seccion.titulo}
            ruta={seccion.ruta}
            campos={seccion.campos}
            editable={editable}
          >
            {rol === "PROVEEDOR"
              ? (fila) => (
                  <AprobacionProveedor
                    partyId={partyId}
                    estado={String(fila.approval_status ?? "")}
                    allowedActions={allowedActions}
                  />
                )
              : undefined}
          </SeccionExtension>
        );
      })}
    </div>
  );
}
