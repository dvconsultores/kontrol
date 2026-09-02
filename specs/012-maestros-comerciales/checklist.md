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

---

# CHECKLIST — ACTUALIZACIÓN DOCUMENTAL POSTERIOR A ARCH-MC-001

- [x] Alcance actual de Tercero medido — **COMPANY**, obligatoria
- [x] Alcance actual de Producto medido — **COMPANY**, obligatoria
- [x] Alcance de Moneda medido — **COMPANY**, obligatoria
- [x] Alcance de Tasa de cambio medido — **COMPANY**, obligatoria
- [x] Todas las entidades de 012 clasificadas — 11
- [x] Alcance indeterminado = **0**
- [x] `__scope__` documentado en las once
- [x] `__scope_authority__` documentado en las tres derivadas
- [x] `CompanyContext` documentado como autoridad de petición
- [x] Entidades directas de empresa definidas — 8
- [x] Entidades derivadas definidas — 3
- [x] Rutas de derivación definidas y no anulables
- [x] Contrato de escritura hija definido
- [x] Contrato de lectura hija definido
- [x] Ataque por identificador de padre definido — N-01 a N-09
- [x] Caso del usuario con acceso a A+B definido — N-05, N-06
- [x] Caso entre tenants definido — N-03
- [x] Unicidad por empresa definida en las once
- [x] Versionado de listas de precios definido
- [x] Alcance de `PriceListItem` definido — derivado, sin `company_id`
- [x] Reglas de descuento definidas
- [x] Condiciones comerciales definidas
- [x] Propietario de `PaymentTerm` confirmado — la 012
- [x] Propietario de comisiones confirmado — la 012, reservado
- [x] Dependencia de unidades reconciliada, con la unidad de plataforma
- [x] Dependencia de presentación reconciliada
- [x] Dependencia de moneda reconciliada
- [x] Dependencia de aprobación reconciliada — Spec 045
- [x] Permisos definidos — seis
- [x] Auditoría definida — actor, tenant, empresa
- [x] Contrato OpenAPI definido — `X-Kontrol-Company` en el 100%
- [x] Contexto de empresa en el frontend definido
- [x] Aislamiento de caché definido
- [x] Seguridad del formulario sucio definida
- [x] Pruebas futuras definidas — A, B, C, D, E, F, G, H, I, J
- [x] Migraciones futuras planificadas — a partir de `0039`
- [x] **Ninguna implementación productiva incluida**

---

# CHECKLIST — IMPLEMENTACIÓN

- [x] 11 entidades reconciliadas — documental = modelo = catálogo
- [x] 8 directas de empresa confirmadas
- [x] 3 derivadas confirmadas, sin `company_id` redundante
- [x] Alcance de Tercero confirmado — COMPANY
- [x] Alcance de Producto confirmado — COMPANY
- [x] Alcance de Moneda confirmado — COMPANY
- [x] Alcance de Tasa de cambio confirmado — COMPANY
- [x] `taxonomy_nodes` confirmado como la categoría
- [x] Semántica de la unidad de plataforma confirmada — empresa nula
- [x] Semántica de presentación confirmada — Spec 011
- [x] Matriz de unicidad confirmada, y probada en los dos sentidos
- [x] Versionado implementado — publicar es irreversible
- [x] Reglas configurables en tiempo de ejecución — `price_precedence`
- [x] Matriz de rutas hijas completa — 5 rutas
- [x] Validación del padre en cada ruta hija
- [x] Ataque por identificador de padre definido y ejecutado — N-01..N-08
- [x] Pruebas entre tenants ejecutadas
- [x] Prueba de la empresa en el cuerpo ejecutada — `422`
- [x] Pruebas de SQL directo ejecutadas — por SQLSTATE
- [x] Permisos definidos — seis, y registrados en el arranque
- [x] Auditoría — actor y empresa resueltos por contexto
- [x] Aprobaciones reconciliadas — Spec 045, sin motor nuevo
- [x] Contratos de API implementados — 22 operaciones, 22 con cabecera
- [x] Aislamiento de estado en el frontend — clave de consulta y empresa fijada
- [x] Migraciones ordenadas — `0040`, `0041`
- [x] Instalación limpia verificada
- [x] Regresión completa ejecutada
