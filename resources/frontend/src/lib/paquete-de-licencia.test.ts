import { describe, expect, it } from "vitest";

import { ApiError } from "@/api/client";
import {
  PaqueteInvalidoError,
  interpretarPaquete,
  mensajeDeErrorDeActivacion,
  validarArchivoDeLicencia,
  vistaPrevia,
} from "@/lib/paquete-de-licencia";

describe("validarArchivoDeLicencia", () => {
  it("acepta .json con tipo application/json", () => {
    expect(() =>
      validarArchivoDeLicencia({ name: "license.json", type: "application/json", size: 10 }),
    ).not.toThrow();
  });

  it("acepta LICENCIA.JSON con tipo vacío", () => {
    expect(() =>
      validarArchivoDeLicencia({ name: "LICENCIA.JSON", type: "", size: 10 }),
    ).not.toThrow();
  });

  it("rechaza extensión no json", () => {
    expect(() =>
      validarArchivoDeLicencia({ name: "license.txt", type: "application/json", size: 10 }),
    ).toThrow(/extensión \.json/);
  });

  it("rechaza license.json.exe", () => {
    expect(() =>
      validarArchivoDeLicencia({ name: "license.json.exe", type: "application/json", size: 10 }),
    ).toThrow(/extensión \.json/);
  });

  it("rechaza tipo text/plain", () => {
    expect(() =>
      validarArchivoDeLicencia({ name: "license.json", type: "text/plain", size: 10 }),
    ).toThrow(/tipo del archivo no es JSON/);
  });

  it("rechaza archivo mayor de 256 KiB", () => {
    expect(() =>
      validarArchivoDeLicencia({
        name: "license.json",
        type: "application/json",
        size: 256 * 1024 + 1,
      }),
    ).toThrow(/256 KiB/);
  });

  it("rechaza archivo vacío", () => {
    expect(() =>
      validarArchivoDeLicencia({ name: "license.json", type: "application/json", size: 0 }),
    ).toThrow(/vacío/);
  });
});

describe("interpretarPaquete", () => {
  it("rechaza claves privadas PEM", () => {
    const MARCA = "-----BEGIN " + "PRIV" + "ATE KEY-----";
    expect(() => interpretarPaquete(`${MARCA}\n...`)).toThrow(/clave privada/);
  });

  it("rechaza claves privadas ed25519", () => {
    const MARCA = "-----BEGIN " + "ED25519 " + "PRIV" + "ATE KEY-----";
    expect(() => interpretarPaquete(`${MARCA}\n...`)).toThrow(/clave privada/);
  });

  it("rechaza texto no JSON", () => {
    expect(() => interpretarPaquete("{no json")).toThrow(/JSON válido/);
  });

  it("rechaza raíz arreglo", () => {
    expect(() => interpretarPaquete("[]")).toThrow(/objeto JSON/);
  });

  it("rechaza payload que no es objeto", () => {
    expect(() =>
      interpretarPaquete(
        JSON.stringify({ payload: "x", signature_hex: "ab".repeat(64) }),
      ),
    ).toThrow(/payload válido/);
  });

  it("rechaza firma ausente", () => {
    const p = {
      payload: {
        license_id: "L",
        installation_id: "I",
        kid: "K",
        period_start: "S",
        period_end: "E",
      },
    };
    expect(() => interpretarPaquete(JSON.stringify(p))).toThrow(/signature_hex/);
  });

  it("rechaza firma en blanco", () => {
    const p = {
      payload: {
        license_id: "L",
        installation_id: "I",
        kid: "K",
        period_start: "S",
        period_end: "E",
      },
      signature_hex: "   ",
    };
    expect(() => interpretarPaquete(JSON.stringify(p))).toThrow(/signature_hex/);
  });

  it.each([
    ["license_id", { installation_id: "I", kid: "K", period_start: "S", period_end: "E" }],
    ["installation_id", { license_id: "L", kid: "K", period_start: "S", period_end: "E" }],
    ["kid", { license_id: "L", installation_id: "I", period_start: "S", period_end: "E" }],
    ["period_start", { license_id: "L", installation_id: "I", kid: "K", period_end: "E" }],
    ["period_end", { license_id: "L", installation_id: "I", kid: "K", period_start: "S" }],
  ])("rechaza payload sin %s", (campo, parcial) => {
    const p = { payload: parcial, signature_hex: "ab" };
    expect(() => interpretarPaquete(JSON.stringify(p))).toThrow(
      new RegExp(`no contiene ${campo}`),
    );
  });

  it("acepta paquete y conserva las claves en orden", () => {
    const orden = [
      "license_id",
      "installation_id",
      "kid",
      "period_start",
      "period_end",
      "extra",
    ];
    const p = {
      payload: {
        license_id: "L",
        installation_id: "I",
        kid: "K",
        period_start: "S",
        period_end: "E",
        extra: "x",
      },
      signature_hex: "ab".repeat(64),
    };
    const r = interpretarPaquete(JSON.stringify(p));
    expect(r.payload).toEqual(p.payload);
    expect(Object.keys(r.payload)).toEqual(orden);
  });
});

