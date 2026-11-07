# N40_MATERIALITY_MATRIX

Método: para cada requisito se busca regla, instrumento y artículo, y la relación causal con el diseño. Sin esa prueba no hay MATERIAL_REQUIRED. La ausencia de regla se refiere a los instrumentos del inventario; el corpus es dinámico y por eso la revisión profesional la confirma. Las fuentes «validadas» son clase A o B de la Biblioteca, no una validación jurídica de Claude.

| PROCESS_ID | REQUIREMENT_ID | REQUIREMENT_TEXT | OTHER_VALIDATED_SOURCES | N40_ITEM_ID | N40_EXACT_RULE | MATERIALITY_CLASS | AFFECTED_SUBFEATURE | CAN_CORE_FUNCTION_EXIST_WITHOUT_N40 | OTHER_BLOCKERS | LEGAL_REVIEW_REQUIRED | EVIDENCE | ACTION |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ORG-06 | GOV-ORG-007 | Relacionar cada usuario con identidad, cargo, unidad y alcance institucional; el | N20,N27 | N40-01 | art. 30: entrega según perfil y cargo | REDUNDANT_WITH_VALIDATED_SOURCE | — | Sí | — | Sí | N20 arts. 32 y 39.3 y N27 art. 23 ya exigen acceso autorizado. N40 no fija cómo vincular usuario, cargo y unidad | REMOVE_N40_BLOCKER |
| DOC-01 | GOV-DOC-002 | Mantener documentos originales, versiones, anexos, autor, fecha, firma y hash/in | N27,N29 | N40-02, N40-03 | Firma en cadena de confianza | CONDITIONAL | Verificar firma; clasificación N40-01 no está en el requisito | Sí | Catálogo de procedimientos por medir | Sí | «cuando tecnicamente aplique». Conservar originales, versiones y hash descansa en N27 y N29 | NARROW_N40_BLOCKER |
| DOC-05 | GOV-DOC-006 | Permitir firma electronica cuando sea juridica y tecnicamente procedente, sin as | N29 | N40-02, N40-03, N40-05 | Modelo jerárquico; perfil de certificado y LCR (Norma 032 §§1, 2, anexo F); AC Raíz | MATERIAL_REQUIRED | Firma electrónica | No | D-GOV-08 | Sí | N27 art. 24 exige firmas de la cadena de confianza del Estado; sin esos perfiles no se valida una firma | KEEP_N40_BLOCKER |
| DOC-07 | GOV-DOC-008 | Implementar busqueda por expediente, acto, tercero, contrato, presupuesto, bien  | N27 | N40-01 | art. 30: necesidad de conocer | REDUNDANT_WITH_VALIDATED_SOURCE | Restricción de resultados | Sí | DOC-01, CNT-01, BUD-03, AST-01 | Sí | El control de acceso lo funda N20 art. 32. La búsqueda sigue sin objetos que buscar | REMOVE_N40_BLOCKER |
| CTL-02 | GOV-CTL-002 | Registrar bitacora append-only de autenticacion, consultas sensibles, cambios, a | N18,N20,N27 | Ninguno | Ninguna regla hallada | NOT_MATERIAL | — | Sí | Rol y unidad vía ORG-06; campos de bitácora compartida | Confirmación | N18, N20 y N27 lo sustentan. Ningún instrumento hallado regula la bitácora de un sistema de gestión | REMOVE_N40_BLOCKER |
| CTL-02 | GOV-CTL-003 | Mantener autor, actor efectivo, rol, unidad, IP/sesion tecnica, timestamp y corr | N20,N27 | Ninguno | Ninguna regla hallada | NOT_MATERIAL | — | Sí | Rol y unidad vía ORG-06; campos de bitácora compartida | Confirmación | Igual que GOV-CTL-002 | REMOVE_N40_BLOCKER |
| CTL-03 | GOV-CTL-004 | No permitir al administrador tecnico fabricar autoridad funcional para compromet | N20,N23 | N40-01 | art. 27 par. 2.º: claves de máximo privilegio, otro objeto | NOT_MATERIAL | — | Sí | ORG-06 | Sí | N20 y N23 sustentan la separación; la norma de claves no trata autoridad funcional | REMOVE_N40_BLOCKER |
| DIG-03 | GOV-DIG-004 | Implementar API/intercambio con autenticacion, autorizacion, minimizacion, traza | N28,N27 | N40-NF1, N40-NF2 | N28 arts. 26 a 28 remiten a normas no localizadas | UNDETERMINED | Intercambio institucional | No medido | D-GOV-08 | Sí | La ley remite a normas técnicas obligatorias que no se hallaron; no se puede citar artículo | NO_CHANGE_UNDETERMINED |
| DIG-02 | GOV-DIG-009 | Publicar estados y notificaciones sin exponer informacion reservada o datos inne | N27 | N40-01 | arts. 12 y 16 par. único: clasificar y autorizar antes de publicar | MATERIAL_FOR_SUBFEATURE_ONLY | Clasificación previa a publicar, solo APN | Sí | D-GOV-06 | Sí | Publicar estados es funcional; decidir qué es público depende de la clasificación | NARROW_N40_BLOCKER |
| F21 | GOV-DIG-010 | Usar tecnologias y estandares compatibles con la Ley de Infogobierno y politicas | N27 | N40-NF3, N40-10, N40-11 | Normas instruccionales no localizadas | UNDETERMINED | Estándares del Estado | No medido | — | Sí | Fundamento F21, sin proceso | NO_CHANGE_UNDETERMINED |
| DIG-03 | GOV-DIG-011 | Registrar consentimiento/base de intercambio y restricciones cuando el marco jur | N28 | N40-NF2 | «cuando el marco juridico lo requiera» | CONDITIONAL | Base de intercambio | Sí | D-GOV-08 | Sí | Condicional; DIG-03 mantiene su bloqueo por GOV-DIG-004 | NO_CHANGE_UNDETERMINED |
| DIG-03 | GOV-DIG-012 | Mantener inventario de interoperabilidades, responsable, contrato, SLA, version  | N28,N20 | Ninguno | Ninguna regla hallada | NOT_MATERIAL | — | Sí | D-GOV-08 | Confirmación | N28 y N20 sustentan el inventario; DIG-03 sigue por GOV-DIG-004 | NO_CHANGE_UNDETERMINED |
| HR-02 | GOV-HR-005 | Mantener enlace entre empleado/cargo/unidad/centro presupuestario y pago agregad | N20,N27 | N40-01, N40-NF2 | arts. 14 y 30: datos de personal confidenciales | MATERIAL_FOR_SUBFEATURE_ONLY | Clasificación solo APN; transporte sin norma | Sí | D-GOV-07 | Sí | N20 y N27 sustentan el enlace; N40 condiciona clasificación y transporte | NARROW_N40_BLOCKER |
| F05 F06 | RNF-GOV-001 | Aislamiento Cada tenant/ente debe tener aislamiento de datos, llaves, configurac | N20,N27 | Ninguno | Ninguna regla hallada | NOT_MATERIAL | — | Sí | — | Confirmación | Fundamento técnico sin bloqueo de proceso | NO_CHANGE_UNDETERMINED |
| F03 F04 | RNF-GOV-006 | Autorizacion Toda autorizacion critica se valida en backend; no confiar en UI ni | N20 | N40-01 | art. 30 | REDUNDANT_WITH_VALIDATED_SOURCE | — | Sí | — | Sí | N20 lo sustenta | NO_CHANGE_UNDETERMINED |
| F11 F12 | RNF-GOV-010 | Disponibilidad Definir RTO/RPO por instalacion y validar backup/restore antes de | N20,N27 | Ninguno | Ninguna regla hallada | NOT_MATERIAL | — | Sí | — | Confirmación | N20 art. 39.9 lo sustenta | NO_CHANGE_UNDETERMINED |
| F01 F18 | RNF-GOV-011 | Seguridad Cifrado en transito, secretos fuera de codigo, MFA para roles privileg | N27 | N40-01 | arts. 5.3, 21, 26 y 27 par. 2.º: cifrado y claves de máximo privilegio | MATERIAL_FOR_SUBFEATURE_ONLY | Cifrado de lo confidencial, solo APN | Sí | — | Sí | Exige contenedores cifrados para lo confidencial; revisar contra F01 y F18 | NO_CHANGE_UNDETERMINED |
| F10 | RNF-GOV-015 | Interoperabilidad APIs versionadas, contrato de esquema, errores deterministas y | N28 | N40-NF1 | N28 arts. 26 y 27 | UNDETERMINED | Contrato de interoperabilidad | No medido | — | Sí | Normas del operador no localizadas | NO_CHANGE_UNDETERMINED |
| F22 | RNF-GOV-017 | Observabilidad Logs estructurados, metricas, health checks y correlacion sin fil | N20,N27 | Ninguno | Ninguna regla hallada | NOT_MATERIAL | — | Sí | — | Confirmación | N20 y N27 lo sustentan | NO_CHANGE_UNDETERMINED |
| F26 | RNF-GOV-021 | Privacidad operativa Minimizar exposicion de cedulas, bancos, declaraciones y da | N20,N27 | N40-01 | arts. 14 y 30 | MATERIAL_FOR_SUBFEATURE_ONLY | Clasificación de datos personales, solo APN | Sí | — | Sí | N20 y N27 cubren la minimización; N40-01 añade niveles | NO_CHANGE_UNDETERMINED |
| F16 | RNF-GOV-023 | Configuracion segura Valores regulatorios y endpoints no se hardcodean; cambios  | N20 | Ninguno | Ninguna regla hallada | NOT_MATERIAL | — | Sí | — | Confirmación | N20 lo sustenta | NO_CHANGE_UNDETERMINED |

