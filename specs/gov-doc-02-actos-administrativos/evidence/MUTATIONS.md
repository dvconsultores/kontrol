# DOC-02 · mutaciones de negocio (T009)

Herramienta de Claude `mutar07b.py` (scratchpad del ciclo): cada mutante aplica un SEARCH único → REPLACE, purga `__pycache__`,
ejecuta su orden y restaura el fichero comprobando sha256 (todos `restaurado`). Backend: `pytest tests/test_gov_doc02_actos.py`
sobre PostgreSQL con el analizador. Interfaz: `vitest` de `src/modules/gobierno/actos`, `Sidebar.test.tsx` y `fecha-de-negocio.test.ts`.

## Resultado

| Lote | Mutantes | KILLED | EQUIVALENT | SURVIVED |
|---|---|---|---|---|
| Backend (servicio y API) | 21 | 21 | 0 | 0 |
| Interfaz (menú, pantallas, paneles, fechas) | 22 | 21 | 1 | 0 |
| **Total** | **43** | **42** | **1** | **0** |

Primera pasada: 5 supervivientes en backend (BE-03, BE-07, BE-15, BE-19, BE-20) y 2 en interfaz (UI-11, UI-22). Las pruebas nuevas
GA-32..GA-36 (DeepSeek, T001c) y FRM-14 (T007b2) matan BE-03/07/15/19/20 y UI-11 en la segunda pasada. UI-22 es equivalente: quitar la
comprobación del día en `sumarDiasDeNegocio` no cambia ningún resultado, porque todo día inválido (0, 29–31 inexistentes, 32–99)
desborda a otro mes y la comprobación del mes ya lo rechaza.

## Backend

| ID | Mutación | Fichero | Estado | Prueba que lo mata |
|---|---|---|---|---|
| BE-01 | número sin normalizar a mayúsculas | service_actos.py | KILLED | test_ga07_numero_duplicado |
| BE-02 | sin control de versión (If-Match) | service_actos.py | KILLED | test_ga10_modificar_borrador |
| BE-03 | escritura sin filtro de empresa | service_actos.py | KILLED | test_ga32_escritura_de_otra_empresa |
| BE-04 | emite con datos incompletos | service_actos.py | KILLED | test_ga12_emitir_con_faltantes |
| BE-05 | interno queda emitido, no eficaz | service_actos.py | KILLED | test_ga15_emitir_interno |
| BE-06 | interno con eficacia anterior al acto | service_actos.py | KILLED | test_ga15_emitir_interno |
| BE-07 | particular admite fecha de eficacia al emitir | service_actos.py | KILLED | test_ga33_particular_no_admite_eficacia_al_emitir |
| BE-08 | la emisión no congela los vínculos | service_actos.py | KILLED | test_ga14_emitir_particular_y_congelar_vinculo |
| BE-09 | la emisión no se audita | service_actos.py | KILLED | test_ga14_emitir_particular_y_congelar_vinculo |
| BE-10 | prensa con 14 días | service_actos.py | KILLED | test_ga17_eficacia_particular_prensa |
| BE-11 | eficacia explícita anterior a la base | service_actos.py | KILLED | test_ga17_eficacia_particular_prensa |
| BE-12 | publicación anterior al acto | service_actos.py | KILLED | test_ga16_eficacia_particular_personal |
| BE-13 | gaceta o prensa sin referencia | service_actos.py | KILLED | test_ga18_eficacia_general |
| BE-14 | referencia en borrador admitida | service_actos.py | KILLED | test_ga21_revocar |
| BE-15 | referencia anterior al acto admitida | service_actos.py | KILLED | test_ga34_referencia_anterior_al_acto |
| BE-16 | acto que se revoca a sí mismo | service_actos.py | KILLED | test_ga21_revocar |
| BE-17 | competencia no exigida al cargo | service_actos.py | KILLED | test_ga06_autoridad_y_competencia |
| BE-18 | emitir con permiso de edición | api_actos.py | KILLED | test_ga25_permisos |
| BE-19 | revocar con permiso de emisión | api_actos.py | KILLED | test_ga35_revocar_exige_annul |
| BE-20 | CSV sin filtro de año | service_actos.py | KILLED | test_ga36_csv_filtra_por_anio |
| BE-21 | lista sin filtro de año | service_actos.py | KILLED | test_ga08_listar |

## Interfaz

