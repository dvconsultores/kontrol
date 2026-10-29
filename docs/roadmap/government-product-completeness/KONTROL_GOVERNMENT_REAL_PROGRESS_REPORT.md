# KONTROL GOBIERNO — REAL STATUS

> Retrospectiva GOV-PRODUCT-COMPLETENESS-RETRO-01 · 2026-10-29 · `develop` `0dbe632`. Norma aplicada: `docs/governance/product-completeness-and-owner-uat-policy.md`. Matrices de detalle en esta carpeta.

## Resumen para la dueña

**Hoy no hay ninguna parte de KONTROL Gobierno que puedas probar como usuaria.** No hay menú, pantallas, API ni datos de Gobierno. Lo que existe es:

- la planificación completa: requisitos, biblioteca normativa, arquitectura y readiness;
- un núcleo compartido técnico cada vez más sólido (MFA, permisos, auditoría, hora de Caracas, copia y restauración, aislamiento), sobre el que Gobierno se construirá.

Esto no contradice informes anteriores: ninguno afirmó que Gobierno estuviera listo. En el repositorio, la readiness dice BLOCKED y la arquitectura dice CLOSED como documento de planificación.

| Indicador | Valor | Fórmula y denominador |
|---|---|---|
| **Technical Foundation Readiness** | **36,8 %** | 14 fundamentos COMPLETE ÷ 38 fundamentos aplicables (34,2 % = 13/38 en la retrospectiva; +F05 al cerrar el ciclo 07) |
| **Functional Product Completeness** | **0,0 %** | 0 compuertas en PASS ÷ 1 280 compuertas aplicables |
| **Owner UAT Ready** | **0,0 %** | 0 procesos listos para probar ÷ 122 procesos requeridos |
| **Owner Accepted** | **0,0 %** | 0 procesos aceptados por la dueña ÷ 122 |

No hay redondeo al alza. Las cuatro cifras no se combinan.

## Módulos (§43)

| Módulo | Procesos | Aceptados | Listos para probar | Parciales | No iniciados | Bloqueados | ¿Completo? |
|---|---|---|---|---|---|---|---|
| Government Core: ente, estructura y autoridad | 7 | 0 | 0 | 0 | 4 | 3 | NO |
| Presupuesto público | 13 | 0 | 0 | 0 | 4 | 9 | NO |
| Requisiciones públicas | 5 | 0 | 0 | 0 | 4 | 1 | NO |
| Contrataciones públicas / Licitaciones | 12 | 0 | 0 | 0 | 9 | 3 | NO |
| Contratos públicos | 9 | 0 | 0 | 0 | 8 | 1 | NO |
| Almacén de consumo público | 5 | 0 | 0 | 0 | 4 | 1 | NO |
| Tesorería pública | 10 | 0 | 0 | 0 | 8 | 2 | NO |
| Contabilidad pública | 8 | 0 | 0 | 0 | 3 | 5 | NO |
| Bienes públicos / Activo fijo patrimonial | 11 | 0 | 0 | 0 | 5 | 6 | NO |
| Expedientes y actos administrativos | 8 | 0 | 0 | 0 | 4 | 4 | NO |
| Control interno, auditoría y rendición | 10 | 0 | 0 | 0 | 8 | 2 | NO |
| Gobierno Digital: trámites e interoperabilidad | 3 | 0 | 0 | 0 | 0 | 3 | NO |
| Gasto de personal e interfaz Atenea | 3 | 0 | 0 | 0 | 1 | 2 | NO |
| Integraciones institucionales | 7 | 0 | 0 | 0 | 1 | 6 | NO |
| Reportes y tableros institucionales | 11 | 0 | 0 | 0 | 6 | 5 | NO |
| **Total** | **122** | **0** | **0** | **0** | **69** | **53** | **0 de 15** |

- **Prefecturas:** no está en los requisitos ni en el repositorio (MOQ-RETRO-02).
- **Activos fijos privados (Spec 057):** PLANNED / NOT_STARTED; es otra línea de producto.

