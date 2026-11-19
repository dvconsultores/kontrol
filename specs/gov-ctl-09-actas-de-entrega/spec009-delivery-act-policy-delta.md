# Delta CTL-09 · Política de actas de entrega (CTL-09-DELIVERY-ACT-POLICY)

**Spec dueña:** `specs/gov-ctl-09-actas-de-entrega/spec.md`. **Prioridad:** P0, por un defecto de producto vigente.
**Autorización de implement:** el encargo «P2 — CTL-09 · Actas de entrega paramétricas y normativa versionada» (2026-11-18).

## 1. Defecto P0

- **Antes** (`service_actas.py`):
  - `ANEXOS_CATALOGO` (A11_1..A11_6) y `ANEXOS_MUNICIPALES` (A17_1..A17_5) son listas fijas, sin fuente, versión ni vigencia;
  - al crear el acta, A17 se añade a todo ente `MUNICIPAL` con ámbito `ENTE`, sin mirar qué órgano es: un instituto, una fundación, un Concejo o una Contraloría municipal reciben como obligatorios los anexos de una Alcaldía;
  - y al revés: el acta de la **Dirección de hacienda municipal** (una dependencia, ámbito `UNIDAD`) no los recibe, aunque N34 art. 17 se los exige;
  - los arts. 12 a 16 (unidad administradora, ramos específicos, control fiscal, Ministerio de Finanzas, Gobernación y hacienda estadal) no existen;
  - testigos (art. 9), numeración `AE-` y plazos (arts. 4, 21 y 22) están en el código sin fuente ni versión;
  - el anexo A11_2 resuelve el ocupante de cada cargo con una copia propia de la vigencia (`_asignacion_al_corte`), que ignora los actos nulos o revocados y la vigencia del cargo.
- **Causa raíz:** el servicio infiere el sujeto del art. 17 a partir del nivel territorial (`municipal == alcaldía`). La norma lo define por el **órgano** (Alcaldía o Dirección de hacienda), un dato que KONTROL no tenía.
- **Después:**
  - una sola autoridad (`service_actas_regla.py`) resuelve la **regla aplicada** a cada acta: el catálogo legal versionado de N34 más la política del ente;
  - los supuestos de los arts. 12–17 se aplican solo donde la política del ente **los declara**, a la entidad o a unidades concretas (OD-AE-01);
  - la creación, la suscripción, la ficha y la UI usan esa regla, y el acta la congela.

## 2. Fuente verificada

Copia oficial custodiada: `requerimientos/gobierno/normativa-n34/N34_GO_39229_Res_CGR_01-00-000162_copia_CEBM.pdf` (SHA-256 `436856805eabb9f80a85f30610adf09eeaf3f8b5793e7245dd5bd76800d5cd90`, descargada de cebm.gob.ve el 2026-11-18). Resolución CGR Nº 01-00-000162, G.O. 39.229 (28-07-2009), vigente desde su publicación (art. 29), sin derogación conocida. El detalle por regla está en `evidence/delivery-act-policy/N34_VALIDATION.md`.

| Art. | Sujeto | Lo que fija |
|---|---|---|
| 5 | Poder Público nacional, estadal, distrital y municipal; institutos autónomos; personas de derecho público; sociedades y fundaciones con participación pública | **Todo** servidor que administre o custodie recursos entrega mediante acta |
| 4 | Toda acta | Se entrega en la toma de posesión o dentro de **3 días hábiles** |
| 9 | Acta levantada por quien recibe | **Dos testigos** y el auditor interno |
| 10 | Toda acta | Contenido mínimo |
| 11 | Toda acta (órgano, entidad, oficina o dependencia) | Anexos 1–6 |
| 12 | Unidad administradora | Los anexos del Reglamento Nº 1 de la LOAFSP (no custodiado) |
| 13 | Oficinas o dependencias que manejan ramos específicos | Lo liquidado y recaudado, y los derechos pendientes |
| 14 | Órganos de control fiscal | Expedientes de investigación y de determinación de responsabilidades |
| 15 | Ministerio de Finanzas | 4 anexos |
| 16 | Gobernación, oficina o dependencia de hacienda estadal | 3 anexos |
| 17 | **Alcaldía o Dirección de hacienda distrital o municipal** | 5 anexos |
| 19 | Toda acta | Si falta la información, se deja constancia y motivo |
| 21 | Toda acta | Copia a la UAI dentro de **5 días hábiles** |
| 22 | Quien recibe | Observaciones dentro de **120 días hábiles** |

**MATERIAL_NORMATIVE_UNKNOWN=YES**, resuelta por la dueña con OD-AE-01:

