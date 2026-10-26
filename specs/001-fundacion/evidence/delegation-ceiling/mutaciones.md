# Techo de delegación · mutaciones (2026-10-26)

Herramienta de Claude, fuera del repositorio: `mutaciones_delegacion.py`.
- Cada mutante se aplica, se prueba con `-x` y se restaura byte a byte.
- Una aserción comprueba la huella SHA-256 del fichero restaurado.
- Se purgan los `__pycache__` en cada paso y se ejecuta con `PYTHONDONTWRITEBYTECODE=1`.
- D17 (sin candado) se ejecuta sobre PostgreSQL; el resto, sobre SQLite.
- El producto nunca quedó mutado: `git status` de `app/` era idéntico antes y después.

## Primera pasada: 18 de 21 muertos

Tres mutantes sobrevivieron, y en los tres casos el hueco estaba en las pruebas, no en el producto.

| Mutante | Hueco | Prueba nueva |
|---|---|---|
| D08 (crear rol sin techo de alcance) | Ninguna prueba creaba un rol de una empresa fuera del alcance del actor | DSC-C01 (TD-A3) |
| D13 (usuario inactivo conserva capacidades) | Ninguna prueba fijaba el contrato «inactivo = sin autoridad» | DC-U01 (TD-A3) |
| D17 (sin candado consultivo) | DLA-L04/L05 pasaban sin candado: las dos operaciones no llegaban a intercalarse | DLA-L06 (TD-A3b). Fuerza el intercalado con una barrera de 2 hilos tras la comprobación (límite de 2 s): sin candado, las dos renuncias pasan y el tenant se queda sin administradores; con candado, el segundo hilo espera y recibe 409 |

Además, en la primera pasada D13 apuntaba al fichero de pruebas equivocado. Fue un error de configuración de la herramienta de Claude, y se corrigió para que incluya `test_delegation_ceiling.py`.

## Pasada final: 21 de 21 muertos

| ID | Mutante | Resultado | Pruebas |
|---|---|---|---|
| D01 | asignar sin techo de capacidades | MUERTO | 1 failed, 1 passed, 1 warning in 4.47s |
| D02 | autoescalada sin código propio | MUERTO | 1 failed, 3 passed, 1 warning in 4.77s |
| D03 | rol protegido sin exigir tenerlo | MUERTO | 1 failed, 6 passed, 1 warning in 5.21s |
| D04 | asignar sin techo de alcance | MUERTO | 1 failed, 1 warning in 4.32s |
| D05 | quitar sin techo de capacidades | MUERTO | 1 failed, 16 passed, 1 warning in 6.78s |
| D06 | quitar sin techo de alcance | MUERTO | 1 failed, 6 passed, 1 warning in 5.24s |
| D07 | crear rol sin techo | MUERTO | 1 failed, 1 warning in 4.27s |
| D08 | crear rol sin techo de alcance | MUERTO | 1 failed, 18 passed, 1 warning in 7.75s |
| D09 | rol de otro tenant aceptado | MUERTO | 1 failed, 13 passed, 1 warning in 6.27s |
| D10 | rol inactivo aceptado | MUERTO | 1 failed, 15 passed, 1 warning in 6.64s |
| D11 | alcance nulo = todo el tenant (ignora user_scopes) | MUERTO | 1 failed, 3 passed, 1 warning in 4.80s |
| D12 | asignación acotada vale en cualquier empresa | MUERTO | 1 failed, 1 warning in 4.29s |
| D13 | usuario inactivo conserva capacidades | MUERTO | 1 failed, 18 passed, 1 warning in 7.01s |
| D14 | último administrador sin protección | MUERTO | 1 failed, 1 warning in 4.37s |
| D15 | último administrador cuenta por nombre de rol (sin simular) | MUERTO | 1 failed, 1 warning in 4.28s |
| D16 | otros administradores sin mirar capacidades | MUERTO | 1 failed, 1 warning in 4.38s |
| D18 | quitar sin comprobar el último administrador | MUERTO | 1 failed, 1 warning in 4.30s |
| D19 | ADMIN conserva las capacidades funcionales (sin división) | MUERTO | 1 failed, 6 passed, 1 warning in 5.21s |
| D20 | delegabilidad del listado sin techo | MUERTO | 1 failed, 7 passed, 1 warning in 5.14s |
| D21 | cuerpo de asignación acepta campos ocultos | MUERTO | 1 failed, 14 passed, 1 warning in 6.40s |
| D17 | sin candado de autoridad | MUERTO | 1 failed, 4 passed, 1 warning in 12.13s |

**MUTATION_SURVIVORS = 0.**
