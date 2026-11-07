import { useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";
import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { ErrorDeCarga } from "@/modules/gobierno/ocupacion/ErrorDeCarga";
import { LoadingState } from "@/components/LoadingState";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { hoyDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_OCUPACION,
  esDelegacion,
  exigeCargoOrigen,
  exigeFechaFinal,
  type AccionCompetenciaOcupacion,
  type AsignacionDetalle,
  type AsignacionEntrada,
  type CatalogoOcupacion,
  type FiguraAsignacion,
  type MateriaCompetenciaOcupacion,
  type OpcionesOcupacion,
} from "@/modules/gobierno/api";

type ErroresFormulario = {
  ejercicio?: string;
  funcionario?: string;
  cargo?: string;
  cargo_origen?: string;
  acto?: string;
  figura?: string;
  desde?: string;
  hasta?: string;
  fundamento?: string;
  rendicion?: string;
  declara_delegable?: string;
  autorizacion_concejo?: string;
  general?: string;
};

type EstadoCompetencia = `${AccionCompetenciaOcupacion}|${MateriaCompetenciaOcupacion}`;

export function NuevaAsignacionPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const { asignacionId } = useParams();

  const esEdicion = Boolean(asignacionId);
  const puedeGestionar = tiene("gobierno_ocupacion:manage", "empresa");

  const [ejercicio, setEjercicio] = useState(hoyDeNegocio().slice(0, 4));
  const [figura, setFigura] = useState<FiguraAsignacion | "">("");
  const [funcionario, setFuncionario] = useState("");
  const [parametros] = useSearchParams();
  const [cargo, setCargo] = useState(parametros.get("cargo") ?? "");
  const [cargoOrigen, setCargoOrigen] = useState("");
  const [acto, setActo] = useState("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [fundamento, setFundamento] = useState("");
  const [rendicion, setRendicion] = useState("");
  const [declaraDelegable, setDeclaraDelegable] = useState(false);
  const [maximaAutoridad, setMaximaAutoridad] = useState(false);
  const [autorizacionConcejo, setAutorizacionConcejo] = useState("");
  const [competencias, setCompetencias] = useState<EstadoCompetencia[]>([]);
  const [errores, setErrores] = useState<ErroresFormulario>({});
  const codigoFigura: FiguraAsignacion | null = figura === "" ? null : figura;
  const enviandoRef = useRef(false);
  const [detalleCargado, setDetalleCargado] = useState(false);
  const [detalleNoEditable, setDetalleNoEditable] = useState(false);

  const catalogo = useQuery({
    queryKey: [...CONSULTA_OCUPACION, "catalogo", activeCompanyId],
    queryFn: () => apiFetch<CatalogoOcupacion>("/gobierno/ocupacion/catalogo"),
    enabled: puedeGestionar && Boolean(activeCompanyId),
    retry: false,
  });

  const opciones = useQuery({
    queryKey: [...CONSULTA_OCUPACION, "opciones", activeCompanyId, ejercicio],
    queryFn: () =>
      apiFetch<OpcionesOcupacion>(
        `/gobierno/ocupacion/opciones?ejercicio=${encodeURIComponent(ejercicio)}`,
      ),
    enabled: puedeGestionar && Boolean(activeCompanyId) && Boolean(ejercicio),
    retry: false,
    placeholderData: keepPreviousData,
  });

  const detalle = useQuery({
    queryKey: [...CONSULTA_OCUPACION, "asignacion-detalle", activeCompanyId, asignacionId],
    queryFn: () =>
      apiFetch<AsignacionDetalle>(`/gobierno/ocupacion/asignaciones/${asignacionId}`),
    enabled: puedeGestionar && esEdicion && Boolean(activeCompanyId),
    retry: false,
  });

  const figurasCatalogo = useMemo(() => catalogo.data?.figuras ?? [], [catalogo.data]);
  const funcionarios = useMemo(() => opciones.data?.funcionarios ?? [], [opciones.data]);
  const cargos = useMemo(() => opciones.data?.cargos ?? [], [opciones.data]);
  const actos = useMemo(() => opciones.data?.actos ?? [], [opciones.data]);

  const figuraElegida = useMemo(
    () => figurasCatalogo.find((f) => f.codigo === figura),
    [figurasCatalogo, figura],
  );

  const cargoElegido = useMemo(() => {
    if (!cargo) return undefined;
    return cargos.find((c) => c.id === cargo);
  }, [cargos, cargo]);

  const competenciasCargo = useMemo(() => cargoElegido?.competencias ?? [], [cargoElegido]);

  const limpiarError = (campo: keyof ErroresFormulario): void => {
    setErrores((previos) => {
      if (!(campo in previos)) return previos;
      const siguientes = { ...previos };
      delete siguientes[campo];
      return siguientes;
    });
  };

  const cambiarFigura = (valor: FiguraAsignacion | ""): void => {
    setFigura(valor);
    const nuevaFigura: FiguraAsignacion | null = valor === "" ? null : valor;
    if (nuevaFigura !== null && !exigeCargoOrigen(nuevaFigura)) {
      setCargoOrigen("");
    }
    if (nuevaFigura !== null && !exigeFechaFinal(nuevaFigura)) {
      setHasta("");
    }
    if (nuevaFigura !== null && !esDelegacion(nuevaFigura)) {
      setRendicion("");
      setDeclaraDelegable(false);
      setCompetencias([]);
    }
    if (nuevaFigura !== "SUPLENCIA") {
      setMaximaAutoridad(false);
      setAutorizacionConcejo("");
    }
    limpiarError("figura");
    limpiarError("cargo_origen");
    limpiarError("hasta");
    limpiarError("rendicion");
    limpiarError("declara_delegable");
    limpiarError("autorizacion_concejo");
  };

  const cambiarCargo = (valor: string): void => {
    setCargo(valor);
    setCompetencias([]);
    limpiarError("cargo");
  };

  const toggleCompetencia = (competencia: EstadoCompetencia): void => {
    setCompetencias((previas) => {
      if (previas.includes(competencia)) {
        return previas.filter((c) => c !== competencia);
      }
      return [...previas, competencia];
    });
  };

  const rellenarDesdeDetalle = (d: AsignacionDetalle): void => {
    setEjercicio(String(d.cargo.ejercicio));
    setFuncionario(d.funcionario.id);
    setCargo(d.cargo.id);
    setCargoOrigen(d.cargo_origen?.id ?? "");
    setActo(d.acto.id);
    setFigura(d.figura);
    setDesde(d.desde);
    setHasta(d.hasta ?? "");
    setFundamento(d.fundamento);
    setRendicion(d.rendicion ?? "");
    setDeclaraDelegable(d.declara_delegable);
    setMaximaAutoridad(d.maxima_autoridad);
    setAutorizacionConcejo(d.autorizacion_concejo ?? "");
    setCompetencias(
      d.competencias.map(
        (c) => `${c.accion}|${c.materia}` as EstadoCompetencia,
      ),
    );
    setDetalleCargado(true);
  };

  useMemo(() => {
    if (esEdicion && detalle.data && !detalleCargado) {
      if (detalle.data.status !== "BORRADOR") {
        setDetalleNoEditable(true);
      } else {
        rellenarDesdeDetalle(detalle.data);
      }
    }
  }, [esEdicion, detalle.data, detalleCargado]);

  const validar = (): ErroresFormulario => {
    const siguientes: ErroresFormulario = {};

    if (!ejercicio) {
      siguientes.ejercicio = "Indique el ejercicio.";
    }

    if (!figura) {
      siguientes.figura = "Elija la figura.";
    }

    if (!funcionario) {
      siguientes.funcionario = "Elija el funcionario.";
    }

    if (!cargo) {
      siguientes.cargo = "Elija el cargo.";
    }

    if (codigoFigura !== null && exigeCargoOrigen(codigoFigura) && !cargoOrigen) {
      siguientes.cargo_origen = "Elija el cargo de origen.";
    }

    if (!acto) {
      siguientes.acto = "Elija el acto que la sustenta.";
    }

    if (!desde) {
      siguientes.desde = "Indique la fecha de inicio.";
    }

    if (codigoFigura !== null && exigeFechaFinal(codigoFigura) && !hasta) {
      siguientes.hasta = "Indique la fecha final.";
    }

    if (hasta && desde && hasta < desde) {
      siguientes.hasta = "La fecha final no puede ser anterior a la inicial.";
    }

    const fundamentoRecortado = fundamento.trim();
    if (fundamentoRecortado.length < 10 || fundamentoRecortado.length > 500) {
      siguientes.fundamento = "El fundamento debe tener entre 10 y 500 caracteres.";
    }

    if (codigoFigura !== null && esDelegacion(codigoFigura)) {
      const rendicionRecortada = rendicion.trim();
      if (rendicionRecortada.length < 10 || rendicionRecortada.length > 500) {
        siguientes.rendicion = "La rendición de cuenta debe tener entre 10 y 500 caracteres.";
      }

      if (!declaraDelegable) {
        siguientes.declara_delegable = "Debe declarar que la competencia no es indelegable.";
      }
    }

    if (figura === "SUPLENCIA" && maximaAutoridad) {
      const autorizacionRecortada = autorizacionConcejo.trim();
      if (autorizacionRecortada.length < 5 || autorizacionRecortada.length > 200) {
        siguientes.autorizacion_concejo = "La autorización debe tener entre 5 y 200 caracteres.";
      }
    }

    return siguientes;
  };

  const enviar = async (): Promise<void> => {
    if (!puedeGestionar || enviandoRef.current) return;

    const erroresLocales = validar();
    setErrores(erroresLocales);
    if (Object.keys(erroresLocales).length > 0) return;

    const cuerpo: AsignacionEntrada = {
      funcionario_id: funcionario,
      cargo_id: cargo,
      figura: figura as FiguraAsignacion,
      cargo_origen_id: cargoOrigen || null,
      acto_id: acto,
      desde,
      hasta: hasta || null,
      fundamento: fundamento.trim(),
      rendicion: codigoFigura !== null && esDelegacion(codigoFigura) ? rendicion.trim() : null,
      maxima_autoridad: figura === "SUPLENCIA" ? maximaAutoridad : false,
      autorizacion_concejo:
        figura === "SUPLENCIA" && maximaAutoridad ? autorizacionConcejo.trim() : null,
      declara_delegable: codigoFigura !== null && esDelegacion(codigoFigura) ? declaraDelegable : false,
      competencias: codigoFigura !== null && esDelegacion(codigoFigura)
        ? competencias.map((c) => {
            const [accion, materia] = c.split("|");
            return {
              accion: accion as AccionCompetenciaOcupacion,
              materia: materia as MateriaCompetenciaOcupacion,
            };
          })
        : [],
    };

    enviandoRef.current = true;
    try {
      if (esEdicion && detalle.data) {
        const actualizada = await apiFetch<AsignacionDetalle>(
          `/gobierno/ocupacion/asignaciones/${detalle.data.id}`,
          {
            method: "PATCH",
            body: cuerpo,
            ifMatch: String(detalle.data.version),
          },
        );
        notify({ type: "success", title: "Asignación actualizada" });
        await queryClient.invalidateQueries({ queryKey: [...CONSULTA_OCUPACION] });
        navigate(`/gobierno/ocupacion/asignaciones/${actualizada.id}`);
      } else {
        const creada = await apiFetch<AsignacionDetalle>(
          "/gobierno/ocupacion/asignaciones",
          {
            method: "POST",
            body: cuerpo,
          },
        );
        notify({ type: "success", title: "Asignación registrada en borrador" });
        await queryClient.invalidateQueries({ queryKey: [...CONSULTA_OCUPACION] });
        navigate(`/gobierno/ocupacion/asignaciones/${creada.id}`);
      }
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 422 && error.code === "VALIDATION_ERROR") {
          setErrores({
            ejercicio: error.fieldErrors.ejercicio?.[0],
            funcionario: error.fieldErrors.funcionario_id?.[0],
            cargo: error.fieldErrors.cargo_id?.[0],
            cargo_origen: error.fieldErrors.cargo_origen_id?.[0],
            acto: error.fieldErrors.acto_id?.[0],
            figura: error.fieldErrors.figura?.[0],
            desde: error.fieldErrors.desde?.[0],
            hasta: error.fieldErrors.hasta?.[0],
            fundamento: error.fieldErrors.fundamento?.[0],
            rendicion: error.fieldErrors.rendicion?.[0],
            declara_delegable: error.fieldErrors.declara_delegable?.[0],
            autorizacion_concejo: error.fieldErrors.autorizacion_concejo?.[0],
            general: error.fieldErrors["_"]?.[0],
          });
          return;
        }
        if (error.status === 422) {
          setErrores({ general: error.message });
          return;
        }
        if (error.status === 409 && error.code === "GOV_ASSIGNMENT_STALE") {
          setErrores({
            general: "Otra persona cambió esta asignación. Recargue la página.",
          });
          return;
        }
        if (error.code?.startsWith("GOV_ASSIGNMENT_")) {
          setErrores({ general: error.message });
          return;
        }
        if (error.status === 403) {
          notify({
            type: "error",
            title: "No tiene permiso para registrar asignaciones",
          });
          return;
        }
      }
      notify({ type: "error", title: "No fue posible guardar la asignación" });
    } finally {
      enviandoRef.current = false;
    }
  };

  if (!puedeGestionar) {
    return (
      <PageContent>
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para gestionar asignaciones."
        />
      </PageContent>
    );
  }

  if (esEdicion && detalle.isLoading) {
    return (
      <PageContent>
        <PageHeader
          crumbs={[
            { label: "Gobierno" },
            { label: "Ocupación de cargos", to: "/gobierno/ocupacion" },
            { label: "Asignaciones", to: "/gobierno/ocupacion/asignaciones" },
          ]}
          title="Editar asignación"
        />
        <LoadingState label="Cargando asignación…" />
      </PageContent>
    );
  }

  if (esEdicion && detalle.isError) {
    return (
      <PageContent>
        <PageHeader
          crumbs={[
            { label: "Gobierno" },
            { label: "Ocupación de cargos", to: "/gobierno/ocupacion" },
            { label: "Asignaciones", to: "/gobierno/ocupacion/asignaciones" },
          ]}
          title="Editar asignación"
        />
        <ErrorDeCarga
          message="No fue posible cargar la asignación."
          onRetry={() => void detalle.refetch()}
        />
      </PageContent>
    );
  }

  if (esEdicion && detalleNoEditable) {
    return (
      <PageContent>
        <PageHeader
          crumbs={[
            { label: "Gobierno" },
            { label: "Ocupación de cargos", to: "/gobierno/ocupacion" },
            { label: "Asignaciones", to: "/gobierno/ocupacion/asignaciones" },
          ]}
          title="Editar asignación"
        />
        <EmptyState
          title="Solo se edita un borrador"
          description="Esta asignación ya no está en borrador y no puede modificarse."
        />
      </PageContent>
    );
  }

  if (catalogo.isLoading || (esEdicion && !detalleCargado)) {
    return (
      <PageContent>
        <PageHeader
          crumbs={[
            { label: "Gobierno" },
            { label: "Ocupación de cargos", to: "/gobierno/ocupacion" },
            { label: "Asignaciones", to: "/gobierno/ocupacion/asignaciones" },
          ]}
          title={esEdicion ? "Editar asignación" : "Nueva asignación"}
        />
        <LoadingState label="Cargando catálogo…" />
      </PageContent>
    );
  }

  if (catalogo.isError) {
    return (
      <PageContent>
        <PageHeader
          crumbs={[
            { label: "Gobierno" },
            { label: "Ocupación de cargos", to: "/gobierno/ocupacion" },
            { label: "Asignaciones", to: "/gobierno/ocupacion/asignaciones" },
          ]}
          title={esEdicion ? "Editar asignación" : "Nueva asignación"}
        />
        <ErrorDeCarga
          message="No fue posible cargar el catálogo."
          onRetry={() => void catalogo.refetch()}
        />
      </PageContent>
    );
  }

  if (opciones.isError) {
    return (
      <PageContent>
        <PageHeader
          crumbs={[
            { label: "Gobierno" },
            { label: "Ocupación de cargos", to: "/gobierno/ocupacion" },
            { label: "Asignaciones", to: "/gobierno/ocupacion/asignaciones" },
          ]}
          title={esEdicion ? "Editar asignación" : "Nueva asignación"}
        />
        <ErrorDeCarga
          message="No fue posible cargar las opciones."
          onRetry={() => void opciones.refetch()}
        />
      </PageContent>
    );
  }

  const selectClase = (error?: string) =>
    `w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600 ${
      error ? "border-danger-600" : "border-border-default"
    }`;

  const textareaClase = (error?: string) =>
    `min-h-24 w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600 ${
      error ? "border-danger-600" : "border-border-default"
    }`;

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno" },
          { label: "Ocupación de cargos", to: "/gobierno/ocupacion" },
          { label: "Asignaciones", to: "/gobierno/ocupacion/asignaciones" },
        ]}
        title={esEdicion ? "Editar asignación" : "Nueva asignación"}
        description="Registre quién ejercerá el cargo, bajo qué figura y por qué acto. Queda en borrador hasta que otra persona la active."
      />

      <form
        noValidate
        className="mt-4 space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          void enviar();
        }}
      >
        <FormField
          label="Ejercicio"
          htmlFor="asignacion-ejercicio"
          required
          error={errores.ejercicio}
        >
          <input
            id="asignacion-ejercicio"
            type="number"
            min={hoyDeNegocio().slice(0, 4)}
            max={hoyDeNegocio().slice(0, 4)}
            value={ejercicio}
            onChange={(evento) => {
              setEjercicio(evento.target.value);
              limpiarError("ejercicio");
            }}
            aria-invalid={Boolean(errores.ejercicio)}
            className={selectClase(errores.ejercicio)}
          />
        </FormField>

        <FormField
          label="Figura"
          htmlFor="asignacion-figura"
          required
          error={errores.figura}
        >
          <select
            id="asignacion-figura"
            value={figura}
            onChange={(evento) => cambiarFigura(evento.target.value as FiguraAsignacion | "")}
            aria-invalid={Boolean(errores.figura)}
            className={selectClase(errores.figura)}
          >
            <option value="">Elija la figura</option>
            {figurasCatalogo.map((f) => (
              <option key={f.codigo} value={f.codigo}>
                {f.etiqueta}
              </option>
            ))}
          </select>
          {figuraElegida && (
            <p className="mt-2 text-sm text-text-700">
              {figuraElegida.descripcion} · {figuraElegida.base_legal}
            </p>
          )}
        </FormField>

        <FormField
          label="Funcionario"
          htmlFor="asignacion-funcionario"
          required
          error={errores.funcionario}
        >
          {funcionarios.length === 0 ? (
            <p className="text-sm text-text-700">
              No hay funcionarios registrados.{" "}
              <Link className="text-brand-700 hover:underline" to="/gobierno/ocupacion/funcionarios">
                Registrar funcionario
              </Link>
            </p>
          ) : (
            <select
              id="asignacion-funcionario"
              value={funcionario}
              onChange={(evento) => {
                setFuncionario(evento.target.value);
                limpiarError("funcionario");
              }}
              aria-invalid={Boolean(errores.funcionario)}
              className={selectClase(errores.funcionario)}
            >
              <option value="">Elija el funcionario</option>
              {funcionarios.map((f) => (
                <option key={f.id} value={f.id}>
                  {`${f.nombre} (${f.codigo})`}
                </option>
              ))}
            </select>
          )}
          <p className="mt-2 text-sm text-text-700">
            <Link className="text-brand-700 hover:underline" to="/gobierno/ocupacion/funcionarios">
              Registrar funcionario
            </Link>
          </p>
        </FormField>

        <FormField
          label="Cargo"
          htmlFor="asignacion-cargo"
          required
          error={errores.cargo}
        >
          {cargos.length === 0 ? (
            <p className="text-sm text-text-700">
              No hay cargos para el ejercicio seleccionado.
            </p>
          ) : (
            <select
              id="asignacion-cargo"
              value={cargo}
              onChange={(evento) => cambiarCargo(evento.target.value)}
              aria-invalid={Boolean(errores.cargo)}
              className={selectClase(errores.cargo)}
            >
              <option value="">Elija el cargo</option>
              {cargos.map((c) => (
                <option key={c.id} value={c.id}>
                  {`${c.nombre} · ${c.unidad}`}
                </option>
              ))}
            </select>
          )}
        </FormField>

        {codigoFigura !== null && exigeCargoOrigen(codigoFigura) && (
          <FormField
            label="Cargo de origen"
            htmlFor="asignacion-cargo-origen"
            error={errores.cargo_origen}
            help="Cargo que suple, del que viene o desde el que delega"
          >
            {cargos.length === 0 ? (
              <p className="text-sm text-text-700">
                No hay cargos para el ejercicio seleccionado.
              </p>
            ) : (
              <select
                id="asignacion-cargo-origen"
                value={cargoOrigen}
                onChange={(evento) => {
                  setCargoOrigen(evento.target.value);
                  limpiarError("cargo_origen");
                }}
                aria-invalid={Boolean(errores.cargo_origen)}
                className={selectClase(errores.cargo_origen)}
              >
                <option value="">Elija el cargo de origen</option>
                {cargos.map((c) => (
                  <option key={c.id} value={c.id}>
                    {`${c.nombre} · ${c.unidad}`}
                  </option>
                ))}
              </select>
            )}
          </FormField>
        )}

        <FormField
          label="Acto que la sustenta"
          htmlFor="asignacion-acto"
          required
          error={errores.acto}
          help="Debe estar eficaz antes del inicio; las delegaciones exigen publicación en gaceta."
        >
          {actos.length === 0 ? (
            <p className="text-sm text-text-700">
              No hay actos registrados.{" "}
              <Link className="text-brand-700 hover:underline" to="/gobierno/actos">
                Registrar acto
              </Link>
            </p>
          ) : (
            <select
              id="asignacion-acto"
              value={acto}
              onChange={(evento) => {
                setActo(evento.target.value);
                limpiarError("acto");
              }}
              aria-invalid={Boolean(errores.acto)}
              className={selectClase(errores.acto)}
            >
              <option value="">Elija el acto</option>
              {actos.map((a) => (
                <option key={a.id} value={a.id}>
                  {`${a.tipo} ${a.numero} · ${a.emisor_cargo}`}
                </option>
              ))}
            </select>
          )}
          <p className="mt-2 text-sm text-text-700">
            <Link className="text-brand-700 hover:underline" to="/gobierno/actos">
              Registrar acto
            </Link>
          </p>
        </FormField>

        <FormField label="Desde" htmlFor="asignacion-desde" required error={errores.desde}>
          <input
            id="asignacion-desde"
            type="date"
            value={desde}
            onChange={(evento) => {
              setDesde(evento.target.value);
              limpiarError("desde");
              limpiarError("hasta");
            }}
            aria-invalid={Boolean(errores.desde)}
            className={selectClase(errores.desde)}
          />
        </FormField>

        <FormField
          label="Hasta"
          htmlFor="asignacion-hasta"
          required={codigoFigura !== null && exigeFechaFinal(codigoFigura)}
          error={errores.hasta}
        >
          <input
            id="asignacion-hasta"
            type="date"
            value={hasta}
            min={desde}
            onChange={(evento) => {
              setHasta(evento.target.value);
              limpiarError("hasta");
            }}
            aria-invalid={Boolean(errores.hasta)}
            className={selectClase(errores.hasta)}
          />
        </FormField>

        <FormField
          label="Fundamento"
          htmlFor="asignacion-fundamento"
          required
          error={errores.fundamento}
        >
          <textarea
            id="asignacion-fundamento"
            value={fundamento}
            maxLength={500}
            onChange={(evento) => {
              setFundamento(evento.target.value);
              limpiarError("fundamento");
            }}
            aria-invalid={Boolean(errores.fundamento)}
            className={textareaClase(errores.fundamento)}
          />
        </FormField>

        {codigoFigura !== null && esDelegacion(codigoFigura) && (
          <>
            <FormField
              label="Rendición de cuenta"
              htmlFor="asignacion-rendicion"
              required
              error={errores.rendicion}
            >
              <textarea
                id="asignacion-rendicion"
                value={rendicion}
                maxLength={500}
                onChange={(evento) => {
                  setRendicion(evento.target.value);
                  limpiarError("rendicion");
                }}
                aria-invalid={Boolean(errores.rendicion)}
                className={textareaClase(errores.rendicion)}
              />
            </FormField>

            <div className="flex flex-col gap-1.5">
              <label className="flex items-center gap-2 text-sm text-text-900">
                <input
                  id="asignacion-declara-delegable"
                  type="checkbox"
                  checked={declaraDelegable}
                  onChange={(evento) => {
                    setDeclaraDelegable(evento.target.checked);
                    limpiarError("declara_delegable");
                  }}
                />
                Declaro que la competencia no es indelegable (LOAP art. 35)
              </label>
              {errores.declara_delegable && (
                <p className="text-sm text-danger-600" role="alert">
                  {errores.declara_delegable}
                </p>
              )}
            </div>

            <fieldset className="flex flex-col gap-1.5">
              <legend className="text-sm font-medium text-text-700">Competencias a delegar</legend>
              {cargo ? (
                competenciasCargo.length === 0 ? (
                  <p className="text-sm text-text-700">El cargo no tiene competencias registradas.</p>
                ) : (
                  <div className="space-y-2">
                    {competenciasCargo.map((c) => {
                      const clave = `${c.accion}|${c.materia}` as EstadoCompetencia;
                      return (
                        <label key={clave} className="flex items-center gap-2 text-sm text-text-900">
                          <input
                            type="checkbox"
                            checked={competencias.includes(clave)}
                            onChange={() => toggleCompetencia(clave)}
                          />
                          {`${c.accion} · ${c.materia}`}
                        </label>
                      );
                    })}
                  </div>
                )
              ) : (
                <p className="text-sm text-text-700">Elija primero el cargo.</p>
              )}
            </fieldset>
          </>
        )}

        {figura === "SUPLENCIA" && (
          <>
            <div className="flex flex-col gap-1.5">
              <label className="flex items-center gap-2 text-sm text-text-900">
                <input
                  id="asignacion-maxima-autoridad"
                  type="checkbox"
                  checked={maximaAutoridad}
                  onChange={(evento) => {
                    setMaximaAutoridad(evento.target.checked);
                    if (!evento.target.checked) {
                      setAutorizacionConcejo("");
                    }
                    limpiarError("autorizacion_concejo");
                  }}
                />
                Suple a la máxima autoridad
              </label>
            </div>

            {maximaAutoridad && (
              <FormField
                label="Autorización del Concejo"
                htmlFor="asignacion-autorizacion-concejo"
                required
                error={errores.autorizacion_concejo}
                help="Más de 15 días exige autorización del Concejo; más de 90 días no procede (LOPPM art. 87)."
              >
                <textarea
                  id="asignacion-autorizacion-concejo"
                  value={autorizacionConcejo}
                  maxLength={200}
                  onChange={(evento) => {
                    setAutorizacionConcejo(evento.target.value);
                    limpiarError("autorizacion_concejo");
                  }}
                  aria-invalid={Boolean(errores.autorizacion_concejo)}
                  className={textareaClase(errores.autorizacion_concejo)}
                />
              </FormField>
            )}
          </>
        )}

        {errores.general && (
          <p role="alert" className="text-sm text-danger-600">
            {errores.general}
          </p>
        )}

        <div className="flex flex-wrap items-center gap-2">
          <AsyncButton variant="primary" onClick={enviar}>
            Guardar borrador
          </AsyncButton>
          <Button
            variant="secondary"
            onClick={() => navigate("/gobierno/ocupacion/asignaciones")}
          >
            Cancelar
          </Button>
        </div>
      </form>
    </PageContent>
  );
}
