/**
 * Cliente del MFA (Spec 002/003, ADR-004).
 *
 * Nada se guarda fuera de la memoria: ni desafíos, ni códigos, ni secretos.
 * El access token lo gestiona `client.ts`; aquí solo se envían los datos que
 * el backend pide en cada llamada.
 */
import { apiFetch } from "@/api/client";
import type {
  AuthenticatedLogin,
  LoginResponse,
  MfaEnrollmentStart,
  MfaRecoveryCodes,
  MfaStatus,
  ReauthResult,
} from "@/api/types";

/** Verifica el segundo factor tras `POST /auth/login` con estado `MFA_REQUIRED`. */
export function verifyMfa(
  challengeToken: string,
  secreto: { code: string } | { recoveryCode: string },
): Promise<AuthenticatedLogin> {
  const body = "code" in secreto
    ? { challenge_token: challengeToken, code: secreto.code }
    : { challenge_token: challengeToken, recovery_code: secreto.recoveryCode };
  return apiFetch<AuthenticatedLogin>("/auth/mfa/verify", { method: "POST", body });
}

/** Inicia el alta de MFA, forzada (con desafío) o voluntaria/reemplazo (con sesión). */
export function startEnrollment(challengeToken?: string): Promise<MfaEnrollmentStart> {
  return apiFetch<MfaEnrollmentStart>("/auth/mfa/enrollment", {
    method: "POST",
    body: challengeToken !== undefined ? { challenge_token: challengeToken } : {},
  });
}

/** Confirma el alta de MFA. Con desafío devuelve login completo; con sesión, solo los códigos. */
export function confirmEnrollment(
  code: string,
  challengeToken?: string,
): Promise<AuthenticatedLogin | MfaRecoveryCodes> {
  const body = challengeToken !== undefined
    ? { challenge_token: challengeToken, code }
    : { code };
  return apiFetch<AuthenticatedLogin | MfaRecoveryCodes>("/auth/mfa/enrollment/confirm", {
    method: "POST",
    body,
  });
}

/** Estado del MFA del usuario autenticado. */
export function getMfaStatus(): Promise<MfaStatus> {
  return apiFetch<MfaStatus>("/auth/mfa");
}

/** Genera un nuevo conjunto de códigos de recuperación. */
export function regenerateRecoveryCodes(): Promise<MfaRecoveryCodes> {
  return apiFetch<MfaRecoveryCodes>("/auth/mfa/recovery-codes", { method: "POST" });
}

/** Elimina el MFA propio. Devuelve `void` (204). */
export function removeOwnFactor(): Promise<void> {
  return apiFetch<void>("/auth/mfa", { method: "DELETE" });
}

/** Reautentica al usuario con contraseña y, si procede, segundo factor. */
export function reauthenticate(
  password: string,
  segundo?: { code: string } | { recoveryCode: string },
): Promise<ReauthResult> {
  const body: Record<string, string> = { password };
  if (segundo !== undefined) {
    if ("code" in segundo) {
      body.code = segundo.code;
    } else {
      body.recovery_code = segundo.recoveryCode;
    }
  }
  return apiFetch<ReauthResult>("/auth/reauth", { method: "POST", body });
}

/** Restablece el MFA de un usuario (operación administrativa). */
export function resetUserMfa(userId: string): Promise<void> {
  return apiFetch<void>(`/users/${userId}/mfa/reset`, { method: "POST" });
}

/** Estrecha una respuesta de login: `true` solo si trae access token. */
export function isAuthenticatedLogin(x: {
  status: LoginResponse["status"];
} & { access_token?: string }): x is AuthenticatedLogin {
  return x.status === "AUTHENTICATED" && typeof x.access_token === "string";
}
