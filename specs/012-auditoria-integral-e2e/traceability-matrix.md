# Spec 012 — Matriz de Trazabilidad (traceability-matrix.md)

## Dirección 1: Requisito → Implementación (muestra crítica)
| Req (contexto) | Dominio | Menú | Ruta | Página | API | DB | Estado |
|---|---|---|---|---|---|---|---|
| FR org empresa activa | Org | ✔ Empresas | ✔ | ✔ | ✔ | ✔ | COMPLETE |
| FR org sucursal | Org | ✔ Sucursales | ✔ | ✔ | ✔ | ✔ | COMPLETE |
| FR org establecimiento | Org | ✖ | ✖ | ✖ | ✔ | ✔ | PARTIAL |
| FR seguridad usuarios | Seguridad | ✔ | ✖ | ✖ | ✔ | ✔ | BROKEN |
| FR seguridad roles | Seguridad | ✔ | ✖ | ✖ | ✖ | ✔ | BROKEN |
| FR licencia central | Licencia | ✔ | ✔ | ✔ | ✔ | ✔ | COMPLETE |

## Dirección 2: Implementación → Requisito (detección)
- **API sin interfaz**: 117 endpoints sin consumidor (F-04) → verificar si tienen requisito sin pantalla.
- **Menú sin ruta**: 2 (Seguridad) → requisito declarado pero sin implementación de UI (F-01/F-02).
- **Ruta sin menú**: 0 (todas las rutas del router tienen entrada de menú o son de sistema).

## Regla
Una celda "BROKEN"/"PARTIAL" implica que la función NO está completa aunque la API exista.
