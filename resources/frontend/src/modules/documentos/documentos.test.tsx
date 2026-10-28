/** Pruebas del módulo documental (Spec 046).
 *
 * Lo que se comprueba aquí es sobre todo lo que el usuario **lee**: que un
 * fallo de carga se explique en términos accionables y no como «error
 * desconocido», y que un nombre largo no oculte la extensión, que es lo que
 * identifica al archivo.
 */
import { describe, expect, it } from "vitest";

import { ApiError } from "@/api/client";

import { can, formatSize, truncateName, uploadErrorMessage } from "./types";

describe("formatSize", () => {
  it("no oculta la magnitud real", () => {
    expect(formatSize(512)).toBe("512 B");
    expect(formatSize(2048)).toBe("2.0 KB");
    expect(formatSize(5 * 1024 * 1024)).toBe("5.0 MB");
  });
});

describe("truncateName", () => {
  it("conserva la extensión al truncar por el centro", () => {
    const name = `${"a".repeat(80)}.pdf`;
    const short = truncateName(name);
    expect(short.length).toBeLessThan(name.length);
    expect(short).toContain("…");
    expect(short.endsWith(".pdf")).toBe(true);
  });

  it("deja intacto lo que ya cabe", () => {
    expect(truncateName("contrato.pdf")).toBe("contrato.pdf");
  });
});

describe("uploadErrorMessage", () => {
  it("dice cuál es el límite cuando el archivo es grande", () => {
    const err = new ApiError(413, {
      code: "FILE_TOO_LARGE", message: "grande",
      details: { max_size_bytes: 2 * 1024 * 1024 },
    });
    expect(uploadErrorMessage(err)).toContain("2.0 MB");
  });

  it("dice qué formatos sí se admiten", () => {
    const err = new ApiError(422, {
      code: "MIME_NOT_ALLOWED", message: "no",
      details: { allowed: ["application/pdf"] },
    });
    expect(uploadErrorMessage(err)).toContain("application/pdf");
  });

  it("no disfraza un archivo malicioso de fallo genérico", () => {
    const err = new ApiError(422, { code: "FILE_INFECTED", message: "x" });
    expect(uploadErrorMessage(err)).toMatch(/malicioso/i);
  });

  it("distingue «no se pudo verificar» de «está limpio»", () => {
    const err = new ApiError(422, { code: "SCAN_FAILED", message: "x" });
    const message = uploadErrorMessage(err);
    expect(message).toMatch(/no se pudo verificar/i);
    expect(message).not.toMatch(/limpio|verificado/i);
  });

  it("SCAN_FAILED con SCANNER_UNAVAILABLE dice que el servicio no está disponible, sin afirmar malware", () => {
    const err = new ApiError(422, {
      code: "SCAN_FAILED", message: "x",
      details: { category: "SCANNER_UNAVAILABLE" },
    });
    const message = uploadErrorMessage(err);
    expect(message).toContain("no está disponible");
    expect(message).not.toContain("malicioso");
  });

  it("SCAN_FAILED con SCAN_TIMEOUT dice que el análisis tardó demasiado", () => {
    const err = new ApiError(422, {
      code: "SCAN_FAILED", message: "x",
      details: { category: "SCAN_TIMEOUT" },
    });
    expect(uploadErrorMessage(err)).toContain("tardó demasiado");
  });

  it("FILE_INFECTED no interpola la firma del analizador", () => {
    const err = new ApiError(422, {
      code: "FILE_INFECTED", message: "x",
      details: { category: "MALWARE_DETECTED", signature: "Firma-Sintetica" },
    });
    expect(uploadErrorMessage(err)).not.toContain("Firma-Sintetica");
  });

  it("explica que un vínculo congelado no se retira", () => {
    const err = new ApiError(409, { code: "LINK_FROZEN", message: "x" });
    expect(uploadErrorMessage(err)).toMatch(/congelado/i);
  });

  it("nunca responde «error desconocido»", () => {
    const err = new ApiError(500, { code: "ALGO_RARO", message: "Fallo del servidor" });
    const message = uploadErrorMessage(err);
    expect(message).toBe("Fallo del servidor");
    expect(message.toLowerCase()).not.toContain("desconocido");
  });
});

describe("can", () => {
  it("refleja lo que el backend autoriza, no lo que el cliente supone", () => {
    const document = { allowed_actions: ["view", "download"] };
    expect(can(document, "download")).toBe(true);
    expect(can(document, "delete")).toBe(false);
  });
});
