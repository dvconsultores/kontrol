# Diagnóstico externo de kontrol.globaldv.net (2026-11-06)

Solo GET, DNS y TLS; sin credenciales. `PRODUCTION_TOUCHED = NO`.

| Campo | Resultado |
|---|---|
| PROD_DNS_STATUS | OK, resuelve |
| PROD_TLS_STATUS | OK, Let's Encrypt, verificado, válido hasta 2027-01-01 |
| PROD_LOGIN_PAGE_STATUS | 200, el SPA carga |
| PROD_SETUP_STATUS_HTTP | 502 |
| PROD_API_STATUS | 502 en `/api/v1/setup/status`, `/license/status`, `/health`, `/health/live` |
| PROD_REVERSE_PROXY_STATUS | OK: openresty responde, redirige HTTP a HTTPS y sirve el SPA |
| PROD_BACKEND_REACHABLE | NO desde el proxy |
| PROD_CURRENT_BLOCKER | TLS_OK_PROXY_502 · BACKEND_UPSTREAM_UNREACHABLE |
| SERVER_ACCESS_REQUIRED | YES |

`/health`, `/health/live` y `/health/ready` devuelven 200 con el HTML del SPA: no prueban salud del backend. El mismo 502 se registró el 2026-08-11. La causa no es visible desde fuera.

**ACCESS_PURPOSE:** ver por qué el proxy no alcanza el backend.

**READ_ONLY_COMMANDS_NEEDED:** estado de los contenedores o servicios del backend; sus últimos registros, sin secretos; configuración del upstream de `/api`, sin modificarla; puertos en escucha; petición local al puerto del backend; espacio en disco y memoria.

**EXPECTED_EVIDENCE:** si el backend está detenido, reiniciando, en otro puerto o sin base de datos, y qué versión hay desplegada.
