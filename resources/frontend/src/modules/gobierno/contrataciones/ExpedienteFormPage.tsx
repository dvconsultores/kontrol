import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";
import { ErrorDeCarga } from "@/modules/gobierno/ocupacion/ErrorDeCarga";
import {
  CONSULTA_EXPEDIENTES,
  type ExpedienteCatalogo,
  type ExpedienteDetalle,
  type ExpedienteOpciones,
} from "@/modules/gobierno/api";

const control =
  "block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600";

type Errores = Record<string, string[]>;

export function ExpedienteFormPage() {
  const { expedienteId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const { notify } = useNotifications();
  const puedeEditar = tiene("gobierno_expedientes:manage", "empresa");
  const esEdicion = Boolean(expedienteId);

  const [numero, setNumero] = useState("");
  const [fechaInicio, setFechaInicio] = useState("");
  const [objeto, setObjeto] = useState("");
  const [partes, setPartes] = useState("");
  const [tipo, setTipo] = useState("");
  const [unidadId, setUnidadId] = useState("");
  const [responsableId, setResponsableId] = useState("");
  const [modalidad, setModalidad] = useState("");
  const [fundamento, setFundamento] = useState("");
  const [fuente, setFuente] = useState("");
  const [motivo, setMotivo] = useState("");
  const [errores, setErrores] = useState<Errores>({});
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [inicializado, setInicializado] = useState(false);

  const catalogoQuery = useQuery({
    queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId, "catalogo"],
    queryFn: () => apiFetch<ExpedienteCatalogo>("/gobierno/contrataciones/expedientes/catalogo"),
    enabled: puedeEditar && Boolean(activeCompanyId),
    retry: false,
  });

  const opcionesQuery = useQuery({
    queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId, "opciones"],
    queryFn: () => apiFetch<ExpedienteOpciones>("/gobierno/contrataciones/expedientes/opciones"),
    enabled: puedeEditar && Boolean(activeCompanyId),
    retry: false,
  });

  const detalleQuery = useQuery({
    queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId, "detalle", expedienteId],
    queryFn: () => apiFetch<ExpedienteDetalle>(`/gobierno/contrataciones/expedientes/${expedienteId}`),
    enabled: puedeEditar && esEdicion && Boolean(activeCompanyId),
    retry: false,
  });

  const detalle = detalleQuery.data;

  useEffect(() => {
    if (!esEdicion || !detalle || inicializado) return;
    setNumero(detalle.numero);
    setFechaInicio(detalle.fecha_inicio);
    setObjeto(detalle.objeto);
    setPartes(detalle.partes);
    setTipo(detalle.tipo_contratacion);
    setUnidadId(detalle.unidad_id);
    setModalidad(detalle.modalidad_declarada);
    setFundamento(detalle.modalidad_fundamento);
    setFuente(detalle.modalidad_fuente);
    setInicializado(true);
  }, [esEdicion, detalle, inicializado]);

  const crumbs = [
    { label: "Gobierno", to: "/gobierno" },
    { label: "Contrataciones" },
    { label: "Expedientes", to: "/gobierno/contrataciones/expedientes" },
    { label: esEdicion ? "Editar" : "Nuevo" },
  ];

  if (!puedeEditar) {
    return (
      <PageContent>
        <PageHeader crumbs={crumbs} title={esEdicion ? "Editar expediente" : "Nuevo expediente"} />
        <EmptyState title="Sin acceso" description="No tiene permisos para gestionar expedientes." />
      </PageContent>
    );
  }

  if (esEdicion && detalleQuery.isLoading) {
    return (
      <PageContent>
        <PageHeader crumbs={crumbs} title="Editar expediente" />
        <LoadingState />
      </PageContent>
    );
  }

  if (esEdicion && detalleQuery.isError) {
    return (
      <PageContent>
        <PageHeader crumbs={crumbs} title="Editar expediente" />
        <ErrorDeCarga message="No se pudo cargar el expediente." onRetry={() => detalleQuery.refetch()} />
      </PageContent>
    );
  }

  const catalogo = catalogoQuery.data;
  const opciones = opcionesQuery.data;

  const foliosBloquean = esEdicion && (detalle?.folios.length ?? 0) > 0;

  const unidades = opciones?.unidades ?? [];
  const unidadesConVigente =
    esEdicion && detalle && !unidades.some((u) => u.id === detalle.unidad_id)
      ? [...unidades, { id: detalle.unidad_id, nombre: detalle.unidad_nombre }]
      : unidades;

  async function guardar(e: React.FormEvent) {
    e.preventDefault();
    setEnviando(true);
    setErrores({});
    setMensaje(null);
    try {
      if (esEdicion && detalle) {
        const body = {
          numero,
          fecha_inicio: fechaInicio,
          objeto,
          partes: partes || null,
          tipo_contratacion: tipo,
          modalidad_declarada: modalidad || null,
          modalidad_fundamento: fundamento || null,
          modalidad_fuente: fuente || null,
          unidad_id: unidadId,
          motivo,
        };
        await apiFetch(`/gobierno/contrataciones/expedientes/${detalle.id}`, {
          method: "PATCH",
          body,
          ifMatch: String(detalle.version),
        });
        notify({ type: "success", title: "Expediente actualizado" });
        await queryClient.invalidateQueries({ queryKey: CONSULTA_EXPEDIENTES });
        navigate(`/gobierno/contrataciones/expedientes/${detalle.id}`);
      } else {
        const body = {
          numero,
          fecha_inicio: fechaInicio,
          objeto,
          partes: partes || null,
          tipo_contratacion: tipo,
          modalidad_declarada: modalidad || null,
          modalidad_fundamento: fundamento || null,
          modalidad_fuente: fuente || null,
          unidad_id: unidadId,
          responsable_id: responsableId,
        };
        const creado = await apiFetch<{ id: string }>("/gobierno/contrataciones/expedientes", {
          method: "POST",
          body,
        });
        notify({ type: "success", title: "Expediente creado" });
        await queryClient.invalidateQueries({ queryKey: CONSULTA_EXPEDIENTES });
        navigate(`/gobierno/contrataciones/expedientes/${creado.id}`);
      }
    } catch (err) {
      const apiErr = err as { status?: number; code?: string; message?: string; fieldErrors?: Errores };
      if (apiErr.status === 409 || apiErr.code === "stale") {
        setMensaje("El expediente cambió; recárguelo");
      } else {
        if (apiErr.fieldErrors) setErrores(apiErr.fieldErrors);
        setMensaje(apiErr.message ?? "No se pudo guardar el expediente.");
      }
    } finally {
      setEnviando(false);
    }
  }

  return (
    <PageContent>
      <PageHeader
        crumbs={crumbs}
        title={esEdicion ? `Editar ${numero}` : "Nuevo expediente"}
      />
      <form onSubmit={guardar} className="space-y-4">
        {mensaje ? (
          <div role="alert" className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
            {mensaje}
          </div>
        ) : null}

        <FormField label="Número" htmlFor="expediente-numero" required error={errores["numero"]?.join(", ")} help={foliosBloquean ? "No cambia una vez hay folios (LCP art. 19)" : undefined}>
          <TextInput id="expediente-numero" className={control} value={numero} onChange={(e) => setNumero(e.target.value)} disabled={foliosBloquean} required />
        </FormField>

        <FormField label="Fecha de iniciación" htmlFor="expediente-fecha" required error={errores["fecha_inicio"]?.join(", ")} help={foliosBloquean ? "No cambia una vez hay folios (LCP art. 19)" : undefined}>
          <TextInput id="expediente-fecha" type="date" className={control} value={fechaInicio} onChange={(e) => setFechaInicio(e.target.value)} disabled={foliosBloquean} required />
        </FormField>

        <FormField label="Objeto" htmlFor="expediente-objeto" required error={errores["objeto"]?.join(", ")}>
          <textarea id="expediente-objeto" className={control} maxLength={1000} value={objeto} onChange={(e) => setObjeto(e.target.value)} required />
        </FormField>

        <FormField label="Partes" htmlFor="expediente-partes" error={errores["partes"]?.join(", ")} help="Nombre de las partes, LCP art. 19. Puede completarlas después">
          <textarea id="expediente-partes" className={control} value={partes} onChange={(e) => setPartes(e.target.value)} />
        </FormField>

        <FormField label="Tipo de contratación" htmlFor="expediente-tipo" required error={errores["tipo_contratacion"]?.join(", ")}>
          <select id="expediente-tipo" className={control} value={tipo} onChange={(e) => setTipo(e.target.value)} required>
            <option value="">Seleccione…</option>
            {(catalogo?.tipos ?? []).map((o) => (
              <option key={o.codigo} value={o.codigo}>{o.etiqueta}</option>
            ))}
          </select>
        </FormField>

        <FormField label="Unidad responsable" htmlFor="expediente-unidad" required error={errores["unidad_id"]?.join(", ")}>
          <select id="expediente-unidad" className={control} value={unidadId} onChange={(e) => setUnidadId(e.target.value)} required>
            <option value="">Seleccione…</option>
            {unidadesConVigente.map((o) => (
              <option key={o.id} value={o.id}>{o.nombre}</option>
            ))}
          </select>
        </FormField>

        {!esEdicion ? (
          <FormField label="Responsable del expediente" htmlFor="expediente-responsable" required error={errores["responsable_id"]?.join(", ")}>
            <select id="expediente-responsable" className={control} value={responsableId} onChange={(e) => setResponsableId(e.target.value)} required>
              <option value="">Seleccione…</option>
              {(opciones?.funcionarios ?? []).map((o) => (
                <option key={o.id} value={o.id}>{`${o.nombre} · ${o.cargos.join(", ")}`}</option>
              ))}
            </select>
          </FormField>
        ) : null}

        <fieldset className="space-y-3">
          <legend className="text-sm font-medium text-text-900">Modalidad declarada</legend>
          <p className="text-sm text-text-700">{catalogo?.aviso_modalidad}</p>
          <FormField label="Modalidad" htmlFor="expediente-modalidad" error={errores["modalidad_declarada"]?.join(", ")}>
            <select id="expediente-modalidad" className={control} value={modalidad} onChange={(e) => setModalidad(e.target.value)}>
              <option value="">Sin declarar</option>
              {(catalogo?.modalidades ?? []).map((o) => (
                <option key={o.codigo} value={o.codigo}>{o.etiqueta}</option>
              ))}
            </select>
          </FormField>
          <FormField label="Fundamento declarado" htmlFor="expediente-fundamento" required={Boolean(modalidad)} error={errores["modalidad_fundamento"]?.join(", ")}>
            <textarea id="expediente-fundamento" className={control} value={fundamento} onChange={(e) => setFundamento(e.target.value)} />
          </FormField>
          <FormField label="Fuente o soporte" htmlFor="expediente-fuente" error={errores["modalidad_fuente"]?.join(", ")}>
            <TextInput id="expediente-fuente" className={control} value={fuente} onChange={(e) => setFuente(e.target.value)} />
          </FormField>
        </fieldset>

        {esEdicion ? (
          <FormField label="Motivo del cambio" htmlFor="expediente-motivo" required error={errores["motivo"]?.join(", ")}>
            <TextInput id="expediente-motivo" className={control} value={motivo} onChange={(e) => setMotivo(e.target.value)} required />
          </FormField>
        ) : null}

        <div className="flex gap-2">
          <Button type="submit" variant="primary" disabled={enviando}>Guardar</Button>
          <Link to={esEdicion && detalle ? `/gobierno/contrataciones/expedientes/${detalle.id}` : "/gobierno/contrataciones/expedientes"} className="inline-flex items-center rounded-md border border-border-subtle px-3 py-2 text-sm font-medium text-text-900">
            Cancelar
          </Link>
        </div>
      </form>
    </PageContent>
  );
}
