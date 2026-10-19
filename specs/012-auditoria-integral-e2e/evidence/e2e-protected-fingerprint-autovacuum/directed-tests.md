# Pruebas dirigidas y mutaciones — huella

**Contrato** (delta §4): por base, `{"oid", "sesiones", "clientes"}` o `None`.
- `clientes` es `[pid, backend_start, state_change]` de cada `client backend`.
- Falla cerrada si se mide la base del observador.
- Ignora `tup_*`, `xact_*` y la actividad que no es `client backend`.

| Prueba | Caso del encargo | Qué demuestra |
|---|---|---|
| 23 (adaptada) | T1 | sin actividad: dos lecturas iguales, `clientes == []`, 0 conexiones, base inexistente = `None` |
| 24 | T2/T8 | autovacuum/autoanalyze **real** sobre una base con 5000 filas: las tuplas cambian sin ningún cliente y la huella **no** |
| 25 | T3/T4/T10 | una conexión abierta con SELECT cambia la huella, visible en `clientes` aunque su estadística aún no se haya volcado |
| 26 | T3 | una conexión ya cerrada y desaparecida cambia la huella por `sesiones` |
| 27 ×3 | T5/T6/T7 | INSERT, UPDATE y DELETE desde una conexión nueva cambian la huella |
| 28 | T9 / sesión preexistente | una sesión abierta antes que escribe cambia la huella **con las mismas sesiones**: la delata `state_change` |
| 29 | DDL | recrear la base con el mismo nombre cambia el `oid` |
| 30 | T9 / observador | medir la base del observador falla cerrada (`CicloDeBaseRoto`) |
| 31 | contrato vigente | una base inexistente vale `None` antes y después |

Esperas: solo sondeos con condición, plazo y diagnóstico.
- La 24 espera al autovacuum, con plazo de 240 s.
- `_esperar_sin_clientes` espera a que las conexiones lleguen a 0, con plazo de 30 s.
- No hay pausas de estabilización ni `skip`. El módulo era ya solo de PostgreSQL por su `pytestmark`.

## Resultados (PostgreSQL de QA)

| Ejecución | Resultado |
|---|---|
| Huella (23–31, 11 casos) | 11/0/0 |
| Huella en orden inverso | 11/0/0 |
| Módulo `test_e2e_base_ciclo.py` completo | 33/0/0 (la 24 tardó 30,3 s) |
| `test_e2e_corrida.py` completo, incluida `test_e2ecorrida_01` | 19/0/0 |
| **Rojo contra el `qa/e2e_base.py` de HEAD** | **7 fallos** (23, 24, 25, 26, 28, 29, 30) / 4 pasan (27 ×3, 31) |

- **Por qué falla la 24 contra HEAD:** es la razón exacta del falso positivo.
  `{'escrituras': 5040, 'sesiones': 1} != {'escrituras': 5038, 'sesiones': 1}`. Autovacuum movió las tuplas, las
  sesiones no cambiaron y no había ningún cliente.
- **Por qué pasan con HEAD la 27 (×3) y la 31:** la escritura desde una conexión nueva ya movía `sesiones` en la huella
  antigua. Que también caen si se debilita el detector lo demuestran M02 y M06.
- ruff limpio en las dos rutas. mypy limpio en `qa/e2e_base.py` y `qa/e2e_corrida.py`, cuya anotación es compatible sin
  cambio.
- Residuos: 0 bases de corrida.

## Mutaciones (`mutations.json`)
**11 significativas: KILLED 11, SURVIVED 0, EQUIVALENT 0, RESTORED 11/11.** M12 no aplica.

| ID | Mutación | La mata |
|---|---|---|
| M01 | volver a `tup_*` de toda la base | 24 |
| M02 | sesiones constantes (ignorar la conexión nueva) | 26 |
| M03 | lista de clientes vacía | 25 |
| M04 | sin fail-closed del observador | 30 |
| M05 | contar `xact_commit` (el mantenimiento como violación) | 24 |
| M06 | quitar la señal de sesiones | 23 |
| M07 | quitar `state_change` | 28 |
| M08 | invertir el filtro del observador | 25 |
| M09 | contar clientes en vez de listarlos | 23 |
| M10 | fail-open: toda base vale `None` | 23 |
| M11 | perder la detección de recreación (`oid`) | 29 |
| M12 | omitir la espera de propagación | NO APLICABLE: no hay espera; la propagación se resuelve por construcción |
