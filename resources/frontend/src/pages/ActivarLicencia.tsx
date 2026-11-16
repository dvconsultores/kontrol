import { useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";

import { apiFetch } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useLicense } from "@/app/contexts/LicenseContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Button } from "@/components/Button";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import {
  etiquetaDeModo,
  etiquetaDeModulo,
  etiquetaDePerfil,
  textosDeActivacion,
} from "@/lib/licencia-presentacion";
import {
  interpretarPaquete,
  mensajeDeErrorDeActivacion,
  mensajeDeErrorDeCarga,
  validarArchivoDeLicencia,
  vistaPrevia,
  type PaqueteDeLicencia,
  type VistaPreviaDeLicencia,
} from "@/lib/paquete-de-licencia";
import { formatearFechaDeInstante } from "@/lib/fecha-de-negocio";

export function ActivarLicencia({
  installationId,
  modo,
}: {
  installationId: string;
  modo: string;
}): React.JSX.Element {
  const { notify } = useNotifications();
  const queryClient = useQueryClient();
  const { refresh } = useLicense();
  const { tiene } = useAutoridad();
  // Puerta propia (defensa en profundidad): sin license:create no se ofrece la activación; el backend sigue siendo la autoridad.
  const puedeActivar = tiene("license:create", "global");
  const textos = textosDeActivacion(modo);
  const inputRef = useRef<HTMLInputElement>(null);

  const [paquete, setPaquete] = useState<PaqueteDeLicencia | null>(null);
  const [vista, setVista] = useState<VistaPreviaDeLicencia | null>(null);
  const [nombreArchivo, setNombreArchivo] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exito, setExito] = useState<string | null>(null);
  const [confirmando, setConfirmando] = useState(false);
  const [enCurso, setEnCurso] = useState(false);

  const limpiar = (): void => {
    setPaquete(null);
    setVista(null);
    setNombreArchivo(null);
    setError(null);
    setConfirmando(false);
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  };

  const onChange = async (e: React.ChangeEvent<HTMLInputElement>): Promise<void> => {
    setError(null);
    setPaquete(null);
    setVista(null);
    setNombreArchivo(null);
    setExito(null);

    const archivo = e.target.files?.[0];
    if (!archivo) {
      return;
    }

    try {
      validarArchivoDeLicencia(archivo);
      const texto = await archivo.text();
      const p = interpretarPaquete(texto);
      setPaquete(p);
      setVista(vistaPrevia(p));
      setNombreArchivo(archivo.name);
    } catch (errorDeCarga) {
      setError(mensajeDeErrorDeCarga(errorDeCarga));
      if (inputRef.current) {
        inputRef.current.value = "";
      }
    }
  };

  const activar = async (p: PaqueteDeLicencia): Promise<void> => {
    if (enCurso) {
      return;
    }
    setEnCurso(true);
    setError(null);
    try {
      const aplicada = vistaPrevia(p);
      const r = await apiFetch<{ ok: boolean; license_id: string; mode: string }>(
        "/license/activate",
        {
          method: "POST",
          body: { payload: p.payload, signature_hex: p.signature_hex },
        },
      );
      const mensaje = `Perfil: ${etiquetaDePerfil(aplicada.perfil)} · Estado: ${etiquetaDeModo(r.mode)} · Licencia ${r.license_id}`;
      setExito(mensaje);
      limpiar();
      notify({
        type: "success",
        title: "Licencia activada correctamente",
        description: mensaje,
      });
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["license"] }),
        queryClient.invalidateQueries({ queryKey: ["licencia", "modulo", "gobierno"] }),
        refresh(),
      ]);
    } catch (errorDeActivacion) {
      setError(mensajeDeErrorDeActivacion(errorDeActivacion));
    } finally {
      setEnCurso(false);
    }
  };

  const confirmar = async (): Promise<void> => {
    const actual = paquete;
    setConfirmando(false);
    if (!actual) {
      return;
    }
    void activar(actual);
  };

  if (!puedeActivar) {
    return (
      <section aria-labelledby="activar-licencia" className="mt-6 rounded-lg border border-border-default bg-surface-0 p-6">
        <h2 id="activar-licencia" className="text-base font-semibold text-text-900">
          Activar o actualizar licencia
        </h2>
        <p className="mt-1 text-sm text-text-700">
          No tiene permiso para activar o reemplazar licencias.
        </p>
        <p className="mt-1 text-sm text-text-500">
          Se requiere license:create. Solicítelo al administrador de KONTROL.
        </p>
      </section>
    );
  }

  const claseBorde = textos.destacada
    ? "mt-6 rounded-lg border-2 border-brand-600 bg-surface-0 p-6"
    : "mt-6 rounded-lg border border-border-default bg-surface-0 p-6";

  return (
    <section aria-labelledby="activar-licencia" aria-busy={enCurso} className={claseBorde}>
      <h2 id="activar-licencia" className="text-base font-semibold text-text-900">
        {textos.titulo}
      </h2>
      <p className="mt-1 text-sm text-text-500">
        {textos.descripcion} El servidor verificará la firma, la identidad de la instalación y la
        vigencia antes de aplicarla.
      </p>

      {exito ? (
        <div role="status" className="mt-4 rounded-md bg-success-100 p-3 text-sm text-text-900">
          <p className="font-semibold">Licencia activada correctamente</p>
          <p className="mt-1 break-words">{exito}</p>
        </div>
      ) : null}

      <div className="relative mt-4">
        <p id="archivo-licencia-rotulo" className="text-sm font-medium text-text-700">
          Archivo de licencia firmado
        </p>
        <input
          id="archivo-licencia"
          ref={inputRef}
          type="file"
          accept=".json,application/json"
          disabled={enCurso}
          tabIndex={-1}
          aria-labelledby="archivo-licencia-rotulo"
          onChange={(e) => void onChange(e)}
          className="sr-only"
        />
        <div className="mt-2 flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
          <Button
            variant="secondary"
            onClick={() => inputRef.current?.click()}
            disabled={enCurso}
            aria-describedby="archivo-licencia-estado"
            className="w-full sm:w-auto"
          >
            {textos.seleccionar}
          </Button>
          <p id="archivo-licencia-estado" className="break-all text-sm text-text-700">
            {nombreArchivo ? `Archivo seleccionado: ${nombreArchivo}` : "Ningún archivo seleccionado"}
          </p>
        </div>
      </div>

      {error ? (
        <p role="alert" className="mt-3 break-words text-sm text-danger-600">
          {error}
        </p>
      ) : null}

      {vista ? (
        <div className="mt-4 rounded-md border border-border-default bg-surface-50 p-4">
          <h3 className="text-sm font-semibold text-text-900">Vista previa de la licencia</h3>
          <dl className="mt-3 grid gap-3 sm:grid-cols-2">
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-text-500">Licencia</dt>
              <dd className="mt-1 break-all text-sm text-text-900">{vista.licenseId}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-text-500">Instalación</dt>
              <dd className="mt-1 break-all text-sm text-text-900">{vista.installationId}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-text-500">Perfil</dt>
              <dd className="mt-1 break-all text-sm text-text-900">{etiquetaDePerfil(vista.perfil)}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-text-500">Período</dt>
              <dd className="mt-1 break-all text-sm text-text-900">
                {formatearFechaDeInstante(vista.periodStart)} →{" "}
                {formatearFechaDeInstante(vista.periodEnd)}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-text-500">Revisión</dt>
              <dd className="mt-1 break-all text-sm text-text-900">{vista.revision ?? "sin revisión"}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-text-500">Versión mínima</dt>
              <dd className="mt-1 break-all text-sm text-text-900">{vista.minimumVersion ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-text-500">Clave de firma</dt>
              <dd className="mt-1 break-all text-sm text-text-900">{vista.kid}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-text-500">Empresas</dt>
              <dd className="mt-1 break-all text-sm text-text-900">{vista.empresas ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-text-500">Usuarios</dt>
              <dd className="mt-1 break-all text-sm text-text-900">{vista.usuarios ?? "—"}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-xs font-medium uppercase tracking-wide text-text-500">Módulos habilitados</dt>
              <dd className="mt-1">
                {vista.modulos.length > 0 ? (
                  <ul className="mt-1 flex flex-wrap gap-2">
                    {vista.modulos.map((modulo) => (
                      <li key={modulo} className="rounded bg-surface-100 px-2 py-0.5 text-sm text-text-900">
                        {etiquetaDeModulo(modulo)}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-text-900">Ninguno</p>
                )}
              </dd>
            </div>
          </dl>
        </div>
      ) : null}

      {vista ? (
        vista.installationId === installationId ? (
          <p className="mt-3 text-sm text-success-600">
            ✓ Instalación verificada: el paquete corresponde a esta instalación. La firma la
            verificará el servidor.
          </p>
        ) : (
          <p className="mt-3 rounded-md bg-warning-100 p-3 text-sm text-text-900">
            <strong>Advertencia:</strong> Esta licencia fue emitida para otra instalación. El
            servidor la rechazará.
          </p>
        )
      ) : null}

      <div className="mt-4 flex flex-col gap-3 sm:flex-row">
        <Button
          onClick={() => setConfirmando(true)}
          disabled={!paquete || enCurso}
          aria-busy={enCurso}
          className="w-full sm:w-auto"
        >
          {enCurso ? "Validando…" : textos.aplicar}
        </Button>
        {paquete && !enCurso ? (
          <Button variant="secondary" onClick={limpiar} className="w-full sm:w-auto">
            Quitar archivo
          </Button>
        ) : null}
      </div>

      <ConfirmationDialog
        open={confirmando && vista !== null}
        title={textos.titulo}
        description="La licencia quedará vinculada a esta instalación. El servidor verificará la firma, la identidad y la vigencia antes de aplicarla."
        confirmLabel={textos.aplicar}
        cancelLabel="Cancelar"
        onCancel={() => setConfirmando(false)}
        onConfirm={confirmar}
      >
        {vista ? (
          <dl className="mt-2 grid gap-2">
            <div className="flex items-start justify-between gap-2">
              <dt className="text-xs font-medium uppercase tracking-wide text-text-500">Perfil</dt>
              <dd className="break-all text-sm text-text-900">{etiquetaDePerfil(vista.perfil)}</dd>
            </div>
            <div className="flex items-start justify-between gap-2">
              <dt className="text-xs font-medium uppercase tracking-wide text-text-500">Instalación</dt>
              <dd className="break-all text-sm text-text-900">{vista.installationId}</dd>
            </div>
            <div className="flex items-start justify-between gap-2">
              <dt className="text-xs font-medium uppercase tracking-wide text-text-500">Licencia</dt>
              <dd className="break-all text-sm text-text-900">{vista.licenseId}</dd>
            </div>
            <div className="flex items-start justify-between gap-2">
              <dt className="text-xs font-medium uppercase tracking-wide text-text-500">Período</dt>
              <dd className="break-all text-sm text-text-900">
                {formatearFechaDeInstante(vista.periodStart)} →{" "}
                {formatearFechaDeInstante(vista.periodEnd)}
              </dd>
            </div>
            <div className="flex items-start justify-between gap-2">
              <dt className="text-xs font-medium uppercase tracking-wide text-text-500">Revisión</dt>
              <dd className="break-all text-sm text-text-900">{vista.revision ?? "sin revisión"}</dd>
            </div>
            <div className="flex items-start justify-between gap-2">
              <dt className="text-xs font-medium uppercase tracking-wide text-text-500">Clave de firma</dt>
              <dd className="break-all text-sm text-text-900">{vista.kid}</dd>
            </div>
            <div className="flex items-start justify-between gap-2">
              <dt className="text-xs font-medium uppercase tracking-wide text-text-500">Módulos</dt>
              <dd className="break-all text-sm text-text-900">
                {vista.modulos.length > 0
                  ? vista.modulos.map((modulo) => etiquetaDeModulo(modulo)).join(", ")
                  : "Ninguno"}
              </dd>
            </div>
            <div className="flex items-start justify-between gap-2">
              <dt className="text-xs font-medium uppercase tracking-wide text-text-500">Empresas</dt>
              <dd className="break-all text-sm text-text-900">{vista.empresas ?? "—"}</dd>
            </div>
            <div className="flex items-start justify-between gap-2">
              <dt className="text-xs font-medium uppercase tracking-wide text-text-500">Usuarios</dt>
              <dd className="break-all text-sm text-text-900">{vista.usuarios ?? "—"}</dd>
            </div>
            <div className="flex items-start justify-between gap-2">
              <dt className="text-xs font-medium uppercase tracking-wide text-text-500">Versión mínima</dt>
              <dd className="break-all text-sm text-text-900">{vista.minimumVersion ?? "—"}</dd>
            </div>
          </dl>
        ) : null}
      </ConfirmationDialog>
    </section>
  );
}
