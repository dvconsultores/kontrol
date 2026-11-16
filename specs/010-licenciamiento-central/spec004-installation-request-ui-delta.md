# SPEC 004 · DELTA DIRIGIDO — SOLICITUD DE ACTIVACIÓN EN «MI LICENCIA»

> 2026-11-16. Dueño: **Spec 004 global (Licenciamiento)**, en `010-licenciamiento-central`, junto a los demás
> `spec004-*-delta.md`. No crea otra Spec.
>
> Encargo de la dueña: «DELTA URGENTE DE LICENCIAMIENTO · MI LICENCIA → SOLICITUD DE ACTIVACIÓN».
> Es solo frontend y preserva la seguridad existente.

## 1. Motivo

El endpoint `GET /api/v1/license/installation-request` ya existe: exige sesión y `license:view` (FR-010-108, DOC-07 §6.2).
Sin embargo, «Mi licencia» no ofrecía ninguna acción para obtener la solicitud que se entrega al propietario para registrar
la instalación y emitir la licencia real. Esto bloqueaba la licencia de la UAT remota.

## 2. Contrato backend (sin cambios)

| | |
|---|---|
| Ruta | `GET /api/v1/license/installation-request` |
| Autenticación | sesión obligatoria (401 sin ella) |
| Permiso | `license:view` (403 sin él) |
| Respuesta | `installation_request_payload(...)` → `{installation_id, public_key, version, nonce, requested_at}`. Solo identidad pública |
| Campo de la clave | **`public_key`**, exactamente (no `public_key_pem`, `installation_public_key` ni `key`) |

```text
BACKEND_CHANGE_REQUIRED=0  MIGRATION_REQUIRED=0  API_CONTRACT_CHANGE=0  CRYPTO_CHANGE=0  NEW_ENDPOINT=0
```

## 3. Comportamiento

| ID | Requisito |
|---|---|
| LR-01 | La sección `<section>` con el h2 «Solicitud de activación» aparece **solo** con `mode === "PENDING"`. No aparece en FULL_ACCESS, RENEWAL_NOTICE, CRITICAL_RENEWAL_NOTICE, READ_ONLY ni SECURITY_SUSPENSION. |
| LR-02 | Hay dos acciones, «Descargar solicitud» y «Copiar solicitud». Cada una pide una solicitud nueva con `apiFetch("/license/installation-request")`; nada se guarda entre acciones. |
| LR-03 | Antes de usar la respuesta, se valida que sea un objeto y que `installation_id` y `public_key` sean strings no vacíos (tras trim). Si no, se rechaza con `INVALID_INSTALLATION_REQUEST`, con error legible y sin copia ni descarga. |
| LR-04 | Se usa el objeto completo, con `version`, `nonce` y `requested_at`, serializado como `JSON.stringify(payload, null, 2) + "\n"`. |
| LR-05 | La descarga es un Blob `application/json;charset=utf-8` que sigue la secuencia `createObjectURL` → `<a download>` → click → remove → `revokeObjectURL` (siempre se revoca). |
| LR-06 | El archivo se llama `kontrol-installation-request-<id saneado>.json`. El saneado deja solo `[A-Za-z0-9._-]` y pone `_` en lugar del resto; colapsa las secuencias de `..`, quita los puntos iniciales, limita la longitud a 100 y usa `sin-identificador` si el resultado queda vacío. |
| LR-07 | La copia escribe el JSON completo formateado con `navigator.clipboard.writeText`. |
| LR-08 | Un estado común (`solicitudEnCurso`) deshabilita **ambos** botones mientras cualquiera trabaja. El botón activo muestra «Descargando…» o «Copiando…», con `aria-busy`. |
| LR-09 | Errores, con `ApiError.status`: 401 → «La sesión venció…»; 403 → «…Se requiere license:view.»; fallo de red → «No fue posible conectar con KONTROL…». Fallo del portapapeles → «No fue posible copiar…», sin éxito falso. Fallo de la descarga → «No fue posible descargar…». |
| LR-10 | Los éxitos se notifican como «Solicitud descargada» y «Solicitud copiada». Ninguna notificación incluye la clave ni el JSON. |
| LR-11 | Seguridad: la clave privada no se lee, no se envía y no se menciona. No se usan localStorage, sessionStorage ni IndexedDB, y no se registra el payload. |
| LR-12 | Responsive a 1280, 390 y 320: los botones se apilan en móvil (`flex-col sm:flex-row`). |

## 4. Pruebas

- **Vitest** `MiLicenciaPage.test.tsx`: LICREQ-01..17, más pruebas unitarias del saneado y de la validación.
- **E2E** `licencia.spec.ts`, E2E-LIC-11:
  - el admin, con el detalle interceptado como PENDING, descarga la solicitud real;
  - se comprueba el nombre seguro, que el JSON es igual a la respuesta, `installation_id` y `public_key`, y que no aparece «PRIVATE KEY»;
  - el portapapeles se cubre en Vitest.
- **Backend dirigido**: `test_license_access` y `test_license_trust_anchor` confirman que el endpoint sigue exigiendo sesión y `license:view` y devuelve solo la clave pública.

## 5. Fuera de alcance

- Backend, criptografía, migraciones y endpoints nuevos.
- Métricas de Gobierno: `GOVERNMENT_PROCESS_INCREMENT=0`.

La evidencia y el resultado de las pruebas están en `evidence/installation-request-ui/CIERRE.md`.
