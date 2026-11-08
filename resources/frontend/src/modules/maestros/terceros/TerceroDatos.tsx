import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { ApiError, apiFetch } from "@/api/client";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Autorizado } from "@/components/Autorizado";
import { TextInput } from "@/components/TextInput";
import { FilaDato, SeccionDatos } from "./SeccionDatos";

function resumenDireccion(fila: FilaDato): string {
  const direccion = typeof fila.address === "string" ? fila.address : "";
  return `${direccion}${fila.is_fiscal === true ? " · Fiscal" : ""}`;
}

function resumenContacto(fila: FilaDato): string {
  const nombre = typeof fila.name === "string" ? fila.name : "";
  const telefono = typeof fila.phone === "string" ? fila.phone : "";
  const correo = typeof fila.email === "string" ? fila.email : "";
  const dato = nombre || telefono || correo;
  return `${dato}${fila.preferred === true ? " · Preferido" : ""}`;
}

function resumenCuenta(fila: FilaDato): string {
  const banco = typeof fila.bank === "string" ? fila.bank : "";
  const numero = typeof fila.account_number === "string" ? fila.account_number : "";
  return `${banco} ${numero}${fila.verified === true ? " · Verificada" : ""}`;
}

function VerificarCuenta({
  partyId,
  fila,
  resumen,
}: {
  partyId: string;
  fila: FilaDato;
  resumen: (fila: FilaDato) => string;
}) {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const [evidence, setEvidence] = useState("");

  async function verificar() {
    if (evidence.trim() === "") {
      notify({
        type: "error",
        title: "Falta evidencia",
        description: "Escriba la evidencia de la verificación.",
      });
      return;
    }

    try {
      await apiFetch(
        `/maestros/terceros/${partyId}/bank-accounts/${fila.id}/verify`,
        {
          method: "POST",
          body: { evidence },
        },
      );
      notify({
        type: "success",
        title: "Cuenta verificada",
        description: "La cuenta bancaria fue verificada correctamente.",
      });
      void queryClient.invalidateQueries({ queryKey: ["maestros"] });
    } catch (error) {
      notify({
        type: "error",
        title: "No se pudo verificar",
        description:
          error instanceof ApiError
            ? error.message
            : "Ocurrió un error inesperado.",
      });
    }
  }

  const bank = typeof fila.bank === "string" ? fila.bank : "";

  return (
    <Autorizado
      operacion={[
        "POST",
        `/maestros/terceros/${partyId}/bank-accounts/${fila.id}/verify`,
      ]}
    >
      <div className="mt-2 flex flex-col gap-2 sm:flex-row sm:items-center">
        <TextInput
          aria-label={`Evidencia de ${resumen(fila)}`}
          placeholder="Evidencia"
          value={evidence}
          onChange={(evento) => setEvidence(evento.target.value)}
        />
        <AsyncButton
          variant="secondary"
          size="sm"
          aria-label={`Verificar ${bank}`}
          onClick={verificar}
        >
          Verificar
        </AsyncButton>
      </div>
    </Autorizado>
  );
}

export function TerceroDatos({
  partyId,
  editable,
}: {
  partyId: string;
  editable: boolean;
}) {
  return (
    <div className="space-y-6">
      <SeccionDatos
        partyId={partyId}
        titulo="Direcciones"
        ruta="addresses"
        editable={editable}
        campos={[
          { name: "address_type", label: "Tipo" },
          { name: "country", label: "País" },
          { name: "state", label: "Estado" },
          { name: "city", label: "Ciudad" },
          { name: "municipality", label: "Municipio" },
          { name: "postal_code", label: "Código postal" },
          { name: "address", label: "Dirección", required: true },
          { name: "is_fiscal", label: "Fiscal", tipo: "booleano" },
          { name: "is_delivery", label: "Entrega", tipo: "booleano" },
        ]}
        resumen={resumenDireccion}
      />

      <SeccionDatos
        partyId={partyId}
        titulo="Contactos"
        ruta="contacts"
        editable={editable}
        campos={[
          { name: "name", label: "Nombre" },
          { name: "role", label: "Cargo" },
          { name: "phone", label: "Teléfono" },
          { name: "email", label: "Correo" },
          { name: "preferred", label: "Preferido", tipo: "booleano" },
        ]}
        resumen={resumenContacto}
      />

      <SeccionDatos
        partyId={partyId}
        titulo="Cuentas bancarias"
        ruta="bank-accounts"
        editable={editable}
        aviso="Editar la cuenta quita su verificación y devuelve el proveedor a pendiente de aprobación."
        campos={[
          { name: "bank", label: "Banco", required: true },
          { name: "account_type", label: "Tipo de cuenta" },
          { name: "currency", label: "Moneda" },
          { name: "account_number", label: "Número de cuenta", required: true },
          { name: "beneficiary", label: "Beneficiario" },
        ]}
        resumen={resumenCuenta}
        extra={(fila) =>
          fila.verified !== true ? (
            <VerificarCuenta
              partyId={partyId}
              fila={fila}
              resumen={resumenCuenta}
            />
          ) : null
        }
      />
    </div>
  );
}
