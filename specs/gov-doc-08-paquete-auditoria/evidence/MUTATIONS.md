# GOV-DOC-08 · mutaciones de negocio (T011, herramienta de Claude `mutar_ctl04.py`)

**Método**
- Un SEARCH único por mutante, sustituido por su REPLACE.
- Purga de `__pycache__` y `PYTHONDONTWRITEBYTECODE=1`.
- Restauración verificada por sha256 tras cada mutante.

**Órdenes**
- Backend: las 5 suites `tests/test_gov_doc08_*.py` sobre PostgreSQL.
- Interfaz: `vitest run` del fichero de pruebas del componente mutado.

## Resultado final: 17 mutantes · 17 muertos · 0 equivalentes · 0 supervivientes

| ID | Mutación (garantía de negocio rota) | Resultado | Prueba que lo mata |
|---|---|---|---|
| DOC8-M01 | alcance: se acepta la muestra de otra empresa | KILLED | DA-03 |
| DOC8-M02 | inclusión: se incluye un documento sin permiso | KILLED | DA-01 |
| DOC8-M03 | huella: los ficheros JSON y de texto declaran una huella falsa | KILLED | DC-03 (y 3 más) |
| DOC8-M04 | verificación: se ignora la huella del manifiesto | KILLED | DV-07 |
| DOC8-M05 | descarga: no se comprueba la huella del almacenamiento | KILLED | DA-04 |
| DOC8-M06 | descarga: no se exige permiso documental | KILLED | DA-01 |
| DOC8-M07 | verificación: se acepta un archivo alterado | KILLED | DV-03, DV-04 |
| DOC8-M08 | referencias cruzadas: se pierden las referencias del documento | KILLED | DP-01, DC-05 |
| DOC8-M09 | auditoría: la generación se audita con otra acción | KILLED | DP-07 (y 30 más) |
| DOC8-M10b | seguridad: se aceptan rutas inseguras del ZIP | KILLED (2.ª tanda) | DV-12 |
| DOC8-M11 | verificación: se ignoran los ficheros no declarados | KILLED | DV-06 |
| DOC8-M12 | verificación: un fichero ausente pasa por válido | KILLED | DV-05 |
| DOC8-M13 | idempotencia: la misma clave sirve para otra muestra | KILLED | DP-04 |
| DOC8-M14 | verificación: se encuentra el paquete de otra empresa | KILLED | DV-11 |
| DOC8-M15 | interfaz: se genera sin `gobierno_paquetes:generate` | KILLED | GPQ-01 |
| DOC8-M16 | interfaz: se anuncia copia idéntica aunque no lo sea | KILLED | PQS-05 |
| DOC8-M17 | interfaz: estado del documento invertido en la ficha | KILLED (2.ª tanda) | PQT-01 (reforzada) |

## Cómo se llegó a 0 supervivientes

**DOC8-M10 sobrevivió en la primera tanda por un error de diseño del mutante, de Claude.**
- La mutación `return False and nombre.startswith("/") …` dejaba viva, por la precedencia de `and`/`or`, la comprobación `".." in nombre.split("/")`.
- Se rehízo como DOC8-M10b: la línea completa pasa a `return False`. DV-12 lo mata.

**DOC8-M17 sobrevivió en la primera tanda: hueco real de la prueba.**
- PQT-01 comprobaba que «Incluido» y «Excluido» aparecían en la región, pero no en qué fila.
- DeepSeek reforzó la prueba (T009c-r1) atando cada etiqueta a la fila de su documento. Desde entonces el mutante muere.

**Estado final:** árbol verificado sin restos de mutantes (sha256).