- los datos del ente (nivel MUNICIPAL y forma ADMINISTRACION_CENTRAL) no distinguen una Alcaldía de un Concejo o una Contraloría municipal, y ningún dato marca la Dirección de hacienda. KONTROL no infiere el sujeto: lo declara el ente.
- El art. 12 remite al Reglamento Nº 1 de la LOAFSP, que no está custodiado: el supuesto queda sin anexos enumerados y el ente define los suyos.
- KONTROL no tiene nivel DISTRITAL (`NIVELES_TERRITORIALES`). El art. 17 se admite en entes MUNICIPALES; el distrital queda como deuda.

## 3. Decisiones de la dueña (2026-11-18)

| Id | Decisión |
|---|---|
| OD-AE-01 | Los supuestos de los arts. 12–17 se **declaran en la política** del ente, vinculados a la entidad o a unidades concretas. Sin vínculo solo rige el art. 11 |
| OD-AE-02 | **Transición con aviso, sin automatismo ni backfill.** Las actas existentes conservan sus anexos. En un ente municipal sin el art. 17 declarado, la UI avisa: «Si el acta corresponde a una Alcaldía o Dirección de hacienda, declárelo en la política de actas» |
| OD-AE-03 | El catálogo legal versionado incluye los **arts. 11 a 17** |
| OD-AE-04 | Sin patrón configurado, la numeración sigue `AE-{ANIO}-{NUMERO:4}` como configuración operativa por defecto |
| OD-AE-05 | Tope de 16 llamadas a DeepSeek (encargo §59) |

## 4. Decisiones de diseño de Claude

| Id | Decisión |
|---|---|
| D-AE-01 | **Catálogo legal** en código, versionado (`N34-2009`), con fuente, artículo, sujeto, niveles en que se puede declarar y ámbitos. Es LEGAL_MANDATORY: el ente no lo edita. El art. 11 es universal; los arts. 12–17 son declarables |
| D-AE-02 | **Piso legal estructural:** los anexos legales no se copian a la política, así que no se pueden rebajar. La política solo **añade** vínculos, requisitos, testigos y plazos internos. Un vínculo del art. 15 exige ente NACIONAL, el del art. 16 ESTADAL y el del art. 17 MUNICIPAL. Un plazo interno no puede superar el legal del mismo hito |
| D-AE-03 | **Una política VIGENTE por empresa** (índice único parcial). Versiones BORRADOR → VIGENTE → CERRADA; activar una versión nueva cierra la anterior como SUSTITUIDA. Se aplica la política vigente cuya vigencia cubre la fecha de corte |
| D-AE-04 | **Requisitos del ente con tipo de evidencia:** DOCUMENTO, CERTIFICACION, DECLARACION o DATO, con ámbito (TODAS, ENTE o UNIDAD), opcionalmente atados a un supuesto y a un tipo documental del catálogo existente (`document_types`). Un DOCUMENTO o una CERTIFICACION se resuelven con documentos (del tipo exigido, si lo hay); una DECLARACION o un DATO, con texto. Todos admiten la constancia del art. 19 |
| D-AE-05 | **Testigos:** el piso del art. 9 (dos testigos y auditor en el acta levantada por el receptor) sigue fijo y con fuente. La política puede exigir testigos también en la entrega por el saliente (`testigos_en_entrega`, de 0 a 5) |
| D-AE-06 | **Plazos:** los legales (arts. 4, 21 y 22) se expresan en días hábiles. Como no hay calendario hábil oficial (DOC-03 bloqueado; BUSINESS_CALENDAR no existe), se muestran con su fuente y sin vencimiento calculado («Sin calendario hábil oficial»). La política puede fijar plazos internos de ELABORACION y REMISION_UAI en días continuos, que sí se calculan: EN_PLAZO, VENCIDO, CUMPLIDO o CUMPLIDO_FUERA_DE_PLAZO. Informan y no bloquean: N34 no anula un acta tardía, la sanciona (art. 26) |
| D-AE-07 | **Numeración:** patrón de la política con `{ANIO}` y `{NUMERO:n}` (n de 3 a 6, obligatorio), de 20 caracteres como máximo, con vista previa. La secuencia sigue siendo por empresa y prefijo |
| D-AE-08 | **Responsabilidad (ORG-04 reutilizada):** el saliente tiene que ejercer su ocupación el día del corte según la autoridad de ORG-04 (`situacion_en`), y A11_2 usa `_vigentes_en`. Se eliminan `_asignacion_al_corte` y `_estado_vigente`. La regla congela el bloque `responsabilidad`: saliente, receptor, relación (SUCESOR si el receptor ocupa el mismo cargo; DESIGNADO si no), ámbito, unidad y fecha efectiva |
| D-AE-09 | **Congelación:** la regla se resuelve al crear el borrador y se recalcula al editarlo (los anexos se sincronizan: se añaden los nuevos, se quitan los que ya no aplican y se conserva lo resuelto de los que siguen). Se guarda en el acta (`policy_id`, `policy_version`, `regla`). Suscribir la incluye en la instantánea con huella, y el disparador de PG impide cambiarla después |
| D-AE-10 | **Legado:** un acta sin `regla` usa una regla HISTORICA construida con sus propias filas de anexo («Regla anterior a la política de actas»). Nunca se recalcula con reglas nuevas |
| D-AE-11 | **Estados:** se conservan BORRADOR → SUSCRITA → VERIFICADA. **No se añade anulación:** N34 corrige un acta con los errores y deficiencias (art. 20), las observaciones (art. 22) y la verificación (art. 23), no anulándola. La regla solo es editable en BORRADOR |
| D-AE-12 | **Permisos:** `gobierno_actas:configure` (estándar) para crear y editar políticas, y `gobierno_actas:activate` (sensible, con MFA) para activarlas y cerrarlas. La separación entre quien configura y quien activa la dan los permisos; una regla «no la activa quien la creó» sería SoD y pertenece a CTL-01 (no se duplica) |
| D-AE-13 | **SoD:** la regla de verificación existente («ni quien suscribió, ni el saliente, ni el receptor») es una invariante del art. 23 y sigue en el servicio. No se duplica CTL-01 |
| D-AE-14 | **Ámbito (art. 6, auditado):** el `maxima_autoridad` de ORG-04 solo existe en la SUPLENCIA, de modo que el acta del **titular** de la máxima autoridad salía con ámbito UNIDAD y nunca podía recibir los supuestos declarados para la entidad. Ahora el acta es de la ENTIDAD si el saliente suple a la máxima autoridad o si ocupa el cargo cuyo **código** declara la política (`cargo_maxima_autoridad_codigo`; el código se mantiene entre ejercicios). KONTROL no lo infiere del nombre del cargo. La regla guarda el `ambito_motivo` |

