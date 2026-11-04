# GOV-CTL-01 · mutaciones de negocio (T012, herramienta de Claude `mutar_ctl04.py`)

**Método**
- Un SEARCH único por mutante, sustituido por su REPLACE.
- Purga de `__pycache__` y `PYTHONDONTWRITEBYTECODE=1`.
- Restauración verificada por sha256 tras cada mutante.

**Órdenes**
- Backend: las 4 suites `tests/test_gov_ctl01_*.py` sobre PostgreSQL (22 pruebas).
- Interfaz: `vitest run` del fichero de pruebas del componente mutado.

## Resultado final: 19 mutantes · 19 muertos · 0 equivalentes · 0 supervivientes

| ID | Mutación (garantía de negocio rota) | Resultado | Pruebas que fallan |
|---|---|---|---|
| SOD-M01 | guarda: nunca evalúa | KILLED | 5 (SG-01, SG-02, SG-06, SD-01, SC-02) |
| SOD-M02 | guarda: sentido invertido | KILLED | 5 |
| SOD-M03 | guarda: ignora la empresa de la regla | KILLED | 1 (SG-05) |
| SOD-M04 | guarda: ignora el objeto | KILLED | 2 (SG-06 y otra) |
| SOD-M05 | guarda: ignora el inicio de vigencia | KILLED | 1 (SG-03) |
| SOD-M06 | guarda: ignora el actor (bloquea a cualquiera) | KILLED | 6 |
| SOD-M07 | guarda: no audita el intento bloqueado | KILLED | 2 (SG-01, SD-01) |
| SOD-M08 | guarda: aplica reglas en borrador o cerradas | KILLED | 5 |
| SOD-M09 | guarda: ignora el sentido bidireccional | KILLED | 1 (SG-02) |
| SOD-M10 | integración: CTL-06 recomendar sin guarda | KILLED | 3 |
| SOD-M11 | integración: DOC-02 editar sin guarda | KILLED | 1 (SD-01) |
| SOD-M12 | regla: acepta B creadora en un solo sentido | KILLED | 1 (CR-04) |
| SOD-M13 | regla: no detecta duplicadas | KILLED | 1 (CR-07) |
| SOD-M14 | regla: activa en cualquier estado | KILLED | 1 (CR-06) |
| SOD-M15 | interfaz: la alerta acepta cualquier 409 | KILLED | CSD-01 |
| SOD-M16 | interfaz: «Nueva regla» sin `gobierno_sod:manage` | KILLED | RSP-02 |
| SOD-M17 | interfaz: la acción B ofrece la creadora en un solo sentido | KILLED | NRS-02 |
| SOD-M18 | interfaz: «Activar regla» sin `gobierno_sod:activate` | KILLED | RSD-02 |
| SOD-M19 | interfaz: los conflictos ignoran la regla de la URL | KILLED | CSP-02 |

## Incidencia de la primera tanda (error de Claude)
- Los 5 mutantes de interfaz salieron INVALID: la ruta del fichero de prueba llevaba el prefijo `resources/frontend/` y vitest se ejecuta desde ese directorio, así que no encontraba pruebas.
- Se repitieron con la ruta relativa correcta: los 5 mueren.

**Integración de la alerta en las fichas de acto y de hallazgo:** no tiene prueba vitest propia; la cubren las E2E SOD-E2E-01 (hallazgo) y SOD-E2E-02 (acto) en los tres navegadores.

**Estado final:** árbol verificado sin restos de mutantes (sha256).
