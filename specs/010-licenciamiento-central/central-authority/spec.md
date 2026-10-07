# SPEC 004 · COMPONENTE — AUTORIDAD CENTRAL DE LICENCIAS (FASE 1)

| Campo | Valor |
|---|---|
| Código | `004/central-authority` (componente desplegable de la Spec 004 Licenciamiento; **no** es un Master Spec: MASTER56 sigue en 56) |
| Nombre | Autoridad Central de Licencias — Fase 1: registro de instalaciones, libro de emisiones, `revision` firmada, paquete firmado por el propietario, CLI del propietario, health |
| Estado | ESPECIFICADA → en implementación (encargo `EMISOR-DE-LICENCIAS-SIN-IMPLEMENTAR + MATERIALIZACIÓN D0-06`, 2026-10-06) |
| Dueña | SPEC004 (`001-fundacion` + `010-licenciamiento-central`); apoyos 052 (frontera de despliegue) y 054 (QA) |
| Fuente | DOC-07 §4.1, §10.1–10.2, §11.1, §12.1, §15; ADR-D0-006; `spec004-licencia-revision-delta.md` (reglas de `revision` y compatibilidad canónica probada); `spec004-licencia-downgrade-fase-a-delta.md` |
| Ruta | `specs/010-licenciamiento-central/central-authority/` |

## 1. Problema

El cliente KONTROL verifica licencias firmadas por el propietario, pero el emisor —la Autoridad
Central que DOC-07 define— no existía en ningún repositorio. Sin emisor no hay `revision`
monótona (la reemisión dentro de un período no se ordena), no hay rotación posible de la clave y la
activación en línea no tiene servidor. D0-06 estaba `BUSINESS_DECISION_PENDING`; la dueña ratificó
la arquitectura: servicio central, del propietario, aislado del cliente, agnóstico de proveedor.

## 2. Decisiones ratificadas de la dueña

Servicio central independiente (backend, PostgreSQL, secretos, clave privada de firma propios),
fuera del Compose de cualquier cliente; Python + FastAPI + PostgreSQL + Alembic + contenedor, sin
colas ni workers; operación del propietario por **CLI** (sin API de administración pública);
`revision` entera ≥ 1, firmada, monótona por instalación + período, asignada solo por la autoridad,
reinicia en 1 por período; huecos permitidos, reutilización prohibida; `kid` identifica la clave y
no la revisión; una sola clave de firma activa; clave privada nunca en repositorio, base, cliente,
registro ni evidencia; en producción falta de clave → fallo cerrado; API de sync solo si la
autenticación del cliente existente está definida.

## 3. Alcance Fase 1

**Dentro:** registro de instalaciones · emisión y reemisión · paquete firmado canónico con
`revision` · custodia de la clave privada por configuración · libro de emisiones inmutable ·
linaje de `revision` transaccional y seguro en concurrencia · `kid` según semántica actual ·
auditoría de operaciones · health mínimo · firmante sintético de QA explícito · despliegue
independiente documentado y agnóstico de proveedor · pruebas de contrato con el verificador del
cliente.

**Fuera:** rotación de claves, varias claves, retiro de claves, portales, facturación, pagos,
paneles, autoservicio, rollback de emergencia, integraciones, comparación de `revision` en el
cliente, reverificación del estado, rediseño de la activación en línea, **API de sync productiva**
(bloqueada: §6).

## 4. Requisitos (FR-010-267..321 = FR-CLA-001..055 del encargo)

| FR | Requisito |
|---|---|
| 267 · 268 | Existe una Autoridad Central independiente de las instalaciones; pertenece a SPEC004 sin Master 57 |
| 269 · 270 | PostgreSQL propio; sin compartir base, volúmenes, secretos ni claves con clientes |
| 271 · 272 · 273 · 274 | La clave privada del propietario solo en infraestructura central; no en repositorio; no viaja al cliente; en producción no se genera automáticamente si falta |
| 275 · 276 | Registro de instalaciones con identidad canónica única |
| 277 · 278 | Libro de emisiones; las emisiones históricas no se editan por los flujos de Fase 1 |
| 279 · 280 · 281 · 282 · 283 · 284 · 285 · 286 · 287 | Toda emisión produce un paquete firmado por el propietario con `revision` entera ≥ 1, firmada, por instalación + período; primera revisionada = 1; reemisión → mayor; concurrentes → distintas; sin reutilización para payloads distintos; reinicia en 1 por período |
| 288 · 289 · 290 · 291 · 292 · 293 · 294 | `revision` no depende de `kid`, de la fecha de la base ni del orden de llegada; los derechos suben o bajan sin definir el orden; `kid` conserva su semántica; una sola clave activa; sin rotación |
| 295 · 296 | CLI del propietario para registrar, emitir y reemitir; sin API de administración pública |
| 297 · 298 · 299 | API de sync solo si su autenticación está definida canónicamente; sin lecturas cruzadas; instalación desconocida sin fuga |
| 300 · 301 | `/health/live` y `/health/ready` mínimos sin información sensible |
| 302 · 303 · 304 · 305 · 306 | Frontera de despliegue separada del Compose cliente; esquema del cliente intacto; migraciones propias; instalación limpia; constraints e índices |
| 307 · 308 · 309 | Asignación de `revision` transaccional y segura en PostgreSQL; el artefacto exacto se reconstruye desde el libro |
| 310 · 311 | `issued_at` técnico (UTC) no ordena; las reglas de negocio siguen en `America/Caracas` |
| 312 · 313 | Canonicalización preservada; una legacy nunca se reconstruye con `revision: null` |
| 314 · 315 · 316 | Firmante sintético explícito en QA, nunca activo por defecto en producción; sin claves, credenciales ni licencias reales en registros ni evidencia |
| 317 · 318 | Prueba de contrato paquete central ↔ verificador/cliente; si el cliente no pudiera consumirlo, despliegue productivo bloqueado |
| 319 · 320 · 321 | D0-06 actualizado (frontera, agnóstico de proveedor); MASTER56 = 56; `NEXT SPEC = 029` |

## 5. Historias mínimas

- Como propietario, registro una instalación con su identidad y clave pública y emito su primera
  licencia firmada del período en curso.
- Como propietario, reemito la licencia del mismo período con más o menos derechos, y el cliente
  podrá ordenar las dos reemisiones cuando compare `revision`.
- Como operador del propietario, consulto qué se emitió a una instalación y con qué `revision`.
- Como auditor, veo quién emitió qué, cuándo y con qué resultado, sin poder alterarlo.

## 6. Bloqueo separado: la API de sync

El cliente existente (`default_sync_client`) envía `POST {server_url}/v1/license/sync` **sin
autenticación**: solo `installation_id`, `license_jws`, `modules` y `requested_at`. Exponer un
servidor para ese contrato sería «conozco el `installation_id`, dame la licencia». Regla del
encargo: `CENTRAL-SYNC-AUTHORITY-UNDEFINED — MATERIAL_DECISION_REQUIRED`. La Fase 1 **no** expone la
API de sync; el núcleo del emisor se cierra sin afirmar que el sync productivo esté listo.
