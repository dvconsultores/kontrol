# ORG-04 · Ocupación de cargos

## 1. Lo que podrá hacer el usuario

Desde **Gobierno › Ocupación de cargos** el responsable de organización podrá registrar a los funcionarios del ente y dejar constancia de quién ejerce cada cargo: titular, encargado, suplente, en comisión de servicio o por delegación, con su acto, su vigencia y su fundamento.

Control Interno podrá elegir una fecha y ver, por cargo, quién era titular, quién lo ejercía, bajo qué figura, por qué acto y con qué autoridad.

## 2. Fuentes

| Tipo | Referencia | Regla |
|---|---|---|
| Requisito | GOV-ORG-004 (P0; N02, N25, N23) | Versionar delegaciones, suplencias, encargadurías y designaciones con acto soporte, vigencia y autoridad emisora |
| Requisito | GOV-ORG-009 (P1; N02, N25, N37) | Catálogo de actos que habilitan autoridad |
| Norma | N24 LOPPM, G.O. 6.015 Ext. | Art. 54 instrumentos; art. 78 estatuto; art. 87 suplencia; art. 88.7 personal |
| Norma | N02 LOAP, G.O. 6.147 Ext. | Art. 34 delegación de atribuciones y firma; art. 35 límites; art. 37 efectos; art. 40 forma y eficacia; art. 41 avocación |
| Norma | N32 LEFP, G.O. 37.522 | Arts. 1, 20, 71, 72: comisión de servicio, un año como máximo |
| Local | Gaceta Municipal 512 Ext., art. 120 | Acto delegatorio |

Copias en `requerimientos/gobierno/normativa-n37-naguanagua/`. Inventario y documentos locales pendientes en `specs/gov-0-06-identidad-usuarios/evidence/`.

## 3. Decisiones de diseño

Son de Claude, por norma y arquitectura. Ninguna requiere a la dueña.

| Id | Decisión |
|---|---|
| OD-ORG04-01 | Las **figuras** salen de la norma nacional: TITULAR, ENCARGADURIA, SUPLENCIA, COMISION_SERVICIO, DELEGACION_ATRIBUCIONES, DELEGACION_FIRMA |
| OD-ORG04-02 | La identidad institucional es `GovernmentOfficial`, propia del ente: nombre y documento. ORG-06 enlazará la cuenta con ella. No es usuario ni ficha de empleado |
| OD-ORG04-03 | **PII mínima:** el documento se guarda para evitar duplicados y **nunca sale completo por la API**; se muestra enmascarado |
| OD-ORG04-04 | El acto es de DOC-02 y debe estar **EFICAZ** con eficacia no posterior al inicio. Sin segundo registro de actos ni de PDF |
| OD-ORG04-05 | **Publicación:** solo las delegaciones exigen medio GACETA (LOAP art. 40). Las demás figuras dependen de la eficacia que DOC-02 ya controla |
| OD-ORG04-06 | **Autoridad emisora:** en delegación y avocación, el cargo del acto es el delegante (art. 34, 41). En TITULAR, ENCARGADURIA y COMISION_SERVICIO, un cargo distinto del afectado. En SUPLENCIA puede ser el mismo cargo, porque el titular designa a quien lo suple (LOPPM art. 87) |
| OD-ORG04-07 | **Ocupación:** a una fecha, ejerce quien tenga una figura temporal vigente; si no, el titular vigente. El titular suplido sigue siendo titular, pero no ejerce |
| OD-ORG04-08 | **Maker-checker:** quien registra no activa. Evita la autoasignación sin vínculo de usuario; ORG-06 lo reforzará por identidad |
| OD-ORG04-09 | ENCARGADURIA cubre también la designación temporal. Ninguna norma hallada las distingue; el acto conserva su denominación. Va al paquete profesional, sin efecto en el modelo |
| OD-ORG04-10 | Se **incluye** COMISION_SERVICIO: encomienda el ejercicio de otro cargo (LEFP art. 71) y por tanto decide quién ejerce |
| OD-ORG04-11 | Art. 87 solo se aplica si se marca «suple a la máxima autoridad» y el ente es MUNICIPAL: más de 15 días exige referencia de autorización del Concejo; más de 90 se rechaza |
| OD-ORG04-12 | Cargos por ejercicio: la vigencia termina dentro del ejercicio del cargo. Al cambiar de ejercicio se registra de nuevo sobre el cargo del año |
| OD-ORG04-13 | Art. 35.3 lo aplica el sistema: no delega quien firmó el acto por delegación, y solo se delegan competencias propias del cargo. Art. 35.1, 2 y 4 no tienen dato verificable: quien registra declara que no son indelegables, y queda constancia |
| OD-ORG04-14 | ORG-07 no se modifica. La autoridad en una fecha se responde en esta pantalla |

