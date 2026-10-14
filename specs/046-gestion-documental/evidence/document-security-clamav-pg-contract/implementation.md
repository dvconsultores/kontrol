# Implementación (etapa 2, solo OBS-08; producto 0; analizador sin tocar)

| Fichero | Cambio |
|---|---|
| `tests/test_documents_security.py` | `import os`; `PG = os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql")` y `solo_postgresql = pytest.mark.skipif(not PG, reason="la carrera de versiones se certifica sobre PostgreSQL (FR-046-115, conc-046; P21)")` con comentario de autoridad; el marcador en **siete** pruebas: las seis de OBS-08 (`test_dos_subidas…[0..2]`, `test_la_primera_version…`, `test_la_peticion_http…`, `test_tres_subidas…`, `test_la_misma_clave_en_carrera…`, `test_otro_tenant…`) y `test_subidas_a_documentos_distintos_no_se_esperan` (descubierta por el contrato: depende del bloqueo de fila). Ninguna aserción cambia; ninguna otra prueba se marca |
| `tests/test_documents_carreras_contrato.py` (nuevo) | DOCENV-05 conjunto exacto de marcadas; DOCENV-12 mecanismos de carrera solo en las marcadas (por AST), marcador dependiente del motor y con autoridad en su razón, omisión efectiva en SQLite con razón; DOCENV-13 ≥ 25 pruebas no concurrentes sin `skipif`; DOCENV-14 sin `set_scanner`/`DisabledScanner`/variables del analizador; DOCENV-15 ningún `in (200, 422)` |
| Sin cambio | producto, `scanning.py`, fixture del módulo, `tests/concurrency.py`, E2E, runner, Docker/compose, migraciones, esquema |

`COMMENT`/autoridad citada en el propio marcador. El analizador no se instala, no se simula, no se apaga.
