# Mutaciones M-01…M-14 (A2) · GOOD→PASS, MUTATED→FAIL, RESTORED→PASS (`mutation-run-a2.txt`, `mutation-script-a2.sh`)
Detector: `tests/test_clamav_qa.py` con el analizador real exportado (GOOD 15/15, luego 17/17). SEARCH/REPLACE único,
`__pycache__` purgado, restauración byte a byte.

| Id | Mutación | Detector | Resultado |
|---|---|---|---|
| M-01 | el preflight no escanea (solo existe el ejecutable) | CLAM-10, CLAM-10b | muerta |
| M-02 | sin verificación de EICAR | CLAM-10b | muerta |
| M-03 | aceptar que falten firmas | 1.ª pasada **sobrevivió** (CLAM-08 aceptaba «QAC-03/04» por prefijo) → razón exacta «QAC-03: faltan firmas» → muerta | muerta |
| M-04 | el runner marca el analizador disponible sin preflight | contrato del runner | muerta |
| M-05 / M-06 | sin exportar `KONTROL_CLAMAV_DB` / `KONTROL_CLAMSCAN_PATH` | CLAM-11 | muertas |
| M-07 | `sudo apt-get install` | CLAM-13 | muerta |
| M-08 | no distinguir el error de proceso de CLEAN (QAC-06) | 1.ª pasada **sobrevivió** → CLAM-10c (analizador que ignora las firmas) → muerta | muerta |
| M-09 | sin idempotencia | CLAM-02 | muerta |
| M-10 | prefijo dentro del repositorio | CLAM-12 (+ reales 04/05/06/09 al no encontrar el prefijo) | muerta |
| M-11 | el modo canónico vuelve a omitir si falta el analizador | contrato del runner | muerta |
| M-12 | EICAR aceptado como limpio (rc 0) | CLAM-10b | muerta |
| M-13 | debilitar el rechazo de EICAR en `test_documents.py` | 1.ª pasada **sobrevivió** (la prueba real sigue pasando) → DOCENV-03 estático → muerta | muerta |
| M-14 | aceptar un motor que no arranca | 1.ª pasada mal formada (SEARCH) → corregida → CLAM-07 → muerta | muerta |

**14/14 muertas** (tres tras reforzar pruebas, una tras corregir el SEARCH; documentado). Equivalentes: 0.
