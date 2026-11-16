/**
 * F-03/F-04 · «Mi licencia» exige `license:view` antes de pedir nada (FR-010-113).
 * El backend es la autoridad —`GET /license/detail` responde 401/403—; aquí se comprueba que la
 * pantalla no pide ni pinta el detalle a quien no puede verlo, y que con permiso lo pide y lo pinta.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Mock, MockInstance } from "vitest";

import { ApiError } from "@/api/client";
import type { InstallationRequest, LicenseStatus } from "@/api/types";
import {
  SolicitudInvalidaError,
  nombreDeArchivoDeSolicitud,
  validarSolicitud,
} from "@/lib/solicitud-de-activacion";

const apiFetch = vi.fn();
const notify = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

let permisos = new Set(["license:view"]);

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
  useLicense: () => ({ refresh: vi.fn().mockResolvedValue(undefined), status: null, mode: null, loading: false, blocksWrite: false }),
}));

const { MiLicenciaPage } = await import("./MiLicenciaPage");

const DETALLE: LicenseStatus = {
  installation_id: "KTL-XX-0000-TEST",
  activated: true,
  mode: "FULL_ACCESS",
  period_start: "2026-04-01T00:00:00+00:00",
  period_end: "2027-03-31T23:59:59+00:00",
  read_only_start: "2027-05-01T00:00:00+00:00",
  entitlements: {},
  minimum_version: "1.0.0",
  license_url: "/mi-licencia",
};

const DETALLE_PENDIENTE: LicenseStatus = {
  ...DETALLE,
  mode: "PENDING",
};

const SOLICITUD: InstallationRequest = {
  installation_id: "KTL-VE-TEST-0001",
  public_key:
    "-----BEGIN PUBLIC KEY-----\nMFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEprueba\n-----END PUBLIC KEY-----",
  version: "test",
  nonce: "nonce-test",
  requested_at: "2026-11-16T00:00:00+00:00",
};

const MENSAJE_INVALID = "La solicitud de activación recibida no es válida (INVALID_INSTALLATION_REQUEST).";
const MENSAJE_SESION = "La sesión venció. Inicie sesión nuevamente para obtener la solicitud de activación.";
const MENSAJE_PERMISO = "No tiene permiso para consultar la solicitud de activación. Se requiere license:view.";
const MENSAJE_RED = "No fue posible conectar con KONTROL para obtener la solicitud de activación.";
const MENSAJE_PORTAPAPELES = "No fue posible copiar la solicitud al portapapeles.";

async function esperarNotificacion(tipo: "success" | "error", texto: string): Promise<void> {
  await waitFor(() =>
    expect(notify).toHaveBeenCalledWith(
      expect.objectContaining(
        tipo === "success" ? { type: tipo, title: texto } : { type: tipo, description: texto },
      ),
    ),
  );
}

function montar() {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter>
        <MiLicenciaPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function leerBlob(b: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const lector = new FileReader();
    lector.onload = () => resolve(String(lector.result));
    lector.onerror = () => reject(lector.error);
    lector.readAsText(b);
  });
}

function configurarMocksDeDescarga(nombres: string[]) {
  Object.defineProperty(URL, "createObjectURL", {
    value: vi.fn(() => "blob:prueba"),
    configurable: true,
    writable: true,
  });
  Object.defineProperty(URL, "revokeObjectURL", {
    value: vi.fn(),
    configurable: true,
    writable: true,
  });
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (
    this: HTMLAnchorElement,
  ) {
    nombres.push(this.download);
  });
}

function configurarPortapapeles(writeText: Mock<(texto: string) => Promise<void>>) {
  Object.defineProperty(navigator, "clipboard", {
    value: { writeText },
    configurable: true,
  });
}

describe("MiLicenciaPage", () => {
  beforeEach(() => {
    apiFetch.mockReset();
    notify.mockReset();
    permisos = new Set(["license:view"]);
  });

  it("F-03 · sin license:view: acceso prohibido y ninguna petición", async () => {
    permisos = new Set(["organization:view"]);
    montar();
    expect(await screen.findByRole("heading", { level: 1, name: "Acceso prohibido" })).toBeTruthy();
    expect(screen.queryByRole("heading", { level: 1, name: "Mi licencia" })).toBeNull();
    expect(screen.queryByText("KTL-XX-0000-TEST")).toBeNull();
    expect(apiFetch.mock.calls.some(([ruta]) => typeof ruta === "string" && ruta.startsWith("/license"))).toBe(false);
  });

  it("F-04 · con license:view pide /license/detail y pinta identificador, modo y fechas", async () => {
    apiFetch.mockResolvedValue(DETALLE);
    montar();
    expect(await screen.findByText("KTL-XX-0000-TEST")).toBeTruthy();
    expect(screen.getByRole("heading", { level: 1, name: "Mi licencia" })).toBeTruthy();
    expect(screen.getByText("Acceso completo")).toBeTruthy();
    expect(screen.getByText("FULL_ACCESS")).toBeTruthy();
    for (const etiqueta of ["Estado general", "Perfil de producto", "Estado", "Instalación", "Período pagado", "Solo consulta desde", "Versión mínima", "Módulo Gobierno", "Módulos habilitados"]) {
      expect(screen.getByText(etiqueta)).toBeTruthy();
    }
    expect(apiFetch).toHaveBeenCalledWith("/license/detail");
    expect(apiFetch).not.toHaveBeenCalledWith("/license/status");
    expect(screen.queryByRole("heading", { level: 1, name: "Acceso prohibido" })).toBeNull();
  });

  it("LICUX-08 · perfil KONTROL Gobierno visible en la página", async () => {
    apiFetch.mockImplementation((ruta: string) => {
      if (ruta === "/license/detail") {
        return { ...DETALLE, entitlements: { modules: ["gobierno"] } };
      }
      if (ruta === "/gobierno/modulo") {
        return { habilitado: true, perfil: "GOBIERNO" };
      }
      return undefined;
    });
    montar();
    expect(await screen.findByText("KONTROL Gobierno")).toBeInTheDocument();
    expect(screen.getByText("Habilitado")).toBeInTheDocument();
    expect(screen.getAllByText("Gobierno").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Acceso completo")).toBeInTheDocument();
  });

  it("LICUX-09 · MIXTO lista los módulos firmados con nombre humano", async () => {
    apiFetch.mockImplementation((ruta: string) => {
      if (ruta === "/license/detail") {
        return { ...DETALLE, entitlements: { modules: ["gobierno", "ventas", "tesoreria"] } };
      }
      if (ruta === "/gobierno/modulo") {
        return { habilitado: true, perfil: "MIXTO" };
      }
      return undefined;
    });
    montar();
    expect(await screen.findByText("KONTROL Mixto")).toBeInTheDocument();
    expect(screen.getByText("Ventas")).toBeInTheDocument();
    expect(screen.getByText("Tesorería")).toBeInTheDocument();
  });

  it("LICUX-10 · error de perfil muestra No disponible y nunca Enterprise", async () => {
    apiFetch.mockImplementation((ruta: string) => {
      if (ruta === "/license/detail") {
        return DETALLE;
      }
      if (ruta === "/gobierno/modulo") {
        return Promise.reject(new Error("red"));
      }
      return undefined;
    });
    montar();
    expect(await screen.findByText("No disponible")).toBeInTheDocument();
    expect(screen.queryByText("KONTROL Enterprise")).toBeNull();
  });

  it("LICUX-11 · sin license:create: estado visible y explicación del permiso", async () => {
    permisos = new Set(["license:view"]);
    apiFetch.mockImplementation((ruta: string) => {
      if (ruta === "/license/detail") {
        return DETALLE;
      }
      if (ruta === "/gobierno/modulo") {
        return { habilitado: true, perfil: "GOBIERNO" };
      }
      return undefined;
    });
    montar();
    expect(await screen.findByText("Acceso completo")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Activar o actualizar licencia" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("No tiene permiso para activar o reemplazar licencias."),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("Archivo de licencia firmado")).toBeNull();
  });

  it("LICUX-12 · PENDING: la solicitud y la activación conviven", async () => {
    permisos = new Set(["license:view", "license:create"]);
    apiFetch.mockImplementation((ruta: string) => {
      if (ruta === "/license/detail") {
        return DETALLE_PENDIENTE;
      }
      if (ruta === "/gobierno/modulo") {
        return { habilitado: true, perfil: "GOBIERNO" };
      }
      return undefined;
    });
    montar();
    const solicitud = await screen.findByRole("heading", { name: "Solicitud de activación" });
    const activacion = await screen.findByRole("heading", { name: "Activar licencia" });
    expect(screen.getByRole("button", { name: "Descargar solicitud" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Copiar solicitud" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Seleccionar archivo de licencia" })).toBeInTheDocument();
    expect(solicitud.compareDocumentPosition(activacion) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0);
  });

  it("F-04b · si el detalle falla se muestra el error, no el acceso prohibido", async () => {
    apiFetch.mockRejectedValue(new Error("403"));
    montar();
    expect(await screen.findByText("No fue posible consultar el estado de la licencia.")).toBeTruthy();
    expect(screen.queryByRole("heading", { level: 1, name: "Acceso prohibido" })).toBeNull();
  });

  it("Licencia unitaria · nombreDeArchivoDeSolicitud anula rutas y normaliza identificadores", () => {
    expect(nombreDeArchivoDeSolicitud("KTL-VE-ABC12345-1234")).toBe(
      "kontrol-installation-request-KTL-VE-ABC12345-1234.json",
    );
    expect(nombreDeArchivoDeSolicitud("../../KTL/ABC\\DEF")).toBe(
      "kontrol-installation-request-____KTL_ABC_DEF.json",
    );
    expect(nombreDeArchivoDeSolicitud("")).toBe("kontrol-installation-request-sin-identificador.json");
  });

  it("Licencia unitaria · validarSolicitud rechaza null, arrays y cadenas", () => {
    expect(() => validarSolicitud(null)).toThrow(SolicitudInvalidaError);
    expect(() => validarSolicitud([])).toThrow(SolicitudInvalidaError);
    expect(() => validarSolicitud("x")).toThrow(SolicitudInvalidaError);
  });

  it("Licencia unitaria · validarSolicitud acepta una solicitud válida y devuelve el mismo objeto", () => {
    expect(validarSolicitud(SOLICITUD)).toBe(SOLICITUD);
  });
});

describe("Solicitud de activación", () => {
  let nombres: string[];
  let writeText: Mock<(texto: string) => Promise<void>>;
  let spySetItem: MockInstance<Storage["setItem"]>;

  beforeEach(() => {
    apiFetch.mockReset();
    notify.mockReset();
    permisos = new Set(["license:view"]);
    nombres = [];
    writeText = vi.fn().mockResolvedValue(undefined);
    spySetItem = vi.spyOn(Storage.prototype, "setItem");

    apiFetch.mockImplementation((ruta: string) => {
      if (ruta === "/license/detail") {
        return Promise.resolve(DETALLE_PENDIENTE);
      }
      if (ruta === "/license/installation-request") {
        return Promise.resolve(SOLICITUD);
      }
      return Promise.reject(new Error(`Ruta no mockeada: ${ruta}`));
    });

    configurarMocksDeDescarga(nombres);
    configurarPortapapeles(writeText);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    Object.defineProperty(navigator, "clipboard", {
      value: undefined,
      configurable: true,
    });
  });

  it("LICREQ-01 · PENDING muestra heading h2 y botones de solicitud", async () => {
    montar();
    expect(
      await screen.findByRole("heading", { level: 2, name: "Solicitud de activación" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Descargar solicitud" }),
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: "Copiar solicitud" })).toBeTruthy();
  });

  it("LICREQ-02 · FULL_ACCESS no muestra la sección de solicitud", async () => {
    apiFetch.mockImplementation((ruta: string) => {
      if (ruta === "/license/detail") {
        return Promise.resolve(DETALLE);
      }
      return Promise.reject(new Error(`Ruta no mockeada: ${ruta}`));
    });
    montar();
    expect(await screen.findByText("KTL-XX-0000-TEST")).toBeTruthy();
    expect(
      screen.queryByRole("heading", { level: 2, name: "Solicitud de activación" }),
    ).toBeNull();
    expect(screen.queryByRole("button", { name: "Descargar solicitud" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Copiar solicitud" })).toBeNull();
  });

  it("LICREQ-03 · Descargar llama a /license/installation-request", async () => {
    montar();
    await userEvent.click(await screen.findByRole("button", { name: "Descargar solicitud" }));
    await esperarNotificacion("success", "Solicitud descargada");
    expect(apiFetch).toHaveBeenCalledWith("/license/installation-request");
  });

  it("LICREQ-04 · el Blob es el JSON formateado con todos los campos", async () => {
    montar();
    await userEvent.click(await screen.findByRole("button", { name: "Descargar solicitud" }));
    await esperarNotificacion("success", "Solicitud descargada");

    const createObjectURL = vi.mocked(URL.createObjectURL);
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    const blob = createObjectURL.mock.calls[0][0] as Blob;
    const texto = await leerBlob(blob);
    const esperado = JSON.stringify(SOLICITUD, null, 2) + "\n";
    expect(texto).toBe(esperado);
    expect(texto).toContain(SOLICITUD.version);
    expect(texto).toContain(SOLICITUD.nonce);
    expect(texto).toContain(SOLICITUD.requested_at);
  });

  it("LICREQ-05 · el Blob es application/json y revokeObjectURL se llama con blob:prueba", async () => {
    montar();
    await userEvent.click(await screen.findByRole("button", { name: "Descargar solicitud" }));
    await esperarNotificacion("success", "Solicitud descargada");

    const createObjectURL = vi.mocked(URL.createObjectURL);
    const blob = createObjectURL.mock.calls[0][0] as Blob;
    expect(blob.type).toBe("application/json;charset=utf-8");
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:prueba");
    expect(notify).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "success",
        title: "Solicitud descargada",
      }),
    );
  });

  it("LICREQ-06 · installation_id malicioso genera nombre seguro", async () => {
    const solicitud = { ...SOLICITUD, installation_id: "../../KTL/ABC\\DEF" };
    apiFetch.mockImplementation((ruta: string) => {
      if (ruta === "/license/detail") {
        return Promise.resolve(DETALLE_PENDIENTE);
      }
      if (ruta === "/license/installation-request") {
        return Promise.resolve(solicitud);
      }
      return Promise.reject(new Error(`Ruta no mockeada: ${ruta}`));
    });

    montar();
    await userEvent.click(await screen.findByRole("button", { name: "Descargar solicitud" }));
    await esperarNotificacion("success", "Solicitud descargada");

    expect(nombres[0]).toBe("kontrol-installation-request-____KTL_ABC_DEF.json");
    expect(nombres[0]).not.toContain("/");
    expect(nombres[0]).not.toContain("\\");
    expect(nombres[0]).not.toContain("..");
  });

  it("LICREQ-07 · Copiar escribe el JSON formateado y notifica éxito", async () => {
    montar();
    await userEvent.click(await screen.findByRole("button", { name: "Copiar solicitud" }));
    await esperarNotificacion("success", "Solicitud copiada");

    expect(writeText).toHaveBeenCalledTimes(1);
    expect(writeText).toHaveBeenCalledWith(JSON.stringify(SOLICITUD, null, 2) + "\n");
    expect(notify).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "success",
        title: "Solicitud copiada",
      }),
    );
  });

  it("LICREQ-08 · durante la descarga ambos botones están disabled y luego se habilitan", async () => {
    let resolver!: (v: unknown) => void;
    const pendiente = new Promise((resolve) => {
      resolver = resolve;
    });
    apiFetch.mockImplementation((ruta: string) => {
      if (ruta === "/license/detail") {
        return Promise.resolve(DETALLE_PENDIENTE);
      }
      if (ruta === "/license/installation-request") {
        return pendiente;
      }
      return Promise.reject(new Error(`Ruta no mockeada: ${ruta}`));
    });

    montar();
    const botonDescarga = await screen.findByRole("button", { name: "Descargar solicitud" });
    await userEvent.click(botonDescarga);

    const botonDescargando = screen.getByRole("button", { name: "Descargando…" });
    expect(botonDescargando.hasAttribute("disabled")).toBe(true);
    expect(botonDescargando.getAttribute("aria-busy")).toBe("true");
    const botonCopiar = screen.getByRole("button", { name: "Copiar solicitud" });
    expect(botonCopiar.hasAttribute("disabled")).toBe(true);

    resolver(SOLICITUD);
    await esperarNotificacion("success", "Solicitud descargada");
    await waitFor(() => {
      const botonCopiarTrasResolver = screen.getByRole("button", { name: "Copiar solicitud" });
      expect(botonCopiarTrasResolver.hasAttribute("disabled")).toBe(false);
    });
    expect(screen.queryByRole("button", { name: "Descargando…" })).toBeNull();
  });

  it("LICREQ-09 · durante la copia ambos botones están disabled y luego se habilitan", async () => {
    let resolver!: (v: unknown) => void;
    const pendiente = new Promise((resolve) => {
      resolver = resolve;
    });
    apiFetch.mockImplementation((ruta: string) => {
      if (ruta === "/license/detail") {
        return Promise.resolve(DETALLE_PENDIENTE);
      }
      if (ruta === "/license/installation-request") {
        return pendiente;
      }
      return Promise.reject(new Error(`Ruta no mockeada: ${ruta}`));
    });

    montar();
    const botonCopiar = await screen.findByRole("button", { name: "Copiar solicitud" });
    await userEvent.click(botonCopiar);

    const botonCopiando = screen.getByRole("button", { name: "Copiando…" });
    expect(botonCopiando.hasAttribute("disabled")).toBe(true);
    expect(botonCopiando.getAttribute("aria-busy")).toBe("true");
    const botonDescarga = screen.getByRole("button", { name: "Descargar solicitud" });
    expect(botonDescarga.hasAttribute("disabled")).toBe(true);

    resolver(SOLICITUD);
    await esperarNotificacion("success", "Solicitud copiada");
    await waitFor(() => {
      const botonDescargaTrasResolver = screen.getByRole("button", { name: "Descargar solicitud" });
      expect(botonDescargaTrasResolver.hasAttribute("disabled")).toBe(false);
    });
    expect(screen.queryByRole("button", { name: "Copiando…" })).toBeNull();
  });

  it("LICREQ-10 · instalación sin identification_id notifica INVALID_INSTALLATION_REQUEST", async () => {
    const invalida = { ...SOLICITUD, installation_id: undefined };
    apiFetch.mockImplementation((ruta: string) => {
      if (ruta === "/license/detail") {
        return Promise.resolve(DETALLE_PENDIENTE);
      }
      if (ruta === "/license/installation-request") {
        return Promise.resolve(invalida);
      }
      return Promise.reject(new Error(`Ruta no mockeada: ${ruta}`));
    });

    montar();
    await userEvent.click(await screen.findByRole("button", { name: "Descargar solicitud" }));
    await esperarNotificacion("error", MENSAJE_INVALID);
    expect(URL.createObjectURL).not.toHaveBeenCalled();

    notify.mockClear();
    await userEvent.click(screen.getByRole("button", { name: "Copiar solicitud" }));
    await esperarNotificacion("error", MENSAJE_INVALID);
    expect(writeText).not.toHaveBeenCalled();
  });

  it("LICREQ-11 · public_key en blanco notifica INVALID_INSTALLATION_REQUEST", async () => {
    const invalida = { ...SOLICITUD, public_key: "  " };
    apiFetch.mockImplementation((ruta: string) => {
      if (ruta === "/license/detail") {
        return Promise.resolve(DETALLE_PENDIENTE);
      }
      if (ruta === "/license/installation-request") {
        return Promise.resolve(invalida);
      }
      return Promise.reject(new Error(`Ruta no mockeada: ${ruta}`));
    });

    montar();
    await userEvent.click(await screen.findByRole("button", { name: "Descargar solicitud" }));
    await esperarNotificacion("error", MENSAJE_INVALID);
    expect(URL.createObjectURL).not.toHaveBeenCalled();

    notify.mockClear();
    await userEvent.click(screen.getByRole("button", { name: "Copiar solicitud" }));
    await esperarNotificacion("error", MENSAJE_INVALID);
    expect(writeText).not.toHaveBeenCalled();
  });

  it("LICREQ-12 · 401 notifica el mensaje de sesión exacto", async () => {
    apiFetch.mockImplementation((ruta: string) => {
      if (ruta === "/license/detail") {
        return Promise.resolve(DETALLE_PENDIENTE);
      }
      if (ruta === "/license/installation-request") {
        return Promise.reject(new ApiError(401, { code: "AUTH_REQUIRED", message: "x" }));
      }
      return Promise.reject(new Error(`Ruta no mockeada: ${ruta}`));
    });

    montar();
    await userEvent.click(await screen.findByRole("button", { name: "Descargar solicitud" }));
    await esperarNotificacion("error", MENSAJE_SESION);
    expect(URL.createObjectURL).not.toHaveBeenCalled();
    expect(writeText).not.toHaveBeenCalled();
  });

  it("LICREQ-13 · 403 notifica el mensaje de permiso exacto", async () => {
    apiFetch.mockImplementation((ruta: string) => {
      if (ruta === "/license/detail") {
        return Promise.resolve(DETALLE_PENDIENTE);
      }
      if (ruta === "/license/installation-request") {
        return Promise.reject(new ApiError(403, { code: "PERMISSION_DENIED", message: "x" }));
      }
      return Promise.reject(new Error(`Ruta no mockeada: ${ruta}`));
    });

    montar();
    await userEvent.click(await screen.findByRole("button", { name: "Copiar solicitud" }));
    await esperarNotificacion("error", MENSAJE_PERMISO);
    expect(URL.createObjectURL).not.toHaveBeenCalled();
    expect(writeText).not.toHaveBeenCalled();
  });

  it("LICREQ-14 · error de red notifica el mensaje RED exacto", async () => {
    apiFetch.mockImplementation((ruta: string) => {
      if (ruta === "/license/detail") {
        return Promise.resolve(DETALLE_PENDIENTE);
      }
      if (ruta === "/license/installation-request") {
        return Promise.reject(new TypeError("Failed to fetch"));
      }
      return Promise.reject(new Error(`Ruta no mockeada: ${ruta}`));
    });

    montar();
    await userEvent.click(await screen.findByRole("button", { name: "Descargar solicitud" }));
    await esperarNotificacion("error", MENSAJE_RED);
    expect(URL.createObjectURL).not.toHaveBeenCalled();
    expect(writeText).not.toHaveBeenCalled();
  });

  it("LICREQ-15 · writeText rechaza y no notifica éxito", async () => {
    writeText.mockRejectedValueOnce(new Error("denegado"));
    montar();
    await userEvent.click(await screen.findByRole("button", { name: "Copiar solicitud" }));
    await esperarNotificacion("error", MENSAJE_PORTAPAPELES);
    expect(notify).not.toHaveBeenCalledWith(expect.objectContaining({ type: "success" }));
  });

  it("LICREQ-16 · descargar y copiar no usan almacenamiento", async () => {
    montar();
    await userEvent.click(await screen.findByRole("button", { name: "Descargar solicitud" }));
    await esperarNotificacion("success", "Solicitud descargada");
    await userEvent.click(screen.getByRole("button", { name: "Copiar solicitud" }));
    await esperarNotificacion("success", "Solicitud copiada");
    expect(spySetItem).not.toHaveBeenCalled();
  });

  it("LICREQ-17 · ningún material privado aparece en la UI, el archivo, el portapapeles ni las notificaciones", async () => {
    montar();
    await userEvent.click(await screen.findByRole("button", { name: "Descargar solicitud" }));
    await esperarNotificacion("success", "Solicitud descargada");
    await userEvent.click(screen.getByRole("button", { name: "Copiar solicitud" }));
    await esperarNotificacion("success", "Solicitud copiada");

    const createObjectURL = vi.mocked(URL.createObjectURL);
    const blob = createObjectURL.mock.calls[0][0] as Blob;
    const textoBlob = await leerBlob(blob);
    const notificaciones = JSON.stringify(notify.mock.calls);

    expect(/PRIVATE KEY|private_key|privada/i.test(document.body.textContent ?? "")).toBe(false);
    expect(/PRIVATE KEY|private_key|privada/i.test(textoBlob)).toBe(false);
    expect(/PRIVATE KEY|private_key|privada/i.test(String(writeText.mock.calls[0][0]))).toBe(false);
    expect(/PRIVATE KEY|private_key|privada/i.test(notificaciones)).toBe(false);
    expect(writeText.mock.calls[0][0]).toBe(JSON.stringify(SOLICITUD, null, 2) + "\n");
    expect(textoBlob).toBe(JSON.stringify(SOLICITUD, null, 2) + "\n");
  });
});
