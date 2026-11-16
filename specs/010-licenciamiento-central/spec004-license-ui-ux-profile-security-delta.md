# Spec 004 · Delta · «Mi licencia» real, activación visible, perfil fail-closed y frontera del backend por perfil

Spec dueña: 010 Licenciamiento central.
Encargo: «P1 · Cierre integral de licenciamiento» (2026-11-16).
Entrada: 2f2ce4c (alembic 0121_gov_cnt09_alertas).
GOVERNMENT_PROCESS_INCREMENT=0. MIGRATION_REQUIRED=0.

## 1. Observación de la dueña y causa raíz (demostrada)

La dueña abrió «Mi licencia» y no encontró dónde cargar el archivo de licencia. **CODE_EXISTS ≠ OWNER_USABLE.**

| Candidata | Evidencia | Veredicto |
|---|---|---|
| D/E. El frontend servido no corresponde al HEAD | Las dos pilas UAT en pie se levantaron desde commits anteriores al delta de activación (6befc1c): 16773 desde b98d4e6 y 16873 desde 2d74eef. `git merge-base --is-ancestor 6befc1c` es falso en ambas. El `MiLicenciaPage.tsx` que sirven contiene 0 referencias a `ActivarLicencia` | **CAUSA 1 (la de su ambiente)** |
| A. `license.mode == FULL_ACCESS` | `GET /api/v1/license/status` en ambas pilas devuelve `{"mode":"FULL_ACCESS"}`. En el HEAD 2f2ce4c, `MODOS_DE_ACTIVACION` excluía FULL_ACCESS: aunque se reconstruyera la pila, la activación seguiría oculta | **CAUSA 2 (latente en HEAD)** |
| B. Falta `license:create` en `/auth/me` | El ADMIN canónico la recibe por la siembra. La E2E entra como admin y ve el control (LICUX-E2E-01/02) | Descartada |
| C, F, G | Sin evidencia distinta de D y A | No aplican |

**ROOT_CAUSE = D (pila UAT anterior al delta) + A (FULL_ACCESS ocultaba la acción en el HEAD).**

## 2. Decisiones de la dueña en este ciclo

- **OD-LICUX-01 = A.** En perfil EMPRESA (sin `gobierno` firmado) las API empresariales no cambian. Solo GOBIERNO y MIXTO ganan la frontera.
  Deuda nombrada: **LIC-PROFILE-ENTERPRISE-MODULE-01** (baja): en EMPRESA no se exige el derecho por módulo.
- **OD-LICUX-02 = A.** `/organization/companies` es SHARED: es el tenant de ambas líneas, y Gobierno crea su empresa o ente por ahí. Sucursales, establecimientos y la estructura de almacenes son ENTERPRISE.

## 3. Interfaz (frontend)

- **«Estado general».** Muestra:
  - perfil de producto: KONTROL Gobierno, Mixto o Enterprise, derivado de los derechos firmados vía `/gobierno/modulo`;
  - estado con etiqueta humana y el código técnico al lado;
  - instalación, período, «solo consulta desde» y versión mínima;
  - «Módulo Gobierno: Habilitado / No habilitado»;
  - «Módulos habilitados» en chips con nombre humano.
- **Solicitud de activación (solo PENDING).** Se conserva intacta: «Descargar solicitud» y «Copiar solicitud».
- **Activación en los seis modos.** Cada modo tiene su título, su botón de selección y su botón de aplicar:

  | Modo | Título | Selección | Aplicar | Destacada |
  |---|---|---|---|---|
  | PENDING | Activar licencia | Seleccionar archivo de licencia | Validar y activar licencia | sí |
  | FULL_ACCESS | Actualizar o reemplazar licencia | Seleccionar nueva licencia | Validar y aplicar licencia | no |
  | RENEWAL_NOTICE / CRITICAL_RENEWAL_NOTICE | Renovar licencia | Seleccionar licencia renovada | Validar y aplicar licencia | sí |
  | READ_ONLY | Reactivar licencia | Seleccionar licencia vigente | Validar y aplicar licencia | sí |
  | SECURITY_SUSPENSION | Restablecer licencia válida | Seleccionar licencia válida | Validar y aplicar licencia | sí |

- **Sin `license:create`.** Aparece la sección «Activar o actualizar licencia» con «No tiene permiso para activar o reemplazar licencias. Se requiere license:create.». No hay selector ni POST, y el backend sigue exigiendo el permiso (403).
- **Selector.** El rótulo es «Archivo de licencia firmado» y el botón de selección es la vía de teclado. Se muestra «Ningún archivo seleccionado» o «Archivo seleccionado: <nombre>», nunca la ruta local.
- **Vista previa.** Es una tarjeta con licencia, instalación, perfil, período, revisión, versión mínima, `kid`, empresas, usuarios y módulos. Nunca muestra `signature_hex`, el JSON ni claves.
- **Instalación.** Si coincide: «✓ Instalación verificada…», sin afirmar todavía la firma. Si no coincide: «Advertencia: Esta licencia fue emitida para otra instalación. El servidor la rechazará.»
- **Diálogo canónico.** Muestra perfil, instalación, licencia, período, revisión, `kid`, módulos, límites y versión mínima. La reautenticación sigue el flujo canónico de `apiFetch`: 403 `REAUTH_REQUIRED` → modal → reintento único.
- **Éxito.** Aviso inline y notificación «Licencia activada correctamente · Perfil · Estado · Licencia». Se invalidan las consultas y se llama a `refresh()`: el estado, el perfil y el menú cambian sin recargar.
- **Perfil fail-closed.** `EstadoDePerfil` = RESOLVIENDO | RESUELTO | ERROR. Un error ya no resuelve EMPRESA. En RESOLVIENDO o ERROR solo se ve lo SHARED. `RutaDePerfil` muestra un error explícito en las rutas GOVERNMENT y ENTERPRISE.

