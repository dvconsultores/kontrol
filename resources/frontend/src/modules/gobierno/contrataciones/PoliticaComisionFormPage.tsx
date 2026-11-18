import { useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";

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
import {
  CONSULTA_POLITICAS_COMISION,
  RUTA_POLITICAS,
  type PoliticaComisionCatalogo,
  type PoliticaComisionDetalle,
  type PoliticaComisionOpciones,
} from "@/modules/gobierno/contrataciones/politicasComision";

type RequisitoFormulario = {
  etiqueta: string;
  funcion: string;
  condicion: string;
  tipo: string;
  area: string | null;
  position_id: string | null;
  unit_id: string | null;
  competencia_accion: string | null;
  competencia_materia: string | null;
  official_id: string | null;
  minimo: number;
  maximo: number | null;
};

type DocumentoFormulario = {
  document_type_id: string;
  etapa: string;
  obligatorio: boolean;
  condicion: string | null;
};

type ErroresFormulario = {
  codigo?: string;
  nombre?: string;
  vigente_desde?: string;
  vigente_hasta?: string;
  min_principales?: string;
  max_principales?: string;
  quorum?: string;
  decision?: string;
  requisitos?: string;
  documentos?: string;
  aplica?: string;
  general?: string;
};

const REQUISITO_VACIO: RequisitoFormulario = {
  etiqueta: "",
  funcion: "",
  condicion: "",
  tipo: "",
  area: null,
  position_id: null,
  unit_id: null,
  competencia_accion: null,
  competencia_materia: null,
  official_id: null,
  minimo: 1,
  maximo: null,
};

const DOCUMENTO_VACIO: DocumentoFormulario = {
  document_type_id: "",
  etapa: "",
  obligatorio: true,
  condicion: null,
};

export function PoliticaComisionFormPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const { politicaId } = useParams();

  const esEdicion = Boolean(politicaId);
  const puedeConfigurar = tiene("gobierno_comisiones:configure", "empresa");

  const [codigo, setCodigo] = useState("");
  const [nombre, setNombre] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [tipoComision, setTipoComision] = useState("");
  const [aplicaApertura, setAplicaApertura] = useState(true);
  const [aplicaRecomendacion, setAplicaRecomendacion] = useState(true);
  const [baseNormativa, setBaseNormativa] = useState("NINGUNA");
  const [fundamento, setFundamento] = useState("");
  const [vigenteDesde, setVigenteDesde] = useState("");
  const [vigenteHasta, setVigenteHasta] = useState("");
  const [minPrincipales, setMinPrincipales] = useState(1);
  const [maxPrincipales, setMaxPrincipales] = useState<number | null>(null);
  const [exigeImpar, setExigeImpar] = useState(false);
  const [suplentePorPrincipal, setSuplentePorPrincipal] = useState(false);
  const [exigeSecretario, setExigeSecretario] = useState(false);
  const [exigeSuplenteSecretario, setExigeSuplenteSecretario] = useState(false);
  const [exigePresidente, setExigePresidente] = useState(false);
  const [quorumTipo, setQuorumTipo] = useState("");
  const [quorumCantidad, setQuorumCantidad] = useState<number | null>(null);
  const [quorumNumerador, setQuorumNumerador] = useState<number | null>(null);
  const [quorumDenominador, setQuorumDenominador] = useState<number | null>(null);
  const [decisionTipo, setDecisionTipo] = useState("");
  const [decisionCantidad, setDecisionCantidad] = useState<number | null>(null);
  const [decisionNumerador, setDecisionNumerador] = useState<number | null>(null);
  const [decisionDenominador, setDecisionDenominador] = useState<number | null>(null);
  const [decisionBase, setDecisionBase] = useState("");
  const [presidenteVota, setPresidenteVota] = useState(false);
  const [presidenteDirimente, setPresidenteDirimente] = useState(false);
  const [actoRequerido, setActoRequerido] = useState(false);
  const [actoMedio, setActoMedio] = useState("");
  const [requisitos, setRequisitos] = useState<RequisitoFormulario[]>([]);
  const [documentos, setDocumentos] = useState<DocumentoFormulario[]>([]);
  const [errores, setErrores] = useState<ErroresFormulario>({});
  const enviandoRef = useRef(false);
  const [detalleCargado, setDetalleCargado] = useState(false);

  const catalogo = useQuery({
    queryKey: [...CONSULTA_POLITICAS_COMISION, "catalogo", activeCompanyId],
    queryFn: () =>
      apiFetch<PoliticaComisionCatalogo>(`${RUTA_POLITICAS}/catalogo`),
    enabled: puedeConfigurar && Boolean(activeCompanyId),
    retry: false,
  });

  const opciones = useQuery({
    queryKey: [...CONSULTA_POLITICAS_COMISION, "opciones", activeCompanyId],
    queryFn: () =>
      apiFetch<PoliticaComisionOpciones>(`${RUTA_POLITICAS}/opciones`),
    enabled: puedeConfigurar && Boolean(activeCompanyId),
    retry: false,
  });

  const detalle = useQuery({
    queryKey: [
      ...CONSULTA_POLITICAS_COMISION,
      "politica-detalle",
      activeCompanyId,
      politicaId,
    ],
    queryFn: () =>
      apiFetch<PoliticaComisionDetalle>(`${RUTA_POLITICAS}/${politicaId}`),
    enabled: puedeConfigurar && esEdicion && Boolean(activeCompanyId),
    retry: false,
  });

  const esPisoLegal = baseNormativa === "LCP_ART14";

  if (!puedeConfigurar || !activeCompanyId) {
    return (
      <PageContent>
        <EmptyState
          title="Sin acceso"
          description="No tiene permisos para configurar políticas de comisión."
        />
      </PageContent>
    );
  }

  if (
    catalogo.isLoading ||
    opciones.isLoading ||
    (esEdicion && detalle.isLoading)
  ) {
    return (
      <PageContent>
        <LoadingState />
      </PageContent>
    );
  }

  if (
    catalogo.isError ||
    opciones.isError ||
    (esEdicion && detalle.isError)
  ) {
    const error = catalogo.isError
      ? catalogo.error
      : opciones.isError
        ? opciones.error
        : detalle.error;
    return (
      <PageContent>
        <ErrorDeCarga
          message={
            error instanceof Error
              ? error.message
              : "No fue posible cargar la política de comisión."
          }
          onRetry={() => {
            if (catalogo.isError) catalogo.refetch();
            if (opciones.isError) opciones.refetch();
            if (esEdicion && detalle.isError) detalle.refetch();
          }}
        />
      </PageContent>
    );
  }

  if (esEdicion && detalle.data) {
    if (!detalle.data.puede_editar) {
      return (
        <PageContent>
          <EmptyState
            title="No editable"
            description="Esta política ya no es un borrador; cree una nueva versión desde su ficha."
            action={
              <Link
                to={`${RUTA_POLITICAS}/${detalle.data.id}`}
                className="text-brand-700 underline"
              >
                Volver a la política
              </Link>
            }
          />
        </PageContent>
      );
    }
    if (!detalleCargado) {
      setCodigo(detalle.data.codigo);
      setNombre(detalle.data.nombre);
      setDescripcion(detalle.data.descripcion ?? "");
      setTipoComision(detalle.data.tipo_comision);
      setAplicaApertura(detalle.data.aplica_apertura);
      setAplicaRecomendacion(detalle.data.aplica_recomendacion);
      setBaseNormativa(detalle.data.base_normativa);
      setFundamento(detalle.data.fundamento ?? "");
      setVigenteDesde(detalle.data.vigente_desde);
      setVigenteHasta(detalle.data.vigente_hasta ?? "");
      setMinPrincipales(detalle.data.min_principales);
      setMaxPrincipales(detalle.data.max_principales);
      setExigeImpar(detalle.data.exige_impar);
      setSuplentePorPrincipal(detalle.data.suplente_por_principal);
      setExigeSecretario(detalle.data.exige_secretario);
      setExigeSuplenteSecretario(detalle.data.exige_suplente_secretario);
      setExigePresidente(detalle.data.exige_presidente);
      setQuorumTipo(detalle.data.quorum.tipo);
      setQuorumCantidad(detalle.data.quorum.cantidad);
      setQuorumNumerador(detalle.data.quorum.numerador);
      setQuorumDenominador(detalle.data.quorum.denominador);
      setDecisionTipo(detalle.data.decision.tipo);
      setDecisionCantidad(detalle.data.decision.cantidad);
      setDecisionNumerador(detalle.data.decision.numerador);
      setDecisionDenominador(detalle.data.decision.denominador);
      setDecisionBase(detalle.data.decision.base);
      setPresidenteVota(detalle.data.presidente_vota);
      setPresidenteDirimente(detalle.data.presidente_dirimente);
      setActoRequerido(detalle.data.acto_requerido);
      setActoMedio(detalle.data.acto_medio ?? "");
      setRequisitos(
        detalle.data.requisitos.map((r) => ({
          etiqueta: r.etiqueta,
          funcion: r.funcion,
          condicion: r.condicion,
          tipo: r.tipo,
          area: r.area ?? null,
          position_id: r.position_id ?? null,
          unit_id: r.unit_id ?? null,
          competencia_accion: r.competencia_accion ?? null,
          competencia_materia: r.competencia_materia ?? null,
          official_id: r.official_id ?? null,
          minimo: r.minimo,
          maximo: r.maximo ?? null,
        })),
      );
      setDocumentos(
        detalle.data.documentos.map((d) => ({
          document_type_id: d.document_type_id,
          etapa: d.etapa,
          obligatorio: d.obligatorio,
          condicion: d.condicion ?? null,
        })),
      );
      setDetalleCargado(true);
    }
  }

  const limpiarError = (campo: keyof ErroresFormulario) => {
    setErrores((previos) => ({ ...previos, [campo]: undefined }));
  };

  const inputClase = (error?: string) =>
    `w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600 ${
      error ? "border-danger-600" : "border-border-default"
    }`;

  const textareaClase = (error?: string) =>
    `min-h-24 w-full rounded-md border bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600 ${
      error ? "border-danger-600" : "border-border-default"
    }`;

  const checkboxClase = "h-4 w-4 rounded border-border-default text-brand-600 focus:ring-brand-600";

  const cambiarTipoRequisito = (indice: number, tipo: string) => {
    setRequisitos((previos) =>
      previos.map((r, i) =>
        i === indice
          ? {
              ...r,
              tipo,
              area: null,
              position_id: null,
              unit_id: null,
              competencia_accion: null,
              competencia_materia: null,
              official_id: null,
            }
          : r,
      ),
    );
  };

  const validarLocal = (): boolean => {
    const nuevos: ErroresFormulario = {};

    if (!esEdicion && !codigo.trim()) {
      nuevos.codigo = "El código es obligatorio.";
    }
    if (!nombre.trim()) {
      nuevos.nombre = "El nombre es obligatorio.";
    }
    if (!vigenteDesde) {
      nuevos.vigente_desde = "La fecha desde es obligatoria.";
    }
    if (vigenteHasta && vigenteDesde && vigenteHasta < vigenteDesde) {
      nuevos.vigente_hasta = "La fecha hasta no puede ser anterior a la desde.";
    }
    if (maxPrincipales !== null && maxPrincipales < minPrincipales) {
      nuevos.max_principales = "El máximo no puede ser menor que el mínimo.";
    }
    if (minPrincipales < 1) {
      nuevos.min_principales = "El mínimo debe ser al menos 1.";
    }

    if (quorumTipo === "ABSOLUTE_COUNT" && (quorumCantidad === null || quorumCantidad < 1)) {
      nuevos.quorum = "La cantidad debe ser al menos 1.";
    }
    if (quorumTipo === "QUALIFIED_MAJORITY") {
      if (
        quorumNumerador === null ||
        quorumDenominador === null ||
        quorumNumerador < 1 ||
        quorumDenominador < 1 ||
        quorumNumerador > quorumDenominador ||
        2 * quorumNumerador <= quorumDenominador
      ) {
        nuevos.quorum = "Fracción mayor que la mitad, p. ej. 2/3.";
      }
    }

    if (decisionTipo === "ABSOLUTE_COUNT" && (decisionCantidad === null || decisionCantidad < 1)) {
      nuevos.decision = "La cantidad debe ser al menos 1.";
    }
    if (decisionTipo === "QUALIFIED_MAJORITY") {
      if (
        decisionNumerador === null ||
        decisionDenominador === null ||
        decisionNumerador < 1 ||
        decisionDenominador < 1 ||
        decisionNumerador > decisionDenominador ||
        2 * decisionNumerador <= decisionDenominador
      ) {
        nuevos.decision = "Fracción mayor que la mitad, p. ej. 2/3.";
      }
    }

    if (!aplicaApertura && !aplicaRecomendacion) {
      nuevos.aplica = "La política debe aplicar al menos a la apertura o a la recomendación.";
    }

    for (const r of requisitos) {
      if (!r.etiqueta.trim()) {
        nuevos.requisitos = "Cada requisito necesita una etiqueta.";
        break;
      }
      if (!r.funcion || !r.condicion || !r.tipo) {
        nuevos.requisitos = "Elija la función, la condición y el tipo de cada requisito.";
        break;
      }
      if (r.tipo === "AREA" && !r.area) {
        nuevos.requisitos = "Seleccione el área del requisito.";
        break;
      }
      if (r.tipo === "CARGO" && !r.position_id) {
        nuevos.requisitos = "Seleccione el cargo del requisito.";
        break;
      }
      if (r.tipo === "UNIDAD" && !r.unit_id) {
        nuevos.requisitos = "Seleccione la unidad del requisito.";
        break;
      }
      if (r.tipo === "COMPETENCIA" && (!r.competencia_accion || !r.competencia_materia)) {
        nuevos.requisitos = "Seleccione acción y materia de competencia.";
        break;
      }
      if (r.tipo === "FUNCIONARIO" && !r.official_id) {
        nuevos.requisitos = "Seleccione el funcionario del requisito.";
        break;
      }
    }

    for (const d of documentos) {
      if (!d.document_type_id) {
        nuevos.documentos = "Cada documento necesita un tipo documental.";
        break;
      }
    }

    setErrores(nuevos);
    return Object.keys(nuevos).length === 0;
  };

  const enviar = async () => {
    if (enviandoRef.current) return;
    if (!validarLocal()) return;

    const cuerpo = {
      codigo: codigo.trim(),
      nombre: nombre.trim(),
      descripcion: descripcion.trim() || null,
      tipo_comision: tipoComision,
      aplica_apertura: aplicaApertura,
      aplica_recomendacion: aplicaRecomendacion,
      base_normativa: baseNormativa,
      fundamento: fundamento.trim() || null,
      vigente_desde: vigenteDesde,
      vigente_hasta: vigenteHasta || null,
      min_principales: minPrincipales,
      max_principales: maxPrincipales,
      exige_impar: exigeImpar,
      suplente_por_principal: suplentePorPrincipal,
      exige_secretario: exigeSecretario,
      exige_suplente_secretario: exigeSuplenteSecretario,
      exige_presidente: exigePresidente,
      quorum: {
        tipo: quorumTipo,
        cantidad: quorumCantidad,
        numerador: quorumNumerador,
        denominador: quorumDenominador,
      },
      decision: {
        tipo: decisionTipo,
        cantidad: decisionCantidad,
        numerador: decisionNumerador,
        denominador: decisionDenominador,
        base: decisionBase,
      },
      presidente_vota: presidenteVota,
      presidente_dirimente: presidenteDirimente,
      acto_requerido: actoRequerido,
      acto_medio: actoMedio || null,
      requisitos: requisitos.map((r) => ({
        etiqueta: r.etiqueta.trim(),
        funcion: r.funcion,
        condicion: r.condicion,
        tipo: r.tipo,
        area: r.area,
        position_id: r.position_id,
        unit_id: r.unit_id,
        competencia_accion: r.competencia_accion,
        competencia_materia: r.competencia_materia,
        official_id: r.official_id,
        minimo: r.minimo,
        maximo: r.maximo,
      })),
      documentos: documentos.map((d) => ({
        document_type_id: d.document_type_id,
        etapa: d.etapa,
        obligatorio: d.obligatorio,
        condicion: d.condicion || null,
      })),
    };

    enviandoRef.current = true;
    try {
      if (esEdicion && detalle.data) {
        const actualizado = await apiFetch<PoliticaComisionDetalle>(
          `${RUTA_POLITICAS}/${detalle.data.id}`,
          {
            method: "PUT",
            body: cuerpo,
            ifMatch: String(detalle.data.version),
          },
        );
        notify({ type: "success", title: "Política guardada" });
        await queryClient.invalidateQueries({ queryKey: [...CONSULTA_POLITICAS_COMISION] });
        navigate(`${RUTA_POLITICAS}/${actualizado.id}`);
      } else {
        const creado = await apiFetch<PoliticaComisionDetalle>(RUTA_POLITICAS, {
          method: "POST",
          body: cuerpo,
        });
        notify({ type: "success", title: "Política guardada" });
        await queryClient.invalidateQueries({ queryKey: [...CONSULTA_POLITICAS_COMISION] });
        navigate(`${RUTA_POLITICAS}/${creado.id}`);
      }
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 422 && Object.keys(error.fieldErrors).length > 0) {
          // Las claves compuestas del validador («requisitos.0.funcion») se muestran en su sección.
          const primeroDe = (prefijo: string): string | undefined =>
            Object.entries(error.fieldErrors).find(([clave]) => clave.startsWith(`${prefijo}.`))?.[1]?.[0];
          setErrores({
            codigo: error.fieldErrors.codigo?.[0],
            nombre: error.fieldErrors.nombre?.[0],
            vigente_desde: error.fieldErrors.vigente_desde?.[0],
            vigente_hasta: error.fieldErrors.vigente_hasta?.[0],
            min_principales: error.fieldErrors.min_principales?.[0],
            max_principales: error.fieldErrors.max_principales?.[0],
            quorum: error.fieldErrors.quorum?.[0],
            decision: error.fieldErrors.decision?.[0],
            requisitos: error.fieldErrors.requisitos?.[0] ?? primeroDe("requisitos"),
            documentos: error.fieldErrors.documentos?.[0] ?? primeroDe("documentos"),
            aplica: error.fieldErrors.aplica_apertura?.[0],
            general: error.fieldErrors["_"]?.[0] ?? error.message,
          });
          return;
        }
        if (error.status === 409 && error.code === "GOV_COMMISSION_POLICY_CODE_TAKEN") {
          setErrores({ codigo: "El código ya está en uso." });
          return;
        }
        if (error.status === 409 && error.code === "GOV_COMMISSION_POLICY_NOT_DRAFT") {
          setErrores({ general: "La política ya no es un borrador; cree una nueva versión." });
          return;
        }
        if (error.code?.startsWith("GOV_COMMISSION_POLICY_")) {
          setErrores({ general: error.message });
          return;
        }
      }
      setErrores({ general: "No se pudo guardar la política." });
    } finally {
      enviandoRef.current = false;
    }
  };

  const tiposComision = catalogo.data?.tipos_comision ?? [];
  const basesNormativas = catalogo.data?.bases_normativas ?? [];
  const tiposMayoria = catalogo.data?.tipos_mayoria ?? [];
  const basesDecision = catalogo.data?.bases_decision ?? [];
  const funciones = catalogo.data?.funciones ?? [];
  const condiciones = catalogo.data?.condiciones ?? [];
  const tiposRequisito = catalogo.data?.tipos_requisito ?? [];
  const areas = catalogo.data?.areas ?? [];
  const etapas = catalogo.data?.etapas ?? [];
  const medios = catalogo.data?.medios ?? [];
  const accionesCompetencia = catalogo.data?.acciones_competencia ?? [];
  const materiasCompetencia = catalogo.data?.materias_competencia ?? [];
  const cargos = opciones.data?.cargos ?? [];
  const unidades = opciones.data?.unidades ?? [];
  const funcionarios = opciones.data?.funcionarios ?? [];
  const tiposDocumentales = opciones.data?.tipos_documentales ?? [];

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno" },
          { label: "Contrataciones" },
          {
            label: "Políticas de comisión",
            to: RUTA_POLITICAS,
          },
        ]}
        title={esEdicion ? "Editar política de comisión" : "Nueva política de comisión"}
        description="Registre la política. Queda en borrador hasta que otra persona la active."
      />

      <form
        noValidate
        className="mt-4 space-y-8"
        onSubmit={(e) => {
          e.preventDefault();
          void enviar();
        }}
      >
        <section aria-labelledby="identidad-titulo">
          <h2 id="identidad-titulo" className="text-lg font-semibold text-text-900">
            Identidad
          </h2>
          <div className="mt-2 space-y-4">
            {!esEdicion && (
              <FormField
                label="Código"
                htmlFor="politica-codigo"
                required
                error={errores.codigo}
              >
                <input
                  id="politica-codigo"
                  type="text"
                  value={codigo}
                  onChange={(evento) => {
                    setCodigo(evento.target.value);
                    limpiarError("codigo");
                  }}
                  aria-invalid={Boolean(errores.codigo)}
                  className={inputClase(errores.codigo)}
                />
              </FormField>
            )}
            <FormField
              label="Nombre"
              htmlFor="politica-nombre"
              required
              error={errores.nombre}
            >
              <input
                id="politica-nombre"
                type="text"
                value={nombre}
                onChange={(evento) => {
                  setNombre(evento.target.value);
                  limpiarError("nombre");
                }}
                aria-invalid={Boolean(errores.nombre)}
                className={inputClase(errores.nombre)}
              />
            </FormField>
            <FormField
              label="Descripción"
              htmlFor="politica-descripcion"
            >
              <textarea
                id="politica-descripcion"
                value={descripcion}
                onChange={(evento) => setDescripcion(evento.target.value)}
                className={textareaClase()}
              />
            </FormField>
          </div>
        </section>

        <section aria-labelledby="ambito-titulo">
          <h2 id="ambito-titulo" className="text-lg font-semibold text-text-900">
            Ámbito y fundamento
          </h2>
          <div className="mt-2 space-y-4">
            <FormField
              label="Tipo de comisión"
              htmlFor="politica-tipo-comision"
              required
            >
              <select
                id="politica-tipo-comision"
                value={tipoComision}
                onChange={(evento) => setTipoComision(evento.target.value)}
                className={inputClase()}
              >
                <option value="">Elija el tipo</option>
                {tiposComision.map((t) => (
                  <option key={t.codigo} value={t.codigo}>
                    {t.etiqueta}
                  </option>
                ))}
              </select>
            </FormField>

            <fieldset>
              <legend className="text-sm font-medium text-text-700">Aplicación</legend>
              <div className="mt-2 space-y-2">
                <label className="flex items-center gap-2 text-sm text-text-700">
                  <input
                    type="checkbox"
                    checked={aplicaApertura}
                    onChange={(e) => setAplicaApertura(e.target.checked)}
                    className={checkboxClase}
                  />
                  Aplica a la apertura de ofertas
                </label>
                <label className="flex items-center gap-2 text-sm text-text-700">
                  <input
                    type="checkbox"
                    checked={aplicaRecomendacion}
                    onChange={(e) => setAplicaRecomendacion(e.target.checked)}
                    className={checkboxClase}
                  />
                  Aplica a la recomendación
                </label>
              </div>
              {errores.aplica && (
                <p className="mt-1 text-sm text-danger-600" role="alert">
                  {errores.aplica}
                </p>
              )}
            </fieldset>

            <FormField
              label="Base normativa"
              htmlFor="politica-base-normativa"
              required
            >
              <select
                id="politica-base-normativa"
                value={baseNormativa}
                onChange={(evento) => {
                  const valor = evento.target.value;
                  setBaseNormativa(valor);
                  if (valor === "LCP_ART14") {
                    setExigeImpar(true);
                    setSuplentePorPrincipal(true);
                    setExigeSecretario(true);
                    setExigeSuplenteSecretario(true);
                    setActoRequerido(true);
                  }
                }}
                className={inputClase()}
              >
                {basesNormativas.map((b) => (
                  <option key={b.codigo} value={b.codigo}>
                    {b.etiqueta}
                  </option>
                ))}
              </select>
            </FormField>

            {esPisoLegal && (
              <p role="note" className="text-sm text-amber-700">
                Piso legal LCP art. 14: el ente puede endurecerlo, no rebajarlo.
              </p>
            )}

            <FormField
              label="Fundamento"
              htmlFor="politica-fundamento"
            >
              <textarea
                id="politica-fundamento"
                value={fundamento}
                onChange={(evento) => setFundamento(evento.target.value)}
                className={textareaClase()}
              />
            </FormField>
          </div>
        </section>

        <section aria-labelledby="vigencia-titulo">
          <h2 id="vigencia-titulo" className="text-lg font-semibold text-text-900">
            Vigencia
          </h2>
          <div className="mt-2 space-y-4">
            <FormField
              label="Desde"
              htmlFor="politica-vigente-desde"
              required
              error={errores.vigente_desde}
            >
              <input
                id="politica-vigente-desde"
                type="date"
                value={vigenteDesde}
                onChange={(evento) => {
                  setVigenteDesde(evento.target.value);
                  limpiarError("vigente_desde");
                  limpiarError("vigente_hasta");
                }}
                aria-invalid={Boolean(errores.vigente_desde)}
                className={inputClase(errores.vigente_desde)}
              />
            </FormField>
            <FormField
              label="Hasta"
              htmlFor="politica-vigente-hasta"
              error={errores.vigente_hasta}
              help="Déjelo vacío si no tiene fecha final."
            >
              <input
                id="politica-vigente-hasta"
                type="date"
                value={vigenteHasta}
                min={vigenteDesde}
                onChange={(evento) => {
                  setVigenteHasta(evento.target.value);
                  limpiarError("vigente_hasta");
                }}
                aria-invalid={Boolean(errores.vigente_hasta)}
                className={inputClase(errores.vigente_hasta)}
              />
            </FormField>
          </div>
        </section>

        <section aria-labelledby="composicion-titulo">
          <h2 id="composicion-titulo" className="text-lg font-semibold text-text-900">
            Composición
          </h2>
          <div className="mt-2 space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <FormField
                label="Mínimo de principales"
                htmlFor="politica-min-principales"
                required
                error={errores.min_principales}
              >
                <input
                  id="politica-min-principales"
                  type="number"
                  min={1}
                  value={minPrincipales}
                  onChange={(evento) => {
                    setMinPrincipales(Number(evento.target.value));
                    limpiarError("min_principales");
                  }}
                  aria-invalid={Boolean(errores.min_principales)}
                  className={inputClase(errores.min_principales)}
                />
              </FormField>
              <FormField
                label="Máximo de principales"
                htmlFor="politica-max-principales"
                error={errores.max_principales}
              >
                <input
                  id="politica-max-principales"
                  type="number"
                  min={1}
                  value={maxPrincipales ?? ""}
                  onChange={(evento) => {
                    setMaxPrincipales(
                      evento.target.value === "" ? null : Number(evento.target.value),
                    );
                    limpiarError("max_principales");
                  }}
                  aria-invalid={Boolean(errores.max_principales)}
                  className={inputClase(errores.max_principales)}
                />
              </FormField>
            </div>

            <fieldset>
              <legend className="text-sm font-medium text-text-700">Exigencias</legend>
              <div className="mt-2 space-y-2">
                <label className="flex items-center gap-2 text-sm text-text-700">
                  <input
                    type="checkbox"
                    checked={exigeImpar}
                    disabled={esPisoLegal}
                    onChange={(e) => setExigeImpar(e.target.checked)}
                    className={checkboxClase}
                  />
                  Número impar
                </label>
                <label className="flex items-center gap-2 text-sm text-text-700">
                  <input
                    type="checkbox"
                    checked={suplentePorPrincipal}
                    disabled={esPisoLegal}
                    onChange={(e) => setSuplentePorPrincipal(e.target.checked)}
                    className={checkboxClase}
                  />
                  Suplente por principal
                </label>
                <label className="flex items-center gap-2 text-sm text-text-700">
                  <input
                    type="checkbox"
                    checked={exigeSecretario}
                    disabled={esPisoLegal}
                    onChange={(e) => setExigeSecretario(e.target.checked)}
                    className={checkboxClase}
                  />
                  Secretario
                </label>
                <label className="flex items-center gap-2 text-sm text-text-700">
                  <input
                    type="checkbox"
                    checked={exigeSuplenteSecretario}
                    disabled={esPisoLegal}
                    onChange={(e) => setExigeSuplenteSecretario(e.target.checked)}
                    className={checkboxClase}
                  />
                  Suplente del secretario
                </label>
                <label className="flex items-center gap-2 text-sm text-text-700">
                  <input
                    type="checkbox"
                    checked={exigePresidente}
                    onChange={(e) => {
                      setExigePresidente(e.target.checked);
                      if (!e.target.checked) {
                        setPresidenteDirimente(false);
                      }
                    }}
                    className={checkboxClase}
                  />
                  Exige presidente
                </label>
              </div>
            </fieldset>
          </div>
        </section>

        <section aria-labelledby="requisitos-titulo">
          <h2 id="requisitos-titulo" className="text-lg font-semibold text-text-900">
            Requisitos de integración
          </h2>
          {errores.requisitos && (
            <p role="alert" className="mt-2 text-sm text-danger-600">
              {errores.requisitos}
            </p>
          )}
          <div className="mt-2 space-y-4">
            {requisitos.map((requisito, indice) => (
              <fieldset
                key={indice}
                className="rounded-md border border-border-default p-3"
              >
                <legend className="px-1 text-sm font-medium text-text-700">
                  Requisito {indice + 1}
                </legend>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <FormField
                    label="Etiqueta"
                    htmlFor={`requisito-etiqueta-${indice}`}
                    required
                  >
                    <input
                      id={`requisito-etiqueta-${indice}`}
                      type="text"
                      value={requisito.etiqueta}
                      onChange={(evento) => {
                        const nuevos = [...requisitos];
                        nuevos[indice] = {
                          ...nuevos[indice],
                          etiqueta: evento.target.value,
                        };
                        setRequisitos(nuevos);
                        limpiarError("requisitos");
                      }}
                      className={inputClase()}
                    />
                  </FormField>
                  <FormField
                    label="Función"
                    htmlFor={`requisito-funcion-${indice}`}
                  >
                    <select
                      id={`requisito-funcion-${indice}`}
                      value={requisito.funcion}
                      onChange={(evento) => {
                        const nuevos = [...requisitos];
                        nuevos[indice] = {
                          ...nuevos[indice],
                          funcion: evento.target.value,
                        };
                        setRequisitos(nuevos);
                      }}
                      className={inputClase()}
                    >
                      <option value="">Sin función</option>
                      {funciones.map((f) => (
                        <option key={f.codigo} value={f.codigo}>
                          {f.etiqueta}
                        </option>
                      ))}
                    </select>
                  </FormField>
                  <FormField
                    label="Condición del miembro"
                    htmlFor={`requisito-condicion-${indice}`}
                  >
                    <select
                      id={`requisito-condicion-${indice}`}
                      value={requisito.condicion}
                      onChange={(evento) => {
                        const nuevos = [...requisitos];
                        nuevos[indice] = {
                          ...nuevos[indice],
                          condicion: evento.target.value,
                        };
                        setRequisitos(nuevos);
                      }}
                      className={inputClase()}
                    >
                      <option value="">Sin condición</option>
                      {condiciones.map((c) => (
                        <option key={c.codigo} value={c.codigo}>
                          {c.etiqueta}
                        </option>
                      ))}
                    </select>
                  </FormField>
                  <FormField
                    label="Tipo de requisito"
                    htmlFor={`requisito-tipo-${indice}`}
                    required
                  >
                    <select
                      id={`requisito-tipo-${indice}`}
                      value={requisito.tipo}
                      onChange={(evento) => {
                        cambiarTipoRequisito(indice, evento.target.value);
                        limpiarError("requisitos");
                      }}
                      className={inputClase()}
                    >
                      <option value="">Elija el tipo</option>
                      {tiposRequisito.map((t) => (
                        <option key={t.codigo} value={t.codigo}>
                          {t.etiqueta}
                        </option>
                      ))}
                    </select>
                  </FormField>

                  {requisito.tipo === "AREA" && (
                    <FormField
                      label="Área"
                      htmlFor={`requisito-area-${indice}`}
                      required
                    >
                      <select
                        id={`requisito-area-${indice}`}
                        value={requisito.area ?? ""}
                        onChange={(evento) => {
                          const nuevos = [...requisitos];
                          nuevos[indice] = {
                            ...nuevos[indice],
                            area: evento.target.value || null,
                          };
                          setRequisitos(nuevos);
                          limpiarError("requisitos");
                        }}
                        className={inputClase()}
                      >
                        <option value="">Elija el área</option>
                        {areas.map((a) => (
                          <option key={a.codigo} value={a.codigo}>
                            {a.etiqueta}
                          </option>
                        ))}
                      </select>
                    </FormField>
                  )}

                  {requisito.tipo === "CARGO" && (
                    <FormField
                      label="Cargo"
                      htmlFor={`requisito-cargo-${indice}`}
                      required
                    >
                      <select
                        id={`requisito-cargo-${indice}`}
                        value={requisito.position_id ?? ""}
                        onChange={(evento) => {
                          const nuevos = [...requisitos];
                          nuevos[indice] = {
                            ...nuevos[indice],
                            position_id: evento.target.value || null,
                          };
                          setRequisitos(nuevos);
                          limpiarError("requisitos");
                        }}
                        className={inputClase()}
                      >
                        <option value="">Elija el cargo</option>
                        {cargos.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.etiqueta}
                          </option>
                        ))}
                      </select>
                    </FormField>
                  )}

                  {requisito.tipo === "UNIDAD" && (
                    <FormField
                      label="Unidad"
                      htmlFor={`requisito-unidad-${indice}`}
                      required
                    >
                      <select
                        id={`requisito-unidad-${indice}`}
                        value={requisito.unit_id ?? ""}
                        onChange={(evento) => {
                          const nuevos = [...requisitos];
                          nuevos[indice] = {
                            ...nuevos[indice],
                            unit_id: evento.target.value || null,
                          };
                          setRequisitos(nuevos);
                          limpiarError("requisitos");
                        }}
                        className={inputClase()}
                      >
                        <option value="">Elija la unidad</option>
                        {unidades.map((u) => (
                          <option key={u.id} value={u.id}>
                            {u.etiqueta}
                          </option>
                        ))}
                      </select>
                    </FormField>
                  )}

                  {requisito.tipo === "COMPETENCIA" && (
                    <>
                      <FormField
                        label="Acción de competencia"
                        htmlFor={`requisito-competencia-accion-${indice}`}
                        required
                      >
                        <select
                          id={`requisito-competencia-accion-${indice}`}
                          value={requisito.competencia_accion ?? ""}
                          onChange={(evento) => {
                            const nuevos = [...requisitos];
                            nuevos[indice] = {
                              ...nuevos[indice],
                              competencia_accion: evento.target.value || null,
                            };
                            setRequisitos(nuevos);
                            limpiarError("requisitos");
                          }}
                          className={inputClase()}
                        >
                          <option value="">Elija la acción</option>
                          {accionesCompetencia.map((a) => (
                            <option key={a.codigo} value={a.codigo}>
                              {a.etiqueta}
                            </option>
                          ))}
                        </select>
                      </FormField>
                      <FormField
                        label="Materia de competencia"
                        htmlFor={`requisito-competencia-materia-${indice}`}
                        required
                      >
                        <select
                          id={`requisito-competencia-materia-${indice}`}
                          value={requisito.competencia_materia ?? ""}
                          onChange={(evento) => {
                            const nuevos = [...requisitos];
                            nuevos[indice] = {
                              ...nuevos[indice],
                              competencia_materia: evento.target.value || null,
                            };
                            setRequisitos(nuevos);
                            limpiarError("requisitos");
                          }}
                          className={inputClase()}
                        >
                          <option value="">Elija la materia</option>
                          {materiasCompetencia.map((m) => (
                            <option key={m.codigo} value={m.codigo}>
                              {m.etiqueta}
                            </option>
                          ))}
                        </select>
                      </FormField>
                    </>
                  )}

                  {requisito.tipo === "FUNCIONARIO" && (
                    <FormField
                      label="Funcionario"
                      htmlFor={`requisito-funcionario-${indice}`}
                      required
                    >
                      <select
                        id={`requisito-funcionario-${indice}`}
                        value={requisito.official_id ?? ""}
                        onChange={(evento) => {
                          const nuevos = [...requisitos];
                          nuevos[indice] = {
                            ...nuevos[indice],
                            official_id: evento.target.value || null,
                          };
                          setRequisitos(nuevos);
                          limpiarError("requisitos");
                        }}
                        className={inputClase()}
                      >
                        <option value="">Elija el funcionario</option>
                        {funcionarios.map((f) => (
                          <option key={f.id} value={f.id}>
                            {f.etiqueta}
                          </option>
                        ))}
                      </select>
                    </FormField>
                  )}

                  <div className="grid grid-cols-2 gap-3">
                    <FormField
                      label="Mínimo"
                      htmlFor={`requisito-minimo-${indice}`}
                      required
                    >
                      <input
                        id={`requisito-minimo-${indice}`}
                        type="number"
                        min={1}
                        value={requisito.minimo}
                        onChange={(evento) => {
                          const nuevos = [...requisitos];
                          nuevos[indice] = {
                            ...nuevos[indice],
                            minimo: Number(evento.target.value),
                          };
                          setRequisitos(nuevos);
                        }}
                        className={inputClase()}
                      />
                    </FormField>
                    <FormField
                      label="Máximo que cumplen"
                      htmlFor={`requisito-maximo-${indice}`}
                    >
                      <input
                        id={`requisito-maximo-${indice}`}
                        type="number"
                        min={1}
                        value={requisito.maximo ?? ""}
                        onChange={(evento) => {
                          const nuevos = [...requisitos];
                          nuevos[indice] = {
                            ...nuevos[indice],
                            maximo:
                              evento.target.value === ""
                                ? null
                                : Number(evento.target.value),
                          };
                          setRequisitos(nuevos);
                        }}
                        className={inputClase()}
                      />
                    </FormField>
                  </div>
                </div>
                <div className="mt-3 flex justify-end">
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setRequisitos((previos) =>
                        previos.filter((_, i) => i !== indice),
                      );
                      limpiarError("requisitos");
                    }}
                  >
                    Quitar requisito
                  </Button>
                </div>
              </fieldset>
            ))}
            <Button
              variant="secondary"
              onClick={() => {
                setRequisitos((previos) => [...previos, { ...REQUISITO_VACIO }]);
                limpiarError("requisitos");
              }}
            >
              Añadir requisito
            </Button>
          </div>
        </section>

        <section aria-labelledby="quorum-titulo">
          <h2 id="quorum-titulo" className="text-lg font-semibold text-text-900">
            Quórum
          </h2>
          {errores.quorum && (
            <p role="alert" className="mt-2 text-sm text-danger-600">
              {errores.quorum}
            </p>
          )}
          <div className="mt-2 space-y-4">
            <FormField
              label="Tipo de quórum"
              htmlFor="politica-quorum-tipo"
              required
            >
              <select
                id="politica-quorum-tipo"
                value={quorumTipo}
                onChange={(evento) => {
                  setQuorumTipo(evento.target.value);
                  limpiarError("quorum");
                }}
                className={inputClase()}
              >
                <option value="">Elija el tipo</option>
                {tiposMayoria.map((t) => (
                  <option key={t.codigo} value={t.codigo}>
                    {t.etiqueta}
                  </option>
                ))}
              </select>
            </FormField>
            {quorumTipo === "ABSOLUTE_COUNT" && (
              <FormField
                label="Cantidad del quórum"
                htmlFor="politica-quorum-cantidad"
                required
              >
                <input
                  id="politica-quorum-cantidad"
                  type="number"
                  min={1}
                  value={quorumCantidad ?? ""}
                  onChange={(evento) => {
                    setQuorumCantidad(
                      evento.target.value === "" ? null : Number(evento.target.value),
                    );
                    limpiarError("quorum");
                  }}
                  className={inputClase()}
                />
              </FormField>
            )}
            {quorumTipo === "QUALIFIED_MAJORITY" && (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <FormField
                  label="Numerador del quórum"
                  htmlFor="politica-quorum-numerador"
                  required
                  help="Fracción mayor que la mitad, p. ej. 2/3."
                >
                  <input
                    id="politica-quorum-numerador"
                    type="number"
                    min={1}
                    value={quorumNumerador ?? ""}
                    onChange={(evento) => {
                      setQuorumNumerador(
                        evento.target.value === "" ? null : Number(evento.target.value),
                      );
                      limpiarError("quorum");
                    }}
                    className={inputClase()}
                  />
                </FormField>
                <FormField
                  label="Denominador del quórum"
                  htmlFor="politica-quorum-denominador"
                  required
                >
                  <input
                    id="politica-quorum-denominador"
                    type="number"
                    min={1}
                    value={quorumDenominador ?? ""}
                    onChange={(evento) => {
                      setQuorumDenominador(
                        evento.target.value === "" ? null : Number(evento.target.value),
                      );
                      limpiarError("quorum");
                    }}
                    className={inputClase()}
                  />
                </FormField>
              </div>
            )}
          </div>
        </section>

        <section aria-labelledby="decision-titulo">
          <h2 id="decision-titulo" className="text-lg font-semibold text-text-900">
            Decisión
          </h2>
          {errores.decision && (
            <p role="alert" className="mt-2 text-sm text-danger-600">
              {errores.decision}
            </p>
          )}
          <div className="mt-2 space-y-4">
            <FormField
              label="Tipo de mayoría"
              htmlFor="politica-decision-tipo"
              required
            >
              <select
                id="politica-decision-tipo"
                value={decisionTipo}
                onChange={(evento) => {
                  setDecisionTipo(evento.target.value);
                  limpiarError("decision");
                }}
                className={inputClase()}
              >
                <option value="">Elija el tipo</option>
                {tiposMayoria.map((t) => (
                  <option key={t.codigo} value={t.codigo}>
                    {t.etiqueta}
                  </option>
                ))}
              </select>
            </FormField>
            {decisionTipo === "ABSOLUTE_COUNT" && (
              <FormField
                label="Cantidad de la decisión"
                htmlFor="politica-decision-cantidad"
                required
              >
                <input
                  id="politica-decision-cantidad"
                  type="number"
                  min={1}
                  value={decisionCantidad ?? ""}
                  onChange={(evento) => {
                    setDecisionCantidad(
                      evento.target.value === "" ? null : Number(evento.target.value),
                    );
                    limpiarError("decision");
                  }}
                  className={inputClase()}
                />
              </FormField>
            )}
            {decisionTipo === "QUALIFIED_MAJORITY" && (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <FormField
                  label="Numerador de la decisión"
                  htmlFor="politica-decision-numerador"
                  required
                  help="Fracción mayor que la mitad, p. ej. 2/3."
                >
                  <input
                    id="politica-decision-numerador"
                    type="number"
                    min={1}
                    value={decisionNumerador ?? ""}
                    onChange={(evento) => {
                      setDecisionNumerador(
                        evento.target.value === "" ? null : Number(evento.target.value),
                      );
                      limpiarError("decision");
                    }}
                    className={inputClase()}
                  />
                </FormField>
                <FormField
                  label="Denominador de la decisión"
                  htmlFor="politica-decision-denominador"
                  required
                >
                  <input
                    id="politica-decision-denominador"
                    type="number"
                    min={1}
                    value={decisionDenominador ?? ""}
                    onChange={(evento) => {
                      setDecisionDenominador(
                        evento.target.value === "" ? null : Number(evento.target.value),
                      );
                      limpiarError("decision");
                    }}
                    className={inputClase()}
                  />
                </FormField>
              </div>
            )}
            <FormField
              label="Base de la decisión"
              htmlFor="politica-decision-base"
              required
            >
              <select
                id="politica-decision-base"
                value={decisionBase}
                onChange={(evento) => {
                  setDecisionBase(evento.target.value);
                  limpiarError("decision");
                }}
                className={inputClase()}
              >
                <option value="">Elija la base</option>
                {basesDecision.map((b) => (
                  <option key={b.codigo} value={b.codigo}>
                    {b.etiqueta}
                  </option>
                ))}
              </select>
            </FormField>
            <fieldset>
              <legend className="text-sm font-medium text-text-700">
                Participación del presidente
              </legend>
              <div className="mt-2 space-y-2">
                <label className="flex items-center gap-2 text-sm text-text-700">
                  <input
                    type="checkbox"
                    checked={presidenteVota}
                    onChange={(e) => setPresidenteVota(e.target.checked)}
                    className={checkboxClase}
                  />
                  El presidente vota
                </label>
                <label className="flex items-center gap-2 text-sm text-text-700">
                  <input
                    type="checkbox"
                    checked={presidenteDirimente}
                    disabled={!exigePresidente}
                    onChange={(e) => setPresidenteDirimente(e.target.checked)}
                    className={checkboxClase}
                  />
                  Voto dirimente del presidente
                </label>
              </div>
            </fieldset>
          </div>
        </section>

        <section aria-labelledby="documentos-titulo">
          <h2 id="documentos-titulo" className="text-lg font-semibold text-text-900">
            Documentos exigidos
          </h2>
          {errores.documentos && (
            <p role="alert" className="mt-2 text-sm text-danger-600">
              {errores.documentos}
            </p>
          )}
          <div className="mt-2 space-y-4">
            {documentos.map((documento, indice) => (
              <fieldset
                key={indice}
                className="rounded-md border border-border-default p-3"
              >
                <legend className="px-1 text-sm font-medium text-text-700">
                  Documento {indice + 1}
                </legend>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <FormField
                    label="Tipo documental"
                    htmlFor={`documento-tipo-${indice}`}
                    required
                  >
                    <select
                      id={`documento-tipo-${indice}`}
                      value={documento.document_type_id}
                      onChange={(evento) => {
                        const nuevos = [...documentos];
                        nuevos[indice] = {
                          ...nuevos[indice],
                          document_type_id: evento.target.value,
                        };
                        setDocumentos(nuevos);
                        limpiarError("documentos");
                      }}
                      className={inputClase()}
                    >
                      <option value="">Elija el tipo</option>
                      {tiposDocumentales.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.etiqueta}
                        </option>
                      ))}
                    </select>
                  </FormField>
                  <FormField
                    label="Etapa"
                    htmlFor={`documento-etapa-${indice}`}
                  >
                    <select
                      id={`documento-etapa-${indice}`}
                      value={documento.etapa}
                      onChange={(evento) => {
                        const nuevos = [...documentos];
                        nuevos[indice] = {
                          ...nuevos[indice],
                          etapa: evento.target.value,
                        };
                        setDocumentos(nuevos);
                      }}
                      className={inputClase()}
                    >
                      <option value="">Sin etapa</option>
                      {etapas.map((e) => (
                        <option key={e.codigo} value={e.codigo}>
                          {e.etiqueta}
                        </option>
                      ))}
                    </select>
                  </FormField>
                  <label className="flex items-center gap-2 text-sm text-text-700">
                    <input
                      type="checkbox"
                      checked={documento.obligatorio}
                      onChange={(evento) => {
                        const nuevos = [...documentos];
                        nuevos[indice] = {
                          ...nuevos[indice],
                          obligatorio: evento.target.checked,
                        };
                        setDocumentos(nuevos);
                      }}
                      className={checkboxClase}
                    />
                    Obligatorio
                  </label>
                  <FormField
                    label="Condición del documento"
                    htmlFor={`documento-condicion-${indice}`}
                  >
                    <input
                      id={`documento-condicion-${indice}`}
                      type="text"
                      value={documento.condicion ?? ""}
                      onChange={(evento) => {
                        const nuevos = [...documentos];
                        nuevos[indice] = {
                          ...nuevos[indice],
                          condicion:
                            evento.target.value.trim() === ""
                              ? null
                              : evento.target.value,
                        };
                        setDocumentos(nuevos);
                      }}
                      className={inputClase()}
                    />
                  </FormField>
                </div>
                <div className="mt-3 flex justify-end">
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setDocumentos((previos) =>
                        previos.filter((_, i) => i !== indice),
                      );
                      limpiarError("documentos");
                    }}
                  >
                    Quitar documento
                  </Button>
                </div>
              </fieldset>
            ))}
            <Button
              variant="secondary"
              onClick={() => {
                setDocumentos((previos) => [...previos, { ...DOCUMENTO_VACIO }]);
                limpiarError("documentos");
              }}
            >
              Añadir documento
            </Button>
          </div>
        </section>

        <section aria-labelledby="acto-titulo">
          <h2 id="acto-titulo" className="text-lg font-semibold text-text-900">
            Acto
          </h2>
          <div className="mt-2 space-y-4">
            <label className="flex items-center gap-2 text-sm text-text-700">
              <input
                type="checkbox"
                checked={actoRequerido}
                disabled={esPisoLegal}
                onChange={(e) => setActoRequerido(e.target.checked)}
                className={checkboxClase}
              />
              Acto requerido
            </label>
            <FormField
              label="Medio del acto"
              htmlFor="politica-acto-medio"
            >
              <select
                id="politica-acto-medio"
                value={actoMedio}
                onChange={(evento) => setActoMedio(evento.target.value)}
                className={inputClase()}
              >
                <option value="">Sin medio</option>
                {medios.map((m) => (
                  <option key={m.codigo} value={m.codigo}>
                    {m.etiqueta}
                  </option>
                ))}
              </select>
            </FormField>
          </div>
        </section>

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
            onClick={() =>
              navigate(esEdicion && detalle.data ? `${RUTA_POLITICAS}/${detalle.data.id}` : RUTA_POLITICAS)
            }
          >
            Cancelar
          </Button>
        </div>
      </form>
    </PageContent>
  );
}
