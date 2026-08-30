# CHECKLIST — SPEC 012

## Antes de implementar

- [ ] `ADR-D0-005` leído completo; ninguna de sus decisiones se re-decide.
- [ ] `OQ-06` sigue abierta y se entiende **por qué no bloquea**.
- [ ] Verificado que hoy no existe ninguna tabla comercial.
- [ ] Verificado que **no** hay `price_1..price_5` y que no aparecerán.
- [ ] Motor de conversión de la Spec 011 entendido: 012 lo usa, no lo replica.
- [ ] Motor de aprobaciones de la Spec 045 entendido: 012 lo consume, no lo replica.
- [ ] `WarehouseZone` revisada, para no confundirla con `CommercialZone`.

## Durante

- [ ] F3 (resolución) **antes** que F7 (API).
- [ ] F6 (snapshot) **antes** que F7 (API).
- [ ] Ningún importe en `float`.
- [ ] Ningún porcentaje, plazo, zona o canal en el código.
- [ ] La precedencia se lee de tabla en cada resolución.
- [ ] Ninguna migración crea un maestro por su cuenta.
- [ ] Ninguna columna heredada se modifica ni se borra.

## Antes de declarar COMPLETE_100

- [ ] Los 45 criterios de aceptación, con prueba que los ejecuta.
- [ ] Suite completa sobre **PostgreSQL 18.x**.
- [ ] `masters_created = 0`, `columns_modified = 0`, `documents_repriced = 0`.
- [ ] Reordenar la precedencia **cambia** el precio resuelto (prueba viva de `P8`).
- [ ] Editar una lista **no** cambia un documento aprobado.
- [ ] Un empate irresoluble devuelve 422, no un precio.
- [ ] Sin lista aplicable devuelve ausencia, no cero.
- [ ] 0 cálculos de precio fuera de `pricing.py`.
- [ ] 0 aprobaciones, permisos o auditoría propios.
- [ ] axe sin violaciones serias; 6 viewports sin desbordamiento.
- [ ] Cross-browser en los tres navegadores.
- [ ] `/speckit.converge 012` PASS.
- [ ] Matriz de impacto verificada contra código, no contra nombres.
