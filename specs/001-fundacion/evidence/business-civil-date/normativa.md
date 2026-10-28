# Registro normativo · BUSINESS CIVIL DATE (03) · 2026-10-28

**Método.**
- Búsqueda en fuentes primarias oficiales. Blogs y despachos solo sirvieron de pista.
- No se pudo conectar con `seniat.gob.ve`, y el certificado TLS de `bcv.org.ve` no se pudo validar. Ningún texto procede de esos portales.
- Cuando el PDF de la Gaceta estaba en un servidor no oficial, se indica.
- Las copias locales (fuera de Git, datos no confiables, solo lectura) llevan su SHA-256.

| SOURCE_ID | AUTHORITY | DOCUMENT · NUMBER | GACETA · PUBLICACIÓN | VIGENCIA | URL | SHA-256 de la copia | ARTÍCULO | REGLA EXTRAÍDA | VERIFICADA | CLASE | EFECTO EN EL PRODUCTO |
|---|---|---|---|---|---|---|---|---|---|---|---|
| HL-1 | Presidencia de la República | Decreto N.º 2.301 (15-04-2016) | G.O. N.º 6.224 Extraordinario, 18-04-2016 | 01-05-2016, 02:30 a. m. | http://historico.tsj.gob.ve/gaceta_ext/abril/1842016/E-1842016-4551.pdf | `c5130db7…a7680758` | arts. 1–3 | Hora legal = UTC−4; a las 02:30 del 01-05-2016 se cuentan las 03:00 | **sí** | OFFICIAL_REQUIREMENT | `ZoneInfo("America/Caracas")`. La IANA modela la transición en 2016-05-01T07:00Z: coincide. Sin horario de verano |
| HL-2 | Presidencia | Reforma de la Ley de Metrología (2007), UTC−4:30 | G.O. 38.819 (fecha NO VERIFICADA) | 09-12-2007 | — | — | — | — | **no** · NORMATIVE_SOURCE_MISSING | — | Sin efecto: no se reinterpretan datos históricos. La IANA modela 2007-12-09T07:00Z |
| FA-1 | SENIAT | Providencia SNAT/2011/00071 (facturación) | G.O. 39.795, 08-11-2011 | Desde la publicación | Copia no oficial (transcripción) | `3b5d44f1…ce861cd20` | arts. 13.6, 13.14, 14.4 y 16.5 | Formato libre: fecha de emisión de 8 dígitos, sin hora. Máquina fiscal: hora y fecha. En divisas: tipo de cambio aplicable | parcial | OFFICIAL_REQUIREMENT | La fecha de emisión es una fecha civil legal (Caracas). Sin cambio en 03 |
| FA-2 | SENIAT | Providencia SNAT/2024/000102 (medios digitales) | G.O. 43.032, 19-12-2024, págs. 466.518–466.519 | Desde la publicación | Imagen de la Gaceta (copia de un despacho) | `a36316a9…ed19d` | arts. 7.6, 7.15, 8, 10.2 y 22 | «Fecha y hora de emisión», DDMMAAAA y HH.MM.SS | sí | OFFICIAL_REQUIREMENT | `issued_at` es INSTANT y se muestra en hora legal (Caracas): AD-8 |
| IVA-1 | Asamblea Nacional Constituyente | Ley del IVA (reforma) | G.O. 6.507 Ext., 29-01-2020 | — | Imagen de la Gaceta (copia) | `43267fd9…6f3e` | arts. 13, 25, 32, 56 y 69 | Período = mes calendario; las operaciones se registran en el mes en que se perfeccionan; el hecho imponible de bienes es lo primero entre emisión, pago o entrega | sí | OFFICIAL_REQUIREMENT | **Los libros no se filtran por fecha de emisión** → OD-TIME-11 |
| IVA-2 | Ejecutivo | Reglamento General de la Ley del IVA | G.O. 5.363 Ext., 12-07-1999 | — | — | — | arts. 70–78 | — | **no** · NORMATIVE_SOURCE_MISSING | — | LEGAL_VALIDATION_REQUIRED para libros |
| RET-1 | SENIAT | Providencia SNAT/2025/000054 (agentes de retención de IVA) | G.O. 43.171, 16-07-2025, págs. 468.767–468.769 | 01-08-2025 (art. 20) | Imagen de la Gaceta (copia) | `ac1e66a1…b0460f` | arts. 7, 13, 14, 16, 20 y **21 (deroga la SNAT/2015/0049)** | Retención al pago o abono, lo primero; enteramiento quincenal (días 1–15 y 16–fin); comprobante a más tardar en los 2 primeros días hábiles del período siguiente, registrado en el período de su emisión o entrega | sí | OFFICIAL_REQUIREMENT | Sin implementación. Deuda FISCAL-RETENCION-NORMA-2025: verificar qué providencia cita el producto |
| TC-1 | ANC | Ley del IVA | G.O. 6.507 Ext. | — | ídem | ídem | art. 25 | Tipo de cambio del día del hecho imponible; en día no hábil financiero, el del día hábil **siguiente** | sí | OFFICIAL_REQUIREMENT | Sin cambio. Deuda RATE-NON-BUSINESS-DAY-RULE (frente al arrastre de la selección de tasas): LEGAL_VALIDATION_REQUIRED |
| TC-2 | BCV y Ejecutivo | Convenio Cambiario N.º 1 | G.O. 6.405 Ext., 07-09-2018 | — | Transcripción (secundaria) | — | arts. 8.a, 9 y 84 | Tipo de referencia del BCV; base imponible al tipo «vigente para la fecha de la liquidación» | parcial | OFFICIAL_REQUIREMENT (sin verificar) | Choca con TC-1 → LEGAL_VALIDATION_REQUIRED |
| PL-1 | ANC | Código Orgánico Tributario | G.O. 6.507 Ext. | — | ídem | ídem | art. 10 | Plazos en días: hábiles salvo disposición contraria; un vencimiento en día inhábil se prorroga | sí | OFFICIAL_REQUIREMENT | El producto no lo usa hoy; anotado |

**Sin fuente primaria:**
- HL-2;
- IVA-2;
- el texto oficial del Convenio Cambiario;
- la hora y la «fecha valor» de la publicación del BCV;
- la ratificación del Decreto 2.301 (art. 4);
- posibles modificaciones de la 0071 (SNAT/2018/0141, citada en la 2024/000102).

**Ambigüedades que se escalan, no se resuelven:**
- La «fecha valor» del BCV frente al «día hábil siguiente» (TC-1).
- El art. 84 del Convenio frente al art. 25 de la Ley del IVA.
- La definición de «día hábil del sector financiero».
- El período del libro cuando el hecho imponible y la factura caen en meses distintos.
- En retenciones, el período de la retención frente al período de registro del comprobante.

**Resultado:** NORMATIVE_RESEARCH_COMPLETE = 1 · NORMATIVE_SOURCES = 10 · NORMATIVE_SOURCE_MISSING = 1 (HL-2, IVA-2 y el texto del Convenio). Ninguna regla fiscal se implementa en 03.
