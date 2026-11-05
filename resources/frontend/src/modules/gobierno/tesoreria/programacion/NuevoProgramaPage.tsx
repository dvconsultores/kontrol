import { useRef, useState } from "react";
import { useNavigate } from "react-router";
import { useQueryClient } from "@tanstack/react-query";

import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { hoyDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_CAJA,
  MONEDAS_CUENTA,
  NOMBRES_DE_MES,
  type MonedaCuenta,
  type ProgramaDetalle,
  type ProgramaEntrada,
} from "@/modules/gobierno/api";

type ErroresFormulario = {
  ejercicio?: string;
  moneda?: string;
  mes_inicial?: string;
  general?: string;
};

export function NuevoProgramaPage(): React.JSX.Element {
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const { tiene } = useAutoridad();
  const queryClient = useQueryClient();

  const puedeGestionar = tiene("gobierno_caja:manage", "empresa");

  const [ejercicio, setEjercicio] = useState(String(Number(hoyDeNegocio().slice(0, 4))));
  const [moneda, setMoneda] = useState<MonedaCuenta | "">("");
  const [mesInicial, setMesInicial] = useState(1);
  const [errores, setErrores] = useState<ErroresFormulario>({});
  const enviandoRef = useRef(false);

  const limpiarError = (campo: keyof ErroresFormulario): void => {
    setErrores((previos) => {
      if (!(campo in previos)) return previos;
      const siguientes = { ...previos };
      delete siguientes[campo];
      return siguientes;
    });
  };

  const validar = (): ErroresFormulario => {
    const siguientes: ErroresFormulario = {};

    if (!/^\d{4}$/.test(ejercicio)) {
      siguientes.ejercicio = "El ejercicio debe tener 4 dígitos.";
    }

    if (!moneda) {
      siguientes.moneda = "Elija la moneda.";
    }

    if (mesInicial < 1 || mesInicial > 12) {
      siguientes.mes_inicial = "Elija el mes inicial.";
    }

    return siguientes;
  };

  const enviar = async (): Promise<void> => {
    if (!puedeGestionar || enviandoRef.current) return;

    const erroresLocales = validar();
    setErrores(erroresLocales);
    if (Object.keys(erroresLocales).length > 0) return;
    if (moneda === "") return;

    const cuerpo: ProgramaEntrada = {
      ejercicio: Number(ejercicio),
      moneda,
      mes_inicial: mesInicial,
    };

    enviandoRef.current = true;
    try {
      const creado = await apiFetch<ProgramaDetalle>(
        "/gobierno/tesoreria/programas",
        {
          method: "POST",
          body: cuerpo,
        },
      );
      notify({ type: "success", title: "Programa registrado" });
      await queryClient.invalidateQueries({ queryKey: [...CONSULTA_CAJA] });
      navigate(`/gobierno/tesoreria/programacion/${creado.id}`);
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 409 && error.code === "GOV_CASH_PROGRAM_DUPLICATE") {
          setErrores({ ejercicio: "Ya hay un programa de ese ejercicio y moneda." });
          return;
        }
        if (error.status === 422 && error.code === "VALIDATION_ERROR") {
          setErrores({
            ejercicio: error.fieldErrors.ejercicio?.[0],
            moneda: error.fieldErrors.moneda?.[0],
            mes_inicial: error.fieldErrors.mes_inicial?.[0],
            general: error.fieldErrors["_"]?.[0],
          });
          return;
        }
        if (error.status === 422) {
          setErrores({ general: error.message });
          return;
        }
        if (error.status === 403) {
          notify({
            type: "error",
            title: "No tiene permiso para registrar programas",
          });
          return;
        }
      }
      setErrores({ general: "No fue posible registrar el programa" });
    } finally {
      enviandoRef.current = false;
    }
  };

  if (!puedeGestionar) {
    return (
      <PageContent>
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para registrar programas financieros."
        />
      </PageContent>
    );
  }

  const selectClase = (error?: string) =>
    `w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600 ${
      error ? "border-danger-600" : "border-border-default"
    }`;

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno" },
          { label: "Tesorería", to: "/gobierno/tesoreria/programacion" },
          { label: "Programación financiera", to: "/gobierno/tesoreria/programacion" },
        ]}
        title="Nuevo programa"
      />

      <form
        noValidate
        className="relative mt-4 space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          void enviar();
        }}
      >
        <FormField
          label="Ejercicio"
          htmlFor="programa-ejercicio"
          required
          error={errores.ejercicio}
        >
          <TextInput
            id="programa-ejercicio"
            value={ejercicio}
            inputMode="numeric"
            maxLength={4}
            autoComplete="off"
            onChange={(evento) => {
              setEjercicio(evento.target.value.replace(/\D/g, ""));
              limpiarError("ejercicio");
            }}
            aria-invalid={Boolean(errores.ejercicio)}
          />
        </FormField>

        <FormField
          label="Moneda"
          htmlFor="programa-moneda"
          required
          error={errores.moneda}
        >
          <select
            id="programa-moneda"
            value={moneda}
            onChange={(evento) => {
              setMoneda(evento.target.value as MonedaCuenta | "");
              limpiarError("moneda");
            }}
            aria-invalid={Boolean(errores.moneda)}
            className={selectClase(errores.moneda)}
          >
            <option value="">Elija la moneda</option>
            {MONEDAS_CUENTA.map((valor) => (
              <option key={valor} value={valor}>
                {valor}
              </option>
            ))}
          </select>
        </FormField>

        <FormField
          label="Mes inicial"
          htmlFor="programa-mes-inicial"
          required
          error={errores.mes_inicial}
        >
          <select
            id="programa-mes-inicial"
            value={mesInicial}
            onChange={(evento) => {
              setMesInicial(Number(evento.target.value));
              limpiarError("mes_inicial");
            }}
            aria-invalid={Boolean(errores.mes_inicial)}
            className={selectClase(errores.mes_inicial)}
          >
            {NOMBRES_DE_MES.map((nombre, indice) => (
              <option key={indice + 1} value={indice + 1}>
                {nombre}
              </option>
            ))}
          </select>
        </FormField>

        {errores.general && (
          <p role="alert" className="text-sm text-danger-600">
            {errores.general}
          </p>
        )}

        <div className="flex items-center gap-2">
          <AsyncButton variant="primary" onClick={enviar}>
            Registrar programa
          </AsyncButton>
          <Button
            variant="secondary"
            onClick={() => navigate("/gobierno/tesoreria/programacion")}
          >
            Cancelar
          </Button>
        </div>
      </form>
    </PageContent>
  );
}
