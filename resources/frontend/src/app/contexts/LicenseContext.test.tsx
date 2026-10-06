/**
 * F-01/F-02 · El contexto de licencia consume el contrato mínimo pre-sesión (FR-010-112):
 * `mode` y `blocksWrite` salen de `{ mode, license_url }`; ante error no decide nada (status null).
 */
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiFetch = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

const { LicenseProvider, useLicense, PERMISO_DE_LICENCIA } = await import("./LicenseContext");

function Sonda(): React.JSX.Element {
  const { status, mode, loading, blocksWrite } = useLicense();
  return (
    <p data-testid="sonda">
      {loading ? "cargando" : "listo"}|{mode ?? "sin-modo"}|{blocksWrite ? "bloquea" : "libre"}|{status === null ? "null" : Object.keys(status).sort().join(",")}
    </p>
  );
}

describe("LicenseContext · contrato pre-sesión", () => {
  beforeEach(() => {
    apiFetch.mockReset();
  });

  it("F-01 · con { mode, license_url } expone mode y blocksWrite", async () => {
    apiFetch.mockResolvedValue({ mode: "READ_ONLY", license_url: "/mi-licencia" });
    render(
      <LicenseProvider>
        <Sonda />
      </LicenseProvider>,
    );
    expect(await screen.findByText("listo|READ_ONLY|bloquea|license_url,mode")).toBeTruthy();
    expect(apiFetch).toHaveBeenCalledWith("/license/status");
  });

  it("F-01b · FULL_ACCESS no bloquea", async () => {
    apiFetch.mockResolvedValue({ mode: "FULL_ACCESS", license_url: "/mi-licencia" });
    render(
      <LicenseProvider>
        <Sonda />
      </LicenseProvider>,
    );
    expect(await screen.findByText("listo|FULL_ACCESS|libre|license_url,mode")).toBeTruthy();
  });

  it("F-02 · si la petición falla, status null, sin modo, sin bloquear y sin lanzar", async () => {
    apiFetch.mockRejectedValue(new Error("red"));
    render(
      <LicenseProvider>
        <Sonda />
      </LicenseProvider>,
    );
    expect(await screen.findByText("listo|sin-modo|libre|null")).toBeTruthy();
  });

  it("F-02b · el permiso del detalle es license:view", () => {
    expect(PERMISO_DE_LICENCIA).toBe("license:view");
  });
});
