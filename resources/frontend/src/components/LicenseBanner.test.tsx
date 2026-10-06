/**
 * F-06/F-07 · El aviso de licencia lo ve todo usuario; el enlace a «Mi licencia», solo quien
 * puede entrar (FR-010-114). En FULL_ACCESS no hay aviso.
 */
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

let permisos = new Set<string>();
let licencia: { mode: string | null; status: { mode: string; license_url: string } | null } = { mode: null, status: null };

vi.mock("@/app/contexts/AuthContext", () => ({
  useAuth: () => ({ hasPermission: (permiso: string) => permisos.has(permiso) }),
}));

vi.mock("@/app/contexts/LicenseContext", async (original) => ({
  ...(await original<typeof import("@/app/contexts/LicenseContext")>()),
  useLicense: () => ({ ...licencia, loading: false, blocksWrite: false, refresh: async () => undefined }),
}));

const { LicenseBanner } = await import("./LicenseBanner");

function montar(): void {
  render(
    <MemoryRouter>
      <LicenseBanner />
    </MemoryRouter>,
  );
}

describe("LicenseBanner · aviso y enlace de licencia", () => {
  beforeEach(() => {
    permisos = new Set<string>();
    licencia = { mode: null, status: null };
  });

  it("F-06 · con license:view el aviso lleva el enlace a Mi licencia", () => {
    permisos = new Set(["license:view"]);
    licencia = { mode: "RENEWAL_NOTICE", status: { mode: "RENEWAL_NOTICE", license_url: "/mi-licencia" } };
    montar();
    expect(screen.getByRole("status")).toBeTruthy();
    expect(screen.getByText(/requiere renovación/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "Ver Mi licencia" }).getAttribute("href")).toBe("/mi-licencia");
  });

  it("F-06b · sin license:view el aviso se ve, pero sin enlace", () => {
    licencia = { mode: "READ_ONLY", status: { mode: "READ_ONLY", license_url: "/mi-licencia" } };
    montar();
    expect(screen.getByRole("status")).toBeTruthy();
    expect(screen.getByText(/solo consulta/)).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Ver Mi licencia" })).toBeNull();
  });

  it("F-07 · en FULL_ACCESS o sin modo no hay aviso", () => {
    permisos = new Set(["license:view"]);
    licencia = { mode: "FULL_ACCESS", status: { mode: "FULL_ACCESS", license_url: "/mi-licencia" } };
    montar();
    expect(screen.queryByRole("status")).toBeNull();
    licencia = { mode: null, status: null };
    montar();
    expect(screen.queryByRole("status")).toBeNull();
  });
});
