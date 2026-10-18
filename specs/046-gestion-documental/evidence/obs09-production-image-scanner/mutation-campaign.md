# Campaña de mutaciones (GOOD → PASS · MUTATED → FAIL · RESTORED → PASS desde copias GOOD; `__pycache__` purgado; `PYTHONDONTWRITEBYTECODE=1`; juego O09 + CLAMD-QA = 44 pruebas; guion `<scratch>/o9/mutar.py`)
| Id | Mutación | Fichero | Detectada por | Resultado |
|---|---|---|---|---|
| M-01 | CLEAN interpretado como INFECTED | `scanning.py` | O09-01, 21… | detectada |
| M-02 | INFECTED interpretado como CLEAN | ídem | O09-02, 20 | detectada |
| M-03 | ERROR del demonio → CLEAN | ídem | O09-15, 22 | detectada |
| M-04 | tiempo agotado → aceptación | ídem | O09-05 | detectada |
| M-05 | la selección del analizador se ignora (siempre clamscan) | ídem | O09-12, 14 | detectada |
| M-06 | alternativa automática a clamscan si clamd no conecta | ídem | O09-03, 14, 25 | detectada |
| M-07 | el flujo se sustituye por `zSCAN <ruta>` | ídem | O09-08, 09, 10 (y la ruta aparece en lo recibido) | detectada |
| M-08 | `StreamMaxLength 25M` (por debajo del máximo documental) | `deploy/clamd/clamd.conf` | CLAMD-QA-01, 02, 04 | detectada |
| M-09 | respuesta malformada → CLEAN | `scanning.py` | O09-06, 21 | detectada |
| M-10 | puerto de clamd publicado al anfitrión | `compose.yaml` | CLAMD-QA-04 | detectada |
| M-11 | clamd monta el almacén documental | `compose.yaml` | CLAMD-QA-04 | detectada |
| M-12 | respuesta truncada → CLEAN | `scanning.py` | O09-07 | detectada |
| M-13 | la elección del analizador deja de validarse | `config.py` | O09-23 | detectada |
| M-14 | el puerto deja de validarse | `config.py` | O09-18 | detectada |
| M-15 | el backend vuelve a llevar clamscan | `Dockerfile.backend` | O09-24 | detectada (reejecutada tras corregir el patrón del guion) |
| M-16 | el QA aprueba aunque el demonio caído responda CLEAN | `qa/clamd_qa.py` | CLAMD-QA-09 | detectada |
**16/16 detectadas**; cada mutación restaurada con copia idéntica (`filecmp`) y 44/44 tras restaurar. Fuente: `<scratch>/o9/mutaciones.txt`.
