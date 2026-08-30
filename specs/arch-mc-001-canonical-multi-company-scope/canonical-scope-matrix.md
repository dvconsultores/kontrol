# MATRIZ DE ALCANCE CANÓNICO — ARCH-MC-001

Derivada del modelo real por script. Las tablas sin columna de ámbito no se
adivinan: se resuelven por punto fijo siguiendo claves foráneas **obligatorias**
hasta una autoridad ya clasificada.

## 1. Vocabulario

| Alcance | Significado |
|---|---|
| `GLOBAL_SCOPE` | Igual para toda instalación; no pertenece a nadie |
| `INSTALLATION_SCOPE` | De la instalación: licencia, homologación, versión fiscal |
| `TENANT_SCOPE` | Del tenant, compartido por sus empresas |
| `COMPANY_SCOPE` | De una empresa jurídica concreta |
| `BRANCH_SCOPE` | De una sucursal |
| `DERIVED` | Determina su empresa por una FK **obligatoria** a una autoridad |

> No existe `UNKNOWN_SCOPE`. Las 166 tablas quedan clasificadas.

## 2. Recuento

| Alcance | Tablas |
|---|---:|
| `COMPANY_SCOPE` | 133 |
| `TENANT_SCOPE` | 14 |
| `INSTALLATION_SCOPE` | 16 |
| `GLOBAL_SCOPE` | 3 |
| **Total** | **166** |

De las de empresa:

| Forma | Tablas |
|---|---:|
| `DIRECT` — llevan `company_id` propio | 97 |
| `DERIVED` — lo determinan por FK obligatoria | 36 |

**Ninguna** deriva por una FK anulable. Eso importa: una ruta que puede ser
nula no es una ruta (§11 del encargo).

## 3. Estado actual frente al objetivo

| Estado actual | Tablas |
|---|---:|
| company_id (texto) = tenant_id | 90 |
| sin columna de ámbito | 56 |
| company_id + FK | 17 |
| tenant_id | 3 |

## 4. Las 14 del tenant — por qué lo son

| Tabla | Razón |
|---|---|
| `audit_events` | Lleva `tenant_id` y `company_id`; el segundo debe ser empresa real |
| `currencies` | Moneda: catálogo nacional |
| `exchange_rates` | Tasa BCV: nacional |
| `idempotency_records` | Infraestructura de petición |
| `legacy_document_references` | Anotación de migración documental |
| `outbox_events` | Infraestructura de mensajería |
| `password_resets` | Del usuario |
| `report_definitions` | Plantilla compartida del tenant |
| `role_permissions` | Deriva de `roles` |
| `roles` | Rol global o de empresa; `company_id` anulable ya lo expresa |
| `sessions` | Sesión del usuario |
| `user_roles` | Asignación de rol; su `company_id` **sí** es empresa (anulable) |
| `user_scopes` | Alcance del usuario; su `company_id` **sí** es empresa (anulable) |
| `users` | El usuario es del tenant; su acceso a empresas va aparte |

> `user_roles`, `user_scopes` y `audit_events` son del tenant como fila, pero su
> columna `company_id` **sí** designa una empresa y debe pasar a FK real. No es
> una contradicción: la fila pertenece al tenant, el alcance que expresa es de empresa.
