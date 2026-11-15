# CNT-04 · Fuentes leídas (2026-11-15)

## Normativa

N11 es el Decreto-Ley de Contrataciones Públicas: G.O. 6.154 Ext., 19-11-2014, Decreto 1.399. N12 es su Reglamento: G.O. 39.181, 19-05-2009, Decreto 6.708. Ambos están definidos en `requerimientos/gobierno/Biblioteca_Normativa_Oficial_KONTROL_Gobierno_v1.0.pdf`.

El texto se leyó de las mismas copias verificadas en PROC-02 a PROC-10 y en CNT-01 (sha256 del PDF de la LCP `a87a12d3…`). Están fuera del repositorio.

N20 son las Normas Generales de Control Interno (G.O. 40.851, 2016). La copia disponible es un escaneo sin capa de texto. Los extractos citados en `specs/gov-ctl-03-separacion-tecnica-funcional/FUENTES.md` (arts. 5, 6, 30, 32, 34.3 y 39) no tratan del supervisor del contrato.

| Regla | Fuente | Texto (literal, abreviado) | Consecuencia en CNT-04 |
|---|---|---|---|
| Quién designa | LCP art. 136 | «El contratante ejercerá el control y la fiscalización de los contratos que suscriba asignando el o los supervisores o ingenieros inspectores, de acuerdo a la naturaleza del contrato.» | Designa el contratante. OD-CNT04-02: el cargo emisor del acto debe tener APROBAR×CONTRATACIONES |
| Uno o varios | LCP art. 136 | «el o los supervisores» | Varios están permitidos, no exigidos. OD-CNT04-01: v1 tiene uno vigente por contrato y fecha; varios a la vez queda como OQ-CNT04-01 |
| Supervisión contratada | LCP art. 136, párr. 2 | «los contratantes deberán designar los responsables de verificar el cumplimiento de las obligaciones contraídas» | El designado siempre es un funcionario del ente, nunca un tercero |
| Bienes y servicios | LCP art. 137 | «Atribuciones del Responsable de la Supervisión…: 1. Verificar el inicio de la ejecución… 3. Informar por escrito el avance… 5. Elaborar y firmar los documentos de conformidad… 6. Cualquiera otra que sea atribuida por la máxima autoridad» | Las atribuciones las ejerce CNT-03 (consumidor), no CNT-04 |
| Obras | LCP art. 138 | «Atribuciones del Ingeniero Inspector de Obras» (15 numerales: acta de inicio, fiscalizar, valuaciones, actas) | Es el mismo rol, con otra denominación según la naturaleza. Etiqueta única «Supervisor / responsable del contrato» |
| Conformación de pagos | LCP arts. 141.3, 142 y 143; RLCP art. 177 | «Conformación, por parte del supervisor o ingeniero inspector…»; «debidamente conformadas por el supervisor o Ingeniero inspector» | CNT-03 necesita saber quién era el supervisor en una fecha: `supervisor_en(contrato, fecha)` |
| Sustitución o revocación | LCP y RLCP | Ningún artículo las regula | Solo hay sustitución (nueva designación con acto y motivo). REVOCADA no se construye (encargo §23) |
| Incompatibilidad firmante/supervisor | — | Ninguna fuente la establece | No se codifica. La SoD se configura en CTL-01 (encargo §27) |

## Requisito del sponsor

Fuente: `requerimientos/gobierno/Ingenieria_de_Requerimientos_KONTROL_Gobierno_v1.0.pdf`, §7.5.

> **GOV-CNT-004** (N11, N20; P0): «Registrar supervisor/responsable del contrato y sus cambios con acto de designacion.»

- Actor en la matriz: Máxima autoridad.
- IR §5: «Administrador/Supervisor de contrato — Controla hitos, entregables, valuaciones, recepciones y garantias» (es el actor de CNT-03).

## Autoridades del repositorio que se reutilizan

| Dato | Autoridad | Código |
|---|---|---|
| Contrato | CNT-01 | `GovernmentContract`, solo `estado=FORMALIZADO`. El guard PG impide cualquier UPDATE del contrato formalizado: CNT-04 lo bloquea con FOR UPDATE y nunca lo escribe |
| Funcionario | ORG-04 | `GovernmentOfficial` (estado ACTIVO) |
| Ocupación vigente | ORG-04 | `service_ocupacion.ocupaciones_de_funcionario(db, ctx, official_id, fecha)`, con situacion VIGENTE y figura de los grupos TITULARIDAD o TEMPORAL (no DELEGACION) |
| Cargo y unidad | ORG-03 y ORG-02 | `GovernmentPosition` (code, name, unit_id) y `GovernmentUnit` (name) |
| Acto de designación | DOC-02 | `GovernmentAct`: status EFICAZ con `fecha_eficacia ≤ desde`, mismo ente y documento del acto obligatorio (CHECK `emitido_documentado`) |
| Autoridad que designa | ORG-03/04/06/07 | `_autoridad_valida(db, company, acto.cargo_id, acto.fecha, "APROBAR", "CONTRATACIONES")` y `exigir_autoridad_funcional(db, ctx, acto.cargo_id, "APROBAR", "CONTRATACIONES")` |
| SoD | CTL-01 | `CATALOGO_SOD["PROC-03"]` y `evaluar_antes_de_actuar` |
| Cronología | PROC-03 | `_evento(…, "CONTRATO", …)`. La clase ya existe, así que no cambia el CHECK |
| Auditoría | CTL-02 | Eventos sobre `GovernmentProcurementFile`, igual que CNT-01 |
| ORG-05 | — | OQ-ORG05-03 sigue abierta. CNT-04 solo deja CONTRACT_RESOURCE_NOW_EXISTS=1 |
