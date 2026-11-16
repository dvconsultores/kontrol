# SPEC 004 · DELTA DIRIGIDO — ACTIVAR LICENCIA FIRMADA DESDE «MI LICENCIA» + PERFIL KONTROL GOBIERNO

> 2026-11-16. Dueño: **Spec 004 global (Licenciamiento)**, en `010-licenciamiento-central`. No crea otra Spec.
> Encargo de la dueña: «DELTA PRIORITARIO DE LICENCIAMIENTO · IMPORTAR Y ACTIVAR LICENCIA FIRMADA DESDE
> «MI LICENCIA» + PERFIL DE INTERFAZ KONTROL GOBIERNO». `GOVERNMENT_PROCESS_INCREMENT=0`.
> Precede: `spec004-installation-request-ui-delta.md` (descarga de la solicitud).

## 1. Ciclo de punta a punta

Descargar solicitud → la Autoridad Central registra y emite → el administrador carga el paquete JSON en «Mi licencia»
→ vista previa saneada → confirmación → `POST /license/activate` (con la reautenticación canónica de `apiFetch`) → el backend
verifica → se refrescan la licencia y el perfil sin recargar → con `gobierno` firmado y sin derechos empresariales, la interfaz
es **KONTROL Gobierno**.

## 2. Contrato backend existente (se preserva)

| | |
|---|---|
| Ruta | `POST /api/v1/license/activate` (y `/license/import`, offline): ambas llaman `licensing_service.import_license` |
| Cuerpo | `{payload: {...}, signature_hex: "..."}` exactamente |
| Compuertas | sesión · `license:create` · `require_recent_reauth` (403 `REAUTH_REQUIRED`) |
| Validaciones (orden actual) | ancla del propietario (`LICENSE_TRUST_ANCHOR_*`, 503) → `kid` firmado (`LICENSE_SIGNING_KID_UNKNOWN`/`_MISSING`, 423) → Ed25519 (`LICENSE_SIGNATURE_INVALID`, 423) → instalación (`LICENSE_INSTALLATION_MISMATCH`, 423) → contrato (`LICENSE_INVALID_REVISION`, 423) → bloqueo → período (`LICENSE_PERIOD_DOWNGRADE`/`_CONFLICT`) → revisión (`LICENSE_REVISION_DOWNGRADE`/`_CONFLICT`, `LICENSE_LEGACY_REISSUE_REQUIRES_REVISION`, `LICENSE_LEGACY_AFTER_REVISION`, `LICENSE_CURRENT_ARTIFACT_INVALID`) → persistir |
| Éxito | `{ok: true, license_id, mode}` |

`NEW_ACTIVATION_ENDPOINT=0  BACKEND_VALIDATION_RELAXED=0  FRONTEND_CRYPTO_VERIFICATION=0`.

## 3. Brecha `minimum_version` (auditada)

- Contrato: `specs/001-fundacion/contracts/license-contract.md` §Reglas: «Verificación de firma, `audience`, `installation_id`,
  fechas, derechos y **versión mínima** en cada arranque y **antes de aplicar licencia nueva**».
- Código antes del delta: `minimum_version` se parsea, se persiste y se publica, pero **ninguna comparación** impide aplicarla.
- Versión canónica en ejecución: `Settings.app_version` → `app.__version__` (`spec001-panel-version-delta.md`).

`MINIMUM_VERSION_CONTRACT=REQUIRED_BEFORE_APPLY` → se implementa **en backend** (PDD-LICACT-09):

