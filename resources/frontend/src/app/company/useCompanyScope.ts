/**
 * Protección de operaciones ante un cambio de empresa (ARCH-MC-001, N6).
 *
 * El caso que esto evita es concreto y silencioso: alguien abre un formulario
 * en la empresa A, cambia a B en otra parte de la pantalla, vuelve y pulsa
 * Guardar. Sin esta captura, el registro se crearía en B con datos pensados
 * para A —clientes, almacenes y precios de otra empresa— y todo respondería 200.
 *
 * La empresa se fija **al abrir**, no al enviar. Cuál sea la activa al pulsar
 * el botón es justamente el dato que no se puede usar.
 *
 * Nada de esto es seguridad: el backend valida cada petición igual. Es lo que
 * impide que un descuido se convierta en un asiento en la empresa equivocada.
 */
import { useCallback, useRef } from "react";

import { useCompany } from "@/app/contexts/CompanyContext";

export class CompanyMismatchError extends Error {
  readonly abierta: string | null;
  readonly activa: string | null;

  constructor(abierta: string | null, activa: string | null) {
    super("La empresa cambió desde que se abrió esta pantalla");
    this.name = "CompanyMismatchError";
    this.abierta = abierta;
    this.activa = activa;
  }
}

export interface CompanyScope {
  /** Empresa en la que se abrió la pantalla o el formulario. */
  readonly companyId: string | null;
  /** ¿Sigue siendo la activa? */
  readonly vigente: boolean;
  /**
   * Ejecuta la operación solo si la empresa no ha cambiado, y la envía
   * explícitamente con la empresa de apertura.
   */
  ejecutar: <T>(operacion: (companyId: string) => Promise<T>) => Promise<T>;
}

export function useCompanyScope(): CompanyScope {
  const { activeCompanyId } = useCompany();
  // La empresa de apertura se congela en la primera renderización y no vuelve
  // a moverse mientras la pantalla viva.
  const abierta = useRef<string | null>(activeCompanyId);

  const ejecutar = useCallback(
    async <T,>(operacion: (companyId: string) => Promise<T>): Promise<T> => {
      const origen = abierta.current;
      if (!origen || origen !== activeCompanyId) {
        throw new CompanyMismatchError(origen, activeCompanyId);
      }
      return operacion(origen);
    },
    [activeCompanyId],
  );

  return {
    companyId: abierta.current,
    vigente: abierta.current !== null && abierta.current === activeCompanyId,
    ejecutar,
  };
}
