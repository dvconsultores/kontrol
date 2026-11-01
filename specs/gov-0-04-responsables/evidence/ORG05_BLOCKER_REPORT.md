# ORG05_BLOCKER_REPORT · GOV-0-FUNCTIONAL-04 (2026-11-01)

VERDICT = **BLOCKED_BY_DOMAIN_DEPENDENCIES** · ORG05_FULL_PROCESS_IMPLEMENTABLE = 0 · implementación de producto: ninguna.

## 1. Prueba de descomposición (§12 del encargo)

| Fuente | Qué dice | Descompone ORG-05 |
|---|---|---|
| IR v1.0 §7.1 GOV-ORG-006 | Un requisito: responsables por nueve clases de objeto, con historia | NO |
| Inventario canónico de procesos (`GOVERNMENT_PRODUCT_COMPLETENESS_MATRIX.csv`) | ORG-05 es un proceso, 11 compuertas, requisito único GOV-ORG-006 | NO |
| Línea base de arquitectura (`docs/roadmap/government-architecture-baseline.md`) | «RESPONSABILIDAD ADMINISTRATIVA: responsabilidad registrada con historia sobre cada objeto custodiado» | NO |
| Decisiones de la dueña | Ninguna sobre ORG-05 | NO |

Conclusión: ORG-05 es **un proceso indivisible**. Un «responsable de unidad» solo no puede declararse OWNER_UAT_READY (§11).

## 2. Bloqueos materiales

| Id | Clase | Bloqueo | Evidencia | Se levanta con |
|---|---|---|---|---|
| B-ORG05-01 | DOMAIN_DEPENDENCY + DATA_INTEGRITY | 8 de 9 clases de objeto no existen en Gobierno (programa, proyecto, cuenta, almacén, caja, banco, contrato, bien) | `ORG05_TARGET_RESOURCE_MATRIX.md` | Los procesos dueños: BUD-03, ACC-01 (u otro según OQ-ORG05-02), WH-02, TRE-08, TRE-01, CNT-01, AST-01 |
| B-ORG05-02 | LEGAL (heredado) | Tres de esos procesos dueños están BLOCKED por validación legal: BUD-03 (N07, N08), ACC-01 (N36), AST-01 (N15, N17) | matriz canónica, columna BLOCKERS | Validación legal de esas normas clase C |
| B-ORG05-03 | DOMAIN_DEPENDENCY (identidad) | Si el responsable es una **persona** (funcionario, custodio, cuentadante), la vinculación persona → cargo → ente es ORG-06, BLOCKED por N40 | línea base de arquitectura §identidad («Gobierno añade la vinculación persona → cargo → ente»); matriz: ORG-06 | Levantar ORG-06, o decisión OQ-ORG05-01 |

Referenciar los objetos que faltan con texto libre, UUID sin validar, JSON genérico, referencias polimórficas débiles u objetos de
Empresarial está prohibido por el encargo (§8, §28) y no se hizo.

## 3. Preguntas materiales para la dueña (se resuelven antes de especificar ORG-05)

| Id | Pregunta | Por qué es material |
|---|---|---|
| OQ-ORG05-01 | ¿El responsable es el **cargo** (ORG-03), la **persona** que lo ocupa (ORG-06) o ambos según el tipo (p. ej. custodio de bien = persona; responsable de unidad = cargo)? | Cambia el modelo de datos y la dependencia de ORG-06 / N40; el control fiscal (N18, N21) y las actas de entrega (N34) apuntan a personas |
| OQ-ORG05-02 | ¿Qué es «cuenta» en GOV-ORG-006: cuenta contable (plan de cuentas), partida presupuestaria o cuenta de rendición (N21)? | Cambia el dominio dueño y su estado (ACC-01 BLOCKED, BUD-* o CTL-06) |
| OQ-ORG05-03 | ¿ORG-05 es un **registro transversal** de responsables que consumen los demás procesos, o cada dominio guarda los suyos (supervisor del contrato en CNT-04, custodia en AST-03, autorizados en TRE-01, responsables de caja en TRE-08 y de almacén en WH-02) y ORG-05 los **consolida** con historia? | La IR asigna también responsables dentro de esos requisitos: sin decidirlo, ORG-05 duplicaría o contradiría esos procesos (CONTRADICTION potencial, no resuelta en silencio) |

## 4. Lo que sí está disponible

UNIT (ORG-02, `gov_units`) y CARGO (ORG-03, `gov_positions`) existen con integridad y alcance de empresa. Bastarían para la fila UNIT
solo si OQ-ORG05-01 decide «cargo» para ese tipo; aun así ORG-05 seguiría sin poder cerrarse (§1).

## 5. Qué no se hizo (y por qué)

Sin plan, tareas, código, migración, pruebas ni llamadas a DeepSeek: la compuerta de la Constitución exige
ORG05_FULL_PROCESS_IMPLEMENTABLE = 1 (§37). No se sustituyó ORG-05 por otro proceso ni por trabajo técnico (§14): el siguiente
paso lo deciden la dueña y su equipo.
