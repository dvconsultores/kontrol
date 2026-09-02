# N10 — REGRESIÓN DEL SUBSISTEMA DOCUMENTAL

## Registro de tipos vinculables

Recontado, no citado: **23** `ResourceKind`. Sin cambios desde N9 y sin cambios
legítimos que documentar.

| | |
|---|---:|
| Esperados | 23 |
| Registrados | 23 |
| Verificados con entidad real | 23 |
| Faltantes | 0 |
| Sobrantes | 0 |
| Duplicados | 0 |

## Cierre del registro

`AnyModel`, `parties`, una ruta de importación y una inyección de tabla: los
cuatro rechazados. El registro no admite un modelo dinámico.

## Seguridad documental

Metadatos, descarga, vista previa y versiones de otra empresa: bloqueados.

## Historia congelada

Un vínculo congelado en la versión aprobada sigue apuntando a esa versión
después de crearse otra. `freeze_links` es una operación del servicio que
invoca el consumidor cuando su entidad se vuelve inmutable, no una bandera del
cuerpo de la petición.

## Antivirus

ClamAV **1.4.3** real, con firmas descargadas.

| Caso | Resultado |
|---|---|
| Archivo limpio | Se entrega |
| EICAR | Rechazado |
| Escáner ausente | `SCAN_FAILED` |
| Limpio falso | **0** |

El tercer caso se observó de verdad en este ciclo, y no a propósito: el entorno
de N10 empezó sin ClamAV instalado y quince pruebas de seguridad documental
fallaron con `SCAN_FAILED`. Es el comportamiento correcto —sin escáner no se
afirma que un archivo esté limpio— y una demostración mejor que la deliberada.

## Almacenamiento

| Backend | Estado |
|---|---|
| Disco | `VERIFIED` |
| S3 | `IMPLEMENTED_NOT_VERIFIED` — P1 externa, sin servicio real en este entorno |

Las pruebas que se saltan son las de `test_documents_storage.py`. Ninguna otra.

## Spec 045

Integración de `ApprovalRequest`: PASS. La empresa impuesta desde el cuerpo:
bloqueada. Y N10 añadió lo que faltaba en el otro extremo: quién puede decidir
sobre esa solicitud.

## Estados

`REM-046-001`: **CLOSED**. Spec 046: **RECONVERGED**. Sin cambios en N10.
