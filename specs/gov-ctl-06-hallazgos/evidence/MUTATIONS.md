# GOV-CTL-06 · mutaciones de negocio (T011, herramienta de Claude `mutar_ctl04.py` sobre `mutantes.json`)

**Método**
- Un SEARCH único por mutante, sustituido por su REPLACE.
- Purga de `__pycache__` y `PYTHONDONTWRITEBYTECODE=1`.
- Restauración verificada por sha256 tras cada mutante.

**Órdenes**
- Backend: las 9 suites `tests/test_gov_ctl06_*.py` sobre PostgreSQL.
- Interfaz: `vitest run` del fichero de pruebas del componente mutado.

## Resultado final: 16 mutantes · 16 muertos · 0 equivalentes · 0 supervivientes

| ID | Mutación | Resultado | Prueba que lo mata |
|---|---|---|---|
| CTL6-M01 | maker-checker: quien presentó puede verificar | KILLED (2.ª tanda) | GH6-31 |
| CTL6-M02 | maker-checker: el autor de un avance puede verificar | KILLED (2.ª tanda) | GH6-32 |
| CTL6-M03 | responsable: se admite un cargo no VIGENTE | KILLED | GH6-10 |
| CTL6-M04 | responsable: se admite un cargo de otro ejercicio | KILLED | GH6-10 |
| CTL6-M05 | fecha objetivo pasada admitida | KILLED | GH6-11 |
| CTL6-M06 | avance decreciente admitido | KILLED | GH6-15 |
| CTL6-M07 | 100 % sin evidencia admitido | KILLED | GH6-16 |
| CTL6-M08 | presentar con acciones incompletas | KILLED | GH6-17 |
| CTL6-M09 | sin control de versión (If-Match) | KILLED | GH6-08 (y 1 más) |
| CTL6-M10 | origen: muestra de otra empresa admitida | KILLED | GH6-06 |
| CTL6-M11 | al cerrar no se congela la evidencia | KILLED | GH6-19 |
| CTL6-M12 | avance fuera de EN_REMEDIACION | KILLED | GH6-14 (y 1 más) |
| CTL6-M13 | auditoría del alta con acción equivocada | KILLED | GH6-03 (y 22 más) |
| CTL6-M14 | plan editable sin `gobierno_hallazgos:manage` (interfaz) | KILLED | PDA-04b |
| CTL6-M15 | verificar sin `gobierno_hallazgos:verify` (interfaz) | KILLED (3.ª tanda) | HLP-06 |
| CTL6-M16 | registrar hallazgo sin manage (interfaz) | KILLED | HLL-02 |

## Cómo se llegó a 0 supervivientes

**CTL6-M01 y CTL6-M02 sobrevivieron en la primera tanda.**
- En todas las pruebas, el mismo usuario («ua») registraba los avances y presentaba el hallazgo. Cada comprobación del maker-checker bastaba por sí sola, así que quitar una de las dos no se notaba.
- Se añadió `tests/test_gov_ctl06_makerchecker.py`, que separa los dos papeles:
  - GH6-31: presenta «uab» e intenta verificar «uab»;
  - GH6-32: registra el avance «ua», presenta «uab» e intenta verificar «ua»; un tercer usuario con verify verifica y cierra.
- Con esas pruebas, los dos mutantes mueren.

**CTL6-M15 sobrevivió dos veces.** El ejecutor lo marcó INVALID, pero en ambas tandas pasaban todas las pruebas, así que en la práctica sobrevivía.
- No había prueba de «sin verify, no hay botones». Se añadió HLP-06.
- HLP-06 seguía siendo vacía: esperaba un `h1` «Hallazgo» que ya existe en el estado de carga.
- Se corrigió para esperar «Hallazgo HAL-001», y entonces el mutante muere.

**Estado final:** árbol verificado sin restos de mutantes (sha256).
