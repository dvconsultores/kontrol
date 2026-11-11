# Spec PROC-09 · Compromiso de responsabilidad social (GOV-PROC-012, P1)

Estado: **BLOCKED en el CONSTITUTION GATE** (2026-11-11). Sin plan, tareas ni código; `DEEPSEEK_CALLS = 0`.

## Requisito

GOV-PROC-012 (IR): «Controlar compromiso de responsabilidad social cuando sea legalmente aplicable, con regla versionada y
soporte.» Fuente N11. Actor principal: Unidad contratante; relacionado: contratista.

## Qué tendría que hacer el producto (por fuente)

1. Determinar, por oferta y con una regla versionada, si el compromiso **aplica**, **no aplica** (con la exclusión y su artículo)
   o **no es determinable** (con los datos que faltan) — LCP art. 31; RLCP arts. 3, 34, 40, 48 y 49.
2. Registrar la declaración jurada del compromiso ofrecido con su soporte documental, y advertir el rechazo cuando falte siendo
   exigible — RLCP art. 38; LCP art. 76 num. 8.
3. Conservar el compromiso del adjudicatario con la regla y la versión aplicadas, y publicarlo con la adjudicación — RLCP art. 42.
4. Controlar su ejecución y cumplimiento antes del cierre administrativo del contrato — LCP arts. 30, 32 y 118 num. 3; RLCP
   arts. 36 y 44.

## Por qué está bloqueado

Ver `DECISIONES.md` (gate) y `FIELD_CONTRACT.md` (datos). En resumen:
- la procedencia depende del **monto total de la oferta con tributos**, que la plataforma no registra (OBS-PROC08-MONTO-01);
- el umbral está en **unidades tributarias** y su valor no tiene fuente verificada (N38, clase C);
- el **porcentaje** tiene un conflicto entre la LCP (3 %) y el RLCP (1 % a 5 %) que requiere validación jurídica;
- el control del cumplimiento depende del **contrato** (CNT-01, CNT-03, CNT-08) y la incorporación al pliego, de PROC-04.

## Para desbloquear

OQ-PROC09-01 a OQ-PROC09-04 en `DECISIONES.md`.
