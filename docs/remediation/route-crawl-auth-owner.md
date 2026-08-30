# PROPIEDAD DEL FALLO — `route-crawl` / `/auth/refresh`

Fecha: 2026-08-30 · Diagnóstico previo a cualquier cambio de código

## El fallo

`e2e/route-crawl.spec.ts` falla al recorrer el menú: la consola acumula entre 3
y 5 errores `401 (Unauthorized)`. Las peticiones que los producen son
`POST /api/v1/auth/refresh` —no peticiones de negocio— al recargar
`/organizacion/almacenes` y `/tesoreria/maestros`.

Ninguna ruta de la Spec 046 aparece. **No es un defecto de 046.**

## Capa y módulo

| Dimensión | Valor |
|---|---|
| Capa | Frontend · restauración de sesión |
| Módulo | `src/app/contexts/AuthContext.tsx` + `src/api/client.ts` |
| Contraparte backend | `app/modules/identity_access/service.py::rotate_session` |
| Naturaleza | Carrera entre dos renovaciones concurrentes con token de un solo uso |

## Spec propietaria

**Spec 002 · Seguridad, autenticación y sesiones.**

Justificación, no suposición:

| Evidencia | Fuente |
|---|---|
| `ADR-004 · Autenticación y almacenamiento de sesión` está asignado a las Specs **002, 003, 055** | `docs/governance/architecture-decision-register.md:21` |
| La baseline sitúa «tabla `Session` con hash de refresh, **rotación y revocación**» en su §6 «Autenticación y sesión», bajo `ADR-004` | `KONTROL_ARCHITECTURE_BASELINE.md:106-112` |
| El código de rotación vive en `app/modules/identity_access/` | — |
| 003 gobierna usuarios/roles/alcance, no el ciclo del token | `56-specs-gap-analysis.md` |
| 055 gobierna hardening, no la mecánica de sesión | ídem |

**No es de 005** (navegación) aunque se manifieste al navegar: la navegación
solo expone la carrera, no la causa. **No es de 006** (observabilidad): el 401
es real, no un artefacto de instrumentación. **No es de 054** (QA): el test es
correcto y detecta un defecto verdadero.

## Por qué no es un fallo de la prueba

La prueba recarga la página con `page.goto()`, que es exactamente lo que hace un
usuario al pulsar F5 o al abrir un enlace directo. El access token vive en
memoria por diseño (`ADR-004`), de modo que **toda** recarga dispara la
restauración de sesión. La prueba reproduce el camino real; el 401 lo produce la
aplicación.

Clasificación: **`ROOT_CAUSE = APPLICATION`**, no `TEST_INFRASTRUCTURE`.
