# Inventario de llamadas al ayudante de empresa (HEAD 0f4a5c3)

| CALLER | FILE | PURPOSE | BEFORE_NAV | AFTER_NAV | USES_NETWORKIDLE | USES_COUNT | USES_EXPECT_AUTO_WAIT | USES_EXACT | POSTCONDITION | CUSTOM_COPY | CLASSIFICATION |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `activarEmpresa` | `e2e/helpers/empresa.ts:40` | dejar una empresa activa | login hecho | navega al menú | **sí** | **sí** (decisión instantánea) | solo en la postcondición | sí | exactamente una activa | canónico | HELPER_CANONICO |
| `empresa-helper.spec.ts` (4 pruebas, 7 llamadas) | `e2e/empresa-helper.spec.ts` | prueba del ayudante | — | — | vía helper | vía helper | sí | sí | sí | no | CONSUMER_HELPER |
| `warehouse-a11y.spec.ts:31`, `uom-a11y.spec.ts:29`, `uom-conversion.spec.ts:45`, `warehouse-structure.spec.ts:52` | esos ficheros | `uiLogin` → empresa activa | login | sí | vía helper | vía helper | sí | sí | sí | no | CONSUMER_HELPER |
| `activarEmpresa` local | `e2e/approvals.spec.ts:73` (y `controlesDeEmpresa` :55) | ídem, con compuerta por código de la empresa (`empresa(page.request, …)`) | login | navega | **sí** | **sí** | solo postcondición | sí | sí | **copia local** (3 llamadas: `uiLogin:120`, `:520`, `:532`) | CUSTOM_COPY (misma carrera) |
| activación local | `e2e/documents.spec.ts:76-80`, `e2e/documents-a11y.spec.ts:34-38` | `if (await activar.first().count()) click` | login | navega | **sí** | **sí** | sí tras el clic | sí | no (no comprueba estado si no pulsa) | copia reducida de ciclos convergidos (CONC-046) | CUSTOM_COPY_REDUCIDA — fuera de FR-HE-019; anotada (§11 del delta) |
| `rates.spec.ts:427` | — | pulsa «Desactivar» de una fila de tasas (otra pantalla) | — | — | — | — | — | no | — | no | NO_RELACIONADO |
| `approvals.spec.ts:259` | — | botón «Activar» de una política de aprobación (otra pantalla) | — | — | — | — | — | no | — | no | NO_RELACIONADO |

`UNKNOWN_CALLERS = 0`. Dos implementaciones del algoritmo (canónica + approvals) comparten la misma carrera; dos
copias reducidas en documentos no deciden por estado (solo pulsan si ven «Activar») y quedan anotadas.
