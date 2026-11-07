# GOV-ORG-04 · registro de intentos

Máximo 2 reintentos semánticos por subtarea real. Una subtarea nueva exige NEW_ROOT_CAUSE=1 o NEW_TECHNICAL_BOUNDARY=1, registrado aquí. Tras STOP: rediagnóstico, división o reclasificación.

Declaraciones de Claude:
- Encargo T004p ambiguo («deben fallar con 404»): error de Claude; no consumió reintento de DeepSeek.
- Encargos T011..T014 sin el cuerpo de los tipos: DeepSeek inventó campos; causa compartida con Claude. Se corrigió con el contrato literal.
- Encargo T016 con selectores `exact` que no valen para celdas con dos datos.
- Ajustes mecánicos sin semántica: `import User` reubicado, `ruff --fix` (I, F401, F541, F841) y orden de imports de `app/main.py`; `GovernmentOfficial` añadido a un import, avisado en el encargo; bloques SEARCH que unían líneas no contiguas o repetían una línea, aplicados con su mismo REPLACE; `T019t`, dividido en dos puntos del mismo fichero.
- La primera suite PostgreSQL corrió sin `KONTROL_PG_BIN_DIR`: 30 fallos de copia de seguridad atribuibles al entorno, no al producto.

Defectos reales de producto hallados por las pruebas y corregidos por DeepSeek:
- T003n: nombres de esquema repetidos renombraban componentes OpenAPI existentes.
- T014d: doble serialización del cuerpo en dos pantallas.
- T013e: `FormField` sobre casillas duplicaba `id` y dejaba rótulos sin control.
- T014e: el nombre del funcionario no se podía vaciar y se enviaba vacío si no se tocaba.
- T016c: `<dl>` mal formada (axe).
- T016f: contraste de `ErrorState` compartido: ORG-04 usa `ErrorDeCarga` propio; OBS-A11Y-ERRORSTATE-01 queda abierta en núcleo compartido.
- T011v: la vigencia mostrada ignoraba el fin efectivo.
- T019s: el catálogo SoD devolvía 500 porque el tipo de salida no admitía `ORG-04`.

## Registro cronológico