| ID | Regla |
|---|---|
| MV-01 | Ausente o `null` → sin restricción (campo opcional del contrato; licencias legacy). |
| MV-02 | Presente: debe ser texto `MAJOR.MINOR.PATCH` de enteros sin signo (`^\d+\.\d+\.\d+$`, sin ceros a la izquierda salvo «0»). Otro valor → 423 `LICENSE_INVALID_MINIMUM_VERSION` (nomenclatura de `LICENSE_INVALID_REVISION`). |
| MV-03 | `minimum_version` > versión en ejecución (comparación numérica por componente) → 423 `LICENSE_MINIMUM_VERSION_INCOMPATIBLE` (nomenclatura de `LICENSE_SIGNATURE_INVALID`/`LICENSE_INSTALLATION_MISMATCH`). Igual o menor → entra. |
| MV-04 | Se evalúa **después** del anti-retroceso de período y revisión y **antes** de persistir artefacto o estado (paso 5c). El orden de los rechazos existentes no cambia (REVC-08 sigue dando `LICENSE_REVISION_CONFLICT`). |
| MV-05 | Rechazo: evento `LICENSE_MINIMUM_VERSION_REJECTED` con `{license_id, minimum_version, running_version, outcome: INCOMPATIBLE|INVALID}` (sin firma ni carga), `commit`, y ningún `LicenseArtifact` ni cambio de `LicenseState`. |
| MV-06 | Sin dependencias nuevas (`packaging` no está en el lock de ejecución): comparación propia en `app/core/license_contract.py`. |

Fuera de este delta (deuda `LIC-MINVER-REVERIFY-01`, baja; **CLOSED** en `spec004-license-ui-ux-profile-security-delta.md`): la verificación «en cada arranque» del artefacto vigente. Cambiaría
el modo de una instalación ya activa y la semántica de la reverificación; no se toca lateralmente.

Período, auditado (§41): `FUTURE_PERIOD_CURRENT_CONTRACT=FULL_ACCESS` (antes de `period_start`, `compute_mode` da FULL_ACCESS);
`EXPIRED_PERIOD_CURRENT_CONTRACT=TEMPORAL_MODE` (vencida → RENEWAL_NOTICE / CRITICAL_RENEWAL_NOTICE / READ_ONLY según sus fechas).
No hay código backend de «vencida» ni «no vigente»; el frontend no lo simula.

## 4. Pantalla «Mi licencia» · sección «Activar licencia»

