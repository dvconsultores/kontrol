/**
 * Pruebas del cliente MFA (Spec 002/003): rutas, cuerpos exactos y narrowing
 * de respuestas de login. No se comprueba persistencia porque no la hay:
 * el contrato es no guardar nada fuera de memoria.
 */
import { afterEach, describe, expect, it, vi } from "vitest";

import { setAccessToken } from "@/api/client";
import {
  confirmEnrollment,
  getMfaStatus,
  isAuthenticatedLogin,
  reauthenticate,
  regenerateRecoveryCodes,
  removeOwnFactor,
  resetUserMfa,
  startEnrollment,
  verifyMfa,
} from "@/api/mfa";

const originalFetch = globalThis.fetch;

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

afterEach(() => {
  globalThis.fetch = originalFetch;
  setAccessToken(null);
  vi.restoreAllMocks();
});

describe("verifyMfa", () => {
  it("envía challenge_token y code", async () => {
    const fetchMock = vi.fn(async () => jsonResponse({ status: "AUTHENTICATED" }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await verifyMfa("desafio", { code: "123456" });

    expect(fetchMock).toHaveBeenCalledOnce();
    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({
      challenge_token: "desafio",
      code: "123456",
    });
  });

  it("envía challenge_token y recovery_code en snake_case", async () => {
    const fetchMock = vi.fn(async () => jsonResponse({ status: "AUTHENTICATED" }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await verifyMfa("desafio", { recoveryCode: "abcd-efgh" });

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/v1/auth/mfa/verify");
    expect(JSON.parse(init.body as string)).toEqual({
      challenge_token: "desafio",
      recovery_code: "abcd-efgh",
    });
  });
});

describe("startEnrollment", () => {
  it("con challenge_token lo envía en el cuerpo", async () => {
    const fetchMock = vi.fn(async () => jsonResponse({}));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await startEnrollment("desafio");

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/v1/auth/mfa/enrollment");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({ challenge_token: "desafio" });
  });

  it("sin challenge_token envía un objeto vacío", async () => {
    const fetchMock = vi.fn(async () => jsonResponse({}));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await startEnrollment();

    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(JSON.parse(init.body as string)).toEqual({});
  });
});

describe("confirmEnrollment", () => {
  it("con challenge_token envía challenge_token y code", async () => {
    const fetchMock = vi.fn(async () => jsonResponse({}));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await confirmEnrollment("123456", "desafio");

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/v1/auth/mfa/enrollment/confirm");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({
      challenge_token: "desafio",
      code: "123456",
    });
  });

  it("sin challenge_token envía solo code", async () => {
    const fetchMock = vi.fn(async () => jsonResponse({}));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await confirmEnrollment("123456");

    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(JSON.parse(init.body as string)).toEqual({ code: "123456" });
  });
});

describe("resto de rutas", () => {
  it("getMfaStatus usa GET /auth/mfa", async () => {
    const fetchMock = vi.fn(async () => jsonResponse({}));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await getMfaStatus();

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/v1/auth/mfa");
    expect(init.method).toBe("GET");
  });

  it("regenerateRecoveryCodes usa POST /auth/mfa/recovery-codes", async () => {
    const fetchMock = vi.fn(async () => jsonResponse({}));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await regenerateRecoveryCodes();

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/v1/auth/mfa/recovery-codes");
    expect(init.method).toBe("POST");
  });

  it("removeOwnFactor usa DELETE /auth/mfa", async () => {
    const fetchMock = vi.fn(async () => new Response(null, { status: 204 }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await removeOwnFactor();

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/v1/auth/mfa");
    expect(init.method).toBe("DELETE");
  });

  it("resetUserMfa usa POST /users/{id}/mfa/reset", async () => {
    const fetchMock = vi.fn(async () => new Response(null, { status: 204 }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await resetUserMfa("user-1");

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/v1/users/user-1/mfa/reset");
    expect(init.method).toBe("POST");
  });
});

describe("reauthenticate", () => {
  it("envía password como recovery_code", async () => {
    const fetchMock = vi.fn(async () => jsonResponse({}));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await reauthenticate("clave", { recoveryCode: "abcd-efgh" });

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/v1/auth/reauth");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({
      password: "clave",
      recovery_code: "abcd-efgh",
    });
  });

  it("envía password y code", async () => {
    const fetchMock = vi.fn(async () => jsonResponse({}));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await reauthenticate("clave", { code: "123456" });

    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(JSON.parse(init.body as string)).toEqual({
      password: "clave",
      code: "123456",
    });
  });

  it("envía solo password sin segundo factor", async () => {
    const fetchMock = vi.fn(async () => jsonResponse({}));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await reauthenticate("clave");

    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(JSON.parse(init.body as string)).toEqual({ password: "clave" });
  });
});

describe("isAuthenticatedLogin", () => {
  it("distingue las tres formas de LoginResponse", () => {
    expect(isAuthenticatedLogin({ status: "AUTHENTICATED", access_token: "x" })).toBe(true);
    expect(isAuthenticatedLogin({ status: "AUTHENTICATED" })).toBe(false);
    expect(isAuthenticatedLogin({ status: "MFA_REQUIRED" })).toBe(false);
    expect(isAuthenticatedLogin({ status: "MFA_ENROLLMENT_REQUIRED" })).toBe(false);
  });
});
