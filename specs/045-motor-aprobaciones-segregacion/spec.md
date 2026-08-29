# SPEC 045 — MOTOR DE APROBACIONES Y SEGREGACIÓN

| Campo | Valor |
|---|---|
| Iniciativa | `045-motor-aprobaciones-segregacion` |
| Spec maestra | **045** (catálogo de 56) |
| Versión | 1.0 |
| Estado | Especificada — **sin autorización de implementación** |
| Rama | `develop` |
| Fecha | 2026-08-29 |
| Autoridad | Constitución v1.1 · `ADR-D0-002` · `POL-D0-001` · Baseline arquitectónica v1.0 |
| Prioridad | **P0** — nodo de mayor grado del grafo de dependencias |

---

## 1. Propósito

Construir **un único motor transversal de aprobaciones** para toda la plataforma: parametrizable por
empresa, con políticas versionadas, segregación de funciones configurable y auditoría completa.

No es una pantalla de aprobaciones. Es una **capacidad de plataforma** que otros dominios consumen.

## 2. Por qué esta Spec es la primera del roadmap

Tres razones convergentes:

1. **Grado del grafo.** Bloquea directamente a 015, 017, 025, 030, 033 y 047 (`D0-spec-dependencies.md`).
2. **Deuda que crece.** Ya existen **cuatro implementaciones divergentes** de aprobación en el código.
   Cada Spec nueva que resuelva la suya añade una quinta.
3. **Obligación constitucional.** El Principio 22 (Constitución v1.1) exige autoridad única por
   capacidad transversal. Un quinto motor sería una violación, no una decisión de diseño.

### Las cuatro implementaciones que este motor sustituye

| Dominio | Ubicación | Semántica actual |
|---|---|---|
| Compras | `purchasing/service.py` | Transición de estado + `approval_ref` textual |
| Ventas | `sales/service.py` | Estado `CREDIT_PENDING` + `credit_decision` |
| Inventario | `inventory/service.py` | Campos crea/revisa/aprueba en la propia entidad |
| Regulatorio | `regulatory/models.py` | Tabla `approval_requests` con decisión |

Cuatro nociones distintas de «aprobado», ninguna versionada, ninguna con delegación, ninguna con
bandeja, y solo una con entidad propia.

## 3. Alcance

### Incluido

1. **Configuración**: políticas de aprobación por empresa y por tipo de proceso, versionadas con
   vigencia, con reglas y niveles.
2. **Motor de evaluación**: dada una operación, determinar si requiere aprobación, qué niveles y qué
   actores, y crear la solicitud correspondiente.
3. **Ciclo de resolución**: aprobar, rechazar, devolver para corrección, cancelar; con cuórum por
   nivel y motivo obligatorio en las decisiones negativas.
4. **Segregación de funciones**: restricción configurable de autoaprobación y de participación del
   creador.
5. **Delegación y sustitución temporal**: acotadas en ámbito y vigencia, revocables y auditadas.
6. **Obsolescencia**: detección automática cuando el documento cambia después de solicitar aprobación.
7. **Bandeja de trabajo**: «Mis aprobaciones» con filtros, y consulta del historial por documento.
8. **Auditoría**: todo evento del motor registrado mediante `AuditEvent` (ADR-012).
9. **API transversal** que los demás módulos consumen; sin lógica de aprobación fuera del motor.
10. **Migración de las cuatro implementaciones actuales** al motor único.
11. **Evidencias**: contrato de adjuntos preparado para la arquitectura documental de la Spec 046.
12. **Eventos de dominio** para que la Spec 047 (notificaciones) los consuma sin acoplarse.

### Fuera de alcance

- **Envío de notificaciones y correo** — Spec 047. Este motor **emite eventos**; no notifica.
- **Almacenamiento de archivos** — Spec 046. Este motor **vincula** adjuntos; no los guarda.
- **Reglas de negocio de cada dominio** (qué es una desviación de recepción, qué es un descuento
  excesivo). Cada Spec consumidora define su condición; el motor la evalúa.
- **Umbrales, niveles y responsables concretos** de ninguna empresa: son configuración (`OQ-02`).
- **Flujos de trabajo generales (BPM)**: el motor resuelve aprobaciones, no orquestación arbitraria.

### Dependencias con Specs no construidas

| Dependencia | Spec | Tratamiento en 045 |
|---|---|---|
| Adjuntos de evidencia | **046** | Se define el contrato `AttachmentLink` sobre `ApprovalRequest`. Mientras 046 no exista, la evidencia se limita a `reason` y `observations` en texto. La Spec 046 **no** requerirá cambios en el modelo de 045 |
| Notificaciones y tareas | **047** | 045 emite eventos de dominio (`approval.requested`, `approval.resolved`, `approval.obsolete`, `approval.escalated`). 047 los consumirá. 045 **no** conoce a 047 |
| Moneda base y tasa | 013 (implementado) | El motor consume la tasa snapshot del documento; no la calcula |
| Alcance de usuario | 003, `ADR-D0-013` | La resolución de actores usa el vocabulario de alcance existente; no crea uno propio |

