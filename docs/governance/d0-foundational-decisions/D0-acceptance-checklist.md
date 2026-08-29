# CHECKLIST DE ACEPTACIÓN D0

## Criterios de cierre (§30 del encargo)

- [x] **D0-01** tiene decisión — `ADR-D0-001`, APPROVED
- [x] **D0-02** tiene arquitectura — `ADR-D0-002` + `POL-D0-001`, modelo de 7 entidades
- [x] **D0-03** tiene política — `ADR-D0-003` + `POL-D0-002`, disparador configurable con defecto
- [x] **D0-04** tiene modelo — `ADR-D0-004` + `POL-D0-003`, jerarquía genérica sin zonas fijas
- [x] **D0-05** tiene arquitectura comercial — `ADR-D0-005` + `POL-D0-004`, 9 maestros y precedencia
- [x] **D0-06** tiene arquitectura de licenciamiento — `ADR-D0-006` + `POL-D0-005`
- [x] **D0-07** tiene matriz fiscal — `ADR-D0-007` + `POL-D0-006` + 24 reglas
- [x] **D0-08** tiene modelo documental — `ADR-D0-008`, 4 entidades con vinculación polimórfica
- [x] **D0-09** tiene regla de UOM y presentación — `ADR-D0-009`, snapshot obligatorio
- [x] **D0-10** tiene modelo de estados — `ADR-D0-010`, 15 estados y separación documento/mercancía
- [x] **D0-11** tiene trazabilidad pedido → factura — `ADR-D0-011`
- [x] **D0-12** tiene definición de confirmación independiente — `ADR-D0-012`
- [x] **D0-13** tiene matriz organizacional — `ADR-D0-013`, 19 tipos de documento

## Condiciones adicionales

- [x] 13 ADR creados, todos con estado explícito
- [x] 6 políticas funcionales creadas
- [x] Decisiones aprobadas documentadas con alternativas y descartes razonados
- [x] Decisiones empresariales abiertas identificadas y clasificadas (6)
- [x] Decisiones legales abiertas identificadas y clasificadas (2)
- [x] Dependencias actualizadas — `D0-spec-dependencies.md`
- [x] Roadmap actualizado — `D0-roadmap-adjustment.md`
- [x] Migraciones futuras identificadas y clasificadas
- [x] Riesgo sobre datos históricos documentado — `D0-historical-data-risk.md`
- [x] Enmiendas constitucionales propuestas sin aplicar — `D0-constitution-diff.md`
- [x] **Ninguna decisión crítica queda implícita**

## Prohibiciones respetadas (§35)

- [x] No se implementó código productivo — `git status resources/` = 0 cambios
- [x] No se creó ninguna Spec funcional
- [x] No se ejecutó `/speckit.implement`
- [x] No se modificaron migraciones
- [x] No se alteraron datos
- [x] No se introdujeron tablas, endpoints ni páginas
- [x] No se ocultó ningún problema existente
- [x] No se hardcodearon reglas empresariales
- [x] No se hardcodearon reglas fiscales
- [x] **No se codificaron zonas A-E** — prohibición explícita en `ADR-D0-004` R-D0-04-1
- [x] No se inventaron montos, niveles ni políticas de comisión
- [x] No se inventaron alícuotas ni conceptos fiscales
- [x] No se inventó proveedor de hospedaje
- [x] No se alteró código para hacerlo coincidir con las decisiones

## Verificación de formato (§5)

Cada ADR contiene: identificación · problema · por qué ahora · evidencia · alternativas ·
recomendada con fundamento · descartadas con motivo · regla definitiva · modelo conceptual cuando
aplica · estados cuando aplican · reglas de negocio · impacto en 7 dimensiones · migración ·
Specs bloqueadas · criterios de aceptación · preguntas pendientes · estado final.

Ningún estado ambiguo tipo «más adelante».
