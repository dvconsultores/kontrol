# CLI del propietario — contrato (Fase 1)

`python -m central_authority.cli <orden> --operator <etiqueta> [...]`. Toda orden exige
`--operator` (etiqueta operativa que queda en libro y auditoría; **no** es autenticación remota: la
CLI corre dentro del entorno de la autoridad). Salida: JSON en stdout; errores en stderr con código
y salida ≠ 0. Nunca imprime la clave privada.

| Orden | Argumentos | Efecto |
|---|---|---|
| `register-installation` | `--installation-id`, `--public-key-file <pem>`, `--customer-id`, `--contract-id`, `--company-tax-id` | alta idempotente; mismos datos → mismo registro; datos distintos → `INSTALLATION_CONFLICT` |
| `issue-license` | `--installation-id`, `--anio <AAAA>` (período DOC-07) o `--period-start/--period-end` ISO, `--entitlements '<json>'`, `--minimum-version` | emite la siguiente `revision` del período (1 si es la primera); imprime `{"payload": …, "signature_hex": …, "license_id": …, "revision": …}` |
| `reissue-license` | ídem | alias de `issue-license`: la reemisión es una emisión más del mismo período |
| `show-issuance` | `--license-id` | una emisión del libro (payload, firma, hash, `revision`, operador, fecha) |
| `list-issuances` | `--installation-id` | emisiones de una instalación, por período y `revision` |

Errores: `INSTALLATION_NOT_FOUND`, `INSTALLATION_CONFLICT`, `SIGNING_KEY_MISSING`,
`SIGNING_KEY_INVALID`, `INVALID_PERIOD`, `INVALID_ENTITLEMENTS`, `ISSUANCE_NOT_FOUND`.
