# OWNER_UAT_READY_CATALOG — KONTROL Gobierno

> Retrospectiva GOV-PRODUCT-COMPLETENESS-RETRO-01 · `develop` `0dbe632` · 2026-10-29.

## Estado: VACÍO

Hoy **no hay ningún proceso de KONTROL Gobierno que la dueña pueda probar**:

- `OWNER_UAT_READY` = 0 de 122 procesos;
- `OWNER_ACCEPTED` = 0 de 122.

**Motivo.** Gobierno no tiene ninguna entrada de menú, pantalla, ruta de API, tabla ni migración (`GOVERNMENT_PRODUCT_INVENTORY.md` §1). La línea está en planificación: `GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0`, las fuentes siguen en SPONSOR REVIEW, el freeze normativo va en 0/10 y D-GOV-01..08 siguen abiertas.

No se ha subido ningún proceso parcial para que el catálogo no quede vacío (política §7).

## Qué tendría que pasar para la primera tarjeta

1. Freeze del sponsor y autorización expresa de implementar.
2. Que un ciclo GOV-n entregue un proceso con las doce compuertas de la política en PASS.
3. Que Claude escriba aquí su tarjeta: dónde entrar, rol, precondiciones, datos sintéticos, pasos, resultado, documentos, reportes, auditoría, prueba negativa, limpieza y deudas conocidas.

Según la IR §14, el primer candidato natural es GOV-0, por ejemplo ORG-01 «Configurar el ente» u ORG-03 «Cargos con competencias».

## Fundamentos técnicos

Los fundamentos técnicos (MFA, aislamiento, copia y restauración…) **no** entran en este catálogo. No son procesos de Gobierno que la dueña pruebe como usuaria de negocio: ver la política, §5. Las pantallas de núcleo que ya existen, como `/seguridad/mfa`, son de la línea Empresarial.
