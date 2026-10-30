# GOV-0-01 · mutaciones de comportamiento de negocio (2026-10-30)

Herramienta de Claude (`mutar07b`): un mutante cada vez, purga de `__pycache__`, restauración verificada por sha256; KILLED solo si una prueba falla de verdad (rc 1 con fallos), INVALID ante error de colección. Backend: `tests/test_gov0_ente.py` (PostgreSQL). Frontend: vitest de `src/modules/gobierno` y `Sidebar.test.tsx`.

| Id | Mutación | Resultado | Prueba que lo mata | Restaurado |
|---|---|---|---|---|
| GB01 | PATCH sin exigir gobierno_ente:edit | KILLED | tests/test_gov0_ente.py::test_ge12_permisos | sí |
| GB02 | activar sin exigir gobierno_ente:activate | KILLED | tests/test_gov0_ente.py::test_ge12_permisos | sí |
| GB03 | saltar la máquina de estados (activar un ACTIVO) | KILLED | tests/test_gov0_ente.py::test_ge10_doble_activacion | sí |
| GB04 | no exigir el documento del acto | KILLED | tests/test_gov0_ente.py::test_ge03_alta_en_borrador | sí |
| GB05 | no exigir el número del acto | KILLED | tests/test_gov0_ente.py::test_ge03_alta_en_borrador | sí |
| GB06 | aceptar un documento de otra empresa | KILLED | tests/test_gov0_ente.py::test_ge14_documento_ajeno | sí |
| GB07 | aceptar el ente de otro contenedor (sin filtro de empresa) | KILLED | tests/test_gov0_ente.py::test_ge05_validacion | sí |
| GB08 | quitar la auditoría de la activación | KILLED | tests/test_gov0_ente.py::test_ge07_activacion | sí |
| GB09 | aceptar una versión vieja en la edición | KILLED | tests/test_gov0_ente.py::test_ge06_if_match_en_borrador | sí |
| GB10 | no exigir la longitud del motivo | KILLED | tests/test_gov0_ente.py::test_ge09_modificacion_del_activo | sí |
| GB11 | quitar el control del módulo de licencia (require_module siempre deja pasar) | KILLED | tests/test_gov0_ente.py::test_ge01_modulo_habilitado_y_entitlement | sí |
| GB12 | no exigir If-Match (versión por defecto) | KILLED | tests/test_gov0_ente.py::test_ge06_if_match_en_borrador | sí |
| GB13 | permitir que un ACTIVO quede incompleto | KILLED | tests/test_gov0_ente.py::test_ge09_modificacion_del_activo | sí |
| GB14 | aceptar fecha del acto futura | KILLED | tests/test_gov0_ente.py::test_ge05_validacion | sí |
| GB15 | no versionar la activación (historial incompleto) | KILLED | tests/test_gov0_ente.py::test_ge11_historial | sí |
| GB16 | no exigir el motivo en un ACTIVO | KILLED | tests/test_gov0_ente.py::test_ge09_modificacion_del_activo | sí |
| GB17 | aceptar un RIF con formato inválido | KILLED | tests/test_gov0_ente.py::test_ge05_validacion | sí |
| GB18 | nivel territorial sin catálogo cerrado en la API | KILLED | tests/test_gov0_ente.py::test_ge05_validacion | sí |
| GB19 | aceptar campos desconocidos en el alta | KILLED | tests/test_gov0_ente.py::test_ge05_validacion | sí |
| GF01 | la UI ofrece «Activar» sin gobierno_ente:activate | KILLED | GobiernoEntePage > GEP-06 · sin activate ni edit no hay acciones 22ms | sí |
| GF02 | «Activar» habilitado con requisitos pendientes | KILLED | GobiernoEntePage > GEP-04 · borrador con faltantes muestra requisitos, activación deshabilitada e historial 41ms | sí |
| GF03 | el menú ignora el módulo de licencia | KILLED | Sidebar · Gobierno (GOV-0-01) > GSB-02 · capacidad sin módulo no muestra el enlace 22ms | sí |
| GF04 | un campo condicional oculto no se vacía | KILLED | EnteFormulario > GEF-05 · campo oculto se vacía al cambiar de nivel 49ms | sí |
| GF05 | la UI ofrece las acciones de borrador en un ente ACTIVO | KILLED | GobiernoEntePage > GEP-07 · activo con edit muestra Modificar y la fecha del acto 98ms | sí |

**Total: 24 mutantes · 24 KILLED · 0 SURVIVED · 0 INVALID.**

GB14 sobrevivió en la primera pasada: GE-05 daba verde falso (todos sus casos llevaban una denominación ya inválida). Se corrigió la prueba (T001c: cada caso con denominación válida y el campo rechazado comprobado en `field_errors`) y GB14, junto con GB17–GB19 añadidos para el resto de validaciones de entrada, se mató en la segunda pasada.
