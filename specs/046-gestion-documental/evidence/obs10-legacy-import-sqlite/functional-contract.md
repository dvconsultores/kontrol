# Contrato funcional y ciclo de vida
`PRECONDITION_STATE`: un `DocumentType` (con `scan_required=False`) y una `LegacyDocumentReference` sembrados directamente en
la sesión de la prueba. `DURABLE_BEFORE_HTTP`: **no aplica a la importación** (es una llamada de servicio en la misma sesión,
no HTTP); los únicos HTTP de los siete son los **ayudantes** `_company_id()` (login + `GET /organization/companies`) y la sesión
auxiliar de `_actor()`, que solo resuelven identificadores: nada en el contrato exige que ocurran con la sesión de escritura
abierta. `INTENTIONALLY_UNCOMMITTED_STATE`: ninguno (la prueba confirma al final con `db.commit()`). `API_OPERATION`: solo en
`test_lo_importado…` (`GET /descargar` tras `db.close()`, 409 `FILE_NOT_SCANNED`). `FINAL_STATE`: clasificación de la
referencia, documento/`StoredFile` cuando procede, fuente heredada intacta. `SQLITE_IN_SCOPE` = sí (módulo sin marcador, P21
no lo excluye: no ejercita el dialecto); `POSTGRES_IN_SCOPE` = sí (8/8 hoy). `ENGINE_AUTHORITY`: Spec 046 + P21; no hay
autoridad PG-only y no hace falta: con el ciclo de vida correcto SQLite cumple el contrato (Control C).
