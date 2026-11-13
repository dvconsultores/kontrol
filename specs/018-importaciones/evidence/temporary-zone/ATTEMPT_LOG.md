# Zona temporal · registro de intentos

- **Modelo y modo:** todo con `deepseek-v4-pro`, `stream=true` y `max_tokens` explícito (de 16000 a 32000).
- **Topes:** 8 llamadas por ciclo como máximo global y 2 reintentos por subproblema como máximo.
- **Excepciones:** ninguna `OWNER_EXCEPTION`. Las de ciclos anteriores no se heredan.

| Llamada | Subproblema | Entrada/salida (tokens) | Coste | Resultado |
|---|---|---|---|---|
| DEEPSEEK_CALL_1 | A. Backend: migración 0104, modelo, servicio, API, proyección, catálogo, guardias y pruebas | 4452/6396 | $0,007501 | AUDIT_PASS de 16 bloques. Rechazados 2: las rutas usaban `Context` y `get_context`, que no existen en `purchasing/api.py` (habría un NameError al importar), y las pruebas repetían la marca `MARCA` y el código de almacén con una fixture de módulo, además de importar `Decimal` sin uso |
| DEEPSEEK_CALL_2 | A·R1 | 4304/3513 | $0,004929 | AUDIT_PASS. 161 PASS en PostgreSQL; dos mutaciones muertas |
| DEEPSEEK_CALL_3 | B. Pantallas y E2E | 3320/3854 | $0,004797 | AUDIT_PASS de 10 bloques. Rechazados: `ZonaTemporal.tsx` importaba por defecto `AsyncButton` y `FormField`, que solo tienen exportación con nombre, y la E2E venía con sangría ajena |
| DEEPSEEK_CALL_4 | B·R1 | 1905/1561 | $0,002187 | AUDIT_PASS. Al medir aparecieron 3 fallos de Vitest: la guardia `gate-coverage` (el componente escribe sin puerta propia) y dos pruebas que cambiaban el `select` antes de que llegaran las opciones |
| DEEPSEEK_CALL_5 | B·R2 | 2483/1690 | $0,002550 | AUDIT_PASS. El componente lleva su propia puerta `Autorizado` y las pantallas dejan de envolverlo. Vitest 1949/1949 |
| DEEPSEEK_CALL_6 | E. Topología Alembic tras la fusión con PROC-11 de P1 | 900/496 | $0,000823 | AUDIT_PASS de 5 bloques. P1 publicó `0104_gov_proc11_sod_funciones` desde `0103`. La migración de este ciclo, sin publicar, se reencadena como `0105_receipt_temporary_zone` detrás de la de P1, con el cuerpo intacto; las guardias de cabeza pasan a 0105 y el catálogo a 494 (493 de P1 + 1). Una sola cabeza; ida, vuelta e ida en PostgreSQL; 100 PASS más la línea base de `n10` |

```text
TOTAL_CALLS=6  TOTAL_RETRIES=3  SUBPROBLEMS=3 (A, B, E)  MAX_RETRIES_SINGLE_SUBPROBLEM=2 (B)
GLOBAL_CAP_REACHED=0  OWNER_EXCEPTION=0  TOTAL_COST=$0,022787
```

**Implementado por Claude:** ninguna línea de producto, prueba, E2E ni migración. Claude hizo:
- la autoridad, el delta, el gate, los briefs y la auditoría;
- la aplicación literal de los bloques aprobados;
- las mutaciones de control, restauradas byte a byte;
- las sondas de Axe y de humo de UAT, fuera del repositorio;
- la regeneración mecánica de las fixtures;
- en la fusión, la resolución de Git de las 4 guardias en conflicto con la versión publicada de P1 (`--theirs`), y el `git mv` de `0104_…` a `0105_…`; el cambio de su contenido lo hizo DeepSeek (llamada 6);
- los documentos.

**Confirmaciones operativas (ALLOW o SKIP):**
- ALLOW:
  - detener y relanzar la UAT local;
  - crear y borrar bases de prueba de este ciclo (`ktz104`, `ktesttz`);
  - migrar la base de UAT;
  - usar la contraseña sintética pública de las identidades de E2E contra la UAT.
- SKIP:
  - leer `uat/mfa_keys` y las credenciales de `ACCESO_UAT.txt` (no hacía falta);
  - repetir la suite completa del ciclo anterior.
