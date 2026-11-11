# Spec CTL-03 · Administrador técnico sin autoridad funcional (GOV-CTL-004, P0)

Fuentes: `FUENTES.md` (N20, N23). Superficies: `AUTHORITY_FABRICATION_SURFACE_MATRIX.md`. Decisiones y gate:
`DECISIONES.md` (`CONSTITUTION_GATE = PASS`, `MATERIAL_DECISION_REQUIRED = 0`). Pantalla: `SCREEN_CONTRACT.md`.

## Historias
- US1 (Control Interno): ver quiénes administran la plataforma en el ente, qué roles técnicos y funcionales tienen y de dónde
  vienen, si ejercen un cargo y qué autoridad institucional derivan.
- US2 (Control Interno): ver los intentos de escalada y de ejercer autoridad sin cargo que el sistema denegó.
- US3 (seguridad): un administrador técnico puro conserva sus tareas técnicas y no puede fabricar autoridad funcional.

## Requisitos
- FR-001 ADMIN puro no puede asignarse ni asignar a otro un rol con capacidades que no tiene (incluido FUNCIONAL_COMPLETO):
  403, sin asignación, con evento de denegación.
- FR-002 ADMIN puro no puede crear un rol con capacidades funcionales: 403, sin rol.
- FR-003 ADMIN puro conserva sus tareas técnicas (crear cuenta, crear un rol técnico).
- FR-004 Toda superficie de autoridad de Gobierno y de aprobaciones exige una capacidad funcional (invariante sobre las rutas).
- FR-005 En la cabeza de la base, ADMIN tiene solo capacidades técnicas y FUNCIONAL_COMPLETO ninguna técnica.
- FR-006 Un permiso funcional no basta para un acto que exige cargo cuando la exigencia de identidad está activa: cuenta ADMIN +
  FUNCIONAL_COMPLETO sin vínculo → GOV_IDENTITY_LINK_REQUIRED; un actor con vínculo, ocupación y competencia emite el acto.
- FR-007 Proyección de solo lectura `GET /gobierno/control/separacion` con integridad, administradores técnicos (roles, origen,
  identidad, autoridad, estado de separación) e intentos denegados del ente (PDD-CTL03-02..10).
- FR-008 Pantalla «Separación técnica y funcional» según `SCREEN_CONTRACT.md`.
- FR-009 Aislamiento: el Control Interno de un ente no ve cuentas ni denegaciones de otro ente.

## Criterios de éxito
- SC-001 E2E en Chromium: ADMIN puro trabaja en lo técnico y es rechazado al escalar, al conceder y al crear un rol sombra;
  actor dual sin cargo rechazado al emitir un acto; actor legítimo lo emite; Control Interno ve todo en la pantalla.
- SC-002 Axe sin violaciones; 1280, 390 y 320 sin desborde.

## Fuera de alcance
Compromiso y pago (no existen: `COMMIT_PROCESS_NOT_IMPLEMENTED`, `PAY_PROCESS_NOT_IMPLEMENTED`); PROC-11; cambiar
OD-ORG06-09; nuevas capacidades o migraciones.
