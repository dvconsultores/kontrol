# PLAN — SPEC 045

## 1. Arquitectura del motor

Módulo nuevo `backend/app/modules/approvals/` (monolito modular, ADR-001). Es una **capacidad de
plataforma**: los dominios lo consumen a través de una fachada, nunca al revés.

```
  Dominio consumidor (purchasing, sales, inventory, treasury, fiscal, regulatory…)
        │
        │  approvals.require(process_type, document, context)   ← única entrada
        ▼
  ┌─────────────────────────────────────────────────────────────┐
  │  approvals                                                  │
  │                                                             │
  │  PolicyResolver   política vigente para (empresa, proceso)  │
  │  ConditionEvaluator  predicados tipados sobre el contexto   │
  │  ActorResolver    rol/usuario/delegación → actores elegibles│
  │  RequestService   ciclo de la solicitud y de los pasos      │
  │  FingerprintService  huella de obsolescencia                │
  │  EventEmitter     eventos de dominio (consumo futuro: 047)  │
  └─────────────────────────────────────────────────────────────┘
        │                          │
        ▼                          ▼
   AuditEvent (ADR-012)     AttachmentLink (ADR-D0-008, Spec 046)
```

### Regla de acoplamiento

> El módulo `approvals` **no importa** ningún módulo de dominio. Recibe un `context` plano
> (diccionario tipado) construido por el consumidor. Así un `process_type` nuevo no exige tocar el
> motor (FR-045-006) y el motor puede probarse sin ningún dominio.

## 2. Contrato de consumo

Tres operaciones que un dominio necesita:

| Operación | Cuándo la llama | Devuelve |
|---|---|---|
| `evaluate(process_type, context)` | Antes de enviar, para mostrar al usuario si requerirá aprobación | Niveles previstos, o «no requiere» |
| `require(process_type, document_ref, context, actor)` | Al enviar el documento | `ApprovalRequest` creada, o «no requiere» y el documento avanza |
| `status(document_ref)` | Al consultar el documento | Estado, pasos, decisiones y `allowed_actions` |

El dominio **no** decide si hay aprobación: pregunta. Esa inversión es lo que impide que vuelva a
aparecer una quinta implementación.

## 3. Fases

| Fase | Contenido | Depende de |
|---|---|---|
| **F1 · Modelo** | 7 tablas, migración, seeds de permisos y catálogo de `process_type` | PostgreSQL (BLK-D0-01) |
| **F2 · Motor** | `PolicyResolver`, `ConditionEvaluator`, `ActorResolver`, `FingerprintService` | F1 |
| **F3 · Ciclo** | `RequestService`: crear, aprobar, rechazar, devolver, cancelar, obsoletar; cuórum y niveles | F2 |
| **F4 · API** | Endpoints de configuración, bandeja, resolución y consulta; `allowed_actions` | F3 |
| **F5 · Frontend** | Pantallas completas de políticas, bandeja e historial | F4 |
| **F6 · Migración** | Las cuatro implementaciones actuales, con política equivalente previa | F3 |
| **F7 · Pruebas** | Unidad, integración, contrato, concurrencia, E2E, axe, responsive | F1-F6 |

## 4. Estrategia de migración

Es la parte con riesgo real. El orden importa:

1. **Crear política equivalente** por cada implementación actual, que reproduzca exactamente el
   comportamiento vigente (mismo punto de disparo, mismos resolutores, un nivel).
2. **Activar la política** y verificar en pruebas que el comportamiento no cambia.
3. **Redirigir el dominio** al motor, conservando su estado externo.
4. **Migrar el histórico** como solicitudes cerradas con `policy_version = LEGACY_UNVERSIONED`.
5. **Eliminar** la lógica propia del dominio.

> **Nunca** se ejecuta el paso 3 sin el 2 completado. El riesgo identificado en `research.md` §8 —que
> el sistema quede sin ningún control por falta de política— se evita porque la política equivalente
> existe antes del corte.

Clasificación: `BACKFILL_REQUIRED` + `MANUAL_REVIEW_REQUIRED` (ADR-D0-002 §Migración).

## 5. Decisiones técnicas

| Tema | Decisión | Fundamento |
|---|---|---|
| Condición | Predicados tipados con `AND`; el `OR` se expresa con varias reglas | CL-045-04 |
| Huella | SHA-256 sobre los campos de la condición, con la lista de campos almacenada | CL-045-05 |
| Concurrencia | Bloqueo de fila del paso dentro de la transacción; 409 al perdedor | ADR-013 |
| Idempotencia | Clave por `(document_ref, fingerprint)` | ADR-013, FR-045-053 |
| Moneda | Equivalente en base con tasa snapshot del documento | research §4 |
| Eventos | Registro en tabla propia del motor; sin cola (ADR-009 difiere workers) | ADR-009 |
| Adjuntos | `AttachmentLink` sobre `ApprovalRequest`; inactivo hasta Spec 046 | CL-045-10 |
| Permisos | `require_permission` con recurso `aprobaciones` | P6 |

## 6. Impacto en módulos existentes

| Módulo | Cambio | Riesgo |
|---|---|---|
| `purchasing` | Sustituye su transición de aprobación por llamada al motor | Medio — es la cadena mejor construida; no debe romperse |
| `sales` | Sustituye `CREDIT_PENDING`/`credit_decision` | Medio |
| `inventory` | Sustituye segregación codificada de ajustes y conteos | Bajo |
| `regulatory` | Migra `approval_requests` | Bajo |
| `identity_access` | Añade permisos del recurso `aprobaciones` al seed | Bajo |
| `audit` | Sin cambio: el motor usa `record_audit` existente | Ninguno |

## 7. Restricciones de esta iniciativa

- No se ejecuta `/speckit.implement` sin autorización expresa (P2).
- Toda la evidencia sobre PostgreSQL (P21) — depende de BLK-D0-01.
- Sin valores de negocio en código (P8).
- Pantallas completas, sin modales para configuración (P18, ADR-015).