**Listos para probar:** ninguno (`OWNER_UAT_READY_CATALOG.md`, vacío).
**Parciales:** ninguno. No hay nada de Gobierno construido a medias.
**No iniciados:** 69 procesos sin otro impedimento que la puerta general de entrada (freeze del sponsor y autorización).
**Bloqueados por norma o decisión:** 53 procesos.
- 35 dependen de una decisión del sponsor D-GOV-01..08:
  - la jurisdicción piloto;
  - la profundidad presupuestaria;
  - SNC y SUDEBIP;
  - la contabilidad ONCOP;
  - el catálogo de trámites;
  - Atenea;
  - la firma y la interoperabilidad.
- Los otros 18 citan una fuente de clase C sin pin oficial, sobre todo:
  - N37, ordenanzas locales, que dependen de la jurisdicción piloto;
  - N40, normas técnicas de seguridad digital;
  - N07–N10, instructivos ONAPRE y clasificador;
  - N14–N17, providencias SUDEBIP;
  - N36, contabilidad pública;
  - N38, normativa tributaria.

  La regla aplicada es la de la línea base: una fuente de clase C no sustenta reglas P0 hasta el freeze. Es una regla prudente, y varios de estos procesos pasarán a «no iniciado» cuando el freeze fije esas fuentes.

**Bloqueos técnicos** (fundamentos no COMPLETE con deuda abierta):

| Bloqueo | Siguiente paso |
|---|---|
| RTO/RPO (F12) | ciclo 08 |
| Fiabilidad del arnés E2E/TOTP (F25) | ciclo 09 |
| Certificación oficial de release (F30) | anfitrión dedicado |
| Dimensión de ente (F06), auditoría institucional (F08), versionado normativo (F16), numeración institucional (F38) | GOV-0 |

## Cómo se calculó cada cifra

**A · Technical Foundation Readiness = 14 ÷ 38 = 36,8 %** (13/38 en la retrospectiva; F05 pasó a COMPLETE con el cierre del ciclo 07, 2026-10-29).
- Hay 38 fundamentos (`GOVERNMENT_TECHNICAL_FOUNDATION_MATRIX.md`): los 25 RNF-GOV de la IR §10 desglosados por mecanismo, más los motores del núcleo que Gobierno reutiliza (045, 046, 047, 004, 050, shell, certificación, tres navegadores) y los fundamentos propios de Gobierno (ente, auditoría institucional, versión normativa, numeración).
- Cuenta como COMPLETE solo lo que tiene delta convergido con evidencia en `HEAD`: F01–F05, F07, F09–F11, F24, F29, F31, F33 y F37.
- No cuentan:
  - los NOT_MEASURED.
- Recuento: COMPLETE 14 · PARTIAL 12 · NOT_STARTED 7 · NOT_MEASURED 4 · BLOCKED 1.

**B · Functional Product Completeness = 0 ÷ 1 280 = 0,0 %.**
- Hay 122 procesos × 11 compuertas funcionales: backend, frontend, menú, proceso, campos, roles, documentos, reportes, auditoría, E2E y ficha de pantalla. Eso da 1 342.
- Se restan 44 compuertas de documentos y 18 de reportes que no aplican: quedan 1 280.
- Ninguna está en PASS.
- Aunque fuese mayor que 0, este porcentaje **no** dice que un módulo esté terminado: eso solo lo dice la tabla de módulos.

**C · Owner UAT Ready = 0 ÷ 122 = 0,0 %**, y **Owner Accepted = 0 ÷ 122 = 0,0 %**.

## Requisitos de Ingeniería (§38, §70)

194 entradas de la IR, todas trazadas: `ENGINEERING_REQUIREMENTS_COVERAGE = 100 %` y `UNEXPLAINED_REQUIREMENT_OMISSIONS = 0`.

