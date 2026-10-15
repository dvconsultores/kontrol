# Campaña de mutaciones (GOOD → PASS · MUTATED → FAIL · RESTORED → PASS desde copias GOOD; `__pycache__` purgado; `PYTHONDONTWRITEBYTECODE=1`; juego O12-01…20; guion `<scratch>/o12/mutar.py`)
| Id | Mutación | Fichero | Detectada por | Resultado |
|---|---|---|---|---|
| M-01 | duración por reloj de pared en vez de monotónica | `qa/suite_tiempos.py` | O12-01, O12-11 | detectada |
| M-02 | el manifiesto omite la duración total | ídem | O12-01, O12-02 | detectada |
| M-03 | rutas absolutas sin sanear | ídem | O12-04, O12-05 | detectada |
| M-04 | el manifiesto anota el nombre del equipo | ídem | O12-04 | detectada |
| M-05 | el almacén fijo cuenta como residuo | ídem | O12-09 | detectada |
| M-06 | la anomalía convierte un verde en rojo | ídem | O12-11 | detectada |
| M-07 | techo del subproceso `clamscan` 120 → 240 s | `scanning.py` (restaurado) | O12-13 | detectada |
| M-08 | `time.sleep(0)` en la herramienta | `qa/suite_tiempos.py` | O12-20 | detectada |
| M-09 | `KONTROL_DOCUMENT_SCAN=off` para ir más rápido | ídem | O12-08, O12-15 | detectada |
| M-10 | reorden (`--ff`) en la orden | ídem | O12-17 | detectada |
| M-11 | paralelismo (`-n 4`) | ídem | O12-17, O12-18 | detectada |
| M-12 | fuente del producto cambiada (motivo del falso seguro) | `scanning.py` (restaurado) | O12-15 | detectada |
| M-13 | una fuente de `/proc` ausente tumba la medición | `qa/suite_tiempos.py` | O12-07 | detectada |
**13/13 detectadas**; cada mutación restaurada con copia idéntica (`filecmp`) y 20/20 tras restaurar. Fuente: `<scratch>/o12/mutaciones.txt`.
