import { useRef, useState } from "react";
import { useNavigate } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { hoyDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_CUENTAS,
  ETIQUETAS_TIPO_CUENTA,
  MONEDAS_CUENTA,
  type CuentaDetalle,
  type CuentaEntrada,
  type CuentasOpciones,
  type MonedaCuenta,
  type TipoCuenta,
} from "@/modules/gobierno/api";

type ErroresFormulario = {
  denominacion?: string;
  banco_id?: string;
  tipo?: string;
  numero?: string;
  moneda?: string;
  vigente_desde?: string;
  vigente_hasta?: string;
  general?: string;
};

export function NuevaCuentaPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();

  const puedeGestionar = tiene("gobierno_cuentas:manage", "empresa");

  const [denominacion, setDenominacion] = useState("");
  const [bancoId, setBancoId] = useState("");
  const [tipo, setTipo] = useState<TipoCuenta | "">("");
  const [numero, setNumero] = useState("");
  const [moneda, setMoneda] = useState<MonedaCuenta | "">("");
  const [desde, setDesde] = useState(hoyDeNegocio());
  const [hasta, setHasta] = useState("");
  const [errores, setErrores] = useState<ErroresFormulario>({});
  const enviandoRef = useRef(false);

  const opciones = useQuery({
    queryKey: [...CONSULTA_CUENTAS, "opciones", activeCompanyId],
    queryFn: () => apiFetch<CuentasOpciones>("/gobierno/tesoreria/opciones"),
    enabled: puedeGestionar && Boolean(activeCompanyId),
    retry: false,
  });

  const bancos = opciones.data?.bancos ?? [];

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

    if (!denominacion.trim() || denominacion.trim().length < 3) {
      siguientes.denominacion = "La denominación debe tener al menos 3 caracteres.";
    }

    if (!bancoId) {
      siguientes.banco_id = "Elija un banco.";
    }

    if (!tipo) {
      siguientes.tipo = "Elija el tipo de cuenta.";
    }

    if (!/^\d{20}$/.test(numero)) {
      siguientes.numero = "El número debe tener 20 dígitos.";
    } else if (bancoId) {
      const banco = bancos.find((b) => b.id === bancoId);
      if (banco && !numero.startsWith(banco.codigo)) {
        siguientes.numero = "El número debe empezar por el código del banco.";
      }
    }

    if (!moneda) {
      siguientes.moneda = "Elija la moneda.";
    }

    if (!desde) {
      siguientes.vigente_desde = "Elija la fecha de inicio.";
    }

    if (hasta && desde && hasta < desde) {
      siguientes.vigente_hasta =
        "La vigencia final no puede ser anterior a la inicial.";
    }

    return siguientes;
  };

  const enviar = async (): Promise<void> => {
    if (!puedeGestionar || enviandoRef.current) return;

    const erroresLocales = validar();
    setErrores(erroresLocales);
    if (Object.keys(erroresLocales).length > 0) return;
    if (tipo === "" || moneda === "") return;

    const cuerpo: CuentaEntrada = {
      denominacion: denominacion.trim(),
      banco_id: bancoId,
      tipo,
      numero,
      moneda,
      vigente_desde: desde,
      vigente_hasta: hasta || null,
    };

    enviandoRef.current = true;
    try {
      const creada = await apiFetch<CuentaDetalle>(
        "/gobierno/tesoreria/cuentas",
        {
          method: "POST",
          body: cuerpo,
        },
      );
      notify({ type: "success", title: "Cuenta registrada en borrador" });
      await queryClient.invalidateQueries({ queryKey: [...CONSULTA_CUENTAS] });
      navigate(`/gobierno/tesoreria/cuentas/${creada.id}`);
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 422 && error.code === "VALIDATION_ERROR") {
          setErrores({
            denominacion: error.fieldErrors.denominacion?.[0],
            banco_id: error.fieldErrors.banco_id?.[0],
            tipo: error.fieldErrors.tipo?.[0],
            numero: error.fieldErrors.numero?.[0],
            moneda: error.fieldErrors.moneda?.[0],
            vigente_desde: error.fieldErrors.vigente_desde?.[0],
            vigente_hasta: error.fieldErrors.vigente_hasta?.[0],
            general: error.fieldErrors["_"]?.[0],
          });
          return;
        }
        if (error.status === 409 && error.code === "GOV_BANK_ACCOUNT_DUPLICATE") {
          setErrores({ numero: error.message });
          return;
        }
        if (
          error.status === 409 &&
          error.code === "GOV_BANK_ACCOUNT_INVALID"
        ) {
          setErrores({ general: error.message });
          return;
        }
        if (error.status === 422) {
          setErrores({ general: error.message });
          return;
        }
        if (error.status === 403) {
          notify({
            type: "error",
            title: "No tiene permiso para registrar cuentas",
          });
          return;
        }
      }
      setErrores({ general: "No fue posible registrar la cuenta" });
    } finally {
      enviandoRef.current = false;
    }
  };

  if (!puedeGestionar) {
    return (
      <PageContent>
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para registrar cuentas bancarias."
        />
      </PageContent>
    );
  }

  if (opciones.isLoading) {
    return (
      <PageContent>
        <PageHeader
          crumbs={[
            { label: "Gobierno" },
            { label: "Tesorería", to: "/gobierno/tesoreria/cuentas" },
          ]}
          title="Nueva cuenta bancaria"
        />
        <LoadingState label="Cargando los bancos…" />
      </PageContent>
    );
  }

  if (opciones.isError) {
    return (
      <PageContent>
        <PageHeader
          crumbs={[
            { label: "Gobierno" },
            { label: "Tesorería", to: "/gobierno/tesoreria/cuentas" },
          ]}
          title="Nueva cuenta bancaria"
        />
        <ErrorState
          message="No fue posible cargar los bancos."
          onRetry={() => void opciones.refetch()}
        />
      </PageContent>
    );
  }

  if (bancos.length === 0) {
    return (
      <PageContent>
        <PageHeader
          crumbs={[
            { label: "Gobierno" },
            { label: "Tesorería", to: "/gobierno/tesoreria/cuentas" },
          ]}
          title="Nueva cuenta bancaria"
        />
        <EmptyState
          title="Aún no hay bancos activos"
          description="Registre primero el banco en el catálogo."
          action={
            <Button
              variant="primary"
              onClick={() => navigate("/gobierno/tesoreria/bancos")}
            >
              Ir a Bancos
            </Button>
          }
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
          { label: "Tesorería", to: "/gobierno/tesoreria/cuentas" },
        ]}
        title="Nueva cuenta bancaria"
      />

      <p className="mt-2 text-sm text-text-600">
        Quedará en borrador hasta vincular su acto y autorizar los cargos.
      </p>

      <form
        noValidate
        className="mt-4 space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          void enviar();
        }}
      >
        <FormField
          label="Denominación"
          htmlFor="cuenta-denominacion"
          required
          error={errores.denominacion}
          help="Por ejemplo: Fondos de funcionamiento"
        >
          <TextInput
            id="cuenta-denominacion"
            value={denominacion}
            maxLength={200}
            onChange={(evento) => {
              setDenominacion(evento.target.value);
              limpiarError("denominacion");
            }}
            aria-invalid={Boolean(errores.denominacion)}
          />
        </FormField>

        <FormField
          label="Banco"
          htmlFor="cuenta-banco"
          required
          error={errores.banco_id}
        >
          <select
            id="cuenta-banco"
            value={bancoId}
            onChange={(evento) => {
              setBancoId(evento.target.value);
              limpiarError("banco_id");
              limpiarError("numero");
            }}
            aria-invalid={Boolean(errores.banco_id)}
            className={selectClase(errores.banco_id)}
          >
            <option value="">Elija un banco</option>
            {bancos.map((banco) => (
              <option key={banco.id} value={banco.id}>
                {banco.codigo} · {banco.nombre}
              </option>
            ))}
          </select>
        </FormField>

        <FormField
          label="Tipo de cuenta"
          htmlFor="cuenta-tipo"
          required
          error={errores.tipo}
        >
          <select
            id="cuenta-tipo"
            value={tipo}
            onChange={(evento) => {
              setTipo(evento.target.value as TipoCuenta | "");
              limpiarError("tipo");
            }}
            aria-invalid={Boolean(errores.tipo)}
            className={selectClase(errores.tipo)}
          >
            <option value="">Elija el tipo</option>
            {(Object.keys(ETIQUETAS_TIPO_CUENTA) as TipoCuenta[]).map((valor) => (
              <option key={valor} value={valor}>
                {ETIQUETAS_TIPO_CUENTA[valor]}
              </option>
            ))}
          </select>
        </FormField>

        <FormField
          label="Número de cuenta"
          htmlFor="cuenta-numero"
          required
          error={errores.numero}
          help="20 dígitos, sin guiones. Debe empezar por el código del banco"
        >
          <TextInput
            id="cuenta-numero"
            value={numero}
            inputMode="numeric"
            maxLength={20}
            autoComplete="off"
            onChange={(evento) => {
              setNumero(evento.target.value.replace(/\D/g, ""));
              limpiarError("numero");
            }}
            aria-invalid={Boolean(errores.numero)}
          />
        </FormField>

        <FormField
          label="Moneda"
          htmlFor="cuenta-moneda"
          required
          error={errores.moneda}
        >
          <select
            id="cuenta-moneda"
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
          label="Vigente desde"
          htmlFor="cuenta-desde"
          required
          error={errores.vigente_desde}
        >
          <input
            id="cuenta-desde"
            type="date"
            value={desde}
            onChange={(evento) => {
              setDesde(evento.target.value);
              limpiarError("vigente_desde");
              limpiarError("vigente_hasta");
            }}
            aria-invalid={Boolean(errores.vigente_desde)}
            className={selectClase(errores.vigente_desde)}
          />
        </FormField>

        <FormField
          label="Vigente hasta"
          htmlFor="cuenta-hasta"
          error={errores.vigente_hasta}
          help="Déjelo vacío si no tiene fin previsto"
        >
          <input
            id="cuenta-hasta"
            type="date"
            value={hasta}
            min={desde}
            onChange={(evento) => {
              setHasta(evento.target.value);
              limpiarError("vigente_hasta");
            }}
            aria-invalid={Boolean(errores.vigente_hasta)}
            className={selectClase(errores.vigente_hasta)}
          />
        </FormField>

        {errores.general && (
          <p role="alert" className="text-sm text-danger-600">
            {errores.general}
          </p>
        )}

        <div className="flex items-center gap-2">
          <AsyncButton variant="primary" onClick={enviar}>
            Registrar cuenta
          </AsyncButton>
          <Button
            variant="secondary"
            onClick={() => navigate("/gobierno/tesoreria/cuentas")}
          >
            Cancelar
          </Button>
        </div>
      </form>
    </PageContent>
  );
}