## 4. Actores

| Actor | Uso del motor |
|---|---|
| Administrador de empresa | Configura políticas, reglas, niveles y segregación |
| Solicitante | Cualquier usuario cuya operación dispara una solicitud |
| Aprobador | Resuelve los pasos que le corresponden por rol, usuario o delegación |
| Delegante / delegado | Otorga y ejerce una delegación acotada |
| Auditor | Consulta el historial completo sin poder resolver |
| Sistema | Marca solicitudes obsoletas y vencidas |

## 5. Historias de usuario

**HU-045-01 · Configurar una política**
Como administrador de empresa quiero definir, para un tipo de proceso, qué condiciones exigen
aprobación y cuántos niveles se requieren, **para** que las autorizaciones dejen de depender del
criterio individual de cada operador.
*Criterio:* puedo crear una política con vigencia, añadir reglas con condiciones y niveles, y
activarla. Al activarla, la versión anterior cierra su vigencia sin alterar solicitudes ya resueltas.

**HU-045-02 · Solicitar aprobación sin saber que existe el motor**
Como usuario de compras quiero que, al enviar una orden que supera el umbral, el sistema cree la
solicitud automáticamente, **para** no tener que conocer la política.
*Criterio:* la orden pasa a un estado que impide su avance; existe una `ApprovalRequest` con la
versión de política congelada.

**HU-045-03 · Resolver desde una bandeja única**
Como aprobador quiero ver en un solo lugar todo lo que espera mi decisión, con el contexto suficiente
para decidir, **para** no perseguir aprobaciones por módulo.
*Criterio:* «Mis aprobaciones» lista solicitudes de cualquier dominio, con documento, monto en moneda
base, solicitante, antigüedad y vencimiento; puedo aprobar, rechazar o devolver con motivo.

**HU-045-04 · No poder aprobar lo mío**
Como auditor interno quiero que el creador de un documento no pueda resolver su propia solicitud
cuando la política lo exija, **para** sostener la segregación de funciones.
*Criterio:* con segregación activa, el creador no aparece como actor elegible y un intento directo
por API devuelve 403 con motivo explícito.

**HU-045-05 · Devolver para corrección sin perder el historial**
Como aprobador quiero devolver un documento con observaciones en lugar de rechazarlo, **para** que se
corrija y vuelva sin empezar de cero.
*Criterio:* el documento vuelve a estado editable, la solicitud conserva las decisiones previas, y al
reenviarse se crea una solicitud nueva vinculada a la anterior.

**HU-045-06 · Delegar durante una ausencia**
Como aprobador quiero delegar mis aprobaciones por un período y un ámbito determinados, **para** que
la operación no se detenga cuando no estoy.
*Criterio:* la delegación tiene vigencia y ámbito; el delegado resuelve y la decisión registra que
actuó por delegación; la delegación **no** permite saltarse la segregación.

**HU-045-07 · No aprobar algo que ya cambió**
Como aprobador quiero que una solicitud quede invalidada si el documento se modificó después de
solicitarla, **para** no autorizar algo distinto de lo que revisé.
*Criterio:* al cambiar un campo que participa en la condición, la solicitud pasa a `OBSOLETE` y no
admite resolución; el documento debe volver a solicitarla.

**HU-045-08 · Auditar quién autorizó qué**
Como auditor quiero reconstruir, para cualquier documento, quién autorizó, cuándo, bajo qué política
y con qué motivo, **para** responder a una fiscalización.
*Criterio:* el historial muestra la versión de política aplicada, los actores elegibles en su momento,
cada decisión con motivo y la cadena de delegación si la hubo.

**HU-045-09 · Cuórum de varios aprobadores**
Como administrador quiero exigir que un nivel lo resuelvan varias personas, **para** operaciones de
riesgo elevado.
*Criterio:* configuro cuórum «todos» o «N de M»; el paso solo avanza al alcanzarse.

**HU-045-10 · Aprobación multinivel secuencial**
Como administrador quiero que una operación recorra varios niveles en orden, **para** reflejar la
cadena de autoridad.
*Criterio:* el nivel 2 no se abre hasta que el nivel 1 se resuelve favorablemente; un rechazo en
cualquier nivel es terminal para la solicitud.

## 6. Requisitos funcionales

### Configuración de políticas