| ID | Mutación | Fichero | Estado | Prueba que lo mata |
|---|---|---|---|---|
| UI-01 | menú sin la entrada de actos | Sidebar.tsx | KILLED | Sidebar · Gobierno › Actos administrativos > GSB-08 · módulo habilitado y gobierno_actos:v |
| UI-02 | entrada de actos sin exigir el módulo | Sidebar.tsx | KILLED | Sidebar · Gobierno › Actos administrativos > GSB-09 · capacidad sin módulo no muestra el e |
| UI-03 | pantalla de actos exige otra capacidad | pantallas.ts | KILLED | Sidebar · Gobierno › Actos administrativos > GSB-08 · módulo habilitado y gobierno_actos:v |
| UI-04 | alta visible con solo consulta | ActosPage.tsx | KILLED | ActosPage > GAL-09a · sin gobierno_actos:edit no hay botón «Registrar acto» 48ms |
| UI-05 | filtro de estado ignorado | ActosPage.tsx | KILLED | ActosPage > GAL-04 · filtros de Estado, Carácter y Cargo filtran correctamente 99ms |
| UI-06 | 409 de número duplicado no llega al campo | ActosPage.tsx | KILLED | ActosPage > GAL-11 · alta con 409 GOV_ACT_NUMBER_DUPLICATE muestra el error en el output 1 |
| UI-07 | Emitir habilitado con faltantes | ActoPage.tsx | KILLED | ActoPage > ACP-01 · BORRADOR con view+edit+issue y faltantes ["HECHOS","DOCUMENTO_ACTO"] m |
| UI-08 | Emitir visible sin issue | ActoPage.tsx | KILLED | ActoPage > ACP-08 · solo gobierno_actos:view en BORRADOR no muestra botones de escritura 6 |
| UI-09 | If-Match de emisión equivocado | ActoPage.tsx | KILLED | ActoPage > ACP-02 · BORRADOR con faltantes ["DOCUMENTO_ACTO"] permite emitir y llama a POS |
| UI-10 | eficacia futura mal calificada | ActoPage.tsx | KILLED | ActoPage > ACP-06a · EFICAZ con fecha_eficacia 2026-03-12 muestra «Eficaz desde 12/03/2026 |
| UI-11 | la competencia no se vacía al cambiar de cargo | ActoFormulario.tsx | KILLED | ActoFormulario > FRM-14 · al cambiar de cargo la competencia elegida no viaja 588ms |
| UI-12 | fecha futura aceptada | ActoFormulario.tsx | KILLED | ActoFormulario > FRM-07 · una fecha posterior a hoy da error real bajo el campo y no llama |
| UI-13 | edición envía campos sin cambio | ActoFormulario.tsx | KILLED | ActoFormulario > FRM-09 · editar: los campos arrancan con los valores del acto y solo camb |
| UI-14 | emisión ofrece documentos no activos | EmitirActo.tsx | KILLED | EmitirActo > EMI-05 · el select «PDF firmado del acto» ofrece los documentos ACTIVE y no o |
| UI-15 | eficacia interna anterior al acto aceptada | EmitirActo.tsx | KILLED | EmitirActo > EMI-02 · INTERNO con fecha de eficacia anterior a la fecha del acto muestra e |
| UI-16 | prensa con 14 días | RegistrarEficacia.tsx | KILLED | RegistrarEficacia > EFI-03 · PARTICULAR + Prensa con fecha 2026-10-01 muestra «Será eficaz |
| UI-17 | soporte admite el documento del acto | RegistrarEficacia.tsx | KILLED | RegistrarEficacia > EFI-07 · el select «Soporte» no ofrece el documento del propio acto (d |
| UI-18 | corrección envía todo | CorregirActo.tsx | KILLED | CorregirActo > COR-02 · cambiar «Asunto» y escribir el motivo → onConfirmar con lo cambiad |
| UI-19 | vacío opcional como cadena | CorregirActo.tsx | KILLED | CorregirActo > COR-03 · vaciar «Destinatario» (opcional) y motivo válido → onConfirmar con |
| UI-20 | referencia anterior al acto admitida | ReferenciarActo.tsx | KILLED | ReferenciarActo > REF-02 · ofrece solo r1 y r2 con texto formateado 100ms |
| UI-21 | referencia en borrador admitida | ReferenciarActo.tsx | KILLED | ReferenciarActo > REF-02 · ofrece solo r1 y r2 con texto formateado 107ms |
| UI-22 | suma de días acepta fechas inexistentes | fecha-de-negocio.ts | EQUIVALENT | — |
