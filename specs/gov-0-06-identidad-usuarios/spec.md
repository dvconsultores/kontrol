# ORG-06 · Identidad institucional, usuario, cargo, unidad, alcance y separación de roles

## 1. Lo que podrá hacer el usuario

Desde **Gobierno › Identidad institucional** el responsable podrá vincular una cuenta con un funcionario, activar el vínculo con otra persona, cerrarlo o revocarlo y ver su historia. Para cualquier fecha verá qué cuenta correspondía a qué funcionario, qué cargo ejercía, en qué unidad y ente, con qué roles, qué autoridad derivaba y qué prohibía la segregación de funciones, y por qué.

Control Interno clasificará los roles existentes en categorías de separación, definirá incompatibilidades en la Segregación de funciones ya existente y activará la exigencia de identidad.

## 2. Fuentes

GOV-ORG-007 (P0; N20, N27, N40) y GOV-ORG-005 (P0; N18, N20, N23). N40_BLOCKS_ORG06 = 0, sin regla nueva. Reutiliza ORG-03, ORG-04, ORG-07 y CTL-01. Contratos en `evidence/USER_OFFICIAL_CARDINALITY_CONTRACT.md` y `evidence/ORG06_FIELD_CONTRACT.md`.

## 3. Decisiones de diseño

Son de Claude, por seguridad, arquitectura y requisitos. Ninguna requiere a la dueña.

| Id | Decisión |
|---|---|
| OD-ORG06-01 | Cardinalidad 1:1 vigente por ente, con historia. Dos exclusiones PostgreSQL |
| OD-ORG06-02 | **Actor efectivo:** maker-checker y SoD comparan todas las cuentas que han representado al mismo funcionario |
| OD-ORG06-03 | El vínculo es configuración de seguridad: motivo obligatorio, referencia opcional, sin acto nuevo |
| OD-ORG06-04 | El alcance no se guarda: cuenta → vínculo vigente → funcionario → ocupación ORG-04 → cargo ORG-03 → unidad → ente |
| OD-ORG06-05 | Varias ocupaciones simultáneas se representan todas; la SoD decide incompatibilidades |
| OD-ORG06-06 | Categorías: metadato configurable sobre roles existentes, sin roles nuevos |
| OD-ORG06-07 | Sin segundo motor: las incompatibilidades son reglas CTL-01 del proceso ORG-06 cuyos dos extremos son categorías |
| OD-ORG06-08 | Roles a una fecha pasada: se reconstruyen de la auditoría ROLE_ASSIGNED y ROLE_REMOVED. El núcleo no cambia |
| OD-ORG06-09 | Exigencia por ente, inactiva por defecto y activada con MFA, para no bloquear al ente antes de vincular |
| OD-ORG06-10 | Operación protegida en este ciclo: emitir un acto, la única con cargo y competencia explícitos. La guarda es reutilizable por verticales futuros |
| OD-ORG06-11 | Una consulta histórica nunca concede: toda mutación usa la fecha de negocio del servidor |
| OD-ORG06-12 | Avocación: ORG-04 la registra por asunto; no termina la delegación, y se muestra junto a ella |
| OD-ORG06-13 | Quien registra no activa, y nadie registra ni activa el vínculo de su propia cuenta o funcionario |

## 4. Estados

`BORRADOR → ACTIVO → CERRADO | REVOCADO`; `BORRADOR → DESCARTADO`. Situación: BORRADOR, DESCARTADA, FUTURA, VIGENTE, VENCIDA, CERRADA, REVOCADA. La fecha final cuenta completa.

## 5. Autoridad derivada

Autoridad NINGUNA si no hay vínculo vigente, la cuenta no está ACTIVE, el funcionario no está ACTIVO o no hay ocupación vigente. Si no, las competencias de las ocupaciones que ejerce a la fecha. Motivos: SIN_VINCULO, CUENTA_INACTIVA, FUNCIONARIO_INACTIVO, SIN_OCUPACION.

## 6. Orden de seguridad

Autenticación → permiso técnico → empresa → vínculo vigente → funcionario → ocupación → cargo → autoridad → SoD → MFA → mutación → auditoría → respuesta.

## 7. Requisitos funcionales

- **FR-001** Registrar, editar y descartar borradores de vínculo con selectores, sin UUID.
- **FR-002** Activar con maker-checker por actor efectivo, sin autovínculo, con cuenta y funcionario activos, sin solape y sin conflicto SoD.
- **FR-003** Cerrar y revocar con fecha y motivo; la historia nunca se borra.
- **FR-004** Consultar por lista, filtros, detalle, historia y a fecha; exportar CSV auditado.
- **FR-005** Mostrar a una fecha cuenta, funcionario, ocupaciones, cargo, unidad, ente, roles, categorías, autoridad y conflictos, con el motivo si no hay autoridad.
- **FR-006** Cada usuario puede consultar su propio contexto; el cliente no aporta alcance.
- **FR-007** Clasificar roles en las cinco categorías, retirar la clasificación y conservar historia.
- **FR-008** Reglas CTL-01 entre categorías evaluadas al activar, al clasificar y en la operación protegida.
- **FR-009** Exigencia de identidad por ente con MFA; con ella activa, emitir un acto exige ejercer el cargo con esa competencia.
- **FR-010** Maker-checker de ORG-04 y SoD por actor efectivo.
- **FR-011** Toda mutación audita actor, actor institucional, antes y después.
- **FR-012** Otro ente responde 404; el ente nunca viene del cliente.
- **FR-013** La base impide solapes y edición de historia en PostgreSQL.

## 8. Fuera de alcance

Atenea, nómina, creación de usuarios o roles, ORG-05, CTL-08, DOC-03, TRE-08, cambios en autenticación y en el núcleo.

## 9. Criterios de éxito

- **SC-001** Desde el menú se responde qué cuenta era qué funcionario y con qué autoridad en cualquier fecha.
- **SC-002** Vincular no concede autoridad.
- **SC-003** Dos cuentas de una persona no evaden maker-checker ni SoD.
- **SC-004** 20 mutantes exigidos, 0 supervivientes de comportamiento.