| Tipo | N | Estado |
|---|---|---|
| Funcionales GOV-* | 153 | 152 en 122 procesos: 81 BLOCKED, 71 NOT_STARTED. 1 (GOV-DIG-010, estándares de Infogobierno) es fundamento F21: NOT_MEASURED |
| No funcionales RNF-GOV | 25 | 6 PASS en el núcleo (003, 006, 012, 015, 019, 025) · 11 PARTIAL · 4 NOT_MEASURED · 4 NOT_STARTED |
| Aceptación E2E-01..08 | 8 | 6 FAIL. E2E-06 (hostil multi-ente) y E2E-08 (restauración) PARTIAL: solo el núcleo; el ente y los ledgers de Gobierno no existen |
| Puertas del sponsor D-GOV-01..08 | 8 | las 8 OPEN |

## Afirmaciones históricas (§50, §83)

75 afirmaciones inventariadas y reconciliadas (`GOVERNMENT_HISTORICAL_CLAIM_INVENTORY.md`); 0 sin explicar.

| Clase de afirmación | N | Qué significa hoy |
|---|---|---|
| CONFIRMED | 27 | BLOCKED, SPONSOR REVIEW y NOT_STARTED siguen siendo ciertos |
| CONFIRMED — PLANNING CLOSED, NOT PRODUCT | 3 | la línea base está cerrada como plan, no como producto |
| TECHNICAL_FOUNDATION / _COMPLETE | 24 | cierres técnicos correctos que no conceden estado de producto de Gobierno |
| TECHNICALLY CLOSED BUT NOT PRODUCT COMPLETE | 1 | MFA: convergido como fundamento; no es un proceso de Gobierno |
| PARTIAL / NOT_MEASURED | 10 | filas RNF de la readiness del 2026-10-25, remedidas hoy |
| PREMATURE | 2 | dos frases del árbol del ciclo 07 (sin commit) decían «certificado» antes de la E2E. Ya se corrigieron en el árbol |
| CLAIM_NOT_FOUND_IN_REPOSITORY | 3 | «Activo Fijo listo», «Contrataciones 70 %», «Prefecturas listo»: no aparecen en ningún documento del repositorio |
| OUT_OF_SCOPE_PRIVATE_LINE | 1 | «Almacén privado (008, COMPLETE)»: técnicamente cerrado; se revalida en la retrospectiva privada |
| NOT_A_GOVERNMENT_CLAIM / NOT_A_STATUS_CLAIM | 4 | «gobierno» en el sentido de gobernanza, o una condición de secuencia |

Ningún informe anterior queda desmentido. Lo que cambia es la interpretación: un cierre técnico ya no se lee como avance de producto.

## Replanificación (§88)

- **Resultado C:** ningún módulo de Gobierno está listo para UAT, y se dice así.
- **Resultado A:** ningún módulo reclamado tiene comportamiento parcial peligroso, porque no hay ninguno construido. **No** hace falta una remediación inmediata de producto.
- Se mantiene la secuencia técnica:
  1. ~~cerrar **P0-HARDENING-07**~~ (cerrado el 2026-10-29: F05 COMPLETE);
  2. **08** BACKUP SCHEDULE / RPO;
  3. **09** E2E TOTP / AUTH HARNESS RELIABILITY;
  4. **GOVERNMENT READINESS RECONCILIATION**, que hereda esta norma y este backlog.
- Desde ahora, todo ciclo de producto aplica la política (§13 de la política).
- **El primer entregable que la dueña podrá probar** llegará con el primer ciclo GOV-n autorizado tras el freeze. Por la IR §14, el candidato natural es GOV-0: configurar el ente y los cargos con competencias.

## Preguntas materiales para la dueña

- **MOQ-RETRO-01:** ¿aplicamos esta misma norma, con una retrospectiva igual, a la línea **Empresarial**? Son 57 Specs con pantallas reales, y ahí sí puede haber controles muertos, backend sin pantalla y cierres técnicos que no son producto completo. Hoy está fuera de alcance porque el encargo es de Gobierno.
- **MOQ-RETRO-02:** «Prefecturas»: ¿es alcance de KONTROL Gobierno? Si lo es, ¿cuál es su fuente de requisitos? No está en la IR v1.0.
