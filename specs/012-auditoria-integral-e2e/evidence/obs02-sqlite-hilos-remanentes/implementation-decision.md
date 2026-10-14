# Decisión de implementación (etapa 2) · solo arnés · producto 0

| Fichero | Cambio |
|---|---|
| `tests/test_uom_conversion.py` | (1) fixture de módulo `_app_client` sobre `with motor_para_hilos("uom-conversion") as engine:` (mismo cuerpo, sangrado; import `motor_para_hilos` en vez de `make_engine`); (2) `test_concurrencia_una_sola_version_abierta` recoge las excepciones de hilo (`errores`) y, **antes** de la aserción funcional intacta `len(abiertas) == 1`, exige `errores == []` y `len(results) == 2 and set(results) <= {200, 409} and 200 in results` (FR-O2-024/025: ningún hilo muerto ni vector incompleto pasa por PASS; no se debilita nada: se añade); (3) `test_el_historico_no_cambia_al_cambiar_el_factor` resuelve la empresa por la API antes de abrir su sesión de escritura (ciclo de vida; sin cambio de lo que afirma) |
| `tests/test_uom_concurrencia_hilos.py` (nuevo) | O2-02 (I1 forzada en los dos motores: `[200, 409]`, `PRESENTATION_VERSION_OVERLAP`, una abierta / dos en total, dos conexiones DBAPI, 0 excepciones), O2-11 (excepciones de hilo visibles), O2-04 (contrato estático del módulo objetivo) |
| `motor_para_hilos` | sin cambio |
| producto, migraciones, esquema, `test_documents_security.py` | sin cambio |

Por qué el vector `{200, 409}` con «200 in results» y no `[200, 409]` exacto: sin forzar el entrelazado, las dos peticiones
pueden serializarse y crear dos versiones consecutivas (`[200, 200]`, legítimo: AC-011-12 solo exige una abierta); el
`[200, 409]` exacto se exige donde se fuerza la lectura simultánea (O2-02).
