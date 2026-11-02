# OWNER_UAT_READY_CATALOG — KONTROL Gobierno

> Retrospectiva GOV-PRODUCT-COMPLETENESS-RETRO-01 · `develop` `0dbe632` · 2026-10-29. Actualizado por GOV-0-01 (2026-10-30), GOV-0-02 (2026-10-31), GOV-0-03 y GOV-DOC-02 (2026-11-01) y GOV-DOC-04 (2026-11-02).

## Estado: 5 procesos listos para probar (2026-11-02)

- `OWNER_UAT_READY` = 5 de 122 procesos (4,10 %);
- `OWNER_ACCEPTED` = 0 de 122 (solo la dueña lo concede, tras probarlo).

| Proceso | Dónde entrar | Tarjeta | Ciclo |
|---|---|---|---|
| **ORG-01 Configurar el ente** (GOV-ORG-001) | Menú › Gobierno › Configuración del ente | [`specs/gov-0-01-configurar-ente/evidence/OWNER_UAT_CARD.md`](../../../specs/gov-0-01-configurar-ente/evidence/OWNER_UAT_CARD.md) | GOV-0-01 |
| **ORG-02 Estructura organizativa por ejercicio** (GOV-ORG-002, GOV-ORG-008) | Menú › Gobierno › Estructura organizativa | [`specs/gov-0-02-estructura-organizativa/evidence/OWNER_UAT_CARD.md`](../../../specs/gov-0-02-estructura-organizativa/evidence/OWNER_UAT_CARD.md) | GOV-0-02 |
| **ORG-03 Cargos con competencias y límites de firma/aprobación** (GOV-ORG-003) | Menú › Gobierno › Cargos y competencias | [`specs/gov-0-03-cargos-competencias/evidence/OWNER_UAT_CARD.md`](../../../specs/gov-0-03-cargos-competencias/evidence/OWNER_UAT_CARD.md) | GOV-0-03 |
| **DOC-02 Actos administrativos con autoridad, competencia, motivación, eficacia y notificación** (GOV-DOC-003) | Menú › Gobierno › Actos administrativos | [`specs/gov-doc-02-actos-administrativos/evidence/OWNER_UAT_CARD.md`](../../../specs/gov-doc-02-actos-administrativos/evidence/OWNER_UAT_CARD.md) | GOV-DOC-02 |
| **DOC-04 Notificaciones administrativas con constancia de recepción por canal autorizado** (GOV-DOC-005) | Menú › Gobierno › Notificaciones administrativas (y la sección «Notificaciones» del acto particular) | [`specs/gov-doc-04-notificaciones/evidence/OWNER_UAT_CARD.md`](../../../specs/gov-doc-04-notificaciones/evidence/OWNER_UAT_CARD.md) | GOV-DOC-04 |

Los otros 117 procesos siguen fuera del catálogo; ninguno se subió parcial (política §7). La retrospectiva del 2026-10-29 lo dejaba VACÍO y señalaba ORG-01 como primer candidato natural (IR §14).

## Fundamentos técnicos

Los fundamentos técnicos (MFA, aislamiento, copia y restauración…) **no** entran en este catálogo. No son procesos de Gobierno que la dueña pruebe como usuaria de negocio: ver la política, §5. Las pantallas de núcleo que ya existen, como `/seguridad/mfa`, son de la línea Empresarial.
