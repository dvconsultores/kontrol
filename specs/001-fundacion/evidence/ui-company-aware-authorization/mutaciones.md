# UI COMPANY-AWARE AUTHORIZATION · Mutaciones (2026-10-27)

Herramienta de Claude, fuera del árbol (`scratchpad/tools/mutaciones_ui.py`): cada mutante es un reemplazo exacto y único en el código
de producto; se corre vitest sobre `src/app/autoridad`, `src/components`, `src/layout`, `src/api/client.test.ts` y `src/tests`, y el
fichero se restaura y se compara byte a byte (`assert` de igualdad tras cada mutante). Ningún mutante llegó a Git.

## 1. Frontend: resolución, proveedor, guarda, puerta, menú y cliente (20)

| Mutante | Qué rompe | 1.ª corrida | Final | Prueba que lo mata |
|---|---|---|---|---|
| R1 | Cualquier segmento literal casa | MUERTO | MUERTO | resolver: método en minúsculas, query, segmentos |
| R2 | Gana la plantilla menos específica | MUERTO | MUERTO | «prioriza el literal frente a la plantilla» |
| R3 | No quita `/api/v1` | MUERTO | MUERTO | resolver + `authority-surfaces` (operaciones de PANTALLAS) |
| R4 | Ruta desconocida permitida | MUERTO | MUERTO | «deniega una operación desconocida» |
| R5 | Ignora el alcance (suma global, el defecto del ciclo) | MUERTO | MUERTO | «deniega COMPANY/TENANT con la capacidad solo en global» |
| R6 | Basta UNA de las capacidades | **SOBREVIVE** | MUERTO | **nueva** «deniega COMPANY si falta una de sus capacidades aunque tenga la otra» (TF-M1) |
| R7 | Motivos invertidos | MUERTO | MUERTO | «deniega con COMPANY_SCOPE_FORBIDDEN…» |
| P1 | Usa la autoridad de otra empresa | SOBREVIVE | **EQUIVALENTE** | ver §2 |
| P2 | Tenant = suma global | MUERTO | MUERTO | «permite operación tenant solo si está en tenantPermissions» |
| P3 | Sin CARGANDO mientras llega la autoridad de empresa | **SOBREVIVE** | MUERTO | **nueva** «sigue CARGANDO y no ofrece nada mientras /authority/company no responde» (TF-M2) |
| P4 | La denegación no invalida la autoridad | MUERTO | MUERTO | «registra manejador de denegación…» |
| P5 | La denegación no recarga `/auth/me` | MUERTO | MUERTO | idem |
| P6 | `motivoDeCapacidad` sin alcance | **SOBREVIVE** | MUERTO | **nueva** «motivoDeCapacidad distingue la empresa activa del resto» (TF-M2) |
| G1 | Requisito de pantalla sin CARGANDO | MUERTO | MUERTO | RutaAutorizada «CARGANDO pinta el estado de carga» |
| G2 | Requisito ignora la operación | MUERTO | MUERTO | «operación no autorizada aunque la capacidad sí → denegada» |
| G3 | La guarda pinta la pantalla denegada | MUERTO | MUERTO | RutaAutorizada: los tres mensajes |
| G4 | La guarda pinta durante la carga | MUERTO | MUERTO | «CARGANDO pinta el estado de carga» |
| A1 | `Autorizado` siempre pinta | MUERTO | MUERTO | Autorizado: oculta / fallback |
| S1 | Menú sin filtrar | MUERTO | MUERTO | Sidebar NAV-01..07 |
| C1 | El cliente no avisa `COMPANY_SCOPE_FORBIDDEN` | MUERTO | MUERTO | client «avisa con COMPANY_SCOPE_FORBIDDEN…» |

**Resultado: 19/20 muertos y 1 equivalente justificado** (primera corrida 16/20; los tres supervivientes reales se cerraron con
pruebas nuevas, escritas por DeepSeek y auditadas por Claude, y la segunda corrida de R6, P3 y P6 dio 3/3 muertos).

## 2. P1, equivalente

P1 hace que el conjunto de empresa use `/authority/company` aunque su `company_id` no sea la empresa activa. No es observable: en ese
mismo caso `esperandoEmpresa` es verdadero, el estado queda en `CARGANDO` y `puede`, `tiene`, `motivo` y `motivoDeCapacidad` devuelven
`false`/`null` sin mirar el conjunto. Son dos defensas independientes de la misma propiedad (FRONTEND_STALE_SCOPE_AUTHORITY = BLOCKED):
P3 (que quita la del estado) muere con su prueba, y la prueba existente «trata company_id distinto al activo como autoridad de empresa
vacía» fija el comportamiento externo.

## 3. Cobertura de puertas (gate-coverage, 2 mutantes)

| Mutante | Resultado |
|---|---|
| M1 · `SucursalesPage` sin `<Autorizado>` | MUERTO por «todo fichero con una acción mutante que exige autoridad tiene puerta o está exento» |
| M2 · `ListasPrecioPage` (consumidora de un módulo exento) sin `useAutoridad` | MUERTO por la anterior y por «las exenciones siguen vigentes y sus consumidores llevan puerta» |

## 4. Backend: regresión de 02B y de la delegación

Mismas herramientas que en 02B (`mutaciones_alcance.py`, `mutaciones_delegacion.py`), sobre el árbol final del ciclo y PostgreSQL de QA,
con `PYTHONDONTWRITEBYTECODE=1`:

| Conjunto | Mutantes | Muertos | Supervivientes |
|---|---|---|---|
| Autorización por empresa (02B, S01..S21 y variantes) | 23 | 23 | 0 |
| Techo de delegación (D01..D21) | 21 | 21 | 0 |

El ciclo no debilita ninguna defensa del backend: los cambios del backend (proyecciones de solo lectura y la marca `kontrol_scope`) no
alteran la decisión de autorización de ninguna ruta.
