# Spec · CNT-02 · Adendas, prórrogas, modificaciones y variaciones versionadas (GOV-CNT-002)

- Estado: CONVERGED
- Programador: P2. Entrada: `11cff08` (Alembic 0116).
- Requisito: GOV-CNT-002 (N11, N12, N20; P0).
- Antes de CNT-02 se ejecuta un delta previo dentro de la Spec dueña de CNT-01: `specs/gov-cnt-01-contrato-orden/cnt01-moneda-cobertura-delta.md` (H01–H10).

## 1. Objetivo

Un contrato u orden FORMALIZADO de CNT-01 puede recibir instrumentos modificatorios formalizados, en una historia lineal y versionada. El contrato original **no se modifica nunca**. Las condiciones vigentes se derivan del original más las modificaciones formalizadas, en orden, y se reconstruyen a cualquier fecha.

Recorrido del sponsor:
1. Gobierno → Contratos → Contratos y órdenes → abrir el contrato → **Modificaciones**.
2. Comparar las condiciones originales con las vigentes.
3. **Nueva modificación**: elegir el tipo; indicar fecha, vigencia, motivo, plazo o monto, condiciones, referencia y soporte; añadir cobertura si hay aumento; elegir firmante.
4. **Formalizar**: con MFA, el sistema asigna `CT-2026-0001/PR-001`, sella el soporte y congela la modificación.

## 2. Alcance

Dentro:
- Tipos ADENDA, PRORROGA, MODIFICACION y VARIACION.
- Cambio de plazo (solo extensión), de monto (aumento o reducción, en la misma moneda) y de condiciones textuales.
- Cobertura adicional BUD-06.
- Guarda frente a los compromisos BUD-08 en las reducciones.
- Firmante FIRMAR × CONTRATACIONES con el límite contra el **monto efectivo nuevo**, usando TRE-09 si las monedas difieren.
- Soporte DOC-08; MFA; SoD; auditoría; proyección efectiva a una fecha; historia; PG inmutable.

Fuera:
- Ejecución, hitos, valuaciones, recepción y cierre (CNT-03).
- Supervisor o administrador (CNT-04, de P1).
- Penalidades, retenciones y anticipos (CNT-06, bloqueado por N38).
- Terminación o rescisión (CNT-07).
- Fórmulas escalatorias (LCP art. 133).
- Cambio de objeto, de contratista o de moneda.
- Anulación de una modificación formalizada (§6).
- Creación de CDP o de compromisos.
- Reporting (REP-04): `REPORTING=NOT_APPLICABLE`.

## 3. Contratos (C02-01 a C02-22)

