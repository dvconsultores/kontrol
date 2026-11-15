# Trazabilidad · CNT-04

| Contrato | Requisito | Código | Prueba |
|---|---|---|---|
| C04-01 contrato formalizado | FR-01 | `designar` paso 1 (FOR UPDATE, 409 NOT_FORMALIZED, 404) | PG vector b; E2E (contrato formalizado) |
| C04-02 funcionario institucional | FR-02 | `GovernmentOfficial` ACTIVO del ente (422 OFFICIAL_INVALID) | PG vector e |
| C04-03 ocupación vigente | FR-02 | `ocupaciones_de_funcionario` en la fecha efectiva y hoy, sin DELEGACION (422 OCCUPATION_INVALID + BLOCKED) | PG vectores c y opciones |
| C04-04 instantánea de cargo y unidad | FR-03 | columnas `cargo_*`, `unidad_nombre`, `figura` y `funcionario_*` (documento enmascarado) | PG vector a; Vitest b; E2E «Cargo: …» |
| C04-05 acto de designación | FR-04 | acto EFICAZ con eficacia ≤ desde (422 ACT_INVALID), no reutilizado (ACT_REUSED) | PG vectores d y f |
| C04-06 autoridad que designa | FR-05 | `_autoridad_valida(APROBAR, CONTRATACIONES)` a la fecha del acto y `exigir_autoridad_funcional` | PG vector d (cargo con FIRMAR → 422 ACT_AUTHORITY_INVALID); opciones |
| C04-07 permiso técnico | FR-06 | `gobierno_contratos:assign_supervisor` SENSITIVE | PG permisos (403 para quien solo consulta); test_mfa_policy; test_delegation_ceiling |
| C04-08 un supervisor vigente | FR-07 | índice único parcial `uq_gov_contract_supervisors_vigente` | PG concurrencia |
| C04-09 fecha efectiva | FR-08 | rango [min(inicio, formalización) ó desde+1, fin del contrato]; designación programada | PG vectores f y programada (fuera de rango) |
| C04-10 historia de sustituciones | FR-09 | SUSTITUIDA con hasta = D-1; `sustituye`; `programada` / `ultima_id` | PG f, h y programada; Vitest b, d y g; E2E |
| C04-11 sin retroactividad silenciosa | FR-09 | `supervisor_en` por intervalo | PG h (antes de D → A; desde D → B); E2E `/en` |
| C04-12 inmutabilidad | FR-10 | trigger `kontrol_gov_contract_supervisor_guard` | PG inmutable (UPDATE, DELETE, TRUNCATE) |
| C04-13 concurrencia | FR-11 | FOR UPDATE + `sustituye_id` (409 STALE) + índice único (409 CONFLICT) | PG carrera real; E2E doble POST 201/409 |
| C04-14 SoD reutilizada | FR-12 | `PROC03_SUPERVISOR_DESIGNAR/SUSTITUIR` en CTL-01 | PG regla vigente → 409 GOV_SOD_CONFLICT |
| C04-15 aislamiento | FR-13 | `company_id` en todas las consultas; 404 ajeno | PG vector e |
| C04-16 auditoría | FR-14 | ASSIGNED, REPLACED, BLOCKED + cronología del expediente | PG a, c y f; E2E bitácora |
| C04-17 consumidor CNT-03 | FR-15 | `supervisor_en`, `supervisor_vigente`, GET `/supervision/en` | PG h; E2E |
| C04-18 E2E / UAT | FR-16 | sección en la ficha del contrato | E2E gobierno-contratos (tramo CNT-04), 1280/390/320 + Axe; humo UAT |
