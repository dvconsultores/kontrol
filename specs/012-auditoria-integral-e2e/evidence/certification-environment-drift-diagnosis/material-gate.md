# Material gate — diagnóstico de la deriva del entorno de certificación

| Indicador | Valor |
|---|---|
| PRODUCTION_ENVIRONMENT_DEFINED | 1 (`production-environment.json`) |
| PRODUCTION_INSTALL_SEMANTICS_REPRODUCED | 1, con aproximación documentada (mismo pip, orden y fichero; CPython 3.13.15 de uv frente al de la imagen oficial; transitivas de un build de hoy) |
| V1_CREATED · V1_PIP_CHECK · V1_SMOKE_PASS | 1 · PASS · 1 |
| V2_CREATED · V2_PIP_CHECK · V2_SMOKE_PASS | 1 · PASS · 1 |
| DRIFT_FAILURES_TOTAL | 4 pruebas distintas en V2 (OAS-14, ACS-08, U03, U04) + 31 en V1 |
| DRIFT_PRODUCT_INCOMPATIBILITIES | **0** funcionales |
| DRIFT_TEST_INCOMPATIBILITIES | 1 (OAS-14) |
| PYTHON_INTERPRETER_INCOMPATIBILITIES | 1 (ACS-08, de la prueba) |
| PACKAGE_VERSION_INCOMPATIBILITIES | 1 causa (U03 y U04): FastAPI 0.141 cierra `get_db` después de enviar la respuesta. Cambio semántico en la ruta del producto |
| LIBMAGIC_FAILURES | 31 (V1) |
| VENV_PATH_FAILURES | 0; 10 ficheros de migraciones corrieron con el alembic de V0 (hueco de paridad) |
| LOCK_DRIFT_COUNT | 20 (+2 transitivas fuera del lock, +1 del lock no instalada) |
| INSTALLER_DRIFT_COUNT | 0 (se reprodujo el instalador de la imagen: pip) |
| OPENAPI_CONTRACT_DRIFT | 0 (4 diferencias generadas por el framework, no contractuales) |
| E2E_V2_EXECUTED · E2E_V2_RESULT | 1 · 284/0/0 |
| OWNER_DECISION_REQUIRED | 0 (OD-CERT-01 y OD-CERT-02 ratificadas) |
| MATERIAL_OQ | 0 para el diagnóstico. Una decisión técnica abierta para el ciclo siguiente: semántica de cierre de `get_db` |
| UNKNOWN | 0 |

**Resultado: CASO D, mixto.**
- No hay incompatibilidad funcional del producto.
- Hay dos incompatibilidades de prueba (OAS-14, ACS-08) y un cambio semántico del framework en la ruta del producto
  (`get_db` después de la respuesta).
- La deuda independiente de libmagic queda reproducida.
- SQLite y PostgreSQL no están en verde con V2, así que no se cumple la puerta del CASO A:
  DEPLOYMENT_PARITY_PRODUCT_COMPATIBLE no se declara y RELEASE_DEPLOYMENT_PARITY_CERTIFIED = 0.
