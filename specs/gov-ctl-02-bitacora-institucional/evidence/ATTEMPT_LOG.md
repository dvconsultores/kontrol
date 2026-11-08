# CTL-02 · ATTEMPT LOG

Presupuesto: MAX_DEEPSEEK_CALLS_THIS_CYCLE = 12; MAX_TEST_ONLY_DEEPSEEK_CALLS = 2.
ALEMBIC_HEAD_BEFORE = 0077_gov_org06_identidad
ENTRY_HEAD = 69c6b8a21525e04ad31688f544221456db36b81c
Llamada 1/12 · T001 ATTEMPT enviado
T001 ATTEMPT AUDIT_PASS: 5 pruebas CTL-02 verdes en PG; ruff --fix ordeno imports y retiro un import sin uso (solo formato, declarado)
Llamada 2/12 · T002 ATTEMPT enviado
T002 ATTEMPT AUDIT_REJECT: Session sin importar (omision del encargo); AttributeError con funcionario None en SIN_VINCULO; tipos dict[UUID, str]; validar accion carga funcionarios y unidades
Llamada 3/12 · T002 RETRY_1 enviado
T002 RETRY_1 AUDIT_PASS: 4 pruebas de API verdes en PG
Llamada 4/12 · T003 ATTEMPT enviado (lista, detalle, menu y Vitest; incluye T004 del plan)
T003 ATTEMPT AUDIT_REJECT: respuesta incompleta, 1 de 8 entregas, formato no pedido
Llamada 5/12 · T003 RETRY_1 enviado
T003 RETRY_1 aplicado (extraccion literal por cabeceras FILE). Producto correcto; AUDIT_REJECT en pruebas: 4 selectores ambiguos, waitFor sin usar
Llamada 6/12 · T003t RETRY_2 enviado (pruebas 1/2)
T003t aplicado: 6/7; queda un selector ambiguo (Unidad Uno)
SUBTAREA NUEVA T003b: NEW_ROOT_CAUSE=1 (auditoria manual: enlace al objeto compara capacidad con 'empresa' y nunca aparece; motivo sin autoridad como codigo crudo; vistas sin acceso fuera de PageContent; no-op .then)
Llamada 7/12 · T003b ATTEMPT enviado
T003b ATTEMPT: producto y selector AUDIT_PASS (Vitest 7/7); bloque de pruebas nuevas AUDIT_REJECT: inventa server.use y renderizarConCapacidades, .catch da verde falso; no aplicado
Llamada 8/12 · T005 ATTEMPT enviado (pruebas 2/2)
T005 ATTEMPT AUDIT_PASS: BIT-E2E-01 chromium 1/1 con axe; Vitest 8/8; API 5/5
T005 sin mas llamadas. Validacion unica: backend dirigido PG 1212/0, Vitest 1430/1430, tsc, eslint, build, ruff, mypy 0 nuevos, OpenAPI 3 rutas nuevas 0 retiradas, migracion arriba-abajo-arriba
Convergencia: 0 hallazgos. Relevo UAT a 0c0356b, humo 1/1
CIERRE: 8 llamadas de 12; 2 de pruebas de 2; reintentos: T002 RETRY_1, T003 RETRY_1 y T003t; T003b producto con bloque de pruebas rechazado
