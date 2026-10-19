# Orquestación Claude + DeepSeek — huella de las bases protegidas

Regla permanente 1:
- **Claude:** fijó el invariante desde las fuentes, reprodujo, midió la semántica, diseñó el contrato y el algoritmo,
  escribió los briefs con fragmentos literales e imports reales, auditó, aplicó tal cual y certificó.
- **DeepSeek:** escribió todo el código QA y todas las pruebas.
- Claude no escribió código QA ni pruebas.

| Llamada | Tarea | Modelo | Tokens (entrada/salida) | Coste | Auditoría |
|---|---|---|---|---|---|
| 1 | H02a `qa/e2e_base.py::huella` | deepseek-v4-pro | 2065/1163 | $0,001800 | AUDIT_PASS; aplicado tal cual |
| 2 | H02b `tests/test_e2e_base_ciclo.py` (23 adaptada, 24–31 nuevas) | deepseek-v4-pro | 3422/2774 | $0,003792 | AUDIT_PASS; aplicado tal cual |

**Total:** 2 llamadas, 5487/3937 tokens, **$0,005592**. Reintentos 0, rechazos 0.

**Observación cosmética aceptada (H02b):** una variable local `n` sombrea el alias del módulo `e2e_nombres as n`
dentro de `_esperar_sin_clientes`, que no lo usa. No cambia el comportamiento.

## Egress
Por llamada: EGRESS_CHECK_COMPLETE_BEFORE_CALL = 1, LOCAL_PATHS_SANITIZED = 1, SECRET_EXPOSURE = 0.

- Se buscaron nombre de usuario, `/home`, puerto y URL de PostgreSQL de QA, y contraseñas: 0 coincidencias en los dos
  briefs.
- ENV_FILES=0 SECRETS=0 PROD_URLS=0 TOKENS=0 PRIVATE_KEYS=0 REAL_PII=0 REAL_PAYROLL=0 BANK_DATA=0.

## Herramientas mecánicas de Claude
El reinicio del equipo vació el scratchpad, así que Claude rehízo, fuera del repositorio, el extractor de la respuesta
cruda y el aplicador SEARCH/REPLACE de coincidencia única.

- El aplicador falló una vez en seco con H02a porque el puente devuelve la respuesta envuelta en JSON. Se corrigió el
  extractor y no se tocó el parche.
- También es de Claude el guion de mutaciones local; tuvo un defecto de selección (`-k` con corchetes) que se corrigió
  y se repitió.
