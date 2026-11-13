import { useId, useState } from "react";

import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";

import type {
  CategoriaProgramatica,
  EjercicioDetalle,
  EscribirEjercicio,
} from "./api";

interface EstructuraEjercicioProps {
  detalle: EjercicioDetalle;
  puedeGestionar: boolean;
  escribir: EscribirEjercicio;
  erroresServidor: Record<string, string[]>;
}

/**
 * Estructura programática del ejercicio: niveles y categorías.
 * Solo editable para un ejercicio en BORRADOR y con capacidad de gestión.
 */
export function EstructuraEjercicio({
  detalle,
  puedeGestionar,
  escribir,
  erroresServidor,
}: EstructuraEjercicioProps) {
  const idTitulo = useId();
  const editable = puedeGestionar && detalle.estado === "BORRADOR";

  const [niveles, setNiveles] = useState<string[]>(() =>
    detalle.niveles.length > 0
      ? detalle.niveles.map((nivel) => nivel.nombre)
      : [""],
  );
  const [enviandoNiveles, setEnviandoNiveles] = useState(false);

  const [categoriaEnEdicion, setCategoriaEnEdicion] = useState<string | null>(
    null,
  );
  const [denominacionEdicion, setDenominacionEdicion] = useState("");
  const [enviandoFila, setEnviandoFila] = useState(false);
  const [enviandoEliminacion, setEnviandoEliminacion] = useState(false);

  const [nivelNueva, setNivelNueva] = useState("");
  const [padreNueva, setPadreNueva] = useState("");
  const [codigoNueva, setCodigoNueva] = useState("");
  const [denominacionNueva, setDenominacionNueva] = useState("");
  const [enviandoNueva, setEnviandoNueva] = useState(false);

  const listaDeCategorias = detalle.categorias;
  const hayCategorias = listaDeCategorias.length > 0;

  async function guardarNiveles() {
    if (!editable) return;
    setEnviandoNiveles(true);
    try {
      await escribir("/niveles", "PUT", {
        niveles: niveles.map((nombre) => ({ nombre: nombre.trim() })),
      });
    } catch {
      // La página ya informó del error y conserva lo escrito.
    } finally {
      setEnviandoNiveles(false);
    }
  }

  function cambiarNivel(indice: number, valor: string) {
    setNiveles((actuales) =>
      actuales.map((nivel, i) => (i === indice ? valor : nivel)),
    );
  }

  function anadirNivel() {
    setNiveles((actuales) =>
      actuales.length >= 8 ? actuales : [...actuales, ""],
    );
  }

  function quitarNivel(indice: number) {
    setNiveles((actuales) =>
      actuales.length <= 1
        ? actuales
        : actuales.filter((_, i) => i !== indice),
    );
  }

  function comenzarEdicion(categoria: CategoriaProgramatica) {
    setCategoriaEnEdicion(categoria.id);
    setDenominacionEdicion(categoria.denominacion);
  }

  function cancelarEdicion() {
    setCategoriaEnEdicion(null);
    setDenominacionEdicion("");
  }

  async function guardarEdicion(id: string) {
    setEnviandoFila(true);
    try {
      await escribir(`/categorias/${id}`, "PATCH", {
        denominacion: denominacionEdicion.trim(),
      });
      setCategoriaEnEdicion(null);
      setDenominacionEdicion("");
    } catch {
      // La página ya informó del error.
    } finally {
      setEnviandoFila(false);
    }
  }

  async function eliminarCategoria(id: string) {
    setEnviandoEliminacion(true);
    try {
      await escribir(`/categorias/${id}`, "DELETE");
    } catch {
      // La página ya informó del error.
    } finally {
      setEnviandoEliminacion(false);
    }
  }

  const nivelSeleccionado = Number(nivelNueva);
  const opcionesPadre =
    nivelSeleccionado > 1
      ? listaDeCategorias.filter(
          (categoria) => categoria.nivel_orden === nivelSeleccionado - 1,
        )
      : [];

  async function agregarCategoria() {
    if (!editable || nivelSeleccionado < 1) return;
    setEnviandoNueva(true);
    try {
      await escribir("/categorias", "POST", {
        nivel_orden: nivelSeleccionado,
        parent_id: nivelSeleccionado > 1 ? padreNueva || null : null,
        codigo: codigoNueva.trim(),
        denominacion: denominacionNueva.trim(),
      });
      setCodigoNueva("");
      setDenominacionNueva("");
      setPadreNueva("");
    } catch {
      // La página ya informó del error.
    } finally {
      setEnviandoNueva(false);
    }
  }

  return (
    <section aria-labelledby={idTitulo}>
      <h2
        id={idTitulo}
        className="mb-4 text-lg font-semibold text-text-900"
      >
        Estructura programática
      </h2>

      <div className="mb-6">
        <h3 className="mb-2 text-base font-medium text-text-800">
          Niveles programáticos
        </h3>
        {editable && listaDeCategorias.length === 0 ? (
          <div className="rounded-md border border-border-default p-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {niveles.map((nombre, indice) => (
                <div
                  key={indice}
                  className="flex items-start gap-2"
                >
                  <div className="flex-1">
                    <FormField
                      label={`Nivel ${indice + 1}`}
                      htmlFor={`nivel-${indice}`}
                    >
                      <TextInput
                        id={`nivel-${indice}`}
                        value={nombre}
                        onChange={(evento) =>
                          cambiarNivel(indice, evento.target.value)
                        }
                        placeholder="Nombre del nivel"
                      />
                    </FormField>
                  </div>
                  <button
                    type="button"
                    onClick={() => quitarNivel(indice)}
                    disabled={niveles.length <= 1 || enviandoNiveles}
                    className="mt-7 inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Quitar
                  </button>
                </div>
              ))}
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={anadirNivel}
                disabled={niveles.length >= 8 || enviandoNiveles}
                className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Añadir nivel
              </button>
              <button
                type="button"
                onClick={() => void guardarNiveles()}
                disabled={enviandoNiveles}
                className="inline-flex h-10 items-center rounded-md bg-brand-600 px-3 text-sm font-medium text-white hover:bg-brand-700 focus-visible:outline-brand-600 disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-brand-300"
              >
                Guardar niveles
              </button>
            </div>
          </div>
        ) : (
          <div>
            {listaDeCategorias.length === 0 && detalle.niveles.length === 0 ? (
              <p className="text-sm text-text-700">
                Aún no hay niveles programáticos.
              </p>
            ) : (
              <ol className="list-inside list-decimal text-sm text-text-900">
                {detalle.niveles.map((nivel) => (
                  <li key={nivel.orden}>
                    {nivel.orden}. {nivel.nombre}
                  </li>
                ))}
              </ol>
            )}
            {editable && hayCategorias ? (
              <p className="mt-2 text-sm text-text-700">
                Los niveles no se pueden cambiar mientras existan categorías.
              </p>
            ) : null}
          </div>
        )}
      </div>

      <div className="mb-6">
        <h3 className="mb-2 text-base font-medium text-text-800">
          Categorías programáticas
        </h3>
        <div
          className="relative overflow-x-auto"
          tabIndex={0}
          role="region"
          aria-label="Categorías programáticas"
        >
          <table className="w-full border-collapse text-left">
            <caption className="sr-only">
              Categorías programáticas del ejercicio
            </caption>
            <thead>
              <tr className="border-b border-border-subtle">
                <th
                  scope="col"
                  className="px-3 py-2 text-sm font-medium text-text-700"
                >
                  Código
                </th>
                <th
                  scope="col"
                  className="px-3 py-2 text-sm font-medium text-text-700"
                >
                  Denominación
                </th>
                <th
                  scope="col"
                  className="px-3 py-2 text-sm font-medium text-text-700"
                >
                  Nivel
                </th>
                {editable ? (
                  <th
                    scope="col"
                    className="px-3 py-2 text-sm font-medium text-text-700"
                  >
                    <span className="sr-only">Acciones</span>
                  </th>
                ) : null}
              </tr>
            </thead>
            <tbody>
              {listaDeCategorias.length === 0 ? (
                <tr className="border-b border-border-subtle">
                  <td
                    colSpan={editable ? 4 : 3}
                    className="px-3 py-2 text-sm text-text-700"
                  >
                    Aún no hay categorías.
                  </td>
                </tr>
              ) : (
                listaDeCategorias.map((categoria) => (
                  <tr
                    key={categoria.id}
                    className="border-b border-border-subtle"
                  >
                    <td className="px-3 py-2 text-sm text-text-900">
                      {categoria.codigo_completo}
                    </td>
                    <td className="px-3 py-2 text-sm text-text-900">
                      {categoriaEnEdicion === categoria.id ? (
                        <div className="flex items-center gap-2">
                          <div className="flex-1">
                            <TextInput
                              id={`denominacion-${categoria.id}`}
                              aria-label="Denominación"
                              value={denominacionEdicion}
                              onChange={(evento) =>
                                setDenominacionEdicion(evento.target.value)
                              }
                            />
                          </div>
                          <button
                            type="button"
                            onClick={() => void guardarEdicion(categoria.id)}
                            disabled={enviandoFila}
                            className="inline-flex h-10 items-center rounded-md bg-brand-600 px-3 text-sm font-medium text-white hover:bg-brand-700 focus-visible:outline-brand-600 disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-brand-300"
                          >
                            Guardar
                          </button>
                          <button
                            type="button"
                            onClick={cancelarEdicion}
                            disabled={enviandoFila}
                            className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            Cancelar
                          </button>
                        </div>
                      ) : (
                        categoria.denominacion
                      )}
                    </td>
                    <td className="px-3 py-2 text-sm text-text-900">
                      {categoria.nivel_nombre}
                    </td>
                    {editable ? (
                      <td className="px-3 py-2 text-sm text-text-900">
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => comenzarEdicion(categoria)}
                            disabled={
                              enviandoFila ||
                              enviandoEliminacion ||
                              categoriaEnEdicion !== null
                            }
                            className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            Editar
                          </button>
                          <button
                            type="button"
                            onClick={() => void eliminarCategoria(categoria.id)}
                            disabled={enviandoEliminacion || enviandoFila}
                            className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-red-700 hover:bg-surface-100 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            Eliminar
                          </button>
                        </div>
                      </td>
                    ) : null}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {editable && detalle.niveles.length > 0 ? (
        <div>
          <h3 className="mb-2 text-base font-medium text-text-800">
            Nueva categoría
          </h3>
          <form
            onSubmit={(evento) => {
              evento.preventDefault();
              void agregarCategoria();
            }}
            className="rounded-md border border-border-default p-4"
          >
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <FormField
                label="Nivel"
                htmlFor="nivel-nueva-categoria"
                error={erroresServidor.nivel_orden?.[0]}
              >
                <select
                  id="nivel-nueva-categoria"
                  value={nivelNueva}
                  onChange={(evento) => {
                    setNivelNueva(evento.target.value);
                    setPadreNueva("");
                  }}
                  aria-invalid={Boolean(erroresServidor.nivel_orden)}
                  className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
                >
                  <option value="">Seleccione un nivel</option>
                  {detalle.niveles.map((nivel) => (
                    <option key={nivel.orden} value={nivel.orden}>
                      {nivel.orden}. {nivel.nombre}
                    </option>
                  ))}
                </select>
              </FormField>

              {nivelSeleccionado > 1 ? (
                <FormField
                  label="Categoría superior"
                  htmlFor="padre-nueva-categoria"
                  error={erroresServidor.parent_id?.[0]}
                >
                  <select
                    id="padre-nueva-categoria"
                    value={padreNueva}
                    onChange={(evento) => setPadreNueva(evento.target.value)}
                    aria-invalid={Boolean(erroresServidor.parent_id)}
                    className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
                  >
                    <option value="">Sin categoría superior</option>
                    {opcionesPadre.map((categoria) => (
                      <option key={categoria.id} value={categoria.id}>
                        {categoria.codigo} · {categoria.denominacion}
                      </option>
                    ))}
                  </select>
                </FormField>
              ) : null}

              <FormField
                label="Código"
                htmlFor="codigo-nueva-categoria"
                error={erroresServidor.codigo?.[0]}
              >
                <TextInput
                  id="codigo-nueva-categoria"
                  value={codigoNueva}
                  onChange={(evento) => setCodigoNueva(evento.target.value)}
                  aria-invalid={Boolean(erroresServidor.codigo)}
                />
              </FormField>

              <FormField
                label="Denominación"
                htmlFor="denominacion-nueva-categoria"
                error={erroresServidor.denominacion?.[0]}
              >
                <TextInput
                  id="denominacion-nueva-categoria"
                  value={denominacionNueva}
                  onChange={(evento) =>
                    setDenominacionNueva(evento.target.value)
                  }
                  aria-invalid={Boolean(erroresServidor.denominacion)}
                />
              </FormField>
            </div>
            <div className="mt-4">
              <button
                type="submit"
                disabled={enviandoNueva || !nivelNueva}
                className="inline-flex h-10 items-center rounded-md bg-brand-600 px-3 text-sm font-medium text-white hover:bg-brand-700 focus-visible:outline-brand-600 disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-brand-300"
              >
                Agregar categoría
              </button>
            </div>
          </form>
        </div>
      ) : null}
    </section>
  );
}
