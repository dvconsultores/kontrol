# GOV-0-02 · mutaciones de comportamiento de negocio (2026-10-30)

Herramienta de Claude (`mutar07b`): un mutante cada vez, purga de `__pycache__`, restauración verificada por sha256; KILLED solo si una
prueba falla de verdad (rc 1 con fallos), INVALID ante error de colección. Backend: `tests/test_gov0_estructura.py` sobre PostgreSQL
(`KONTROL_TEST_DB_URL` de QA). Frontend: vitest de `src/modules/gobierno`, `src/components/company` y `Sidebar.test.tsx`.

## Backend (21)

| Id | Mutación | Resultado | Prueba que lo mata | Restaurado |
|---|---|---|---|---|
| OB01 | quitar el alcance de empresa al buscar la estructura | KILLED | test_gs14_ente_no_activo (+10) | sí |
| OB02 | quitar el alcance de estructura y empresa al buscar una unidad | KILLED | test_gs24_aislamiento | sí |
| OB03 | permitir ciclos de jerarquía | KILLED | test_gs08_jerarquia | sí |
| OB04 | quitar la comprobación explícita de autorreferencia | EQUIVALENT | — (ver nota 1) | sí |
| OB05 | aceptar un superior inactivo al crear | KILLED | test_gs18_desactivar (+2) | sí |
| OB06 | crear unidades sin `gobierno_estructura:edit` | KILLED | test_gs23_permisos | sí |
| OB07 | poner en vigor sin `gobierno_estructura:publish` | KILLED | test_gs23_permisos | sí |
| OB08 | aceptar una versión vieja de la unidad al editar | KILLED | test_gs10_if_match_unidad (+3) | sí |
| OB09 | no exigir el acto para poner en vigor | KILLED | test_gs04_abrir (+4) | sí |
| OB10 | no exigir el ente ACTIVO | KILLED | test_gs14_ente_no_activo (+3) | sí |
| OB11 | registrar la puesta en vigor con otra acción de auditoría | KILLED | test_gs15_publicar_a | sí |
| OB12 | una estructura cerrada admite escrituras | KILLED | test_gs21_cerrar | sí |
| OB13 | eliminar unidades de una estructura vigente | KILLED | test_gs17_sin_borrado_vigor | sí |
| OB14 | no exigir motivo al crear en una estructura vigente | KILLED | test_gs16_cambios_vigor (+3) | sí |
| OB15 | permitir cambiar el código en vigor (código de error distinto) | KILLED | test_gs16_cambios_vigor (+4) | sí |
| OB16 | desactivar con subordinadas activas | KILLED | test_gs18_desactivar (+3) | sí |
| OB17 | cerrar un ejercicio no terminado | KILLED | test_gs21_cerrar | sí |
| OB18 | copiar también las unidades inactivas | KILLED | test_gs22_copia | sí |
| OB19 | quitar la comprobación previa de código duplicado al crear | EQUIVALENT | — (ver nota 2) | sí |
| OB20 | contar un acto cuyo documento es de otra empresa | KILLED (tras GS-27) | test_gs27_documento_de_otra_empresa | sí |
| OB21 | aceptar una versión vieja de la estructura al publicar | KILLED | test_gs13_publicar_sin_acto | sí |

Primera pasada: 18 KILLED, 3 SURVIVED (OB04, OB19, OB20). OB20 era un hueco real de prueba: se encargó GS-27 (ORG02-T001c, DeepSeek) y la
segunda pasada lo mata. OB04 y OB19 son mutantes equivalentes (no cambian el comportamiento observable):

1. OB04: `_es_descendiente(por_id, nuevo_superior, unidad)` empieza comparando el candidato con la propia unidad, así que la autorreferencia ya
   devuelve 422 `GOV_UNIT_HIERARCHY_CYCLE` sin la comparación explícita; la condición es redundante, no una regla distinta.
2. OB19: sin la consulta previa, el `UNIQUE(structure_id, code)` de la base dispara `IntegrityError`, que el servicio traduce al mismo 409
   `GOV_UNIT_CODE_DUPLICATE` (prueba GS-07 sigue verde con el mismo código y estado).

Resultado backend: 19 KILLED, 2 EQUIVALENT, 0 supervivientes de comportamiento.

## Frontend (14)

| Id | Mutación | Resultado | Prueba que lo mata | Restaurado |
|---|---|---|---|---|
| GF01 | la UI ofrece edición sin `gobierno_estructura:edit` | KILLED | EstructuraPage > GES-04 · sin edit no hay acciones de edición | sí |
| GF02 | una estructura cerrada se puede editar | KILLED | EstructuraPage > GES-03 · cerrada solo muestra historial | sí |
| GF03 | «Poner en vigor» habilitado con requisitos pendientes | KILLED | EstructuraPage > GES-01 | sí |
| GF04 | «Cerrar ejercicio» habilitado en el ejercicio en curso | KILLED | EstructuraPage > GES-09 | sí |
| GF05 | «Eliminar» se ofrece en una estructura vigente | KILLED | EstructuraPage > GES-03 · vigente | sí |
| GF06 | «Depende de» ofrece descendientes (ciclo) | KILLED | UnidadFormulario > GUF-01 | sí |
| GF07 | «Depende de» ofrece unidades inactivas | KILLED | UnidadFormulario > GUF-01 | sí |
| GF08 | en vigor se guarda sin motivo | KILLED | UnidadFormulario > GUF-03 | sí |
| GF09 | el código se puede cambiar en una estructura vigente | KILLED | UnidadFormulario > GUF-03 | sí |
| GF10 | la compuerta dice «ente» fuera de Gobierno (GOV0-UI-01) | KILLED | EstadoDeEmpresa > GUI-02 | sí |
| GF11 | el menú ignora el módulo en «Estructura organizativa» | KILLED | Sidebar · Gobierno · estructura > GSB-05 | sí |
| GF12 | la copia ofrece un borrador como origen | KILLED | EjerciciosPage > GEJ-03 | sí |
| GF13 | un aviso descartado no libera su clave (nunca vuelve a mostrarse) | KILLED | NotificationContext > NOT-02 | sí |
| GF14 | sin control de avisos duplicados visibles | KILLED | NotificationContext > NOT-01 | sí |

Resultado frontend: 14 KILLED, 0 supervivientes.

**Total: 35 mutantes · 33 KILLED · 2 EQUIVALENT (justificados) · 0 supervivientes de comportamiento · 0 INVALID.**

Añadido tras la E2E real (T006g): GF15 «la vigencia formatea fechas civiles como instantes (día desplazado)» → KILLED por
EstructuraPage > GES-10 · la vigencia muestra fechas civiles sin desplazar el día. **Total final: 36 mutantes · 34 KILLED · 2 EQUIVALENT · 0
supervivientes de comportamiento.**

Añadidos por la convergencia (T011/T012, pruebas GS-28 y GS-29): OB22 «un PATCH sin cambios crea versión y evento» → KILLED por
`test_gs29_sin_cambios`; OB23 «un ejercicio sin estructura responde otro código» → KILLED por `test_gs28_estructura_inexistente`.
**Total del ciclo: 38 mutantes · 36 KILLED · 2 EQUIVALENT · 0 supervivientes de comportamiento · 0 INVALID.**
