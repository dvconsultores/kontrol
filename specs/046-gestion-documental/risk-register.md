# REGISTRO DE RIESGOS — SPEC 046

## 1. Modelo de amenazas (§126) — requisito, no anexo

Esta Spec introduce la primera superficie de **entrada de binarios** de KONTROL.
Hasta hoy el sistema solo generaba archivos; a partir de aquí los recibe.

| # | Amenaza | Vector | Mitigación de diseño | Verifica |
|---|---|---|---|---|
| AMZ-01 | **Recorrido de rutas** | Nombre con `../`, ruta absoluta, Unicode, doble codificación | La `storage_key` la genera el servidor; el nombre del usuario **nunca** toca el sistema de archivos | AC-046-05 |
| AMZ-02 | **Suplantación de MIME** | `.exe` renombrado a `.pdf`; `Content-Type` falso | Detección por contenido; declarado y detectado por separado; discrepancia rechazada | AC-046-06, 07 |
| AMZ-03 | **Subida de ejecutable** | Tipo no contemplado por la lista blanca | Lista blanca por tipo; **vacía significa ninguno** | AC-046-02, 26 |
| AMZ-04 | **Contenido activo** | SVG o HTML con guion, mostrado en contexto autenticado | Siempre `attachment`, nunca en línea | AC-046-25 |
| AMZ-05 | **XSS por nombre de archivo** | Nombre con etiquetas, mostrado sin escapar | Saneado solo para presentación; el original se conserva sin interpretarse | AC-046-05 |
| AMZ-06 | **Referencia insegura directa** | Adivinar o filtrar un identificador | Autorización sobre la **entidad vinculada**; respuesta 404 | AC-046-20, 21 |
| AMZ-07 | **Fuga entre empresas** | Vincular o descargar cruzado | Filtro obligatorio en las cinco operaciones | AC-046-22 |
| AMZ-08 | **Fuga por URL pública** | URL permanente o registrada | Sin URL públicas; las firmadas expiran y no se registran | AC-046-23, 49 |
| AMZ-09 | **URL firmada de vida larga** | TTL excesivo o alcance amplio | TTL corto y configurable, alcance al objeto | AC-046-23 |
| AMZ-10 | **Malware** | Archivo infectado distribuido por el repositorio | Estado de seguridad; no `CLEAN` no se entrega; sin analizador **se declara** | AC-046-27, 28 |
| AMZ-11 | **Bomba de descompresión** | Comprimido anidado | Comprimidos rechazados por defecto | AC-046-26 |
| AMZ-12 | **Adivinación de `storage_key`** | Clave derivable del nombre | Clave opaca y aleatoria | AC-046-04 |
| AMZ-13 | **Sobrescritura** | Reemplazar el binario de una versión histórica | Nunca en sitio: versión nueva | AC-046-10, 12 |
| AMZ-14 | **Colisión de hash como control** | Confiar en el hash para autorizar | El hash es integridad, **no** autorización | AC-046-36 |
| AMZ-15 | **Asignación masiva** | Enviar `storage_key`, `sha256` o `version_number` | El servidor los determina; los del cliente se ignoran | AC-046-09, 11 |
| AMZ-16 | **Vinculación no autorizada** | Adjuntar a una entidad ajena | Permiso sobre el destino | AC-046-17 |
| AMZ-17 | **Desvinculación no autorizada** | Quitar evidencia de un proceso cerrado | Vínculo congelado inmutable | AC-046-19 |
| AMZ-18 | **Agotamiento por archivo grande** | Subida enorme | Máximo por tipo, rechazo temprano | AC-046-08 |
| AMZ-19 | **Inyección de cabeceras** | Nombre con CR/LF en `Content-Disposition` | Nombre saneado al construir la cabecera | AC-046-05 |
| AMZ-20 | **Fuga por registros** | Contenido o credenciales en trazas | Se registran identificadores, nunca contenido ni secretos | AC-046-49 |

---

## 2. Riesgos de proyecto

