# KONTROL GOBIERNO — REAL STATUS

> Retrospectiva GOV-PRODUCT-COMPLETENESS-RETRO-01 · 2026-10-29 · `develop` `0dbe632`. Norma aplicada: `docs/governance/product-completeness-and-owner-uat-policy.md`. Matrices de detalle en esta carpeta.

## Resumen para la dueña

**Actualización GOV-ORG-FUNCTIONAL-06 (2026-11-07): el sponsor cerró el piloto (Alcaldía del Municipio Naguanagua) e integrar con Atenea. ORG-06 no puede construirse completo sin ORG-04: el ocupante de un cargo puede ser suplente, delegado o encargado, y hasta el titular se designa ahí. Sin producto parcial. Siguiente vertical: ORG-04. Las cifras de producto no cambian.**

**Actualización GOV-NORM-N40-01 (2026-11-07): N40 es un corpus, no una norma. De 21 requisitos que la citan, 1 la necesita por completo. Se retira de ORG-06, CTL-02, CTL-03 y DOC-07, se acota en DOC-01, DIG-02 y HR-02, y se mantiene en DOC-05 y DIG-03. La reclasificación no suma producto. Siguiente vertical: ORG-06.**

**Actualización GOV-CTL-FUNCTIONAL-05 (2026-11-07): «Historial de cambios de maestros sensibles» queda BLOQUEADO. GOV-CTL-010 nombra proveedores y clasificadores, que no existen como maestros de Gobierno, y no fija qué significa «cuentas». Ningún otro vertical de Gobierno es elegible hoy; el bloqueo de mayor desbloqueo resoluble por ingeniería es N40.**

**Actualización GOV-DOC-03 (2026-11-07): «Lapsos, suspensiones, subsanaciones y prórrogas» queda BLOQUEADO. Los lapsos de la LOPA corren sobre una solicitud o un expediente, y DOC-01 sigue bloqueado; además, el art. 42 exige el calendario de la Administración Pública, sin fuente ni responsable en KONTROL. Siguiente vertical: CTL-08.**

**Actualización GOV-0-06 (2026-11-08): ya hay quince procesos de Gobierno que puedes probar como usuaria; el nuevo es «Vincular usuario con identidad, cargo, unidad y alcance; separación de roles» (menú Gobierno › Identidad institucional). Dice qué cuenta era qué funcionario, con qué cargo, unidad y autoridad en cualquier fecha. La certificación exhaustiva de esta vertical queda en `FINAL_GOVERNMENT_CERTIFICATION.md`, por directiva de la dueña.**

**Actualización GOV-ORG-04 (2026-11-07): ya hay catorce procesos de Gobierno que puedes probar como usuaria; el nuevo es «Delegaciones, suplencias, encargadurías y designaciones con acto» (menú Gobierno › Ocupación de cargos). Dice quién ejerce cada cargo, bajo qué figura, por qué acto, emitido por quién, desde cuándo y hasta cuándo, y qué autoridad tiene a una fecha. Quien registra no activa. Con esto ORG-06 ya no está bloqueado por ORG-04.**

**Actualización GOV-CTL-10 (2026-11-07): ya hay trece procesos de Gobierno que puedes probar como usuaria; el nuevo es «Controles materiales que impiden cerrar ejercicio o proceso» (menú Gobierno › Controles de cierre). Una política de Control Interno impide cerrar la estructura de un ejercicio o un programa financiero mientras haya hallazgos abiertos o actos sin eficacia, y el cierre explica qué falta. Dos cierres y dos controles, sin motor de reglas. Abiertas, ambas LOW: OBS-CTL10-LISTA-01 y T043.**

**Actualización GOV-CTL-06 (2026-11-04): ya hay ocho procesos de Gobierno que puedes probar como usuaria; el nuevo es «Hallazgos, recomendaciones y planes de acción correctiva» (menú Gobierno › Hallazgos y acciones correctivas, o «Registrar hallazgo» desde una muestra de la auditoría institucional): Control Interno registra el hallazgo con su condición, criterio, causa, efecto y riesgo, emite recomendaciones y un plan de acción con cargo responsable y fecha objetivo, registra los avances con su evidencia y lo presenta; otro usuario de Control Interno lo verifica y cierra (o lo devuelve), con historia completa y el plan exportable.** Su tarjeta está en `OWNER_UAT_READY_CATALOG.md`. Ninguno está aceptado: eso lo decides tú al probarlos.

