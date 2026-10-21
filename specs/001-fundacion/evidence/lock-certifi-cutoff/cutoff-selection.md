# Selección del corte del lock (OD-LOCK-01/02, 2026-10-21)

## Revalidación del aviso
- **PYSEC-2026-4320 = GHSA-6q48-6c7w-9gw2:**
  - OSV: `introduced 2019.03.09`, `fixed 2026.10.19`.
  - GHSA: severidad **critical**, `>= 2019.03.09, < 2026.10.19`, `first_patched 2026.10.19`.
  - Ninguno de los dos está retirado.
- CERTIFI_SAFE_VERSION = CERTIFI_SECURITY_FLOOR = **2026.10.19**, que es además la última publicada.
- **pip-audit (PyPI y OSV) sobre el lock de `e0f0804`:** solo certifi 2026.10.18 y PYSEC-2026-4320.
  NEW_ADVISORIES_SINCE_E0F0804 = 0, sin contar el objetivo.

## Artefacto relevante
- **CERTIFI_RELEVANT_ARTIFACT** = `certifi-2026.10.19-py3-none-any.whl` (wheel), subido el
  **2026-10-20T02:24:15.072385Z** (API JSON de PyPI e índice simple PEP 700).
- El sdist `certifi-2026.10.19.tar.gz` se subió a las 02:24:16.604828Z.

## Semántica de frontera de `--exclude-newer` (uv 0.12.17, medida)
| Corte | certifi resuelto |
|---|---|
| `02:24:15Z` | 2026.10.18 |
| `02:24:15.072384Z` · `.072385Z` · `.072386Z` · `.0724Z` · `.072999Z` | 2026.10.18 |
| **`02:24:15.073Z`** | **2026.10.19** |
| `.1Z` · `.25Z` · `.5Z` · `.999999Z` · `16Z` · `16.000001Z` | 2026.10.19 |

- **EXCLUDE_NEWER_BOUNDARY_SEMANTICS:** uv compara a precisión de **milisegundo** con «subido < corte» estricto. El
  wheel (`.072385`) cuenta como `.072`, así que el corte mínimo aceptado es `.073`.
- **LOCK_CUTOFF_PREVIOUS** = `2026-10-20T00:00:00Z` → **LOCK_CUTOFF_NEW** = `2026-10-20T02:24:15.073Z`.
- **LOCK_CUTOFF_DELTA_SECONDS** = **8655,073**, sin margen arbitrario.

## Inventario de la ventana
RELEASES_INSIDE_CUTOFF_WINDOW, para los 49 paquetes del lock en `(2026-10-20T00:00:00Z, 2026-10-20T02:24:16Z]`:
- solo los dos artefactos de certifi 2026.10.19 (`advisory-and-release.json`);
- dentro del corte elegido entra únicamente el wheel.

## Resoluciones independientes
- Dos resoluciones con el comando canónico, el corte nuevo y cachés separadas (`--no-cache`).
- LOCK_RUN1_GRAPH_HASH = LOCK_RUN2_GRAPH_HASH = `6a5d16420a3c8640…`, con ficheros idénticos byte a byte.
  LOCK_GRAPH_DETERMINISTIC = 1.
- La regeneración en el repositorio coincide con el candidato y es idempotente.

## Atribución del diff (lock de `e0f0804` → nuevo)
| Clase | Cambios |
|---|---|
| TARGET_SECURITY_CHANGE | `certifi 2026.10.18 → 2026.10.19` |
| DIRECT_CHANGE | 0 |
| TRANSITIVE_REQUIRED_BY_TARGET | 0 (certifi no tiene dependencias) |
| **UNRELATED_CHANGE** | **0** |
| Cabecera | solo el corte (`--custom-compile-command` declara el comando completo, con `--upgrade`) |

- **Auditoría del lock nuevo:** pip-audit PyPI = 0 y OSV = 0, sin exclusiones.
- **Uso de certifi en el producto:** 0 imports de certifi, httpx, requests o urllib3 en `app` y `central_authority`.

## Suelo de seguridad (OD-LOCK-03)
- **Fuente:** `docs/evidence/cve-review.md` §«Avisos de dependencias transitivas» (aviso, rango afectado, corregida en
  y publicación de la corregida).
- **SDV-08 exige:**
  - certifi en el lock;
  - versión del lock ≥ corregida;
  - corregida fuera del rango afectado;
  - certifi **no** directa en `requirements.txt`;
  - corte de la cabecera posterior a la publicación de la corregida.
- IDL-04 acepta ya cortes con fracción de segundo.
- CERTIFI_DIRECT_REQUIREMENT_ADDED = 0.