## 5. Clasificación de reglas

| Regla | Clase |
|---|---|
| Arts. 11–17: anexos y sujetos; art. 9: testigos y auditor; arts. 4, 21 y 22: plazos; art. 19: constancia; art. 18: corte al cese | LEGAL_MANDATORY |
| Aislamiento por empresa; historia inmutable; acta suscrita congelada; saliente ejerce al corte; receptor distinto del saliente; una acta por ocupación | PLATFORM_INVARIANT |
| Vínculos declarados (arts. 12–17), requisitos adicionales, testigos en la entrega y plazos internos | INSTITUTIONAL_POLICY |
| Patrón de numeración, etiquetas y textos de ayuda | OPERATIONAL_CONFIGURATION |

## 6. Requisitos

| FR | Requisito |
|---|---|
| FR-AE-01 | Políticas por empresa con versiones, historia inmutable, nueva versión, activación con MFA y cierre |
| FR-AE-02 | Catálogo legal versionado de N34 (arts. 11–17, 9, 4, 21, 22) con fuente, artículo, sujeto, niveles y ámbitos |
| FR-AE-03 | Vínculos de los supuestos 12–17 a la entidad o a unidades, validados por nivel y ámbito |
| FR-AE-04 | Autoridad única: regla aplicada = catálogo legal + política, por ámbito, unidad y fecha de corte |
| FR-AE-05 | **P0:** A17 solo donde la política lo vincula. Un ente municipal sin vínculo no recibe A17; con vínculo, lo recibe y su ausencia bloquea la suscripción |
| FR-AE-06 | Requisitos del ente con tipo de evidencia y resolución acorde (documento del tipo exigido o texto) |
| FR-AE-07 | Testigos: piso legal más el mínimo de la política en la entrega |
| FR-AE-08 | Plazos legales e internos con estado calculado (D-AE-06) |
| FR-AE-09 | Numeración configurable con vista previa; formato por defecto OD-AE-04 |
| FR-AE-10 | Responsabilidad resuelta con la autoridad de ORG-04 y congelada |
| FR-AE-11 | Congelación de la regla y legado HISTORICO |
| FR-AE-12 | API, permisos, MFA, auditoría y aislamiento |
| FR-AE-13 | UI: pantallas de políticas, regla aplicada en la nueva acta y en la ficha, anexos condicionales, aviso OD-AE-02, plazos y responsabilidad |
| FR-AE-14 | Pruebas: PG, mutaciones M1–M10, Vitest, E2E (P0, A17 positivo, versión, ORG-04) y Axe en 1280, 390 y 320; humo UAT |
