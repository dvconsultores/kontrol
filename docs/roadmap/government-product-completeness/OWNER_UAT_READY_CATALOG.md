# OWNER_UAT_READY_CATALOG — KONTROL Gobierno

> Retrospectiva GOV-PRODUCT-COMPLETENESS-RETRO-01 · `develop` `0dbe632` · 2026-10-29. Actualizado por GOV-0-01 (2026-10-30) y GOV-0-02 (2026-10-31).

## Estado: 2 procesos listos para probar (2026-10-31)

- `OWNER_UAT_READY` = 2 de 122 procesos (1,64 %);
- `OWNER_ACCEPTED` = 0 de 122 (solo la dueña lo concede, tras probarlo).

| Proceso | Dónde entrar | Tarjeta | Ciclo |
|---|---|---|---|
| **ORG-01 Configurar el ente** (GOV-ORG-001) | Menú › Gobierno › Configuración del ente | [`specs/gov-0-01-configurar-ente/evidence/OWNER_UAT_CARD.md`](../../../specs/gov-0-01-configurar-ente/evidence/OWNER_UAT_CARD.md) | GOV-0-01 |
| **ORG-02 Estructura organizativa por ejercicio** (GOV-ORG-002, GOV-ORG-008) | Menú › Gobierno › Estructura organizativa | [`specs/gov-0-02-estructura-organizativa/evidence/OWNER_UAT_CARD.md`](../../../specs/gov-0-02-estructura-organizativa/evidence/OWNER_UAT_CARD.md) | GOV-0-02 |

Los otros 120 procesos siguen fuera del catálogo; ninguno se subió parcial (política §7). La retrospectiva del 2026-10-29 lo dejaba VACÍO y señalaba ORG-01 como primer candidato natural (IR §14).

## Fundamentos técnicos

Los fundamentos técnicos (MFA, aislamiento, copia y restauración…) **no** entran en este catálogo. No son procesos de Gobierno que la dueña pruebe como usuaria de negocio: ver la política, §5. Las pantallas de núcleo que ya existen, como `/seguridad/mfa`, son de la línea Empresarial.