**Actualización GOV-CTL-04 (2026-11-03): ya hay siete procesos de Gobierno que puedes probar como usuaria; el nuevo es «Consulta y muestreo read-only del auditor interno/externo» (menú Gobierno › Auditoría institucional): la población de eventos de Gobierno del ente con filtros, la evidencia segura de cada evento con enlace al objeto, y muestras guardadas como papel de trabajo que no se puede cambiar (todas las partidas, partidas específicas o selección aleatoria con semilla visible y reproducible), con su CSV auditado. Además, los actos administrativos (DOC-02) ya validan cargo, competencia y autoridad a la fecha del acto, no a la de hoy (FIND-ORG07-01 cerrado).** Su tarjeta está en `OWNER_UAT_READY_CATALOG.md`. Ninguno está aceptado: eso lo decides tú al probarlos.

**Actualización GOV-ORG-07 (2026-11-02): ya hay seis procesos de Gobierno que puedes probar como usuaria; el nuevo es «Matriz auditable de quién puede solicitar, comprometer, causar, ordenar el pago, pagar, registrar, custodiar, aprobar, auditar y firmar» (menú Gobierno › Matriz de autoridad): por ejercicio y a una fecha, qué cargo puede qué, sobre qué materia, en qué unidad, hasta qué monto, con qué acto y vigencia, con su historial y su CSV auditado. La autoridad es la del cargo (ORG-03); las personas y las delegaciones llegarán con ORG-06 y ORG-04.** Su tarjeta está en `OWNER_UAT_READY_CATALOG.md`. Ninguno está aceptado: eso lo decides tú al probarlos.

**Actualización GOV-DOC-04 (2026-11-02): ya hay cinco procesos de Gobierno que puedes probar como usuaria; el nuevo es «Notificaciones administrativas con constancia de recepción por canal autorizado» (menú Gobierno › Notificaciones administrativas; los destinatarios se agregan desde el acto particular): a cada interesado se le entrega el acto en persona con recibo firmado o, si no se pudo, se publica en prensa y queda notificado a los 15 días (LOPA arts. 75–76); cuando todos están notificados, el acto pasa a «Eficaz» con la fecha más tardía. El panel «Registrar la notificación» de DOC-02 ya no existe para los actos particulares: la Gaceta de los actos generales sigue en DOC-02.** Su tarjeta está en `OWNER_UAT_READY_CATALOG.md`. Ninguno está aceptado: eso lo decides tú al probarlos.

**Actualización GOV-DOC-02 (2026-11-01): ya hay cuatro procesos de Gobierno que puedes probar como usuaria; el nuevo es «Actos administrativos con autoridad, competencia, motivación, eficacia y notificación» (menú Gobierno › Actos administrativos): registras el acto ya firmado con el cargo que lo dicta y su competencia, lo emites sobre su PDF, registras su publicación o notificación (con la regla de 15 días de la prensa) y, si hace falta, su corrección, revocación o nulidad.** Su tarjeta está en `OWNER_UAT_READY_CATALOG.md`. Ninguno está aceptado: eso lo decides tú al probarlos.

**Actualización GOV-0-04 (2026-11-01): «Responsables por unidad, programa, proyecto, cuenta, almacén, caja, banco, contrato y bien» (ORG-05) queda BLOQUEADO: de los nueve objetos sobre los que hay que nombrar responsables, Gobierno solo tiene hoy las unidades; programas, proyectos, cuentas, almacenes, cajas, cuentas bancarias, contratos y bienes llegan con sus propios procesos. Además hacen falta tres decisiones tuyas (`specs/gov-0-04-responsables/evidence/ORG05_BLOCKER_REPORT.md`). Tu entorno de prueba ya tiene ORG-03.** Las cifras de avance no cambian.

**Actualización GOV-0-03 (2026-11-01): ya hay tres procesos de Gobierno que puedes probar como usuaria: «Configurar el ente», «Estructura organizativa por ejercicio» y «Cargos con competencias y límites de firma/aprobación» (menú Gobierno › Cargos y competencias, GOV-0-03).** Sus tarjetas de prueba están en `OWNER_UAT_READY_CATALOG.md`. Ninguno está aceptado: eso lo decides tú al probarlos.

**Actualización GOV-0-02 (2026-10-31): ya hay dos procesos de Gobierno que puedes probar como usuaria: «Configurar el ente» (menú Gobierno › Configuración del ente, GOV-0-01) y «Estructura organizativa por ejercicio» (menú Gobierno › Estructura organizativa, GOV-0-02).** Sus tarjetas de prueba están en `OWNER_UAT_READY_CATALOG.md`. Ninguno está aceptado: eso lo decides tú al probarlos. El resto de Gobierno sigue sin menú, pantallas ni API. La retrospectiva del 2026-10-29 decía:

