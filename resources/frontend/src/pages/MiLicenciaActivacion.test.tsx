/**
 * LICACT-D3 ± «Activar licencia»: carga del paquete firmado, vista previa,
 * confirmación y refresco sin recarga. El backend es la única autoridad
 * para verificar la firma; la pantalla no la reconstruye ni la expone.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
if (typeof Blob.prototype.text !== "function") {
  Object.defineProperty(Blob.prototype, "text", {
    configurable: true,
    value: function text(this: Blob): Promise<string> {
      return new Promise<string>((resolve, reject) => {
        const lector = new FileReader();
        lector.onload = () => resolve(String(lector.result));
        lector.onerror = () => reject(lector.error);
        lector.readAsText(this);
      });
    },
  });
}

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { MockInstance } from "vitest";

import { ApiError } from "@/api/client";
import type { LicenseStatus } from "@/api/types";
import { mensajeDeErrorDeActivacion } from "@/lib/paquete-de-licencia";

const apiFetch = vi.fn();
const notify = vi.fn();
const refresh = vi.fn().mockResolvedValue(undefined);

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

let permisos = new Set(["license:view", "license:create"]);

vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({
    estado: "LISTA",
    tiene: (c: string) => permisos.has(c),
    puede: () => true,
    motivo: () => null,
    motivoDeCapacidad: () => null,
  }),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify }),
}));

vi.mock("@/app/contexts/LicenseContext", async (original) => ({
  ...(await original<typeof import("@/app/contexts/LicenseContext")>()),
  useLicense: () => ({
    refresh,
    status: null,
    mode: null,
    loading: false,
    blocksWrite: false,
  }),
}));

const { MiLicenciaPage } = await import("./MiLicenciaPage");

const DETALLE_BASE: LicenseStatus = {
  installation_id: "KTL-TEST-INSTALACION-0001",
  activated: true,
  mode: "FULL_ACCESS",
  period_start: "2026-04-01T00:00:00+00:00",
  period_end: "2027-03-31T23:59:59+00:00",
  read_only_start: null,
  entitlements: {},
  minimum_version: "1.0.0",
  license_url: "/mi-licencia",
};

const PAQUETE = {
  payload: {
    issuer: "QA",
    license_id: "LIC-TEST-0001",
    installation_id: "KTL-TEST-INSTALACION-0001",
    customer_id: "C-TEST",
    contract_id: "K-TEST",
    period_start: "2026-04-01T00:00:00-04:00",
    period_end: "2027-03-31T23:59:59-04:00",
    entitlements: { companies: 3, users: 25, modules: ["gobierno"] },
    minimum_version: "1.0.0",
    kid: "kontrol-lic-2026-01",
    revision: 2,
  },
  signature_hex: "ab".repeat(64),
};

function configurarDetalle(mode: LicenseStatus["mode"]): LicenseStatus {
  return { ...DETALLE_BASE, mode };
}

function renderPagina(): { cliente: QueryClient; invalida: MockInstance } {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const invalida = vi.spyOn(cliente, "invalidateQueries");
  render(
    <QueryClientProvider client={cliente}>
      <MemoryRouter>
        <MiLicenciaPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return { cliente, invalida };
}

async function subirPaquete(texto?: string, opciones?: { name?: string; type?: string }) {
  const user = userEvent.setup({ applyAccept: false });
  const archivo = new File(
    [texto ?? JSON.stringify(PAQUETE)],
    opciones?.name ?? "licencia.json",
    { type: opciones?.type ?? "application/json" },
  );
  await user.upload(screen.getByLabelText("Archivo de licencia firmado"), archivo);
  return user;
}

beforeEach(() => {
  apiFetch.mockReset();
  notify.mockReset();
  refresh.mockClear();
  apiFetch.mockImplementation(async (ruta: string) => {
    if (ruta === "/license/detail") {
      return configurarDetalle("PENDING");
    }
    if (ruta === "/license/activate") {
      return {
        ok: true,
        license_id: "LIC-TEST-0001",
        mode: "FULL_ACCESS",
      };
    }
    return undefined;
  });
});

afterEach(() => {
  permisos = new Set(["license:view", "license:create"]);
});

describe("Activar licencia · visibilidad por modo", () => {
  it.each([
    ["PENDING", "Activar licencia", "Seleccionar archivo de licencia", "Validar y activar licencia"],
    ["FULL_ACCESS", "Actualizar o reemplazar licencia", "Seleccionar nueva licencia", "Validar y aplicar licencia"],
    ["RENEWAL_NOTICE", "Renovar licencia", "Seleccionar licencia renovada", "Validar y aplicar licencia"],
    ["CRITICAL_RENEWAL_NOTICE", "Renovar licencia", "Seleccionar licencia renovada", "Validar y aplicar licencia"],
    ["READ_ONLY", "Reactivar licencia", "Seleccionar licencia vigente", "Validar y aplicar licencia"],
    ["SECURITY_SUSPENSION", "Restablecer licencia válida", "Seleccionar licencia válida", "Validar y aplicar licencia"],
  ] as const)("LICUX-01..06 en %s muestra el control con su título", async (mode, titulo, seleccionar, aplicar) => {
    apiFetch.mockImplementation(async (ruta: string) => {
      if (ruta === "/license/detail") {
        return configurarDetalle(mode);
      }
      return undefined;
    });
    renderPagina();
    expect(
      await screen.findByRole("heading", { level: 2, name: titulo }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: seleccionar })).toBeVisible();
    expect(screen.getByRole("button", { name: aplicar })).toBeDisabled();
    expect(screen.getByLabelText("Archivo de licencia firmado")).toBeInTheDocument();
    expect(screen.getByText("Ningún archivo seleccionado")).toBeInTheDocument();
  });

  it("LICUX-07 FULL_ACCESS ofrece reemplazar la licencia (defecto observado por la dueña)", async () => {
    apiFetch.mockImplementation(async (ruta: string) => {
      if (ruta === "/license/detail") {
        return configurarDetalle("FULL_ACCESS");
      }
      return undefined;
    });
    renderPagina();
    expect(
      await screen.findByRole("heading", { level: 2, name: "Actualizar o reemplazar licencia" }),
    ).toBeInTheDocument();
    await subirPaquete();
    expect(await screen.findByText("LIC-TEST-0001")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Validar y aplicar licencia" })).toBeEnabled();
    expect(screen.getByText("Archivo seleccionado: licencia.json")).toBeInTheDocument();
  });

  it("LICACT-06 sin license:create explica el permiso y no ofrece el control", async () => {
    for (const mode of ["PENDING", "FULL_ACCESS"] as const) {
      apiFetch.mockImplementation(async (ruta: string) => {
        if (ruta === "/license/detail") {
          return configurarDetalle(mode);
        }
        return undefined;
      });
      permisos = new Set(["license:view"]);
      renderPagina();
      expect(
        await screen.findByRole("heading", { level: 2, name: "Activar o actualizar licencia" }),
      ).toBeInTheDocument();
      expect(
        screen.getByText("No tiene permiso para activar o reemplazar licencias."),
      ).toBeInTheDocument();
      expect(
        screen.getByText("Se requiere license:create. Solicítelo al administrador de KONTROL."),
      ).toBeInTheDocument();
      expect(screen.queryByLabelText("Archivo de licencia firmado")).toBeNull();
      expect(screen.queryByRole("button", { name: "Seleccionar archivo de licencia" })).toBeNull();
      expect(screen.queryByRole("button", { name: "Validar y activar licencia" })).toBeNull();
      expect(
        apiFetch.mock.calls.some(([ruta]) => ruta === "/license/activate"),
      ).toBe(false);
      cleanup();
    }
  });
});

describe("Activar licencia · carga y vista previa", () => {
  it("LICACT-07 un .json válido muestra la vista previa", async () => {
    renderPagina();
    await screen.findByRole("heading", { name: "Activar licencia" });
    await subirPaquete();
    expect(await screen.findByText("LIC-TEST-0001")).toBeInTheDocument();
    expect(screen.getByText("kontrol-lic-2026-01")).toBeInTheDocument();
    expect(screen.getByText("KONTROL Gobierno")).toBeInTheDocument();
    expect(screen.getByText("Gobierno")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "Vista previa de la licencia" })).toBeInTheDocument();
    expect(screen.getByText(/Instalación verificada/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Validar y activar licencia" })).toBeEnabled();
  });

  it("LICACT-08 rechaza extensión distinta", async () => {
    renderPagina();
    await screen.findByRole("heading", { name: "Activar licencia" });
    await subirPaquete(undefined, { name: "license.txt" });
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "extensión .json. (INVALID_LICENSE_PACKAGE)",
    );
    expect(screen.getByRole("button", { name: "Validar y activar licencia" })).toBeDisabled();
  });

  it("LICACT-09 rechaza JSON inválido", async () => {
    renderPagina();
    await screen.findByRole("heading", { name: "Activar licencia" });
    await subirPaquete("{no json");
    expect(await screen.findByRole("alert")).toHaveTextContent("JSON válido");
  });

  it("LICACT-10 rechaza raíz arreglo", async () => {
    renderPagina();
    await screen.findByRole("heading", { name: "Activar licencia" });
    await subirPaquete("[]");
    expect(await screen.findByRole("alert")).toHaveTextContent("objeto JSON");
  });

  it("LICACT-11 rechaza payload que no es objeto", async () => {
    renderPagina();
    await screen.findByRole("heading", { name: "Activar licencia" });
    await subirPaquete(JSON.stringify({ payload: "x", signature_hex: "ab" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("payload válido");
  });

  it("LICACT-12 rechaza firma ausente o en blanco", async () => {
    renderPagina();
    await screen.findByRole("heading", { name: "Activar licencia" });
    await subirPaquete(JSON.stringify({ payload: PAQUETE.payload }));
    expect(await screen.findByRole("alert")).toHaveTextContent("signature_hex");
    await subirPaquete(JSON.stringify({ payload: PAQUETE.payload, signature_hex: "   " }));
    expect(await screen.findByRole("alert")).toHaveTextContent("signature_hex");
  });

  it("LICACT-13 la vista previa no expone la firma ni el JSON", async () => {
    renderPagina();
    await screen.findByRole("heading", { name: "Activar licencia" });
    await subirPaquete();
    await screen.findByText("LIC-TEST-0001");
    expect(document.body.textContent).not.toContain("ab".repeat(64));
    expect(document.body.textContent).not.toContain("signature_hex");
  });

  it("LICACT-14 rechaza claves privadas sin exponerlas", async () => {
    renderPagina();
    await screen.findByRole("heading", { name: "Activar licencia" });
    const MARCA = "-----BEGIN " + "PRIV" + "ATE KEY-----";
    await subirPaquete(`${MARCA}\ncontenido`);
    expect(await screen.findByRole("alert")).toHaveTextContent("clave privada");
    expect(document.body.textContent).not.toContain(MARCA);
    expect(
      apiFetch.mock.calls.some(([ruta]) => ruta === "/license/activate"),
    ).toBe(false);
  });
});

describe("Activar licencia · confirmación", () => {
  it("LICACT-15 el botón abre el diálogo de confirmación sin activar", async () => {
    renderPagina();
    await screen.findByRole("heading", { name: "Activar licencia" });
    await subirPaquete();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Validar y activar licencia" }));
    expect(await screen.findByText(/quedará vinculada/)).toBeInTheDocument();
    expect(
      apiFetch.mock.calls.some(([ruta]) => ruta === "/license/activate"),
    ).toBe(false);
  });

  it("LICACT-16 cancelar cierra sin activar", async () => {
    renderPagina();
    await screen.findByRole("heading", { name: "Activar licencia" });
    await subirPaquete();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Validar y activar licencia" }));
    await screen.findByText(/quedará vinculada/);
    await user.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(
      apiFetch.mock.calls.some(([ruta]) => ruta === "/license/activate"),
    ).toBe(false);
  });

  it("LICACT-17 confirmar activa con el payload intacto y solo dos claves", async () => {
    renderPagina();
    await screen.findByRole("heading", { name: "Activar licencia" });
    await subirPaquete();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Validar y activar licencia" }));
    await screen.findByText(/quedará vinculada/);
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Validar y activar licencia" }));

    await waitFor(() => {
      expect(
        apiFetch.mock.calls.filter(([ruta]) => ruta === "/license/activate"),
      ).toHaveLength(1);
    });
    const llamada = apiFetch.mock.calls.find(([ruta]) => ruta === "/license/activate");
    expect(llamada).toBeTruthy();
    const [ruta, init] = llamada as [string, { method: string; body: Record<string, unknown> }];
    expect(ruta).toBe("/license/activate");
    expect(init.method).toBe("POST");
    expect(Object.keys(init.body)).toEqual(["payload", "signature_hex"]);
    expect(init.body.payload).toEqual(PAQUETE.payload);
    expect(Object.keys(init.body.payload as Record<string, unknown>)).toEqual(
      Object.keys(PAQUETE.payload),
    );
  });

  it("LICACT-18 un POST pendiente bloquea la UI y no duplica llamadas", async () => {
    let resolver: (v: unknown) => void = () => undefined;
    apiFetch.mockImplementation(async (ruta: string) => {
      if (ruta === "/license/detail") {
        return configurarDetalle("PENDING");
      }
      if (ruta === "/license/activate") {
        return new Promise((resolve) => {
          resolver = resolve;
        });
      }
      return undefined;
    });
    renderPagina();
    await screen.findByRole("heading", { name: "Activar licencia" });
    await subirPaquete();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Validar y activar licencia" }));
    await screen.findByText(/quedará vinculada/);
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Validar y activar licencia" }));

    expect(await screen.findByRole("button", { name: "Validando…" })).toBeDisabled();
    expect(screen.getByLabelText("Archivo de licencia firmado")).toBeDisabled();
    expect(
      apiFetch.mock.calls.filter(([ruta]) => ruta === "/license/activate"),
    ).toHaveLength(1);

    await user.click(screen.getByRole("button", { name: "Validando…" }));
    expect(
      apiFetch.mock.calls.filter(([ruta]) => ruta === "/license/activate"),
    ).toHaveLength(1);

    resolver({ ok: true, license_id: "LIC-TEST-0001", mode: "FULL_ACCESS" });
  });

  it("LICACT-19 éxito notifica y limpia el archivo", async () => {
    renderPagina();
    await screen.findByRole("heading", { name: "Activar licencia" });
    await subirPaquete();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Validar y activar licencia" }));
    await screen.findByText(/quedará vinculada/);
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Validar y activar licencia" }));

    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "success",
          title: "Licencia activada correctamente",
          description: expect.stringContaining("LIC-TEST-0001"),
        }),
      );
    });
    expect(notify.mock.calls[0]?.[0]?.description).toBe("Perfil: KONTROL Gobierno · Estado: Acceso completo · Licencia LIC-TEST-0001");
    expect(screen.getByRole("status")).toHaveTextContent("Licencia activada correctamente");
    expect(screen.queryByText("LIC-TEST-0001")).toBeNull();
    expect(screen.getByLabelText("Archivo de licencia firmado")).toHaveValue("");
  });

  it("LICACT-20/22 éxito invalida las consultas de licencia", async () => {
    const { invalida } = renderPagina();
    await screen.findByRole("heading", { name: "Activar licencia" });
    await subirPaquete();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Validar y activar licencia" }));
    await screen.findByText(/quedará vinculada/);
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Validar y activar licencia" }));

    await waitFor(() => {
      expect(invalida).toHaveBeenCalledWith({ queryKey: ["license"] });
      expect(invalida).toHaveBeenCalledWith({ queryKey: ["licencia", "modulo", "gobierno"] });
    });
  });

  it("LICACT-21 éxito refresca el contexto de licencia", async () => {
    renderPagina();
    await screen.findByRole("heading", { name: "Activar licencia" });
    await subirPaquete();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Validar y activar licencia" }));
    await screen.findByText(/quedará vinculada/);
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Validar y activar licencia" }));

    await waitFor(() => expect(refresh).toHaveBeenCalledTimes(1));
  });
});

describe("Activar licencia · reintento de reauth", () => {
  it("LICACT-23..25 la pantalla delega el reintento en el cliente canónico y no reabre el diálogo", async () => {
    const usuario = userEvent.setup();
    renderPagina();
    await screen.findByRole("heading", { name: "Activar licencia" });
    await subirPaquete(undefined, undefined);
    await usuario.click(screen.getByRole("button", { name: "Validar y activar licencia" }));
    await screen.findByText(/quedará vinculada/);
    await usuario.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Validar y activar licencia" }));

    await waitFor(() => {
      expect(
        apiFetch.mock.calls.filter(([ruta]) => ruta === "/license/activate"),
      ).toHaveLength(1);
    });
    expect(screen.queryByText(/quedará vinculada/)).toBeNull();
    expect(
      apiFetch.mock.calls.some(([ruta]) => ruta === "/auth/reauth"),
    ).toBe(false);
  });

  it("LICACT-26 reauth cancelada muestra aviso y no refresca", async () => {
    apiFetch.mockImplementation(async (ruta: string) => {
      if (ruta === "/license/detail") {
        return configurarDetalle("PENDING");
      }
      if (ruta === "/license/activate") {
        throw new ApiError(403, { code: "REAUTH_REQUIRED" });
      }
      return undefined;
    });
    renderPagina();
    await screen.findByRole("heading", { name: "Activar licencia" });
    await subirPaquete();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Validar y activar licencia" }));
    await screen.findByText(/quedará vinculada/);
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Validar y activar licencia" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No se confirmó su identidad; la licencia no se activó. (REAUTH_REQUIRED)",
    );
    expect(refresh).not.toHaveBeenCalled();
  });
});

describe("Activar licencia · seguridad", () => {
  it("LICACT-27 no usa almacenamiento ni registra datos del paquete", async () => {
    const setItem = vi.spyOn(Storage.prototype, "setItem");
    let openSpy: MockInstance | null = null;
    if (typeof indexedDB !== "undefined") {
      openSpy = vi.spyOn(indexedDB, "open");
    }
    const log = vi.spyOn(console, "log").mockImplementation(() => undefined);
    const info = vi.spyOn(console, "info").mockImplementation(() => undefined);
    const debug = vi.spyOn(console, "debug").mockImplementation(() => undefined);
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const errorLog = vi.spyOn(console, "error").mockImplementation(() => undefined);

    renderPagina();
    await screen.findByRole("heading", { name: "Activar licencia" });
    await subirPaquete();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Validar y activar licencia" }));
    await screen.findByText(/quedará vinculada/);
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Validar y activar licencia" }));

    await waitFor(() => expect(refresh).toHaveBeenCalledTimes(1));
    expect(setItem).not.toHaveBeenCalled();
    if (openSpy) {
      expect(openSpy).not.toHaveBeenCalled();
    }
    const todas = [log, info, debug, warn, errorLog];
    for (const espia of todas) {
      for (const args of espia.mock.calls) {
        const texto = args.map((a) => String(a)).join(" ");
        expect(texto).not.toContain("ab".repeat(64));
        expect(texto).not.toContain("LIC-TEST-0001");
      }
    }
  });
});

describe("Activar licencia · errores del servidor", () => {
  it.each([
    ["401", 401, "UNAUTHORIZED"],
    ["403", 403, "PERMISSION_DENIED"],
    ["423 signature", 423, "LICENSE_SIGNATURE_INVALID"],
    ["423 kid unknown", 423, "LICENSE_SIGNING_KID_UNKNOWN"],
    ["423 kid missing", 423, "LICENSE_SIGNING_KID_MISSING"],
    ["423 mismatch", 423, "LICENSE_INSTALLATION_MISMATCH"],
    ["423 downgrade", 423, "LICENSE_PERIOD_DOWNGRADE"],
    ["423 conflict", 423, "LICENSE_PERIOD_CONFLICT"],
    ["423 revision", 423, "LICENSE_INVALID_REVISION"],
    ["423 revision downgrade", 423, "LICENSE_REVISION_DOWNGRADE"],
    ["423 revision conflict", 423, "LICENSE_REVISION_CONFLICT"],
    ["423 legacy", 423, "LICENSE_LEGACY_REISSUE_REQUIRES_REVISION"],
    ["423 legacy after", 423, "LICENSE_LEGACY_AFTER_REVISION"],
    ["423 min", 423, "LICENSE_MINIMUM_VERSION_INCOMPATIBLE"],
    ["red", null, null],
    ["500", 500, "INTERNAL_ERROR"],
  ] as const)(
    "muestra el mensaje mapeado para %s y conserva el paquete",
    async (_nombre, status, code) => {
      apiFetch.mockImplementation(async (ruta: string) => {
        if (ruta === "/license/detail") {
          return configurarDetalle("PENDING");
        }
        if (ruta === "/license/activate") {
          if (status === null) {
            throw new TypeError("Failed to fetch");
          }
          throw new ApiError(status, { code, message: "x" });
        }
        return undefined;
      });
      renderPagina();
      await screen.findByRole("heading", { name: "Activar licencia" });
      await subirPaquete();
      const user = userEvent.setup();
      await user.click(screen.getByRole("button", { name: "Validar y activar licencia" }));
      await screen.findByText(/quedará vinculada/);
      await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Validar y activar licencia" }));

      const esperado = status === null
        ? mensajeDeErrorDeActivacion(new TypeError("Failed to fetch"))
        : mensajeDeErrorDeActivacion(new ApiError(status, { code, message: "x" }));
      expect(await screen.findByRole("alert")).toHaveTextContent(esperado);
      expect(screen.getByText("LIC-TEST-0001")).toBeInTheDocument();
    },
  );
});

describe("Activar licencia · aviso de instalación distinta", () => {
  it("advierte si el paquete fue emitido para otra instalación", async () => {
    renderPagina();
    await screen.findByRole("heading", { name: "Activar licencia" });
    const otro = {
      ...PAQUETE,
      payload: { ...PAQUETE.payload, installation_id: "OTRA-INSTALACION" },
    };
    await subirPaquete(JSON.stringify(otro));
    expect(await screen.findByText(/Esta licencia fue emitida para otra instalación\. El servidor la rechazará\./)).toBeInTheDocument();
    expect(screen.queryByText(/Instalación verificada/)).toBeNull();
    expect(screen.getByRole("button", { name: "Validar y activar licencia" })).toBeEnabled();
  });
});
