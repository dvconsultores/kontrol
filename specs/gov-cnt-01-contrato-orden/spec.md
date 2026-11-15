# Spec · CNT-01 · Contrato u orden derivada de la adjudicación (GOV-CNT-001)

- **Línea:** KONTROL Gobierno · P2.
- **Requisito:** GOV-CNT-001 (P0; N11, N12 y N03).
- **Fuentes:** `FUENTES.md`.
- **Entrada:** `efcf4b2`, Alembic `0112_gov_bud06_certificacion`.

## 1. Objetivo

La Unidad Contratante prepara, a partir de una adjudicación vigente, el contrato o la orden de compra o de servicio. La Máxima Autoridad
lo formaliza.

El instrumento conserva, sin que nadie pueda reescribirlos:
- el objeto del expediente;
- el adjudicatario de la oferta;
- el total declarado con tributos y su moneda.

Además registra:
- el plazo que fija el instrumento firmado;
- la cobertura presupuestaria con certificaciones (CDP) de BUD-06;
- las garantías de PROC-10 que lo acompañan.

Al formalizarse queda congelado y es trazable hasta el expediente, la oferta, la decisión y el acto.

**Recorrido del sponsor:**
1. Expediente › Decisión ADJUDICADA › «Crear contrato u orden».
2. En el borrador: tipo, plazo, referencia, documento, CDP, garantías y firmante.
3. «Formalizar».
4. Ficha en Gobierno › Contratos › Contratos y órdenes.

## 2. Alcance

**Dentro:**
- crear el borrador desde la adjudicación;
- editar los campos propios del borrador;
- vincular CDP con la porción asignada;
- vincular garantías existentes;
- formalizar con autoridad FIRMAR × CONTRATACIONES y su límite;
- ficha, lista, cronología del expediente y auditoría.

**Fuera, sin absorberlo:**
- CNT-02: adendas, prórrogas y variaciones;
- CNT-03: ejecución, hitos y recepciones;
- CNT-04: supervisor;
- CNT-05 a CNT-09: pagos, penalidades, terminación, expediente contractual y alertas;
- BUD-08: compromiso presupuestario;
- PROC-05: RNC/SNC;
- adjudicación parcial (OBS-PROC08-PARCIAL-01);
- conversión de moneda (TRE-09);
- constancia PDF interna, que es opcional según el encargo §34. La ficha la sustituye en pantalla y el documento firmado es la autoridad.

## 3. Contratos (C01-01 a C01-24)

