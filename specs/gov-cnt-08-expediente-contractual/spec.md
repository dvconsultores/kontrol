# Spec · CNT-08 Expediente contractual completo (GOV-CNT-009)

**Iniciativa:** P2 · CNT-08 · 2026-11-15. **Entrada:** `14f1341`, cabeza `0118_gov_cnt02_modificaciones`. **Paralelo:** P1 construye CNT-03, sin solape.

## Objetivo

Quien administra un contrato, o un usuario de control fiscal, abre un contrato **formalizado** y obtiene un expediente único de solo lectura. En orden cronológico ve de dónde nació el contrato, quién lo adjudicó, qué se contrató, por cuánto, con qué presupuesto y garantías, qué modificaciones tuvo, quién lo supervisa, qué documentos y actos existen, quién hizo cada actuación y qué huellas demuestran la integridad. Además puede **exportarlo en un paquete verificable**.

CNT-08 es una **proyección**: no copia registros ni documentos. Cada autoridad sigue siendo dueña de sus datos. CNT-08 no duplica PROC-03; enlaza el expediente de contratación del que nació el contrato.

## Contratos

| Id | Contrato |
|---|---|
| C08-01 | **Raíz contractual.** El expediente pertenece a `company_id` y `contract_id`, con el `file_id` y el `decision_id` del contrato. Solo existe para contratos FORMALIZADO; un BORRADOR responde 409 `GOV_CONTRACT_DOSSIER_NOT_FORMALIZED`. No crea contratos |
| C08-02 | **Origen.** Expediente PROC-03 (número, objeto, tipo, modalidad, unidad y estado) y oferta adjudicada PROC-06, con enlace a la pantalla dueña |
| C08-03 | **Presupuesto.** Trazabilidad CDP (BUD-06) → asignación contractual (CNT-01 y CNT-02) → compromiso BUD-08 del mismo expediente, más el control de compromisos de CNT-01. No crea CDP ni compromisos y no cambia disponibilidades |
| C08-04 | **Contrato original.** Instrumento de CNT-01 (monto, plazo, documento, firmante y huella) presentado como ORIGINAL, nunca sustituido por la proyección |
| C08-05 | **Condiciones vigentes.** Las devuelve `service_contratos_modificaciones.historia`: CNT-08 no recalcula. La UI distingue condiciones originales y vigentes |
| C08-06 | **Garantías.** Instrumentos PROC-10 vinculados al contrato: tipo, referencia, emisor, monto, vigencia, documento, estado y eventos. No recalcula |
| C08-07 | **Supervisión.** `service_contratos_supervision.supervision` con el vigente, el programado y la historia; consulta del supervisor en una fecha mediante la ruta existente de CNT-04 |
| C08-08 | **Ejecución.** Contrato de consumo de CNT-03: mientras P1 no lo publique, la sección muestra `SOURCE_PROCESS_NOT_AVAILABLE` con un mensaje honesto. P2 no escribe hitos, entregables, valuaciones, recepciones ni cierre |
| C08-09 | **Índice documental.** Cada documento con tipo, título, proceso, referencia, versión, sha256, fecha, estado y enlace. La descarga pasa siempre por la autoridad documental o la de BUD. No se copian blobs |
| C08-10 | **Actos.** Actos DOC-02 vinculados (adjudicación, designaciones y folios de acto), con enlace a `/gobierno/actos/{id}`. No hay segundo modelo de actos |
| C08-11 | **Cronología.** Lista única con fecha jurídica o efectiva, fecha de registro, fecha del documento y fecha efectiva separadas, tipo, proceso, fuente, título, actor, autoridad, unidad, documentos y estado. Se ordena por fecha jurídica, después por registro. Admite filtros por proceso y fechas y está paginada |
| C08-12 | **Auditoría.** Eventos CTL-02 cuyo `entity_id` pertenece al expediente (expediente PROC-03, contrato, decisión, modificaciones, designaciones, garantías, CDP, compromisos y paquetes), paginados, con enlace a `/gobierno/auditoria?evento=`. Exige además `gobierno_auditoria:view`. No es una segunda bitácora |
| C08-13 | **Integridad.** Por documento: VERIFIED, MISSING, MISMATCH o NOT_APPLICABLE, verificando los bytes almacenados contra la huella registrada por la autoridad. «Existe el archivo» no equivale a «válido» |
| C08-14 | **Acceso de control fiscal.** Consultar exige `gobierno_contratos:view`; la auditoría, `gobierno_auditoria:view`; los paquetes, `gobierno_paquetes:view` y `generate` (con MFA); los documentos, el control documental. Desde el expediente no se puede editar nada |
| C08-15 | **Paquete.** ZIP determinista con `manifest.json`, `expediente.json`, `cronologia.csv`, `indice.csv`, `referencias.json`, `LEEME.txt`, `SHA256SUMS` y los documentos autorizados. Queda registrado e inmutable y reutiliza las primitivas de DOC-08 |
| C08-16 | **Verificación.** Una copia se verifica contra el registro de la empresa, no por su nombre, y da VALIDO, INVALIDO o INCOMPLETO (más VERSION_NO_SOPORTADA, como en DOC-08). Cada verificación queda registrada |
| C08-17 | **Snapshot.** En PostgreSQL el paquete se genera en una transacción REPEATABLE READ: no mezcla estados de antes y después de una formalización concurrente, y no bloquea el negocio |
| C08-18 | **Aislamiento.** Otra empresa recibe 404 en el expediente, la cronología, la auditoría, la integridad y los paquetes. La verificación de un paquete ajeno da PAQUETE_NO_REGISTRADO, sin revelar nada |
| C08-19 | **Listados acotados.** `limit` (máximo 100 en la lista y 200 en la cronología y la auditoría) y `offset`, con el total |
| C08-20 | **Navegación a la fuente.** Cada elemento lleva `enlace` a su pantalla dueña |
| C08-21 | **Fuentes futuras.** Interfaz extensible (`FUENTES_FUTURAS`) para CNT-03, CNT-05, CNT-06, CNT-07 y TRE-04, en estado SOURCE_PROCESS_NOT_AVAILABLE. Nunca se dice «no hubo» cuando el módulo no existe |
| C08-22 | **E2E y UAT.** Recorrido del sponsor completo (§52 del encargo), a 1280, 390 y 320 px, con Axe sin nuevos «serious» |

