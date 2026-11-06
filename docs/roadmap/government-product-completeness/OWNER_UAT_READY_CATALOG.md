# OWNER_UAT_READY_CATALOG — KONTROL Gobierno

> Retrospectiva GOV-PRODUCT-COMPLETENESS-RETRO-01 · `develop` `0dbe632` · 2026-10-29. Actualizado por GOV-0-01 (2026-10-30), GOV-0-02 (2026-10-31), GOV-0-03 y GOV-DOC-02 (2026-11-01) GOV-DOC-04 y GOV-ORG-07 (2026-11-02) GOV-CTL-04 (2026-11-03), GOV-CTL-06, GOV-DOC-08 y GOV-CTL-01 (2026-11-04) GOV-TRE-01 (2026-11-05) y la corrección de T038 (2026-11-06).

## Estado: 11 procesos listos para probar (2026-11-06)

- `OWNER_UAT_READY` = 11 de 122 procesos (9,02 %);
- `OWNER_ACCEPTED` = 0 de 122 (solo la dueña lo concede, tras probarlo).

| Proceso | Dónde entrar | Tarjeta | Ciclo |
|---|---|---|---|
| **ORG-01 Configurar el ente** (GOV-ORG-001) | Menú › Gobierno › Configuración del ente | [`specs/gov-0-01-configurar-ente/evidence/OWNER_UAT_CARD.md`](../../../specs/gov-0-01-configurar-ente/evidence/OWNER_UAT_CARD.md) | GOV-0-01 |
| **ORG-02 Estructura organizativa por ejercicio** (GOV-ORG-002, GOV-ORG-008) | Menú › Gobierno › Estructura organizativa | [`specs/gov-0-02-estructura-organizativa/evidence/OWNER_UAT_CARD.md`](../../../specs/gov-0-02-estructura-organizativa/evidence/OWNER_UAT_CARD.md) | GOV-0-02 |
| **ORG-03 Cargos con competencias y límites de firma/aprobación** (GOV-ORG-003) | Menú › Gobierno › Cargos y competencias | [`specs/gov-0-03-cargos-competencias/evidence/OWNER_UAT_CARD.md`](../../../specs/gov-0-03-cargos-competencias/evidence/OWNER_UAT_CARD.md) | GOV-0-03 |
| **ORG-07 Matriz auditable de autoridad: quién puede qué** (GOV-ORG-010) | Menú › Gobierno › Matriz de autoridad | [`specs/gov-org-07-matriz-autoridad/evidence/OWNER_UAT_CARD.md`](../../../specs/gov-org-07-matriz-autoridad/evidence/OWNER_UAT_CARD.md) | GOV-ORG-07 |
| **DOC-02 Actos administrativos con autoridad, competencia, motivación, eficacia y notificación** (GOV-DOC-003) | Menú › Gobierno › Actos administrativos | [`specs/gov-doc-02-actos-administrativos/evidence/OWNER_UAT_CARD.md`](../../../specs/gov-doc-02-actos-administrativos/evidence/OWNER_UAT_CARD.md) | GOV-DOC-02 |
| **DOC-04 Notificaciones administrativas con constancia de recepción por canal autorizado** (GOV-DOC-005) | Menú › Gobierno › Notificaciones administrativas (y la sección «Notificaciones» del acto particular) | [`specs/gov-doc-04-notificaciones/evidence/OWNER_UAT_CARD.md`](../../../specs/gov-doc-04-notificaciones/evidence/OWNER_UAT_CARD.md) | GOV-DOC-04 |
| **CTL-04 Consulta y muestreo read-only del auditor interno/externo** (GOV-CTL-005) | Menú › Gobierno › Auditoría institucional | [`specs/gov-ctl-04-auditoria/evidence/OWNER_UAT_CARD.md`](../../../specs/gov-ctl-04-auditoria/evidence/OWNER_UAT_CARD.md) | GOV-CTL-04 |
| **CTL-06 Hallazgos, recomendaciones y planes de acción correctiva** (GOV-CTL-008) | Menú › Gobierno › Hallazgos y acciones correctivas (y «Registrar hallazgo» en la muestra de CTL-04) | [`specs/gov-ctl-06-hallazgos/evidence/OWNER_UAT_CARD.md`](../../../specs/gov-ctl-06-hallazgos/evidence/OWNER_UAT_CARD.md) | GOV-CTL-06 |
| **DOC-08 Paquete de auditoría exportable con índice, huellas y referencias cruzadas** (GOV-DOC-010) | Menú › Gobierno › Paquetes de auditoría (y «Generar paquete de auditoría» en la muestra de CTL-04) | [`specs/gov-doc-08-paquete-auditoria/evidence/OWNER_UAT_CARD.md`](../../../specs/gov-doc-08-paquete-auditoria/evidence/OWNER_UAT_CARD.md) | GOV-DOC-08 |
| **CTL-01 Matriz de segregación de funciones con detección previa** (GOV-CTL-001) | Menú › Gobierno › Segregación de funciones (y la alerta de bloqueo en las fichas de acto y de hallazgo) | [`specs/gov-ctl-01-sod/evidence/OWNER_UAT_CARD.md`](../../../specs/gov-ctl-01-sod/evidence/OWNER_UAT_CARD.md) | GOV-CTL-01 |
| **TRE-01 Cuentas bancarias públicas** (GOV-TRE-001) | Menú › Gobierno · Tesorería › Cuentas bancarias y Bancos | [`specs/gov-tre-01-cuentas-bancarias/evidence/OWNER_UAT_CARD.md`](../../../specs/gov-tre-01-cuentas-bancarias/evidence/OWNER_UAT_CARD.md) |

Los otros 111 procesos siguen fuera del catálogo; ninguno se subió parcial (política §7). La retrospectiva del 2026-10-29 lo dejaba VACÍO y señalaba ORG-01 como primer candidato natural (IR §14).

## Fundamentos técnicos

Los fundamentos técnicos (MFA, aislamiento, copia y restauración…) **no** entran en este catálogo. No son procesos de Gobierno que la dueña pruebe como usuaria de negocio: ver la política, §5. Las pantallas de núcleo que ya existen, como `/seguridad/mfa`, son de la línea Empresarial.
