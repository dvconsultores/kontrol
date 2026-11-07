# N40_LEGAL_REVIEW_PACKET

Para: profesional identificado por el ente o el sponsor. Este paquete no valida nada: pide revisar solo lo material. Copias y hashes en `SOURCE_HASHES.txt`.

## Instrumentos

| Item | Instrumento | Copia | Requisitos afectados |
|---|---|---|---|
| N40-01 | Providencia 009-10, clasificación de la información | Emisor, sin firma | GOV-DIG-009, GOV-HR-005, RNF-GOV-011, RNF-GOV-021; DOC-01 si se incorpora |
| N40-02 | Providencia 016, G.O. 38.636 | Facsímil en el emisor | GOV-DOC-006, GOV-DOC-002 |
| N40-03 | Norma 032 v4.4 | Emisor, firmada | GOV-DOC-006, GOV-DOC-002 |
| N40-05 | Norma 054 | Emisor; firma no validada por pdfsig | GOV-DOC-006 |
| N40-08 | Decreto 5.232 | G.O. 6.977 Ext. | Competencia |
| N40-NF1, NF2 | Normas de interoperabilidad y seguridad del intercambio | No localizadas | GOV-DIG-004, RNF-GOV-015 |

## Preguntas

1. ¿Cuál es el texto oficial de la Providencia 009-10? Se cita G.O. 39.578 de 21-12-2010 por fuente secundaria. La copia de SUSCERTE termina en el art. 34 y la transcripción secundaria en el art. 36, con un art. 4 de competencia. ¿Sigue vigente?
2. Su art. 2 obliga a la Administración Pública Nacional. ¿Obliga o sirve de referencia para estados, municipios y entes descentralizados?
3. Si el ente está sujeto, ¿debe el expediente electrónico registrar los cuatro niveles, heredar la clasificación más alta (art. 17), identificarla en cada página (art. 24) y destruir conforme al art. 28?
4. ¿La verificación de firma exige certificados de la cadena del Estado en todo caso (N27 art. 24), o admite firma de otro tipo según N29? ¿Cuándo basta conservar la firma sin verificarla?
5. ¿Existen normas técnicas vigentes del operador de interoperabilidad, o de seguridad del intercambio (N28 arts. 26 a 28)? ¿Quién es hoy el operador?
6. Tras el Decreto 5.232, ¿qué normas de seguridad dicta SUSCERTE y cuáles el Centro Nacional?
7. Confirmar que ninguna norma técnica vigente regula bitácora, vínculo usuario-cargo o separación del administrador técnico en sistemas de gestión pública. Este ciclo retiró N40 de ORG-06, CTL-02, CTL-03 y DOC-07 porque no halló ninguna.

## Efecto de las respuestas

| Pregunta | Si la respuesta es sí | Si es no |
|---|---|---|
| 2 y 3 | Se incorpora la clasificación a DOC-01, DIG-02 y HR-02 | Se retira N40-01 de esos procesos |
| 4 | DOC-05 exige verificación en cadena | DOC-05 se reduce a conservar evidencia |
| 5 | DIG-03 se diseña sobre esas normas | Se documenta la ausencia |
| 7 | Sin cambio | Se reponen los bloqueos con la regla concreta |

PROFESSIONAL_VALIDATION_REQUIRED no equivale a decisión de la dueña. La identidad del profesional sigue sin designar (ítem 10 del checklist de freeze).

## Adición de ORG-04 (2026-11-07)

| Pregunta | Si la respuesta es sí | Si es no |
|---|---|---|
| ¿La «designación temporal» de la práctica municipal es una encargaduría (LEFP y LOPPM)? | Se mantiene bajo la figura ENCARGADURIA | Se añade una figura nueva sin cambiar el modelo de asignación |

La respuesta no bloquea ORG-04: la figura existe y el acto soporte queda registrado.
