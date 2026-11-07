# CTL-10 · conciliación de reintentos del ciclo anterior

Norma ratificada: máximo 2 reintentos semánticos por subtarea real. Una subtarea nueva exige NEW_ROOT_CAUSE o NEW_TECHNICAL_BOUNDARY. Cambiar el identificador no reinicia el contador.

**Método:** se revisaron los encargos reales del ciclo, por función, y la causa declarada en cada ronda. `ATTEMPT_LOG.md` se conserva intacto. Su línea `MAX_SEMANTIC_RETRIES_PER_SUBTASK_OBSERVED = 2` contaba por subtarea nominal; con esta norma queda **superada**.

**PREVIOUS_CYCLE_RETRY_POLICY_COMPLIANCE = PARTIAL.** Producto certificado: no se revierte nada.

| Subtarea real | Rondas | Causa por ronda | Clasificación |
|---|---|---|---|
| `test_sg07` y `test_sg08`: bloqueo con hallazgo real | S, S3, S4, S4b, S5 | La misma: control y hallazgo del cierre mal construidos; S5 solo la encapsuló en un ayudante | **RETRY_POLICY_VIOLATION** |
| `test_ga07`, `ga08`, `ga09`, `ga18`: ejercicio del programa | F, S3, S4 | La misma: el programa exige ejercicio futuro | **RETRY_POLICY_VIOLATION** |
| `test_pp03`: correlativo por empresa | S, S3, S4 | La misma: contraste del número entre empresas | **RETRY_POLICY_VIOLATION** |
| CIE-E2E-03 | T032, T032b, T032s2, T032s2b | Mismo origen: rutas y firmas inventadas, repartidas al dividir | **RETRY_POLICY_VIOLATION** |
| `test_cc04` | S, S3, S4 | Distintas: verbo PATCH, recogida de hilos, MFA dentro del hilo | LEGITIMATE_SPLIT |
| `test_bl06` | S, S4, S4b | Distintas: activación, política sin control, versión descartada | LEGITIMATE_SPLIT |
| CIE-E2E-02 | T032, T032b, T032s1b, T032s1c | Distintas: faltaba el programa; después, retiraba otra política. T032s1 no cuenta: el encargo salió sin texto | LEGITIMATE_SPLIT |
| T015 | T015, F1, T015c | Distintas: 428 y SoD; después, pruebas vacías | LEGITIMATE_SPLIT |
| T019 y T020 | T019, T019b, F1 | Distintas: montaje; después, import por encargo ambiguo | LEGITIMATE_SPLIT |
| `test_ga16`, `ga17`, `sg01`, `pp05`, `sg03`, `bl03`, `bl04` | hasta 2 con causa común | Dentro del límite, o con causa nueva medida | LEGITIMATE_SPLIT |

**Causa de las violaciones:** se dividió por suite y función para seguir corrigiendo. Parte del daño vino de encargos con datos incompletos, responsabilidad de Claude.

**Medida desde este ciclo:** el contador va por subtarea real y unidad de comportamiento. Cada subtarea nueva declara en `ATTEMPT_LOG` su causa o frontera nueva.

PREVIOUS_CYCLE_RETRY_POLICY_RECONCILED = 1.
