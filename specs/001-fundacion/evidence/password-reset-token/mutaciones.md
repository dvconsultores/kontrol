# Mutaciones del reset de contraseña (Spec 002, delta password-reset-token) — 2026-10-26

Herramienta de Claude (`scratchpad/tools/mutaciones_reset.py`, fuera del repositorio): cada mutante se aplica, se prueba en PostgreSQL y se restaura byte a byte (huella SHA-256 comprobada); 0 ficheros `.mutbak` al final.

## Primera corrida (con TR-A1/TR-A2)

15 muertos, **5 supervivientes**: R06, R09, R11, R13 y R20. Cada uno tenía una segunda guarda que ocultaba la primera (el UPDATE atómico, el sello y la revocación se cubren entre sí). No faltaba código: faltaban pruebas. TR-A3a/b añadieron S05, S06, S07, S08 y B11.

## Segunda corrida (con TR-A3)

```
R01 la solicitud responde 200 (contrato público distinto): MUERTO · 1 failed, 1 warning in 5.09s
R02 respuesta distinta si la cuenta no existe: MUERTO · 1 failed, 1 passed, 1 warning in 5.13s
R03 token en claro en la BD: MUERTO · 1 failed, 6 passed, 1 warning in 5.44s
R04 sin caducidad: MUERTO · 1 failed, 13 passed, 1 warning in 6.18s
R05 TTL de 30 min: MUERTO · 1 failed, 13 passed, 1 warning in 6.21s
R06 reutilización (sin comprobación previa de usado): MUERTO · 1 failed, 31 passed, 1 warning in 9.08s
R07 doble éxito concurrente (UPDATE sin guarda): MUERTO · 1 failed, 11 passed, 1 warning in 6.04s
R08 el token nuevo no invalida los anteriores: MUERTO · 1 failed, 12 passed, 1 warning in 6.23s
R09 el reset no revoca sesiones: MUERTO · 1 failed, 29 passed, 1 warning in 8.90s
R10 get_current_auth no comprueba el sello: MUERTO · 1 failed, 17 passed, 1 warning in 6.59s
R11 la renovación no comprueba el sello: MUERTO · 1 failed, 30 passed, 1 warning in 8.99s
R12 el reset no rota el sello: MUERTO · 1 failed, 17 passed, 1 warning in 7.12s
R13 el desafío MFA usa el sello recargado (carrera login/reset): MUERTO · 1 failed, 32 passed, 1 warning in 10.51s
R14 el reset desactiva el MFA: MUERTO · 1 failed, 20 passed, 1 warning in 8.23s
R15 token en la auditoría: MUERTO · 1 failed, 22 passed, 1 warning in 8.56s
R16 token en el registro: MUERTO · 1 failed, 22 passed, 1 warning in 8.25s
R17 CLI sin confirmación: MUERTO · 1 failed, 24 passed, 1 warning in 8.54s
R18 CLI entre tenants: MUERTO · 1 failed, 26 passed, 1 warning in 8.60s
R19 sin limitar la auditoría anónima: MUERTO · 1 failed, 5 passed, 1 warning in 6.71s
R20 el cambio propio no rota el sello: MUERTO · 1 failed, 33 passed, 1 warning in 11.96s
MUTANTES=20 SUPERVIVIENTES=0
```

MUTATION_SURVIVORS = 0.

## Tercera corrida (tras TR-2c, ventana de auditoría con el reloj real)

MUTANTES=20 SUPERVIVIENTES=0