## 4. Backend

- **`require_enterprise_surface(module=None)`** (`app/core/dependencies.py`) es la autoridad reutilizable por superficie:
  - EMPRESA: sin cambio (OD-LICUX-01);
  - GOBIERNO: 403 `PRODUCT_PROFILE_DENIED`;
  - MIXTO: 403 `MODULE_NOT_ENTITLED` si falta el derecho del módulo.

  Se aplica por router en `include_router` con esta tabla:

  | Routers | Derecho exigido en MIXTO |
  |---|---|
  | almacenes, inventario, planificación, almacenamiento | inventario |
  | compras, importaciones | compras |
  | ventas, comercial | ventas |
  | tesorería | tesoreria |
  | fiscal | fiscal |
  | regulatorio | regulatorio |
  | reportes | reportes |
  | maestros, homologación | ninguno (base empresarial) |

  Además, por endpoint, en sucursales y establecimientos. `require_module("gobierno")` queda intacto. La prueba de inventario (penf_05) recorre `iter_route_contexts` y comprueba que ninguna ruta es a la vez ENTERPRISE y GOVERNMENT y que hay al menos 50 de cada tipo.
- **Reverificación de `minimum_version`** (cierra LIC-MINVER-REVERIFY-01):
  - `evaluate_current_artifact(…, running_version)` reutiliza `license_contract.minimum_version_satisfied`;
  - hay dos clases de fallo nuevas, `MINIMUM_VERSION_INVALID` y `MINIMUM_VERSION_INCOMPATIBLE`, incluidas en `FAILURES`. Siguen la semántica de DOC-07 para una reverificación inválida: SECURITY_SUSPENSION, escritura 423 y un evento `LICENSE_STATE_REVERIFICATION_FAILED` deduplicado;
  - el artefacto firmado no se modifica;
  - la versión en ejecución es `Settings.app_version` (`app.__version__`);
  - corre al arrancar y en cada `get_status`/`current_mode`, como el resto de la reverificación. La comprobación en la importación (paso 5c) se conserva.

## 5. Pruebas

- **Backend:** RVR-MV-01..05 (núcleo puro), PENF-01..05 (frontera por perfil e inventario de superficies) y MVR-01 (binario más antiguo que la versión mínima firmada → suspensión; se recupera al volver a la versión).
- **Guarda OpenAPI (OAS-14):** `_matriz_runtime` rechazaba toda dependencia añadida en `include_router`. Ahora admite solo la frontera de superficie (`kontrol_surface == "ENTERPRISE"`) que no llega a `get_current_auth`, y rechaza cualquier otra. FastAPI ordena las dependencias como inclusión y luego ruta.
  - OAS-14b: admite la frontera de superficie, también en una ruta con dependencia propia.
  - OAS-14c: rechaza otra dependencia de inclusión.
  - OAS-14d: rechaza una dependencia marcada que toca la autenticación.
- **Vitest:**
  - LICUX-01..12: seis modos, reemplazo en FULL_ACCESS, sin permiso, perfil en la página, MIXTO, error de perfil y orden solicitud → activación;
  - `licencia-presentacion`;
  - fail-closed en `superficies`, `RutaDePerfil` y Sidebar (GOVPROF-19).
- **E2E `licencia-perfil` (pantalla real, base nueva):**
  - LICUX-E2E-01: PENDING autorizado, descarga real de la solicitud, negativos reales, vista previa, reauth real, activación, KONTROL Gobierno sin recargar, API de Gobierno 200, API empresarial 403 `PRODUCT_PROFILE_DENIED` y ruta empresarial directa bloqueada;
  - LICUX-E2E-02: reemplazo en FULL_ACCESS;
  - LICUX-E2E-03: sin `license:create`, con POST 403;
  - LICUX-E2E-04: error de perfil fail-closed.
  - Evidencia visual a 1280, 390 y 320 px con Axe.

## 6. Deudas

- LIC-PROFILE-BACKEND-ENTERPRISE-01 → **CLOSED** para GOBIERNO y MIXTO.
- LIC-MINVER-REVERIFY-01 → **CLOSED**.
- Nueva: LIC-PROFILE-ENTERPRISE-MODULE-01 (baja, OD-LICUX-01): en EMPRESA no se exige el derecho por módulo.
- OBS-LICUX-UI-EMPRESAS-01 → **CLOSED** en `spec004-owner-uat-license-profile-menu-delta.md` §6 (la clasificación es la correcta). Texto original, baja: el menú «Empresas» sigue clasificado como ENTERPRISE en la interfaz, mientras su API es SHARED (OD-LICUX-02). Una instalación solo-Gobierno crea su empresa por la configuración inicial.