| ID | Requisito |
|---|---|
| LA-01 | Sección `<section aria-labelledby>` con h2 «Activar licencia», visible en PENDING, RENEWAL_NOTICE, CRITICAL_RENEWAL_NOTICE, READ_ONLY y SECURITY_SUSPENSION; no en FULL_ACCESS. |
| LA-02 | La página sigue gobernada por `license:view`; la sección se **oculta** si `useAutoridad().tiene("license:create", "global")` es falso (`ACTIVATION_CONTROL_HIDDEN=1`). Nunca por rol. |
| LA-03 | `<input type="file" accept=".json,application/json">` con etiqueta asociada «Archivo de licencia firmado». |
| LA-04 | Nombre terminado en `.json` (sin distinguir mayúsculas). `file.type` debe ser `application/json`, `""` o `text/json`; otro MIME se rechaza aunque la extensión sea `.json`. |
| LA-05 | Lectura con `await file.text()`, solo en memoria; tope 256 KiB antes de leer. Sin `localStorage`, `sessionStorage`, IndexedDB, Cache API ni logs. |
| LA-06 | Si el texto contiene `PRIVATE KEY` (p. ej. `-----BEGIN PRIVATE KEY-----`, `-----BEGIN ED25519 PRIVATE KEY-----`, `-----BEGIN OPENSSH PRIVATE KEY-----`) se rechaza sin parsear, sin mostrar contenido y sin enviar nada. |
| LA-07 | `JSON.parse`; raíz objeto no nulo ni arreglo; `payload` objeto no nulo ni arreglo; `signature_hex` string con `trim() !== ""`; en `payload`, `license_id`, `installation_id`, `kid`, `period_start` y `period_end` strings no vacíos. Fallo → error legible con código local `INVALID_LICENSE_PACKAGE` y nada se envía. No es autoridad. |
| LA-08 | Vista previa saneada: Licencia, Instalación, Clave de firma, Período (`period_start → period_end` formateados), Revisión (o «sin revisión»), Versión mínima (o «—»), Empresas, Usuarios, Módulos habilitados (lista firmada; «ninguno» si vacía), y «Perfil: KONTROL Gobierno» si `modules` incluye `gobierno`. Nunca `signature_hex`, el JSON completo ni claves. Textos largos con `break-all`. |
| LA-09 | Si `payload.installation_id` ≠ `installation_id` del detalle, aviso temprano «El paquete fue emitido para otra instalación…» (no bloquea: decide el backend). |
| LA-10 | Botón «Validar y activar licencia», deshabilitado sin paquete válido, durante la operación o sin `license:create`. |
| LA-11 | Abre el `ConfirmationDialog` canónico con instalación, licencia, `kid`, período, revisión, versión mínima y derechos, y la advertencia «La licencia quedará vinculada a esta instalación. El servidor verificará la firma, la identidad y la vigencia antes de aplicarla.» Acciones «Cancelar» / «Activar licencia». Cancelar no hace POST. |
| LA-12 | Confirmar **cierra** el diálogo y ejecuta `apiFetch("/license/activate", {method: "POST", body: {payload, signature_hex}})` con el `payload` tal como se leyó (misma referencia del objeto parseado; sin reordenar ni normalizar). Nada más viaja. |
| LA-13 | Durante la operación: input, botón y sección deshabilitados, `aria-busy="true"`, texto «Validando y activando…»; sin doble POST. |
| LA-14 | `REAUTH_REQUIRED` lo consume `apiFetch` (diálogo canónico, reintento único). Si la reautenticación se cancela, llega `ApiError` `REAUTH_REQUIRED` y se muestra «No se confirmó su identidad; la licencia no se activó. (REAUTH_REQUIRED)». La confirmación no se repite. |
| LA-15 | Éxito: notificación «Licencia activada», descripción «Licencia <license_id> · modo <MODO>». Se limpian archivo, paquete, vista previa e `input.value`. Se invalidan `["license"]` y `["licencia", "modulo", "gobierno"]` y se llama `useLicense().refresh()`. Sin recargar. El modo mostrado es el que devuelve el backend. |
| LA-16 | Errores (mensaje humano + ` (<CODE>)`; nunca pila, cabeceras, token, carga ni firma; `details` no se muestra): 401 → «La sesión venció. Inicie sesión nuevamente para activar la licencia.»; 403 `PERMISSION_DENIED` → «No tiene permiso para activar licencias. Se requiere license:create.»; `LICENSE_SIGNATURE_INVALID` → «La firma de la licencia no es válida.»; `LICENSE_SIGNING_KID_UNKNOWN` → «La licencia está firmada con una clave que esta instalación no reconoce.»; `LICENSE_SIGNING_KID_MISSING` → «La licencia no indica la clave de firma (kid).»; `LICENSE_INSTALLATION_MISMATCH` → «Esta licencia fue emitida para otra instalación.»; `LICENSE_PERIOD_DOWNGRADE` → «La licencia corresponde a un período anterior al vigente.»; `LICENSE_PERIOD_CONFLICT` → «El período de la licencia no es comparable con el vigente.»; `LICENSE_INVALID_REVISION` → «La revisión de la licencia no es válida.»; `LICENSE_REVISION_DOWNGRADE` → «La licencia tiene una revisión anterior a la vigente.»; `LICENSE_REVISION_CONFLICT` → «Ya existe otra licencia con la misma revisión.»; `LICENSE_LEGACY_REISSUE_REQUIRES_REVISION` → «La reemisión requiere una revisión firmada por la autoridad.»; `LICENSE_LEGACY_AFTER_REVISION` → «No se admite una licencia sin revisión después de una revisionada.»; `LICENSE_CURRENT_ARTIFACT_INVALID` → «La licencia vigente no cumple el contrato; contacte al propietario de KONTROL.»; `LICENSE_INVALID_MINIMUM_VERSION` → «La versión mínima de la licencia no es válida.»; `LICENSE_MINIMUM_VERSION_INCOMPATIBLE` → «La licencia exige una versión de KONTROL más reciente que la instalada.»; `LICENSE_TRUST_ANCHOR_*` → «La instalación no tiene configurada la clave pública del propietario.»; red → «No fue posible conectar con KONTROL para activar la licencia.» (se conserva el paquete); otro 5xx → «KONTROL no pudo activar la licencia. Intente más tarde.» + ` (<CODE>)` y, si existe, ` · solicitud <requestId>`; cualquier otro código → `error.message` + ` (<CODE>)`. Tras un rechazo del backend el paquete se conserva para revisar, y se libera con «Quitar archivo». |
| LA-17 | 1280/390/320 sin desbordamiento; error con `role="alert"`; carga con `aria-busy`. |

