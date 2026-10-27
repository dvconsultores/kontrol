/**
 * AUDITORIA-CREATED-AT · la columna «Fecha» muestra el `event_time` del contrato.
 *
 * La columna leía `created_at`, un campo que el servidor no publica: cada fila
 * decía «Invalid Date». El contrato es `event_time` (ISO 8601 con zona, nunca
 * nulo) y la presentación es la convención del producto: `formatearFecha`, que
 * es `toLocaleString("es-VE")` en la zona del navegador, igual que las otras
 * ocho pantallas que enseñan un instante. Por eso el texto exacto depende de la
 * zona del proceso, y aquí se fija por zona: la suite se ejecuta bajo UTC,
 * America/Caracas y Europe/Amsterdam.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, expectTypeOf, it, vi } from "vitest";

import type { AuditEvent, PagedResult } from "@/api/types";
import { formatearFecha } from "@/i18n";

const apiFetch = vi.fn();
vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));
vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({
    estado: "LISTA",
    puede: () => true,
    tiene: () => true,
    motivo: () => null,
    motivoDeCapacidad: () => null,
  }),
}));
const { AuditoriaPage } = await import("./AuditoriaPage");

//: Dos instantes con zona explícita: uno a media tarde y otro que cruza la medianoche
//: civil según la zona (02:30 UTC del 1 de octubre es el 30 de septiembre en Caracas).
const TARDE = "2026-09-30T18:30:00+00:00";
const MEDIANOCHE = "2026-10-01T02:30:00+00:00";

//: Lo que la convención produce bajo cada zona del proceso, medido con Node 24 / ICU 78.
const ESPERADO: Record<string, Record<string, string>> = {
  UTC: { [TARDE]: "30/9/2026, 6:30:00 p. m.", [MEDIANOCHE]: "1/10/2026, 2:30:00 a. m." },
  "America/Caracas": { [TARDE]: "30/9/2026, 2:30:00 p. m.", [MEDIANOCHE]: "30/9/2026, 10:30:00 p. m." },
  "Europe/Amsterdam": { [TARDE]: "30/9/2026, 8:30:00 p. m.", [MEDIANOCHE]: "1/10/2026, 4:30:00 a. m." },
};
const ZONA = Intl.DateTimeFormat().resolvedOptions().timeZone;

function evento(n: number, event_time: string): AuditEvent {
  return {
    id: `ev-${n}`, action: "LOGIN_SUCCESS", entity_type: "User", entity_id: `u-${n}`, user_id: null,
    request_id: `rastro-${n}`, source: "API", reason: null, event_time,
  };
}

function sobre(items: AuditEvent[]): PagedResult<AuditEvent> {
  return { items, total: items.length, page: 1, page_size: 20 };
}

function montar(): void {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuditoriaPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

/** La celda «Fecha» de la fila que lleva ese rastro. */
async function fecha(rastro: string): Promise<string> {
  const fila = (await screen.findByText(rastro)).closest("tr");
  expect(fila).not.toBeNull();
  return fila!.querySelectorAll("td")[0].textContent ?? "";
}

describe("AuditoriaPage · columna Fecha", () => {
  it("DATE-01/02 · la fecha sale de event_time y nunca es «Invalid Date» para un instante válido", async () => {
    apiFetch.mockClear();
    apiFetch.mockResolvedValue(sobre([evento(1, TARDE)]));
    montar();
    const texto = await fecha("rastro-1");
    expect(texto).not.toBe("Invalid Date");
    expect(texto).toBe(formatearFecha(TARDE));
  });

  it(`DATE-03/04/05/06/07 · texto exacto bajo la zona del proceso (${ZONA})`, async () => {
    apiFetch.mockClear();
    apiFetch.mockResolvedValue(sobre([evento(1, TARDE), evento(2, MEDIANOCHE)]));
    montar();
    const tarde = await fecha("rastro-1");
    const medianoche = await fecha("rastro-2");
    // Siempre: la convención del producto, con hora y segundos, y el mismo instante.
    expect(tarde).toBe(formatearFecha(TARDE));
    expect(medianoche).toBe(formatearFecha(MEDIANOCHE));
    expect(tarde).toMatch(/\d{1,2}\/\d{1,2}\/\d{4}, \d{1,2}:\d{2}:\d{2}/);
    // Y bajo las tres zonas de la matriz, el literal medido.
    const literal = ESPERADO[ZONA];
    if (literal) {
      expect(tarde).toBe(literal[TARDE]);
      expect(medianoche).toBe(literal[MEDIANOCHE]);
    }
  });

  it("DATE-08 · cada fila muestra su propio instante", async () => {
    apiFetch.mockClear();
    apiFetch.mockResolvedValue(sobre([evento(1, TARDE), evento(2, MEDIANOCHE)]));
    montar();
    const uno = await fecha("rastro-1");
    const dos = await fecha("rastro-2");
    expect(uno).not.toBe(dos);
    expect(Date.parse(TARDE)).toBeLessThan(Date.parse(MEDIANOCHE));
  });

  it("DATE-13 · un valor que no es un instante no se disfraza de «ahora» ni de «—»", async () => {
    apiFetch.mockClear();
    apiFetch.mockResolvedValue(sobre([evento(1, "no-es-una-fecha")]));
    montar();
    const texto = await fecha("rastro-1");
    expect(texto).toBe("Invalid Date"); // lo que la convención devuelve; no se normaliza
    expect(texto).not.toBe(formatearFecha(new Date().toISOString()));
    expect(texto).not.toBe(formatearFecha(null));
  });

  it("DATE-11/12 · el tipo AuditEvent exige event_time y no conoce created_at", () => {
    expectTypeOf<AuditEvent>().toHaveProperty("event_time");
    expectTypeOf<AuditEvent["event_time"]>().toEqualTypeOf<string>();
    expectTypeOf<AuditEvent>().not.toHaveProperty("created_at");
  });
});