**Efecto de los documentos locales:** `LOCAL_DOCUMENTS_DO_NOT_CHANGE_MODEL = 1`. Figuras, formas y límites vienen de leyes nacionales; un estatuto local podría añadir plazos, pero no suprimir figuras de ley. Si añadiera una figura nueva, sería un delta acotado.

## 4. Figuras

| Figura | Grupo | `hasta` | `cargo_origen` | Base |
|---|---|---|---|---|
| TITULAR | TITULARIDAD | opcional | no | LOPPM 88.7 |
| ENCARGADURIA | TEMPORAL | opcional | opcional | Práctica administrativa; LOPPM 87 usa «encargado» |
| SUPLENCIA | TEMPORAL | obligatoria | obligatorio | LOPPM 87 |
| COMISION_SERVICIO | TEMPORAL | obligatoria, máx. 1 año | obligatorio | LEFP 71, 72 |
| DELEGACION_ATRIBUCIONES | DELEGACION | opcional | obligatorio | LOAP 34, 35, 37, 40 |
| DELEGACION_FIRMA | DELEGACION | opcional | obligatorio | LOAP 34, 35, 40 |

## 5. Estados

`BORRADOR → ACTIVO → REVOCADO | FINALIZADO`; `BORRADOR → DESCARTADO`. El vencimiento se deriva de `hasta`, sin cambio de estado.

**Situación a una fecha:** BORRADOR, DESCARTADA, FUTURA, VIGENTE, VENCIDA, REVOCADA, FINALIZADA o SIN_EFECTO. SIN_EFECTO: acto NULO, o REVOCADO con revocación eficaz en o antes de la fecha. Una asignación revocada sigue siendo VIGENTE para fechas anteriores a su fin: la historia no se reescribe.

## 6. Reglas al activar

1. Permiso, ente, MFA.
2. Quien activa no es quien registró (403).
3. Guarda SoD `ORG04_ACTIVAR`.
4. Funcionario ACTIVO; cargo y estructura VIGENTE; `desde` dentro del cargo y del ejercicio.
5. Acto del ente, EFICAZ, eficaz en o antes de `desde`, con emisor válido (OD-ORG04-06).
6. Reglas de la figura: sección 4 y OD-ORG04-11, 13. SUPLENCIA exige titular activo a `desde`. COMISION y delegación exigen que el funcionario ejerza `cargo_origen`.
7. Delegación: cargo delegado bajo la unidad del delegante o en ella; acto en GACETA con titularidad TITULAR; competencias propias del cargo en vigor; FIRMA solo con acción FIRMAR y ATRIBUCIONES sin ella; rendición obligatoria; declaración marcada.
8. Sin solape: un TITULAR y un TEMPORAL por cargo a la vez; una delegación por cargo y funcionario.

## 7. Requisitos funcionales

- **FR-001** Alta, edición y consulta de funcionarios, con historia y documento enmascarado.
- **FR-002** Registrar, editar y descartar borradores de asignación.
- **FR-003** Activar con las reglas de la sección 6.
- **FR-004** Revocar con acto eficaz; finalizar con fecha y motivo; avocar con acto y asunto.
- **FR-005** Consultar por cargo y fecha: titular, quien ejerce, figura, acto, emisor, delegaciones y competencias.
- **FR-006** Consultar asignaciones con filtros, detalle con historia y exportación CSV auditada.
- **FR-007** Catálogo de figuras con base legal y de instrumentos que habilitan autoridad (GOV-ORG-009), derivado de los tipos de acto de DOC-02.
- **FR-008** Toda mutación audita con anterior y nuevo; historia append-only en base de datos.
- **FR-009** La base impide solapes activos en PostgreSQL y edición de lo activado.
- **FR-010** Otro ente responde 404; el ente nunca viene del cliente.
- **FR-011** Administrador técnico sin capacidad funcional.

## 8. Fuera de alcance

Vínculo usuario-identidad (ORG-06), responsables por objeto (ORG-05), Atenea, cambios en ORG-03 y ORG-07, ficha de personal.

## 9. Criterios de éxito

- **SC-001** Desde el menú se responde quién ejercía un cargo en cualquier fecha, con su acto.
- **SC-002** Ninguna asignación da autoridad sin acto eficaz.
- **SC-003** Dos asignaciones concurrentes incompatibles: una falla.
- **SC-004** 15 mutantes exigidos, 0 sobreviven por comportamiento.
