# Campaña de mutaciones (GOOD → PASS · MUTATED → FAIL · RESTORED → PASS desde copias GOOD; `__pycache__` purgado; `PYTHONDONTWRITEBYTECODE=1`; juego O06-01…20 + O12-01…20 = 40 pruebas; guion `<scratch>/o6/mutar.py`; el almacén fijo histórico no se tocó)
| Id | Mutación | Fichero | Detectada por | Resultado |
|---|---|---|---|---|
| M-01 | vuelve el almacén fijo `<tmp>/kontrol-test-storage` | `conftest.py` | O06-01, 03, 05, 08, 09, 11, 12, 13… | detectada |
| M-02 | vuelven los respaldos fijos | ídem | O06-02, 04, 06, 08, 10 | detectada |
| M-03 | la misma identidad (`…-compartida`) para todos los procesos | ídem | O06-01, 02, 03, 11… | detectada |
| M-04 | `Settings` cacheada antes de la inyección y sin `cache_clear` | ídem | O06-20 (contrato estático: el bloque exige `get_settings.cache_clear()`); en proceso, la fixture de volumen vuelve a limpiar la caché por módulo, por eso O06-08 no la ve: la defensa es el contrato | detectada |
| M-05 | aplicación y fixture con raíces distintas en el mismo proceso (`Settings` cacheada en `storage`, entorno en `otro`) | ídem | O06-05, 07, 08 | detectada |
| M-06 | sin limpieza | ídem | O06-09, 10, 11, 12 (16 raíces huérfanas dejadas por la mutación, retiradas por el guion) | detectada |
| M-07 | limpieza por patrón de todas las raíces del prefijo | ídem | O06-02, 11, 19 | detectada |
| M-08 | el hijo hereda la raíz del padre | ídem | O06-01, 03, 11, 12, 13 | detectada |
| M-09 | el almacén legado cuenta como residuo de la corrida | `qa/suite_tiempos.py` | O06-18, O12-09 | detectada |
| M-10 | almacén aislado pero respaldos sin fijar | `conftest.py` | O06-02, 04, 06, 08, 10… | detectada |
| M-11 | `sleep(0)` en el arnés | ídem | O06-19 | detectada |
| M-12 | las sondas en paralelo (`-n 2`) | `test_almacen_de_pruebas.py` | O06-19 (+ fallos de los hijos sin el plugin) | detectada |
| M-13 | fuente del producto (motivo del falso seguro) | `scanning.py` (restaurado) | O06-17, O12-15 | detectada |
| M-14 | techo del subproceso `clamscan` 120 → 240 | `scanning.py` (restaurado) | O06-17, O12-13 | detectada |
**14/14 detectadas**; cada mutación restaurada con copia idéntica (`filecmp`) y 40/40 tras restaurar; raíces huérfanas
restantes 0. Fuente: `<scratch>/o6/mutaciones.txt`.