| Id | Contrato |
|---|---|
| C01-01 | **Requisito de adjudicación.** Solo se crea desde la decisión del expediente con `estado = VIGENTE`, `resultado = ADJUDICADA` y `offer_id` no nulo. Cualquier otro resultado o estado responde 409 `GOV_CONTRACT_AWARD_REQUIRED`. El expediente debe estar ABIERTO (409 `GOV_PROCUREMENT_FILE_NOT_OPEN`) |
| C01-02 | **Adjudicación vigente.** El backend busca él mismo la decisión vigente del expediente: no recibe `decision_id` ni `offer_id`. Al formalizar vuelve a comprobar que esa decisión sigue VIGENTE y ADJUDICADA con la misma oferta. Si no, 409 `GOV_CONTRACT_AWARD_NOT_CURRENT` |
| C01-03 | **Oferta adjudicada.** El contratista, el monto y la moneda salen de la oferta de la decisión. Una oferta sin monto declarado no permite crear el borrador: 422 `GOV_CONTRACT_OFFER_AMOUNT_REQUIRED` |
| C01-04 | **Contratista.** Se guarda una fotografía con `contratista_nombre`, `contratista_documento` y `contratista_representante` (si existe) y la referencia de la oferta `R-NNNN`. No hay maestro de contratistas |
| C01-05 | **Objeto.** Fotografía de `GovernmentProcurementFile.objeto` y `numero`. Hay una `descripcion_complementaria` aparte, opcional y editable en borrador, que nunca sustituye al objeto |
| C01-06 | **Monto.** `monto = total_con_tributos` de la versión vigente del monto de la oferta (`amount_id` guardado), sin recálculo ni redondeo (`Numeric(18,2)`). Si el cliente envía un monto, se ignora: la API no tiene ese campo |
| C01-07 | **Moneda.** `moneda` = moneda de ese monto. No se edita ni se convierte (`AUTOMATIC_CURRENCY_CONVERSION = 0`) |
| C01-08 | **Tipo de instrumento.** `CONTRATO`, `ORDEN_COMPRA` u `ORDEN_SERVICIO` (LCP art. 6, num. 32). Lo elige el usuario y es obligatorio para formalizar. No se deduce de la modalidad |
| C01-09 | **Plazo.** `fecha_inicio` y `fecha_fin` del instrumento, obligatorias para formalizar, con `fecha_fin >= fecha_inicio` (422 `GOV_CONTRACT_INVALID`). No se toma la fecha del expediente y no se inventa una duración |
| C01-10 | **CDP.** Solo se vinculan CDP del mismo ente, en estado **VIGENTE**, con `moneda` igual a la del contrato y de **un solo ejercicio**. Si la CDP tiene `procurement_file_id`, debe ser el del contrato. Si no cumple, 422 `GOV_CONTRACT_CERTIFICATE_INVALID` con el motivo |
| C01-11 | **Cobertura.** Cada vínculo lleva `monto` > 0 y menor o igual que el saldo libre de la CDP (`CDP.monto` − asignado a contratos FORMALIZADOS). En borrador, la suma no puede superar el monto del contrato. Para formalizar, la suma debe ser **exactamente igual** al monto del contrato. Si es menor, 409 `GOV_CONTRACT_COVERAGE_INSUFFICIENT`; si una CDP queda sobreasignada, 409 `GOV_CONTRACT_CERTIFICATE_OVERALLOCATED` |
| C01-12 | **Sin efecto en BUD-08.** CNT-01 no modifica ni la CDP (`monto` y `estado`) ni `disponible_de_credito`, ni crea ni consume compromisos. Solo registra de dónde viene la cobertura (`BUDGET_FINANCIAL_EFFECT = 0`) |
| C01-13 | **Garantías.** Se vinculan instrumentos PROC-10 del mismo expediente, con `offer_id` igual al adjudicado y en estado `REGISTRADA`. No se duplican ni se recalculan. Puede no haber ninguna: la ficha lo dice («Sin garantías vinculadas») y no se infiere ninguna obligación |
| C01-14 | **Documento.** El instrumento contractual es un documento vinculado al expediente (DOC-08), sin sellar y con versión vigente. Se guardan `document_id`, la versión, el número, el `sha256` y el título. Al formalizar, la versión vigente y el `sha256` deben seguir siendo los mismos; si no, 409 `GOV_CONTRACT_DOCUMENT_CHANGED`. No hay firma electrónica (DOC-05) |
| C01-15 | **Autoridad funcional.** Para formalizar se elige el cargo firmante, que debe tener **FIRMAR × CONTRATACIONES** en vigor en la fecha de formalización (si no, 422 `GOV_CONTRACT_SIGNER_INVALID`). Además se llama a `exigir_autoridad_funcional(…, "FIRMAR", "CONTRATACIONES")` (ORG-06). No basta el permiso técnico |
| C01-16 | **Límite del firmante.** Regla AAL aplicada a la competencia FIRMAR × CONTRATACIONES: SIN_LIMITE pasa; MONTO en la misma moneda pasa si `monto ≤ límite`. Si excede, 409 `GOV_CONTRACT_SIGNER_AMOUNT_EXCEEDED`; si la moneda es otra, 409 `GOV_CONTRACT_SIGNER_CURRENCY_MISMATCH`. No hay conversión ni override. Se usa el mismo clasificador que AAL, que se generaliza sin cambiar su comportamiento |
| C01-17 | **Ciclo.** Solo existen `BORRADOR` y `FORMALIZADO`, que el IR llama DRAFT y APPROVED. No hay descarte: un borrador cuya adjudicación dejó de estar vigente queda bloqueado y la ficha lo indica |
| C01-18 | **Formalización.** Repite todas las comprobaciones (C01-02, 03, 06, 07, 09, 10, 11, 13, 14, 15 y 16) con los datos vigentes y bloqueados. Después asigna el código, congela una fotografía JSON con su huella SHA-256, anota la cronología del expediente (clase `CONTRATO`) y audita |
| C01-19 | **Inmutabilidad.** Disparadores de PostgreSQL: un FORMALIZADO no admite UPDATE, nadie puede hacer DELETE y la tabla no admite TRUNCATE. Tampoco en BORRADOR cambian las fotografías (expediente, decisión, oferta, acto, objeto, contratista, monto y moneda). Los vínculos de CDP y garantías solo cambian mientras el contrato está en BORRADOR, y solo con inserción y borrado |
| C01-20 | **Concurrencia.** Crear bloquea el expediente con `FOR UPDATE`; además, `decision_id` es UNIQUE: de dos creaciones, una responde 201 y la otra 409 `GOV_CONTRACT_ALREADY_EXISTS`. La edición y la formalización usan If-Match sobre la versión del contrato (428 o 409 `GOV_CONTRACT_STALE`). Formalizar bloquea con `FOR UPDATE` el contrato, el expediente, las CDP (ordenadas por id) y la estructura del cargo firmante. El código se asigna con un bloqueo consultivo por ente |
| C01-21 | **Aislamiento.** Todo se filtra por `company_id`. Un contrato o expediente de otro ente responde 404 `GOV_CONTRACT_NOT_FOUND` o `GOV_PROCUREMENT_FILE_NOT_FOUND`, y una CDP, garantía, documento o cargo de otro ente responde 422 |
| C01-22 | **Auditoría.** `GOV_CONTRACT_DRAFT_CREATED`, `GOV_CONTRACT_DRAFT_UPDATED` (con la lista de campos), `GOV_CONTRACT_FORMALIZED` y `GOV_CONTRACT_SIGNER_BLOCKED` (rechazo, tras deshacer la transacción). La entidad es `GovernmentProcurementFile` y el id, el del expediente, para que CTL-01 vea las acciones. No se auditan importes |
| C01-23 | **Frontera con CNT-02.** No hay endpoint que modifique un FORMALIZADO. Las adendas, prórrogas y variaciones serán registros nuevos de CNT-02 |
| C01-24 | **E2E y UAT.** El recorrido del sponsor (encargo §50), con sus negativas, a 1280, 390 y 320 px, con Axe sin violaciones serias nuevas y con humo en la UAT de P2 |