## Decisiones de diseño (no materiales: las más conservadoras)

- **D08-01:** solo los contratos FORMALIZADO tienen expediente contractual; un borrador no es instrumento.
- **D08-02:** el paquete usa tablas propias (`gov_contract_dossier_packages` y `_verifications`), inmutables. Reutiliza las primitivas de `service_paquetes`. La tabla de DOC-08 no cambia.
- **D08-03:** REPEATABLE READ de solo lectura al generar; en SQLite rige la serialización propia del motor.
- **D08-04:** los comprobantes BUD-06 y BUD-08 entran en el paquete solo con `gobierno_presupuesto:view`; si no, quedan EXCLUIDO por SIN_PERMISO. Los folios reservados de PROC-03 quedan EXCLUIDO por RESERVADO.
- **D08-05:** la cronología excluye las clases CONTRATO y GARANTIA de PROC-03, porque esos hechos se proyectan desde CNT-01/02/04 y PROC-10 (sin duplicados).
- **D08-06:** el «estado» de la lista es la **vigencia** derivada del plazo efectivo (POR_INICIAR, EN_PLAZO o VENCIDO). El estado de ejecución depende de CNT-03.
- **D08-07:** no hay permisos nuevos.
- **D08-08:** como en DOC-08, solo se audita generar, descargar y verificar paquetes; las consultas no.
- **D08-09 (decisión de la dueña, 2026-11-15, corregida tras medir):** se respeta el sello documental. La autoridad documental (`_get_document` y `puede_leer_archivo`, el mismo control de DOC-08) no entrega documentos sellados: ni descarga suelta ni paquete. CNT-08 no lo elude. El índice marca `sellado` y dice «Sellado · la autoridad documental no lo entrega (huella registrada)»; el manifiesto los declara EXCLUIDO con motivo SELLADO; su huella sigue siendo verificable. Deudas: OBS-DOC-SELLO-ENTREGA-01, porque la autoridad documental confunde el sello de inmutabilidad (CNT-01/02) con el de confidencialidad (PROC-06), y OBS-CNT01-DOC-SELLADO-01, porque «Ver documento» de la ficha de CNT-01 da 404.

## Fuera de alcance

CNT-03 (P1), CNT-05, CNT-06, CNT-07, TRE-04, pagos y contabilidad, el buscador global DOC-07 y la UAT remota (`BLOCKED_BY_INFRASTRUCTURE`).
