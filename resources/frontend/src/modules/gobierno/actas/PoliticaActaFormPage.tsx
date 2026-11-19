import { useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { DateInput } from "@/components/DateInput";
import { ErrorState } from "@/components/ErrorState";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { ETIQUETAS_EVIDENCIA, ETIQUETAS_HITO, describirPlazo } from "./reglaActa";
import {
  crearPoliticaActa,
  editarPoliticaActa,
  entradaDesdeDetalle,
  getOpcionesPoliticasActa,
  getPoliticaActa,
  vistaPreviaNumeracion,
  type AlcanceVinculo,
  type AmbitoRequisito,
  type CodigoSupuesto,
  type HitoPlazoPolitica,
  type PoliticaActaDetalle,
  type PoliticaActaEntrada,
  type RequisitoPolitica,
  type UnidadPlazo,
} from "./politicasActa";

type ErroresFormulario = Partial<Record<
  | "codigo"
  | "nombre"
  | "descripcion"
  | "fundamento"
  | "act_id"
  | "vigente_desde"
  | "vigente_hasta"
  | "numeracion_patron"
  | "testigos_en_entrega"
  | "cargo_maxima_autoridad_codigo"
  | "vinculos"
  | "requisitos"
  | "plazos"
  | "general",
  string
>>;

type FilaVinculo = {
  supuesto: CodigoSupuesto | "";
  alcance: AlcanceVinculo | "";
  unit_id: string | null;
};

type FilaRequisito = {
  codigo: string;
  titulo: string;
  evidencia: "DOCUMENTO" | "CERTIFICACION" | "DECLARACION" | "DATO" | "";
  obligatorio: boolean;
  ambito: AmbitoRequisito;
  supuesto: CodigoSupuesto | "";
  document_type_id: string | null;
  fuente: string | null;
};

type FilaPlazo = {
  hito: HitoPlazoPolitica | "";
  valor: string;
  unidad: UnidadPlazo;
  fuente: string | null;
};

const CLASES_SELECT = "h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600";
const VACIO_A_NULO = (valor: string): string | null => (valor.trim() === "" ? null : valor.trim());
const VISTA_PREVIA_CANTIDAD = 3;

export function PoliticaActaFormPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const { politicaId } = useParams();
  const esEdicion = Boolean(politicaId);
  const puedeConfigurar = tiene("gobierno_actas:configure", "empresa");

  const [codigo, setCodigo] = useState("");
  const [nombre, setNombre] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [fundamento, setFundamento] = useState("");
  const [actId, setActId] = useState("");
  const [vigenteDesde, setVigenteDesde] = useState("");
  const [vigenteHasta, setVigenteHasta] = useState("");
  const [numeracionPatron, setNumeracionPatron] = useState("");
  const [testigosEnEntrega, setTestigosEnEntrega] = useState("0");
  const [cargoMaximaAutoridadCodigo, setCargoMaximaAutoridadCodigo] = useState("");
  const [vinculos, setVinculos] = useState<FilaVinculo[]>([]);
  const [requisitos, setRequisitos] = useState<FilaRequisito[]>([]);
  const [plazos, setPlazos] = useState<FilaPlazo[]>([]);
  const [errores, setErrores] = useState<ErroresFormulario>({});
  const [vistaPrevia, setVistaPrevia] = useState<{ valido: boolean; motivo: string | null; ejemplos: string[] } | null>(null);
  const [vistaPreviaPendiente, setVistaPreviaPendiente] = useState(false);
  const enviandoRef = useRef(false);
  const detalleCargadoRef = useRef(false);

  const opciones = useQuery({
    queryKey: ["gobierno-actas-politicas-opciones", activeCompanyId],
    queryFn: () => getOpcionesPoliticasActa(),
    enabled: puedeConfigurar && Boolean(activeCompanyId),
    retry: false,
  });

  const detalle = useQuery({
    queryKey: ["gobierno-actas-politica-detalle", activeCompanyId, politicaId],
    queryFn: () => getPoliticaActa(politicaId as string),
    enabled: puedeConfigurar && esEdicion && Boolean(activeCompanyId),
    retry: false,
  });

  const opcionesData = useMemo(() => opciones.data ?? null, [opciones.data]);

  const rellenarDesdeDetalle = (d: PoliticaActaDetalle): void => {
    const entrada = entradaDesdeDetalle(d);
    setCodigo(entrada.codigo);
    setNombre(entrada.nombre);
    setDescripcion(entrada.descripcion ?? "");
    setFundamento(entrada.fundamento ?? "");
    setActId(entrada.act_id ?? "");
    setVigenteDesde(entrada.vigente_desde);
    setVigenteHasta(entrada.vigente_hasta ?? "");
    setNumeracionPatron(entrada.numeracion_patron ?? "");
    setTestigosEnEntrega(String(entrada.testigos_en_entrega));
    setCargoMaximaAutoridadCodigo(entrada.cargo_maxima_autoridad_codigo ?? "");
    setVinculos(
      entrada.vinculos.map((v) => ({
        supuesto: v.supuesto,
        alcance: v.alcance,
        unit_id: v.unit_id,
      })),
    );
    setRequisitos(
      entrada.requisitos.map((r) => ({
        codigo: r.codigo,
        titulo: r.titulo,
        evidencia: r.evidencia,
        obligatorio: r.obligatorio,
        ambito: r.ambito,
        supuesto: r.supuesto ?? "",
        document_type_id: r.document_type_id,
        fuente: r.fuente,
      })),
    );
    setPlazos(
      entrada.plazos.map((p) => ({
        hito: p.hito,
        valor: String(p.valor),
        unidad: p.unidad,
        fuente: p.fuente,
      })),
    );
    detalleCargadoRef.current = true;
  };

  useMemo(() => {
    if (esEdicion && detalle.data && !detalleCargadoRef.current) {
      rellenarDesdeDetalle(detalle.data);
    }
  }, [esEdicion, detalle.data]);

  const limpiarError = (campo: keyof ErroresFormulario): void => {
    setErrores((previos) => {
      if (!(campo in previos)) return previos;
      const siguientes = { ...previos };
      delete siguientes[campo];
      return siguientes;
    });
  };

  const supuestosDeclarables = useMemo(() => {
    if (!opcionesData) return [];
    return opcionesData.supuestos.filter((s) => s.declarable);
  }, [opcionesData]);

  const supuestoPorCodigo = (codigo: CodigoSupuesto | string) => {
    if (!opcionesData) return null;
    return opcionesData.supuestos.find((s) => s.codigo === codigo) ?? null;
  };

  const ambitosDelSupuesto = (codigo: CodigoSupuesto | string): AlcanceVinculo[] => {
    const supuesto = supuestoPorCodigo(codigo);
    return supuesto?.ambitos ?? [];
  };

  const supuestosDeclarados = useMemo(() => {
    const codigos = vinculos
      .filter((v) => v.supuesto)
      .map((v) => v.supuesto as CodigoSupuesto);
    return supuestosDeclarables.filter((s) => codigos.includes(s.codigo));
  }, [vinculos, supuestosDeclarables]);

  const cambiarVinculo = (indice: number, campo: keyof FilaVinculo, valor: string): void => {
    setVinculos((previos) =>
      previos.map((vinculo, i) => {
        if (i !== indice) return vinculo;
        if (campo === "supuesto") {
          return { ...vinculo, supuesto: valor as CodigoSupuesto, alcance: "", unit_id: null };
        }
        if (campo === "alcance") {
          const alcance = valor as AlcanceVinculo;
          return { ...vinculo, alcance, unit_id: alcance === "UNIDAD" ? vinculo.unit_id : null };
        }
        return { ...vinculo, unit_id: valor || null };
      }),
    );
  };

  const nuevaFilaVinculo = (): FilaVinculo => ({ supuesto: "", alcance: "", unit_id: null });

  const nuevaFilaRequisito = (): FilaRequisito => ({
    codigo: "",
    titulo: "",
    evidencia: "DOCUMENTO",
    obligatorio: true,
    ambito: "TODAS",
    supuesto: "",
    document_type_id: null,
    fuente: null,
  });

  const nuevaFilaPlazo = (): FilaPlazo => ({ hito: "", valor: "", unidad: "DIAS_HABILES", fuente: null });

  const cambiarRequisito = (indice: number, campo: keyof FilaRequisito, valor: unknown): void => {
    setRequisitos((previos) =>
      previos.map((requisito, i) => {
        if (i !== indice) return requisito;
        if (campo === "evidencia") {
          const evidencia = valor as FilaRequisito["evidencia"];
          const requiereTipo = evidencia === "DOCUMENTO" || evidencia === "CERTIFICACION";
          return { ...requisito, evidencia, document_type_id: requiereTipo ? requisito.document_type_id : null };
        }
        if (campo === "obligatorio") {
          return { ...requisito, obligatorio: Boolean(valor) };
        }
        if (campo === "supuesto") {
          return { ...requisito, supuesto: valor as CodigoSupuesto | "" };
        }
        if (campo === "ambito") {
          return { ...requisito, ambito: valor as AmbitoRequisito };
        }
        if (campo === "document_type_id") {
          return { ...requisito, document_type_id: valor as string | null };
        }
        if (campo === "codigo" || campo === "titulo" || campo === "fuente") {
          return { ...requisito, [campo]: typeof valor === "string" ? valor : "" };
        }
        return requisito;
      }),
    );
  };

  const cambiarPlazo = (indice: number, campo: keyof FilaPlazo, valor: unknown): void => {
    setPlazos((previos) =>
      previos.map((plazo, i) => {
        if (i !== indice) return plazo;
        if (campo === "hito") {
          return { ...plazo, hito: valor as HitoPlazoPolitica };
        }
        if (campo === "unidad") {
          return { ...plazo, unidad: valor as UnidadPlazo };
        }
        if (campo === "valor") {
          return { ...plazo, valor: String(valor ?? "") };
        }
        if (campo === "fuente") {
          return { ...plazo, fuente: typeof valor === "string" && valor.trim() !== "" ? valor : null };
        }
        return plazo;
      }),
    );
  };

  const previewNumeracion = async (): Promise<void> => {
    if (!numeracionPatron.trim() || vistaPreviaPendiente) return;
    setVistaPreviaPendiente(true);
    try {
      const resultado = await vistaPreviaNumeracion(numeracionPatron.trim());
      setVistaPrevia(resultado);
    } catch (error) {
      if (error instanceof ApiError) {
        setVistaPrevia({ valido: false, motivo: error.message, ejemplos: [] });
      } else {
        setVistaPrevia({ valido: false, motivo: "No fue posible calcular la vista previa.", ejemplos: [] });
      }
    } finally {
      setVistaPreviaPendiente(false);
    }
  };

  const validar = (): ErroresFormulario => {
    const siguientes: ErroresFormulario = {};
    if (!codigo.trim()) {
      siguientes.codigo = "Indique el código.";
    }
    if (!nombre.trim()) {
      siguientes.nombre = "Indique el nombre.";
    }
    if (!vigenteDesde) {
      siguientes.vigente_desde = "Indique la fecha de vigencia.";
    }
    if (vigenteHasta && vigenteDesde && vigenteHasta < vigenteDesde) {
      siguientes.vigente_hasta = "La fecha de fin no puede ser anterior a la de inicio.";
    }
    const testigos = Number(testigosEnEntrega);
    if (!Number.isInteger(testigos) || testigos < 0 || testigos > 5) {
      siguientes.testigos_en_entrega = "Indique un número entre 0 y 5.";
    }
    const erroresVinculos: string[] = [];
    vinculos.forEach((vinculo, indice) => {
      if (!vinculo.supuesto) erroresVinculos.push(`vinculos.${indice}.supuesto`);
      if (!vinculo.alcance) erroresVinculos.push(`vinculos.${indice}.alcance`);
      if (vinculo.alcance === "UNIDAD" && !vinculo.unit_id) erroresVinculos.push(`vinculos.${indice}.unit_id`);
    });
    if (erroresVinculos.length > 0) {
      siguientes.vinculos = `Complete los supuestos declarados (${erroresVinculos.join(", ")}).`;
    }
    const erroresRequisitos: string[] = [];
    requisitos.forEach((requisito, indice) => {
      if (!requisito.codigo.trim()) erroresRequisitos.push(`requisitos.${indice}.codigo`);
      if (!requisito.titulo.trim()) erroresRequisitos.push(`requisitos.${indice}.titulo`);
      const requiereTipo = requisito.evidencia === "DOCUMENTO" || requisito.evidencia === "CERTIFICACION";
      if (requiereTipo && !requisito.document_type_id) erroresRequisitos.push(`requisitos.${indice}.document_type_id`);
    });
    if (erroresRequisitos.length > 0) {
      siguientes.requisitos = `Complete los requisitos del ente (${erroresRequisitos.join(", ")}).`;
    }
    const erroresPlazos: string[] = [];
    plazos.forEach((plazo, indice) => {
      if (!plazo.hito) erroresPlazos.push(`plazos.${indice}.hito`);
      const valor = Number(plazo.valor);
      if (plazo.valor === "" || !Number.isInteger(valor) || valor < 1) erroresPlazos.push(`plazos.${indice}.valor`);
    });
    if (erroresPlazos.length > 0) {
      siguientes.plazos = `Complete los plazos internos (${erroresPlazos.join(", ")}).`;
    }
    return siguientes;
  };

  const construirEntrada = (): PoliticaActaEntrada | null => {
    const testigos = Number(testigosEnEntrega);
    if (!Number.isInteger(testigos) || testigos < 0 || testigos > 5) return null;
    return {
      codigo: codigo.trim(),
      nombre: nombre.trim(),
      descripcion: VACIO_A_NULO(descripcion),
      fundamento: VACIO_A_NULO(fundamento),
      act_id: VACIO_A_NULO(actId),
      vigente_desde: vigenteDesde,
      vigente_hasta: VACIO_A_NULO(vigenteHasta),
      numeracion_patron: VACIO_A_NULO(numeracionPatron),
      testigos_en_entrega: testigos,
      cargo_maxima_autoridad_codigo: VACIO_A_NULO(cargoMaximaAutoridadCodigo),
      vinculos: vinculos
        .filter((v) => v.supuesto && v.alcance)
        .map((v) => ({
          supuesto: v.supuesto as CodigoSupuesto,
          alcance: v.alcance as AlcanceVinculo,
          unit_id: v.alcance === "UNIDAD" ? v.unit_id : null,
        })),
      requisitos: requisitos
        .filter((r) => r.codigo.trim() && r.titulo.trim())
        .map((r) => ({
          codigo: r.codigo.trim(),
          titulo: r.titulo.trim(),
          evidencia: r.evidencia as RequisitoPolitica["evidencia"],
          obligatorio: r.obligatorio,
          ambito: r.ambito,
          supuesto: r.supuesto ? (r.supuesto as CodigoSupuesto) : null,
          document_type_id: r.document_type_id,
          fuente: VACIO_A_NULO(r.fuente ?? ""),
        })),
      plazos: plazos
        .filter((p) => p.hito && p.valor !== "")
        .map((p) => ({
          hito: p.hito as HitoPlazoPolitica,
          valor: Number(p.valor),
          unidad: p.unidad,
          fuente: VACIO_A_NULO(p.fuente ?? ""),
        })),
    };
  };

  const enviar = async (): Promise<void> => {
    if (!puedeConfigurar || enviandoRef.current) return;
    const erroresLocales = validar();
    setErrores(erroresLocales);
    if (Object.keys(erroresLocales).length > 0) return;
    const cuerpo = construirEntrada();
    if (!cuerpo) return;
    enviandoRef.current = true;
    try {
      if (esEdicion && detalle.data) {
        const actualizada = await editarPoliticaActa(detalle.data.id, detalle.data.version, cuerpo);
        notify({ type: "success", title: "Política guardada en borrador." });
        await queryClient.invalidateQueries({ queryKey: ["gobierno-actas-politicas"] });
        navigate(`/gobierno/actas-entrega/politicas/${actualizada.id}`);
      } else {
        const creada = await crearPoliticaActa(cuerpo);
        notify({ type: "success", title: "Política guardada en borrador." });
        await queryClient.invalidateQueries({ queryKey: ["gobierno-actas-politicas"] });
        navigate(`/gobierno/actas-entrega/politicas/${creada.id}`);
      }
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.fieldErrors) {
          const erroresApi: ErroresFormulario = {};
          const generales: string[] = [];
          for (const [clave, mensajes] of Object.entries(error.fieldErrors)) {
            if (!Array.isArray(mensajes) || mensajes.length === 0) continue;
            const mensaje = mensajes[0];
            const esCampoSimple = [
              "codigo",
              "nombre",
              "descripcion",
              "fundamento",
              "act_id",
              "vigente_desde",
              "vigente_hasta",
              "numeracion_patron",
              "testigos_en_entrega",
              "cargo_maxima_autoridad_codigo",
            ].includes(clave);
            if (esCampoSimple) {
              erroresApi[clave as keyof ErroresFormulario] = mensaje;
              continue;
            }
            const esLista = /^(vinculos|requisitos|plazos)(\.\d+\.[a-z_]+)?$/.test(clave);
            if (esLista) {
              const lista = clave.split(".")[0];
              if (!("vinculos" in erroresApi) && lista === "vinculos") erroresApi.vinculos = mensaje;
              if (!("requisitos" in erroresApi) && lista === "requisitos") erroresApi.requisitos = mensaje;
              if (!("plazos" in erroresApi) && lista === "plazos") erroresApi.plazos = mensaje;
              continue;
            }
            generales.push(`${clave}: ${mensaje}`);
          }
          if (error.message && error.code !== "VALIDATION_ERROR") {
            generales.push(error.message);
          }
          if (generales.length > 0) {
            erroresApi.general = generales.join(" · ");
          }
          setErrores(erroresApi);
          return;
        }
        if (error.status === 403) {
          notify({ type: "error", title: "No tiene permiso para configurar políticas de actas" });
          return;
        }
        setErrores({ general: error.message });
        return;
      }
      notify({ type: "error", title: "No fue posible guardar la política" });
    } finally {
      enviandoRef.current = false;
    }
  };

  if (!puedeConfigurar) {
    return (
      <PageContent>
        <ErrorState
          title="Sin acceso"
          message="No tiene permiso para configurar políticas de actas."
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
            { label: "Actas de entrega", to: "/gobierno/actas-entrega" },
            { label: "Políticas", to: "/gobierno/actas-entrega/politicas" },
          ]}
          title="Editar política"
        />
        <LoadingState label="Cargando política…" />
      </PageContent>
    );
  }

  if (esEdicion && detalle.isError) {
    return (
      <PageContent>
        <PageHeader
          crumbs={[
            { label: "Gobierno" },
            { label: "Actas de entrega", to: "/gobierno/actas-entrega" },
            { label: "Políticas", to: "/gobierno/actas-entrega/politicas" },
          ]}
          title="Editar política"
        />
        <ErrorState
          title="No fue posible cargar la política"
          message="Reintente la carga de la política de actas."
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
            { label: "Actas de entrega", to: "/gobierno/actas-entrega" },
            { label: "Políticas", to: "/gobierno/actas-entrega/politicas" },
          ]}
          title={esEdicion ? "Editar política de actas" : "Nueva política de actas"}
        />
        <LoadingState label="Cargando opciones…" />
      </PageContent>
    );
  }

  if (opciones.isError || !opcionesData) {
    return (
      <PageContent>
        <PageHeader
          crumbs={[
            { label: "Gobierno" },
            { label: "Actas de entrega", to: "/gobierno/actas-entrega" },
            { label: "Políticas", to: "/gobierno/actas-entrega/politicas" },
          ]}
          title={esEdicion ? "Editar política de actas" : "Nueva política de actas"}
        />
        <ErrorState
          title="No fue posible cargar las opciones"
          message="Reintente la carga de las opciones del formulario."
        />
      </PageContent>
    );
  }

  const tituloHeader = esEdicion && detalle.data
    ? `Editar política ${detalle.data.codigo} v${detalle.data.numero_version}`
    : "Nueva política de actas";

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno" },
          { label: "Actas de entrega", to: "/gobierno/actas-entrega" },
          { label: "Políticas", to: "/gobierno/actas-entrega/politicas" },
        ]}
        title={tituloHeader}
      />
      {errores.general && (
        <div role="alert" className="form-error-general">
          {errores.general}
        </div>
      )}
      <form
        onSubmit={(evento) => {
          evento.preventDefault();
          void enviar();
        }}
        noValidate
      >
        <div className="grid-formulario">
          <FormField
            label="Código"
            error={errores.codigo}
            htmlFor="pa-codigo"
            required
          >
            <TextInput
              id="pa-codigo"
              value={codigo}
              onChange={(e) => {
                setCodigo(e.target.value);
                limpiarError("codigo");
              }}
              disabled={esEdicion}
            />
          </FormField>
          <FormField
            label="Nombre"
            error={errores.nombre}
            htmlFor="pa-nombre"
            required
          >
            <TextInput
              id="pa-nombre"
              value={nombre}
              onChange={(e) => {
                setNombre(e.target.value);
                limpiarError("nombre");
              }}
            />
          </FormField>
          <FormField
            label="Descripción"
            error={errores.descripcion}
            htmlFor="pa-descripcion"
          >
            <textarea
              id="pa-descripcion"
              value={descripcion}
              onChange={(evento) => {
                setDescripcion(evento.target.value);
                limpiarError("descripcion");
              }}
              rows={3}
            />
          </FormField>
          <FormField
            label="Fundamento"
            error={errores.fundamento}
            htmlFor="pa-fundamento"
            help="Obligatorio para activar"
          >
            <textarea
              id="pa-fundamento"
              value={fundamento}
              onChange={(evento) => {
                setFundamento(evento.target.value);
                limpiarError("fundamento");
              }}
              rows={3}
            />
          </FormField>
          <FormField
            label="Acto que la aprueba"
            error={errores.act_id}
            htmlFor="pa-acto"
          >
            <select
              id="pa-acto"
              className={CLASES_SELECT}
              value={actId}
              onChange={(e) => {
                setActId(e.target.value);
                limpiarError("act_id");
              }}
            >
              <option value="">Seleccione un acto</option>
              {opcionesData.actos.map((acto) => (
                <option key={acto.id} value={acto.id}>
                  {acto.etiqueta}
                </option>
              ))}
            </select>
          </FormField>
          <FormField
            label="Vigente desde"
            error={errores.vigente_desde}
            htmlFor="pa-vigente-desde"
            required
          >
            <DateInput
              id="pa-vigente-desde"
              value={vigenteDesde}
              onChange={(e) => {
                setVigenteDesde(e.target.value);
                limpiarError("vigente_desde");
              }}
            />
          </FormField>
          <FormField
            label="Vigente hasta"
            error={errores.vigente_hasta}
            htmlFor="pa-vigente-hasta"
          >
            <DateInput
              id="pa-vigente-hasta"
              value={vigenteHasta}
              onChange={(e) => {
                setVigenteHasta(e.target.value);
                limpiarError("vigente_hasta");
              }}
            />
          </FormField>
          <FormField
            label="Patrón de numeración"
            error={errores.numeracion_patron}
            htmlFor="pa-numeracion-patron"
            help={`Por defecto: ${opcionesData.patron_por_defecto}. Use {ANIO} y {NUMERO:n}.`}
          >
            <div className="campo-con-accion">
              <TextInput
                id="pa-numeracion-patron"
                value={numeracionPatron}
                onChange={(e) => {
                  setNumeracionPatron(e.target.value);
                  limpiarError("numeracion_patron");
                  setVistaPrevia(null);
                }}
              />
              <Button
                type="button"
                onClick={() => void previewNumeracion()}
                disabled={!numeracionPatron.trim() || vistaPreviaPendiente}
              >
                Vista previa
              </Button>
            </div>
            {vistaPrevia && (
              <div aria-live="polite" className="vista-previa-numeracion">
                {vistaPrevia.valido
                  ? vistaPrevia.ejemplos.slice(0, VISTA_PREVIA_CANTIDAD).map((ejemplo) => (
                      <span key={ejemplo}>{ejemplo}</span>
                    ))
                  : vistaPrevia.motivo}
              </div>
            )}
          </FormField>
          <FormField
            label="Testigos en la entrega por el saliente"
            error={errores.testigos_en_entrega}
            htmlFor="pa-testigos-en-entrega"
          >
            <input
              id="pa-testigos-en-entrega"
              type="number"
              min={0}
              max={5}
              value={testigosEnEntrega}
              onChange={(evento) => {
                setTestigosEnEntrega(evento.target.value);
                limpiarError("testigos_en_entrega");
              }}
            />
          </FormField>
          <FormField
            label="Código del cargo de máxima autoridad"
            error={errores.cargo_maxima_autoridad_codigo}
            htmlFor="pa-cargo-maxima-autoridad"
            help="El acta de quien ocupa este cargo es el acta de la entidad (N34 art. 6)."
          >
            <TextInput
              id="pa-cargo-maxima-autoridad"
              value={cargoMaximaAutoridadCodigo}
              onChange={(e) => {
                setCargoMaximaAutoridadCodigo(e.target.value);
                limpiarError("cargo_maxima_autoridad_codigo");
              }}
            />
          </FormField>
        </div>

        <section className="panel-informativo" aria-labelledby="pa-catalogo-legal-titulo">
          <h2 id="pa-catalogo-legal-titulo">Catálogo legal (N34)</h2>
          {opcionesData.supuestos.map((supuesto) => {
            const detalleSupuesto = supuesto.vinculo === "UNIVERSAL"
              ? " — rige en toda acta"
              : supuesto.declarable
                ? " — declarable"
                : ` — no aplica: ${supuesto.motivo_no_declarable ?? "No declarable"}`;
            return (
              <article key={supuesto.codigo} className="supuesto-catalogo">
                <p>
                  N34 art. {supuesto.articulo} · {supuesto.titulo}{detalleSupuesto}
                </p>
                {supuesto.anexos.length > 0 && (
                  <ul>
                    {supuesto.anexos.map((anexo) => (
                      <li key={anexo.codigo}>
                        {anexo.codigo} · {anexo.titulo}
                      </li>
                    ))}
                  </ul>
                )}
              </article>
            );
          })}
          <div className="catalogo-legal-extra">
            <p>Testigos legales: {opcionesData.testigos_legales.modalidad} · {opcionesData.testigos_legales.testigos} testigos{opcionesData.testigos_legales.auditor_interno ? " · auditor interno" : ""} ({opcionesData.testigos_legales.fuente})</p>
            {opcionesData.plazos_legales.map((legal) => (
              <p key={legal.hito}>
                Plazo legal de {ETIQUETAS_HITO[legal.hito as HitoPlazoPolitica]}: {describirPlazo({ valor: legal.valor, unidad: legal.unidad })} ({legal.fuente})
              </p>
            ))}
          </div>
        </section>

        <section aria-labelledby="pa-vinculos-titulo">
          <h2 id="pa-vinculos-titulo">Supuestos declarados</h2>
          {errores.vinculos && <div role="alert">{errores.vinculos}</div>}
          {vinculos.map((vinculo, indice) => (
            <div key={`vinculo-${indice}`} className="fila-lista">
              <FormField
                label={`Supuesto ${indice + 1}`}
                htmlFor={`pa-vinculo-supuesto-${indice}`}
              >
                <select
                  id={`pa-vinculo-supuesto-${indice}`}
                  className={CLASES_SELECT}
                  value={vinculo.supuesto}
                  onChange={(e) => cambiarVinculo(indice, "supuesto", e.target.value)}
                >
                  <option value="">Seleccione un supuesto</option>
                  {supuestosDeclarables.map((supuesto) => (
                    <option key={supuesto.codigo} value={supuesto.codigo}>
                      N34 art. {supuesto.articulo} · {supuesto.titulo}
                    </option>
                  ))}
                </select>
              </FormField>
              <FormField
                label={`Alcance ${indice + 1}`}
                htmlFor={`pa-vinculo-alcance-${indice}`}
              >
                <select
                  id={`pa-vinculo-alcance-${indice}`}
                  className={CLASES_SELECT}
                  value={vinculo.alcance}
                  onChange={(e) => cambiarVinculo(indice, "alcance", e.target.value)}
                >
                  <option value="">Seleccione el alcance</option>
                  {ambitosDelSupuesto(vinculo.supuesto).map((alcance) => (
                    <option key={alcance} value={alcance}>
                      {alcance === "ENTE" ? "Entidad" : "Unidad"}
                    </option>
                  ))}
                </select>
              </FormField>
              {vinculo.alcance === "UNIDAD" && (
                <FormField
                  label={`Unidad ${indice + 1}`}
                  htmlFor={`pa-vinculo-unidad-${indice}`}
                >
                  <select
                    id={`pa-vinculo-unidad-${indice}`}
                    className={CLASES_SELECT}
                    value={vinculo.unit_id ?? ""}
                    onChange={(e) => cambiarVinculo(indice, "unit_id", e.target.value)}
                  >
                    <option value="">Seleccione una unidad</option>
                    {opcionesData.unidades.map((unidad) => (
                      <option key={unidad.id} value={unidad.id}>
                        {unidad.codigo} · {unidad.nombre}
                      </option>
                    ))}
                  </select>
                </FormField>
              )}
              <Button
                type="button"
                onClick={() => setVinculos((previos) => previos.filter((_, i) => i !== indice))}
              >
                Quitar
              </Button>
            </div>
          ))}
          <Button type="button" onClick={() => setVinculos((previos) => [...previos, nuevaFilaVinculo()])}>
            Añadir supuesto
          </Button>
        </section>

        <section aria-labelledby="pa-requisitos-titulo">
          <h2 id="pa-requisitos-titulo">Requisitos del ente</h2>
          {errores.requisitos && <div role="alert">{errores.requisitos}</div>}
          {requisitos.map((requisito, indice) => {
            const requiereTipo = requisito.evidencia === "DOCUMENTO" || requisito.evidencia === "CERTIFICACION";
            return (
              <div key={`requisito-${indice}`} className="fila-lista">
                <FormField
                  label={`Código del requisito ${indice + 1}`}
                  htmlFor={`pa-requisito-codigo-${indice}`}
                >
                  <TextInput
                    id={`pa-requisito-codigo-${indice}`}
                    value={requisito.codigo}
                    onChange={(e) => cambiarRequisito(indice, "codigo", e.target.value)}
                  />
                </FormField>
                <FormField
                  label={`Requisito ${indice + 1}`}
                  htmlFor={`pa-requisito-${indice}`}
                >
                  <TextInput
                    id={`pa-requisito-${indice}`}
                    value={requisito.titulo}
                    onChange={(e) => cambiarRequisito(indice, "titulo", e.target.value)}
                  />
                </FormField>
                <FormField
                  label={`Evidencia ${indice + 1}`}
                  htmlFor={`pa-requisito-evidencia-${indice}`}
                >
                  <select
                    id={`pa-requisito-evidencia-${indice}`}
                    className={CLASES_SELECT}
                    value={requisito.evidencia}
                    onChange={(e) => cambiarRequisito(indice, "evidencia", e.target.value)}
                  >
                    {Object.entries(ETIQUETAS_EVIDENCIA).map(([valor, etiqueta]) => (
                      <option key={valor} value={valor}>
                        {etiqueta}
                      </option>
                    ))}
                  </select>
                </FormField>
                <FormField
                  label={`Obligatorio ${indice + 1}`}
                  htmlFor={`pa-requisito-obligatorio-${indice}`}
                >
                  <input
                    id={`pa-requisito-obligatorio-${indice}`}
                    type="checkbox"
                    checked={requisito.obligatorio}
                    onChange={(evento) => cambiarRequisito(indice, "obligatorio", evento.target.checked)}
                  />
                </FormField>
                <FormField
                  label={`Ámbito ${indice + 1}`}
                  htmlFor={`pa-requisito-ambito-${indice}`}
                >
                  <select
                    id={`pa-requisito-ambito-${indice}`}
                    className={CLASES_SELECT}
                    value={requisito.ambito}
                    onChange={(e) => cambiarRequisito(indice, "ambito", e.target.value)}
                  >
                    <option value="TODAS">Todas las actas</option>
                    <option value="ENTE">Acta de la entidad</option>
                    <option value="UNIDAD">Acta de una unidad</option>
                  </select>
                </FormField>
                <FormField
                  label={`Supuesto del requisito ${indice + 1}`}
                  htmlFor={`pa-requisito-supuesto-${indice}`}
                >
                  <select
                    id={`pa-requisito-supuesto-${indice}`}
                    className={CLASES_SELECT}
                    value={requisito.supuesto}
                    onChange={(e) => cambiarRequisito(indice, "supuesto", e.target.value)}
                  >
                    <option value="">Ninguno</option>
                    {supuestosDeclarados.map((supuesto) => (
                      <option key={supuesto.codigo} value={supuesto.codigo}>
                        N34 art. {supuesto.articulo} · {supuesto.titulo}
                      </option>
                    ))}
                  </select>
                </FormField>
                {requiereTipo && (
                  <FormField
                    label={`Tipo documental ${indice + 1}`}
                    htmlFor={`pa-requisito-tipo-documental-${indice}`}
                  >
                    <select
                      id={`pa-requisito-tipo-documental-${indice}`}
                      className={CLASES_SELECT}
                      value={requisito.document_type_id ?? ""}
                      onChange={(e) => cambiarRequisito(indice, "document_type_id", e.target.value)}
                    >
                      <option value="">Seleccione un tipo documental</option>
                      {opcionesData.tipos_documento.map((tipo) => (
                        <option key={tipo.id} value={tipo.id}>
                          {tipo.nombre}
                        </option>
                      ))}
                    </select>
                  </FormField>
                )}
                <FormField
                  label={`Fuente ${indice + 1}`}
                  htmlFor={`pa-requisito-fuente-${indice}`}
                >
                  <TextInput
                    id={`pa-requisito-fuente-${indice}`}
                    value={requisito.fuente ?? ""}
                    onChange={(e) => cambiarRequisito(indice, "fuente", e.target.value)}
                  />
                </FormField>
                <Button
                  type="button"
                  onClick={() => setRequisitos((previos) => previos.filter((_, i) => i !== indice))}
                >
                  Quitar
                </Button>
              </div>
            );
          })}
          <Button type="button" onClick={() => setRequisitos((previos) => [...previos, nuevaFilaRequisito()])}>
            Añadir requisito
          </Button>
        </section>

        <section aria-labelledby="pa-plazos-titulo">
          <h2 id="pa-plazos-titulo">Plazos internos</h2>
          {errores.plazos && <div role="alert">{errores.plazos}</div>}
          {plazos.map((plazo, indice) => {
            const legal = opcionesData.plazos_legales.find((p) => p.hito === plazo.hito);
            return (
              <div key={`plazo-${indice}`} className="fila-lista">
                <FormField
                  label={`Hito ${indice + 1}`}
                  htmlFor={`pa-plazo-hito-${indice}`}
                >
                  <select
                    id={`pa-plazo-hito-${indice}`}
                    className={CLASES_SELECT}
                    value={plazo.hito}
                    onChange={(e) => cambiarPlazo(indice, "hito", e.target.value)}
                  >
                    <option value="">Seleccione un hito</option>
                    <option value="ELABORACION">{ETIQUETAS_HITO.ELABORACION}</option>
                    <option value="REMISION_UAI">{ETIQUETAS_HITO.REMISION_UAI}</option>
                  </select>
                </FormField>
                <FormField
                  label={`Días ${indice + 1}`}
                  htmlFor={`pa-plazo-valor-${indice}`}
                >
                  <input
                    id={`pa-plazo-valor-${indice}`}
                    type="number"
                    min={1}
                    value={plazo.valor}
                    onChange={(evento) => cambiarPlazo(indice, "valor", evento.target.value)}
                  />
                </FormField>
                <FormField
                  label={`Unidad ${indice + 1}`}
                  htmlFor={`pa-plazo-unidad-${indice}`}
                >
                  <select
                    id={`pa-plazo-unidad-${indice}`}
                    className={CLASES_SELECT}
                    value={plazo.unidad}
                    onChange={(e) => cambiarPlazo(indice, "unidad", e.target.value)}
                  >
                    <option value="DIAS_HABILES">Días hábiles</option>
                    <option value="DIAS_CONTINUOS">Días continuos</option>
                  </select>
                </FormField>
                <FormField
                  label={`Fuente del plazo ${indice + 1}`}
                  htmlFor={`pa-plazo-fuente-${indice}`}
                >
                  <TextInput
                    id={`pa-plazo-fuente-${indice}`}
                    value={plazo.fuente ?? ""}
                    onChange={(e) => cambiarPlazo(indice, "fuente", e.target.value)}
                  />
                </FormField>
                {legal && (
                  <p>
                    Plazo legal: {describirPlazo({ valor: legal.valor, unidad: legal.unidad })} ({legal.fuente}). El interno no puede superarlo.
                  </p>
                )}
                <Button
                  type="button"
                  onClick={() => setPlazos((previos) => previos.filter((_, i) => i !== indice))}
                >
                  Quitar
                </Button>
              </div>
            );
          })}
          <Button type="button" onClick={() => setPlazos((previos) => [...previos, nuevaFilaPlazo()])}>
            Añadir plazo
          </Button>
        </section>

        <div className="acciones-formulario">
          <AsyncButton type="submit" onClick={() => enviar()}>
            Guardar borrador
          </AsyncButton>
          <Button
            type="button"
            onClick={() =>
              navigate(
                esEdicion && detalle.data
                  ? `/gobierno/actas-entrega/politicas/${detalle.data.id}`
                  : "/gobierno/actas-entrega/politicas",
              )
            }
          >
            Cancelar
          </Button>
        </div>
      </form>
    </PageContent>
  );
}
