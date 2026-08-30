# PLAN — SPEC 046

## 1. Constitution Gate

| Principio | Cumplimiento | Cómo |
|---|---|---|
| P2 · Autorización expresa | ✅ | Ciclo documental; se detiene antes de implementar |
| P3 · Trazabilidad | ✅ | Matriz item por item |
| P4 · Núcleo fiscal separado | ✅ | 046 guarda evidencia; no toca el motor fiscal |
| **P5 · Dato histórico protegido** | ✅ **eje** | Versiones inmutables; evidencia en uso no se borra; original byte a byte |
| **P6 · Backend es la autoridad** | ✅ **eje** | Nombre, MIME, tamaño, permiso y hash se validan en servidor |
| P8 · Sin negocio en código | ✅ | Tipos y categorías nacen vacíos; ninguna extensión codificada |
| P11 · Accesibilidad y responsive | ✅ | NFR-046-04/05; subida sin arrastrar y soltar |
| P13 · Integridad transaccional | ✅ | Escribir, verificar, confirmar; sin metadata huérfana |
| **P17 / P22 · Autoridad única transversal** | ✅ **eje** | Un solo módulo documental; R-D0-08-1 |
| P18 · Sin modales complejos | ✅ | Biblioteca y detalle en página completa |
| P21 · Paridad del motor | ✅ | PostgreSQL 18.x **y proveedor de almacenamiento real** |
| P23 · Captura temprana | ✅ | El hash se calcula al recibir; después ya no es verificable |

**0 violaciones. 0 enmiendas requeridas.**

## 2. Qué se implementa y qué no

| Se implementa | No se implementa |
|---|---|
| `Document`, `DocumentVersion`, `StoredFile`, `DocumentLink` | Procesos consumidores (018, 019, 020, 027, 035, 040, 044) |
| `DocumentType`, `DocumentCategory`, esquema de metadata | Reglas regulatorias (044) |
| Abstracción de almacenamiento + proveedor de sistema de archivos | Notificaciones (047) |
| Subida, descarga y previsualización autorizadas | Absorción de exportaciones (050) |
| Hash, MIME real, tamaño, nombre seguro | OCR, miniaturas, deduplicación, cuotas, *legal hold* |
| Versionado con inmutabilidad | Subida multiparte |
| Estados, archivado, capacidad de retención | Plazos legales de retención |
| Componente de adjuntos + biblioteca | La integración de cada consumidor |
| Contratos de evento | Planificador propio |

## 3. Arquitectura

```
app/modules/documents/            ← NUEVO módulo transversal del monolito
    models.py     Document, DocumentVersion, StoredFile, DocumentLink,
                  DocumentType, DocumentCategory, FileSecurityScan
    storage.py    DocumentStorageProvider (interfaz)
                  FilesystemStorageProvider (por defecto)
                  S3CompatibleStorageProvider (segunda implementación)
    service.py    subida, hash, MIME, versionado, vinculación, autorización
    resources.py  registro de tipos de recurso vinculables
    api.py        endpoints
```

`documents` es un **módulo del monolito modular**, no un microservicio (§141).
El binario vive fuera; el código, dentro.

## 4. Decisiones técnicas

| Decisión | Alternativa descartada | Razón |
|---|---|---|
| `Document`/`Version`/`File`/`Link` | Adjunto por entidad | P17; y un archivo puede servir a varias entidades |
| Registro de tipos de recurso | Polimórfica libre | Sin él la autorización es imposible |
| Subida por el backend | URL pre-firmada | Única compatible con sistema de archivos y con validar antes de aceptar |
| `file_metadata` evoluciona | Tabla nueva | Ya tiene los campos y está vacía de uso |
| Dos columnas de estado | Una combinada | Documento y archivo tienen ciclos distintos |
| `EXPIRED` derivado | Persistido | Evita el desfase fecha/etiqueta |
| Escribir → verificar → confirmar | Confirmar → escribir | El error benigno es binario huérfano, no evidencia perdida |
| SVG solo descarga | Rechazarlo o mostrarlo | Cierra la ejecución activa sin perder el caso legítimo |
| Sin deduplicación | Deduplicar por hash | Acoplaría el ciclo de vida de documentos independientes |

## 5. Fases

