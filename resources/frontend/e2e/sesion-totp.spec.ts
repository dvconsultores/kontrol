/**
 * Vectores públicos de RFC 6238 para el generador TOTP (SHA-1, 6 dígitos,
 * periodo 30 s) y la identidad por worker.
 */
import { expect, test } from "@playwright/test";

import { codigoTotp, identidad } from "./helpers/sesion";

const CLAVE_RFC = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ";

test.describe("Spec 002/003 · arnés de sesión con MFA", () => {
  test("TOTP RFC 6238 · T=59", () => {
    expect(codigoTotp(CLAVE_RFC, 59000).slice(-6)).toBe("287082");
  });

  test("TOTP RFC 6238 · T=1111111109", () => {
    expect(codigoTotp(CLAVE_RFC, 1111111109000).slice(-6)).toBe("081804");
  });

  test("TOTP RFC 6238 · T=1111111111", () => {
    expect(codigoTotp(CLAVE_RFC, 1111111111000).slice(-6)).toBe("050471");
  });

  test("TOTP RFC 6238 · T=1234567890", () => {
    expect(codigoTotp(CLAVE_RFC, 1234567890000).slice(-6)).toBe("005924");
  });

  test("TOTP RFC 6238 · T=2000000000", () => {
    expect(codigoTotp(CLAVE_RFC, 2000000000000).slice(-6)).toBe("279037");
  });

  test("TOTP RFC 6238 · T=20000000000", () => {
    expect(codigoTotp(CLAVE_RFC, 20000000000000).slice(-6)).toBe("353130");
  });

  test("identidad del worker", () => {
    expect(identidad("admin", 3)).toBe("admin_w3");
  });

  test("identidad fuera de 0..5 lanza", () => {
    expect(() => identidad("admin", 6)).toThrow();
  });
});
