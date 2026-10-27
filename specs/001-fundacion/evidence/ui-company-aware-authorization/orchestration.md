# UI COMPANY-AWARE AUTHORIZATION — orquestación Claude + DeepSeek (2026-10-27)

**Reparto del trabajo**
- **Claude:**
  - diseñó el delta `spec003-ui-company-aware-authorization-delta.md` (AD-1..AD-8), la matriz de superficies y el registro de pantallas;
  - generó los 84 encargos por pantalla (TF-8) a partir del inventario de llamadas y del catálogo del backend, y comprobó el EGRESS de cada
    encargo con un guion antes de enviarlo;
  - auditó cada parche en una copia fuera del árbol (diff, comprobación de sintaxis y, para rutas calculadas, resolución contra el catálogo),
    aplicó solo lo aprobado, tal cual, y verificó con las suites, sondas y mutaciones fuera del árbol.
- **DeepSeek:** escribió todo el código de producto, todas las pruebas (backend, vitest y E2E) y la documentación de producto (ADR-018 y
  contrato). Implementadas por Claude: **0**.

**Correcciones de formato de Claude** (OD-ORCH-01): ninguna sobre contenido. Desviaciones de formato del ejecutor, aplicadas sin tocar su
contenido: bloques sin línea de ruta en respuestas de varios ficheros (asignada por el orden del encargo, `--rutas`), vallas ``` alrededor de
los bloques (ignoradas por el aplicador) y un bloque sin cambio (SEARCH = REPLACE, TF-8.83: sin efecto).

**Ningún encargo llevó `.env`, claves, tokens, rutas personales ni datos reales** (EGRESS_OK en las 155 llamadas). La clave de firma que
necesitó la comparación de OpenAPI se generó al vuelo, no salió del equipo y no viajó a DeepSeek.

| Tarea | Contenido | Modelo | Auditoría | Reintentos |
|---|---|---|---|---|
| TA-B1 | Pruebas backend en rojo UIA-B01..07 | pro | c0: aserción de cuenta exacta frágil → c1 sin duplicados → PASS | 1 |
| TA-F1 | E2E en rojo E2E-UI-SCOPE-01..09 | pro | c1 encabezado y 320 px; c2: `getByText` ambiguo (03) y revocación de sesión por cambio de clase de política al quitar un rol (09, comportamiento correcto del producto) → dos roles → PASS | 2 |
| TB-1..4 | `tenant_wide_capabilities`, catálogo de operaciones, endpoints, instantáneas y su deriva, `CATALOGO_DE_PERMISOS` | pro / flash | TB-1 c0: ruff B023 (cierre) → función de módulo → PASS | 1 |
| TF-1 | Cliente: aviso de denegaciones | flash | c0: argumentos invertidos y doble llamada en la prueba → PASS | 1 |
| TF-2 | Resolución pura y vitest | pro | c0 y dos reintentos con defectos de algoritmo y de tipos → **dividida** en TF-2a (tipos) y TF-2b (prueba) → PASS | 2 + división |
| TF-3 | Proveedor `useAutoridad` | pro | c0: campos de catálogo inventados en la prueba → PASS | 1 |
| TF-4 | `Autorizado`, `RutaAutorizada`, `DenegacionDeAutoridad` | pro | c0: import de módulo equivocado y aserción de CARGANDO ausente → PASS | 1 |
| TF-5 | Registro de pantallas, router, guarda e inventario | pro | SEARCH inexistente y código muerto → reintento 2 (último) del bloque del router PASS; TF-5b ata capacidades al catálogo del backend | 2 |
| TF-6 / TF-7 | Menú y los 13 consumidores de `hasPermission` | flash | TF-6 c1: pruebas del menú con la visibilidad vieja; TF-7c retira `PermissionGuard` → PASS | 1 |
| TF-8.02..8.84 | Puertas de acciones, una pantalla por llamada (83; la 8.01 la cubre TF-7b) | flash / pro | **8 reintentos** en 7 pantallas: 8.08 (ocultaba el selector: nace la regla 5), 8.50 (solo imports), 8.63 (hook inexistente), 8.66 (hook sin import), 8.77 (diff unificado; y r2 por AD-6, ver abajo), 8.78 (JSX que no parsea), 8.80 (bloqueaba un control de selección) | 8 |
| TF-8L.01..18 | Limpieza: imports y variables sin uso, `disabled` redundantes, imports fundidos; 8L.17/18 aplican AD-6 | flash | 18/18 PASS al primer intento (diff estricto, sin `-w`) | 0 |
| TF-8T.01..05 | Pruebas de pantalla sin `AutoridadProvider` (23 fallos, una causa) | flash | 5/5 PASS | 0 |
| TF-8z | Prueba de cobertura de puertas | pro | PASS; dos mutantes muertos | 0 |
| TF-9a..d | Texto de alcance de `/auditoria` y sus pruebas | flash | 4/4 PASS | 0 |
| TF-E1 | E2E-SCOPE-10 al comportamiento nuevo | pro / flash | c0: dos aserciones de localizador sin `await` (falso verde; **el encargo de Claude las escribía así**); r1 PASS de auditoría, pero en la corrida el filtro de peticiones (también del encargo) casaba con la navegación y los módulos de Vite → r2 PASS | 2 |
| TF-E2 | Crawler: esperar el menú completo | flash | PASS | 0 |
| TF-M1 / TF-M2 | Pruebas que matan los mutantes R6, P3 y P6 | flash / pro | PASS; 3/3 muertos | 0 |
| TB-R1..3 | Tres guardas del backend que el ciclo tocó (ruta `.venv` en un mensaje, inventario de sondeos con la renovación de 60 s, catálogo del setup en constante) | flash | 3/3 PASS | 0 |
| TD-1 / TD-2 | ADR-018 y contrato de la API | flash | PASS | 0 |

**Desviación de Claude, corregida:** aceptó en TF-8.77 r1 y en la limpieza dos botones deshabilitados por autoridad, contra AD-6 (lo no
autorizado se oculta). Se detectó al redactar el ADR-018 y se corrigió con TF-8.77 r2 y TF-8L.17/18. Los campos de datos de
PoliticaDetalle siguen deshabilitados a propósito: muestran un valor (ADR-018 (d)).

**Coste del ciclo:** 155 llamadas (47 pro, 108 flash) · 475 317 tokens de entrada · 193 616 de salida · **0,2371 USD**.

**Acumulado de la sesión:** 469 llamadas · 1,3054 USD. El coste del puente (Sonnet) lo factura la sesión de Claude Code.

**Rechazos (AUDIT_REJECT):** 23 en total (TA-B1 1, TA-F1 2, TB-1 1, TF-1 1, TF-2 3, TF-3 1, TF-4 1, TF-5 2, TF-6 1, TF-8 8, TF-E1 2),
todos con motivo concreto y contexto completo en el reintento; 3 de ellos atribuibles a Claude: los dos de TF-E1 (el encargo) y el de
TF-8.77 r1 (la auditoría lo había aceptado). Ninguna tarea superó los dos reintentos; TF-2 se dividió tras agotarlos.

**Lecciones para los encargos:**
- Un control que SELECCIONA el valor del que depende la ruta nunca va dentro de la puerta (regla 5, nacida en TF-8.08): segmento fijo `_`.
- En Playwright, toda aserción sobre un localizador lleva `await`; un encargo que la escribe sin él produce un falso verde.
- Un filtro de peticiones en E2E mira la API (`/api/v1/…`), no la ruta de la página: Vite sirve la navegación y los módulos con el mismo nombre.
- El revisor comprueba la sintaxis del fichero parcheado antes de aplicar (TSX con TypeScript, Python con `ast`).
- Una puerta nueva rompe las pruebas de pantalla que no montan el proveedor; se prevé el mock en el mismo encargo.