| ID | Requisito | Prioridad | Fuente |
|---|---|---|---|
| FR-045-001 | Crear, editar y versionar `ApprovalPolicy` por empresa y tipo de proceso, con vigencia y estado | P0 | ADR-D0-002 R-D0-02-2 |
| FR-045-002 | Definir `ApprovalRule` con condición de disparo y niveles requeridos | P0 | ADR-D0-002 |
| FR-045-003 | Definir `ApprovalLevel` con orden, resolutores, cuórum y permiso de delegación | P0 | ADR-D0-002 |
| FR-045-004 | Activar una versión de política cierra la vigencia de la anterior sin alterar solicitudes resueltas | P0 | R-D0-02-3 |
| FR-045-005 | Las políticas no se eliminan: se cierran por vigencia | P0 | POL-D0-001 §4.7 |
| FR-045-006 | El catálogo de tipos de proceso es extensible sin cambio de código de este módulo | P0 | P8 |
| FR-045-007 | Una política puede declarar exigencia de segregación de funciones | P0 | R-D0-02-5 |
| FR-045-008 | Simular una política contra un documento de prueba sin crear solicitud | P2 | UX |

### Condiciones y evaluación

| ID | Requisito | Prioridad | Fuente |
|---|---|---|---|
| FR-045-010 | Evaluar condiciones sobre: empresa, tipo de proceso, monto, moneda, **monto equivalente en moneda base**, porcentaje, sucursal, centro de costo, almacén, rol, usuario, categoría de operación, clasificación de riesgo, condición comercial y marca de excepción | P0 | ADR-D0-002 |
| FR-045-011 | **El monto se evalúa siempre sobre el equivalente en moneda base con la tasa snapshot del documento** | P0 | R-D0-02 §Dimensiones |
| FR-045-012 | Si ninguna regla aplica, la operación **no** requiere aprobación y avanza | P0 | Diseño |
| FR-045-013 | Si aplican varias reglas, se acumulan los niveles y se eliminan duplicados conservando el orden mayor | P0 | Diseño |
| FR-045-014 | La resolución de actores elegibles se congela al abrir cada paso | P0 | HU-045-08 |
| FR-045-015 | Una condición que no puede evaluarse (dato ausente) genera error explícito, nunca un «no requiere aprobación» silencioso | P0 | P6 |

### Ciclo de la solicitud

| ID | Requisito | Prioridad | Fuente |
|---|---|---|---|
| FR-045-020 | Crear `ApprovalRequest` con snapshot de la versión de política y huella del documento | P0 | R-D0-02-3, R-D0-02-9 |
| FR-045-021 | Estados: `DRAFT → PENDING → IN_REVIEW → {APPROVED, REJECTED, RETURNED, CANCELLED, OBSOLETE}` | P0 | ADR-D0-002 |
| FR-045-022 | Aprobar un paso; al completarse el cuórum se abre el siguiente nivel | P0 | HU-045-10 |
| FR-045-023 | Rechazar es terminal para la solicitud; el documento vuelve a estado editable | P0 | R-D0-02-7 |
| FR-045-024 | Devolver para corrección conserva el historial y devuelve el documento a edición | P0 | HU-045-05 |
| FR-045-025 | Cancelar la solicitud (por el solicitante o por política) sin resolver | P0 | ADR-D0-002 |
| FR-045-026 | Motivo **obligatorio** en rechazo y devolución; opcional en aprobación | P0 | Auditoría |
| FR-045-027 | Un paso admite vencimiento configurable; el vencimiento no resuelve por sí solo, marca y notifica | P1 | POL-D0-001 |
| FR-045-028 | Cuórum por nivel: cualquiera · todos · N de M | P0 | HU-045-09 |
| FR-045-029 | Un documento no avanza a su siguiente estado sin solicitud resuelta favorablemente | P0 | POL-D0-001 §4.2 |
| FR-045-030 | Reenviar tras devolución crea una solicitud nueva **vinculada** a la anterior | P0 | HU-045-05 |

### Segregación y delegación

| ID | Requisito | Prioridad | Fuente |
|---|---|---|---|
| FR-045-040 | Con segregación activa, el creador del documento no es actor elegible en ningún paso | P0 | R-D0-02-5 |
| FR-045-041 | Restricción de autoaprobación configurable e independiente de la segregación general | P0 | Encargo |
| FR-045-042 | Delegación con otorgante, receptor, ámbito, vigencia y revocabilidad | P0 | R-D0-02-8 |
| FR-045-043 | **La delegación no puede eludir la segregación**: el delegado hereda las restricciones del delegante y las suyas propias | P0 | R-D0-02-8 |
| FR-045-044 | Sustitución temporal (ausencia) como delegación con vigencia acotada y motivo | P1 | Encargo |
| FR-045-045 | La decisión registra si se ejerció por delegación y cuál | P0 | HU-045-08 |
| FR-045-046 | Una delegación revocada no invalida decisiones ya tomadas bajo ella | P0 | P5 |

