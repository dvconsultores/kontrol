# MATRIZ DE GOBIERNO G0

Verificación de que no existe contradicción activa entre Constitución, ADR vigentes y decisiones D0.

| Tema | Constitución | ADR vigente | D0 | Estado | Puede iniciar Specs |
|---|---|---|---|---|---|
| Arquitectura general | P1, P3 | ADR-001 | — | Coherente | **Sí** |
| Instalación por cliente | P9, P15 | ADR-002 | D0-06 | Coherente | **Sí** |
| PostgreSQL como fuente de verdad | P13 | ADR-003 | D0-01 | Coherente · ADR-003 completado | **Sí** |
| Paridad de motor de pruebas | **P21 (nuevo)** | ADR-D0-001 | D0-01 | Coherente | **Sí** |
| Autenticación y sesión | P6 | ADR-004 | — | Coherente | **Sí** |
| Permisos y alcance | P6 | ADR-004, ADR-011 | D0-13 | Coherente | **Sí** |
| Multiempresa | P9, P11 | ADR-011 (actualizado) | D0-04, D0-13 | Coherente tras actualización | **Sí** |
| Sistema de diseño | P7, P17 | ADR-006 | — | Coherente | **Sí** |
| Política de modales | P18 | ADR-015 | — | Coherente | **Sí** |
| Documentos PDF | P10 | ADR-007 | — | Coherente | **Sí** |
| Archivos y adjuntos | P17, **P22** | ADR-008 (actualizado) | D0-08 | Coherente · modelo superseded | **Sí** |
| Auditoría | P5, **P22** | ADR-012 | — | Coherente · instrumentación incompleta = deuda | **Sí** |
| Idempotencia y concurrencia | P13 | ADR-013 | D0-03 | Coherente | **Sí** |
| Versionado de dependencias | P16 | ADR-014 | — | Coherente · `latest` en compose = deuda de código | **Sí** |
| Cola y workers | — | ADR-009 | — | Diferimiento vigente | **Sí** |
| Observabilidad | P10 | ADR-010 | — | Coherente | **Sí** |
| Licenciamiento y firma | P9, P15 | ADR-005 (actualizado) | D0-06 | Coherente · hospedaje pendiente | **Sí** |
| Aprobaciones | P5, **P22** | ADR-D0-002 | D0-02 | Coherente · umbrales pendientes | **Sí** |
| Reserva de inventario | P6, P13 | ADR-D0-003 | D0-03 | Coherente · disparador pendiente | **Sí** |
| Almacenes y ubicaciones | P8 | ADR-D0-004 | D0-04 | Coherente · mapa físico pendiente | **Sí** |
| Reglas comerciales | **P8** | ADR-D0-005 | D0-05 | Coherente · límites pendientes | **Sí** |
| UOM, presentación y conversión | P5, **P23** | ADR-D0-009 | D0-09 | Coherente | **Sí** |
| Snapshots comercial y fiscal | P4, P5, **P23** | ADR-D0-005, ADR-D0-007 | D0-05, D0-07 | Coherente | **Sí** |
| Estados de mercancía | P5 | ADR-D0-010 | D0-10 | Coherente | **Sí** |
| Vínculo pedido → factura | P3, P5 | ADR-D0-011 | D0-11 | Coherente | **Sí** |
| Confirmación independiente | P5 | ADR-D0-012 | D0-12 | Coherente · segregación configurable | **Sí** |
| Dimensiones organizacionales | P11 | ADR-D0-013 | D0-13 | Coherente | **Sí** |
| Precisión numérica | P8 | ADR-016 | — | Coherente | **Sí** |
| Gobierno fiscal | P4, P8, P19, P20 | ADR-D0-007 | D0-07 | Coherente · **valores sin validar** | **Sí** (cierre bloqueado) |

## Contradicciones detectadas y resueltas en G0

| # | Contradicción | Resolución | Autoridad aplicada |
|---|---|---|---|
| C-G0-01 | `ADR-003` fijaba PG como fuente de verdad pero no el motor de pruebas, permitiendo evidencia sobre SQLite | `ADR-D0-001` extiende, no reemplaza. ADR-003 actualizado: versión fijada en 18.x, validación CL-11 cerrada | ADR-D0-001 es posterior y más específico; ambos compatibles |
| C-G0-02 | `ADR-005` difería el portal central «a la Spec 010», que se implementó solo como cliente | `ADR-D0-006` cierra el diferimiento definiendo la autoridad. ADR-005 actualizado | El diferimiento cumplió su plazo; D0 lo resuelve |
| C-G0-03 | `ADR-008` definía `FileMetadata` como entidad única; `ADR-D0-008` requiere cuatro entidades | Supersesión **parcial y explícita** de §Consecuencias. La decisión de almacenamiento se ratifica | Nivel 5: el ADR posterior sustituye la sección concreta, no el ADR entero |
| C-G0-04 | `ADR-011` definía la cadena organizacional sin `Zone`, `CostCenter` ni `BusinessUnit` | ADR-011 actualizado para incorporarlos | Evita que dos ADR aprobados describan cadenas distintas |
| C-G0-05 | **Dos ADR numerados 012** (Auditoría y Precisión numérica) | El de precisión numérica pasa a **ADR-016** en el registro maestro; archivo conservado con nota | Regla nueva: numeración global única, nunca derivada de la Spec |
| C-G0-06 | `ADR-014` prohíbe `latest`; `compose.yaml` lo usa como valor por defecto | **El ADR prevalece.** El código es Nivel 7 y no justifica contradicción. Registrado como deuda DT-10 | Jerarquía de autoridad de la Constitución |
| C-G0-07 | `ADR-009` conserva `OutboxEvent` «para integraciones futuras»; la tabla no tiene consumidor | No es contradicción del ADR sino deuda de implementación. Diferimiento confirmado | El ADR describe intención de diseño, no estado de código |

**Contradicciones BLOCKER activas: 0.**

## Contradicciones no resueltas

Ninguna. Las siete detectadas quedaron resueltas con autoridad explícita.

## Pendientes que NO impiden crear Specs

| Pendiente | Tipo | Por qué no bloquea |
|---|---|---|
| Umbrales de aprobación (OQ-02) | Empresarial | El motor es parametrizable; los umbrales son datos de implantación |
| Disparador y vigencia de reserva (OQ-03) | Empresarial | La arquitectura es configurable con defecto decidido |
| Precedencia, descuentos y comisiones (OQ-06) | Empresarial | La precedencia es dato versionado, no código |
| Mapa físico del almacén (OQ-05) | Configuración | El modelo es genérico; el mapa es carga de datos |
| Segregación por proceso (OQ-12) | Configuración | Política por empresa con defecto restrictivo |
| Dimensiones activas (OQ-13) | Configuración | Matriz decidida; la activación es por empresa |
| Ratificación de Producto y Legal de la Constitución v1.1 | Gobierno | Las tres enmiendas refuerzan principios existentes; ninguna altera alcance funcional |

## Pendientes que SÍ bloquean el **cierre** de Specs

| Pendiente | Tipo | Specs cuyo cierre bloquea |
|---|---|---|
| Instancia PostgreSQL (BLK-D0-01) | Técnico | **Las 56** (`COMPLETE_100`) |
| Validación tributaria de 24 reglas (BLK-D0-02) | **Legal** | 014, 039, 040, 041, 042, 043, 056 |
| Hospedaje de la autoridad de licencias (OQ-07) | Empresarial | 004 |

Ninguno impide **iniciar** una Spec.
