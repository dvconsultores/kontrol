# Mutaciones de los invariantes de seguridad del MFA (Spec 002) — 2026-10-26

Ejecutor: Claude (`scratchpad/tools/mutaciones_mfa.py`, fuera del repositorio). Cada mutante se aplica con un único reemplazo exacto,
se purgan los `__pycache__` (`PYTHONDONTWRITEBYTECODE=1`), se corren las pruebas dueñas con `-x` sobre SQLite y el fichero se restaura
byte a byte (hash comprobado). Diffstat del producto idéntico antes y después; ninguna copia `.mutbak` residual.

| Mutante | Fichero | Pruebas | Resultado |
|---|---|---|---|
| M01 `requires_mfa` siempre falso | `mfa_policy.py` | `test_mfa_policy`, `test_mfa_login` | MUERTO |
| M02 `get_current_auth` ignora `mfa_verified_at` | `core/dependencies.py` | `test_mfa_session_authority` | MUERTO |
| M03 reautenticación nunca exigida | `core/dependencies.py` | `test_mfa_management`, `test_mfa_session_authority` | MUERTO |
| M04 antirrepetición acepta el mismo paso (`<=`) | `mfa_service.py` | `test_mfa_login`, `test_mfa_concurrency` | MUERTO |
| M05 código de recuperación reutilizable | `mfa_service.py` | `test_mfa_login`, `test_mfa_concurrency` | MUERTO |
| M06 reset administrativo sobre uno mismo | `mfa_service.py` | `test_mfa_management` | MUERTO |
| M07 reset sin techo de privilegios | `mfa_service.py` | `test_mfa_management` | MUERTO |
| M08 rotura de cristal sin confirmación | `mfa_breakglass.py` | `test_mfa_session_authority` | MUERTO |
| M09 cifrado sin AAD (secreto trasladable entre usuarios) | `mfa_crypto.py` | `test_mfa_crypto`, `test_mfa_no_bypass` | MUERTO |
| M10 renovación sin comprobar el segundo factor | `service.py` | `test_mfa_session_authority`, `test_auth_rotacion_atomica` | MUERTO |
| M11 ventana TOTP ampliada (±4 pasos) | `totp.py` | `test_mfa_totp` | MUERTO |

`MUTANTES = 11` · `SUPERVIVIENTES = 0`.
