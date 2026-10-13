# Diseño de la espera

| Registro | Valor |
|---|---|
| Primitiva | `expect.poll` de Playwright (auto-reintento) sobre una **lectura clasificada** de los controles exactos: `leerEstadoDeEmpresa(page, compuerta)` → `{estado, activar, desactivar, activa, compuerta, cargando, botones}`; `esperarEstadoDeEmpresa(page, compuerta, timeout)` repite la lectura hasta `ACTIVA | INACTIVA | COMPUERTA` y **devuelve esa misma lectura** |
| Sin TOCTOU | la decisión (`if lectura.estado === …`) usa la lectura que satisfizo la espera; no hay relectura instantánea posterior para decidir. La comprobación de `exact` («todo lo que alcanza `Activar` se llama Activar») sigue después: no decide nada y con la pantalla pintada es estable |
| Valor del poll | `ACTIVA`/`INACTIVA`/`COMPUERTA` cuando es determinable; si no, `"NO_LISTA: activar=… compuerta=… activa=… desactivar=… cargando=… botones=[…]"` o `"AMBIGUO: …"`: al agotar el tiempo, Playwright imprime el último valor recibido → el diagnóstico se conserva (FR-HE-008) y mejora (añade `cargando`) |
| `CURRENT_EXPECT_TIMEOUT` | 5 000 ms (defecto de Playwright; `config.expect` sin definir, lo exige el contrato del arnés) |
| `CURRENT_ACTION_TIMEOUT` / `CURRENT_NAV_TIMEOUT` | sin límite global (defecto 0); el ayudante usaba `15000` en sus propias esperas (`waitForURL`, postcondición, compuerta) |
| Tiempo de la espera nueva | **15 000 ms** = `ESPERA_DEL_AYUDANTE_MS`, el mismo que el ayudante ya concedía; ningún timeout sube |
| `networkidle` | se retira del ayudante: no es autoridad de preparación (FR-HE-018) |
| `waitForTimeout` / sleep / bucle manual / reintentos / reload | 0 |
| Estado AMBIGUO | se sigue esperando (puede ser un instante de pintado) y, si persiste al agotar el tiempo, falla con el diagnóstico (FR-HE-006/007) |
| Postcondición | intacta: `desactivar` 1, `activa` 1, `activar` = candidatas − 1 (o 0) |