## 5. Perfil de instalación (OD-LICACT-01 = A, dueña 2026-11-16)

Decisión de la dueña ante el conflicto con las E2E canónicas (49 de 112 usan rutas empresariales bajo una licencia de QA con
`gobierno`): **el perfil se deriva de los derechos firmados**.

| Perfil | Condición (solo `licensing_service.module_entitled`) | Menú y rutas |
|---|---|---|
| `GOBIERNO` | `gobierno` habilitado y ningún token empresarial habilitado | SHARED + GOVERNMENT; ENTERPRISE oculto y bloqueado |
| `MIXTO` | `gobierno` y al menos un token empresarial | SHARED + GOVERNMENT + ENTERPRISE (instalación de pruebas) |
| `EMPRESA` | sin `gobierno` | SHARED + ENTERPRISE; GOVERNMENT oculto y bloqueado |

Tokens empresariales = `ENTITLED_MODULES` sin `gobierno`: `ventas, compras, inventario, tesoreria, fiscal, regulatorio, reportes`.

| ID | Requisito |
|---|---|
| PF-01 | `GET /gobierno/modulo` (sesión, sin permiso de pantalla) devuelve `{habilitado, perfil}`; `habilitado` sigue siendo `module_entitled(db, "gobierno")` y nunca se deriva de permisos (PDD-LICACT-07). |
| PF-02 | `licensing_service.perfil_de_instalacion(db)` es la única derivación backend. |
| PF-03 | Frontend `app/perfil/superficies.ts`: `superficieDeRuta(ruta)` por prefijo explícito — `gobierno` → GOVERNMENT; `organizacion, maestros, inventario, compras, ventas, tesoreria, fiscal, regulatorio, comercial, reportes` → ENTERPRISE; todo lo demás → SHARED (Principal, Notificaciones/tareas/alertas/reglas/preferencias, Aprobaciones, Documentos, Licenciamiento, Homologación, Seguridad, Sistema). Fuente: `GOVERNMENT_PRODUCT_INVENTORY.md` §3 y su nota: «Reportes» es superficie de reportes privados aunque el motor 050 sea compartido (§63). |
| PF-04 | `usePerfilDeInstalacion()` → `{estado: "RESOLVIENDO" | "RESUELTO", perfil}`; `useModuloGobierno()` se conserva para sus consumidores. Un error de la consulta resuelve `EMPRESA` (semántica previa: sin Gobierno). |
| PF-05 | Menú: RESOLVIENDO → solo SHARED (sin destello). Luego, según la tabla, y siempre con `evaluarPantalla` y el `modulo: "gobierno"` existente. |
| PF-06 | Guard `RutaDePerfil` en `AppShell`, antes de `RutaAutorizada`: superficie no visible para el perfil → `ForbiddenState`; RESOLVIENDO y superficie no SHARED → `LoadingState`. `GOVERNMENT_PROFILE_DIRECT_ENTERPRISE_ROUTE=BLOCKED_UI`. |
| PF-07 | Tras activar, invalidar `["licencia","modulo","gobierno"]` recompone menú y guard sin recargar. |
| PF-08 | Siembra de QA (`qa/pg-e2e-seed.py`, `qa/licencia_firmada.py::MODULOS_DE_LA_SIEMBRA`): `gobierno` + los siete tokens empresariales → instalación MIXTA, menú como hoy. |

