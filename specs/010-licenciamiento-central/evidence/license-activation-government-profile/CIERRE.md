# Cierre · Activar licencia desde «Mi licencia» + perfil KONTROL Gobierno

Delta de la Spec 010: `spec004-manual-license-activation-ui-government-profile-delta.md`.

**Estado:** COMPLETE. La aceptación (OWNER_ACCEPTED) queda pendiente de la dueña. Delta de licenciamiento: GOVERNMENT_PROCESS_INCREMENT=0.

## Base y reconciliación

- Entrada: 742882f (alembic 0121_gov_cnt09_alertas).
- Durante el ciclo se integró con un merge ordinario la e758ada de P2 (presentación instantánea de CNT-08). Sin rebase ni force.
- MIGRATION_REQUIRED=0 y ALEMBIC_HEAD_COUNT=1. Ninguna migración publicada se modificó.

## Alcance

**Flujo.** La administradora:
1. descarga la solicitud;
2. la Autoridad Central emite la licencia;
3. la administradora carga el JSON firmado y ve la vista previa;
4. confirma en el diálogo canónico y se reautentica en el flujo canónico (`apiFetch`);
5. se llama a `POST /license/activate` con el cuerpo exacto `{payload, signature_hex}`, sin tocar el payload.

Después, el contexto se refresca sin recargar la página y aparece el perfil.

**Autoridad del backend, sin cambios.** El backend sigue verificando el ancla de confianza, el `kid`, la firma Ed25519, la instalación, el período, la revisión y la concurrencia. En el frontend no hay criptografía.

**Cambio de semántica en el backend.** `minimum_version` lo exigía el contrato y no se comprobaba. Ahora se valida en el paso 5c:
- un valor inválido devuelve `LICENSE_INVALID_MINIMUM_VERSION`;
- una versión incompatible devuelve `LICENSE_MINIMUM_VERSION_INCOMPATIBLE`;
- en ambos casos la respuesta es 423 y queda el evento auditado `LICENSE_MINIMUM_VERSION_REJECTED`.

**Paquete.** Vive solo en memoria: nada en `localStorage`, `sessionStorage`, IndexedDB ni Cache API, y nada va a la consola. Un fichero con clave privada se rechaza sin enviarlo.

**Perfil (OD-LICACT-01 = A).** Se deriva de los derechos firmados:
- GOBIERNO: `gobierno` sin ningún token empresarial;
- MIXTO: `gobierno` con alguno;
- EMPRESA: sin `gobierno`.

`/gobierno/modulo` devuelve `{habilitado, perfil}`. Con el perfil se clasifica el menú por superficie (SHARED, GOVERNMENT o ENTERPRISE) y la guarda de rutas `RutaDePerfil` actúa sobre él. Mientras el perfil se resuelve no se muestra Empresa, y los permisos siguen aplicándose.

**Deudas.**
- LIC-PROFILE-BACKEND-ENTERPRISE-01: el backend no restringe el perfil en las rutas empresariales; queda auditado y documentado.
- LIC-MINVER-REVERIFY-01: la versión mínima no se reverifica al arrancar.

## Verificación

| Comprobación | Resultado |
|---|---|
| PG completa, una vez, sobre el árbol final del backend (`qa/suite_tiempos.py --motor postgres --con-analizador`, run r20261116t105842p1361843n81c748) | 5652 pasan / 6 fallan / 18 omitidas |
| Fallos de línea base | 5: imb_07 pip check, n10 ORM↔base, guard_d01 y 2 de spec019 receipt |
| Regresión del ciclo | 1: `test_e2ecorrida_14`. La guarda fijaba la orden canónica sin el proyecto nuevo. Corregida por DeepSeek (D9, excepción 3); `test_e2e_corrida.py` pasa sobre PG |
| PG dirigida: licencia, versión mínima, perfil, gov0 | verde (n10 de línea base) |
| Vitest | 2256/2256 |
| tsc, eslint y build | 0 errores, build OK |
| ruff | limpio |
| mypy | solo los 2 errores de línea base (company_context) |
| E2E `licencia-perfil` (LICACT-E2E-01: negativas reales, reauth por la interfaz, perfil sin recarga, Axe a 1280/390/320; run r20261116t114008p1887199n958602) | 1/1, 0 reintentos |

**Atribución de la E2E.** Los 11 fallos de la chromium completa son iguales sobre la base 742882f. Planificación es intermitente: pasó al repetirla. La spec del expediente es OBS-CNT08-E2E-VALIDO-01, de P2.

## DeepSeek

- 11 llamadas, todas a `deepseek-v4-pro`: 8 del tope y 3 autorizadas por la dueña.
- 45.837 tokens de entrada y 41.525 de salida, USD 0,0560. OWNER_EXCEPTION_USED=3.
- Detalle en ATTEMPT_LOG.md.
- CLAUDE_SEMANTIC_CODE_WRITTEN=0.

## Métricas de Gobierno

Sin cambios: 43 de 122 OWNER_UAT_READY y 441 de 1268 gates. CNT-08 y CNT-09 siguen OWNER_UAT_READY.

## Seguridad

SECRET_EXPOSURE=0 · PRIVATE_KEY_READ=0 · PACKAGE_PERSISTED_IN_BROWSER=0 · SNAT_TOUCHED=0 · PRODUCTION_TOUCHED=0. Las credenciales no se registran.
