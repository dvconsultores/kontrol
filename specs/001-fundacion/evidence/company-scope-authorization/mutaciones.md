# Mutaciones · company-scope-authorization (2026-10-27)

Herramienta de Claude fuera del árbol (`mutaciones_alcance.py`): cada mutante se aplica, se prueba con `-x` y se restaura byte a byte (SHA-256); `PYTHONDONTWRITEBYTECODE=1` y purga de `__pycache__`.

## Alcance por empresa — SQLite (23 mutantes)

```
S01 sin capacidad × empresa en el contexto (solo tenant): MUERTO · 1 failed, 1 warning in 8.18s
S02 la ruta no declara permisos (inventario de permisos vacío): MUERTO · 1 failed, 1 warning in 4.44s
S03 la empresa no cuenta: basta tener la capacidad en alguna: MUERTO · 1 failed, 1 warning in 4.36s
S04 una asignación acotada vale en cualquier empresa (FUNCIONAL_COMPLETO = todas): MUERTO · 1 failed, 1 warning in 4.38s
S05 la denegación no se audita: MUERTO · 1 failed, 1 warning in 4.35s
S06 catálogos de tenant sin exigir todo el tenant: MUERTO · 1 failed, 2 passed, 1 warning in 4.60s
S07 «todo el tenant» = alguna empresa: MUERTO · 1 failed, 1 warning in 4.41s
S08 bitácora sin filtro de empresa: MUERTO · 1 failed, 1 warning in 4.38s
S09 bitácora: eventos sin empresa visibles para cualquiera: MUERTO · 1 failed, 1 warning in 4.40s
S10 aprobadores por rol sin mirar la empresa de la asignación: MUERTO · 1 failed, 4 passed, 1 warning in 5.15s
S11 decidir sin aprobaciones:approve en la empresa de la solicitud: MUERTO · 1 failed, 5 passed, 1 warning in 5.21s
S12 usuario inactivo conserva el alcance: MUERTO · 1 failed, 18 passed, 1 warning in 7.25s
S13 el acceso (user_scopes) deja de acotar el alcance: MUERTO · 1 failed, 27 passed, 1 warning in 10.56s
S14 capacidades en la empresa: la asignación acotada vale en cualquiera: MUERTO · 1 failed, 1 warning in 4.63s
S15 capacidades en la empresa sin exigir el acceso (user_scopes): MUERTO · 1 failed, 4 passed, 1 warning in 5.53s
S16 capacidades en la empresa para un usuario inactivo: MUERTO · 1 failed, 5 passed, 1 warning in 5.34s
S16b capacidades en una empresa de otro tenant: MUERTO · 1 failed, 7 passed, 1 warning in 5.53s
S16c rol inactivo da capacidades en la empresa: MUERTO · 1 failed, 8 passed, 1 warning in 5.60s
S17 tareas/notificaciones con permisos de todo el tenant: MUERTO · 1 failed, 1 warning in 4.74s
S18 documentos con permisos de todo el tenant: MUERTO · 1 failed, 1 passed, 1 warning in 4.59s
S19 acciones de unidades con permisos de todo el tenant: MUERTO · 1 failed, 2 passed, 1 warning in 4.96s
S20 acciones de almacenes con permisos de todo el tenant: MUERTO · 1 failed, 3 passed, 1 warning in 5.03s
S21 la capacidad se exige antes que las reglas de dominio de la aprobación: MUERTO · 1 failed, 20 passed in 4.41s
MUTANTES=23 SUPERVIVIENTES=0
```

## Alcance por empresa — PostgreSQL (23 mutantes)

