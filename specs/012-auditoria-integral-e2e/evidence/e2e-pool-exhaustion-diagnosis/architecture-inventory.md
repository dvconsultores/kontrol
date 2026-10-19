# Inventario de arquitectura (lectura del código en `5b8f86b`)
| Campo | Valor |
|---|---|
| ENGINE_FACTORY | `app/core/database.py::get_engine` — `create_engine(db_url, pool_pre_ping=True, pool_recycle=1800, future=True)` |
| POOL_CLASS · POOL_SIZE · MAX_OVERFLOW · POOL_TIMEOUT | `QueuePool` · 5 · 10 · 30 s (valores por defecto de SQLAlchemy 2.0.36; medidos en la sonda) |
| SESSION_FACTORY | `get_session_factory()` — `sessionmaker(expire_on_commit=False, autoflush=False)` |
| REQUEST_SESSION_OWNER | `get_db()`: dependencia síncrona con `yield`, una sesión por petición, `db.close()` en `finally` |
| MIDDLEWARE_SESSION_OWNER | `app/main.py::_get_mode`: sesión propia (`get_session_factory()()`), `current_mode(db)`, `db.close()` |
| Punto crítico | `app/core/middleware.py::LicenseMiddleware.dispatch` es **`async def`** y llama a `self._get_mode()` **síncrono** en cada escritura no exenta (POST/PUT/PATCH/DELETE): espera la conexión del pool **en el hilo del bucle de eventos** |
| SESSION_CLOSE_PATH | la salida de `get_db` la ejecuta FastAPI 0.115.6 desde el bucle (`contextmanager_in_threadpool`): **necesita el bucle libre** para devolver la conexión |
| TRANSACTION_BOUNDARY | la sesión de la petición se queda con su conexión desde la primera consulta (autenticación) hasta `close()` |
| NESTED_DB_ACQUISITIONS | 0: la consulta del middleware termina y libera antes de `call_next` (medido: 1 conexión simultánea por petición) |
| Otros accesos síncronos a la base en `async def` | solo `_lifespan` (arranque) y `LicenseMiddleware.dispatch` (búsqueda por AST en `app/`) |
| Servidor E2E | un proceso `uvicorn app.main:app` (`qa/e2e_corrida.py`), threadpool anyio 4.14.2 de 40 hilos; Playwright `fullyParallel`, workers por defecto (la mitad de 12 núcleos) |
| Carga documental | `documents/service.py`: la petición ya autenticada (conexión prestada) ejecuta `scanner.scan()` (clamscan: 6-33 s medidos en ciclos anteriores) **con la conexión retenida** |
| POOL_TELEMETRY_AVAILABLE | no en producto; la sonda registró `connect/checkout/checkin/close/invalidate` con eventos de SQLAlchemy en su propio motor |
