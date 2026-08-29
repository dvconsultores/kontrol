# ADR-D0-002 — Motor transversal de aprobaciones y segregación

| Campo | Valor |
|---|---|
| ID | D0-02 |
| Estado | **APPROVED** (arquitectura) · configuración empresarial pendiente |
| Fecha | 2026-08-29 |
| Responsable | Arquitecto empresarial · Arquitecto backend · Auditor interno · Product Owner |
| Specs afectadas | **045** (propietaria) · 015, 017, 018, 025, 026, 028, 030, 033, 034, 036, 040, 042 |

## Problema

No existe un motor de aprobaciones. Existen **cuatro implementaciones divergentes** y una tabla
suelta, cada una con su propio modelo de datos, sus propios estados y su propia noción de quién
puede aprobar qué.

## Por qué debe decidirse ahora

Es el nodo de mayor grado de salida del grafo de dependencias: bloquea seis Specs directamente.
Cada Spec nueva que resuelva su aprobación por su cuenta añade un quinto, un sexto y un séptimo
modelo que después habrá que migrar. El coste de la decisión crece linealmente con cada Spec escrita.

Además hay un problema de control interno: sin motor único no se puede garantizar la segregación de
funciones que la Constitución exige (P5, y la regla «un usuario no crea y aprueba su propia
excepción crítica» del Vol. 1 §5).

## Evidencia

| Implementación actual | Ubicación | Modelo |
|---|---|---|
| Aprobación de requisición y orden de compra | `purchasing/service.py` | Transición de estado + `approval_ref` textual |
| Aprobación de crédito de venta | `sales/service.py` | Estado `CREDIT_PENDING` + `credit_decision` |
| Segregación de ajustes de inventario | `inventory/service.py` | Campos crea/revisa/aprueba en la propia entidad |
| Aprobación regulatoria | `regulatory/models.py` | Tabla `approval_requests` con decisión |

Cuatro semánticas distintas de «aprobado», ninguna versionada, ninguna con delegación, ninguna con
bandeja, y solo una con entidad propia.

## Alternativas

**A. Consolidar sobre `approval_requests` (regulatorio) extendiéndola.**
Reutiliza lo existente. Descartada: esa tabla se diseñó para un caso concreto (solicitud de
aprobación de un permiso), no tiene niveles, ni política versionada, ni delegación, y arrastraría un
modelo estrecho a todo el sistema.

**B. Motor transversal nuevo con política versionada.** ← **RECOMENDADA**
Un solo modelo, configurable por empresa, versionado, con snapshot en la solicitud. Las cuatro
implementaciones actuales migran hacia él.

**C. Dejar que cada módulo mantenga su aprobación y unificar solo la bandeja de UI.**
Descartada: la inconsistencia sería de datos y de reglas, no de presentación. Una bandeja sobre
cuatro modelos distintos no puede aplicar una política común ni auditar de forma homogénea.

## Modelo conceptual

```
ApprovalPolicy            (empresa · proceso · versión · vigencia · estado)
 └── ApprovalRule         (condición de disparo → niveles requeridos)
      └── ApprovalLevel   (orden · resolutor · cuórum · puede_delegar)

ApprovalRequest           (documento · política_versión_snapshot · huella_documento · estado)
 └── ApprovalStep         (nivel · asignado · estado · vencimiento)
      └── ApprovalDecision(actor · decisión · motivo · momento · delegación_origen)

ApprovalDelegation        (otorgante · receptor · ámbito · vigencia · revocable)
ApprovalActorResolution   (regla → conjunto de actores elegibles en el momento de crear el paso)
```

`ApprovalException` y `ApprovalAudit` no son entidades nuevas: una excepción es una `ApprovalRequest`
cuyo `process_type` es de excepción, y la auditoría se registra en `audit_events` (ADR-012), sin
crear un segundo rastro paralelo.

### Dimensiones de condición admitidas por `ApprovalRule`

Empresa · tipo de proceso · monto · moneda · **monto equivalente en moneda base a la tasa del
documento** · porcentaje (descuento, sobrecosto, varianza) · sucursal · centro de costo · almacén ·
rol · usuario · categoría de operación · clasificación de riesgo · condición comercial · marca de
excepción.

> El monto se evalúa **siempre** sobre el equivalente en moneda base con la tasa snapshot del
> documento. Comparar montos en monedas distintas contra un mismo umbral es un error de diseño en
> un producto multimoneda.

## Estados

