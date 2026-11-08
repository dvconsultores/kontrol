# PROC-02 · Comisión de contrataciones

## 1. Lo que podrá hacer el usuario

Desde **Gobierno · Contrataciones › Comisiones**, la unidad contratante registra una comisión permanente o temporal, su vigencia, el acto que la crea, sus miembros principales con sus suplentes por área y su secretario. Otra persona la activa. Se consulta quién la integraba en cualquier fecha, se sustituye un miembro sin perder la historia, y se registran y resuelven inhibiciones.

## 2. Fuentes

GOV-PROC-003 (P0; N11, N12, N23). Textos leídos el 2026-11-08 (copias locales fuera del repositorio; sha256 en `evidence/FUENTES.md`):

| Regla | Fuente |
|---|---|
| Una o varias comisiones, permanentes o temporales | LCP art. 14 |
| Número impar de principales con sus suplentes, designados por la máxima autoridad, a título personal | LCP art. 14 |
| Representadas las áreas jurídica, técnica y económico financiera | LCP art. 14 |
| Secretario con su suplente, con voz y sin voto | LCP art. 14 |
| Notificar la designación al SNC dentro de los 5 días siguientes | LCP art. 14 |
| Certificación de los miembros ante el SNC | LCP art. 14 |
| Publicación de la creación y conformación en Gaceta | RLCP art. 15 |
| Convocar al suplente en falta accidental o temporal; pedir sustituto en falta absoluta | LCP art. 15 |
| Causales de inhibición | RLCP art. 18 |
| Causas de falta absoluta | RLCP art. 20 |

El RLCP es de 2009 y la biblioteca del sponsor lo admite «solo en cuanto sea compatible con ley posterior». Se aplica con esa salvedad.

## 3. Decisiones de diseño

Son de Claude. Ninguna requiere a la dueña.

| Id | Decisión |
|---|---|
| OD-PROC02-01 | Miembro = funcionario de ORG-04. LCP dice «preferentemente» entre empleados o funcionarios: un externo se registra antes como funcionario |
| OD-PROC02-02 | Activar valida lo que dice la ley: impar, tres áreas, cada principal con suplente, secretario con suplente, acto eficaz publicado en gaceta. En borrador se permite cualquier composición |
| OD-PROC02-03 | Reglas con versión y fuente (Constitución P8): `LCP-2014+RLCP-2009`, guardada en la comisión al activarse |
| OD-PROC02-04 | Sin miembros editables tras activar: sustituir es terminar una fila y crear otra, con acto. La composición a una fecha se lee de las vigencias |
| OD-PROC02-05 | Inhibición: `asunto` en texto hasta que exista el procedimiento (PROC-03). Causal del art. 18 RLCP. Resuelve otra persona: quien declara no resuelve |
| OD-PROC02-06 | La notificación al SNC y la certificación se registran como dato; no hay integración (D-GOV-03). Se alerta si falta; los cinco días no se calculan porque la ley no dice si son hábiles y el calendario está pendiente (DOC-03) |
| OD-PROC02-07 | No se verifica que el emisor del acto sea la máxima autoridad: el sistema no identifica hoy ese cargo. Se muestra el emisor |
| OD-PROC02-08 | Capacidad `gobierno_comisiones`: view, manage, activate (MFA), close (MFA) |
| OD-PROC02-09 | Faltas temporales y convocatoria del suplente quedan para las sesiones de PROC-07: sin asuntos no hay qué convocar |

## 4. Estados

`evidence/COMMISSION_STATE_CONTRACT.md`.

## 5. Requisitos funcionales

- **FR-001** Registrar, editar y descartar el borrador: nombre, tipo, objeto, vigencia y acto, con selectores humanos.
- **FR-002** Añadir y retirar miembros en borrador: funcionario, función, área, condición, y el principal al que suple.
- **FR-003** Activar con otra persona, MFA y las validaciones de OD-PROC02-02, con mensajes que digan qué falta.
- **FR-004** Con la comisión vigente: terminar un miembro con causa, y designar otro con acto.
- **FR-005** Consultar la composición a una fecha, sin recalcular con la actual.
- **FR-006** Declarar y resolver inhibiciones.
- **FR-007** Cerrar con fecha y motivo. Registrar la notificación al SNC.
- **FR-008** Listar con búsqueda, filtros y paginación real; exportar CSV auditado.
- **FR-009** Toda mutación audita y aparece en la bitácora. Historia inmutable.
- **FR-010** Otro ente responde 404; el funcionario y el acto han de ser del ente.

## 6. Fuera de alcance

Procedimientos, ofertas y evaluación; quórum, agendas, actas y disentimiento (PROC-07); integración con el SNC; informe de gestión (RLCP art. 16.19).

## 7. Criterios de éxito

- **SC-001** Desde el menú se responde quién integraba una comisión en cualquier fecha.
- **SC-002** Una comisión que incumple el art. 14 LCP no llega a vigente, y el usuario sabe por qué.
