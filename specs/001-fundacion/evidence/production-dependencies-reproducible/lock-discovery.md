# Descubrimiento del lock histórico y prueba de determinismo (2026-10-20, HEAD `44e47b5`)

## Lock histórico (`resources/backend/requirements.lock`)
| Campo | Valor | Evidencia |
|---|---|---|
| LOCK_FORMAT | lista `nombre==versión` estilo `pip freeze` (46 líneas), sin cabecera, sin anotaciones ni marcadores | nombres con la grafía de los metadatos (`Mako`, `MarkupSafe`, `SQLAlchemy`, `email_validator`) |
| LOCK_GENERATOR | `pip freeze` de un entorno instalado, filtrado a mano (sin `pip`/`setuptools`) | formato; commit `8d44002` «requirements.lock (46 paq) … regenerados» |
| LOCK_GENERATOR_VERSION_IF_KNOWN | UNKNOWN | — |
| LOCK_PYTHON_VERSION | **3.11** (inferida) | contiene `greenlet`, que SQLAlchemy 2.0.36 solo exige con `python_version < "3.13"`; resolver con 3.11 lo reproduce (`greenlet` aparece), con 3.13 no |
| LOCK_PLATFORM | linux x86_64 (inferida: `uvloop`, `httptools`) | — |
| LOCK_CREATED_FROM | el entorno de trabajo del 2026-08-04 (T-049, CVE) | `8d44002` |
| LOCK_REFRESH_COMMAND_IF_PRESENT | **ninguno** (sin script, Makefile, CI ni documentación) | búsqueda en `.github`, `scripts`, `qa`, `docs/governance`, README |
| LOCK_HAS_HASHES | 0 | — |
| LOCK_IS_HAND_EDITED | probable (selección de paquetes) | — |
| LOCK_REPRODUCIBLE_FROM_REPO | **0** | sin comando; intérprete distinto del de la imagen |
| Consumidores | **ninguno**: la imagen instala `requirements.txt` | `Dockerfile.backend:20-21` |

**Historia de deriva:**
- `requirements.txt` cambió dos veces sin regenerar el lock:
  - `3cc89a7` (2026-08-12, `reportlab==5.0.0`);
  - `f7e7e44` (2026-10-20, `python-magic==0.4.27`).
- Nada comprueba la coherencia entre los dos ficheros.

## Mecanismo canónico propuesto
Desde `resources/backend/`:

    uv pip compile requirements.txt --python-version 3.13 --python-platform x86_64-unknown-linux-gnu --exclude-newer 2026-10-20T00:00:00Z -o requirements.lock

- **Generador:** uv 0.12.17. ADR-014 ya prevé `requirements.lock` o `uv.lock`, y la imagen no necesita uv.
- **Formato:** requirements fijado con anotaciones `# via`, instalable con `pip`.
- **Intérprete y plataforma:** Python 3.13 (la imagen es `python:3.13-slim`) en Linux x86_64. Los workflows no declaran
  `platforms`, así que el destino es solo amd64.
- **`--exclude-newer`:** fija el instante del índice y hace la resolución repetible. Actualizar dependencias equivale a
  mover ese corte de forma deliberada (actualización controlada, ADR-014).

## Prueba de determinismo
| Corrida | Caché | Paquetes | Hash del grafo (sha256 de `nombre==versión` canónico y ordenado) |
|---|---|---|---|
| 1 | independiente, `--no-cache` | 49 | `f874c6a65ca3319b…` |
| 2 | independiente, `--no-cache` | 49 | `f874c6a65ca3319b…` |

LOCK_GRAPH_DETERMINISTIC = **1**: mismos nombres y versiones, y sin marcadores ni índices alternativos.

| Contraprueba | Resultado |
|---|---|
| Igual pero **sin** `--exclude-newer` (resolver hoy) | difiere en `certifi` (2026.10.19 frente a 2026.10.18): un build sin corte deriva en horas, como ya hace la imagen |
| Igual con `--python-version 3.11` | añade `greenlet` 3.5.6: explica la entrada del lock histórico |
| Grafo propuesto frente a V1' (`pip install -r requirements.txt` del 2026-10-20 02:12Z, certificado) | **idéntico** (49/49) |