## Por proceso

| Proceso | Clase | Acción | Estado resultante |
|---|---|---|---|
| ORG-06 | REDUNDANT_WITH_VALIDATED_SOURCE | REMOVE_N40_BLOCKER | NOT_STARTED |
| DOC-01 | CONDITIONAL | NARROW_N40_BLOCKER | BLOCKED |
| DOC-05 | MATERIAL_REQUIRED | KEEP_N40_BLOCKER | BLOCKED |
| DOC-07 | REDUNDANT_WITH_VALIDATED_SOURCE | REMOVE_N40_BLOCKER | BLOCKED |
| CTL-02 | NOT_MATERIAL | REMOVE_N40_BLOCKER | NOT_STARTED |
| CTL-03 | NOT_MATERIAL | REMOVE_N40_BLOCKER | NOT_STARTED |
| DIG-02 | MATERIAL_FOR_SUBFEATURE_ONLY | NARROW_N40_BLOCKER | BLOCKED |
| DIG-03 | UNDETERMINED | NO_CHANGE_UNDETERMINED | BLOCKED |
| HR-02 | MATERIAL_FOR_SUBFEATURE_ONLY | NARROW_N40_BLOCKER | BLOCKED |

## DOC-01

- **EXPEDIENTE_CORE:** índice, foliado lógico, metadatos y cronología (GOV-DOC-001) citan N25, N26, N27 y N29. No citan N40.
- **SIGNATURE_OR_INTEGRITY_WHEN_APPLICABLE:** GOV-DOC-002 es condicional. Conservar la firma recibida y el hash no exige N40; verificarla sí (DOC-05).
- **SECURITY_TECHNICAL_SUBFEATURES:** N40-01 clasifica expedientes con terceros como «Confidencial» (art. 14) y al conjunto por su documento más alto (art. 17). No está en la IR y solo obliga a la APN.

DOC-01 **sigue BLOCKED**: la pregunta 3 del paquete decide si esa clasificación forma parte del producto, y falta medir si «por tramite/procedimiento» depende del catálogo D-GOV-06. No hubo desbloqueo falso.
