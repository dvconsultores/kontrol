# CHECKLIST — SPEC 045

## Conformidad constitucional

- [ ] **P2** — no se implementa sin autorización expresa que mencione `045`
- [ ] **P3** — cada requisito tiene tarea, código, prueba y evidencia
- [ ] **P5** — decisiones y delegaciones append-only; revocar no reescribe historia
- [ ] **P6** — elegibilidad, segregación y límites validados en backend; `allowed_actions` calculado en servidor
- [ ] **P7 / P17** — solo componentes del design system compartido
- [ ] **P8** — **ningún** umbral, nivel, rol, moneda o proceso en código
- [ ] **P10** — sin evidencia no hay función terminada
- [ ] **P11** — WCAG 2.2 AA y responsive sin scroll horizontal
- [ ] **P12** — decisiones nuevas, si surgen, con ADR
- [ ] **P13** — transaccionalidad, idempotencia y control de concurrencia probados
- [ ] **P18 / ADR-015** — pantallas completas; modales solo para confirmación breve
- [ ] **P21** — toda la evidencia sobre PostgreSQL
- [ ] **P22** — al cerrar, **ningún** módulo conserva lógica propia de aprobación
- [ ] **P23** — `policy_snapshot` y `fingerprint_fields` capturados desde la primera solicitud

## Conformidad con ADR

- [ ] `ADR-D0-002` — las 10 reglas R-D0-02-1..10 implementadas y probadas
- [ ] `ADR-011` / `ADR-D0-013` — `company_id` y alcance en todas las consultas
- [ ] `ADR-012` — auditoría por `record_audit`; **sin rastro paralelo**
- [ ] `ADR-013` — `Idempotency-Key`, ETag/versión y locks
- [ ] `ADR-D0-008` — contrato de adjuntos declarado sin acoplar a la Spec 046
- [ ] `ADR-016` — importes en `Numeric`

## Completitud funcional

- [ ] Política creable, versionable, activable y cerrable; nunca eliminable
- [ ] Dos políticas activas solapadas: rechazado por restricción
- [ ] Regla con predicados tipados; varias reglas expresan `OR`
- [ ] Niveles secuenciales con cuórum `ANY` / `ALL` / `N_OF_M`
- [ ] Monto evaluado en moneda base con tasa snapshot del documento
- [ ] Condición no evaluable → error explícito, nunca «no requiere» silencioso
- [ ] Solicitud con `policy_snapshot` y `fingerprint` congelados
- [ ] Actores elegibles congelados al abrir cada paso
- [ ] Aprobar, rechazar, devolver y cancelar, con motivo obligatorio en negativas
- [ ] Rechazo terminal para la solicitud
- [ ] Devolución conserva historial y encadena la nueva solicitud
- [ ] Obsolescencia automática al cambiar un campo de la huella
- [ ] Vencimiento marca y notifica; **no** resuelve
- [ ] Segregación impide al creador resolver
- [ ] Autoaprobación configurable e independiente
- [ ] Delegación acotada, revocable y auditada
- [ ] Delegación **no** elude segregación
- [ ] Bandeja «Mis aprobaciones» transversal a todos los dominios
- [ ] Historial consultable desde el documento

## Migración

- [ ] Política equivalente creada y verificada **antes** de cada corte
- [ ] Compras migrado sin cambio de comportamiento observable
- [ ] Ventas (crédito) migrado
- [ ] Inventario (ajustes y conteos) migrado
- [ ] Regulatorio migrado
- [ ] Histórico como `LEGACY_UNVERSIONED`, **sin inventar política**
- [ ] Ningún módulo conserva lógica propia (verificado por búsqueda)
- [ ] Migración de datos idempotente

## Pruebas

- [ ] Unidad: evaluador de condiciones, resolución de actores, huella, cuórum
- [ ] Integración: ciclo completo por API
- [ ] Contrato: OpenAPI ↔ frontend; puertas G1-G4
- [ ] **Concurrencia sobre PostgreSQL**: dos decisiones simultáneas → una 409
- [ ] Obsolescencia bajo concurrencia: cambio de documento durante la decisión
- [ ] Idempotencia: doble creación de solicitud no duplica
- [ ] Segregación: 403 con motivo explícito
- [ ] Delegación: hereda restricciones
- [ ] E2E: configurar → disparar → aprobar → documento avanza
- [ ] E2E: devolver → corregir → reenviar → aprobar
- [ ] axe WCAG 2.2 AA en las 3 pantallas
- [ ] Responsive 6 viewports sin scroll horizontal

## Puertas de completitud (evitar regresión)

- [ ] Cada ítem de menú nuevo tiene ruta y página (G1-G2)
- [ ] Cada llamada del frontend resuelve a endpoint existente (G3-G4)
- [ ] Ningún endpoint del motor queda sin consumidor ni sin clasificar

## Prohibiciones

- [ ] Sin montos, límites, niveles, usuarios, roles, monedas o procesos hardcodeados
- [ ] Sin políticas de clientes concretos en el código ni en seeds obligatorios
- [ ] Sin modales para configuración de políticas
- [ ] Sin lógica de notificación dentro del motor
- [ ] Sin almacenamiento de archivos dentro del motor