Frontera backend empresarial (§69): no hay `require_module` en las API empresariales. `ENTERPRISE_BACKEND_PROFILE_ENFORCEMENT=NOT_IMPLEMENTED`
→ deuda `LIC-PROFILE-BACKEND-ENTERPRISE-01` (MEDIUM; **CLOSED** para GOBIERNO y MIXTO en `spec004-license-ui-ux-profile-security-delta.md`): un usuario de una instalación GOBIERNO con permisos empresariales podría llamar
a esas API directamente. El backend de Gobierno conserva `require_module("gobierno")`.

## 6. Diálogo canónico

`ConfirmationDialog` (usado también por la reautenticación) gana, sin cambiar su API: trampa de foco (Tab/Shift+Tab ciclan dentro
del diálogo **solo si el foco ya está dentro**, para no interferir con otro diálogo) y devolución del foco al elemento que lo tenía al
abrirse.

## 7. Decisiones

- PDD-LICACT-01 El frontend no verifica firmas.
- PDD-LICACT-02 `apiFetch` conserva la autoridad de la reautenticación.
- PDD-LICACT-03 El paquete vive solo en memoria de la pantalla.
- PDD-LICACT-04 La activación refresca licencia y perfil sin recargar.
- PDD-LICACT-05 El perfil visual GOBIERNO lo selecciona el derecho firmado `gobierno` sin derechos empresariales (OD-LICACT-01 = A).
- PDD-LICACT-06 GOBIERNO muestra SHARED + GOVERNMENT y oculta ENTERPRISE (menú y rutas del frontend).
- PDD-LICACT-07 La autoridad backend de Gobierno sigue siendo `require_module("gobierno")`.
- PDD-LICACT-08 No se absorbe el enforcement de derechos en las API empresariales (deuda LIC-PROFILE-BACKEND-ENTERPRISE-01).
- PDD-LICACT-09 `minimum_version` se valida en backend antes de persistir (contrato §Reglas), sin dependencias nuevas.
- PDD-LICACT-10 Confirmar cierra el diálogo antes del POST: el diálogo de reautenticación aparece solo y la confirmación no se repite.

## 8. Pruebas

- Backend: `tests/test_license_minimum_version.py` (MINV-01..08) y `tests/test_gobierno_perfil.py` (PERF-01..04); regresión dirigida
  de licencia (activation, access, trust anchor, key rotation, period rollback, revision client/rules/race, import race) y del módulo
  de Gobierno.
- Vitest: `lib/paquete-de-licencia.test.ts`, `ActivarLicencia.test.tsx` (LICACT-01..27 y errores), `superficies.test.ts`,
  `Sidebar` (GOVPROF-01..14, 16..18), `RutaDePerfil.test.tsx` (GOVPROF-15), `ConfirmationDialog.test.tsx`.
- E2E `licencia-perfil.spec.ts` en el proyecto dependiente `licencia-perfil` (tras `licencia-tasa`): PENDING interceptado →
  paquete real `--modulos gobierno` → vista previa → confirmar → `REAUTH_REQUIRED` (primera respuesta interceptada; el login deja la
  reautenticación fresca) → reautenticación real → activación real → menú GOBIERNO sin recargar → pantalla de Gobierno responde →
  ruta empresarial bloqueada; negativos reales: otra instalación, firma alterada, `kid` desconocido. 1280/390/320 y Axe.

## 9. Fuera de alcance

Migraciones (`MIGRATION_REQUIRED=0`), endpoints nuevos, criptografía en el frontend, enforcement empresarial en backend,
reverificación de `minimum_version` en el arranque, métricas de Gobierno.
