/**
 * C04-T11 · la columna «Fecha» del timeline de auditoría usa el formateador
 * central (ADR-020, regla DISPLAY): hora de Caracas, no el ISO crudo.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";

import type { AuditTimelineItem } from "@/api/types";

const apiFetch = vi.fn();
vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

const { ReportesAuditoriaPage } = await import("./ReportesAuditoriaPage");
const { formatearFecha } = await import("@/i18n");

const EVENT_TIME_ISO = "2026-03-10T04:00:00+00:00";

function item(): AuditTimelineItem {
  return {
    id: "ev-1",
    event_time: EVENT_TIME_ISO,
    action: "LOGIN_SUCCESS",
    entity_type: "Probe",
    entity_id: "probe-1",
    user_id: "usuario-1",
    source: "QA",
    reason: null,
  } as AuditTimelineItem;
}

function montar(): void {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, throwOnError: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ReportesAuditoriaPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ReportesAuditoriaPage · columna Fecha", () => {
  it("pinta event_time con el formateador central y no el ISO crudo", async () => {
    apiFetch.mockClear();
    apiFetch.mockResolvedValue({ items: [item()] });
    montar();
    expect(await screen.findByText(formatearFecha(EVENT_TIME_ISO))).toBeInTheDocument();
    expect(screen.queryByText(EVENT_TIME_ISO)).not.toBeInTheDocument();
  });
});
