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

```text
TOTAL_CALLS=5  TOTAL_RETRIES=3  SUBPROBLEMS=2 (A, B)  MAX_RETRIES_SINGLE_SUBPROBLEM=2 (B)
GLOBAL_CAP_REACHED=0  OWNER_EXCEPTION=0  TOTAL_COST=$0,021964
```

**Implementado por Claude:** ninguna línea de producto, prueba, E2E ni migración. Claude hizo:
- la autoridad, el delta, el gate, los briefs y la auditoría;
- la aplicación literal de los bloques aprobados;
- las mutaciones de control, restauradas byte a byte;
- las sondas de Axe y de humo de UAT, fuera del repositorio;
- la regeneración mecánica de las fixtures;
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