### Obsolescencia, idempotencia y concurrencia

| ID | Requisito | Prioridad | Fuente |
|---|---|---|---|
| FR-045-050 | Calcular huella sobre **los campos que participan en la condición**, no sobre el documento completo | P0 | R-D0-02-9 |
| FR-045-051 | Cambiar un campo de la huella marca la solicitud `OBSOLETE` automáticamente | P0 | HU-045-07 |
| FR-045-052 | Una solicitud `OBSOLETE` no admite resolución | P0 | R-D0-02-9 |
| FR-045-053 | Creación de solicitud idempotente por documento y versión de huella | P0 | ADR-013 |
| FR-045-054 | Dos decisiones concurrentes sobre el mismo paso: exactamente una prospera; la otra recibe 409 | P0 | ADR-013, P13 |
| FR-045-055 | La resolución es transaccional: cuórum, avance de nivel, cierre de solicitud y evento en la misma transacción | P0 | P13 |

### Consulta, permisos y auditoría

| ID | Requisito | Prioridad | Fuente |
|---|---|---|---|
| FR-045-060 | Bandeja «Mis aprobaciones» con filtros por proceso, estado, antigüedad y vencimiento | P0 | HU-045-03 |
| FR-045-061 | Historial completo de aprobaciones por documento, consultable desde la entidad | P0 | HU-045-08 |
| FR-045-062 | `allowed_actions` por solicitud y por paso, calculado en backend | P0 | Baseline §2 |
| FR-045-063 | Permisos `aprobaciones: view / create / edit / approve / delegate / configure` | P0 | P6 |
| FR-045-064 | Todo evento del motor registrado en `AuditEvent` con actor, antes/después, motivo y evidencia | P0 | ADR-012, P5 |
| FR-045-065 | El auditor consulta sin poder resolver | P0 | HU-045-08 |
| FR-045-066 | Emitir eventos de dominio para consumo futuro de la Spec 047 | P1 | Alcance §3 |
| FR-045-067 | Contrato de adjuntos de evidencia sobre `ApprovalRequest` conforme a `ADR-D0-008` | P1 | Spec 046 |

### Migración de las implementaciones existentes

| ID | Requisito | Prioridad | Fuente |
|---|---|---|---|
| FR-045-070 | Migrar la aprobación de requisiciones y órdenes de compra al motor | P0 | R-D0-02-10 |
| FR-045-071 | Migrar la aprobación de crédito de ventas al motor | P0 | R-D0-02-10 |
| FR-045-072 | Migrar la segregación de ajustes de inventario al motor | P0 | R-D0-02-10 |
| FR-045-073 | Migrar `regulatory.approval_requests` al motor | P0 | R-D0-02-10 |
| FR-045-074 | Las aprobaciones históricas se migran como cerradas con `policy_version = LEGACY_UNVERSIONED` y marca explícita; **no se inventa qué política se aplicó** | P0 | ADR-D0-002 §Migración |
| FR-045-075 | Tras la migración, ningún módulo conserva lógica propia de aprobación | P0 | P22 |

## 7. Requisitos no funcionales

| ID | Requisito |
|---|---|
| NFR-045-01 | Evaluación de política en ≤ 50 ms P95 sobre dataset representativo |
| NFR-045-02 | Bandeja con paginación desde 11 registros (Vol. 2 §2) |
| NFR-045-03 | WCAG 2.2 AA verificado con axe; navegable solo con teclado |
| NFR-045-04 | Responsive 320–1920 px sin scroll horizontal en tablas |
| NFR-045-05 | Pantallas completas con URL propia; modales solo para confirmación breve (ADR-015, P18) |
| NFR-045-06 | Toda la evidencia de pruebas sobre **PostgreSQL** (P21) |
| NFR-045-07 | Sin valores de negocio en código: montos, niveles, roles, monedas y procesos son datos (P8) |

## 8. Reglas no negociables

1. Los niveles, umbrales y resolutores **no se hardcodean**.
2. Toda política es **versionada**; la solicitud congela la versión aplicada.
3. Cambiar una política **no** altera solicitudes resueltas ni documentos históricos.
4. Toda decisión queda **auditada** con actor, momento, motivo y delegación de origen.
5. Con segregación activa, **el creador no resuelve**.
6. La delegación **no** elude la segregación.
7. Si el documento cambia, la solicitud queda **obsoleta**.
8. **Ningún módulo** implementa aprobación propia (P22).
9. El monto se evalúa en **moneda base** con la tasa del documento.
10. El backend es la autoridad: ocultar un botón no es un control (P6).
