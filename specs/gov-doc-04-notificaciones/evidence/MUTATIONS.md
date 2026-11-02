# GOV-DOC-04 · mutaciones de negocio (T010, herramienta de Claude `mutar07b.py`)

Método: un SEARCH único por mutante → REPLACE; purga de `__pycache__` y `PYTHONDONTWRITEBYTECODE=1`; restauración verificada por sha256
(41/41 restaurados). Interfaz: `vitest run src/modules/gobierno/notificaciones src/modules/gobierno/actos src/layout/Sidebar.test.tsx`.
Backend: `pytest tests/test_gov_doc04_notificaciones.py tests/test_gov_doc02_actos.py` sobre PostgreSQL con el analizador real.

## Interfaz · 22 mutantes · 22 muertos

| ID | Mutación | Resultado | Prueba que lo mata |
|---|---|---|---|
| UN-01 | menú sin la entrada «Notificaciones administrativas» | KILLED | GSB-10 |
| UN-02 | prensa +14 días en vez de +15 | KILLED | INT-07 |
| UN-03 | sin oficio fijado basta un documento | KILLED | INT-08b |
| UN-04 | constancias ya usadas vuelven a ofrecerse | KILLED | INT-07 |
| UN-05 | el oficio se ofrece como constancia | KILLED | INT-04 |
| UN-06 | la constancia no se vacía al elegirla como oficio | SURVIVED → KILLED | INT-10 (añadida, T008c5) |
| UN-07 | fecha anterior al acto aceptada | KILLED | INT-05 |
| UN-08 | fecha futura aceptada | KILLED | INT-05 |
| UN-09 | documentos inactivos ofrecidos | KILLED | INT-08b |
| UN-10 | «Publicar en prensa» sin intento fallido | KILLED | NTP-02 |
| UN-11 | «Corregir datos» con intentos registrados | KILLED | NTP-03 |
| UN-12 | conflicto de versión no mostrado | KILLED | NTP-08 |
| UN-13 | intentos con la capacidad de consulta | KILLED | NTP-04 |
| UN-14 | año de la consulta del acto mal tomado | KILLED | NDA-02 (y 9 más) |
| UN-15 | duplicado sin error en «Cédula o RIF» | KILLED | NDA-08 |
| UN-16 | «Faltan N» solo con más de uno | KILLED | NDA-04 |
| UN-17 | apoderado sin cédula aceptado | KILLED | DST-03 |
| UN-18 | recursos de 1 carácter aceptados | KILLED | DST-01 |
| UN-19 | motivo de anulación de 1 carácter | KILLED | ANU-02 |
| UN-20 | lista sin la marca «(prensa)» | KILLED | NTL-03 |
| UN-21 | el acto particular vuelve a ofrecer el panel de DOC-02 | KILLED | ACP-40 |
| UN-22 | sección «Notificaciones» oculta en el acto particular | KILLED | ACP-40, ACP-41 |

## Backend · 19 mutantes · 15 muertos · 4 equivalentes · 0 supervivientes

| ID | Mutación | Resultado | Prueba que lo mata / justificación |
|---|---|---|---|
| BN-01 | prensa: notificada a los 14 días | KILLED | GN-07 |
| BN-02 | prensa sin intento personal fallido | KILLED | GN-07 |
| BN-03 | acto eficaz con algún destinatario pendiente | KILLED | GN-07 |
| BN-04 | las anuladas cuentan para la eficacia | KILLED | GN-09 |
| BN-05 | eficacia con la fecha más temprana | KILLED | GN-07 |
| BN-06 | fecha de eficacia = fecha del intento (sin +15) | KILLED | GN-07 |
| BN-07 | soporte de eficacia = oficio | KILLED | GN-06 |
| BN-08 | alta sobre un acto no particular | KILLED | GN-03 |
| BN-09 | intento anterior a la fecha del acto | SURVIVED → KILLED | GN-05b corregida (T001c): la prueba solo corría `if HOY.day > 2` y con datos que no eran anteriores al acto |
| BN-10 | intento con fecha futura (servicio) | EQUIVALENT | `IntentoIn._valida_fecha` rechaza «No puede ser futura» antes de llegar al servicio; la comprobación del servicio es defensa en profundidad |
| BN-11 | constancia igual al oficio (servicio, `excluir=None`) | EQUIVALENT | `IntentoIn._valida_documento_id` exige constancia ≠ oficio de la entrada y el servicio exige que ese oficio sea el fijado: no hay entrada válida que llegue a la rama |
| BN-12 | la entrega no notifica | KILLED | GN-05 |
| BN-13 | vínculos del oficio y la constancia sin congelar | KILLED | GN-06 |
| BN-14 | destinatario duplicado aceptado (servicio) | EQUIVALENT en PostgreSQL | el índice único parcial `uq_gov_notifications_act_destinatario` devuelve el mismo 409; en SQLite solo protege el servicio y la suite GN es solo PostgreSQL (como la de DOC-02): **riesgo residual LOW** registrado |
| BN-15 | el intento no lleva el acto a eficaz | KILLED | GN-06 |
| BN-16 | DOC-02 vuelve a aceptar `/eficacia` en actos particulares | KILLED | GN-11 |
| BN-17 | prensa habilitada con cualquier intento personal (salida) | EQUIVALENT | invariante de estado: una notificación PENDIENTE solo puede tener intentos personales FALLIDA (ENTREGADA la pasa a NOTIFICADA) |
| BN-18 | recursos vacíos aceptados al crear (convergencia T012) | KILLED | GN-21 |
| BN-19 | fecha determinante invertida (convergencia T014) | KILLED | GN-07 |

Total: 41 mutantes · 37 muertos (2 tras añadir o corregir su prueba) · 4 equivalentes justificados · 0 supervivientes · 41/41 restaurados.