```
T001b ATTEMPT AUDIT_PASS flash
T001 ATTEMPT AUDIT_REJECT sa.Column,CHECK opciones,DROP CONSTRAINT,funciones
T001 RETRY_1 AUDIT_PASS
T003 ATTEMPT AUDIT_PASS
T005 ATTEMPT AUDIT_REJECT campos inventados, db.or_, del db, firma sin validar, is_maxima_autoridad, SoD inventado
T005 RETRY_1 AUDIT_REJECT autorizacion is True, cargo_origen sin validar
T005 RETRY_2 AUDIT_PASS
T004 ATTEMPT TRANSPORT_TIMEOUT (no semantico); dividido
T006 ATTEMPT AUDIT_REJECT _invalida sin raise x3, imports esquemas, True en where
T007 ATTEMPT AUDIT_REJECT columnas, eficacia_revocacion, ocupacion_en, csv, formas de salida
T006 RETRY_1 AUDIT_PASS
T004 fix RETRY_1 parcial: bloques aplicados salvo f03; ocupantes importa en funciones
T008 ATTEMPT parcial: api y main aplicados; R1 por AsignacionRevocarIn, ejercicio y ramas auditoria
T007 RETRY_1 AUDIT_PASS estatico
T008 RETRY_1 AUDIT_PASS
T004 RETRY_2 aplicado
T004H NEW_ROOT_CAUSE: arnes usa medio_publicacion, rutas sin /api/v1, import service_sod; ATTEMPT
T004H AUDIT_PASS
T004b/c STOP tras RETRY_2 -> REDIAGNOSE: encargo no fijaba semantica de cargo_b ni de activa(). DIVIDE en T004p (f13-f29) y T004q (f30-f49). RECLASSIFY a deepseek-v4-pro. NEW_ROOT_CAUSE documentada.
T004S AUDIT_PASS
T007F AUDIT_PASS
T004p AUDIT_REJECT aserciones 404 por encargo mio ambiguo (error de Claude): redisenado; no consume reintento de DeepSeek
T004 fallos residuales son de prueba; REDIAGNOSE hecho; T004v funciones por nombre
T004w/x/y NEW_ROOT_CAUSE=0; RETRY_1 de T004v por funcion, causas exactas
T004y RETRY_1 AUDIT_PASS (aviso de formato: falsa alarma)
T004x RETRY_1 AUDIT_PASS parcial: f18 conserva autorizacion_concejo=True; omision de Claude en el encargo; T004z
T004z AUDIT_PASS
T004w RETRY_1 parcial: f36,f46,f48 AUDIT_PASS; f47 REJECT (retiro aserciones de codigos); f31 motivo corto; f33 acto a mano viola ck_emitido_documentado; RETRY_2
T004w2 RETRY_2 AUDIT_PASS; T004 49/49 PG; ruff limpio
T009 ATTEMPT AUDIT_REJECT: falta fixture gobierno, json()[error][code] inexistente, fechas date sin isoformat, import O
T008m ATTEMPT parcial: 15/18 bloques; 3 SEARCH no coinciden y falta import delete: RETRY_1
T008m RETRY_2 AUDIT_PASS parcial; STOP. REDIAGNOSE: quedan 3 errores con causa nueva (clave de dict inferida, variable reutilizada); DIVIDE T008n, NEW_ROOT_CAUSE=1
T009 RETRY_1 aplicado; fallo por arnes: login con alta MFA en hilos colisiona en uq_mfa_factor_active. NEW_ROOT_CAUSE=1 (no es producto): T009h
T008n AUDIT_PASS (SEARCH 4 con sangria distinta: casado por texto sin sangria, formato)
T009h AUDIT_PASS: c1,c3,c4,c5 verdes x3
T009d NEW_ROOT_CAUSE=1: datos de caso, no arnes. c2 usa FIRMAR en DELEGACION_ATRIBUCIONES (error del encargo de Claude); c6 viola CHECK de activacion antes que la exclusion
T003n AUDIT_PASS; T009d AUDIT_PASS: 55/55 PG x3; c1..c6 verdes
T010 AUDIT_PASS (bloque 4 con ancla ambigua: anadido al final del fichero, formato)
T011 ATTEMPT AUDIT_REJECT CargoOcupacionPage: campos inventados
T011 causa raiz parcial de Claude: encargo sin cuerpos de tipos; se anade contrato literal
T012 ATTEMPT AUDIT_REJECT campos inventados (encargo sin cuerpos de tipos)
T013,T014 ATTEMPT AUDIT_REJECT campos inventados; RETRY_1
T012 RETRY_1 AUDIT_PASS (SEARCH duplicados por dos apariciones, aplicados a ambas; formato)
T014 RETRY_2 AUDIT_PASS; T011 RETRY_1/T011b AUDIT_PASS
T013 RETRY_2 AUDIT_PASS
T013 STOP tras RETRY_2; REDIAGNOSE: nombre figuraElegida ya existia como FiguraCatalogo (colision); NEW_ROOT_CAUSE=1; T013c
T013c AUDIT_PASS; TSC y ESLint limpios en ocupacion
T014d defecto de producto detectado por Vitest: JSON.stringify doble
T015 ATTEMPT fallos de arnes; T015r* RETRY_1. T016 ATTEMPT AUDIT_REJECT; RETRY_1
T013e defecto de accesibilidad detectado por Vitest: FormField sobre label duplica id
T015 RETRY_2 enviado con causas exactas
T015sB RETRY_2 AUDIT_REJECT (ficheros fuera de alcance). STOP; REDIAGNOSE; DIVIDE por causas: T015n1 ApiError y ruta; T015n2 casillas; T015n3 cargo y NAP-09/10
T014e defecto producto: nombre no vaciable. T015p residuales
T015 AUDIT_PASS 1371/1371 tras DIVIDE T015n,p,q,t,u
T016 RETRY_2 aplicado; 02 PASS; T016c NEW_ROOT_CAUSE axe
OBS-A11Y-ERRORSTATE-01: ErrorState compartido falla contraste en bg-danger; 64 modulos; no absorbido; ORG-04 usa ErrorDeCarga propio. T016f NEW_ROOT_CAUSE
T016 diagnostico: API correcta, carrera de navegacion en la prueba; fin_efectivo inclusivo confirmado
T011v AUDIT_PASS; T016g AUDIT_PASS
T016 PASS 27/27 Chromium, Firefox, WebKit x3, 0 retries
T017 AUDIT_PASS tras RETRY_1 (22 controles OC, total 118)
Mutaciones ronda 1: 16 KILLED, 3 SURVIVED (M4, M10b, M15): faltaban pruebas; T018r
T018 19/19 KILLED tras T018r; T018r RETRY_1
Suite PG 1: 30 fallos por KONTROL_PG_BIN_DIR sin exportar (error de Claude); DEFECTO: Literal de proceso SoD sin ORG-04 -> 500 en catalogo; T019s
T019s,t AUDIT_PASS
T019t: el SEARCH de DeepSeek unia lineas no contiguas; aplicado su REPLACE en dos puntos (mecanico, declarado)
Convergencia: FR-005 parcial, emisor ausente en cargo a fecha; T011e
T011e ATTEMPT AUDIT_REJECT: dos elementos JSX sin padre; RETRY_1
T011e RETRY_2 AUDIT_PASS
```