> Hoy no hay ninguna parte de KONTROL Gobierno que puedas probar como usuaria. No hay menú, pantallas, API ni datos de Gobierno. Lo que existe es:

- la planificación completa: requisitos, biblioteca normativa, arquitectura y readiness;
- un núcleo compartido técnico cada vez más sólido (MFA, permisos, auditoría, hora de Caracas, copia y restauración, aislamiento), sobre el que Gobierno se construirá.

Esto no contradice informes anteriores: ninguno afirmó que Gobierno estuviera listo. En el repositorio, la readiness dice BLOCKED y la arquitectura dice CLOSED como documento de planificación.

| Indicador | Valor | Fórmula y denominador |
|---|---|---|
| **Technical Foundation Readiness** | **36,8 %** | 14 fundamentos COMPLETE ÷ 38 fundamentos aplicables (34,2 % = 13/38 en la retrospectiva; +F05 al cerrar el ciclo 07) |
| **Functional Product Completeness** | **12,1 %** (12,14 %) | 155 compuertas en PASS ÷ 1 277 compuertas aplicables (ORG-01: 10/10; ORG-02: 11/11; ORG-03: 11/11; ORG-06: 10/10; ORG-07: 10/10; DOC-02: 11/11; DOC-04: 11/11; CTL-04: 10/10; CTL-06: 11/11; DOC-08: 11/11; CTL-01: 10/10; TRE-01: 10/10; TRE-02: 9/9; CTL-10: 9/9; ORG-04: 11/11; 0 en la retrospectiva) |
| **Owner UAT Ready** | **12,3 %** (12,30 %) | 15 procesos listos para probar (ORG-01, ORG-02, ORG-03, ORG-04, ORG-06, ORG-07, DOC-02, DOC-04, CTL-04, CTL-06, DOC-08, CTL-01, TRE-01, TRE-02, CTL-10) ÷ 122 procesos requeridos |
| **Owner Accepted** | **0,0 %** | 0 procesos aceptados por la dueña ÷ 122 |

No hay redondeo al alza. Las cuatro cifras no se combinan.

## Módulos (§43)

| Módulo | Procesos | Aceptados | Listos para probar | Parciales | No iniciados | Bloqueados | ¿Completo? |
|---|---|---|---|---|---|---|---|
| Government Core: ente, estructura y autoridad | 7 | 0 | 6 | 0 | 0 | 1 | NO |
| Presupuesto público | 13 | 0 | 0 | 0 | 4 | 9 | NO |
| Requisiciones públicas | 5 | 0 | 0 | 0 | 4 | 1 | NO |
| Contrataciones públicas / Licitaciones | 12 | 0 | 0 | 0 | 9 | 3 | NO |
| Contratos públicos | 9 | 0 | 0 | 0 | 8 | 1 | NO |
| Almacén de consumo público | 5 | 0 | 0 | 0 | 4 | 1 | NO |
| Tesorería pública | 10 | 0 | 2 | 0 | 5 | 3 | NO |
| Contabilidad pública | 8 | 0 | 0 | 0 | 3 | 5 | NO |
| Bienes públicos / Activo fijo patrimonial | 11 | 0 | 0 | 0 | 5 | 6 | NO |
| Expedientes y actos administrativos | 8 | 0 | 3 | 0 | 0 | 5 | NO |
| Control interno, auditoría y rendición | 10 | 0 | 4 | 0 | 5 | 1 | NO |
| Gobierno Digital: trámites e interoperabilidad | 3 | 0 | 0 | 0 | 0 | 3 | NO |
| Gasto de personal e interfaz Atenea | 3 | 0 | 0 | 0 | 1 | 2 | NO |
| Integraciones institucionales | 7 | 0 | 0 | 0 | 1 | 6 | NO |
| Reportes y tableros institucionales | 11 | 0 | 0 | 0 | 6 | 5 | NO |
| **Total** | **122** | **0** | **15** | **0** | **55** | **52** | **0 de 15** |

(Errata corregida en GOV-DOC-04: la fila de Expedientes y el total no se habían actualizado con DOC-02.)

- **Prefecturas:** no está en los requisitos ni en el repositorio (MOQ-RETRO-02).
- **Activos fijos privados (Spec 057):** PLANNED / NOT_STARTED; es otra línea de producto.

