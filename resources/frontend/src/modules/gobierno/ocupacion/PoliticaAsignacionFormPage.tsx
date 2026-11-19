import { useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router";
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
  CONSULTA_POLITICAS_ASIGNACION,
  RUTA_POLITICAS_ASIGNACION,
  type CompetenciaPermitida,
  type PoliticaAsignacionCatalogo,
  type PoliticaAsignacionDetalle,
  type PoliticaAsignacionEntrada,
  type PoliticaAsignacionOpciones,
} from "@/modules/gobierno/ocupacion/politicasAsignacion";

type ErroresFormulario = Partial<Record<
  | "codigo"
  | "nombre"
  | "descripcion"
  | "figura"
  | "fundamento"
  | "vigente_desde"
  | "vigente_hasta"
  | "max_dias"
  | "acto_medio"
  | "emisor_tipo"
  | "emisor_position_id"
  | "emisor_competencia_accion"
  | "emisor_competencia_materia"
  | "autorizacion_requerida"
  | "autorizacion_etiqueta"
  | "autorizacion_ambito"
  | "autorizacion_mas_de_dias"
  | "prohibe_avocacion"
  | "competencias"
  | "documentos"
  | "general",
  string
>>;

type FilaCompetencia = { accion: string; materia: string };
type FilaDocumento = { document_type_id: string; etapa: "ACTIVACION" | "REVOCACION"; obligatorio: boolean };

export function PoliticaAsignacionFormPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const { politicaId } = useParams();

  const esEdicion = Boolean(politicaId);
  const puedeConfigurar = tiene("gobierno_ocupacion:configure", "empresa");

  const [codigo, setCodigo] = useState("");
  const [nombre, setNombre] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [figura, setFigura] = useState("");
  const [fundamento, setFundamento] = useState("");
  const [vigenteDesde, setVigenteDesde] = useState("");
  const [vigenteHasta, setVigenteHasta] = useState("");
  const [exigeFin, setExigeFin] = useState(false);
  const [maxDias, setMaxDias] = useState("");
  const [actoMedio, setActoMedio] = useState("");
  const [emisorTipo, setEmisorTipo] = useState<"CUALQUIERA" | "CARGO" | "COMPETENCIA">("CUALQUIERA");
  const [emisorPositionId, setEmisorPositionId] = useState("");
  const [emisorCompetenciaAccion, setEmisorCompetenciaAccion] = useState("");
  const [emisorCompetenciaMateria, setEmisorCompetenciaMateria] = useState("");
  const [prohibeAvocacion, setProhibeAvocacion] = useState(false);
  const [autorizacionRequerida, setAutorizacionRequerida] = useState(false);
  const [autorizacionEtiqueta, setAutorizacionEtiqueta] = useState("");
  const [autorizacionAmbito, setAutorizacionAmbito] = useState<"TODAS" | "MAXIMA_AUTORIDAD" | "">("");
  const [autorizacionDias, setAutorizacionDias] = useState("");
  const [competencias, setCompetencias] = useState<FilaCompetencia[]>([]);
  const [documentos, setDocumentos] = useState<FilaDocumento[]>([]);
  const [errores, setErrores] = useState<ErroresFormulario>({});
  const enviandoRef = useRef(false);
  const [detalleCargado, setDetalleCargado] = useState(false);
  const [detalleNoEditable, setDetalleNoEditable] = useState(false);

  const catalogo = useQuery({
    queryKey: [...CONSULTA_POLITICAS_ASIGNACION, "catalogo", activeCompanyId],
    queryFn: () => apiFetch<PoliticaAsignacionCatalogo>(`${RUTA_POLITICAS_ASIGNACION}/catalogo`),
    enabled: puedeConfigurar && Boolean(activeCompanyId),
    retry: false,
  });

  const opciones = useQuery({
    queryKey: [...CONSULTA_POLITICAS_ASIGNACION, "opciones", activeCompanyId],
    queryFn: () => apiFetch<PoliticaAsignacionOpciones>(`${RUTA_POLITICAS_ASIGNACION}/opciones`),
    enabled: puedeConfigurar && Boolean(activeCompanyId),
    retry: false,
  });

  const detalle = useQuery({
    queryKey: [...CONSULTA_POLITICAS_ASIGNACION, "politica-detalle", activeCompanyId, politicaId],
    queryFn: () => apiFetch<PoliticaAsignacionDetalle>(`${RUTA_POLITICAS_ASIGNACION}/${politicaId}`),
    enabled: puedeConfigurar && esEdicion && Boolean(activeCompanyId),
    retry: false,
  });

  const figurasCatalogo = useMemo(() => catalogo.data?.figuras ?? [], [catalogo.data]);
  const mediosCatalogo = useMemo(() => catalogo.data?.medios ?? [], [catalogo.data]);
  const emisorTiposCatalogo = useMemo(() => catalogo.data?.emisor_tipos ?? [], [catalogo.data]);
  const ambitosCatalogo = useMemo(() => catalogo.data?.ambitos ?? [], [catalogo.data]);
  const etapasCatalogo = useMemo(() => catalogo.data?.etapas ?? [], [catalogo.data]);
  const accionesCatalogo = useMemo(() => catalogo.data?.acciones ?? [], [catalogo.data]);
  const materiasCatalogo = useMemo(() => catalogo.data?.materias ?? [], [catalogo.data]);
  const cargosOpciones = useMemo(() => opciones.data?.cargos ?? [], [opciones.data]);
  const tiposDocumentales = useMemo(() => opciones.data?.tipos_documentales ?? [], [opciones.data]);
  const pisos = useMemo(() => opciones.data?.pisos ?? [], [opciones.data]);

  const pisosLegales = useMemo(() => {
    if (!figura) return null;
    return pisos.filter((piso) => piso.figuras.includes(figura));
  }, [pisos, figura]);

  const limpiarError = (campo: keyof ErroresFormulario): void => {
    setErrores((previos) => {
      if (!(campo in previos)) return previos;
      const siguientes = { ...previos };
      delete siguientes[campo];
      return siguientes;
    });
  };

  const rellenarDesdeDetalle = (d: PoliticaAsignacionDetalle): void => {
    setCodigo(d.codigo);
    setNombre(d.nombre);
    setDescripcion(d.descripcion ?? "");
    setFigura(d.figura);
    setFundamento(d.fundamento ?? "");
    setVigenteDesde(d.vigente_desde);
    setVigenteHasta(d.vigente_hasta ?? "");
    setExigeFin(d.exige_fin);
    setMaxDias(d.max_dias === null ? "" : String(d.max_dias));
    setActoMedio(d.acto_medio ?? "");
    setEmisorTipo(d.emisor_tipo);
    setEmisorPositionId(d.emisor_position_id ?? "");
    setEmisorCompetenciaAccion(d.emisor_competencia_accion ?? "");
    setEmisorCompetenciaMateria(d.emisor_competencia_materia ?? "");
    setProhibeAvocacion(d.prohibe_avocacion);
    setAutorizacionRequerida(d.autorizacion_requerida);
    setAutorizacionEtiqueta(d.autorizacion_etiqueta ?? "");
    setAutorizacionAmbito(d.autorizacion_ambito ?? "");
    setAutorizacionDias(d.autorizacion_mas_de_dias === null ? "" : String(d.autorizacion_mas_de_dias));
    setCompetencias(d.competencias.map((c) => ({ accion: c.accion, materia: c.materia })));
    setDocumentos(
      d.documentos.map((doc) => ({
        document_type_id: doc.document_type_id,
        etapa: doc.etapa,
        obligatorio: doc.obligatorio,
      })),
    );
    setDetalleCargado(true);
  };

  useMemo(() => {
    if (esEdicion && detalle.data && !detalleCargado) {
      if (detalle.data.estado !== "BORRADOR") {
        setDetalleNoEditable(true);
      } else {
        rellenarDesdeDetalle(detalle.data);
      }
    }
  }, [esEdicion, detalle.data, detalleCargado]);

  const validar = (): ErroresFormulario => {
    const siguientes: ErroresFormulario = {};

    if (!codigo.trim()) {
      siguientes.codigo = "Indique el código.";
    } else if (codigo.trim().length < 1 || codigo.trim().length > 20) {
      siguientes.codigo = "El código debe tener entre 1 y 20 caracteres.";
    }

    if (!nombre.trim()) {
      siguientes.nombre = "Indique el nombre.";
    }

    if (!figura) {
      siguientes.figura = "Elija la figura.";
    }

    if (!vigenteDesde) {
      siguientes.vigente_desde = "Indique la fecha de inicio.";
    }

    if (vigenteHasta && vigenteDesde && vigenteHasta < vigenteDesde) {
      siguientes.vigente_hasta = "La fecha de fin no puede ser anterior a la de inicio.";
    }

    if (maxDias.trim() !== "") {
      const numero = Number(maxDias);
      if (!Number.isInteger(numero) || numero < 1) {
        siguientes.max_dias = "Indique un número entero mayor o igual a 1.";
      }
    }

    if (emisorTipo === "CARGO" && !emisorPositionId) {
      siguientes.emisor_position_id = "Elija el cargo emisor.";
    }

    if (emisorTipo === "COMPETENCIA") {
      if (!emisorCompetenciaAccion) {
        siguientes.emisor_competencia_accion = "Elija la acción del emisor.";
      }
      if (!emisorCompetenciaMateria) {
        siguientes.emisor_competencia_materia = "Elija la materia del emisor.";
      }
    }

    if (autorizacionRequerida) {
      const etiquetaRecortada = autorizacionEtiqueta.trim();
      if (etiquetaRecortada.length < 5 || etiquetaRecortada.length > 120) {
        siguientes.autorizacion_etiqueta = "La autorización debe tener entre 5 y 120 caracteres.";
      }
      if (!autorizacionAmbito) {
        siguientes.autorizacion_ambito = "Elija el ámbito de la autorización.";
      }
      if (autorizacionDias.trim() !== "") {
        const numero = Number(autorizacionDias);
        if (!Number.isInteger(numero) || numero < 0) {
          siguientes.autorizacion_mas_de_dias = "Indique un número entero mayor o igual a 0.";
        }
      }
    }

    return siguientes;
  };

  const enviar = async (): Promise<void> => {
    if (!puedeConfigurar || enviandoRef.current) return;

    const erroresLocales = validar();
    setErrores(erroresLocales);
    if (Object.keys(erroresLocales).length > 0) return;

    const vacioANulo = (valor: string): string | null => (valor.trim() === "" ? null : valor.trim());
    const numeroANulo = (valor: string): number | null => {
      if (valor.trim() === "") return null;
      const numero = Number(valor);
      return Number.isNaN(numero) ? null : numero;
    };

    const cuerpo: PoliticaAsignacionEntrada = {
      codigo: codigo.trim(),
      nombre: nombre.trim(),
      descripcion: vacioANulo(descripcion),
      figura,
      fundamento: vacioANulo(fundamento),
      act_id: null,
      vigente_desde: vigenteDesde,
      vigente_hasta: vacioANulo(vigenteHasta),
      exige_fin: exigeFin,
      max_dias: numeroANulo(maxDias),
      acto_medio: vacioANulo(actoMedio),
      emisor_tipo: emisorTipo,
      emisor_position_id: emisorTipo === "CARGO" ? vacioANulo(emisorPositionId) : null,
      emisor_competencia_accion: emisorTipo === "COMPETENCIA" ? vacioANulo(emisorCompetenciaAccion) : null,
      emisor_competencia_materia: emisorTipo === "COMPETENCIA" ? vacioANulo(emisorCompetenciaMateria) : null,
      autorizacion_requerida: autorizacionRequerida,
      autorizacion_etiqueta: autorizacionRequerida ? vacioANulo(autorizacionEtiqueta) : null,
      autorizacion_ambito: autorizacionRequerida && autorizacionAmbito ? autorizacionAmbito : null,
      autorizacion_mas_de_dias: autorizacionRequerida ? numeroANulo(autorizacionDias) : null,
      prohibe_avocacion: prohibeAvocacion,
      competencias: competencias.map((c): CompetenciaPermitida => ({
        accion: c.accion,
        materia: c.materia,
      })),
      documentos: documentos.map((doc) => ({
        document_type_id: doc.document_type_id,
        etapa: doc.etapa,
        obligatorio: doc.obligatorio,
      })),
    };

    enviandoRef.current = true;
    try {
      if (esEdicion && detalle.data) {
        const actualizada = await apiFetch<PoliticaAsignacionDetalle>(
          `${RUTA_POLITICAS_ASIGNACION}/${detalle.data.id}`,
          {
            method: "PUT",
            body: cuerpo,
            ifMatch: String(detalle.data.version),
          },
        );
        notify({ type: "success", title: "Política guardada en borrador." });
        await queryClient.invalidateQueries({ queryKey: [...CONSULTA_POLITICAS_ASIGNACION] });
        navigate(`${RUTA_POLITICAS_ASIGNACION}/${actualizada.id}`);
      } else {
        const creada = await apiFetch<PoliticaAsignacionDetalle>(RUTA_POLITICAS_ASIGNACION, {
          method: "POST",
          body: cuerpo,
        });
        notify({ type: "success", title: "Política guardada en borrador." });
        await queryClient.invalidateQueries({ queryKey: [...CONSULTA_POLITICAS_ASIGNACION] });
        navigate(`${RUTA_POLITICAS_ASIGNACION}/${creada.id}`);
      }
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.fieldErrors) {
          const erroresApi: ErroresFormulario = {};
          const generales: string[] = [];
          const mapa: Array<[string, keyof ErroresFormulario]> = [
            ["codigo", "codigo"],
            ["nombre", "nombre"],
            ["descripcion", "descripcion"],
            ["figura", "figura"],
            ["fundamento", "fundamento"],
            ["vigente_desde", "vigente_desde"],
            ["vigente_hasta", "vigente_hasta"],
            ["max_dias", "max_dias"],
            ["acto_medio", "acto_medio"],
            ["emisor_tipo", "emisor_tipo"],
            ["emisor_position_id", "emisor_position_id"],
            ["autorizacion_requerida", "autorizacion_requerida"],
            ["autorizacion_etiqueta", "autorizacion_etiqueta"],
            ["autorizacion_ambito", "autorizacion_ambito"],
            ["prohibe_avocacion", "prohibe_avocacion"],
            ["competencias", "competencias"],
            ["documentos", "documentos"],
          ];
          for (const [backend, local] of mapa) {
            if (error.fieldErrors[backend]?.length) {
              erroresApi[local] = error.fieldErrors[backend][0];
            }
          }
          for (const clave of Object.keys(error.fieldErrors)) {
            if (!mapa.some(([backend]) => backend === clave)) {
              const mensajes = error.fieldErrors[clave];
              if (Array.isArray(mensajes) && mensajes.length > 0) {
                generales.push(`${clave}: ${mensajes[0]}`);
              }
            }
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
          notify({ type: "error", title: "No tiene permiso para configurar políticas de asignación" });
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
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para configurar políticas de asignación."
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
            { label: "Políticas de asignación", to: RUTA_POLITICAS_ASIGNACION },
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
            { label: "Ocupación de cargos", to: "/gobierno/ocupacion" },
            { label: "Políticas de asignación", to: RUTA_POLITICAS_ASIGNACION },
          ]}
          title="Editar política"
        />
        <ErrorDeCarga
          message="No fue posible cargar la política."
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
            { label: "Políticas de asignación", to: RUTA_POLITICAS_ASIGNACION },
          ]}
          title="Editar política"
        />
        <EmptyState
          title="Solo se edita una política en borrador."
          description="Esta política no está en borrador y no puede modificarse."
        />
      </PageContent>
    );
  }

  if (catalogo.isLoading || opciones.isLoading || (esEdicion && !detalleCargado)) {
    return (
      <PageContent>
        <PageHeader
          crumbs={[
            { label: "Gobierno" },
            { label: "Ocupación de cargos", to: "/gobierno/ocupacion" },
            { label: "Políticas de asignación", to: RUTA_POLITICAS_ASIGNACION },
          ]}
          title={esEdicion ? "Editar política" : "Nueva política de asignación"}
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
            { label: "Políticas de asignación", to: RUTA_POLITICAS_ASIGNACION },
          ]}
          title={esEdicion ? "Editar política" : "Nueva política de asignación"}
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
            { label: "Políticas de asignación", to: RUTA_POLITICAS_ASIGNACION },
          ]}
          title={esEdicion ? "Editar política" : "Nueva política de asignación"}
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

  const titular =
    esEdicion && detalle.data
      ? `Editar política ${detalle.data.codigo} v${detalle.data.numero_version}`
      : "Nueva política de asignación";

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno" },
          { label: "Ocupación de cargos", to: "/gobierno/ocupacion" },
          { label: "Políticas de asignación", to: RUTA_POLITICAS_ASIGNACION },
        ]}
        title={titular}
        description="Configure las reglas de asignación del ente. Queda en borrador hasta que otra persona la active."
      />

      <form
        noValidate
        className="mt-4 space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          void enviar();
        }}
      >
        <section className="space-y-4">
          <h2 className="text-sm font-semibold text-text-900">Datos</h2>

          <FormField label="Código" htmlFor="politica-codigo" required error={errores.codigo}>
            <input
              id="politica-codigo"
              value={codigo}
              disabled={esEdicion}
              onChange={(evento) => {
                setCodigo(evento.target.value);
                limpiarError("codigo");
              }}
              aria-invalid={Boolean(errores.codigo)}
              className={selectClase(errores.codigo)}
            />
          </FormField>

          <FormField label="Nombre" htmlFor="politica-nombre" required error={errores.nombre}>
            <input
              id="politica-nombre"
              value={nombre}
              onChange={(evento) => {
                setNombre(evento.target.value);
                limpiarError("nombre");
              }}
              aria-invalid={Boolean(errores.nombre)}
              className={selectClase(errores.nombre)}
            />
          </FormField>

          <FormField label="Descripción" htmlFor="politica-descripcion" error={errores.descripcion}>
            <textarea
              id="politica-descripcion"
              value={descripcion}
              onChange={(evento) => {
                setDescripcion(evento.target.value);
                limpiarError("descripcion");
              }}
              aria-invalid={Boolean(errores.descripcion)}
              className={textareaClase(errores.descripcion)}
            />
          </FormField>

          <FormField label="Figura" htmlFor="politica-figura" required error={errores.figura}>
            <select
              id="politica-figura"
              value={figura}
              onChange={(evento) => {
                setFigura(evento.target.value);
                limpiarError("figura");
              }}
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
          </FormField>

          <FormField
            label="Fundamento"
            htmlFor="politica-fundamento"
            error={errores.fundamento}
            help="Obligatorio para activar la política."
          >
            <textarea
              id="politica-fundamento"
              value={fundamento}
              onChange={(evento) => {
                setFundamento(evento.target.value);
                limpiarError("fundamento");
              }}
              aria-invalid={Boolean(errores.fundamento)}
              className={textareaClase(errores.fundamento)}
            />
          </FormField>

          <FormField label="Vigente desde" htmlFor="politica-desde" required error={errores.vigente_desde}>
            <input
              id="politica-desde"
              type="date"
              value={vigenteDesde}
              onChange={(evento) => {
                setVigenteDesde(evento.target.value);
                limpiarError("vigente_desde");
                limpiarError("vigente_hasta");
              }}
              aria-invalid={Boolean(errores.vigente_desde)}
              className={selectClase(errores.vigente_desde)}
            />
          </FormField>

          <FormField label="Vigente hasta" htmlFor="politica-hasta" error={errores.vigente_hasta}>
            <input
              id="politica-hasta"
              type="date"
              value={vigenteHasta}
              min={vigenteDesde}
              onChange={(evento) => {
                setVigenteHasta(evento.target.value);
                limpiarError("vigente_hasta");
              }}
              aria-invalid={Boolean(errores.vigente_hasta)}
              className={selectClase(errores.vigente_hasta)}
            />
          </FormField>
        </section>

        <section aria-labelledby="pisos-legales-titulo" className="rounded-md border border-border-default bg-surface-0 p-4">
          <h2 id="pisos-legales-titulo" className="text-sm font-semibold text-text-900">
            Pisos legales del régimen del ente
          </h2>
          {pisosLegales === null ? (
            <p className="mt-1 text-sm text-text-700">Elija la figura para ver los pisos legales.</p>
          ) : pisosLegales.length === 0 ? (
            <p className="mt-1 text-sm text-text-700">Ningún piso legal para esta figura en el régimen del ente.</p>
          ) : (
            <ul className="mt-1 list-inside list-disc text-sm text-text-700">
              {pisosLegales.map((piso) => (
                <li key={piso.codigo}>
                  {piso.fuente}
                </li>
              ))}
            </ul>
          )}
          {pisosLegales !== null && pisosLegales.length > 0 && (
            <p className="mt-2 text-sm text-text-500">Se aplican siempre; la política solo puede endurecerlos.</p>
          )}
        </section>

        <section className="space-y-4">
          <h2 className="text-sm font-semibold text-text-900">Reglas</h2>

          <div className="flex flex-col gap-1.5">
            <label className="flex items-center gap-2 text-sm text-text-900">
              <input
                id="politica-exige-fin"
                type="checkbox"
                checked={exigeFin}
                onChange={(evento) => {
                  setExigeFin(evento.target.checked);
                }}
              />
              Exige fecha de fin
            </label>
          </div>

          <FormField label="Máximo de días" htmlFor="politica-max-dias" error={errores.max_dias}>
            <input
              id="politica-max-dias"
              type="number"
              value={maxDias}
              min={1}
              onChange={(evento) => {
                setMaxDias(evento.target.value);
                limpiarError("max_dias");
              }}
              aria-invalid={Boolean(errores.max_dias)}
              className={selectClase(errores.max_dias)}
            />
          </FormField>

          <FormField label="Medio del acto" htmlFor="politica-medio" error={errores.acto_medio}>
            <select
              id="politica-medio"
              value={actoMedio}
              onChange={(evento) => {
                setActoMedio(evento.target.value);
                limpiarError("acto_medio");
              }}
              aria-invalid={Boolean(errores.acto_medio)}
              className={selectClase(errores.acto_medio)}
            >
              <option value="">Sin exigencia propia</option>
              {mediosCatalogo.map((medio) => (
                <option key={medio.codigo} value={medio.codigo}>
                  {medio.etiqueta}
                </option>
              ))}
            </select>
          </FormField>

          <FormField label="Emisor del acto" htmlFor="politica-emisor" error={errores.emisor_tipo}>
            <select
              id="politica-emisor"
              value={emisorTipo}
              onChange={(evento) => {
                setEmisorTipo(evento.target.value as "CUALQUIERA" | "CARGO" | "COMPETENCIA");
                if (evento.target.value !== "CARGO") {
                  setEmisorPositionId("");
                  limpiarError("emisor_position_id");
                }
                if (evento.target.value !== "COMPETENCIA") {
                  setEmisorCompetenciaAccion("");
                  setEmisorCompetenciaMateria("");
                  limpiarError("emisor_competencia_accion");
                  limpiarError("emisor_competencia_materia");
                }
                limpiarError("emisor_tipo");
              }}
              aria-invalid={Boolean(errores.emisor_tipo)}
              className={selectClase(errores.emisor_tipo)}
            >
              {emisorTiposCatalogo.map((tipo) => (
                <option key={tipo.codigo} value={tipo.codigo}>
                  {tipo.etiqueta}
                </option>
              ))}
            </select>
          </FormField>

          {emisorTipo === "CARGO" && (
            <FormField label="Cargo emisor" htmlFor="politica-emisor-cargo" required error={errores.emisor_position_id}>
              <select
                id="politica-emisor-cargo"
                value={emisorPositionId}
                onChange={(evento) => {
                  setEmisorPositionId(evento.target.value);
                  limpiarError("emisor_position_id");
                }}
                aria-invalid={Boolean(errores.emisor_position_id)}
                className={selectClase(errores.emisor_position_id)}
              >
                <option value="">Elija el cargo</option>
                {cargosOpciones.map((cargo) => (
                  <option key={cargo.id} value={cargo.id}>
                    {cargo.etiqueta}
                  </option>
                ))}
              </select>
            </FormField>
          )}

          {emisorTipo === "COMPETENCIA" && (
            <>
              <FormField label="Acción del emisor" htmlFor="politica-emisor-accion" required error={errores.emisor_competencia_accion}>
                <select
                  id="politica-emisor-accion"
                  value={emisorCompetenciaAccion}
                  onChange={(evento) => {
                    setEmisorCompetenciaAccion(evento.target.value);
                    limpiarError("emisor_competencia_accion");
                  }}
                  aria-invalid={Boolean(errores.emisor_competencia_accion)}
                  className={selectClase(errores.emisor_competencia_accion)}
                >
                  <option value="">Elija la acción</option>
                  {accionesCatalogo.map((accion) => (
                    <option key={accion.codigo} value={accion.codigo}>
                      {accion.etiqueta}
                    </option>
                  ))}
                </select>
              </FormField>

              <FormField label="Materia del emisor" htmlFor="politica-emisor-materia" required error={errores.emisor_competencia_materia}>
                <select
                  id="politica-emisor-materia"
                  value={emisorCompetenciaMateria}
                  onChange={(evento) => {
                    setEmisorCompetenciaMateria(evento.target.value);
                    limpiarError("emisor_competencia_materia");
                  }}
                  aria-invalid={Boolean(errores.emisor_competencia_materia)}
                  className={selectClase(errores.emisor_competencia_materia)}
                >
                  <option value="">Elija la materia</option>
                  {materiasCatalogo.map((materia) => (
                    <option key={materia.codigo} value={materia.codigo}>
                      {materia.etiqueta}
                    </option>
                  ))}
                </select>
              </FormField>
            </>
          )}

          <div className="flex flex-col gap-1.5">
            <label className="flex items-center gap-2 text-sm text-text-900">
              <input
                id="politica-prohibe-avocacion"
                type="checkbox"
                checked={prohibeAvocacion}
                onChange={(evento) => {
                  setProhibeAvocacion(evento.target.checked);
                }}
              />
              Prohibir la avocación
            </label>
            {errores.prohibe_avocacion && (
              <p className="text-sm text-danger-600" role="alert">
                {errores.prohibe_avocacion}
              </p>
            )}
          </div>
        </section>

        <section className="space-y-4">
          <h2 className="text-sm font-semibold text-text-900">Autorización especial</h2>

          <div className="flex flex-col gap-1.5">
            <label className="flex items-center gap-2 text-sm text-text-900">
              <input
                id="politica-autorizacion"
                type="checkbox"
                checked={autorizacionRequerida}
                onChange={(evento) => {
                  setAutorizacionRequerida(evento.target.checked);
                  if (!evento.target.checked) {
                    setAutorizacionEtiqueta("");
                    setAutorizacionAmbito("");
                    setAutorizacionDias("");
                    limpiarError("autorizacion_etiqueta");
                    limpiarError("autorizacion_ambito");
                    limpiarError("autorizacion_mas_de_dias");
                  }
                  limpiarError("autorizacion_requerida");
                }}
              />
              Exige autorización especial
            </label>
            {errores.autorizacion_requerida && (
              <p className="text-sm text-danger-600" role="alert">
                {errores.autorizacion_requerida}
              </p>
            )}
          </div>

          {autorizacionRequerida && (
            <>
              <FormField label="Nombre de la autorización" htmlFor="politica-autorizacion-etiqueta" required error={errores.autorizacion_etiqueta}>
                <input
                  id="politica-autorizacion-etiqueta"
                  value={autorizacionEtiqueta}
                  maxLength={120}
                  onChange={(evento) => {
                    setAutorizacionEtiqueta(evento.target.value);
                    limpiarError("autorizacion_etiqueta");
                  }}
                  aria-invalid={Boolean(errores.autorizacion_etiqueta)}
                  className={selectClase(errores.autorizacion_etiqueta)}
                />
              </FormField>

              <FormField label="Ámbito de la autorización" htmlFor="politica-autorizacion-ambito" required error={errores.autorizacion_ambito}>
                <select
                  id="politica-autorizacion-ambito"
                  value={autorizacionAmbito}
                  onChange={(evento) => {
                    setAutorizacionAmbito(evento.target.value as "TODAS" | "MAXIMA_AUTORIDAD" | "");
                    limpiarError("autorizacion_ambito");
                  }}
                  aria-invalid={Boolean(errores.autorizacion_ambito)}
                  className={selectClase(errores.autorizacion_ambito)}
                >
                  <option value="">Elija el ámbito</option>
                  {ambitosCatalogo.map((ambito) => (
                    <option key={ambito.codigo} value={ambito.codigo}>
                      {ambito.etiqueta}
                    </option>
                  ))}
                </select>
              </FormField>

              <FormField label="Exigir con más de (días)" htmlFor="politica-autorizacion-dias" error={errores.autorizacion_mas_de_dias}>
                <input
                  id="politica-autorizacion-dias"
                  type="number"
                  value={autorizacionDias}
                  min={0}
                  onChange={(evento) => {
                    setAutorizacionDias(evento.target.value);
                    limpiarError("autorizacion_mas_de_dias");
                  }}
                  aria-invalid={Boolean(errores.autorizacion_mas_de_dias)}
                  className={selectClase(errores.autorizacion_mas_de_dias)}
                />
              </FormField>
            </>
          )}
        </section>

        <section className="space-y-4">
          <h2 className="text-sm font-semibold text-text-900">Competencias permitidas</h2>
          <p className="text-sm text-text-700">Vacío: todas las competencias del cargo (ORG-03).</p>

          {competencias.map((competencia, indice) => (
            <div key={`competencia-${indice}`} className="rounded-md border border-border-default bg-surface-0 p-3 space-y-3">
              <FormField
                label={`Acción de la competencia ${indice + 1}`}
                htmlFor={`politica-competencia-accion-${indice}`}
              >
                <select
                  id={`politica-competencia-accion-${indice}`}
                  value={competencia.accion}
                  onChange={(evento) => {
                    setCompetencias((previas) =>
                      previas.map((c, i) => (i === indice ? { ...c, accion: evento.target.value } : c)),
                    );
                  }}
                  className={selectClase()}
                >
                  <option value="">Elija la acción</option>
                  {accionesCatalogo.map((accion) => (
                    <option key={accion.codigo} value={accion.codigo}>
                      {accion.etiqueta}
                    </option>
                  ))}
                </select>
              </FormField>

              <FormField
                label={`Materia de la competencia ${indice + 1}`}
                htmlFor={`politica-competencia-materia-${indice}`}
              >
                <select
                  id={`politica-competencia-materia-${indice}`}
                  value={competencia.materia}
                  onChange={(evento) => {
                    setCompetencias((previas) =>
                      previas.map((c, i) => (i === indice ? { ...c, materia: evento.target.value } : c)),
                    );
                  }}
                  className={selectClase()}
                >
                  <option value="">Elija la materia</option>
                  {materiasCatalogo.map((materia) => (
                    <option key={materia.codigo} value={materia.codigo}>
                      {materia.etiqueta}
                    </option>
                  ))}
                </select>
              </FormField>

              <Button
                variant="secondary"
                onClick={() => setCompetencias((previas) => previas.filter((_, i) => i !== indice))}
              >
                {`Quitar competencia ${indice + 1}`}
              </Button>
            </div>
          ))}

          <Button
            variant="secondary"
            onClick={() => setCompetencias((previas) => [...previas, { accion: "", materia: "" }])}
          >
            Añadir competencia
          </Button>
        </section>

        <section className="space-y-4">
          <h2 className="text-sm font-semibold text-text-900">Documentos exigidos</h2>

          {documentos.map((documento, indice) => (
            <div key={`documento-${indice}`} className="rounded-md border border-border-default bg-surface-0 p-3 space-y-3">
              <FormField
                label={`Tipo documental ${indice + 1}`}
                htmlFor={`politica-documento-tipo-${indice}`}
              >
                <select
                  id={`politica-documento-tipo-${indice}`}
                  value={documento.document_type_id}
                  onChange={(evento) => {
                    setDocumentos((previas) =>
                      previas.map((d, i) => (i === indice ? { ...d, document_type_id: evento.target.value } : d)),
                    );
                  }}
                  className={selectClase()}
                >
                  <option value="">Elija el tipo</option>
                  {tiposDocumentales.map((tipo) => (
                    <option key={tipo.id} value={tipo.id}>
                      {tipo.etiqueta}
                    </option>
                  ))}
                </select>
              </FormField>

              <FormField
                label={`Etapa del documento ${indice + 1}`}
                htmlFor={`politica-documento-etapa-${indice}`}
              >
                <select
                  id={`politica-documento-etapa-${indice}`}
                  value={documento.etapa}
                  onChange={(evento) => {
                    setDocumentos((previas) =>
                      previas.map((d, i) =>
                        i === indice ? { ...d, etapa: evento.target.value as "ACTIVACION" | "REVOCACION" } : d,
                      ),
                    );
                  }}
                  className={selectClase()}
                >
                  {etapasCatalogo.map((etapa) => (
                    <option key={etapa.codigo} value={etapa.codigo}>
                      {etapa.etiqueta}
                    </option>
                  ))}
                </select>
              </FormField>

              <label className="flex items-center gap-2 text-sm text-text-900">
                <input
                  type="checkbox"
                  checked={documento.obligatorio}
                  onChange={(evento) => {
                    setDocumentos((previas) =>
                      previas.map((d, i) => (i === indice ? { ...d, obligatorio: evento.target.checked } : d)),
                    );
                  }}
                />
                {`Obligatorio ${indice + 1}`}
              </label>

              <Button
                variant="secondary"
                onClick={() => setDocumentos((previas) => previas.filter((_, i) => i !== indice))}
              >
                {`Quitar documento ${indice + 1}`}
              </Button>
            </div>
          ))}

          <Button
            variant="secondary"
            onClick={() =>
              setDocumentos((previas) => [
                ...previas,
                { document_type_id: "", etapa: "ACTIVACION", obligatorio: true },
              ])
            }
          >
            Añadir documento
          </Button>
        </section>

        {errores.general && (
          <div role="alert" className="rounded-md border border-danger-600 bg-danger-50 p-3 text-sm text-danger-600">
            {errores.general}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2">
          <AsyncButton variant="primary" onClick={enviar}>
            Guardar borrador
          </AsyncButton>
          <Button
            variant="secondary"
            onClick={() => navigate(esEdicion ? `${RUTA_POLITICAS_ASIGNACION}/${politicaId}` : RUTA_POLITICAS_ASIGNACION)}
          >
            Cancelar
          </Button>
        </div>
      </form>
    </PageContent>
  );
}
