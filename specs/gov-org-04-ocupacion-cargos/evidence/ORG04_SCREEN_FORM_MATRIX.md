# GOV-ORG-04 · ORG04_SCREEN_FORM_MATRIX

| Campo | S1 · Ocupantes | S2 · Cargo a fecha | S3 · Asignaciones | S4 · Nueva / editar | S5 · Asignación | S6 · Funcionarios | S7 · Funcionario |
|---|---|---|---|---|---|---|---|
| SCREEN_ID | `OcupantesPage` | `CargoOcupacionPage` | `AsignacionesPage` | `NuevaAsignacionPage` | `AsignacionPage` | `FuncionariosPage` | `FuncionarioPage` |
| USER_GOAL | ver quién ocupa cada cargo a una fecha | ver ocupación, autoridad, delegaciones e historia | listar, filtrar y exportar | registrar o editar un borrador | revisar y actuar | registrar y buscar funcionarios | ver y modificar la ficha |
| MENU_PATH | Gobierno › Ocupación de cargos | S1 › cargo | S1 › Asignaciones | S1 › Nueva asignación | S3 › código | S1 › Funcionarios | S6 › código |
| ROLE | `gobierno_ocupacion:view`; alta con `:manage` | `:view` | `:view` | `:manage` | `:view`; `:manage`, `:activate` (MFA), `:revoke` (MFA) | `:view`; alta con `:manage` | `:view`; `:manage` |
| FIELDS | ejercicio, fecha, cargo; cargo, unidad, titular, ejerce, situación, delegaciones | fecha; titular, ejerce, figura, acto, vigencia; competencias; delegaciones; historia | figura, estado, fecha; código, funcionario, cargo, figura, vigencia, situación, acto | ejercicio, figura, funcionario, cargo, cargo de origen, acto, desde, hasta, fundamento, rendición, declaración, competencias, máxima autoridad, autorización | quién, vigencia, acto y base jurídica, competencias, autoridad, avocaciones, historia | nombre, tipo y número de documento; código, documento enmascarado, estado | datos, asignaciones, historia; nombre y estado |
| ACTIONS | filtrar, paginar, abrir cargo | cambiar fecha, ver asignación, nueva asignación | filtrar, paginar, exportar CSV | guardar borrador, cancelar | editar, descartar, activar, revocar, finalizar, avocar | registrar, buscar, paginar | modificar |
| STATES | sin acceso, cargando, módulo no habilitado, error, vacío, cubierto, vacante | sin acceso, cargando, 404, error, vacante | sin acceso, cargando, error, vacío | sin acceso, cargando, no editable, errores de campo, error general, sin opciones | sin acceso, 404, BORRADOR, ACTIVO, REVOCADO, FINALIZADO, DESCARTADO | sin acceso, cargando, error, vacío | sin acceso, 404, error |
| PERMISSIONS | autenticación → permiso → empresa → módulo | ídem | ídem | ídem + reglas del servicio | ídem + If-Match + SoD | ídem | ídem + If-Match |
| AUDIT | — | — | GOV_ASSIGNMENTS_EXPORTED | GOV_ASSIGNMENT_CREATED, _UPDATED | _ACTIVATED, _DISCARDED, _REVOKED, _FINISHED, _AVOCATED | GOV_OFFICIAL_CREATED | GOV_OFFICIAL_UPDATED |
| ERRORS | 403, 422 | 403, 404 | 403 | 404, 409 _STALE, 422 GOV_ASSIGNMENT_* | 403 _SELF_ACTIVATION, 404, 409 _STALE, _INVALID_STATE, _OVERLAP, GOV_SOD_CONFLICT, 422 | 409 GOV_OFFICIAL_DUPLICATE, 422 | 404, 409 _STALE, 422 |
| RESPONSIVE | filtros apilados; tabla en región | listas y tablas en región; 320 px sin desbordar | ídem | campos apilados | paneles en línea, sin modales | formulario apilado | ídem |
| ACCESSIBILITY | h1, `role=search`, caption, región con foco | h1, secciones con h2 | h1, caption | rótulos, `aria-invalid`, `fieldset`/`legend` en competencias | `dl` válidas, `role=alert` | rótulos, `role=alert` | rótulos, `role=alert` |

Axe WCAG 2.2 AA a 1280, 768 y 320 px en lista, cargo, asignaciones, detalle con panel abierto, formulario, formulario con error, funcionarios, ficha y error de carga (`OCU-E2E-03`).
