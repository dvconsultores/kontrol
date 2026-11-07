# GOV-ORG-04 · RED

Las pruebas de reglas y seguridad se escribieron contra la API ausente: la primera corrida de `tests/test_gov_org04_*.py` en PostgreSQL devolvió 404 en cada ruta de `/gobierno/ocupacion`, antes de implementar el servicio. Ese 404 es la evidencia de RED; no se conservó como aserción. El encargo que pedía fijarlo en las pruebas fue un error de Claude y se retiró (`ATTEMPT_LOG.md`).

Los mutantes M1 a M15 demuestran después que las pruebas distinguen el comportamiento: `MUTATIONS.md`.
