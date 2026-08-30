# CHECKLIST — ARCH-MC-001

## Antes de implementar

- [ ] Decisión de producto confirmada: **multiempresa por tenant**. No se re-pregunta.
- [ ] ADR de alcance canónico aprobado.
- [ ] Las 166 tablas clasificadas; **0 sin clasificar**.
- [ ] Las 36 derivadas verifican FK **obligatoria**.
- [ ] `OQ-MC-01` respondida antes de tocar los catálogos afectados.
- [ ] Transporte del contexto decidido y razonado (cabecera).
- [ ] PostgreSQL 18.6 y ClamAV reaprovisionados.

## Durante

- [ ] N1 antes que N2; N2 antes que N3.
- [ ] Ninguna hija se migra antes que su cabecera.
- [ ] Ninguna migración crea empresas por su cuenta.
- [ ] Ninguna columna heredada se borra antes de verificar.
- [ ] El informe previo se ejecuta sin escribir.
- [ ] Un crítico no reconstruible detiene la migración.
- [ ] Ningún escritor sigue poniendo `tenant_id` en `company_id`.

## Antes de declarar COMPLETE_100

- [ ] Los 66 criterios, con prueba que los ejecuta.
- [ ] Suite completa sobre **PostgreSQL 18.x**.
- [ ] Fixture de dos empresas en todos los dominios P0.
- [ ] Las 17 columnas `company_id` con FK pasan a ser **todas**.
- [ ] `grep` de `company_id = actor.tenant_id` devuelve **0**.
- [ ] Series fiscales, números de control y libros separados por empresa.
- [ ] Un pago de A no se aplica a una factura de B.
- [ ] Las existencias de A y B no se mezclan.
- [ ] Manipular el navegador no da acceso a otra empresa.
- [ ] Dos pestañas operan en empresas distintas sin contaminarse.
- [ ] Los 19 tipos de la Spec 046 probados; `STILL_BLOCKED_BY_046` = 0.
- [ ] `REM-046-001` cerrado y 046 convergida.
- [ ] 008, 011, 045 y 046 en regresión completa.
- [ ] Regresión global con **0 fallos**; ningún escenario multiempresa omitido.
- [ ] Ninguna columna de transición sobrevive.
- [ ] **Sin deuda interna diferida** (§227).
