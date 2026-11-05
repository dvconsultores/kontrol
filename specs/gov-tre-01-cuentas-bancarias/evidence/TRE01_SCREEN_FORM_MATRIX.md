# GOV-TRE-01 · TRE01_SCREEN_FORM_MATRIX (ficha de pantallas y formularios)

TRE-01 tiene cuatro pantallas y estos formularios de escritura: alta de banco, edición en línea del banco, alta de cuenta, edición del borrador, vínculo del acto, alta de autorización, fin de autorización y motivo de inactivar, reactivar o cerrar. La activación es una acción sin formulario.

| Campo | S1 · Cuentas bancarias | S2 · Nueva cuenta | S3 · Cuenta | S4 · Bancos |
|---|---|---|---|---|
| SCREEN_ID | `CuentasPage` | `NuevaCuentaPage` | `CuentaPage` + `AutorizadosCuenta` | `BancosPage` |
| BUSINESS_GOAL | ver qué cuentas tiene el ente, en qué estado y con cuántos autorizados | registrar una cuenta en borrador | responder qué cuenta es, quién está autorizado, bajo qué acto, desde cuándo y qué cambió; operar su ciclo de vida | mantener el catálogo de bancos del ente |
| MENU_PATH | Gobierno · Tesorería › Cuentas bancarias (`/gobierno/tesoreria/cuentas`) | S1 › «Nueva cuenta» (`/gobierno/tesoreria/cuentas/nueva`) | «Abrir la cuenta CB-…» en S1 (`/gobierno/tesoreria/cuentas/:cuentaId`) | Gobierno · Tesorería › Bancos (`/gobierno/tesoreria/bancos`) |
| ACTOR | Tesorería, Control Interno, consulta | Tesorería | Tesorería; quien activa | Tesorería |
| FIELDS | indicadores vigentes, borradores, inactivas, cerradas; filtros estado, banco, moneda, cargo; tabla: código, denominación, banco, tipo, moneda, número enmascarado, estado, autorizados | C02 denominación, C03 banco, C04 tipo, C05 número, C06 moneda, C07 desde, C08 hasta | C01–C13 en datos; acto; A01–A06 en autorizados; historia | B01 código, B02 nombre, B03 estado |
| ACTIONS | Nueva cuenta, Bancos, abrir cuenta, filtrar por indicador | Registrar cuenta, Cancelar | Ver y ocultar número, Editar borrador, Vincular acto, Autorizar un cargo, Terminar, Activar, Inactivar, Reactivar, Cerrar | Registrar banco, Editar, Guardar, Cancelar, Inactivar, Activar |
| STATES | sin acceso, cargando, módulo no habilitado, 403, error con reintento, vacío, vacío con filtros; «Acto sin efecto», «Fuera de vigencia» | sin acceso, cargando, sin bancos activos, errores de campo, error general | sin acceso, cargando, no encontrada, error con reintento, aviso de acto sin efecto, sin autorizados, fuera de vigencia, cargo no vigente, conflicto de versión, faltantes para activar, conflicto SoD, cerrada | sin acceso, cargando, error, vacío, conflicto de versión |
| PERMISSIONS | `gobierno_cuentas:view`; «Nueva cuenta» con `:manage` | `:manage` | `:view`; número, edición, acto y autorizados con `:manage`; activar, inactivar, reactivar y cerrar con `:activate` (MFA) | `:view`; escritura con `:manage` |
| DOCUMENTS | — | — | el acto vincula a DOC-02 y su documento vive allí | — |
| AUDIT | — | GOV_BANK_ACCOUNT_CREATED | _UPDATED, _ACT_LINKED, _ACTIVATED, _DEACTIVATED, _REACTIVATED, _CLOSED, _NUMBER_VIEWED, GOV_BANK_AUTHORIZATION_ADDED, _ENDED | GOV_BANK_CREATED, GOV_BANK_UPDATED |
| ERRORS | 403, 422 | 422 GOV_BANK_ACCOUNT_INVALID, 409 _DUPLICATE, _CONFLICT, 403 | 404, 409 _STALE, _INVALID_STATE, _NOT_READY, _ACT_WITHOUT_EFFECT, _AUTHORIZATION_DUPLICATE, GOV_SOD_CONFLICT, 422, 428 | 409 GOV_BANK_CODE_DUPLICATE, _STALE, 404, 422, 428 |
| RESPONSIVE | indicadores y filtros en rejilla; tabla en región con desplazamiento; 320 px sin desbordar | campos apilados | datos en rejilla 1/2; tablas en región | formulario apilado; tabla en región |
| ACCESSIBILITY | h1, caption, región «Tabla de cuentas bancarias», `aria-pressed`, `role=search`, enlaces con nombre | rótulos «(obligatorio)», `aria-invalid`, ayuda por campo | h1 «Cuenta CB-…», regiones con nombre, `role=alert`, `scope=col` | región «Tabla de bancos», botones con el nombre del banco |
| E2E | TRE-E2E-01, 02, 03 (axe 1280/768/320) | TRE-E2E-01, 02, 03 | TRE-E2E-01, 02, 03 | TRE-E2E-01, 03 |

Respuestas de S3 a las preguntas del encargo: qué cuenta (código y denominación), banco, tipo, moneda, si está activa (estado y vigencia), quién está autorizado (tabla de cargos), bajo qué acto (acto habilitante y acto de alta), desde cuándo (autorizado desde), qué cambió (historia).

SCREEN_FUNCTIONAL_OMISSIONS = 0 · MISSING_REQUIRED_FIELDS = 0.
