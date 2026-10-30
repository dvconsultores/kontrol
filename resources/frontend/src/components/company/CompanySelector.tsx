/**
 * Selector de empresa activa (ARCH-MC-001, N6).
 *
 * Solo ofrece empresas que el backend ha declarado operables para este usuario.
 * Elegir aquí no concede nada: fija en qué empresa va cada petición de **esta**
 * pestaña, y el servidor vuelve a validarlo.
 */
import { Building2, Check, ChevronDown } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";

import { useCompany } from "@/app/contexts/CompanyContext";
import { useModuloGobierno } from "@/modules/gobierno/api";

export function CompanySelector(): React.JSX.Element | null {
  const { companies, activeCompany, estado, selectCompany } = useCompany();
  const moduloGobierno = useModuloGobierno();
  const textos = moduloGobierno
    ? {
        activa: "Ente activo",
        cambiar: "Cambiar de ente",
        seleccionar: "Seleccionar ente",
        vacio: "Seleccione un ente",
        lista: "Entes disponibles",
      }
    : {
        activa: "Empresa activa",
        cambiar: "Cambiar de empresa",
        seleccionar: "Seleccionar empresa",
        vacio: "Seleccione una empresa",
        lista: "Empresas disponibles",
      };
  const [abierto, setAbierto] = useState(false);
  const [enfocado, setEnfocado] = useState(0);
  const contenedor = useRef<HTMLDivElement>(null);
  const boton = useRef<HTMLButtonElement>(null);
  const idLista = useId();

  const operables = companies.filter((c) => c.status === "ACTIVE");

  useEffect(() => {
    if (!abierto) {
      return;
    }
    const fuera = (e: MouseEvent): void => {
      if (contenedor.current && !contenedor.current.contains(e.target as Node)) {
        setAbierto(false);
      }
    };
    document.addEventListener("mousedown", fuera);
    return () => document.removeEventListener("mousedown", fuera);
  }, [abierto]);

  if (estado === "COMPANY_LOADING") {
    return (
      <div className="flex items-center gap-2 text-sm text-text-500" role="status" aria-live="polite">
        <Building2 className="size-4 text-text-400" aria-hidden="true" />
        <span>Cargando empresas…</span>
      </div>
    );
  }

  if (operables.length === 0) {
    return (
      <div className="flex items-center gap-2 text-sm text-text-500">
        <Building2 className="size-4 text-text-400" aria-hidden="true" />
        <span>Sin empresas asignadas</span>
      </div>
    );
  }

  // Con una sola empresa no hay nada que elegir: se muestra el contexto, que
  // sigue siendo útil, sin un control que solo puede dar una respuesta.
  if (operables.length === 1) {
    const unica = operables[0];
    return (
      <div className="flex min-w-0 items-center gap-2 text-sm" data-testid="empresa-activa">
        <Building2 className="size-4 shrink-0 text-text-400" aria-hidden="true" />
        <span className="truncate font-medium text-text-900" title={unica.legal_name}>
          {unica.legal_name}
        </span>
        <span className="hidden text-text-400 sm:inline">·</span>
        <span className="hidden text-text-500 sm:inline">{unica.rif}</span>
      </div>
    );
  }

  const elegir = (id: string): void => {
    selectCompany(id);
    setAbierto(false);
    boton.current?.focus();
  };

  const enTeclado = (e: React.KeyboardEvent): void => {
    if (e.key === "Escape") {
      setAbierto(false);
      boton.current?.focus();
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setEnfocado((i) => Math.min(i + 1, operables.length - 1));
      return;
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      setEnfocado((i) => Math.max(i - 1, 0));
      return;
    }
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      elegir(operables[enfocado].id);
    }
  };

  return (
    <div ref={contenedor} className="relative min-w-0">
      <button
        ref={boton}
        type="button"
        data-testid="selector-empresa"
        aria-haspopup="listbox"
        aria-expanded={abierto}
        aria-controls={abierto ? idLista : undefined}
        aria-label={
          activeCompany
            ? `${textos.activa}: ${activeCompany.legal_name}. ${textos.cambiar}`
            : textos.seleccionar
        }
        onClick={() => {
          setEnfocado(Math.max(0, operables.findIndex((c) => c.id === activeCompany?.id)));
          setAbierto((v) => !v);
        }}
        onKeyDown={(e) => {
          if (!abierto && (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ")) {
            e.preventDefault();
            setEnfocado(Math.max(0, operables.findIndex((c) => c.id === activeCompany?.id)));
            setAbierto(true);
          }
        }}
        className="flex min-w-0 max-w-[16rem] items-center gap-2 rounded-md border border-border-default px-2 py-1.5 text-sm hover:bg-surface-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 sm:max-w-[24rem]"
      >
        <Building2 className="size-4 shrink-0 text-text-400" aria-hidden="true" />
        <span className="truncate font-medium text-text-900" title={activeCompany?.legal_name}>
          {activeCompany?.legal_name ?? textos.vacio}
        </span>
        <ChevronDown className="size-4 shrink-0 text-text-400" aria-hidden="true" />
      </button>

      {abierto ? (
        /* `listbox` debe contener `option` **directamente**: intercalar
           elementos de lista rompe la relación que el lector de pantalla usa
           para anunciar «opción 2 de 3». */
        <div
          id={idLista}
          role="listbox"
          tabIndex={-1}
          aria-label={textos.lista}
          aria-activedescendant={`${idLista}-${enfocado}`}
          onKeyDown={enTeclado}
          ref={(el) => el?.focus()}
          className="absolute left-0 z-50 mt-1 max-h-80 w-[min(22rem,calc(100vw-2rem))] overflow-auto rounded-md border border-border-default bg-surface-0 py-1 shadow-lg"
        >
          {operables.map((c, i) => {
            const activa = c.id === activeCompany?.id;
            return (
              <div
                key={c.id}
                id={`${idLista}-${i}`}
                role="option"
                aria-selected={activa}
                data-testid={`opcion-empresa-${c.code}`}
                onMouseEnter={() => setEnfocado(i)}
                onClick={() => elegir(c.id)}
                className={`flex cursor-pointer items-start gap-2 px-3 py-2 text-left text-sm ${
                  i === enfocado ? "bg-surface-100" : ""
                } ${activa ? "font-medium text-text-900" : "text-text-700"}`}
              >
                {/* La empresa activa se marca con un icono además del peso de
                    la tipografía: distinguirla solo por color dejaría fuera a
                    quien no lo percibe. */}
                <Check
                  className={`mt-0.5 size-4 shrink-0 ${activa ? "text-primary-600" : "invisible"}`}
                  aria-hidden="true"
                />
                <span className="min-w-0">
                  <span className="block truncate" title={c.legal_name}>
                    {c.legal_name}
                  </span>
                  <span className="block truncate text-xs text-text-600">
                    {c.code} · {c.rif}
                  </span>
                </span>
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
