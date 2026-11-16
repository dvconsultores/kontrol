import { useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";

import { apiFetch } from "@/api/client";
import { useLicense } from "@/app/contexts/LicenseContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Button } from "@/components/Button";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { formatearFechaDeInstante } from "@/lib/fecha-de-negocio";
import {
  interpretarPaquete,
  mensajeDeErrorDeActivacion,
  mensajeDeErrorDeCarga,
  validarArchivoDeLicencia,
  vistaPrevia,
  type PaqueteDeLicencia,
  type VistaPreviaDeLicencia,
} from "@/lib/paquete-de-licencia";

export function ActivarLicencia({
  installationId,
}: {
  installationId: string;
}): React.JSX.Element {
  const { notify } = useNotifications();
  const queryClient = useQueryClient();
  const { refresh } = useLicense();
  const inputRef = useRef<HTMLInputElement>(null);

  const [paquete, setPaquete] = useState<PaqueteDeLicencia | null>(null);
  const [vista, setVista] = useState<VistaPreviaDeLicencia | null>(null);
  const [nombreArchivo, setNombreArchivo] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
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
      const r = await apiFetch<{ ok: boolean; license_id: string; mode: string }>(
        "/license/activate",
        {
          method: "POST",
          body: { payload: p.payload, signature_hex: p.signature_hex },
        },
      );
      limpiar();
      notify({
        type: "success",
        title: "Licencia activada",
        description: `Licencia ${r.license_id} · modo ${r.mode.replaceAll("_", " ")}`,
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

  return (
    <section
      aria-labelledby="activar-licencia"
      aria-busy={enCurso}
      className="mt-6 rounded-lg border border-border-default bg-surface-0 p-6"
    >
      <h2 id="activar-licencia" className="text-base font-semibold text-text-900">
        Activar licencia
      </h2>
      <p className="mt-1 text-sm text-text-500">
        Cargue el archivo de licencia firmado que emitió el propietario de KONTROL. El servidor
        verificará la firma, la identidad de la instalación y la vigencia antes de aplicarla.
      </p>

      <div className="mt-4">
        <label htmlFor="archivo-licencia" className="block text-sm font-medium text-text-700">
          Archivo de licencia firmado
        </label>
        <input
          id="archivo-licencia"
          ref={inputRef}
          type="file"
          accept=".json,application/json"
          disabled={enCurso}
          onChange={(e) => void onChange(e)}
          className="mt-1 block w-full text-sm text-text-700"
        />
        {paquete && (
          <p className="mt-2 break-all text-sm text-text-700">Archivo: {nombreArchivo}</p>
        )}
      </div>

      {error ? (
        <p role="alert" className="mt-3 break-words text-sm text-danger-600">
          {error}
        </p>
      ) : null}

      {vista ? (
        <dl className="mt-4 grid gap-3 sm:grid-cols-2">
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-text-500">
              Licencia
            </dt>
            <dd className="mt-1 break-all text-sm text-text-900">{vista.licenseId}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-text-500">
              Instalación
            </dt>
            <dd className="mt-1 break-all text-sm text-text-900">{vista.installationId}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-text-500">
              Clave de firma
            </dt>
            <dd className="mt-1 break-all text-sm text-text-900">{vista.kid}</dd>
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
            <dd className="mt-1 break-all text-sm text-text-900">
              {vista.revision ?? "sin revisión"}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-text-500">
              Versión mínima
            </dt>
            <dd className="mt-1 break-all text-sm text-text-900">{vista.minimumVersion ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-text-500">Empresas</dt>
            <dd className="mt-1 break-all text-sm text-text-900">{vista.empresas ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-text-500">Usuarios</dt>
            <dd className="mt-1 break-all text-sm text-text-900">{vista.usuarios ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-text-500">
              Módulos habilitados
            </dt>
            <dd className="mt-1 break-all text-sm text-text-900">
              {vista.modulos.length > 0 ? vista.modulos.join(", ") : "ninguno"}
            </dd>
          </div>
          {vista.perfilGobierno ? (
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-text-500">Perfil</dt>
              <dd className="mt-1 break-all text-sm text-text-900">KONTROL Gobierno</dd>
            </div>
          ) : null}
        </dl>
      ) : null}

      {vista && vista.installationId !== installationId ? (
        <p className="mt-3 text-sm text-warning-600">
          El paquete fue emitido para otra instalación. El servidor lo rechazará si no corresponde
          a esta.
        </p>
      ) : null}

      <div className="mt-4 flex flex-col gap-3 sm:flex-row">
        <Button
          onClick={() => setConfirmando(true)}
          disabled={!paquete || enCurso}
          aria-busy={enCurso}
          className="w-full sm:w-auto"
        >
          {enCurso ? "Validando y activando…" : "Validar y activar licencia"}
        </Button>
        {paquete && !enCurso ? (
          <Button variant="secondary" onClick={limpiar} className="w-full sm:w-auto">
            Quitar archivo
          </Button>
        ) : null}
      </div>

      <ConfirmationDialog
        open={confirmando && vista !== null}
        title="Activar licencia"
        description="La licencia quedará vinculada a esta instalación. El servidor verificará la firma, la identidad y la vigencia antes de aplicarla."
        confirmLabel="Activar licencia"
        cancelLabel="Cancelar"
        onCancel={() => setConfirmando(false)}
        onConfirm={confirmar}
      >
        {vista ? (
          <dl className="mt-2 grid gap-2">
            <div className="flex items-start justify-between gap-2">
              <dt className="text-xs font-medium uppercase tracking-wide text-text-500">
                Instalación
              </dt>
              <dd className="break-all text-sm text-text-900">{vista.installationId}</dd>
            </div>
            <div className="flex items-start justify-between gap-2">
              <dt className="text-xs font-medium uppercase tracking-wide text-text-500">
                Licencia
              </dt>
              <dd className="break-all text-sm text-text-900">{vista.licenseId}</dd>
            </div>
            <div className="flex items-start justify-between gap-2">
              <dt className="text-xs font-medium uppercase tracking-wide text-text-500">
                Clave de firma
              </dt>
              <dd className="break-all text-sm text-text-900">{vista.kid}</dd>
            </div>
            <div className="flex items-start justify-between gap-2">
              <dt className="text-xs font-medium uppercase tracking-wide text-text-500">
                Período
              </dt>
              <dd className="break-all text-sm text-text-900">
                {formatearFechaDeInstante(vista.periodStart)} →{" "}
                {formatearFechaDeInstante(vista.periodEnd)}
              </dd>
            </div>
            <div className="flex items-start justify-between gap-2">
              <dt className="text-xs font-medium uppercase tracking-wide text-text-500">
                Revisión
              </dt>
              <dd className="break-all text-sm text-text-900">
                {vista.revision ?? "sin revisión"}
              </dd>
            </div>
            <div className="flex items-start justify-between gap-2">
              <dt className="text-xs font-medium uppercase tracking-wide text-text-500">
                Versión mínima
              </dt>
              <dd className="break-all text-sm text-text-900">
                {vista.minimumVersion ?? "—"}
              </dd>
            </div>
            <div className="flex items-start justify-between gap-2">
              <dt className="text-xs font-medium uppercase tracking-wide text-text-500">
                Módulos
              </dt>
              <dd className="break-all text-sm text-text-900">
                {vista.modulos.length > 0 ? vista.modulos.join(", ") : "ninguno"}
              </dd>
            </div>
          </dl>
        ) : null}
      </ConfirmationDialog>
    </section>
  );
}