`ApprovalRequest`: `DRAFT → PENDING → IN_REVIEW → {APPROVED | REJECTED | RETURNED | CANCELLED | OBSOLETE}`

- `RETURNED` devuelve el documento a corrección y conserva el historial de decisiones.
- `OBSOLETE` se alcanza automáticamente cuando la huella del documento cambia antes de resolverse.

## Reglas de negocio

| ID | Regla |
|---|---|
| R-D0-02-1 | Los niveles, umbrales y resolutores **no se hardcodean**. Son datos de configuración por empresa. |
| R-D0-02-2 | Toda `ApprovalPolicy` es **versionada** con vigencia y estado. |
| R-D0-02-3 | La `ApprovalRequest` guarda **snapshot de la versión de política aplicada**. Cambiar la política no altera solicitudes ya resueltas ni documentos históricos. |
| R-D0-02-4 | Toda decisión queda auditada con actor, momento, motivo y, si aplica, la delegación que la habilitó. |
| R-D0-02-5 | La política puede exigir segregación de funciones. Cuando lo hace, el creador del documento **no** puede resolver ningún paso. |
| R-D0-02-6 | Un paso admite uno o varios resolutores con cuórum configurable (cualquiera / todos / N de M). |
| R-D0-02-7 | El rechazo es terminal para la solicitud; el documento vuelve a su estado editable anterior. |
| R-D0-02-8 | La delegación es explícita, acotada en ámbito y vigencia, revocable y auditada. Una delegación **no** puede saltarse la segregación de R-D0-02-5. |
| R-D0-02-9 | Si el documento cambia en cualquier campo que participe en la condición de la regla, la solicitud pasa a `OBSOLETE` y debe volver a solicitarse. La detección se hace por huella de los campos relevantes, no del documento entero. |
| R-D0-02-10 | Ningún módulo puede implementar su propia aprobación. Las cuatro implementaciones actuales se migran a este motor. |

## Frontera producto / cliente

| Decide KONTROL (ahora) | Configura cada empresa (después) |
|---|---|
| Que el motor existe y es transversal | Cuántos niveles tiene cada proceso |
| Las entidades y sus relaciones | Los umbrales de monto |
| Que la política se versiona y se congela en snapshot | Quién resuelve cada nivel |
| Que la segregación es configurable | Si su operación exige segregación |
| Que existe delegación acotada | A quién se delega y por cuánto tiempo |
| Las dimensiones de condición disponibles | Qué dimensiones usa realmente |

**No se inventan montos, niveles ni responsables.** Ver `D0-open-questions.md` OQ-02.

## Impacto

| Dimensión | Impacto |
|---|---|
| Frontend | Bandeja «Mis aprobaciones», pantalla de políticas, acciones de aprobar/rechazar/devolver/delegar en cada documento |
| Backend | Módulo nuevo `approvals`; los 4 módulos actuales delegan en él |
| Base de datos | 6 tablas nuevas; migración de las aprobaciones existentes |
| Integraciones | Notificaciones (Spec 047) consumirá los eventos del motor |
| QA | Pruebas de segregación, cuórum, obsolescencia y delegación; concurrencia de decisiones |
| Seguridad | Positivo — la autorización deja de estar dispersa (P6) |
| Fiscal | Aplica a operaciones fiscales críticas (anulación, nota, reapertura de período) |

## Migración / compatibilidad

**`BACKFILL_REQUIRED`** con **`MANUAL_REVIEW_REQUIRED`**.

Las aprobaciones históricas no tienen política asociada porque la política no existía. Se migran
como `ApprovalRequest` cerradas con `policy_version = LEGACY_UNVERSIONED` y una marca explícita.
**No se inventa retroactivamente qué política se aplicó**; se registra que se desconoce.

## Criterios de aceptación

- [ ] Una misma política aplica a compras, ajustes, crédito, pagos y notas sin código duplicado.
- [ ] Cambiar una política no altera ninguna solicitud ya resuelta.
- [ ] Con segregación activa, el creador no puede aprobar (probado).
- [ ] Modificar el documento antes de resolver deja la solicitud `OBSOLETE` (probado).
- [ ] La delegación no permite saltarse la segregación (probado).
- [ ] Las cuatro implementaciones anteriores ya no existen como lógica propia.

## Estado final

**APPROVED** — arquitectura cerrada.
Clasificación de cierre: **CLOSED_WITH_CONFIGURATION_PENDING**.