**Listos para probar:** 5 (ORG-01, ORG-02, ORG-03, DOC-02, DOC-04; `OWNER_UAT_READY_CATALOG.md`).
**Parciales:** ninguno. No hay nada de Gobierno construido a medias.
**No iniciados:** 64 procesos sin otro impedimento que la puerta general de entrada (freeze del sponsor y autorización); 122 = 5 listos + 64 no iniciados + 53 bloqueados (errata: hasta GOV-0-03 decía 69 sin descontar los listos).
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

**B · Functional Product Completeness = 155 ÷ 1 277 = 12,14 %** (0 en la retrospectiva; +10 de ORG-01 con GOV-0-01, 2026-10-30; +11 de ORG-02 con GOV-0-02, 2026-10-31; +11 de ORG-03 con GOV-0-03 y +11 de DOC-02 con GOV-DOC-02, 2026-11-01; +11 de DOC-04 con GOV-DOC-04 y +10 de ORG-07 con GOV-ORG-07, 2026-11-02; +10 de CTL-04 con GOV-CTL-04, 2026-11-03; +11 de CTL-06 con GOV-CTL-06, +11 de DOC-08 con GOV-DOC-08 y +10 de CTL-01 con GOV-CTL-01, 2026-11-04). +11 de TRE-01 con GOV-TRE-01, 2026-11-05; −1 de TRE-01 por reclasificar sus reportes como NOT_APPLICABLE y +9 de TRE-02 con GOV-TRE-02 y T038, 2026-11-06; +9 de CTL-10 con GOV-CTL-10, 2026-11-07.
- Hay 122 procesos × 11 compuertas funcionales: backend, frontend, menú, proceso, campos, roles, documentos, reportes, auditoría, E2E y ficha de pantalla. Eso da 1 342.
- Se restan 44 compuertas de documentos y 21 de reportes que no aplican: quedan 1 277 (GOV-CTL-10 reclasificó el reporte de CTL-10 como NOT_APPLICABLE, FR-025: GOV-CTL-012 no exige exportación; GOV-TRE-02 reclasificó los reportes de TRE-01 y TRE-02 como NOT_APPLICABLE: ningún requisito exige uno; por eso TRE-01 pasa de 11/11 a 10/10).
- En PASS: las 10 compuertas aplicables de ORG-01 (reportes no aplica, justificado en su Spec) y las 11 de ORG-02, ORG-03, DOC-02 y DOC-04 (listado + CSV, documento obligatorio). Ninguna otra.
- Aunque fuese mayor que 0, este porcentaje **no** dice que un módulo esté terminado: eso solo lo dice la tabla de módulos.

**C · Owner UAT Ready = 15 ÷ 122 = 12,30 %** (ORG-01, ORG-02, ORG-03, ORG-04, ORG-06, ORG-07, DOC-02, DOC-04, CTL-04, CTL-06, DOC-08, CTL-01, TRE-01, TRE-02, CTL-10), y **Owner Accepted = 0 ÷ 122 = 0,0 %** (solo la dueña lo concede).

## Requisitos de Ingeniería (§38, §70)

194 entradas de la IR, todas trazadas: `ENGINEERING_REQUIREMENTS_COVERAGE = 100 %` y `UNEXPLAINED_REQUIREMENT_OMISSIONS = 0`.

| Tipo | N | Estado |
|---|---|---|
| Funcionales GOV-* | 153 | 152 en 122 procesos: 77 BLOCKED, 57 NOT_STARTED, 18 OWNER_UAT_READY (GOV-ORG-001, -002, -003, -004, -005, -007, -008, -009, -010, GOV-DOC-003, -005, -010, GOV-CTL-001, -005, -008, -012, GOV-TRE-001, -002). 1 (GOV-DIG-010, estándares de Infogobierno) es fundamento F21: NOT_MEASURED |
| No funcionales RNF-GOV | 25 | 6 PASS en el núcleo (003, 006, 012, 015, 019, 025) · 11 PARTIAL · 4 NOT_MEASURED · 4 NOT_STARTED |
| Aceptación E2E-01..08 | 8 | 6 FAIL. E2E-06 (hostil multi-ente) y E2E-08 (restauración) PARTIAL: solo el núcleo; el ente y los ledgers de Gobierno no existen |
| Puertas del sponsor D-GOV-01..08 | 8 | 6 OPEN; D-GOV-01 CLOSED (Alcaldía del Municipio Naguanagua, Carabobo); D-GOV-07 SPONSOR_SCOPE_CLOSED (integrar con Atenea; contrato técnico ENGINEERING_PENDING) |

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