| Id | Contrato |
|---|---|
| C02-01 | Solo un contrato FORMALIZADO de la empresa del contexto recibe modificaciones. Un BORRADOR responde 409 `GOV_CONTRACT_NOT_FORMALIZED`; otra empresa responde 404. |
| C02-02 | `gov_contracts`, sus asignaciones y sus garantías no reciben ningún UPDATE ni DELETE por CNT-02. La ficha del contrato y su `huella` siguen idénticas después de cualquier modificación. |
| C02-03 | Tipos: `ADENDA`, `PRORROGA`, `MODIFICACION` y `VARIACION`. El tipo clasifica el instrumento y no produce efectos por sí mismo: los efectos son los cambios declarados (plazo, monto y condiciones), que respalda el soporte. Única regla por tipo: PRORROGA exige `nueva_fecha_fin`. |
| C02-04 | La historia es lineal. Como mucho hay **un borrador abierto por contrato** (índice único parcial). Al formalizar, `numero = último + 1` y `previous_amendment_id` apunta a la última modificación formalizada (nulo para la primera, cuya base es el contrato), con `UNIQUE (contract_id, numero)` y `UNIQUE (previous_amendment_id)`. El borrador guarda `base_numero`, el número de modificaciones formalizadas cuando se creó. Si al formalizar ya no coincide, responde 409 `GOV_CONTRACT_AMENDMENT_STALE`. |
| C02-05 | Proyección efectiva a la fecha D: es la última modificación formalizada con `vigente_desde ≤ D`, que aporta `monto_nuevo` y `fecha_fin_nueva`. Si no hay ninguna, rige el original. Las modificaciones con `vigente_desde > D` aparecen como «programadas». La base de un borrador nuevo es siempre la **última** modificación formalizada, aunque sea futura. |
| C02-06 | Plazo: `nueva_fecha_fin > fecha_fin` de la base (solo extensión; acortar el plazo es materia de CNT-07/CNT-08). Al formalizar se guardan `fecha_fin_anterior` y `fecha_fin_nueva`, y un CHECK lo impone. Sin cambio de plazo, `fecha_fin_nueva = fecha_fin_anterior`. |
| C02-07 | Monto: el cliente envía solo `delta_monto` (distinto de 0, con 2 decimales). El servidor deriva `monto_nuevo = monto_anterior + delta_monto` y exige `monto_nuevo > 0`. Al formalizar se guardan `monto_anterior`, `delta_monto` y `monto_nuevo`, y el CHECK `monto_nuevo = monto_anterior + COALESCE(delta_monto, 0)` lo impone. No se aceptan valores divergentes. |
| C02-08 | Cobertura para cualquier modificación:<br>• `existente_valida` = Σ de las asignaciones CNT-01 del contrato y de sus modificaciones formalizadas cuya CDP sigue VIGENTE.<br>• `requerida_adicional = max(monto_nuevo − existente_valida, 0)`.<br>• La cobertura adicional del borrador debe sumar **exactamente** `requerida_adicional`; si es 0, no se admiten asignaciones.<br>Cada CDP adicional: VIGENTE, de la empresa, con ejercicio APROBADO o RECONDUCIDO, moneda canónica igual a la del contrato, expediente nulo o igual al del contrato, y monto ≤ saldo libre (H07, contando **todos** los reclamos formalizados, incluidos los del propio contrato). Todas las CDP adicionales de un borrador son del mismo ejercicio. Fallo: 409 `GOV_CONTRACT_AMENDMENT_COVERAGE_INSUFFICIENT`. No se crea ninguna CDP ni ningún compromiso. |
| C02-09 | Con `delta_monto < 0`: si los compromisos VIGENTES del expediente (en moneda canónica) son mayores que `monto_nuevo`, responde 409 `GOV_CONTRACT_COMMITMENT_EXCEEDS_AMOUNT`. Si hay compromisos en otra moneda, responde 409 `GOV_CONTRACT_COMMITMENT_NOT_COMPARABLE`. El usuario ajusta antes en BUD-08; CNT-02 no reescribe BUD-08. |
| C02-10 | No hay campo para cambiar el objeto. El objeto mostrado es siempre el del contrato (`CONTRACT_OBJECT_CHANGE_ALLOWED=0`). |
| C02-11 | No hay campo para cambiar el contratista (`CONTRACTOR_CHANGE_ALLOWED=0`). |
| C02-12 | La moneda de la modificación es la moneda canónica del contrato, fijada por el servidor (`CONTRACT_CURRENCY_CHANGE_ALLOWED=0`). |
| C02-13 | Soporte DOC-08 obligatorio: documento de la empresa, vinculado al expediente, con versión vigente y sin sellar. Se guardan `document_id`, la versión, `sha256` y el título, además de `referencia_instrumento`. Al formalizar se revalida (versión, sha256 e integridad), se sella y se congela el vínculo. No hay firma electrónica DOC-05. |
| C02-14 | Firmante: cargo de la empresa con FIRMAR × CONTRATACIONES vigente hoy (`_autoridad_valida`) y autoridad funcional del actor (`exigir_autoridad_funcional`). Permisos `gobierno_contratos:manage` (borrador) y `gobierno_contratos:formalize` (SENSITIVE, con MFA). |
| C02-15 | El límite del firmante se compara con el **monto efectivo nuevo**, no con el delta. Así, una autoridad con límite pequeño no puede aprobar incrementos parciales sucesivos. |
| C02-16 | Si la moneda del contrato y la del límite difieren, se usa TRE-09 a la fecha de formalización (H05). Sin tasa: 422 `GOV_OFFICIAL_RATE_REQUIRED`. Exceso: 409 `GOV_CONTRACT_SIGNER_AMOUNT_EXCEEDED`. La conversión se guarda en la fotografía (H06). No hay un segundo motor de FX. |
| C02-17 | Fechas:<br>• `fecha_instrumento ≤ hoy` y `vigente_desde ≥ hoy`: no hay efecto retroactivo sobre fotografías ya emitidas.<br>• `vigente_desde ≥ fecha_instrumento`.<br>• `vigente_desde ≥` el `vigente_desde` de la última modificación formalizada.<br>• Un contrato cuya fecha de fin efectiva (base) ya pasó no recibe modificaciones: 409 `GOV_CONTRACT_AMENDMENT_CONTRACT_EXPIRED` (OQ-CNT02-03).<br>`motivo` es obligatorio, de 10 a 2000 caracteres. |
| C02-18 | Concurrencia, con el orden de bloqueo contrato → modificación → expediente → CDP (por id) → estructura del firmante:<br>• dos borradores simultáneos: uno se crea y el otro recibe 409 `GOV_CONTRACT_AMENDMENT_DRAFT_EXISTS`;<br>• dos formalizaciones del mismo borrador: una tiene éxito y la otra recibe 409 `GOV_CONTRACT_AMENDMENT_STALE`, por la versión;<br>• dos CDP compartidas: no hay sobrerreclamo. |
| C02-19 | Aislamiento: toda consulta se filtra por `company_id` del contexto. Las rutas de otra empresa responden 404. Las rutas nuevas entran en el barrido ISO. |
| C02-20 | Auditoría (`entity_type = GovernmentProcurementFile`, id del expediente, sin importes): `GOV_CONTRACT_AMENDMENT_DRAFT_CREATED`, `_DRAFT_UPDATED`, `_DRAFT_DISCARDED`, `_FORMALIZED` y `_SIGNER_BLOCKED`. Cronología del expediente: clase `CONTRATO`, «Prórroga CT-2026-0001/PR-001 formalizada». |
| C02-21 | CNT-03, CNT-04, CNT-06 y CNT-07 no se implementan. No hay hitos, entregables, valuaciones, supervisores, penalidades ni terminación. |
| C02-22 | Una E2E del recorrido del sponsor (§58 del encargo) y del delta de CNT-01 (§59), a 1280, 390 y 320, con Axe (AXE_NEW_SERIOUS=0), más el humo en la UAT de P2. |

