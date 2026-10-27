import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "./client";
import { descargarArchivo, mensajeDeDescarga, nombreSeguro } from "./descargas";

const apiFetch = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

const createObjectURLOriginal = URL.createObjectURL;
const revokeObjectURLOriginal = URL.revokeObjectURL;

afterEach(() => {
  apiFetch.mockReset();
  URL.createObjectURL = createObjectURLOriginal;
  URL.revokeObjectURL = revokeObjectURLOriginal;
  vi.restoreAllMocks();
  document.body.innerHTML = "";
});

describe("nombreSeguro", () => {
  it("DESC-01 extrae filename básico", () => {
    expect(
      nombreSeguro('attachment; filename="report-executive_ventas-20261027120000.pdf"', "r"),
    ).toBe("report-executive_ventas-20261027120000.pdf");
  });

  it("DESC-02 prefiere filename* RFC 5987", () => {
    expect(
      nombreSeguro("attachment; filename=\"otro.csv\"; filename*=UTF-8''informe%20de%20ventas.csv", "r"),
    ).toBe("informe de ventas.csv");
  });

  it("DESC-03 elimina recorrido de ruta y separadores", () => {
    expect(nombreSeguro('attachment; filename="../../etc/passwd"', "r")).toBe("passwd");
    expect(nombreSeguro('attachment; filename="a\\\\b\\\\c.csv"', "r")).toBe("c.csv");
  });

  it("DESC-04 elimina control y CR/LF", () => {
    expect(nombreSeguro('attachment; filename="repo\r\nrt\u0000.pdf"', "r")).toBe("report.pdf");
  });

  it("DESC-05 usa reserva o descarga", () => {
    expect(nombreSeguro(null, "exportacion-1")).toBe("exportacion-1");
    expect(nombreSeguro(null, "../")).toBe("descarga");
  });

  it("DESC-06 limita a 150 caracteres", () => {
    expect(nombreSeguro(null, "a".repeat(300))).toHaveLength(150);
  });
});

describe("mensajeDeDescarga", () => {
  it("DESC-07 devuelve los cinco textos exactos", () => {
    expect(mensajeDeDescarga(new ApiError(403, { code: "PERMISSION_DENIED" }))).toBe(
      "No tiene permiso para descargar este archivo.",
    );
    expect(mensajeDeDescarga(new ApiError(403, { code: "COMPANY_SCOPE_FORBIDDEN" }))).toBe(
      "No tiene esa autoridad en esta empresa.",
    );
    expect(mensajeDeDescarga(new ApiError(404, { code: "EXPORT_FILE_MISSING" }))).toBe(
      "El archivo ya no existe o no está disponible.",
    );
    expect(mensajeDeDescarga(new TypeError("Failed to fetch"))).toBe(
      "No hay conexión con el servidor. Inténtelo de nuevo.",
    );
    expect(mensajeDeDescarga(new Error("x"))).toBe("No fue posible descargar el archivo.");
  });
});

describe("descargarArchivo", () => {
  it("DESC-08 crea, usa y revoca la URL", async () => {
    URL.createObjectURL = vi.fn(() => "blob:prueba");
    URL.revokeObjectURL = vi.fn();
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    apiFetch.mockResolvedValue({
      blob: new Blob(["%PDF"]),
      contentDisposition: 'attachment; filename="r.pdf"',
    });

    await expect(descargarArchivo("/reporting/exports/e1/download", "exportacion-e1")).resolves.toBe("r.pdf");

    expect(apiFetch).toHaveBeenCalledWith("/reporting/exports/e1/download", { responseType: "archivo" });
    expect(URL.createObjectURL).toHaveBeenCalledTimes(1);
    expect(click).toHaveBeenCalledTimes(1);
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:prueba");
    expect(document.querySelector("a")).toBeNull();
  });

  it("DESC-09 no crea URL ni ancla si la petición falla", async () => {
    URL.createObjectURL = vi.fn();
    URL.revokeObjectURL = vi.fn();
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    const error = new ApiError(403, { code: "PERMISSION_DENIED" });

    apiFetch.mockRejectedValue(error);

    await expect(descargarArchivo("/reporting/exports/e1/download", "exportacion-e1")).rejects.toBe(error);

    expect(URL.createObjectURL).not.toHaveBeenCalled();
    expect(click).not.toHaveBeenCalled();
    expect(URL.revokeObjectURL).not.toHaveBeenCalled();
    expect(document.querySelector("a")).toBeNull();
  });
});
