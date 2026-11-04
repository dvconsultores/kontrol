import { useState } from "react";
import { Link } from "react-router";
import { useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { FormField } from "@/components/FormField";
import {
  CONSULTA_PAQUETES,
  ETIQUETAS_MOTIVO_VERIFICACION,
  ETIQUETAS_RESULTADO_VERIFICACION,
  AVISO_HUELLA_PAQUETE,
  formatearBytes,
  type ResultadoDeVerificacionPaquete,
} from "@/modules/gobierno/api";

export function VerificarPaquete(): React.JSX.Element | null {
  const { tiene } = useAutoridad();
  const puedeVerificar = tiene("gobierno_paquetes:view", "empresa");
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const [archivo, setArchivo] = useState<File | null>(null);
  const [resultado, setResultado] = useState<ResultadoDeVerificacionPaquete | null>(null);
  const [error, setError] = useState<string | null>(null);

  const verificar = async () => {
    if (archivo === null) return;
    const datos = new FormData();
    datos.append("archivo", archivo);
    try {
      const r = await apiFetch<ResultadoDeVerificacionPaquete>("/gobierno/paquetes/verificar", {
        method: "POST",
        body: datos,
      });
      setResultado(r);
      setError(null);
      await queryClient.invalidateQueries({ queryKey: [...CONSULTA_PAQUETES] });
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 422) {
          setError(err.message);
        } else if (err.status === 403) {
          notify({ type: "error", title: "No tiene permiso para verificar paquetes" });
        } else {
          notify({ type: "error", title: "No fue posible verificar el paquete" });
        }
      }
    }
  };

  if (!puedeVerificar) return null;

  return (
    <section aria-labelledby="verificar-paquete" className="mt-8 rounded-md border border-border-default p-4">
      <h2 id="verificar-paquete" className="text-lg font-semibold text-text-900">
        Verificar un paquete
      </h2>
      <p className="text-sm text-text-600">
        Suba una copia del paquete (ZIP) para comprobar que no fue alterado. {AVISO_HUELLA_PAQUETE}
      </p>

      <FormField
        label="Archivo del paquete"
        htmlFor="verificar-archivo"
        required
        help="Suba el ZIP descargado del paquete"
      >
        <input
          id="verificar-archivo"
          type="file"
          accept=".zip,application/zip"
          onChange={(e) => {
            setArchivo(e.target.files?.[0] ?? null);
            setResultado(null);
            setError(null);
          }}
        />
      </FormField>

      <AsyncButton onClick={verificar} disabled={archivo === null}>
        Verificar
      </AsyncButton>

      {error !== null ? (
        <p role="alert" className="text-sm text-danger-600">
          {error}
        </p>
      ) : null}

      {resultado !== null ? (
        <div role="status" className="mt-4 rounded-md border p-3" aria-live="polite">
          <p className="font-semibold">
            Resultado: {ETIQUETAS_RESULTADO_VERIFICACION[resultado.resultado]}
          </p>
          {resultado.identico ? (
            <p>La copia es idéntica byte a byte a la registrada.</p>
          ) : null}
          {resultado.paquete ? (
            <p>
              Paquete{" "}
              <Link to={`/gobierno/paquetes/${resultado.paquete.id}`}>
                {resultado.paquete.codigo}
              </Link>
            </p>
          ) : null}
          <p className="font-mono text-xs break-all">
            Huella del archivo: {resultado.huella_archivo}
          </p>
          <p>Tamaño: {formatearBytes(resultado.bytes_archivo)}</p>
          {resultado.motivos.length > 0 ? (
            <ul aria-label="Motivos">
              {resultado.motivos.map((m, indice) => (
                <li key={`${m.codigo}-${m.ruta ?? ""}-${indice}`}>
                  {ETIQUETAS_MOTIVO_VERIFICACION[m.codigo] ?? m.codigo}
                  {m.ruta ? ` · ${m.ruta}` : ""}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
