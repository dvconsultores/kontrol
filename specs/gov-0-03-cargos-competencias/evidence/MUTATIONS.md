# GOV-0-03 · mutaciones de comportamiento de negocio (2026-11-01)

Herramienta de Claude (`mutar07b`): un mutante cada vez, purga de `__pycache__`, restauración verificada por sha256; KILLED solo si una
prueba falla de verdad, INVALID ante error de colección. Backend: `tests/test_gov0_cargos.py` (+ `tests/test_gov0_estructura.py` para los
mutantes de ORG-02) sobre PostgreSQL. Frontend: vitest de `src/modules/gobierno/cargos` y `src/layout/Sidebar.test.tsx`.

## Backend (25)

| Id | Mutación | Resultado | Prueba que lo mata |
|---|---|---|---|
| OC01 | un cargo se busca sin alcance de estructura ni empresa | KILLED | test_gc23_aislamiento |
| OC02 | la unidad del cargo se acepta de cualquier estructura y empresa | KILLED | test_gc23_aislamiento |
| OC03 | se pone en vigor sin la estructura vigente | KILLED | test_gc20_copia (+GC-21, GC-25) |
| OC04 | se pone en vigor sin acto | KILLED | test_gc03_crear (+GC-08) |
| OC05 | se pone en vigor sin competencias | KILLED | test_gc03_crear (+GC-08) |
| OC06 | se cambia la autoridad de un cargo vigente sin `publish` | KILLED | test_gc13_autoridad_preparador |
| OC07 | no se exige motivo al cambiar competencias de un cargo vigente | KILLED | test_gc12_cambiar_limite |
| OC08 | se retira la última competencia de un cargo vigente | KILLED | test_gc14_agregar_retirar_vigor |
| OC09 | se acepta una versión vieja del cargo | KILLED | test_gc07_if_match |
| OC10 | se escribe en un ejercicio cerrado | KILLED | test_gc21_ejercicio_cerrado |
| OC11 | en un cargo vigente se cambia el código | KILLED | test_gc11_cambios_vigor |
| OC12 | se elimina un cargo con acto vinculado | KILLED | test_gc17_eliminar |
| OC13 | se desactiva con cualquier fecha | KILLED | test_gc16_desactivar |
| OC14 | se pone en vigor un cargo ya vigente | KILLED | test_gc10_activar |
| OC15 | un cambio de límite idéntico crea versión y evento | KILLED | test_gc12_cambiar_limite |
| OC16 | el otorgamiento se audita con otra acción | KILLED | test_gc05_competencias_borrador |
| OC17 | el CSV omite los cargos sin competencias | KILLED | test_gc19_csv |
| OC18 | la copia trae también los cargos en borrador (ORG-02) | KILLED | test_gc20_copia |
| OC19 | se desactiva una unidad con cargos (ORG-02) | KILLED | test_gc18_unidad_con_cargos |
| OC20 | se elimina una unidad con cargos (ORG-02) | KILLED | test_gc21_ejercicio_cerrado |
| OC21 | la API concede siempre la autoridad de `publish` | KILLED | test_gc13_autoridad_preparador |
| OC22 | poner en vigor solo exige `edit` | KILLED | test_gc13_autoridad_preparador |
| OC23 | «sin límite» admite monto (coherencia del esquema) | KILLED | test_gc06_vectores_limite |
| OC24 | el monto admite negativos | KILLED | test_gc06_vectores_limite |
| OC25 | se registra o traslada un cargo a una unidad inactiva | KILLED (tras GC-27) | test_gc27_unidad_inactiva |

Primera pasada: 24 KILLED, 1 SURVIVED (OC25). Era un hueco real de prueba (GC-04 solo cubría un UUID inexistente): se encargó GC-27
(ORG03-T001c, DeepSeek flash) y la segunda pasada lo mata. Resultado backend: **25 KILLED, 0 supervivientes, 0 INVALID**.

## Frontend (15)

| Id | Mutación | Resultado | Prueba que lo mata |
|---|---|---|---|
| FC01 | en un cargo vigente se cambian competencias sin `publish` | KILLED | CargoPage > GCP-04 |
| FC02 | «Poner en vigor» habilitado con requisitos pendientes | KILLED | CargoPage > GCP-01 |
| FC03 | el aviso de inactivo pinta la fecha de inicio | KILLED | CargoPage > GCP-07 |
| FC04 | con el ejercicio cerrado se ofrecen escrituras | KILLED | CargoPage > GCP-06 |
| FC05 | cambiar el límite envía también la acción | KILLED | CargoPage > GCP-09 |
| FC06 | un monto cero se acepta | KILLED | CompetenciaFormulario > GKF-03 |
| FC07 | se repite acción × materia | KILLED | CompetenciaFormulario > GKF-02 |
| FC08 | «sin límite» envía el monto | KILLED | CompetenciaFormulario > GKF-05 |
| FC09 | no se exige motivo en un cargo vigente | KILLED | CompetenciaFormulario > GKF-06 |
| FC10 | editar un cargo vigente compara también código y vigencia | EQUIVALENT | — (nota 1) |
| FC11 | el formulario ofrece unidades inactivas | KILLED | CargoFormulario > GCF-01 |
| FC12 | el límite se muestra en crudo | KILLED | CargoPage > GCP-08 (+GCL-01) |
| FC13 | «Agregar cargo» con el ejercicio cerrado | KILLED | CargosPage > GCL-04 |
| FC14 | el menú ignora el módulo en «Cargos y competencias» | KILLED | Sidebar > GSB-07 |
| FC15 | desactivar acepta cualquier fecha | KILLED | DesactivarCargo > GDC-01 |

1. FC10 cambia `if (!esVigente)` por `if (true)` en la construcción de los cambios. En un cargo vigente los campos Código y Vigente
   desde están deshabilitados y conservan su valor inicial, así que la comparación nunca añade claves: el comportamiento observable no
   cambia (equivalente). El servidor además rechaza ese cambio con `GOV_POSITION_FIELD_LOCKED` (OC11).

Resultado frontend: **14 KILLED, 1 EQUIVALENT (justificado), 0 supervivientes**.

**Total del ciclo: 40 mutantes · 39 KILLED · 1 EQUIVALENT · 0 supervivientes de comportamiento · 0 INVALID.**
