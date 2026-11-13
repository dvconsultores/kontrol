# FUENTES · D-GOV-02 Profundidad presupuestaria (2026-11-13)

Solo se usaron fuentes custodiadas en el repositorio (`requerimientos/gobierno/`) o fichadas en la Biblioteca Normativa. No se descargó nada nuevo. No se tocó el SNAT.

| Id | Fuente | Clase | Custodia (sha256, 16 caracteres) | Qué aporta |
|---|---|---|---|---|
| IR | Ingeniería de Requerimientos KONTROL Gobierno v1.0, §7.2 (GOV-BUD-001..018) y §15 (D-GOV-02) | — | `8f86615f63ecfa0b` | Los 18 requisitos BUD y el criterio de cierre de D-GOV-02: «Confirmar si v1.0 cubre formulación completa o arranca con presupuesto aprobado + ejecución» |
| BN | Biblioteca Normativa Oficial v1.0 | — | `4a980bb96e6b3f79` | Clases de verificación N03–N10, N24, N30, N31 y N37 |
| N24 | LOPPM, G.O. 6.015 Ext. (copia de la Alcaldía), Título V Cap. VI, arts. 228–250 | **A** | `a6794e9eef64d5d9` (escaneada; leída por imagen, págs. 80–81 de la Gaceta) | El régimen legal del presupuesto municipal (detalle abajo) |
| N03 | LOAFSP, G.O. 6.210 Ext. | A (BN) | fichada, sin copia en el repositorio | Autoridad y soporte de toda operación financiera |
| N04 | Reglamento N.º 1 LOAFSP, G.O. 5.781 Ext. | A (BN) | fichada, sin copia en el repositorio | Separar formulación, aprobado, modificaciones y ejecución; versionar ejercicio, clasificador y niveles |
| N05 | Reglamento N.º 3 LOAFSP | A | fichada (base de TRE-02) | Separar caja de presupuesto (ya aplicado en TRE-02) |
| N06 | Reglamento N.º 4 LOAFSP | A | fichada | Momentos y ledger inmutable |
| N07 | Instructivo ONAPRE 20 (entidades **federales**) | C | no custodiada | No aplica a un piloto **municipal** (reclasificar: ver la memoria del piloto) |
| N08 | Instructivo ONAPRE 21 (ordenanza de presupuesto municipal), ed. ago-2023 | C | **no custodiada** | Formularios y estructura de formulación municipal |
| N09 | Instructivo ONAPRE 3 (modificaciones) | C | **no custodiada** | Tipos y niveles de modificación en el ámbito nacional |
| N10 | Clasificador presupuestario ONAPRE | C | **no custodiada** | Códigos y denominaciones por ejercicio |
| N30, N31 | Plan de la Patria; LOPPP | A | fichadas | Plan, metas e indicadores |
| N37 | Ordenanzas y manuales de Naguanagua | C | solo la Gaceta 512 Ext. (`563f37fcf9452860`), que es de **actividades económicas**, no de presupuesto | Falta la ordenanza de presupuesto del ejercicio y el manual presupuestario (NAGUANAGUA_MISSING_DOCUMENTS) |

## LOPPM, Cap. VI «Del sistema presupuestario y contable» (clase A, en custodia)

| Art. | Contenido (paráfrasis fiel) | Consecuencia para KONTROL |
|---|---|---|
| 228 | El presupuesto es un instrumento de planificación con equilibrio fiscal | Gastos ≤ ingresos (ver 240) |
| 229 | Presupuesto aprobado anualmente por el Concejo en la **ordenanza de presupuesto anual de ingresos y gastos** | El aprobado nace de un acto normativo del Concejo |
| 230 | Rige la LOPPM, las ordenanzas y las leyes; se ajusta «en cuanto sea posible» a las disposiciones técnicas de ONAPRE | ONAPRE es técnica (clase C), no la fuente de las reglas estructurales |
| 232 | Presupuesto participativo de inversión: cifra al CLPP en julio | Fase de **formulación** |
| 233 | Proyecto de ordenanza y **POA**, presentados por el alcalde al Concejo antes del 1.º de noviembre | Formulación con plazo legal |
| 234 | Sanción antes del 15 de diciembre; si no, **reconducción** del presupuesto anterior | Estado RECONDUCIDO del ejercicio |
| 235 | Publicación del reconducido con sus ajustes en la Gaceta | Acto y soporte del reconducido |
| 236 | Sin sanción al 31 de marzo, el reconducido queda definitivo hasta el 31 de diciembre | Transición con fecha |
| 237 | Rendición de cuentas y balance de ejecución | Reporte de ejecución (REP-01) |
| 238 | Ingresos: ramos, estimación y otros recursos | Presupuesto de ingresos |
| 239 | Gastos por **sectores, programas, subprogramas, proyectos y categorías equivalentes**, con las **partidas** según las disposiciones técnicas de ONAPRE | Estructura programática + partida: estructura con fuente A; los códigos son de ONAPRE (C) |
| 240 | Gastos ≤ ingresos; admite hasta la mitad de las existencias del Tesoro no comprometidas | Validación del aprobado |
| 241 | Partida «Rectificaciones del Presupuesto» ≤ 3 % de los ingresos estimados; la dispone el alcalde; no se incrementa por traspaso | Tipo de modificación con tope legal |
| 242 | Los créditos son el **límite máximo para gastar**; **ningún gasto ni pago sin previsión presupuestaria**; el alcalde acuerda **traspasos** dentro de los límites de la ordenanza | Disponibilidad y compromiso; traspasos parametrizados por la ordenanza |
| 243 | Contabilidad según la ONCOP | ACC (D-GOV-04), fuera de esta decisión |
| 244 | El Concejo fija las normas de ejecución y ordenación de pagos | Dato local (N37) |
| 245–246 | Especificar inversiones, operación y aportes; no afectar ingresos salvo por ley | Atributos del crédito |
| 247 | **Créditos adicionales** aprobados por el Concejo a solicitud del alcalde, con 5 fuentes (mayor rendimiento certificado por el Tesorero, economías, existencias del Tesoro certificadas, aportes nacionales o estadales, otras fuentes); **insubsistencias** | Tipos de modificación y fuentes de financiamiento |
| 248 | Las cuentas cierran el 31 de diciembre; después **no** se comprometen ni causan gastos con cargo a ese ejercicio | Cierre |
| 249 | Lo causado y no pagado se paga el año siguiente con la caja existente; lo **comprometido y no causado se imputa automáticamente al ejercicio siguiente** | Reconducción de saldos entre ejercicios |
| 250 | El ejercicio va del 1.º de enero al 31 de diciembre | Coincide con OD-ORG02-01 (ejercicio = año calendario) |
