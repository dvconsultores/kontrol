# T052 · registro de intentos

| Intento | Modelo | Coste | Resultado | Motivo |
|---|---|---|---|---|
| T052-A1, inicial | deepseek-v4-pro | $0,005225 | Producción: AUDIT_PASS. Pruebas: AUDIT_REJECT | Import erróneo de `EXIT_BUNDLE_INVALID`, código muerto y sin prueba real de `audit_backup_event` |
| T052-A1, reintento 1 | deepseek-v4-pro | $0,003236 | AUDIT_REJECT | `backup_cli.main.audit_backup_event` no existe |
| T052-A1, reintento 2 | deepseek-v4-pro | $0,003099 | AUDIT_REJECT | Firma inventada, `KONTROL_SKIP_AUDIT` inventada, campos de `AuditEvent` inexistentes |

`T052-A1` queda **BLOCKED**: reintentos semánticos agotados (2 de 2). Nada aplicado: el bloque de producción aprobado no se aplica sin su prueba dirigida. Claude no escribió el parche.

Causa del último fallo: el brief del reintento 2 resumía el intento anterior y omitía la firma de la función, así que el ejecutor, sin memoria, la inventó. Requiere rediagnóstico del brief; renombrar la tarea no reinicia el contador.

# T052-RPO-IMPLEMENTATION-02 · registro de intentos (2026-11-07)

Coste total del ciclo: $0,102742 en 26 llamadas. Otras 2 llamadas no salieron: JSON de entrada mal formado en el puente, sin reintento ni coste.

## T052-A1

| Campo | Valor |
|---|---|
| `A1_PRODUCT_BLOCKS_PREVIOUSLY_APPROVED` | 1 |
| `A1_APPROVED_BLOCKS_STILL_APPLY_CLEANLY` | 1 |
| `A1_FAILURES_CONFINED_TO_TEST_HARNESS` | 1 |
| `A1_TEST_FAILURE_ROOT_CAUSE` | Brief sin firma real: el ejecutor inventó imports, firma y variable |
| `A1_EXISTING_APPROVED_PRODUCT_BLOCKS_APPLIED` | 1: los 9 bloques de producto, sin modificar |
| `A1_NEW_TECHNICAL_BOUNDARY_PROVEN` | 0: la prueba de `verify` era el objeto de los tres intentos agotados |

`T052_A1 = BLOCKED_BY_RETRY_POLICY`: no se llamó a DeepSeek para esa prueba. `audit_backup_event` queda sin prueba propia de CLI; lo ejercen el ledger y las mutaciones de la copia programada, pero **esa función de auditoría por CLI no tiene prueba dirigida**. Deuda: T052-A1-CLI-AUDIT-TEST.

## Fronteras

| Subtarea | Intentos | Rechazos | Coste | Resultado |
|---|---|---|---|---|
| T052-B1 persistencia | 1 | 0 | $0,007723 | Aplicado |
| T052-D1 núcleo puro | 1 + 2 | 2 | $0,016211 | Primer intento: filtro de retención invertido, borraba copias recientes. Cerrado |
| T052-C1 copia programada | 1 + 2 | 2 | $0,031431 | Presupuesto agotado y cerrado en producción; dos pruebas pendientes pasaron a T052-C3 |
| T052-C3 reloj de duración | 1 + 1 | 1 | $0,000835 | `NEW_ROOT_CAUSE`: duración contra reloj lógico, negativa, perdía la copia al cerrar |
| T052-C2 copia manual | 1 + 1 | 1 | $0,008479 | Un `verify` fallido dejaba válida una copia ya validada |
| T052-D2 E/S de destino | 1 + 2 | 2 | $0,012961 | Cerrado |
| T052-B2 API | 1 + 2 | 2 | $0,006268 | Agotado con una prueba en rojo; ver T052-B3 |
| T052-B3 acceso real | 1 + 1 | 1 | $0,001030 | `NEW_TECHNICAL_BOUNDARY`: sesiones reales |
| T052-E interfaz | 1 + 2 | 2 | $0,016331 | Cerrado |
| T053 cliente PG18 | 1 | 0 | $0,000758 | Aplicado |
| T052-F1 guardas | 1 | 0 | $0,000396 | Aplicado |
| T052-F2 mutantes UI | 1 | 0 | $0,000319 | Aplicado |

## Desviaciones de proceso, declaradas

1. **Paralelismo.** T052-C2 se lanzó mientras T052-D2 seguía activa: rompe «nunca en paralelo». Cada una tuvo su EGRESS. No se repitió.
2. **Commit en rojo.** `f52e111` se confirmó con `test_sin_sesion_responde_401` fallando: el comando encadenado no condicionó el commit al resultado. Lo reparó `83b0b9e`. No se reescribió la historia.
3. **Regresión no detectada a tiempo.** `867dea7` cambió el tick y `test_spec047_architecture` no se corrió hasta la suite completa. Lo reparó `6a6059f`.
4. **Secreto de prueba en brief.** Un brief de T052-C1 llevaba un valor de clave ficticio, contra el §7. Se retiró: el valor se genera con `secrets.token_hex`. No era una clave real.
5. **Frontera T052-D2.** Las pruebas de destino y retención formaban parte del intento rechazado de T052-C1. Se separaron como frontera de E/S porque ejercen disco y no el flujo; es un criterio discutible, declarado aquí.