```
S01 sin capacidad × empresa en el contexto (solo tenant): MUERTO · 1 failed, 1 warning in 5.73s
S02 la ruta no declara permisos (inventario de permisos vacío): MUERTO · 1 failed, 1 warning in 5.75s
S03 la empresa no cuenta: basta tener la capacidad en alguna: MUERTO · 1 failed, 1 warning in 5.30s
S04 una asignación acotada vale en cualquier empresa (FUNCIONAL_COMPLETO = todas): MUERTO · 1 failed, 1 warning in 5.35s
S05 la denegación no se audita: MUERTO · 1 failed, 1 warning in 5.31s
S06 catálogos de tenant sin exigir todo el tenant: MUERTO · 1 failed, 2 passed, 1 warning in 5.65s
S07 «todo el tenant» = alguna empresa: MUERTO · 1 failed, 1 warning in 5.72s
S08 bitácora sin filtro de empresa: MUERTO · 1 failed, 1 warning in 5.48s
S09 bitácora: eventos sin empresa visibles para cualquiera: MUERTO · 1 failed, 1 warning in 5.37s
S10 aprobadores por rol sin mirar la empresa de la asignación: MUERTO · 1 failed, 4 passed, 1 warning in 5.98s
S11 decidir sin aprobaciones:approve en la empresa de la solicitud: MUERTO · 1 failed, 5 passed, 1 warning in 5.75s
S12 usuario inactivo conserva el alcance: MUERTO · 1 failed, 18 passed, 1 warning in 8.62s
S13 el acceso (user_scopes) deja de acotar el alcance: MUERTO · 1 failed, 27 passed, 1 warning in 12.94s
S14 capacidades en la empresa: la asignación acotada vale en cualquiera: MUERTO · 1 failed, 1 warning in 5.27s
S15 capacidades en la empresa sin exigir el acceso (user_scopes): MUERTO · 1 failed, 4 passed, 1 warning in 5.91s
S16 capacidades en la empresa para un usuario inactivo: MUERTO · 1 failed, 5 passed, 1 warning in 6.29s
S16b capacidades en una empresa de otro tenant: MUERTO · 1 failed, 7 passed, 1 warning in 6.55s
S16c rol inactivo da capacidades en la empresa: MUERTO · 1 failed, 8 passed, 1 warning in 6.62s
S17 tareas/notificaciones con permisos de todo el tenant: MUERTO · 1 failed, 1 warning in 5.74s
S18 documentos con permisos de todo el tenant: MUERTO · 1 failed, 1 passed, 1 warning in 5.88s
S19 acciones de unidades con permisos de todo el tenant: MUERTO · 1 failed, 2 passed, 1 warning in 6.20s
S20 acciones de almacenes con permisos de todo el tenant: MUERTO · 1 failed, 3 passed, 1 warning in 6.56s
S21 la capacidad se exige antes que las reglas de dominio de la aprobación: MUERTO · 1 failed, 20 passed in 3.44s
MUTANTES=23 SUPERVIVIENTES=0
```

## Regresión del techo de delegación (21 mutantes)

SQLite: 20/21; D17 (candado consultivo) solo tiene pruebas en PostgreSQL y se ejecuta con `--pg`:

```
D01 asignar sin techo de capacidades: MUERTO · 1 failed, 1 passed, 1 warning in 4.98s
D02 autoescalada sin código propio: MUERTO · 1 failed, 3 passed, 1 warning in 5.29s
D03 rol protegido sin exigir tenerlo: MUERTO · 1 failed, 6 passed, 1 warning in 5.79s
D04 asignar sin techo de alcance: MUERTO · 1 failed, 1 warning in 4.81s
D05 quitar sin techo de capacidades: MUERTO · 1 failed, 16 passed, 1 warning in 7.58s
D06 quitar sin techo de alcance: MUERTO · 1 failed, 6 passed, 1 warning in 5.88s
D07 crear rol sin techo: MUERTO · 1 failed, 1 warning in 4.85s
D08 crear rol sin techo de alcance: MUERTO · 1 failed, 18 passed, 1 warning in 8.52s
D09 rol de otro tenant aceptado: MUERTO · 1 failed, 13 passed, 1 warning in 6.82s
D10 rol inactivo aceptado: MUERTO · 1 failed, 15 passed, 1 warning in 7.30s
D11 alcance nulo = todo el tenant (ignora user_scopes): MUERTO · 1 failed, 3 passed, 1 warning in 5.24s
D12 asignación acotada vale en cualquier empresa: MUERTO · 1 failed, 1 warning in 4.69s
D13 usuario inactivo conserva capacidades: MUERTO · 1 failed, 18 passed, 1 warning in 7.98s
D14 último administrador sin protección: MUERTO · 1 failed, 1 warning in 4.83s
D15 último administrador cuenta por nombre de rol (sin simular): MUERTO · 1 failed, 1 warning in 5.06s
D16 otros administradores sin mirar capacidades: MUERTO · 1 failed, 1 warning in 4.91s
D17 sin candado de autoridad: SOBREVIVE · 3 passed, 3 skipped, 1 warning in 7.18s
D18 quitar sin comprobar el último administrador: MUERTO · 1 failed, 1 warning in 4.72s
D19 ADMIN conserva las capacidades funcionales (sin división): MUERTO · 1 failed, 6 passed, 1 warning in 5.70s
D20 delegabilidad del listado sin techo: MUERTO · 1 failed, 7 passed, 1 warning in 5.34s
D21 cuerpo de asignación acepta campos ocultos: MUERTO · 1 failed, 14 passed, 1 warning in 7.39s
MUTANTES=21 SUPERVIVIENTES=1
--- D17 con --pg
D17 sin candado de autoridad: MUERTO · 1 failed, 5 passed
```

**Resultado:** alcance 23/23 en ambos motores; delegación 21/21. SUPERVIVIENTES = 0.

Historia: S13, S15, S16, S16b y S16c sobrevivieron en su primera corrida y se mataron con pruebas nuevas (CSD-05..09, TC-A4/A5/A6) antes del cierre.
