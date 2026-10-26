# Incidente de EGRESS EGR-MFA-01 — reconciliación (2026-10-26)

No se registra aquí el valor. Se identifica por su huella: SHA-256 que empieza por `e497dff5`, 18 caracteres. Las búsquedas leen el
valor del repositorio dentro de un proceso local y solo imprimen rutas y recuentos.

## Hechos

| Pregunta | Respuesta medida |
|---|---|
| WHAT_SECRET_WAS_EXPOSED | La contraseña SINTÉTICA de las identidades de QA (valor por defecto de `KONTROL_E2E_PASSWORD` en `qa/pg-e2e-seed.py` y sus hermanos) |
| WHETHER_SYNTHETIC | Sí. Es un dato de prueba del repositorio desde `342882a`; nunca fue la credencial de una persona ni de producción |
| WHETHER_IT_WAS_EVER_VALID | Sí, solo en entornos de QA: bases E2E efímeras (se siembran en cada corrida y se eliminan al acabar), bases de las pruebas de backend (SQLite en memoria o esquemas temporales de PostgreSQL que el arnés elimina) y la antigua base manual `kaud`, que ya no existe |
| WHAT_ENVIRONMENT_IT_COULD_ACCESS | El servidor PostgreSQL de QA (`localhost:55432`, solo en el equipo) y los procesos de prueba. Producción no: el valor no aparece en `resources/backend/app` y las instalaciones reales crean la cuenta administradora con la contraseña que elige quien instala |
| WHETHER_IT_REMAINS_VALID | En entornos persistentes **no**. Se comprobó en solo lectura con `verify_password` del producto sobre todas las bases del servidor de QA (`postgres` y `ktest`: no queda ninguna tabla `users`) y no hay ficheros SQLite locales. Desde TM-EG1 la E2E canónica ya no lo siembra: cada corrida genera su propia contraseña con `secrets` e ignora la heredada (prueba `test_e2ecorrida_34`). Solo sigue sirviendo como dato fijo de las pruebas de backend, dentro de bases que se crean y se destruyen en cada prueba |
| WHERE_IT_WAS_SENT | A la API de DeepSeek (proveedor externo), dentro de dos encargos de este ciclo (TM-9b y el lote TM-9d-6a), antes de que empezara el enmascarado |
| WHETHER_IT_EXISTS_IN_LOGS/EVIDENCE | **En el proveedor:** fuera de nuestro control; lo conserva según su propia política.<br>**En las transcripciones locales de Claude Code:** está en 20 trazas de los puentes (`~/.claude/projects/…/subagents`, solo locales), que retiene la propia herramienta.<br>**En `qa/e2e-runs/` (fuera de Git):** había 623 artefactos (trazas de Playwright de 9 corridas); se purgaron y quedan 0.<br>**En el scratchpad de la sesión:** había 159 copias de ficheros del repositorio; se purgaron y quedan 0.<br>**En `qa/backend-runs/` y `qa/certificaciones/`:** 0.<br>**En la salida local de esta sesión:** se mostró dos veces (un filtro de redacción incompleto y un `grep` de un fichero de pruebas); no salió del equipo |
| WHETHER_IT_WAS_ROTATED / INVALIDATED | Rotado para la E2E canónica (contraseña por corrida, TM-EG1). Destruido en toda base donde llegó a ser válido: las bases efímeras se eliminan en cada corrida y el manifiesto lo verifica (`limpieza.base = ELIMINADA`) |
| WHETHER_ANY ACCOUNT USING IT STILL EXISTS | Ninguna cuenta persistente |

## Métricas

| Métrica | Valor | Nota |
|---|---|---|
| EGRESS_INCIDENT_COUNT | 1 | Dos mensajes del mismo incidente |
| EGRESS_INCIDENT_SYNTHETIC | 1 | |
| EXPOSED_CREDENTIAL_STILL_VALID | 0 | En entornos persistentes |
| EXPOSED_CREDENTIAL_ROTATED_OR_DESTROYED | 1 | |
| EXPOSED_CREDENTIAL_IN_GIT_ADDED_BY_INCIDENT | 0 | |
| EXPOSED_CREDENTIAL_IN_GIT (dato de prueba previo) | **1** | Ver la contradicción con el objetivo, más abajo |
| EXPOSED_CREDENTIAL_IN_EVIDENCE (local, no rastreada) | 0 | Tras la purga |
| CURRENT_SECRET_EXPOSURE | 0 | |
| HISTORICAL_EGRESS_INCIDENT | 1 | |
| EGRESS_INCIDENT_CLOSED | 1 | |

### Contradicción con el objetivo `EXPOSED_CREDENTIAL_IN_GIT = 0`

El valor estaba en Git antes del incidente y el incidente no lo añadió. Lo contienen hoy 86 ficheros rastreados: 64 de pruebas y de QA, y
22 registros de evidencia de ciclos anteriores. Además está en la historia desde `342882a`.

Dejarlo en 0 exigiría dos cosas:
- reescribir todos esos ficheros, incluida evidencia certificada de otros ciclos;
- reescribir la historia, que es destructiva y está prohibida.

No da seguridad adicional, porque el valor no abre ningún entorno persistente. Queda como deuda **TEST-FIXTURE-PASSWORD-LITERAL** (LOW): un
ciclo de QA puede sustituir el literal de las pruebas de backend por un valor generado en `conftest`. La dueña puede priorizarla o
cerrarla.

## Medidas para que no se repita

- Desde TM-9d los encargos enmascaran ese valor como `<CONTRASENA_DE_SIEMBRA>` o `<SEMILLA_HISTORICA>`, y el aplicador lo restituye en
  local con `--desenmascarar`.
- Antes de cada llamada se comprueba por programa que el mensaje compuesto no contiene el valor.
- La contraseña de la E2E canónica ya no es un valor fijo.
