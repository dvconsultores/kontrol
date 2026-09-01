# RECONVERGENCIA FORMAL DE LA SPEC 046 — N9

`/speckit.converge 046`, ejecutada contra el sistema **actual** y no contra su
cierre histórico.

## 1. Por qué se reconverge

La Spec 046 cerró `COMPLETE_100` el 2026-08-30. Después se demostró que ese
cierre contenía una afirmación inexacta —19 tipos registrados y uno probado— y
que la semántica de empresa de cinco módulos consumidores era incorrecta.

ARCH-MC-001 corrigió la semántica. N9 corrige la evidencia. El estado histórico
no se reutiliza como prueba: se vuelve a comprobar.

## 2. Requisitos frente al sistema actual

| Bloque | Estado |
|---|---|
| Modelo documental: `Document`, `DocumentVersion`, `StoredFile`, `DocumentLink` | PASS |
| Registro cerrado de tipos vinculables | PASS — **23**, cerrado ante nombres inventados |
| Subida, hash en servidor, MIME por contenido, tamaño | PASS |
| Versionado sin sobrescritura | PASS |
| Idempotencia de subida | PASS |
| Descarga y previsualización | PASS, con política de contenido activo |
| Integridad en la entrega | PASS — objeto alterado y objeto ausente detectados |
| Análisis antivirus | PASS — ClamAV 1.4.3 real |
| Congelado de versión | PASS — el histórico no se reinterpreta |
| Borrado protegido y archivado | PASS |
| Metadata declarada por tipo | PASS |
| Seguridad: IDOR, entre empresas, entre tenants | PASS |
| Vincular y desvincular con autorización | PASS |
| Auditoría | PASS |
| Proveedor de sistema de ficheros | **VERIFIED** |
| Proveedor compatible con S3 (`FR-046-032`, P1) | `IMPLEMENTED_NOT_VERIFIED` |
| Retención (`FR-046-065`, P1) | Purga implementada; planificador, de otra Spec |

## 3. Lo que cambió respecto del cierre histórico

**La capacidad de vinculación pasó de 1 tipo probado a 23.** Es el cambio
sustantivo: 046 declaraba un registro cerrado de consumidores y solo uno estaba
demostrado.

**La seguridad entre empresas se corrigió en N5.** `_get_document` resolvía el
alcance contra todas las empresas del tenant. Hoy resuelve contra la empresa
activa, y hay pruebas de metadatos, descarga, previsualización y versiones.

**La matriz de consumidores se rehízo.** Declaraba desbloqueadas cinco Specs por
«tipo registrado y probado»; el propio `REM-046-001` la corrigió, y ahora el
enunciado es cierto porque los 23 están probados.

## 4. Lo que no cambió, y está bien

El modelo documental. `REM-046-001` ya lo decía: *«la causa no está en el modelo
documental: `Document`, `DocumentVersion`, `StoredFile` y `DocumentLink`
soportan perfectamente estos recursos»*. N9 lo confirma sin tocarlos.

## 5. Deuda declarada, no escondida

| Qué | Prioridad | Dueño |
|---|---|---|
| Verificación de S3 con servicio real | P1 | Entorno; el adaptador está implementado |
| Planificador de retención | P1 | Spec de instalación y actualización |

Ninguna es P0. Ninguna se disfraza de completada.

## 6. Veredicto

**`SPEC 046 — RECONVERGED (2026-09-01)`**

Su cierre vuelve a ser exacto, ahora con la evidencia que le faltaba.
