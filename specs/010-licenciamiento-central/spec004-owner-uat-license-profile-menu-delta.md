# Spec 004 · Delta · OWNER-UAT-LICENSE-PROFILE-MENU-01: perfil Gobierno con cero superficie Enterprise en el menú

Spec dueña: 010 Licenciamiento central.
Encargo: «P1 — OWNER-UAT-LICENSE-PROFILE-MENU-01» (2026-11-16).
Entrada: e3f8412. GOVERNMENT_PROCESS_INCREMENT=0. MIGRATION_REQUIRED=0.

## 1. Observación de la dueña

En la pila UAT de e3f8412 (puerto 16973), la dueña activó la licencia de prueba solo-Gobierno y siguió viendo opciones Enterprise en el menú. OWNER_UAT_LICENSE_PROFILE=FAIL.

## 2. Reproducción

La pila 16973 ya no existía: su corrida se interrumpió al cerrarse la sesión (salida 130) y su base efímera se borró. Se reprodujo en una pila nueva de e3f8412 con la misma secuencia:
1. siembra y humo UAT;
2. FULL_ACCESS con licencia MIXTA real;
3. el mismo archivo solo-Gobierno (período 2028);
4. activación por la interfaz real, sin interceptar nada.

Evidencia saneada (sin firma, claves ni credenciales): `evidence/owner-uat-license-profile-menu/reproduccion-e3f8412.json`.

| Hecho | Valor |
|---|---|
| Backend antes | `entitlements.modules` = 8 módulos, `/gobierno/modulo` = `{habilitado: true, perfil: "MIXTO"}` |
| Activación | 200 `{ok: true, license_id: "LIC-UAT-GOB-e3f8412", mode: "FULL_ACCESS"}` (sin reautenticación: sesión reciente) |
| Red tras activar | `POST /license/activate 200` → `GET /license/status` → `GET /gobierno/modulo` → `GET /license/detail` (refetch inmediato, < 25 ms) |
| Backend después | `entitlements.modules = ["gobierno"]`, perfil `GOBIERNO` |
| Menú sin recargar, tras recargar y en sesión nueva | 58 enlaces; 0 de los 10 segmentos Enterprise; **visibles «Homologación» (actos, versiones, timeline) y «Aprobaciones» (bandeja, políticas, delegaciones)** |

## 3. Causa raíz

**El refresco del perfil funciona.** La invalidación de `["licencia","modulo","gobierno"]` vuelve a pedir el perfil, que sale GOBIERNO, y el Sidebar se vuelve a pintar. Sin recargar, tras recargar y en sesión nueva da el mismo resultado: no es un defecto de caché.

**ROOT_CAUSE = clasificación incompleta.**
- `superficieDeRuta` clasificaba por un mapa parcial, en el que todo segmento ausente cae en SHARED.
- `homologacion` y `aprobaciones` no estaban en el mapa, así que se mostraban en GOBIERNO.
- Sobre homologación, el frontend y el backend se contradecían: el backend ya la denegaba (403 `PRODUCT_PROFILE_DENIED`) y el frontend la clasificaba SHARED.
- Aprobaciones (el motor de aprobaciones de compras y ventas) no estaba protegida en ninguno de los dos.

**WHY_EXISTING_E2E_PASSED.** LICUX-E2E-01/02:
- partían de PENDING simulado o de un estado ya Gobierno;
- forzaban la reautenticación interceptando `/license/activate`;
- buscaban hrefs de solo 10 segmentos, sin `homologacion` ni `aprobaciones`, que cumplían la regex.

**WHY_OWNER_UAT_FAILED.** La dueña ve el menú completo. «Homologación» y «Aprobaciones» son funcionalidad Enterprise, la clasificación las dejaba como SHARED y ninguna prueba las miraba.

## 4. Clasificación de superficies (autoridad única: `SUPERFICIE_POR_SEGMENTO`, exhaustivo)

| Segmento | Superficie | WHY |
|---|---|---|
| gobierno | GOVERNMENT | Línea Gobierno |
| organizacion, maestros, inventario, compras, ventas, tesoreria, fiscal, regulatorio, comercial, reportes | ENTERPRISE | Línea Enterprise |
| **homologacion** | **ENTERPRISE** | 0 usos en Gobierno; el backend ya la denegaba |
| **aprobaciones** | **ENTERPRISE** | Motor de compras y ventas; 0 usos en Gobierno; ahora protegida también en el backend |
| documentos | SHARED | Gobierno importa el servicio documental (actos, expedientes) |
| auditoria | SHARED | Gobierno usa la auditoría |
| notificaciones, tareas, alertas | SHARED | CNT-09 crea sus alertas de contratos de Gobierno en ese servicio |
| mi-licencia, licenciamiento | SHARED | Licenciamiento de instalación |
| seguridad, diagnostico, forbidden, cambiar-contrasena | SHARED | Seguridad y sistema |

Una guarda de inventario (`superficies.test.ts`) exige una clave del mapa para cada primer segmento de `router.tsx` y de `Sidebar.tsx`: UNCLASSIFIED_ENTERPRISE_MENU_ITEMS=0. Sin listas duplicadas, sin código por tenant ni por institución.

## 5. Backend

`approvals_router` gana `require_enterprise_surface()`. En GOBIERNO responde 403 `PRODUCT_PROFILE_DENIED`; en MIXTO y EMPRESA no hay cambio. PENF-06 cubre aprobaciones y homologación, y PENF-05 incluye `/api/v1/approvals` en el inventario.

## 6. Caso «Empresas» (§12 del encargo)

`/organization/companies` sigue SHARED en el backend: es el contenedor técnico del tenant (OD-LICUX-02). La pantalla «Empresas» (`/organizacion/empresas`) es ENTERPRISE y queda oculta en Gobierno, que usa «Configuración del ente». **OBS-LICUX-UI-EMPRESAS-01 → CLOSED**: la clasificación es la correcta, no una incoherencia.

## 7. Pruebas

- **LICUX-E2E-05 · OWNER_UAT_REAL_FLOW**, sin interceptar nada:
  - parte de una licencia MIXTA real activada por la interfaz y comprueba que el menú muestra Enterprise;
  - activa la solo-Gobierno con la reautenticación real si se pide;
  - perfil GOBIERNO y `["gobierno"]`;
  - 0 enlaces de los 12 segmentos Enterprise y más de 0 de Gobierno, sin recargar, tras recargar y en sesión nueva;
  - 12 API Enterprise → 403 `PRODUCT_PROFILE_DENIED`;
  - 9 rutas directas → «Acceso prohibido».
- **Mutación:** devolver homologación y aprobaciones a SHARED hace fallar LICUX-E2E-05 («sin recargar: ENTERPRISE_LINKS_VISIBLE»).
- **Vitest:** inventario de superficies; GOVPROF-20 (GOBIERNO oculta Homologación y Aprobaciones aunque haya permiso); GOVPROF-21 (MIXTO las muestra).

## 8. Deudas

- OBS-LICUX-UI-EMPRESAS-01 → CLOSED (§6).
- LIC-PROFILE-ENTERPRISE-MODULE-01 sigue abierta, baja (OD-LICUX-01).
