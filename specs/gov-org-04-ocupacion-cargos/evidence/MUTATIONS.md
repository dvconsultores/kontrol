# GOV-ORG-04 · mutaciones (T018, herramienta de Claude `mutar2.py`)

**Método:** uno o varios SEARCH únicos por mutante; purga de `__pycache__` y `PYTHONDONTWRITEBYTECODE=1`; restauración verificada por sha256; pruebas de `tests/test_gov_org04_*.py` en PostgreSQL con `-x`. Un fallo de importación o arranque no cuenta como muerte.

## Resultado final: 19 mutantes · 19 muertos · 0 equivalentes · 0 supervivientes

Primera ronda: 16 muertos y 3 supervivientes (M4, M10b, M15). Los tres eran pruebas ausentes, no defectos de producto. Se añadió `tests/test_gov_org04_refuerzo.py` (T018r) y se repitieron contra el producto intacto.

M3 quita a la vez la regla de servicio y la exclusión. Quitar solo la regla de servicio deja la exclusión de base de datos actuando: es defensa en profundidad, y por eso M3b prueba la exclusión por separado.

| ID | Mutación | Resultado | Prueba que falla |
|---|---|---|---|
| M1 | quitar el control de ente al leer la asignación | KILLED | `` |
| M1b | quitar el control de ente del cargo | KILLED | `` |
| M2 | aceptar ente enviado por el cliente | KILLED | `` |
| M3 | permitir solape: sin regla de servicio ni exclusión | KILLED | `` |
| M3b | quitar solo la exclusión de base de datos | KILLED | `` |
| M4 | ignorar la vigencia inicial | KILLED (superviviente en la primera ronda) | `` |
| M5 | ignorar el acto soporte | KILLED | `` |
| M6 | permitir que quien registra active | KILLED | `` |
| M7 | no registrar historia | KILLED | `` |
| M8 | perder el actor de la auditoría | KILLED | `` |
| M9 | perder antes y después | KILLED | `` |
| M10 | delegar competencia que no corresponde a la figura | KILLED | `` |
| M10b | delegar sin declarar que es delegable | KILLED (superviviente en la primera ronda) | `` |
| M11 | ignorar la revocación en la situación | KILLED | `` |
| M12 | aceptar acto no eficaz | KILLED | `` |
| M13 | ignorar cargo cerrado | KILLED | `` |
| M14 | saltar la autoridad emisora | KILLED | `` |
| M15 | romper aislamiento del listado | KILLED (superviviente en la primera ronda) | `` |
| M15b | aislar mal el funcionario | KILLED | `` |
