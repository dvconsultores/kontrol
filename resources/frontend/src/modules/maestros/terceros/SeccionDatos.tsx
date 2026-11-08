import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { ApiError, apiFetch } from "@/api/client";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Autorizado } from "@/components/Autorizado";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";

export interface CampoDato {
  name: string;
  label: string;
  required?: boolean;
  tipo?: "texto" | "booleano";
}

export interface FilaDato {
  id: string;
  validity: string;
  version: number;
  [campo: string]: unknown;
}

interface DatosResponse {
  items: FilaDato[];
}

function valorComoTexto(valor: unknown): string {
  if (valor === null || valor === undefined) return "";
  if (typeof valor === "boolean") return valor ? "true" : "false";
  return String(valor);
}

function estaVacio(valor: unknown): boolean {
  if (valor === null || valor === undefined) return true;
  if (typeof valor === "boolean") return false;
  return String(valor).trim() === "";
}

export function SeccionDatos({
  partyId,
  titulo,
  ruta,
  campos,
  resumen,
  editable,
  aviso,
  extra,
}: {
  partyId: string;
  titulo: string;
  ruta: "addresses" | "contacts" | "bank-accounts";
  campos: CampoDato[];
  resumen: (fila: FilaDato) => string;
  editable: boolean;
  aviso?: string;
  extra?: (fila: FilaDato) => React.ReactNode;
}) {
  const queryClient = useQueryClient();
  const { activeCompany } = useCompany();
  const { notify } = useNotifications();

  const base = `/maestros/terceros/${partyId}/${ruta}`;
  const queryKey = [
    "maestros",
    "tercero-datos",
    activeCompany?.id,
    partyId,
    ruta,
  ];

  const { data, isError } = useQuery<DatosResponse>({
    queryKey,
    queryFn: () => apiFetch<DatosResponse>(base),
    retry: false,
  });

  const [abierto, setAbierto] = useState(false);
  const [editando, setEditando] = useState<FilaDato | null>(null);
  const [valores, setValores] = useState<Record<string, unknown>>({});
  const [errorForm, setErrorForm] = useState<string | null>(null);
  const [conflictoVersion, setConflictoVersion] = useState(false);

  function abrirAlta() {
    const inicial: Record<string, unknown> = {};
    for (const campo of campos) {
      inicial[campo.name] = campo.tipo === "booleano" ? false : "";
    }
    setValores(inicial);
    setEditando(null);
    setErrorForm(null);
    setConflictoVersion(false);
    setAbierto(true);
  }

  function abrirEdicion(fila: FilaDato) {
    const inicial: Record<string, unknown> = {};
    for (const campo of campos) {
      const valor = fila[campo.name];
      inicial[campo.name] =
        valor === null || valor === undefined
          ? campo.tipo === "booleano"
            ? false
            : ""
          : valor;
    }
    setValores(inicial);
    setEditando(fila);
    setErrorForm(null);
    setConflictoVersion(false);
    setAbierto(true);
  }

  function cerrar() {
    setAbierto(false);
    setEditando(null);
    setValores({});
    setErrorForm(null);
    setConflictoVersion(false);
  }

  function cambiarCampo(name: string, value: unknown) {
    setValores((previos) => ({ ...previos, [name]: value }));
  }

  function camposFaltantes(): boolean {
    return campos.some(
      (campo) => campo.required && estaVacio(valores[campo.name]),
    );
  }

  function cuerpoAlta(): Record<string, unknown> {
    const cuerpo: Record<string, unknown> = {};
    for (const campo of campos) {
      const valor = valores[campo.name];
      if (campo.tipo === "booleano") {
        if (valor === true) cuerpo[campo.name] = true;
      } else if (!estaVacio(valor)) {
        cuerpo[campo.name] = valor;
      }
    }
    return cuerpo;
  }

  function cuerpoEdicion(): Record<string, unknown> {
    const cuerpo: Record<string, unknown> = {};
    if (!editando) return cuerpo;
    for (const campo of campos) {
      const original = editando[campo.name];
      const nuevo = valores[campo.name];
      const originalTexto = valorComoTexto(original);
      const nuevoTexto = valorComoTexto(nuevo);
      if (originalTexto === nuevoTexto) continue;
      if (campo.tipo === "booleano") {
        cuerpo[campo.name] = nuevo === true;
      } else if (estaVacio(nuevo)) {
        cuerpo[campo.name] = null;
      } else {
        cuerpo[campo.name] = nuevo;
      }
    }
    return cuerpo;
  }

  function mensajeDeError(error: unknown): string {
    if (error instanceof ApiError) return error.message;
    if (error instanceof Error) return error.message;
    return "Ocurrió un error inesperado.";
  }

  async function guardar() {
    if (camposFaltantes()) {
      setErrorForm("Complete los campos obligatorios.");
      return;
    }

    if (editando) {
      const cuerpo = cuerpoEdicion();
      if (Object.keys(cuerpo).length === 0) {
        cerrar();
        return;
      }

      try {
        await apiFetch(`${base}/${editando.id}`, {
          method: "PATCH",
          body: cuerpo,
          ifMatch: String(editando.version),
        });
        notify({
          type: "success",
          title: "Registro actualizado",
          description: `Se actualizó en ${titulo}.`,
        });
        cerrar();
        void queryClient.invalidateQueries({ queryKey: ["maestros"] });
      } catch (error) {
        if (
          error instanceof ApiError &&
          error.status === 409 &&
          error.code === "VERSION_CONFLICT"
        ) {
          setConflictoVersion(true);
          return;
        }
        setErrorForm(mensajeDeError(error));
      }
      return;
    }

    const cuerpo = cuerpoAlta();
    try {
      await apiFetch(base, {
        method: "POST",
        body: cuerpo,
      });
      notify({
        type: "success",
        title: "Registro creado",
        description: `Se guardó en ${titulo}.`,
      });
      cerrar();
      void queryClient.invalidateQueries({ queryKey: ["maestros"] });
    } catch (error) {
      setErrorForm(mensajeDeError(error));
    }
  }

  function recargar() {
    void queryClient.invalidateQueries({ queryKey: ["maestros"] });
    cerrar();
  }

  async function desactivar(fila: FilaDato) {
    try {
      await apiFetch(`${base}/${fila.id}/deactivate`, { method: "POST" });
      notify({
        type: "success",
        title: "Registro desactivado",
        description: `Se desactivó en ${titulo}.`,
      });
      void queryClient.invalidateQueries({ queryKey: ["maestros"] });
    } catch (error) {
      notify({
        type: "error",
        title: "No se pudo desactivar",
        description: mensajeDeError(error),
      });
    }
  }

  const items = data?.items ?? [];

  return (
    <section className="rounded-lg border border-border-default bg-surface-0 p-6">
      <h2 className="mb-4 text-lg font-semibold text-text-900">{titulo}</h2>

      {isError ? (
        <div
          role="alert"
          className="rounded-md border border-danger-100 bg-danger-100/40 p-3 text-sm text-danger-600"
        >
          No fue posible cargar {titulo}.
        </div>
      ) : null}

      {!isError && items.length === 0 && !abierto ? (
        <p className="text-sm text-text-600">Sin registros.</p>
      ) : null}

      {!isError && items.length > 0 ? (
        <ul className="space-y-3">
          {items.map((fila) => {
            const activa = fila.validity === "ACTIVE";
            const descripcion = resumen(fila);
            return (
              <li
                key={fila.id}
                className="flex flex-col gap-2 rounded-md border border-border-subtle p-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm text-text-900">{descripcion}</p>
                    {!activa ? (
                      <p className="text-sm text-text-500">Inactivo</p>
                    ) : null}
                  </div>

                  {editable && activa ? (
                    <div className="flex items-center gap-2">
                      <Autorizado operacion={["PATCH", `${base}/${fila.id}`]}>
                        <Button
                          variant="secondary"
                          size="sm"
                          aria-label={`Editar ${descripcion}`}
                          onClick={() => abrirEdicion(fila)}
                        >
                          Editar
                        </Button>
                      </Autorizado>
                      <Autorizado
                        operacion={["POST", `${base}/${fila.id}/deactivate`]}
                      >
                        <AsyncButton
                          variant="ghost"
                          size="sm"
                          aria-label={`Desactivar ${descripcion}`}
                          onClick={() => desactivar(fila)}
                        >
                          Desactivar
                        </AsyncButton>
                      </Autorizado>
                    </div>
                  ) : null}
                </div>

                {editable && activa && extra ? extra(fila) : null}
              </li>
            );
          })}
        </ul>
      ) : null}

      {editable && !abierto ? (
        <div className="mt-4">
          <Autorizado operacion={["POST", base]}>
            <Button
              variant="secondary"
              aria-label={`Agregar en ${titulo}`}
              onClick={abrirAlta}
            >
              Agregar
            </Button>
          </Autorizado>
        </div>
      ) : null}

      {editable && abierto ? (
        <div className="mt-4 rounded-md border border-border-subtle p-4">
          <h3 className="text-base font-medium text-text-900">
            {editando ? "Editar" : "Agregar"} {titulo}
          </h3>

          {aviso && editando && !conflictoVersion ? (
            <p role="note" className="text-sm text-text-600">
              {aviso}
            </p>
          ) : null}

          {errorForm ? (
            <div
              role="alert"
              className="rounded-md border border-danger-100 bg-danger-100/40 p-3 text-sm text-danger-600"
            >
              {errorForm}
            </div>
          ) : null}

          {conflictoVersion ? (
            <div
              role="alert"
              className="rounded-md border border-danger-100 bg-danger-100/40 p-3 text-sm text-danger-600"
            >
              <p>
                Otro usuario modificó este registro. Recargue para ver los
                cambios.
              </p>
              <Button variant="secondary" size="sm" onClick={recargar}>
                Recargar
              </Button>
            </div>
          ) : (
            <>
              <div className="mt-3 grid gap-4 sm:grid-cols-2">
                {campos.map((campo) => {
                  if (campo.tipo === "booleano") {
                    return (
                      <label
                        key={campo.name}
                        className="flex items-center gap-2 text-sm text-text-900"
                      >
                        <input
                          type="checkbox"
                          checked={Boolean(valores[campo.name])}
                          onChange={(evento) =>
                            cambiarCampo(campo.name, evento.target.checked)
                          }
                        />
                        {campo.label}
                      </label>
                    );
                  }

                  return (
                    <FormField
                      key={campo.name}
                      label={campo.label}
                      required={campo.required}
                    >
                      <TextInput
                        value={valorComoTexto(valores[campo.name])}
                        onChange={(evento) =>
                          cambiarCampo(campo.name, evento.target.value)
                        }
                      />
                    </FormField>
                  );
                })}
              </div>

              <div className="mt-4 flex items-center gap-2">
                <AsyncButton onClick={guardar}>Guardar</AsyncButton>
                <Button variant="ghost" onClick={cerrar}>
                  Cancelar
                </Button>
              </div>
            </>
          )}
        </div>
      ) : null}

      {editable && !abierto && aviso ? (
        <p className="mt-4 text-sm text-text-600">{aviso}</p>
      ) : null}
    </section>
  );
}