## 4. Código del instrumento

Prefijos: ADENDA `AD`, PRORROGA `PR`, MODIFICACION `MO` y VARIACION `VA`. Hay una sola secuencia por contrato para todos los tipos, asignada al formalizar bajo el bloqueo del contrato, con el formato `{codigo_contrato}/{prefijo}-{numero:03d}`, por ejemplo `CT-2026-0001/AD-001` y después `CT-2026-0001/PR-002`. Es único por empresa.

## 5. Estados

`BORRADOR → FORMALIZADA`. El borrador se puede descartar (DELETE, con auditoría); la modificación formalizada no.

**ANULADA no se implementa.** La LCP solo prevé modificar (arts. 130–135) y declarar la nulidad del contrato (art. 121, CNT-07/08), y no regula anular un instrumento modificatorio. Para corregir una modificación formalizada se formaliza **otra** posterior que la rectifique (versionado). Queda registrado como OQ-CNT02-02.

## 6. Preguntas y observaciones abiertas (no bloquean el ciclo)

- **OQ-CNT02-01.** Posibles topes del Reglamento (N12) sobre aumentos o plazos de solicitud; no hay copia local. No se inventan.
- **OQ-CNT02-02.** Anulación de una modificación formalizada: no se construye; se rectifica con otra modificación.
- **OQ-CNT02-03.** Modificar un contrato con el plazo vencido: se bloquea, por ser lo más conservador. La dueña puede relajarlo.
- **OBS-CNT02-LIBERACION-01.** Una reducción no libera cobertura: las asignaciones formalizadas siguen reclamando la CDP, porque son inmutables. Liberar exigiría una «liberación» versionada y decide la dueña.
- **OBS-CNT01D-01** y **OBS-CNT01D-02**: ver el delta de CNT-01.
