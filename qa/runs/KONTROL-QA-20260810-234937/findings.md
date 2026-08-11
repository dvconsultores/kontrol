# REPORTE DE HALLAZGOS — RUN `KONTROL-QA-20260810-234937`

Cada hallazgo: ID · título · severidad · módulo · ruta · pasos · esperado · obtenido · impacto · causa probable (sin modificar código) · recomendación.

---

## KQA-001 — API backend caída (502 Bad Gateway) impide el login y toda operación

- **Severidad:** BLOCKER
- **Módulo:** Infraestructura / Backend (nginx → FastAPI)
- **Ruta:** `/api/v1/*` (setup/status, license/status, auth/refresh, auth/login, organization/companies)
- **Usuario:** Administrador Global
- **Precondiciones:** Navegar a https://kontrol.globaldv.net/login
- **Pasos:**
  1. Abrir la URL. El SPA carga.
  2. En consola: `Failed to load resource ... 502` para `/api/v1/setup/status`, `/api/v1/license/status`, `/api/v1/auth/refresh`.
  3. Intentar login con credenciales QA: botón queda "Iniciando sesión…" y muestra "No fue posible iniciar sesión / No fue posible completar la operación".
  4. Reproducción por API directa: `POST /api/v1/auth/login` → `502 Bad Gateway` (openresty).
  5. Reintentos espaciados (3× en 18 s y a los ~15 min) → siempre 502.
- **Esperado:** 200 con token / respuestas JSON de la API.
- **Obtenido:** 502 Bad Gateway en toda la API. Login imposible.
- **API / HTTP status:** 502 en todos los `/api/v1/*`. Request ID no disponible (el 502 lo emite nginx, no la app).
- **Datos usados:** credenciales QA (no se reproducen aquí; redactadas como ********).
- **Screenshot:** captura del login y del error de consola (evidencia en conversación; en esta pasada el backend no permite capturas autenticadas).
- **Impacto:** 100 % de los flujos funcionales autenticados bloqueados (empresa, sucursales, almacenes, compras, ventas, facturación, CxC, CxP, tesorería, reportes, auditoría, permisos, seguridad).
- **Causa probable (sin modificar código):** el contenedor del backend no está alcanzable desde nginx (caído / crash-loop / red / o despliegue fallido por watchtower tras los últimos pushes). No es un fallo del frontend.
- **Recomendación:** revisar estado del contenedor backend, logs de la app y de nginx; restaurar el upstream; verificar que watchtower no esté dejando la imagen en estado roto. Re-ejecutar la prueba funcional una vez restaurado.

---

## KQA-002 — `/health/live` y `/health/ready` devuelven el SPA (200 HTML), no la salud del backend

- **Severidad:** HIGH (afecta observabilidad y el diagnóstico; relacionado con KQA-001)
- **Módulo:** Infraestructura (nginx)
- **Ruta:** `/health/live`, `/health/ready`
- **Pasos:** `GET /health/live` → 200 con `<!doctype html>...` (index.html del SPA).
- **Esperado:** 200 JSON de health del backend (p. ej. `{"status":"ok"}`).
- **Obtenido:** 200 con el HTML del SPA. El health check real no es alcanzable por esa ruta.
- **Impacto:** los sondeos de salud (watchtower/uptime) no detectan la caída del backend; explica que la instancia siga "viva" con la API caída.
- **Causa probable:** en nginx, `/health/*` cae en el `try_files ... /index.html` de la SPA en lugar de enrutarse al upstream `/api` (falta una ubicación explícita para health antes del fallback SPA).
- **Recomendación:** añadir una regla nginx que sirva `/health/live` y `/health/ready` desde el backend (o un static check) ANTES del fallback SPA.

---

## Observaciones de consola (sin severidad propia, complementan)

- En cada carga de `/login` se registran errores 502 de red (setup/status, license/status, auth/refresh). Es coherente con KQA-001.
- Sin otros errores de consola (JS/React) en la página pública.

## Notas
- La credencial de prueba se utilizó únicamente como secreto de ejecución; no se guardó en repositorio, logs, screenshots ni reportes (redactada como ********).
- No se modificó ningún dato productivo.