| ID | Riesgo | Prob. | Impacto | Sev. | Mitigación |
|---|---|---|---|---|---|
| **RSK-046-01** | **Pérdida de evidencia**: se borra un archivo que respaldaba un proceso cerrado | Media | **Crítico** | **CRÍTICA** | Borrado protegido; vínculo congelado; el binario sobrevive al archivado (AC-046-31, 32, 33) |
| **RSK-046-02** | **Metadata sin binario**: la base afirma un archivo que no está | **Alta** | **Alto** | **CRÍTICA** | Escribir→verificar→confirmar; verificación de integridad; `STORAGE_OBJECT_MISSING` en vez de contenido incorrecto (AC-046-34, 35) |
| **RSK-046-03** | **Descarga no autorizada**: conocer el identificador basta | Media | **Crítico** | **CRÍTICA** | Autorización sobre la entidad; 404 en vez de 403 (AC-046-20, 21) |
| **RSK-046-04** | **El repositorio distribuye malware** | Media | **Crítico** | **ALTA** | Lista blanca, MIME real, estado de seguridad, no `CLEAN` no se entrega |
| **RSK-046-05** | **Fuga entre empresas** | Baja | **Crítico** | **ALTA** | `company_id` en las cuatro entidades; prueba en las cinco operaciones |
| **RSK-046-06** | **Sobrescritura de versión histórica** | Media | **Crítico** | **ALTA** | Nunca en sitio; versión superada inmutable |
| **RSK-046-07** | **Dos versiones con el mismo número** en concurrencia | Media | Alto | **ALTA** | Restricción única e índice parcial de versión vigente (AC-046-11) |
| **RSK-046-08** | **Se inventa evidencia legada**: se crea un documento por cada texto | **Alta** | **Crítico** | **CRÍTICA** | Solo se marca; nunca se crea documento desde texto ni desde hash (AC-046-39, 40, 41) |
| **RSK-046-09** | **Referencias rotas del legado**: se reescribe una columna y se pierde la pista | Media | Alto | MEDIA | Las 9 columnas se conservan intactas; solo se anotan |
| **RSK-046-10** | **Duplicación de subida** por doble clic o reintento | **Alta** | Medio | MEDIA | Idempotencia con el mecanismo existente (AC-046-13) |
| **RSK-046-11** | **Almacenamiento no disponible** | Media | Alto | MEDIA | 503 explícito; sin metadata huérfana; reintento del borrado por el trabajador común |
| **RSK-046-12** | **Se convierte en un sistema de archivos por módulo** | Media | **Crítico** | **ALTA** | R-D0-08-1 y P22; componente único; matriz de consumidores como criterio de salida |
| **RSK-046-13** | **Sobreingeniería**: OCR, miniaturas, deduplicación y cuotas inflan el MVP | **Alta** | Medio | MEDIA | `FUTURE_CAPABILITY` explícito; el modelo no los bloquea |
| **RSK-046-14** | **Se inventan plazos legales de retención** | Media | **Alto** | **ALTA** | Se implementa la **capacidad**, no los plazos; ESC-046-03 escalado |
| **RSK-046-15** | **Se absorbe la Spec 050** al «unificar» las exportaciones | Media | Medio | MEDIA | Fuera de alcance declarado; `reporting` no se toca |
| **RSK-046-16** | **Análisis obligatorio que nadie puede desplegar**, o ausencia silenciosa | Media | **Alto** | **ALTA** | Configurable **y declarado**: `SKIPPED` viaja en la respuesta; ESC-046-01 escalado |
| **RSK-046-17** | **La clave foránea polimórfica degrada a texto libre** con el tiempo | Media | Alto | **ALTA** | Registro cerrado de tipos de recurso; tipo desconocido rechazado (AC-046-16) |

## 3. Riesgo dominante

**RSK-046-08 — inventar evidencia legada.** Las otras Specs enseñaron el patrón:
en 008 fue anular una referencia para que la migración pasara; en 011, asignar la
unidad más probable. Aquí la tentación equivalente es **crear un documento por
cada `file_ref` con texto**, y quedaría un repositorio lleno de documentos que no
se pueden abrir, con apariencia de completitud.

Por eso la migración de esta Spec **no crea ni un solo documento**: solo anota.

## 4. La diferencia con las Specs anteriores

| Spec | Riesgo dominante | Naturaleza |
|---|---|---|
| 008 | Que la jerarquía fuera inusable | **Producto** |
| 011 | Tardar: cada día perdía un dato irrecuperable | **Tiempo** |
| **046** | **Que el sistema entregue lo que no debe, o pierda lo que debe guardar** | **Seguridad e integridad** |

Es la primera Spec del proyecto cuyo riesgo dominante es de seguridad. De ahí que
el modelo de amenazas encabece este registro y no lo cierre.
