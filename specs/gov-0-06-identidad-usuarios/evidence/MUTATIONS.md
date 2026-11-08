# GOV-0-06 · mutaciones (T015, herramienta de Claude `mutar2.py`)

**Método:** cada mutante aplica uno o varios reemplazos exactos sobre anclas elegidas por Claude y verificadas como únicas; DeepSeek redactó cada mutación. Purga de `__pycache__`, `PYTHONDONTWRITEBYTECODE=1`, restauración verificada por sha256; pruebas `tests/test_gov_org06_*.py` y `tests/test_mfa_policy.py` en PostgreSQL con `-x`. Un fallo de importación o arranque no cuenta como muerte.

## Resultado final: 20 mutantes · 19 muertos · 1 equivalente · 0 supervivientes

Primera ronda: 15 muertos y 5 supervivientes (M1, M2, M6, M8, M10). M1, M2, M6 y M10 eran pruebas ausentes, no defectos de producto: se añadió `tests/test_gov_org06_refuerzo.py` (T015r: escritura desde otro ente, cuenta sin acceso al ente, autoactivación del registrador, ocupación revocada fuera del contexto) y se repitieron contra el producto intacto.

**M8 equivalente (justificación causal):** `ocupaciones_de_funcionario` filtra en SQL `GovernmentAssignment.desde <= fecha`, y `situacion_en` solo devuelve FUTURA cuando `fecha < desde`; ninguna fila que llegue al filtro de situación puede ser FUTURA, así que aceptar FUTURA no cambia el resultado. La ocupación futura se prueba en N02 y en la E2E (IDE-E2E-02 b).

M11 quita a la vez la regla de servicio y las dos exclusiones de base de datos (defensa en profundidad). M20 quita el bloqueo serializador del ente en activar y en clasificar.

| ID | Mutación | Resultado | Ronda |
|---|---|---|---|
| M1 | quitar el control de ente al leer el vínculo para escribir | KILLED | 2 (superviviente en la 1) |
| M2 | aceptar una cuenta sin acceso al ente | KILLED | 2 (superviviente en la 1) |
| M3 | aceptar alcance o claves extra enviados por el cliente | KILLED | 1 |
| M4 | el vínculo da autoridad sin ocupación | KILLED | 1 |
| M5 | administrador técnico sin vínculo pasa la guarda | KILLED | 1 |
| M6 | quitar el maker-checker por actor efectivo del vínculo | KILLED | 2 (superviviente en la 1) |
| M7 | maker-checker y SoD solo por user_id | KILLED | 1 |
| M8 | ignorar el inicio de la ocupación (futura cuenta) | EQUIVALENTE | 1 y 2 |
| M9 | ignorar el fin de la ocupación (vencida o finalizada cuenta) | KILLED | 1 |
| M10 | ignorar la revocación de ORG-04 | KILLED | 2 (superviviente en la 1) |
| M11 | permitir vínculos duplicados: sin regla de servicio ni exclusión | KILLED | 1 |
| M12 | permitir borrar la historia del vínculo | KILLED | 1 |
| M13 | quitar la separación de funciones por categorías | KILLED | 1 |
| M14 | permitir autoasignación del vínculo | KILLED | 1 |
| M15 | perder el actor institucional en la auditoría | KILLED | 1 |
| M16 | perder el antes en la auditoría del vínculo | KILLED | 1 |
| M17 | aceptar un funcionario de otro ente | KILLED | 1 |
| M18 | autoridad congelada en el pasado (caché) en la guarda | KILLED | 1 |
| M19 | saltar MFA en la activación de vínculos y política | KILLED | 1 |
| M20 | conflicto concurrente: sin bloqueo serializador del ente | KILLED | 1 |