describe("vistaPrevia", () => {
  it("extrae campos y módulos de arreglo", () => {
    const v = vistaPrevia({
      payload: {
        license_id: "LIC-1",
        installation_id: "I-1",
        kid: "K-1",
        period_start: "2026-01-01T00:00:00Z",
        period_end: "2027-01-01T00:00:00Z",
        revision: 3,
        minimum_version: "1.2.0",
        entitlements: { companies: 2, users: 5, modules: ["nomina"] },
      },
      signature_hex: "ab",
    });
    expect(v.licenseId).toBe("LIC-1");
    expect(v.revision).toBe("3");
    expect(v.empresas).toBe(2);
    expect(v.usuarios).toBe(5);
    expect(v.modulos).toEqual(["nomina"]);
    expect(v.perfil).toBe("EMPRESA");
  });

  it("acepta modules como objeto de banderas", () => {
    const v = vistaPrevia({
      payload: {
        license_id: "L",
        installation_id: "I",
        kid: "K",
        period_start: "S",
        period_end: "E",
        entitlements: { modules: { gobierno: true, nomina: false } },
      },
      signature_hex: "ab",
    });
    expect(v.modulos).toEqual(["gobierno"]);
    expect(v.perfil).toBe("GOBIERNO");
  });

  it("usa valores por defecto si faltan entitlements", () => {
    const v = vistaPrevia({
      payload: {
        license_id: "L",
        installation_id: "I",
        kid: "K",
        period_start: "S",
        period_end: "E",
      },
      signature_hex: "ab",
    });
    expect(v.revision).toBeNull();
    expect(v.minimumVersion).toBeNull();
    expect(v.empresas).toBeNull();
    expect(v.usuarios).toBeNull();
    expect(v.modulos).toEqual([]);
  });
});

describe("mensajeDeErrorDeActivacion", () => {
  it("paquete inválido", () => {
    const e = mensajeDeErrorDeActivacion(new PaqueteInvalidoError("roto"));
    expect(e).toBe("roto (INVALID_LICENSE_PACKAGE)");
  });

  it("error de red", () => {
    expect(mensajeDeErrorDeActivacion(new TypeError("Failed to fetch"))).toBe(
      "No fue posible conectar con KONTROL para activar la licencia.",
    );
  });

  it("401", () => {
    const e = mensajeDeErrorDeActivacion(new ApiError(401, { code: "UNAUTHORIZED" }));
    expect(e).toBe("La sesión venció. Inicie sesión nuevamente para activar la licencia. (UNAUTHORIZED)");
  });

  it("REAUTH_REQUIRED", () => {
    const e = mensajeDeErrorDeActivacion(new ApiError(403, { code: "REAUTH_REQUIRED" }));
    expect(e).toBe("No se confirmó su identidad; la licencia no se activó. (REAUTH_REQUIRED)");
  });

  it("PERMISSION_DENIED", () => {
    const e = mensajeDeErrorDeActivacion(new ApiError(403, { code: "PERMISSION_DENIED" }));
    expect(e).toBe("No tiene permiso para activar licencias. Se requiere license:create. (PERMISSION_DENIED)");
  });

  it("403 sin code", () => {
    const e = mensajeDeErrorDeActivacion(new ApiError(403, { code: "" }));
    expect(e).toBe("No tiene permiso para activar licencias. Se requiere license:create. (PERMISSION_DENIED)");
  });

  it.each([
    "LICENSE_SIGNATURE_INVALID",
    "LICENSE_SIGNING_KID_UNKNOWN",
    "LICENSE_SIGNING_KID_MISSING",
    "LICENSE_INSTALLATION_MISMATCH",
    "LICENSE_PERIOD_DOWNGRADE",
    "LICENSE_PERIOD_CONFLICT",
    "LICENSE_INVALID_REVISION",
    "LICENSE_REVISION_DOWNGRADE",
    "LICENSE_REVISION_CONFLICT",
    "LICENSE_LEGACY_REISSUE_REQUIRES_REVISION",
    "LICENSE_LEGACY_AFTER_REVISION",
    "LICENSE_CURRENT_ARTIFACT_INVALID",
    "LICENSE_INVALID_MINIMUM_VERSION",
    "LICENSE_MINIMUM_VERSION_INCOMPATIBLE",
  ])("mapea %s", (code) => {
    const e = mensajeDeErrorDeActivacion(new ApiError(423, { code, message: "x" }));
    expect(e).toContain(`(${code})`);
  });

  it("LICENSE_TRUST_ANCHOR_*", () => {
    const e = mensajeDeErrorDeActivacion(
      new ApiError(423, { code: "LICENSE_TRUST_ANCHOR_MISSING" }),
    );
    expect(e).toBe(
      "La instalación no tiene configurada la clave pública del propietario. (LICENSE_TRUST_ANCHOR_MISSING)",
    );
  });

  it("500 incluye request_id pero no details", () => {
    const e = mensajeDeErrorDeActivacion(
      new ApiError(500, {
        code: "INTERNAL_ERROR",
        request_id: "req-1",
        details: { secreto: "no" },
      }),
    );
    expect(e).toContain("solicitud req-1");
    expect(e).not.toContain("secreto");
  });

  it("otro ApiError usa message y code", () => {
    const e = mensajeDeErrorDeActivacion(new ApiError(422, { code: "X", message: "fallo" }));
    expect(e).toBe("fallo (X)");
  });
});
