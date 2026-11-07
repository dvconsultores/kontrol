# Plan · ORG-04

## Datos (migración `0076_gov_org04_ocupacion`)

- `gov_officials`: `company_id`, `codigo`, `nombre`, `tipo_documento`, `numero_documento`, `estado`, `version`. Únicos: (company, codigo), (company, tipo, numero).
- `gov_official_history`: inmutable.
- `gov_assignments`: `company_id`, `codigo`, `official_id`, `position_id`, `figura`, `grupo`, `cargo_origen_id`, `act_id`, `desde`, `hasta`, `fin_efectivo`, `status`, `fundamento`, `rendicion`, `maxima_autoridad`, `autorizacion_concejo`, `declara_delegable`, `revocation_act_id`, `motivo_fin`, `activated_at/by`, `ended_at/by`, `version`.
- `gov_assignment_competencies`: acción, materia y copia del límite.
- `gov_assignment_history`: inmutable, con `antes` y `despues`.
- PostgreSQL: `EXCLUDE USING gist` por (position, grupo) para TITULARIDAD y TEMPORAL, y por (position, official) para DELEGACION, con `WHERE status = 'ACTIVO'`. Triggers: sin borrar; sin editar lo activado; historia inmutable.
- `gov_sod_rules.proceso`: añade ORG-04.

## Capacidades

`gobierno_ocupacion`: `view`, `manage` estándar; `activate`, `revoke` con MFA. Solo FUNCIONAL_COMPLETO.

## API `/gobierno/ocupacion`

`GET catalogo`, `GET opciones`, `GET|POST funcionarios`, `GET|PATCH funcionarios/{id}`, `GET|POST asignaciones`, `GET asignaciones.csv`, `GET|PATCH asignaciones/{id}`, `POST asignaciones/{id}/activar|descartar|revocar|finalizar|avocar`, `GET cargos`, `GET cargos/{id}`.

## Frontend

Módulo `gobierno/ocupacion/`: `OcupantesPage`, `CargoOcupacionPage`, `AsignacionesPage`, `NuevaAsignacionPage`, `AsignacionPage`, `FuncionariosPage`.

## Constitución

| Gate | Resultado |
|---|---|
| Rama única y origin | PASS |
| Delegación tras gate; Claude no escribe código | PASS |
| Sin núcleo compartido nuevo: solo añadidos de registro, como CTL-10 | PASS |
| Egress | PASS |
| Completitud de producto | Exigida |