## 4. Código del instrumento

`{PREFIJO}-{AAAA}-{NNNN}`:
- **Prefijo:** `CT` (contrato), `OC` (orden de compra) u `OS` (orden de servicio).
- **AAAA:** año de la fecha de formalización (hora de Caracas).
- **NNNN:** secuencia por ente, prefijo y año.

El código se asigna **al formalizar**, porque el tipo puede cambiar mientras es borrador. Es único por ente (`UNIQUE (company_id, codigo)`) y se genera bajo `pg_advisory_xact_lock` del ente, con el patrón de `service_identidad`.

En borrador, la pantalla identifica el instrumento como «Borrador · {expediente} · {DEC-NN}». Nunca muestra UUID.

## 5. Permisos

| Permiso | Qué permite | Clase |
|---|---|---|
| `gobierno_contratos:view` | Lista y ficha | STANDARD |
| `gobierno_contratos:manage` | Crear el borrador, editarlo y vincular CDP y garantías | STANDARD |
| `gobierno_contratos:formalize` | Formalizar | **SENSITIVE, con MFA** |

Se conceden a `FUNCIONAL_COMPLETO`.

## 6. SoD

CTL-01 añade a `PROC-03` dos acciones:
- `PROC03_CONTRATO_PREPARAR` → `GOV_CONTRACT_DRAFT_CREATED`;
- `PROC03_CONTRATO_FORMALIZAR` → `GOV_CONTRACT_FORMALIZED`.

La institución puede configurar con ellas una regla, por ejemplo «Decidir el resultado del procedimiento» frente a «Formalizar».
CNT-01 llama a `evaluar_antes_de_actuar` al crear y al formalizar. No se crea ninguna regla ni ninguna matriz nueva.

PROC-11 no tiene una función de firmante (FUNCIONES: SOLICITANTE, RECEPTOR, EVALUADOR, ADJUDICADOR y PAGADOR, este último no disponible). Añadirla sería una regla nueva de la dueña: **OBS-CNT01-SOD-01**. Receptor y pagador del contrato no existen todavía.

## 7. Preguntas y observaciones abiertas (no bloquean el ciclo)

| Id | Tema | Tratamiento en CNT-01 |
|---|---|---|
| OQ-CNT01-01 | Contrato por el monto disponible y contratos plurianuales (LCP arts. 74, párr. 3, y 75) | No se construye: exige cobertura completa y un solo ejercicio. Es decisión de la dueña o jurídica |
| OQ-CNT01-02 | Bolívar en VES (Gobierno) frente a VED (moneda funcional del presupuesto) | Igualdad estricta de códigos: VES y VED no son comparables. Es decisión de la dueña o necesita TRE-09 |
| OBS-CNT01-SOD-01 | Función «firmante del contrato» en PROC-11 | No se crea; CTL-01 sí puede configurarse |
| OBS-CNT01-PROC08-01 | Una TERMINADA o NULIDAD posterior a un contrato FORMALIZADO no se impide en PROC-08 | Pertenece a CNT-07 y CNT-08 (terminación y nulidad del contrato, LCP art. 121) |
| OBS-CNT01-PLAZO-01 | Lapso de 8 días hábiles para la firma (LCP art. 117) | Se informa en la ficha; la alerta pertenece a CNT-09 |
| OBS-CNT01-BUD08-01 | P1 publicó BUD-08 durante el ciclo (6da5b20): los compromisos consumen CDP y dejan un remanente derivado. CNT-01 calcula el saldo libre de una CDP como su monto menos las asignaciones de otros contratos, sin descontar lo consumido por compromisos BUD-08 | No se cambia en este ciclo (frontera fijada `CNT01_REQUIRES_BUD08=0`). La dueña decide si la cobertura del contrato debe usar el remanente de BUD-08 y si el compromiso debe nacer del contrato (`MATERIAL_DECISION_REQUIRED` para el ciclo de integración CNT-01 ↔ BUD-08) |