| Fase | Contenido | Depende de | Por qué en este orden |
|---|---|---|---|
| **F1 · Modelo y catálogo** | 7 entidades; `file_metadata` evoluciona; migración de esquema | — | Nada se guarda sin dónde |
| **F2 · Abstracción de almacenamiento** | Interfaz + proveedor de sistema de archivos + verificación de integridad | F1 | El proveedor debe existir antes que el servicio |
| **F3 · Servicio documental** | Hash, MIME real, nombre seguro, tamaño, versionado, estados | F1, F2 | Donde vive el valor; se prueba sin API |
| **F4 · Vinculación y autorización** | Registro de recursos, `link`/`detach`, permisos, `allowed_actions` | F3 | **Antes que la API**: sin autorización, exponer descarga sería una vulnerabilidad |
| **F5 · Seguridad del archivo** | Estado de análisis, cuarentena, política por tipo | F3 | — |
| **F6 · API** | Documentos, versiones, vínculos, subida, descarga, previsualización | F4, F5 | — |
| **F7 · Pruebas de backend** | Unidad, integración, **seguridad**, concurrencia, fallo de almacenamiento | F6 | Antes del frontend |
| **F8 · Frontend** | Biblioteca, detalle, versiones, componente de adjuntos | F6, F7 | — |
| **F9 · Legado y cierre** | Marcado de columnas legadas, informe, E2E, convergencia | F8 | El legado se marca cuando el modelo existe |

> **F4 va antes que F6** deliberadamente. En la Spec 008 fue la captura del dato;
> aquí es la **autorización**: publicar una descarga antes de saber quién puede
> descargar convertiría la Spec en una vulnerabilidad, no en una capacidad.

## 6. Migraciones previstas

Números provisionales (§117): la cadena está hoy en `0022` y el número real se
fija al implementar, comprobando `alembic heads`.

| Migración | Tipo | Contenido | Clasificación |
|---|---|---|---|
| `00XX_document_model` | Esquema | 6 tablas nuevas; `file_metadata` evoluciona a `stored_files` | `SAFE_MIGRATION` |
| `00XX_document_legacy_marks` | Datos | Marca las 9 columnas `UNVERIFIED_LEGACY`; **no crea documentos** | `ANNOTATION_ONLY` |

`file_metadata` está **vacía de uso real** (sin endpoint, sin consumidor), de modo
que su evolución no requiere backfill, tal como el ADR anticipó.

La segunda migración **no crea ningún documento** a partir de texto: solo anota
qué columnas quedan pendientes de revisión humana. Es la diferencia entre
registrar una deuda y fabricar evidencia.

## 7. Impacto en módulos existentes

| Módulo | Cambio | Riesgo |
|---|---|---|
| `documents` | **Nuevo** | Medio — superficie de seguridad nueva |
| `system` | `file_metadata` evoluciona | Bajo — sin consumidores |
| `regulatory`, `homologation`, `licensing`, `master_data`, `inventory`, `fiscal` | **Ninguno funcional**: sus columnas se conservan y se marcan | Bajo |
| `reporting` | **Ninguno** | Ninguno — 050 conserva su mecanismo |
| Frontend compartido | Componente de adjuntos nuevo | Bajo |

**Ningún módulo consumidor se modifica.** 046 publica la capacidad; cada Spec la
adoptará en su momento.

## 8. Estrategia de pruebas

Sobre PostgreSQL 18.x **y un proveedor de almacenamiento real** (§158). Detalle
en `test-plan.md`. La seguridad no es un apartado: es una suite.

## 9. Rollout

1. Modelo y almacenamiento, sin API: nada cambia de comportamiento.
2. Servicio y autorización, probados sin exposición.
3. API, con la autorización ya construida.
4. Componente de adjuntos; los consumidores lo adoptan en sus propias Specs.
5. Marcado del legado, revisable antes de cualquier importación.

## 10. Políticas normativas anexas

| Documento | Gobierna |
|---|---|
| `document-consumer-contract-matrix.md` | Qué obtiene cada Spec y qué gobierna cada parte |
| `legacy-document-migration-matrix.md` | Clases del legado, regla del hash sin archivo, qué no se toca |

Ninguno amplía el alcance: ambos lo **restringen**.

## 11. Restricciones de esta iniciativa

No se implementa ninguna Spec consumidora. No se crea microservicio. No se
guardan binarios en PostgreSQL. No se inventan plazos legales ni archivos.
